from uuid import UUID
from fastapi import HTTPException
from sqlmodel import Session, select

from app.domains.academics.models import ClassName, Classroom, Section
from app.core.lifecycle import release_login
from app.core.logins import delete_login
from app.domains.academics.repository import delete_room_if_unused
from app.domains.users import repository as user_repository
from app.domains.users.models import User

from . import repository
from .models import Guardian, Student, StudentGuardianRelationship
from .schemas import StudentCreate, StudentDeleteResult, StudentRead


def _guardians_by_student(session: Session) -> dict[UUID, Guardian]:
    """{student_id: guardian} - one query for the whole directory.

    The **primary** guardian of each child (`is_primary`, then the order they were
    added), read through the link: a parent is one row shared by all their children,
    so this is the single place the directory looks for a family's contact - and the
    "Guardians" tile counts the logins among these rows.

    The directory shows the person and not the relation, so the relation the query
    also carries (`repository.primary_guardian_links`) is dropped here.
    """
    return {
        student_id: guardian
        for student_id, (guardian, _) in repository.primary_guardian_links(
            session
        ).items()
    }


def _build_student_read(
    session: Session, s: Student, guardian: Guardian | None = None
) -> StudentRead:
    user = session.get(User, s.user_id) if s.user_id else None
    guardian_user = (
        session.get(User, guardian.user_id) if guardian and guardian.user_id else None
    )
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
        # The guardian is a person of their own: the name, the login and the user id
        # all come from that row (never from a column copied onto the child).
        guardian_name=guardian.name if guardian else None,
        guardian=guardian.name if guardian else None,
        guardianEmail=guardian_user.email if guardian_user else None,
        guardianUserId=guardian_user.id if guardian_user else None,
        section_id=s.classroom_id,
        # The name is the profile's own; a student created before this column existed
        # still reads it from their login.
        name=s.full_name or (user.full_name if user else "Student"),
        # A student whose admission is not finished has no class or section yet.
        # Saying so beats inventing "10-A", which would file them in a class they
        # are not in (the frontend shows "Not placed" for an empty class).
        className=classroom.classname if classroom else "",
        section=sec.section_name if sec else "",
        # The profile stores a gender per student; "Male" used to be invented for
        # everyone, which silently broke the boys/girls split.
        gender=s.gender or "",
        # `Student` has no phone column yet, so there is nothing truthful
        # to send; the directory shows "-" rather than a made-up number.
        phone="",
        # No login means no address to show - never an invented one. The status is
        # "Active" for a student who simply has no account: it describes the roll,
        # not the login.
        email=user.email if user else "",
        # The roll comes first: a child who has left is Inactive **whatever their login
        # is doing**, and a student's login is never switched off - leaving the school is
        # a family matter, not a security one (`students/lifecycle.py`). Otherwise a
        # login that was switched off says so, and no login at all still describes the
        # roll as Active.
        status=(
            "Inactive"
            if s.deactivated_at is not None
            else ("Active" if (user is None or user.is_active) else "Inactive")
        ),
        #: The day they left (and when the button was pressed) - the directory's badge.
        leftOn=s.left_on.isoformat() if s.left_on else None,
        deactivatedAt=s.deactivated_at.isoformat() if s.deactivated_at else None,
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


def create_student(session: Session, student_in: StudentCreate) -> Student:
    """Add a student by hand (the admission form is the usual way in).

    A login is optional: a child may have no account of their own and sign in through
    their guardian's - when one **is** given it has to exist, and it must not already
    belong to another student. An **admission number** is not optional: the roll cannot
    name a student without one, so the server mints it from the school's own sequence
    when the client does not bring one, exactly as the admission screen does - "the
    form" and "the directory" describe one kind of row now.
    """
    if student_in.user_id is not None:
        user = user_repository.get_user_by_id(session, user_id=student_in.user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        existing_student = repository.get_student_by_user_id(
            session, user_id=student_in.user_id
        )
        if existing_student:
            raise HTTPException(
                status_code=400, detail="Student profile already exists for this user"
            )
    if not student_in.admission_number:
        # Imported here rather than at module level: the number sequence lives with
        # the admission workflow (`admissions/repository.py`), and that module
        # imports this domain.
        from app.domains.admissions import repository as admissions_repository

        student_in.admission_number = admissions_repository.next_admission_number(
            session
        )
    return repository.create_student(session, student_in=student_in)


def delete_student(session: Session, student_id: UUID) -> dict:
    """Permanently delete a student and every record that references it.

    Order matters: the child rows (attendance, marks, fees, homework, diary,
    leaves, library issues), the parent links and the admission application all
    carry a foreign key to `Student`, so they go before the profile. The
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
        select(StudentGuardianRelationship).where(
            StudentGuardianRelationship.student_id == student_id
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

    # --- 2. the row itself ----------------------------------------------------
    # The student **is** their admission row now, so deleting the student deletes
    # the application too - there is no second record to chase.
    student_user_id = student.user_id
    session.delete(student)
    # Flush first: the helper asks the database who is left in the room, so the
    # delete above has to be on its way before it looks.
    session.flush()
    classroom_removed = delete_room_if_unused(session, room_id)
    session.commit()
    # The `student` role goes with the row. The login itself is removed **only** when it
    # opened nothing else: a parent who also studied here (or a person with any other
    # role) keeps signing in - leaving the roll is not leaving the school
    # (`app/core/lifecycle.py::release_login`).
    login_removed = release_login(session, student_user_id, withdraw=["student"])

    return {
        "deleted": True,
        "id": student_id,
        "classroomRemoved": classroom_removed,
        "loginRemoved": login_removed,
    }


def _delete_user_login(session: Session, user_id: UUID | None) -> bool:
    """Remove a login and its role/chat/notification/ticket references.

    Kept as this domain's name for it; the work itself lives in `app/core/logins.py`,
    because the Staff Hiring screen removes logins too and they have to go the same way
    whoever is leaving.
    """
    return delete_login(session, user_id)
