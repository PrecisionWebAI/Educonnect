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
from uuid import UUID
from fastapi import HTTPException, UploadFile
from sqlmodel import Session

from app.core import contacts
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


def get_candidate_or_404(session: Session, candidate_id: UUID) -> HiringCandidate:
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
    # 30 continues the numbering the existing applicants use (CAN-2026-0031 was
    # the first one ever created).
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


def _same_name(first: str | None, second: str | None) -> bool:
    """True when two spellings of a name are the same name (case/space aside).

    Used for one thing only: recognising the person themselves. A parent applying to
    teach fills the interview form with the number and address the school already has
    for them, and that is not somebody else - the same name is what says so.
    """
    return " ".join((first or "").lower().split()) == " ".join((second or "").lower().split())


def _guard_candidate_contact(session: Session, candidate_in: HiringCandidateCreate) -> str | None:
    """Check the interview form's contact against the one contact = one person rule.

    A candidate is somebody the school may hire later, so their number and address must
    be theirs: a contact that already belongs to a family, to a colleague, or to another
    candidate in the pipeline is refused (`409`), naming who holds it - the same number
    cannot describe two people. The exception is the person **themselves** (a parent who
    is now applying to teach keeps the contact they are already reachable on), which is
    recognised by name and returned as a note for the office.
    """
    phone = (candidate_in.phone or "").strip() or None
    email = (candidate_in.email or "").strip().lower() or None
    holder = contacts.find_contact(session, phone=phone, email=email)
    if holder is None:
        return None
    if _same_name(candidate_in.candidate_name, holder.name):
        return f"{holder.describe()} - already on file, the same person."
    raise HTTPException(
        status_code=409,
        detail=(
            f"{phone or email} already belongs to {holder.describe()}. "
            "Open their existing record instead of adding a second person."
        ),
    )


def create_candidate(
    session: Session, candidate_in: HiringCandidateCreate
) -> HiringCandidateRead:
    """Registers a person for an interview (the "+ Interview" form).

    Scheduling an interview moves the candidate straight to the "Interview"
    stage; without a date+time they simply enter at "Resume".
    """
    interview_at = candidate_in.interview_at
    payload = candidate_in.model_dump(
        exclude={"applied_on", "interview_on", "interview_at", "interview_note"}
    )
    note = _guard_candidate_contact(session, candidate_in)
    candidate = HiringCandidate(
        **payload,
        applied_on=candidate_in.applied_on or date.today(),
        interview_on=candidate_in.interview_on
        or (interview_at.date() if interview_at else None),
        candidate_no=_next_candidate_no(session),
        emp_id=None,
        interview_note=note or candidate_in.interview_note,
        status=STATUS_INTERVIEW if interview_at else STATUS_RESUME,
    )
    return _read(repository.create_candidate(session, candidate))


def schedule_interview(
    session: Session, candidate_id: UUID, schedule_in: InterviewScheduleUpdate
) -> HiringCandidateRead:
    """Set / change a candidate's interview date+time (and an optional note)."""
    candidate = get_candidate_or_404(session, candidate_id)
    if schedule_in.interview_at is not None:
        candidate.interview_at = schedule_in.interview_at
        candidate.interview_on = schedule_in.interview_at.date()
        if candidate.status not in (STATUS_HIRED,):
            candidate.status = STATUS_INTERVIEW
    if schedule_in.interview_note is not None:
        candidate.interview_note = schedule_in.interview_note.strip() or None
    return _read(repository.save_candidate(session, candidate))


def save_resume(
    session: Session, candidate_id: UUID, file: UploadFile, school_id: UUID | None
) -> HiringCandidateRead:
    """Stores a candidate's resume on disk and records its path."""
    candidate = get_candidate_or_404(session, candidate_id)
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

    root = Path(settings.UPLOAD_DIR) / "resumes" / (str(school_id) if school_id else "unscoped")
    root.mkdir(parents=True, exist_ok=True)
    safe_name = f"{candidate.id}_{candidate.candidate_no or 'candidate'}{suffix}"
    destination = root / safe_name
    destination.write_bytes(data)

    candidate.resume_path = str(destination)
    return _read(repository.save_candidate(session, candidate))


def update_status(
    session: Session, candidate_id: UUID, status_in: HiringStatusUpdate
) -> HiringCandidateRead:
    if status_in.status not in HIRING_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown hiring status '{status_in.status}'. "
            f"Expected one of: {', '.join(HIRING_STATUSES)}",
        )
    if status_in.status == STATUS_HIRED:
        # Hiring is the registration form's job: it creates the login, the
        # `employee` row and the EMP code, and flips the candidate itself.
        raise HTTPException(
            status_code=422,
            detail="Use the hire form to confirm a hire - it creates the employee record.",
        )

    candidate = get_candidate_or_404(session, candidate_id)
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
