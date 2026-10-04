"""Database access for the hiring pipeline. All queries live here."""

from sqlmodel import Session, func, select

from .models import HiringCandidate, StaffVacancy


def get_candidates(session: Session) -> list[HiringCandidate]:
    """Newest first, so a just-added candidate lands on top of the table."""
    return list(
        session.exec(select(HiringCandidate).order_by(HiringCandidate.id.desc())).all()
    )


def get_candidate_number_values(session: Session, prefix: str) -> list[str]:
    """Every candidate number already handed out for `prefix` (e.g. `CAN-2026-`)."""
    return list(
        session.exec(
            select(HiringCandidate.candidate_no).where(
                HiringCandidate.candidate_no.startswith(prefix)
            )
        ).all()
    )


def get_emp_ids(session: Session) -> list[str]:
    """Every employee id already handed out."""
    return list(
        session.exec(
            select(HiringCandidate.emp_id).where(HiringCandidate.emp_id.is_not(None))
        ).all()
    )


def get_candidate_by_id(session: Session, candidate_id: int) -> HiringCandidate | None:
    return session.get(HiringCandidate, candidate_id)


def create_candidate(session: Session, candidate: HiringCandidate) -> HiringCandidate:
    session.add(candidate)
    session.commit()
    session.refresh(candidate)
    return candidate


def save_candidate(session: Session, candidate: HiringCandidate) -> HiringCandidate:
    session.add(candidate)
    session.commit()
    session.refresh(candidate)
    return candidate


def get_vacancies(session: Session) -> list[StaffVacancy]:
    return list(session.exec(select(StaffVacancy).order_by(StaffVacancy.role)).all())


def count_by_status(session: Session) -> dict[str, int]:
    """{status: candidate count} - one query, used by the stat tiles."""
    rows = session.exec(
        select(HiringCandidate.status, func.count()).group_by(HiringCandidate.status)
    ).all()
    return {status: int(count) for status, count in rows}


def open_seats(session: Session) -> int:
    """Seats on vacancies that are still Open."""
    total = session.exec(
        select(func.sum(StaffVacancy.openings)).where(StaffVacancy.status == "Open")
    ).one()
    return int(total or 0)
