"""Leave reads: both leave screens, from `leaverequest`.

The student screen and the staff screen used to answer with invented applications;
the table already holds them and `student_id` says which screen a row belongs to.

Both lists read their supporting facts (names, roles, class-section labels) in a
fixed number of statements. The old code looked each of them up per row, which is
why a school with a term's worth of leave took seconds to open a tab.
"""

from uuid import UUID

from sqlmodel import Session, select

from app.core.formatting import day, stamp
from app.domains.academic.classroom.labels import labels_by_section
from app.domains.academic.classroom.students.models import Student
from app.domains.admin.users.models import User
from app.domains.auth.roles import primary_role_labels
from app.domains.people.staff.models import Employee

from .models import LeaveRequest
from .schemas import LeaveApplicationItem, StaffLeaveRow


def _student_rows(
    session: Session, requests: list[LeaveRequest]
) -> list[LeaveApplicationItem]:
    student_ids = [request.student_id for request in requests if request.student_id]
    students = (
        {
            student.id: student
            for student in session.exec(
                select(Student).where(Student.id.in_(student_ids))
            ).all()
        }
        if student_ids
        else {}
    )
    user_ids = [student.user_id for student in students.values() if student.user_id]
    users = (
        {
            user.id: user
            for user in session.exec(select(User).where(User.id.in_(user_ids))).all()
        }
        if user_ids
        else {}
    )
    class_labels = labels_by_section(
        session,
        [student.classroom_id for student in students.values() if student.classroom_id],
    )

    items: list[LeaveApplicationItem] = []
    for request in requests:
        student = students.get(request.student_id)
        user = users.get(student.user_id) if (student and student.user_id) else None
        items.append(
            LeaveApplicationItem(
                id=request.id,  # type: ignore[arg-type]
                student=user.full_name if user else "",
                class_name=(
                    class_labels.get(student.classroom_id, "")
                    if student and student.classroom_id
                    else ""
                ),
                type=request.leave_type,
                from_date=day(request.from_date),
                to_date=day(request.to_date),
                reason=request.reason or "",
                days=request.days,
                status=request.status,
                submitted_at=stamp(request.created_at),
            )
        )
    return items


def _staff_rows(session: Session, requests: list[LeaveRequest]) -> list[StaffLeaveRow]:
    user_ids = list(dict.fromkeys(request.requester_user_id for request in requests))
    users = (
        {
            user.id: user
            for user in session.exec(select(User).where(User.id.in_(user_ids))).all()
        }
        if user_ids
        else {}
    )
    # The employee row is what carries EMP-####. A requester without one (a
    # guardian filing on a teacher's behalf, say) still gets a row - just no code.
    codes = (
        {
            employee.user_id: employee.employee_code
            for employee in session.exec(
                select(Employee).where(Employee.user_id.in_(user_ids))
            ).all()
        }
        if user_ids
        else {}
    )
    roles = primary_role_labels(session, user_ids)

    items: list[StaffLeaveRow] = []
    for request in requests:
        user = users.get(request.requester_user_id)
        items.append(
            StaffLeaveRow(
                id=request.id,  # type: ignore[arg-type]
                staff_name=user.full_name if user else "",
                staff_code=codes.get(request.requester_user_id, ""),
                role=roles.get(request.requester_user_id, "Staff"),
                leave_type=request.leave_type,
                from_date=day(request.from_date),
                to_date=day(request.to_date),
                days=request.days,
                reason=request.reason or "",
                status=request.status,
                applied_at=stamp(request.created_at),
            )
        )
    return items


def list_leave_applications(
    session: Session, student_id: UUID | None = None
) -> list[LeaveApplicationItem]:
    """Student leave requests, newest first. `student_id` narrows it to one student."""
    statement = select(LeaveRequest).where(LeaveRequest.student_id != None)
    if student_id is not None:
        statement = statement.where(LeaveRequest.student_id == student_id)
    statement = statement.order_by(LeaveRequest.created_at.desc())  # type: ignore[attr-defined]
    return _student_rows(session, list(session.exec(statement).all()))


def list_staff_leave(session: Session) -> list[StaffLeaveRow]:
    """Staff leave requests, newest first (`student_id` is NULL for these)."""
    statement = (
        select(LeaveRequest)
        .where(LeaveRequest.student_id == None)
        .order_by(LeaveRequest.created_at.desc())  # type: ignore[attr-defined]
    )
    return _staff_rows(session, list(session.exec(statement).all()))
