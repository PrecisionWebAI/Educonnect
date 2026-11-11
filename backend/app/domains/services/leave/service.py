"""Leave reads: both leave screens, from `leaverequest`.

The student screen and the staff screen used to answer with invented applications;
the table already holds them and `student_id` says which screen a row belongs to.
"""

from uuid import UUID

from sqlmodel import Session, select

from app.core.formatting import day, stamp
from app.domains.academic.classroom.academics.models import ClassName, Classroom, Section
from app.domains.academic.classroom.students.models import Student
from app.domains.auth.roles import primary_role_name
from app.domains.admin.users.models import User

from .models import LeaveRequest
from .schemas import LeaveApplicationItem, StaffLeaveRow


def _class_label(session: Session, student: Student | None) -> str:
    """What the student's class-section is called: "Class 10-A"."""
    if student is None or student.classroom_id is None:
        return ""
    room = session.get(Classroom, student.classroom_id)
    if room is None:
        return ""
    classroom = session.get(ClassName, room.class_id)
    section = session.get(Section, room.section_id)
    name = classroom.classname if classroom else ""
    return f"{name}-{section.section_name}" if section else name


def list_leave_applications(
    session: Session, student_id: UUID | None = None
) -> list[LeaveApplicationItem]:
    """Student leave requests, newest first. `student_id` narrows it to one student."""
    statement = select(LeaveRequest).where(
        LeaveRequest.student_id != None  # noqa: E711
    )
    if student_id is not None:
        statement = statement.where(LeaveRequest.student_id == student_id)
    statement = statement.order_by(LeaveRequest.created_at.desc())  # type: ignore[attr-defined]

    items: list[LeaveApplicationItem] = []
    for request in session.exec(statement).all():
        student = session.get(Student, request.student_id)
        user = session.get(User, student.user_id) if (student and student.user_id) else None
        items.append(
            LeaveApplicationItem(
                id=request.id,  # type: ignore[arg-type]
                student=user.full_name if user else "",
                className=_class_label(session, student),
                type=request.leave_type,
                from_date=day(request.from_date),
                to_date=day(request.to_date),
                reason=request.reason or "",
                days=request.days,
                status=request.status,
                submittedAt=stamp(request.created_at),
            )
        )
    return items


def list_staff_leave(session: Session) -> list[StaffLeaveRow]:
    """Staff leave requests, newest first (`student_id` is NULL for these)."""
    statement = (
        select(LeaveRequest)
        .where(LeaveRequest.student_id == None)  # noqa: E711
        .order_by(LeaveRequest.created_at.desc())  # type: ignore[attr-defined]
    )

    items: list[StaffLeaveRow] = []
    for request in session.exec(statement).all():
        user = session.get(User, request.requester_user_id)
        items.append(
            StaffLeaveRow(
                id=request.id,  # type: ignore[arg-type]
                name=user.full_name if user else "",
                role=primary_role_name(session, request.requester_user_id) or "Staff",
                type=request.leave_type,
                from_date=request.from_date.strftime("%b %d"),
                days=request.days,
                balance=0,  # no leave-balance table yet
                status=request.status,
            )
        )
    return items
