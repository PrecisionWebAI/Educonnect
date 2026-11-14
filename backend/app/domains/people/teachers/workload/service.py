"""What the workload tab may change, why a write is refused, and the two reads.

The writes answer Phase 3's three questions in the same order, because the same
mistakes are possible here:

* **may this caller see this person?** - out of scope is `404`, never `403`: the
  API must not confirm that a colleague's id exists;
* **may this caller change the week at all?** - `teachers.manage_workload` plus
  `scope.may_manage_workload` decides the *capacity rule* and the *duties*; a
  department head holds the read right only;
* **is the record still open?** - a leaver's profile is history, so a new duty on
  it is `409`, with the message naming reactivation as the way back in.

A duty is a fact with a shape (`schemas.StaffDutyCreate` refuses the impossible
combinations), and every add or removal is appended to `staffauditlog` under the
`duty` section. The rule itself carries `updated_by_user_id` and `updated_at`
instead: it is a school-level policy, and the audit table is keyed on an employee.
"""

from datetime import date, time
from uuid import UUID

from fastapi import HTTPException
from sqlmodel import Session

from app.domains.academic.classroom.labels import labels_by_section
from app.domains.admin.users.models import User
from app.domains.people.staff.models import Employee

from .. import labels, scope
from .. import service as teachers_service
from ..profile import repository as profile_repository
from ..profile.service import record_audit, require_employee
from . import repository
from .models import StaffDuty
from .schemas import (
    DepartmentLoad,
    StaffDutyCreate,
    StaffDutyRead,
    StaffWeekRead,
    WeekDayRead,
    WeekSlotRead,
    WorkloadAnalytics,
    WorkloadRuleRead,
    WorkloadRuleWrite,
)


def require_manage(session: Session, user: User | None) -> None:
    """Refuse a write on the week unless this caller runs the timetable of staff.

    Checked here as well as on the route (`RequirePermission`), for the reason the
    profile's writes are: the route guard is one line somebody can forget to add,
    and this function is what every write already calls.
    """
    if not scope.may_manage_workload(session, user):
        raise HTTPException(
            status_code=403,
            detail="Your role may not set the workload capacity or assign duties.",
        )


# --- the capacity rule -----------------------------------------------------


def read_rule(session: Session) -> WorkloadRuleRead:
    """The school's policy as the dialog opens it, with who set it last."""
    row = repository.rule(session)
    if row is None:
        # The defaults are not a decision: `is_set` is what the dialog reads to
        # decide whether it is editing or making the first one.
        return WorkloadRuleRead(is_set=False)

    names = profile_repository.recorder_names(
        session, [row.updated_by_user_id] if row.updated_by_user_id else []
    )
    return WorkloadRuleRead(
        weekly_periods=row.weekly_periods,
        overload_percent=row.overload_percent,
        underload_percent=row.underload_percent,
        is_set=bool(row.weekly_periods),
        updated_at=row.updated_at,
        updated_by=names.get(row.updated_by_user_id)
        if row.updated_by_user_id
        else None,
    )


def set_rule(
    session: Session, payload: WorkloadRuleWrite, user: User | None
) -> WorkloadRuleRead:
    """Store the school's full week. One row, upserted, never a second policy."""
    require_manage(session, user)
    repository.save_rule(session, payload, user.id if user is not None else None)
    return read_rule(session)


# --- duties ----------------------------------------------------------------


def _duty_name(row: StaffDuty) -> str:
    """`Exam Duty` or `Exam Duty: Half-Yearly - Hall B`."""
    name = labels.DUTY_TYPE_LABELS.get(row.duty_type, row.duty_type)
    return f"{name}: {row.title}" if row.title else name


def _duty_summary(row: StaffDuty) -> str:
    """`Exam Duty (Monday 09:00-11:00)` - the line the audit feed prints.

    One sentence, in the reader's words: an auditor with the drawer open should
    not have to decode a column name to know what was added.
    """
    name = _duty_name(row)
    when: list[str] = []
    if row.day_of_week:
        when.append(labels.day_label(row.day_of_week) or row.day_of_week)
    if row.on_date:
        when.append(row.on_date.isoformat())
    if row.start_time and row.end_time:
        when.append(labels.period_label(row.start_time, row.end_time))
    return f"{name} ({' '.join(when)})" if when else name


