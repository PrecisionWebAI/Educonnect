"""One way to tell somebody something - and the **only** code that writes `notification`.

Two rules live here, and neither belongs in a caller:

* **Recipients are resolved from the data, never from the caller's list of names.**
  "The guardians of this child" is `student_guardian_relationship` -> `guardian.user_id`;
  "the class teacher" is `classroom.class_teacher_id` -> `employee.user_id`; "the
  principals" are the people holding the `principal` / `vice_principal` role. A screen
  that guessed differently would message the wrong family.
* **A notification never fails the thing that caused it.** The rows are written inside
  a savepoint and every exception is logged and swallowed (spec rule 9): a register that
  saved correctly must not 500 because the bell could not be rung.

`dedupe_key` is what makes "one message per event per person" true: the same key on a
second save finds the first row and writes nothing. The unique index in the model is
the backstop for two requests racing.
"""

import logging
from uuid import UUID

from sqlmodel import Session, select

from app.core.tenancy import tenant_of
from app.domains.academic.classroom.academics.models import Classroom
from app.domains.academic.classroom.students.models import (
    Guardian,
    Student,
    StudentGuardianRelationship,
)
from app.domains.auth.models import Permission, Role, RolePermission, UserRole
from app.domains.people.staff.models import Employee

from .models import Notification

logger = logging.getLogger("eduverse.notifications")

#: The events the school knows about today. Strings, because they are stored and
#: filtered on; a typo in a caller is a wrong string, not a crash - and the tests pin
#: the ones that matter.
EVENT_ATTENDANCE_ABSENT = "attendance.absent"
EVENT_ATTENDANCE_CONSECUTIVE = "attendance.consecutive"
EVENT_SUBSTITUTION_ASSIGNED = "substitution.assigned"
EVENT_SUBSTITUTION_WITHDRAWN = "substitution.withdrawn"
EVENT_HOMEWORK_ASSIGNED = "homework.assigned"
EVENT_HOMEWORK_FEEDBACK = "homework.feedback"
EVENT_COURSE_WEEK_SUBMITTED = "course.week_submitted"
EVENT_COURSE_WEEK_APPROVED = "course.week_approved"
EVENT_COURSE_WEEK_REJECTED = "course.week_rejected"
EVENT_COURSE_REMINDER = "course.reminder"

#: The people a message can be addressed to. Passed as a set by the caller.
GUARDIANS = "guardians"
STUDENT = "student"
CLASS_TEACHER = "class_teacher"
PRINCIPALS = "principals"
#: Whoever holds `course.approve` - resolved from role grants, never a name list.
COURSE_APPROVERS = "course_approvers"

#: The roles that count as "the office's head" for a school-wide alert.
PRINCIPAL_ROLES: tuple[str, ...] = ("principal", "vice_principal")

#: The tab the bell groups by - the row's own words, not the event name.
_KIND_BY_EVENT: dict[str, str] = {
    EVENT_ATTENDANCE_ABSENT: "Attendance",
    EVENT_ATTENDANCE_CONSECUTIVE: "Attendance",
    EVENT_SUBSTITUTION_ASSIGNED: "Substitution",
    EVENT_SUBSTITUTION_WITHDRAWN: "Substitution",
    EVENT_HOMEWORK_ASSIGNED: "Homework",
    EVENT_HOMEWORK_FEEDBACK: "Homework",
    EVENT_COURSE_WEEK_SUBMITTED: "Course",
    EVENT_COURSE_WEEK_APPROVED: "Course",
    EVENT_COURSE_WEEK_REJECTED: "Course",
    EVENT_COURSE_REMINDER: "Course",
}


def kind_for(event: str) -> str:
    """The tab a row belongs to ("Attendance"), derived from its event."""
    return _KIND_BY_EVENT.get(event, event.split(".")[0].replace("_", " ").title())


def guardian_user_ids(session: Session, student_id: UUID) -> list[UUID]:
    """The logins of this child's guardians (a family shares one person row)."""
    rows = session.exec(
        select(Guardian.user_id)
        .join(
            StudentGuardianRelationship,
            StudentGuardianRelationship.guardian_id == Guardian.id,
        )
        .where(StudentGuardianRelationship.student_id == student_id)
    ).all()
    return [row for row in rows if row is not None]


def student_user_id(session: Session, student_id: UUID) -> UUID | None:
    """This child's own login, when they have one."""
    student = session.get(Student, student_id)
    return student.user_id if student is not None else None


