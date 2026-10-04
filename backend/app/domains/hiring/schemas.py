from datetime import date

from pydantic import BaseModel

from .models import HiringCandidateBase, StaffVacancyBase


class HiringCandidateCreate(BaseModel):
    """Body of `POST /hiring/candidates` (the New Candidate modal)."""

    candidate_name: str
    role: str
    department: str
    qualification: str | None = None
    experience: int = 0
    applied_on: date | None = None
    interview_on: date | None = None


class HiringStatusUpdate(BaseModel):
    """Body of `PUT /hiring/candidates/{candidate_id}/status`."""

    status: str
    interview_on: date | None = None


class HiringCandidateRead(HiringCandidateBase):
    id: int


class StaffVacancyRead(StaffVacancyBase):
    id: int


class HiringSummary(BaseModel):
    """Figures the Staff Hiring stat tiles show."""

    total: int
    shortlisted: int
    interviews: int
    hired: int
    #: Open posts = seats on Open vacancies that nobody has been hired into yet.
    open_vacancies: int
