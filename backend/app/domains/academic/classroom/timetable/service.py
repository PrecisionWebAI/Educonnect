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

from app.domains.admin.settings import values as setting_values
from app.domains.admin.settings.academic_year_context import current_academic_year_id

from . import repository
from .models import BellSchedule, TimetablePeriod
from .schemas import (
    BellScheduleWrite,
    ExtraClassesWrite,
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


def _subject_name(session: Session, classroom_subject_id: UUID | None) -> str:
    from app.domains.academic.classroom.course.models import ClassroomSubject

    subject = (
        session.get(ClassroomSubject, classroom_subject_id)
        if classroom_subject_id
        else None
    )
    return subject.name if subject is not None else "a subject"


def _require_section(session: Session, section_id: UUID) -> None:
    from app.domains.academic.classroom.academics.models import Classroom

    if session.get(Classroom, section_id) is None:
        raise HTTPException(status_code=404, detail="Class section not found")


def _require_course(session: Session, section_id: UUID, course_id: UUID) -> None:
    from app.domains.academic.classroom.course.subjects import require_section_subject

    require_section_subject(session, section_id, course_id)


def _refuse_clash(
    session: Session,
    period_in: TimetablePeriodCreate,
    academic_year_id: UUID | None,
    *,
    ignore_id: UUID | None = None,
) -> None:
    """Refuse the save **with the name of whoever is already there**."""
    other = repository.clash(
        session,
        teacher_id=period_in.teacher_id,
        classroom_id=period_in.section_id,
        day_of_week=period_in.day_of_week,
        start_time=period_in.start_time,
        academic_year_id=academic_year_id,
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
            f"{_subject_name(session, other.classroom_subject_id)} at {hour} on {day}."
        )
    raise HTTPException(status_code=409, detail=detail)


def _period_read(row: TimetablePeriod) -> TimetablePeriodRead:
    """The API's word for a period: `section_id`, not the column's `classroom_id`."""
    return TimetablePeriodRead(
        id=row.id,
        section_id=row.classroom_id,
        academic_year_id=row.academic_year_id,
        classroom_subject_id=row.classroom_subject_id,
        teacher_id=row.teacher_id,
        day_of_week=row.day_of_week,
        start_time=row.start_time,
        end_time=row.end_time,
        room=row.room,
    )


def create_period(
    session: Session, period_in: TimetablePeriodCreate
) -> TimetablePeriodRead:
    """Add a period to a class-section's week for the current academic year."""
    year_id = current_academic_year_id(session)
    _require_section(session, period_in.section_id)
    _require_course(session, period_in.section_id, period_in.classroom_subject_id)
    _refuse_clash(session, period_in, year_id)
    try:
        return _period_read(repository.create_period(session, period_in, year_id))
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
    year_id = current_academic_year_id(session)
    if (
        year_id is not None
        and period.academic_year_id is not None
        and period.academic_year_id != year_id
    ):
        raise HTTPException(
            status_code=409,
            detail="A past academic year's timetable is read-only.",
        )
    _require_section(session, period_in.section_id)
    _require_course(session, period_in.section_id, period_in.classroom_subject_id)
    _refuse_clash(session, period_in, year_id, ignore_id=period.id)
    try:
        return _period_read(
            repository.update_period(session, period, period_in, year_id)
        )
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
    year_id = current_academic_year_id(session)
    if (
        year_id is not None
        and period.academic_year_id is not None
        and period.academic_year_id != year_id
    ):
        raise HTTPException(
            status_code=409,
            detail="A past academic year's timetable is read-only.",
        )
    repository.delete_period(session, period)


def get_timetable_by_class(
    session: Session,
    class_id: UUID,
    section_id: UUID | None = None,
    academic_year_id: UUID | None = None,
) -> list[TimetablePeriodRead]:
    year_id = academic_year_id or current_academic_year_id(session)
    return [
        _period_read(row)
        for row in repository.get_timetable_by_class(
            session, class_id, section_id, year_id
        )
    ]


def get_timetable_by_teacher(
    session: Session,
    teacher_id: UUID,
    academic_year_id: UUID | None = None,
) -> list[TimetablePeriodRead]:
    year_id = academic_year_id or current_academic_year_id(session)
    return [
        _period_read(row)
        for row in repository.get_timetable_by_teacher(session, teacher_id, year_id)
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

    return _slots_read(rows) + extra_slots(session)


def _layout(
    count: int, breaks: list, start: time, minutes: int, first_no: int = 1
) -> list[dict]:
    """Back-to-back rows: `count` lessons of `minutes`, a break after the listed ones."""
    seen: set[int] = set()
    for brk in breaks:
        if brk.after_period > count:
            raise HTTPException(
                status_code=422,
                detail=f"A break cannot follow period {brk.after_period}: there "
                f"are only {count}.",
            )
        if brk.after_period in seen:
            raise HTTPException(
                status_code=422,
                detail=f"Two breaks are set after period {brk.after_period}.",
            )
        seen.add(brk.after_period)
    by_period = {brk.after_period: brk.minutes for brk in breaks}

    cursor = start.hour * 60 + start.minute
    slots: list[dict] = []

    def add(is_break: bool, length: int) -> None:
        end = cursor + length
        if end > 24 * 60 - 1:
            raise HTTPException(
                status_code=422, detail="The day runs past midnight - shorten it."
            )
        slots.append(
            {
                "period_no": first_no + len(slots),
                "start_time": time(cursor // 60, cursor % 60),
                "end_time": time(end // 60, end % 60),
                "is_break": is_break,
            }
        )

    for lesson in range(1, count + 1):
        add(False, minutes)
        cursor += minutes
        if lesson in by_period:
            add(True, by_period[lesson])
            cursor += by_period[lesson]
    return slots


#: Extra classes (E1, E2 ...) are a second, optional day-part kept in school settings:
#: their rows are laid out from this config on every read.
EXTRA_KEY = "timetable.extra_classes"
EXTRA_FIRST_NO = 100


def _extra_config(session: Session) -> ExtraClassesWrite | None:
    raw = setting_values.get_value(session, EXTRA_KEY, None)
    if not raw:
        return None
    try:
        config = ExtraClassesWrite.model_validate_json(raw)
    except ValueError:
        return None
    return config if config.count > 0 else None


def extra_slots(session: Session) -> list[BellSlotRead]:
    config = _extra_config(session)
    if config is None:
        return []
    rows = _layout(
        config.count,
        config.breaks,
        config.start_time,
        config.period_minutes,
        EXTRA_FIRST_NO,
    )
    return _slots_read([BellSchedule(**row) for row in rows], prefix="E", extra=True)


def set_bell_schedule(session: Session, payload: BellScheduleWrite) -> list[BellSlotRead]:
    """Lay the day out from "N periods, breaks after these periods".

    Rows are written back to back from `start_time`: each lesson runs
    `period_minutes`, each break its own `minutes`. The day is global: periods
    already placed in any class move to the matching new lesson time.
    `payload.extra` (when sent) sets the extra classes E1, E2 ... the same way.
    """
    slots = _layout(
        payload.periods, payload.breaks, payload.start_time, payload.period_minutes
    )
    if payload.extra is not None:
        extra = payload.extra
        if extra.count > 0:
            rows = _layout(
                extra.count,
                extra.breaks,
                extra.start_time,
                extra.period_minutes,
                EXTRA_FIRST_NO,
            )
            if extra.position == "after" and rows[0]["start_time"] < slots[-1]["end_time"]:
                raise HTTPException(
                    status_code=422,
                    detail="Extra classes after the day must start once the last "
                    f"regular period ends ({slots[-1]['end_time']:%H:%M}).",
                )
            if extra.position == "before" and rows[-1]["end_time"] > slots[0]["start_time"]:
                raise HTTPException(
                    status_code=422,
                    detail="Extra classes before the day must end by the first "
                    f"regular period ({slots[0]['start_time']:%H:%M}).",
                )
    try:
        rows = repository.replace_bell_slots(session, slots, force=payload.force)
    except repository.PeriodsWouldBeLost as lost:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"{lost.count} placed period(s) fall after the new last period "
            "and would be removed from the classes' timetables.",
        )
    if payload.extra is not None:
        setting_values.set_value(session, EXTRA_KEY, payload.extra.model_dump_json())
    return _slots_read(rows) + extra_slots(session)


def _slots_read(
    rows: list[BellSchedule], prefix: str = "P", extra: bool = False
) -> list[BellSlotRead]:
    slots: list[BellSlotRead] = []
    lesson = 0
    for row in rows:
        if not row.is_break:
            lesson += 1
        slots.append(
            BellSlotRead(
                period_no=row.period_no,
                label="Break" if row.is_break else f"{prefix}{lesson}",
                start_time=row.start_time,
                end_time=row.end_time,
                is_break=row.is_break,
                extra=extra,
            )
        )
    return slots


def list_slots(
    session: Session, academic_year_id: UUID | None = None
) -> list[TimetableSlotRead]:
    """The weekly grid, built from real `timetableperiod` rows."""
    from app.domains.academic.classroom.course.models import ClassroomSubject

    slots: list[TimetableSlotRead] = []
    year_id = academic_year_id or current_academic_year_id(session)
    for period in repository.get_all_periods(session, year_id):
        subject = (
            session.get(ClassroomSubject, period.classroom_subject_id)
            if period.classroom_subject_id
            else None
        )
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
                teacherId=period.teacher_id,
                sectionId=period.classroom_id,
            )
        )
    return slots
