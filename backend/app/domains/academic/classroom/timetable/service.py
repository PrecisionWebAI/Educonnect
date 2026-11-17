"""The week: one slot at a time, and the school's day shape.

Two rules are enforced here, and both were only words in a docstring before Phase 9:

* a teacher cannot be in two rooms at the same hour;
* a class-section cannot hold two subjects in the same slot.

`repository.clash` finds the row that would break either rule, this module turns that
into a `409` **naming the teacher or the class**, and the unique keys behind it are the
backstop for two clerks saving at once. A clash is never a `500`.
"""

from datetime import time
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from . import repository
from .models import BellSchedule, TimetablePeriod
from .schemas import (
    BellSlotRead,
    TimetablePeriodCreate,
    TimetablePeriodRead,
    TimetableSlotRead,
)

#: A sensible six-period day with the usual breaks, written once for a school that has
#: never set one. It is a **default, not a rule**: the rows are editable rows in
#: `bellschedule`, and the grid draws whatever is there.
DEFAULT_DAY: list[dict] = [
    {
        "period_no": 1,
        "start_time": time(8, 0),
        "end_time": time(8, 45),
        "is_break": False,
    },
    {
        "period_no": 2,
        "start_time": time(8, 45),
        "end_time": time(9, 30),
        "is_break": False,
    },
    {
        "period_no": 3,
        "start_time": time(9, 30),
        "end_time": time(9, 50),
        "is_break": True,
    },
    {
        "period_no": 4,
        "start_time": time(9, 50),
        "end_time": time(10, 35),
        "is_break": False,
    },
    {
        "period_no": 5,
        "start_time": time(10, 35),
        "end_time": time(11, 20),
        "is_break": False,
    },
    {
        "period_no": 6,
        "start_time": time(11, 20),
        "end_time": time(11, 40),
        "is_break": True,
    },
    {
        "period_no": 7,
        "start_time": time(11, 40),
        "end_time": time(12, 25),
        "is_break": False,
    },
    {
        "period_no": 8,
        "start_time": time(12, 25),
        "end_time": time(13, 10),
        "is_break": False,
    },
]


def _section_label(session: Session, room_id: UUID | None) -> str:
    """`"Class 9-A"` for a class-section id."""
    from app.domains.academic.classroom.academics.models import (
        ClassName,
        Classroom,
        Section,
    )

    if room_id is None:
        return "That class-section"
    room = session.get(Classroom, room_id)
    if room is None:
        return "That class-section"
    klass = session.get(ClassName, room.class_id)
    letter = session.get(Section, room.section_id)
    name = klass.classname if klass else "That class-section"
    return f"{name}-{letter.section_name}" if letter else name


def _teacher_name(session: Session, employee_id: UUID | None) -> str:
    from app.domains.admin.users.models import User
    from app.domains.people.staff.models import Employee

    if employee_id is None:
        return "That teacher"
    profile = session.get(Employee, employee_id)
    if profile is None:
        return "That teacher"
    user = session.get(User, profile.user_id) if profile.user_id else None
    return user.full_name if user is not None else "That teacher"


def _subject_name(session: Session, subject_id: UUID | None) -> str:
    from app.domains.academic.classroom.academics.models import Subject

    subject = session.get(Subject, subject_id) if subject_id else None
    return subject.name if subject is not None else "a subject"


def _require_section(session: Session, section_id: UUID) -> None:
    from app.domains.academic.classroom.academics.models import Classroom

    if session.get(Classroom, section_id) is None:
        raise HTTPException(status_code=404, detail="Class section not found")


def _refuse_clash(
    session: Session, period_in: TimetablePeriodCreate, *, ignore_id: UUID | None = None
) -> None:
    """Refuse the save **with the name of whoever is already there**."""
    other = repository.clash(
        session,
        teacher_id=period_in.teacher_id,
        classroom_id=period_in.section_id,
        day_of_week=period_in.day_of_week,
        start_time=period_in.start_time,
        ignore_id=ignore_id,
    )
    if other is None:
        return
    hour = period_in.start_time.strftime("%H:%M")
    day = period_in.day_of_week.value.capitalize()
    if other.teacher_id == period_in.teacher_id:
        detail = (
            f"{_teacher_name(session, period_in.teacher_id)} is already booked at "
            f"{hour} on {day} ({_section_label(session, other.classroom_id)})."
        )
    else:
        detail = (
            f"{_section_label(session, period_in.section_id)} already has "
            f"{_subject_name(session, other.subject_id)} at {hour} on {day}."
        )
    raise HTTPException(status_code=409, detail=detail)