def duty_read(row: StaffDuty) -> StaffDutyRead:
    """One row, with the screen's words for its type, its day and its slot."""
    slot = (
        labels.period_label(row.start_time, row.end_time)
        if row.start_time and row.end_time
        else None
    )
    return StaffDutyRead(
        id=row.id,
        duty_type=row.duty_type,
        duty_type_label=labels.DUTY_TYPE_LABELS.get(row.duty_type, row.duty_type),
        title=row.title,
        day_of_week=row.day_of_week,
        day_label=labels.day_label(row.day_of_week),
        on_date=row.on_date,
        start_time=row.start_time,
        end_time=row.end_time,
        slot=slot,
        hours=labels.hours_between(row.start_time, row.end_time),
        effective_from=row.effective_from,
        effective_to=row.effective_to,
        note=row.note,
        created_at=row.created_at,
    )


def duty_reads(session: Session, employee_id: UUID) -> list[StaffDutyRead]:
    """This person's duties, Monday first (see `repository._duty_order`)."""
    return [duty_read(row) for row in repository.duties(session, employee_id)]


def _require_open(employee: Employee) -> None:
    """Refuse a write on a person the school has taken off the roll (`409`)."""
    if labels.serves_read_only(
        deactivated_at=employee.deactivated_at, left_on=employee.left_on
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "This staff record is off the roll, so its week is read-only. "
                "Reactivate the person first."
            ),
        )


def add_duty(
    session: Session,
    employee: Employee,
    payload: StaffDutyCreate,
    user: User | None,
) -> StaffDutyRead:
    """Add one duty, refusing the same duty twice (`409`)."""
    require_manage(session, user)
    _require_open(employee)

    duplicate = repository.same_duty(
        session,
        employee_id=employee.id,
        duty_type=payload.duty_type,
        day_of_week=payload.day_of_week,
        on_date=payload.on_date,
        start_time=payload.start_time,
    )
    if duplicate is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                "That duty is already on this person's file: "
                f"{_duty_summary(duplicate)}."
            ),
        )

    row = StaffDuty(
        employee_id=employee.id,
        duty_type=payload.duty_type,
        title=payload.title,
        day_of_week=payload.day_of_week,
        on_date=payload.on_date,
        start_time=payload.start_time,
        end_time=payload.end_time,
        # A duty starts today unless the office back-dates it: "no start date" and
        # "started today" are the same fact, and NULL would make the column
        # optional in a table where every other date is a decision.
        effective_from=payload.effective_from or date.today(),
        effective_to=payload.effective_to,
        note=payload.note,
        created_by_user_id=user.id if user is not None else None,
    )
    session.add(row)
    session.commit()
    session.refresh(row)

    record_audit(
        session,
        employee_id=employee.id,
        section="duty",
        action="created",
        row_id=row.id,
        summary=f"Added {_duty_summary(row)}",
        user=user,
    )
    return duty_read(row)


def remove_duty(
    session: Session, employee: Employee, duty_id: UUID, user: User | None
) -> None:
    """Remove one duty. The audit line keeps the story, the same way history does."""
    require_manage(session, user)
    _require_open(employee)

    row = repository.duty(session, employee_id=employee.id, duty_id=duty_id)
    if row is None:
        # `404`, not `403`: the id may belong to a colleague, and the API must not
        # confirm that it exists.
        raise HTTPException(status_code=404, detail="Duty not found")

    summary = _duty_summary(row)
    session.delete(row)
    session.commit()

    record_audit(
        session,
        employee_id=employee.id,
        section="duty",
        action="deleted",
        row_id=duty_id,
        summary=f"Removed {summary}",
        user=user,
    )


# --- one person's week -----------------------------------------------------

#: The column a duty with no day and no date sits in. It is not a weekday, and
#: the grid draws it after the week rather than pretending it has a slot.
STANDING = "standing"


def _slot_day(day: str) -> str:
    """`monday` -> `Monday`; the standing column keeps its own word."""
    if day == STANDING:
        return "Standing"
    return labels.day_label(day) or day


def _duty_day(row: StaffDuty) -> str:
    """Which column of the grid a duty belongs in.

    A weekly duty names its day; a dated duty belongs in that date's weekday; a
    duty with neither is standing and goes in the column after the week.
    """
    if row.day_of_week:
        return row.day_of_week
    if row.on_date:
        return labels.WEEK_DAYS[row.on_date.weekday()]
    return STANDING


def _slot_order(slot: WeekSlotRead) -> tuple:
    """Start time, then periods before duties, then the label - chronology first."""
    return (slot.start or time.max, slot.kind != "period", slot.subject)


