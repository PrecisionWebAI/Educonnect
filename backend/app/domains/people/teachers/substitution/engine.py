"""Who can cover this period - and the words that justify the answer.

The order of business is fixed, because it is the order the office uses:

1. **hard filters.** Not the person who is away; not somebody off the staff roll;
   not somebody on approved leave that day; not somebody already standing in another
   room at that hour; not somebody who has their own class then - unless that class
   is itself covered, in which case they are free after all. A colleague who does
   not teach the subject never reaches this list: `teachersubject` is the gate.
2. **a ranking**, not a grade. Same department first, then somebody who already
   teaches that class-section (the children know them), then the lighter timetable -
   because the fair answer to "who is free" is usually the person with room.
3. **a reason, in words.** Every candidate is offered with the sentence that
   explains them, and every colleague who was refused carries the sentence that
   explains that too. A number nobody can interrogate is how a screen gets ignored
   in favour of the WhatsApp group.

Nothing here writes: the engine answers a question, `service` records the decision.
"""

from dataclasses import dataclass, field
from datetime import date
from uuid import UUID

from sqlmodel import Session

from app.domains.academic.classroom import labels as classroom_labels
from app.domains.academic.classroom.timetable.models import TimetablePeriod
from app.domains.people.staff.models import Employee
from app.domains.people.teachers import labels
from app.domains.people.teachers import repository as teachers_repository
from app.domains.people.teachers.profile.repository import employee_names

from . import repository
from .models import SubstitutionAssignment

#: A colleague from the absent teacher's own department.
SAME_DEPARTMENT = 20
#: Somebody who already takes this class-section - continuity for the children.
KNOWS_THE_CLASS = 5
#: Every eligible candidate starts here; the ranking only moves them around it.
BASE = 100


@dataclass
class DayContext:
    """One date's facts, read once and shared by every period on the board.

    The board asks "who is free at 09:00?" for a dozen periods; re-reading the
    school's timetable, its leave and its assignments for each of them is the
    difference between one board and thirty.
    """

    on_date: date
    #: `{employee_id: leave_type}` - who is on approved leave that day.
    on_leave: dict[UUID, str] = field(default_factory=dict)
    #: `{employee_id: [period, ...]}` for the whole school that weekday.
    periods_by_teacher: dict[UUID, list[TimetablePeriod]] = field(default_factory=dict)
    #: `{period_id: assignment}` - the slots already spoken for.
    assignments: dict[UUID, SubstitutionAssignment] = field(default_factory=dict)


def build_context(session: Session, on_date: date) -> DayContext:
    """Read the day once: leave, the weekday's timetable, and the covers arranged."""
    context = DayContext(on_date=on_date)

    leave = teachers_repository.approved_leave_between(session, on_date, on_date)
    if leave:
        people = repository.employees_by_user_ids(session, list(leave))
        for user_id, windows in leave.items():
            employee = people.get(user_id)
            if employee is not None and windows:
                context.on_leave[employee.id] = windows[0][2]

    weekday = repository.weekday_key(on_date)
    for period in repository.periods_on_weekday(session, weekday):
        context.periods_by_teacher.setdefault(period.teacher_id, []).append(period)

    for assignment in repository.assignments_on(session, on_date):
        context.assignments[assignment.period_id] = assignment

    return context


def _overlaps(first: TimetablePeriod, start, end) -> bool:
    """Whether two periods happen at the same hour (a shared boundary is fine)."""
    return first.start_time < end and first.end_time > start


def _label(period: TimetablePeriod, subject: str, class_labels: dict) -> str:
    """`Class 9-A Maths` - the words the blocked reason quotes."""
    room = class_labels.get(period.classroom_id, "")
    return f"{room} {subject}".strip()


