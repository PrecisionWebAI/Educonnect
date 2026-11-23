"""Who may read or change a Course row - the server's answer, never the screen's.

The Course tab is one of the few places where "a teacher may read the class" is not the
same as "a teacher may read every subject in it". The permission says **whether** a
caller may open the tab; these helpers say **which rows** and **what they may do** with
them:

* the office (``course.manage`` / ``course.assign_teacher`` / ``course.approve`` /
  ``course.view_all``) sees the whole section and every teacher;
* a teacher (``course.read`` + ``course.plan``) sees only the subjects they hold **now**,
  and may submit a week or tick a chapter only for those;
* a second school sees nothing - every read goes through the tenant-filtered session
  (``app/core/db.py``), and a row from another school simply does not exist (404).

The three names the phase plan asks for are here: ``can_manage_course``,
``can_approve_course`` and ``is_own_course_teacher``. Everything else is built on them so
a later phase cannot invent a fourth interpretation of "my subject".
"""

from uuid import UUID

from sqlmodel import Session, select

from app.domains.academic.classroom.academics.models import Classroom, SubjectTeacher
from app.domains.academic.classroom.course.models import ClassroomSubject
from app.domains.auth.service import AuthorizationService
from app.domains.people.staff.models import Employee

#: The codenames this module speaks. Constants stop a typo becoming "denied forever".
COURSE_READ = "course.read"
COURSE_PLAN = "course.plan"
COURSE_ASSIGN_TEACHER = "course.assign_teacher"
COURSE_MANAGE = "course.manage"
COURSE_APPROVE = "course.approve"
COURSE_VIEW_ALL = "course.view_all"


def _has(session: Session, user, permission: str) -> bool:
    """The PBAC check, with the request's session (roles and grants are rows)."""
    return bool(user) and AuthorizationService.has_permission(
        user, permission, session=session
    )


def employee_of(session: Session, user) -> Employee | None:
    """The `employee` row behind a login, or None for a person who is not staff."""
    if user is None or getattr(user, "id", None) is None:
        return None
    return session.exec(select(Employee).where(Employee.user_id == user.id)).first()


def can_read_course(session: Session, user) -> bool:
    """May this caller open the Course tab (the subject rows are filtered after)?"""
    return _has(session, user, COURSE_READ)


def can_plan_course(session: Session, user) -> bool:
    """May this caller submit a week or tick a chapter for a subject they hold?"""
    return _has(session, user, COURSE_PLAN)


def can_manage_course(session: Session, user) -> bool:
    """The office: subjects, chapters, and any teacher's course."""
    return _has(session, user, COURSE_MANAGE)


def can_assign_teacher(session: Session, user) -> bool:
    """May this caller assign/change the teacher of a section subject?"""
    return _has(session, user, COURSE_ASSIGN_TEACHER)


def can_approve_course(session: Session, user) -> bool:
    """May this caller read the review queue and approve/reject a week?"""
    return _has(session, user, COURSE_APPROVE)


def can_view_all_courses(session: Session, user) -> bool:
    """May this caller see every teacher's course (the Teachers > Course tab)?"""
    return _has(session, user, COURSE_VIEW_ALL)


def may_read_section_course(session: Session, user, classroom_id: UUID) -> bool:
    """A section that exists in this school, and a caller who may open its Course tab.

    The existence check is a **select**, not `session.get`: the identity map can still
    hold a row loaded before the session was bound to another school, and `get` would
    return it without running the tenant filter. A select always runs it.
    """
    room = session.exec(
        select(Classroom.id).where(Classroom.id == classroom_id)
    ).first()
    if room is None:
        return False
    return can_read_course(session, user)


def _open_rows(
    session: Session, employee_id: UUID, classroom_id: UUID
) -> list[SubjectTeacher]:
    """The assignments this person holds **now** in this section (open rows only)."""
    return list(
        session.exec(
            select(SubjectTeacher)
            .join(
                ClassroomSubject,
                ClassroomSubject.id == SubjectTeacher.classroom_subject_id,
            )
            .where(
                ClassroomSubject.classroom_id == classroom_id,
                SubjectTeacher.teacher_id == employee_id,
                SubjectTeacher.effective_to.is_(None),
            )
        ).all()
    )


def is_own_course_teacher(session: Session, user, classroom_subject_id: UUID) -> bool:
    """Is the signed-in person the **current** teacher of this section subject?

    The claim is the open `subjectteacher` row linked to this `classroomsubject`; a
    closed row is history, not a claim.
    """
    course_subject = session.exec(
        select(ClassroomSubject).where(ClassroomSubject.id == classroom_subject_id)
    ).first()
    if course_subject is None:
        return False

    employee = employee_of(session, user)
    if employee is None:
        return False

    return any(
        row.classroom_subject_id == course_subject.id
        for row in _open_rows(session, employee.id, course_subject.classroom_id)
    )


def may_edit_plan(session: Session, user, classroom_subject_id: UUID) -> bool:
    """The office may edit any plan; a teacher only the subject they hold now."""
    if can_manage_course(session, user):
        return True
    return can_plan_course(session, user) and is_own_course_teacher(
        session, user, classroom_subject_id
    )


def may_read_teacher_course(session: Session, user, employee_id: UUID) -> bool:
    """The office reads anybody's course; a teacher reads only their own."""
    if can_view_all_courses(session, user):
        return True
    own = employee_of(session, user)
    return own is not None and own.id == employee_id and can_read_course(session, user)


def visible_course_subject_ids(
    session: Session, user, classroom_id: UUID
) -> set[UUID] | None:
    """Which subjects of this section the caller may see.

    `None` means **all** of them (the office's view, so the caller does not build an `IN`
    list from ids it already trusts). A set means only those rows; an empty set is a
    caller who may open the tab but holds nothing in this section.
    """
    if can_view_all_courses(session, user) or can_manage_course(session, user):
        return None
    if can_approve_course(session, user):
        # A reviewer reads the week they are deciding on, whichever teacher wrote it.
        return None
    if not can_read_course(session, user):
        return set()

    section_ids = set(
        session.exec(
            select(ClassroomSubject.id).where(
                ClassroomSubject.classroom_id == classroom_id
            )
        ).all()
    )
    if not section_ids:
        return set()

    employee = employee_of(session, user)
    if employee is None:
        return set()

    assignments = _open_rows(session, employee.id, classroom_id)
    return {
        row.classroom_subject_id
        for row in assignments
        if row.classroom_subject_id is not None
    } & section_ids
