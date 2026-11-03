from uuid import UUID
from fastapi import HTTPException
from sqlmodel import Session, select

from app.domains.academics.models import ClassName, Classroom, Section
from app.domains.academics.repository import delete_room_if_unused
from app.domains.users import repository as user_repository
from app.domains.users.models import User

from . import repository
from .models import StudentParentRelationship, StudentProfile
from .schemas import StudentCreate, StudentDeleteResult, StudentRead


def _guardians_by_student(session: Session) -> dict[UUID, User]:
    """{student_id: guardian login} - one query for the whole directory.

    The guardian is who the directory's "Guardians" tile counts: distinct parent
    **logins** linked to a student, not the free-text names on the profiles.
    """
    rows = session.exec(
        select(StudentParentRelationship.student_id, User).join(
            User, User.id == StudentParentRelationship.parent_user_id
        )
    ).all()
    return {
        student_id: user for student_id, user in rows if student_id is not None
    }


def _build_student_read(
    session: Session, s: StudentProfile, guardian: User | None = None
) -> StudentRead:
    user = session.get(User, s.user_id) if s.user_id else None
    # The student's class-section is a room; the class and the section letter are
    # read from the two platform catalogs it points at.
    room = session.get(Classroom, s.classroom_id) if s.classroom_id else None
    classroom = session.get(ClassName, room.class_id) if room else None
    sec = session.get(Section, room.section_id) if room else None

    return StudentRead(
        id=s.id,
        user_id=s.user_id,
        admission_number=s.admission_number,
        admissionNo=s.admission_number,
        date_of_birth=s.date_of_birth,
        guardian_name=s.guardian_name,
        guardian=s.guardian_name,
        guardianEmail=guardian.email if guardian else None,
        guardianUserId=guardian.id if guardian else None,
        section_id=s.classroom_id,
        name=user.full_name if user else "Student",
        # A student whose admission is not finished has no class or section yet.
        # Saying so beats inventing "10-A", which would file them in a class they
        # are not in (the frontend shows "Not placed" for an empty class).
        className=classroom.classname if classroom else "",
        section=sec.section_name if sec else "",
        # The profile stores a gender per student; "Male" used to be invented for
        # everyone, which silently broke the boys/girls split.
        gender=s.gender or "",
        # `studentprofile` has no phone column yet, so there is nothing truthful
        # to send; the directory shows "-" rather than a made-up number.
        phone="",
        email=user.email if user else "student@school.edu",
        status="Active" if (user and user.is_active) else "Inactive",
    )


def get_student(session: Session, student_id: UUID) -> StudentRead:
    student = repository.get_student_by_id(session, student_id=student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    guardian = _guardians_by_student(session).get(student.id)
    return _build_student_read(session, student, guardian)


def get_students(
    session: Session, skip: int = 0, limit: int = 100
) -> list[StudentRead]:
    raw_students = repository.get_students(session, skip=skip, limit=limit)
    guardians = _guardians_by_student(session)
    return [_build_student_read(session, s, guardians.get(s.id)) for s in raw_students]


def create_student(session: Session, student_in: StudentCreate) -> StudentProfile:
    # Validate user exists
    user = user_repository.get_user_by_id(session, user_id=student_in.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if student already exists for this user
    existing_student = repository.get_student_by_user_id(
        session, user_id=student_in.user_id
    )
    if existing_student:
        raise HTTPException(
            status_code=400, detail="Student profile already exists for this user"
        )

    return repository.create_student(session, student_in=student_in)


def delete_student(session: Session, student_id: UUID) -> dict:
    """Permanently delete a student and every record that references it.

    Order matters: the child rows (attendance, marks, fees, homework, diary,
    leaves, library issues), the parent links and the admission application all
    carry a foreign key to `studentprofile`, so they go before the profile. The
    student's own login is then removed; the guardian login is left alone - it is
    a separate person whose account outlives one child.

    The class-section goes with the **last** student in it: a room nobody sits in
    is not a class-section any more, so `delete_room_if_unused` removes it and
    everything it owned in this same transaction. The returned `classroomRemoved`
    names it, so the screen can say exactly what happened.
    """
    student = repository.get_student_by_id(session, student_id=student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # The class-section they sit in - read before the profile goes.
    room_id = student.classroom_id

    # --- 1. rows that reference the student profile ---------------------------
    links = session.exec(
        select(StudentParentRelationship).where(
            StudentParentRelationship.student_id == student_id
        )
    ).all()
    for link in links:
        session.delete(link)

    from app.domains.admissions.models import AdmissionApplication
    from app.domains.attendance.models import AttendanceRecord
    from app.domains.exams.models import Mark
    from app.domains.finance.models import FeeTransaction
    from app.domains.homework.models import DiaryRemark, HomeworkSubmission
    from app.domains.operations.models import LeaveRequest, LibraryIssue

    for model in (
        AttendanceRecord,
        Mark,
        FeeTransaction,
        HomeworkSubmission,
        DiaryRemark,
        LeaveRequest,
        LibraryIssue,
    ):
        for row in session.exec(
            select(model).where(model.student_id == student_id)  # type: ignore[attr-defined]
        ).all():
            session.delete(row)

    # --- 2. the admission application that created it -------------------------
    application = session.exec(
        select(AdmissionApplication).where(
            AdmissionApplication.student_id == student_id
        )
    ).first()
    if application is not None:
        session.delete(application)

    # --- 3. the profile, then the class-section it emptied --------------------
    student_user_id = student.user_id
    session.delete(student)
    # Flush first: the helper asks the database who is left in the room, so the
    # delete above has to be on its way before it looks.
    session.flush()
    classroom_removed = delete_room_if_unused(session, room_id)
    session.commit()
    _delete_user_login(session, student_user_id)

    return {
        "deleted": True,
        "id": student_id,
        "classroomRemoved": classroom_removed,
    }


def _delete_user_login(session: Session, user_id: UUID | None) -> None:
    """Remove a login and its role/chat/notification/ticket references."""
    if not user_id:
        return
    user = session.get(User, user_id)
    if user is None:
        return

    from app.domains.auth.models import UserRole
    from app.domains.chat.models import ChatMessage, ChatThreadParticipant
    from app.domains.operations.models import LeaveRequest, Notification, SupportTicket

    for row in session.exec(select(UserRole).where(UserRole.user_id == user_id)).all():
        session.delete(row)
    for row in session.exec(
        select(ChatThreadParticipant).where(ChatThreadParticipant.user_id == user_id)
    ).all():
        session.delete(row)
    for row in session.exec(
        select(ChatMessage).where(ChatMessage.sender_id == user_id)
    ).all():
        session.delete(row)
    for row in session.exec(
        select(Notification).where(Notification.user_id == user_id)
    ).all():
        session.delete(row)
    for row in session.exec(
        select(SupportTicket).where(SupportTicket.reporter_user_id == user_id)
    ).all():
        session.delete(row)
    for row in session.exec(
        select(LeaveRequest).where(LeaveRequest.requester_user_id == user_id)
    ).all():
        session.delete(row)

    session.delete(user)
    session.commit()