def candidates(
    session: Session,
    *,
    period: TimetablePeriod,
    absent: Employee,
    context: DayContext,
) -> tuple[list, list]:  # (eligible, blocked)
    """`(eligible, blocked)` for one period, best first.

    Returns schema objects rather than dicts so the route has nothing to guess, and
    sorts by score **then by name**, so two colleagues with the same load are offered
    in a stable order instead of whatever the database happened to return.
    """
    from .schemas import BlockedCandidateRead, SubstitutionCandidateRead

    subject_name = repository.subject_names(session, [period.subject_id]).get(
        period.subject_id, "the subject"
    )
    teacher_ids = [
        teacher_id
        for teacher_id in repository.teacher_ids_for_subject(session, period.subject_id)
        if teacher_id != absent.id
    ]
    if not teacher_ids:
        return [], []

    people = repository.employees(session, teacher_ids)
    names = employee_names(session, teacher_ids)
    loads = teachers_repository.period_counts(session, teacher_ids)
    class_labels = classroom_labels.labels_by_section(session, [period.classroom_id])
    slot = _label(period, subject_name, class_labels)

    eligible = []
    blocked = []
    for teacher_id in teacher_ids:
        employee = people.get(teacher_id)
        name = names.get(teacher_id) or (employee.employee_code if employee else "")
        if employee is None:
            continue

        refused = _refusal(
            session, employee, period, context, subject_name, class_labels
        )
        if refused is not None:
            blocked.append(
                BlockedCandidateRead(employee_id=employee.id, name=name, reason=refused)
            )
            continue

        same_department = _same_department(absent.department, employee.department)
        weekly = loads.get(employee.id, 0)
        knows = any(
            own.classroom_id == period.classroom_id
            for own in context.periods_by_teacher.get(employee.id, [])
        )
        score = BASE + (SAME_DEPARTMENT if same_department else 0)
        score += KNOWS_THE_CLASS if knows else 0
        score -= weekly

        eligible.append(
            SubstitutionCandidateRead(
                employee_id=employee.id,
                name=name,
                employee_code=employee.employee_code,
                department=employee.department,
                same_department=same_department,
                weekly_periods=weekly,
                knows_the_class=knows,
                score=score,
                reason=_reason(
                    subject_name=subject_name,
                    same_department=same_department,
                    department=employee.department,
                    knows=knows,
                    slot=slot,
                    weekly=weekly,
                ),
            )
        )

    eligible.sort(key=lambda row: (-row.score, row.name.lower()))
    blocked.sort(key=lambda row: row.name.lower())
    return eligible, blocked


def _same_department(first: str | None, second: str | None) -> bool:
    """Departments compared the way every other filter in this domain compares them."""
    return bool(first and second) and first.strip().lower() == second.strip().lower()


def _reason(
    *,
    subject_name: str,
    same_department: bool,
    department: str | None,
    knows: bool,
    slot: str,
    weekly: int,
) -> str:
    """The sentence beside a candidate: why them, in the office's own terms."""
    parts = [f"Teaches {subject_name}"]
    if same_department and department:
        parts.append(f"{department} department")
    if knows:
        parts.append(f"already takes {slot}")
    parts.append(f"{weekly} periods a week" if weekly else "no periods yet this week")
    return "; ".join(parts)


def _refusal(
    session: Session,
    employee: Employee,
    period: TimetablePeriod,
    context: DayContext,
    subject_name: str,
    class_labels: dict,
) -> str | None:
    """Why this colleague cannot take the slot, or None if they can.

    Each answer is the sentence the office needs: not "unavailable", but "on
    approved Sick leave" or "teaching Class 9-A Maths at 09:00".
    """
    if labels.serves_read_only(
        deactivated_at=employee.deactivated_at, left_on=employee.left_on
    ):
        return "Off the staff roll"

    leave_type = context.on_leave.get(employee.id)
    if leave_type:
        return f"On approved {leave_type} leave"

    # Their own class does not block them when that class is already covered: the
    # whole point of a cover is that the person standing in frees their own slot.
    covered_by_others = {
        assignment.period_id
        for assignment in context.assignments.values()
        if assignment.substitute_employee_id != employee.id
    }
    for own in context.periods_by_teacher.get(employee.id, []):
        if not _overlaps(own, period.start_time, period.end_time):
            continue
        if own.id in covered_by_others:
            continue
        where = _label(own, subject_name, class_labels)
        return f"Teaching {where} at {own.start_time.strftime('%H:%M')}"

    for assignment in context.assignments.values():
        if assignment.substitute_employee_id != employee.id:
            continue
        other = repository.period(session, assignment.period_id)
        if other is None or not _overlaps(other, period.start_time, period.end_time):
            continue
        where = _label(other, subject_name, class_labels)
        return f"Already covering {where} at {other.start_time.strftime('%H:%M')}"

    return None