def _period_read(row: TimetablePeriod) -> TimetablePeriodRead:
    """The API's word for a period: `section_id`, not the column's `classroom_id`."""
    return TimetablePeriodRead(
        id=row.id,
        section_id=row.classroom_id,
        subject_id=row.subject_id,
        teacher_id=row.teacher_id,
        day_of_week=row.day_of_week,
        start_time=row.start_time,
        end_time=row.end_time,
        room=row.room,
    )


def create_period(
    session: Session, period_in: TimetablePeriodCreate
) -> TimetablePeriodRead:
    """Add a period to a class-section's week."""
    _require_section(session, period_in.section_id)
    _refuse_clash(session, period_in)
    try:
        return _period_read(repository.create_period(session, period_in))
    except IntegrityError:
        # Two clerks saved the same slot at the same moment; the key won, say so.
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail="That slot was just taken - reload the week and try again.",
        ) from None


def update_period(
    session: Session, period_id: UUID, period_in: TimetablePeriodCreate
) -> TimetablePeriodRead:
    """Move a period to another slot / subject / teacher / room."""
    period = repository.get_period(session, period_id)
    if period is None:
        raise HTTPException(status_code=404, detail="Timetable period not found")
    _require_section(session, period_in.section_id)
    _refuse_clash(session, period_in, ignore_id=period.id)
    try:
        return _period_read(repository.update_period(session, period, period_in))
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail="That slot was just taken - reload the week and try again.",
        ) from None


def delete_period(session: Session, period_id: UUID) -> None:
    """Clear a slot from the week."""
    period = repository.get_period(session, period_id)
    if period is None:
        raise HTTPException(status_code=404, detail="Timetable period not found")
    repository.delete_period(session, period)


def get_timetable_by_class(
    session: Session, class_id: UUID, section_id: UUID | None = None
) -> list[TimetablePeriodRead]:
    return [
        _period_read(row)
        for row in repository.get_timetable_by_class(session, class_id, section_id)
    ]


def get_timetable_by_teacher(
    session: Session, teacher_id: UUID
) -> list[TimetablePeriodRead]:
    return [
        _period_read(row)
        for row in repository.get_timetable_by_teacher(session, teacher_id)
    ]


def _label(index: int, is_break: bool) -> str:
    return "Break" if is_break else f"P{index}"


def bell_schedule(session: Session) -> list[BellSlotRead]:
    """The school's day: its own rows, or the six-period default written once.

    Seeding happens on the **first read** rather than in the migration, because a new
    school created after the migration needs a day shape too. The unique key on
    `(school_id, period_no)` means two concurrent first reads cannot both write it.
    """
    rows: list[BellSchedule] = repository.bell_slots(session)
    if not rows:
        try:
            rows = repository.add_bell_slots(session, DEFAULT_DAY)
        except IntegrityError:
            session.rollback()
            rows = repository.bell_slots(session)

    slots: list[BellSlotRead] = []
    lesson = 0
    for row in rows:
        if not row.is_break:
            lesson += 1
        slots.append(
            BellSlotRead(
                period_no=row.period_no,
                label=_label(lesson, row.is_break),
                start_time=row.start_time,
                end_time=row.end_time,
                is_break=row.is_break,
            )
        )
    return slots


def list_slots(session: Session) -> list[TimetableSlotRead]:
    """The weekly grid, built from real `timetableperiod` rows."""
    from app.domains.academic.classroom.academics.models import Subject

    slots: list[TimetableSlotRead] = []
    for period in repository.get_all_periods(session):
        subject = session.get(Subject, period.subject_id) if period.subject_id else None
        slots.append(
            TimetableSlotRead(
                day=period.day_of_week.value.capitalize(),
                period=(
                    f"{period.start_time.strftime('%H:%M')}-"
                    f"{period.end_time.strftime('%H:%M')}"
                ),
                className=_section_label(session, period.classroom_id),
                subject=subject.name if subject else "",
                teacher=_teacher_name(session, period.teacher_id),
            )
        )
    return slots