def staff_week(session: Session, employee_id: UUID, user: User | None) -> StaffWeekRead:
    """One person's week: their timetable periods and their duties, day by day.

    Two statements (periods, duties) plus the class labels and the person's name,
    and the answer lists **every day of the week**, empty ones included: "nothing
    on Wednesday" is a fact the principal is looking for, and a grid that silently
    drops the day makes it invisible.

    `404` for somebody this caller may not see, exactly like the directory row - a
    teacher reads their own week and nobody else's.
    """
    employee = require_employee(session, employee_id, user)
    name = profile_repository.employee_names(session, [employee.id]).get(
        employee.id, ""
    )

    periods = repository.week_periods(session, employee.id)
    room_labels = labels_by_section(
        session, list({period.classroom_id for period, _ in periods})
    )

    by_day: dict[str, list[WeekSlotRead]] = {}
    for period, subject_name in periods:
        day = getattr(period.day_of_week, "value", period.day_of_week)
        by_day.setdefault(day, []).append(
            WeekSlotRead(
                kind="period",
                day=day,
                day_label=_slot_day(day),
                start=period.start_time,
                end=period.end_time,
                slot=labels.period_label(period.start_time, period.end_time),
                subject=subject_name,
                class_label=room_labels.get(period.classroom_id),
                room=period.room,
                period_id=period.id,
            )
        )

    duty_hours = 0.0
    for row in repository.duties(session, employee.id):
        day = _duty_day(row)
        duty_hours += labels.hours_between(row.start_time, row.end_time)
        by_day.setdefault(day, []).append(
            WeekSlotRead(
                kind="duty",
                day=day,
                day_label=_slot_day(day),
                start=row.start_time,
                end=row.end_time,
                slot=(
                    labels.period_label(row.start_time, row.end_time)
                    if row.start_time and row.end_time
                    else ""
                ),
                subject=labels.DUTY_TYPE_LABELS.get(row.duty_type, row.duty_type),
                title=row.title,
                duty_id=row.id,
            )
        )

    days: list[WeekDayRead] = []
    periods_total = duties_total = empty_days = 0
    for day in (*labels.WEEK_DAYS, STANDING):
        slots = sorted(by_day.get(day, []), key=_slot_order)
        if not slots and day == STANDING:
            # The standing column exists only when something stands in it.
            continue
        taught = sum(1 for slot in slots if slot.kind == "period")
        on_duty = len(slots) - taught
        periods_total += taught
        duties_total += on_duty
        if not slots:
            empty_days += 1
        days.append(
            WeekDayRead(
                day=day,
                day_label=_slot_day(day),
                slots=slots,
                periods=taught,
                duties=on_duty,
            )
        )

    return StaffWeekRead(
        id=employee.id,
        name=name,
        department=employee.department or "",
        days=days,
        periods=periods_total,
        duties=duties_total,
        duty_hours=round(duty_hours, 2),
        empty_days=empty_days,
    )


# --- analytics -------------------------------------------------------------


def analytics(session: Session) -> WorkloadAnalytics:
    """The tiles above the matrix, counted over the rows the matrix shows.

    Built from `teachers.service.workload_matrix` rather than a second set of
    `COUNT`s: the average on the tile and the numbers in the table below it must
    come from one definition of "a teacher's load", and the matrix already includes
    the class teachers who teach no subject.

    Utilisation is averaged as `total periods / (capacity x staff)` - one division
    over the whole roll, not the mean of the percentages. Averaging percentages
    weights a teacher with 2 periods the same as one with 30, and the tile would
    then disagree with the total printed beside it.
    """
    rows = teachers_service.workload_matrix(session)
    capacity, source, week_slots = repository.capacity(session)
    rule = repository.rule(session)

    staff = len(rows)
    total_periods = sum(row.periods for row in rows)

    departments = repository.departments(session, [row.id for row in rows])
    grouped: dict[str, list] = {}
    for row in rows:
        # A blank department is grouped under "Unassigned" so the split still adds
        # up to the roll - hiding the row would make the column a lie.
        key = (departments.get(row.id) or "").strip() or "Unassigned"
        grouped.setdefault(key, []).append(row)

    by_department = [
        DepartmentLoad(
            department=department,
            staff=len(members),
            periods=sum(member.periods for member in members),
            utilisation=labels.utilisation(
                sum(member.periods for member in members), capacity * len(members)
            ),
            overloaded=sum(1 for member in members if member.overloaded),
        )
        # Ascending by department, the same order the directory's filter offers.
        for department, members in sorted(grouped.items())
    ]

    return WorkloadAnalytics(
        capacity=capacity,
        capacity_source=source,
        week_slots=week_slots,
        weekly_periods_rule=rule.weekly_periods if rule is not None else None,
        staff=staff,
        total_periods=total_periods,
        average_periods=round(total_periods / staff, 1) if staff else 0.0,
        average_utilisation=(
            labels.utilisation(total_periods, capacity * staff) if staff else 0
        ),
        overloaded=sum(1 for row in rows if row.overloaded),
        unassigned=sum(1 for row in rows if row.periods == 0),
        duties=sum(row.duties for row in rows),
        by_department=by_department,
    )
