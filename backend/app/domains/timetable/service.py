from uuid import UUID

from fastapi import HTTPException
from sqlmodel import Session

from . import repository
from .models import TimetablePeriod
from .schemas import TimetablePeriodCreate


def create_period(
    session: Session, period_in: TimetablePeriodCreate
) -> TimetablePeriod:
    # We could add conflict detection here (e.g. is teacher already booked at this time?)
    return repository.create_period(session, period_in)


def update_period(
    session: Session, period_id: UUID, period_in: TimetablePeriodCreate
) -> TimetablePeriod:
    """Move a period to another slot / subject / teacher / room."""
    period = repository.get_period(session, period_id)
    if period is None:
        raise HTTPException(status_code=404, detail="Timetable period not found")
    return repository.update_period(session, period, period_in)


def delete_period(session: Session, period_id: UUID) -> None:
    """Clear a slot from the week."""
    period = repository.get_period(session, period_id)
    if period is None:
        raise HTTPException(status_code=404, detail="Timetable period not found")
    repository.delete_period(session, period)


def get_timetable_by_class(
    session: Session, class_id: UUID, section_id: UUID | None = None
) -> list[TimetablePeriod]:
    return repository.get_timetable_by_class(session, class_id, section_id)


def get_timetable_by_teacher(
    session: Session, teacher_id: UUID
) -> list[TimetablePeriod]:
    return repository.get_timetable_by_teacher(session, teacher_id)


def list_slots(session: Session) -> list["TimetableSlotRead"]:
    """The weekly grid, built from real `timetableperiod` rows."""
    from app.domains.academics.models import Classroom, Section, Subject
    from app.domains.staff.models import Employee
    from app.domains.users.models import User

    from .schemas import TimetableSlotRead

    slots: list[TimetableSlotRead] = []
    for period in repository.get_all_periods(session):
        section = session.get(Section, period.section_id) if period.section_id else None
        classroom = session.get(Classroom, section.classroom_id) if section else None
        subject = session.get(Subject, period.subject_id) if period.subject_id else None
        teacher_name = ""
        if period.teacher_id:
            profile = session.get(Employee, period.teacher_id)
            if profile and profile.user_id:
                user = session.get(User, profile.user_id)
                teacher_name = user.full_name if user else ""
        class_name = classroom.name if classroom else ""
        if section:
            class_name = f"{class_name}-{section.name}"
        slots.append(
            TimetableSlotRead(
                day=period.day_of_week.value.capitalize(),
                period=f"{period.start_time.strftime('%H:%M')}-{period.end_time.strftime('%H:%M')}",
                className=class_name,
                subject=subject.name if subject else "",
                teacher=teacher_name,
            )
        )
    return slots