def class_teacher_user_id(session: Session, classroom_id: UUID) -> UUID | None:
    """The login of the teacher who runs this class-section, if one is assigned."""
    room = session.get(Classroom, classroom_id)
    school = tenant_of(session)
    if room is None or (school is not None and room.school_id != school):
        return None
    if room.class_teacher_id is None:
        return None
    employee = session.get(Employee, room.class_teacher_id)
    return employee.user_id if employee is not None else None


def principal_user_ids(session: Session) -> list[UUID]:
    """The school's head(s): whoever holds `principal` or `vice_principal`."""
    rows = session.exec(
        select(UserRole.user_id)
        .join(Role, Role.id == UserRole.role_id)
        .where(Role.codename.in_(PRINCIPAL_ROLES))
    ).all()
    return list(dict.fromkeys(row for row in rows if row is not None))


def course_approver_user_ids(session: Session) -> list[UUID]:
    """The logins whose roles hold `course.approve` - one query, tenant-filtered."""
    rows = session.exec(
        select(UserRole.user_id)
        .join(Role, Role.id == UserRole.role_id)
        .join(RolePermission, RolePermission.role_id == Role.id)
        .join(Permission, Permission.id == RolePermission.permission_id)
        .where(Permission.codename == "course.approve")
    ).all()
    return list(dict.fromkeys(row for row in rows if row is not None))


def audience(
    session: Session,
    *,
    roles: set[str],
    student_id: UUID | None = None,
    classroom_id: UUID | None = None,
) -> list[UUID]:
    """Every login that should hear about this, de-duplicated, no Nones.

    One person is one row per message even if they are two of these at once (a class
    teacher whose own child is in the class is both the teacher and the guardian).
    """
    found: list[UUID] = []
    if student_id is not None:
        if GUARDIANS in roles:
            found.extend(guardian_user_ids(session, student_id))
        if STUDENT in roles:
            own = student_user_id(session, student_id)
            if own is not None:
                found.append(own)
    if classroom_id is not None and CLASS_TEACHER in roles:
        teacher = class_teacher_user_id(session, classroom_id)
        if teacher is not None:
            found.append(teacher)
    if PRINCIPALS in roles:
        found.extend(principal_user_ids(session))
    if COURSE_APPROVERS in roles:
        found.extend(course_approver_user_ids(session))
    return list(dict.fromkeys(found))


def _write(session: Session, rows: list[Notification]) -> None:
    """The single insert. Separate so a test can make it fail on purpose."""
    session.add_all(rows)


def notify(
    session: Session,
    *,
    event: str,
    recipients: list[UUID],
    title: str,
    body: str,
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    dedupe_key: str | None = None,
    channel: str = "in_app",
    commit: bool = True,
) -> int:
    """Tell each recipient once. Returns how many rows were actually written.

    `commit=False` keeps the rows in the caller's transaction (the substitution flow
    does that, so a cover and its message cannot exist apart). With `commit=True` - the
    default, because most callers have already committed their own work - the rows are
    committed here, so a failure can never roll the caller back.

    Never raises: a notification that cannot be written is logged and reported as `0`.
    """
    user_ids = list(dict.fromkeys(uid for uid in recipients if uid is not None))
    if not user_ids:
        return 0

    if dedupe_key is not None:
        already = set(
            session.exec(
                select(Notification.user_id).where(
                    Notification.user_id.in_(user_ids),
                    Notification.dedupe_key == dedupe_key,
                )
            ).all()
        )
        user_ids = [uid for uid in user_ids if uid not in already]
        if not user_ids:
            return 0

    school = tenant_of(session)
    rows = [
        Notification(
            user_id=user_id,
            title=title,
            body=body,
            kind=kind_for(event),
            event_type=event,
            entity_type=entity_type,
            entity_id=entity_id,
            dedupe_key=dedupe_key,
            channel=channel,
            school_id=school,
        )
        for user_id in user_ids
    ]

    savepoint = None
    try:
        savepoint = session.begin_nested()
        _write(session, rows)
        session.flush()
        savepoint.commit()
        if commit:
            session.commit()
    except Exception as error:
        try:
            if savepoint is not None and savepoint.is_active:
                savepoint.rollback()
        except Exception:  # pragma: no cover - nothing left to roll back
            pass
        logger.warning(
            "notification %s was not written (%s): %s", event, dedupe_key, error
        )
        return 0

    return len(rows)
