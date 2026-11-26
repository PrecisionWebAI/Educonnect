"""One person's week: their timetable periods and their duties, day by day.

This is what the teacher's own "My week" panel reads (`GET /teachers/me/week`). The
Workload tab that used to sit beside it - the capacity rule, the duties' editor and the
analytics - has been removed; only the read the teacher's own screen still needs stays.

Out of scope is `404`, never `403`: the API must not confirm that a colleague's id exists.
"""

from datetime import time
from uuid import UUID

from sqlmodel import Session

from app.domains.academic.classroom.labels import labels_by_section
from app.domains.admin.users.models import User

from .. import labels
from ..profile import repository as profile_repository
from ..profile.service import require_employee
from . import repository
from .models import StaffDuty
from .schemas import StaffWeekRead, WeekDayRead, WeekSlotRead


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
