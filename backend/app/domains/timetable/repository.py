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
    session: Session, class_id: int, section_id: int | None = None
) -> list[TimetablePeriod]:
    query = select(TimetablePeriod).where(TimetablePeriod.grade_class_id == class_id)
    if section_id:
        query = query.where(
            (TimetablePeriod.section_id == section_id)
            | (TimetablePeriod.section_id == None)
        )
    # Order by day and time
    return list(
        session.exec(
            query.order_by(TimetablePeriod.day_of_week, TimetablePeriod.start_time)
        ).all()
    )


def get_timetable_by_teacher(
    session: Session, teacher_id: int
) -> list[TimetablePeriod]:
    statement = (
        select(TimetablePeriod)
        .where(TimetablePeriod.teacher_id == teacher_id)
        .order_by(TimetablePeriod.day_of_week, TimetablePeriod.start_time)
    )
    return list(session.exec(statement).all())
