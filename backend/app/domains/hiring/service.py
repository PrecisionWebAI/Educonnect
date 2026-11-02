"""Staff hiring service.

The real logic here is the two identifiers the pipeline hands out:

* `candidate_no` (`CAN-2026-0036`) - minted server-side.
* `emp_id` (`EMP-0037`) - stamped the moment a candidate becomes **Hired**,
  because that is the id the salary register and the staff directory use.
  The next number is always `max(existing) + 1`, so two people hiring from two
  browsers cannot end up sharing an employee id.
"""

from datetime import date, datetime
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlmodel import Session

from app.core.config import settings

from . import repository
from .models import (
    FIRST_EMP_NUMBER,
    HIRING_STATUSES,
    STATUS_HIRED,
    STATUS_INTERVIEW,
    STATUS_RESUME,
    HiringCandidate,
)
from .schemas import (
    HiringCandidateCreate,
    HiringCandidateRead,
    HiringStatusUpdate,
    HiringSummary,
    InterviewScheduleUpdate,
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
    """Registers a person for an interview (the "+ Interview" form).

    Scheduling an interview moves the candidate straight to the "Interview"
    stage; without a date+time they simply enter at "Resume".
    """
    interview_at = candidate_in.interview_at
    payload = candidate_in.model_dump(
        exclude={"applied_on", "interview_on", "interview_at"}
    )
    candidate = HiringCandidate(
        **payload,
        applied_on=candidate_in.applied_on or date.today(),
        interview_on=candidate_in.interview_on
        or (interview_at.date() if interview_at else None),
        candidate_no=_next_candidate_no(session),
        emp_id=None,
        status=STATUS_INTERVIEW if interview_at else STATUS_RESUME,
    )
    return _read(repository.create_candidate(session, candidate))


def schedule_interview(
    session: Session, candidate_id: int, schedule_in: InterviewScheduleUpdate
) -> HiringCandidateRead:
    """Set / change a candidate's interview date+time (and an optional note)."""
    candidate = _get_or_404(session, candidate_id)
    if schedule_in.interview_at is not None:
        candidate.interview_at = schedule_in.interview_at
        candidate.interview_on = schedule_in.interview_at.date()
        if candidate.status not in (STATUS_HIRED,):
            candidate.status = STATUS_INTERVIEW
    if schedule_in.interview_note is not None:
        candidate.interview_note = schedule_in.interview_note.strip() or None
    return _read(repository.save_candidate(session, candidate))


def save_resume(
    session: Session, candidate_id: int, file: UploadFile, school_id: int | None
) -> HiringCandidateRead:
    """Stores a candidate's resume on disk and records its path."""
    candidate = _get_or_404(session, candidate_id)
    if not file.filename:
        raise HTTPException(status_code=422, detail="Resume file is required.")

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png"}:
        raise HTTPException(
            status_code=422,
            detail="Resume must be a PDF, Word document or image.",
        )
    data = file.file.read()
    if len(data) > settings.UPLOAD_MAX_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"Resume exceeds the {settings.UPLOAD_MAX_MB} MB limit.",
        )

    root = Path(settings.UPLOAD_DIR) / "resumes" / str(school_id or 0)
    root.mkdir(parents=True, exist_ok=True)
    safe_name = f"{candidate.id}_{candidate.candidate_no or 'candidate'}{suffix}"
    destination = root / safe_name
    destination.write_bytes(data)

    candidate.resume_path = str(destination)
    return _read(repository.save_candidate(session, candidate))


def _hire_read(candidate: HiringCandidate) -> HiringCandidateHireRead:
    read = HiringCandidateHireRead.model_validate(candidate.model_dump())
    return read


def update_status(
    session: Session, candidate_id: int, status_in: HiringStatusUpdate
) -> HiringCandidateRead:
    if status_in.status not in HIRING_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown hiring status '{status_in.status}'. "
            f"Expected one of: {', '.join(HIRING_STATUSES)}",
        )
    if status_in.status == STATUS_HIRED:
        raise HTTPException(
            status_code=422,
            detail="Use the 'Hired' button to confirm a hire (type 'Hired').",
        )

    candidate = _get_or_404(session, candidate_id)
    if status_in.interview_on:
        candidate.interview_on = status_in.interview_on
    candidate.status = status_in.status
    return _read(repository.save_candidate(session, candidate))


def summary(session: Session) -> HiringSummary:
    """Stat-tile figures, aggregated in one pass over the pipeline."""
    counts = repository.count_by_status(session)
    hired = counts.get(STATUS_HIRED, 0)
    return HiringSummary(
        total=sum(counts.values()),
        shortlisted=counts.get("Shortlisted", 0),
        interviews=counts.get("Interview", 0),
        hired=hired,
    )
