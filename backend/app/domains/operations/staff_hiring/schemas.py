from datetime import date, datetime
from uuid import UUID
from pydantic import BaseModel

from app.core.text import CanonicalRequest
from .models import HiringCandidateBase



class HiringCandidateCreate(CanonicalRequest):
    """Body of `POST /hiring/candidates` (the interview-scheduling form)."""

    candidate_name: str
    department: str
    #: Role codename applied for (teacher, accountant, ...). `role` is the
    #: human label the pipeline table shows, kept for legacy rows.
    applied_for: str | None = None
    role: str | None = None
    qualification: str | None = None
    experience: int = 0
    phone: str | None = None
    email: str | None = None
    subject_id: UUID | None = None
    subject_name: str | None = None
    applied_on: date | None = None
    interview_on: date | None = None
    interview_at: datetime | None = None
    interview_note: str | None = None


class InterviewScheduleUpdate(CanonicalRequest):
    """Body of `PUT /hiring/candidates/{id}/interview`."""

    interview_at: datetime | None = None
    interview_note: str | None = None


class HiringStatusUpdate(CanonicalRequest):
    """Body of `PUT /hiring/candidates/{candidate_id}/status` (non-Hired moves)."""

    status: str
    interview_on: date | None = None


class HiringCandidateRead(HiringCandidateBase):
    id: UUID


class HiringSummary(BaseModel):
    """Figures the Staff Hiring stat tiles show."""

    total: int
    shortlisted: int
    interviews: int
    hired: int
