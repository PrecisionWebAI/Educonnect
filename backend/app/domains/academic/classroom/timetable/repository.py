from uuid import UUID
from sqlmodel import Session, select

from .models import TimetablePeriod
from .schemas import TimetablePeriodCreate


def create_period(
    session: Session, period_in: TimetablePeriodCreate
) -> TimetablePeriod:
    db_period = TimetablePeriod.model_validate(period_in)
    session.add(db_period)
    session.commit()
    session.refresh(db_period)
    return db_period


def get_timetable_by_class(
    session: Session, class_id: UUID, section_id: UUID | None = None
) -> list[TimetablePeriod]:
    """A class's week, or one section's when `section_id` is named.

    A period names only its section; the class is matched through
    `section.class_id`, so "the whole class" means every section in it.
    """
    from app.domains.academic.classroom.academics.models import Classroom, Section

    query = (
        select(TimetablePeriod)
        .join(Classroom, Classroom.id == TimetablePeriod.classroom_id)
        .where(Classroom.class_id == class_id)
    )
    if section_id:
        query = query.where(TimetablePeriod.classroom_id == section_id)
    return list(
        session.exec(
            query.order_by(TimetablePeriod.day_of_week, TimetablePeriod.start_time)
        ).all()
    )


def get_timetable_by_teacher(
    session: Session, teacher_id: UUID
) -> list[TimetablePeriod]:
    statement = (
        select(TimetablePeriod)
        .where(TimetablePeriod.teacher_id == teacher_id)
        .order_by(TimetablePeriod.day_of_week, TimetablePeriod.start_time)
    )
    return list(session.exec(statement).all())


def get_all_periods(session: Session) -> list[TimetablePeriod]:
    return list(
        session.exec(
            select(TimetablePeriod).order_by(
                TimetablePeriod.day_of_week, TimetablePeriod.start_time
            )
        ).all()
    )


def get_period(session: Session, period_id: UUID) -> TimetablePeriod | None:
    """One period, for the edit/clear actions."""
    return session.get(TimetablePeriod, period_id)


def update_period(
    session: Session, period: TimetablePeriod, period_in: TimetablePeriodCreate
) -> TimetablePeriod:
    """Replace a period's fields.

    The grid always sends the whole slot (subject, teacher, day, times, room), so
    a plain field-by-field copy is the honest update - no partial-merge guessing.
    """
    for field, value in period_in.model_dump().items():
        setattr(period, field, value)
    session.add(period)
    session.commit()
    session.refresh(period)
    return period


def delete_period(session: Session, period: TimetablePeriod) -> None:
    """Clear a slot: the period is gone from the week."""
    session.delete(period)
    session.commit()
