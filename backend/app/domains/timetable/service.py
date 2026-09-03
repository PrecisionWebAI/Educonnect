from sqlmodel import Session

from . import repository
from .models import TimetablePeriod
from .schemas import TimetablePeriodCreate


def create_period(
    session: Session, period_in: TimetablePeriodCreate
) -> TimetablePeriod:
    # We could add conflict detection here (e.g. is teacher already booked at this time?)
    return repository.create_period(session, period_in)


def get_timetable_by_class(
    session: Session, class_id: int, section_id: int | None = None
) -> list[TimetablePeriod]:
    return repository.get_timetable_by_class(session, class_id, section_id)


def get_timetable_by_teacher(
    session: Session, teacher_id: int
) -> list[TimetablePeriod]:
    return repository.get_timetable_by_teacher(session, teacher_id)
