"""Staff hiring service.

The real logic here is the two identifiers the pipeline hands out:

* `candidate_no` (`CAN-2026-0036`) - minted server-side.
* `emp_id` (`EMP-0037`) - stamped the moment a candidate becomes **Hired**,
  because that is the id the salary register and the staff directory use.
  The next number is always `max(existing) + 1`, so two people hiring from two
  browsers cannot end up sharing an employee id.
"""

from datetime import date

from fastapi import HTTPException
from sqlmodel import Session

from . import repository
from .models import (
    FIRST_EMP_NUMBER,
    HIRING_STATUSES,
    STATUS_HIRED,
    STATUS_RESUME,
    HiringCandidate,
)
from .schemas import (
    HiringCandidateCreate,
    HiringCandidateRead,
    HiringStatusUpdate,
    HiringSummary,
    StaffVacancyRead,
)


def _read(candidate: HiringCandidate) -> HiringCandidateRead:
    return HiringCandidateRead.model_validate(candidate.model_dump())


def _get_or_404(session: Session, candidate_id: int) -> HiringCandidate:
    candidate = repository.get_candidate_by_id(session, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate


def _tail_number(value: str | None) -> int | None:
    """`EMP-0037` / `CAN-2026-0031` -> 37 / 31."""
    if not value:
        return None
    tail = value.rsplit("-", 1)[-1]
    return int(tail) if tail.isdigit() else None


def _next_candidate_no(session: Session) -> str:
    prefix = f"CAN-{date.today().year}-"
    numbers = [
        number
        for number in (
            _tail_number(value)
            for value in repository.get_candidate_number_values(session, prefix)
        )
        if number is not None
    ]
    # 30 keeps the demo school's numbering (CAN-2026-0031 was its first applicant).
    return f"{prefix}{max(numbers, default=30) + 1:04d}"


def _next_emp_id(session: Session) -> str:
    numbers = [
        number
        for number in (_tail_number(value) for value in repository.get_emp_ids(session))
        if number is not None
    ]
    return f"EMP-{max(numbers, default=FIRST_EMP_NUMBER - 1) + 1:04d}"


def list_candidates(session: Session) -> list[HiringCandidateRead]:
    return [_read(candidate) for candidate in repository.get_candidates(session)]


def create_candidate(
    session: Session, candidate_in: HiringCandidateCreate
) -> HiringCandidateRead:
    candidate = HiringCandidate(
        **candidate_in.model_dump(exclude={"applied_on"}),
        applied_on=candidate_in.applied_on or date.today(),
        candidate_no=_next_candidate_no(session),
        emp_id=None,
        status=STATUS_RESUME,
    )
    return _read(repository.create_candidate(session, candidate))


def update_status(
    session: Session, candidate_id: int, status_in: HiringStatusUpdate
) -> HiringCandidateRead:
    if status_in.status not in HIRING_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown hiring status '{status_in.status}'. "
            f"Expected one of: {', '.join(HIRING_STATUSES)}",
        )

    candidate = _get_or_404(session, candidate_id)
    if status_in.interview_on:
        candidate.interview_on = status_in.interview_on
    if status_in.status == STATUS_HIRED and not candidate.emp_id:
        candidate.emp_id = _next_emp_id(session)
    candidate.status = status_in.status
    return _read(repository.save_candidate(session, candidate))


def list_vacancies(session: Session) -> list[StaffVacancyRead]:
    return [
        StaffVacancyRead.model_validate(vacancy.model_dump())
        for vacancy in repository.get_vacancies(session)
    ]


def summary(session: Session) -> HiringSummary:
    """Stat-tile figures, aggregated in one pass over the pipeline."""
    counts = repository.count_by_status(session)
    hired = counts.get(STATUS_HIRED, 0)
    return HiringSummary(
        total=sum(counts.values()),
        shortlisted=counts.get("Shortlisted", 0),
        interviews=counts.get("Interview", 0),
        hired=hired,
        open_vacancies=max(repository.open_seats(session) - hired, 0),
    )
