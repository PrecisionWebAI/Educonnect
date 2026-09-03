import enum
from datetime import date

from sqlmodel import Field, SQLModel


class AdmissionStatus(enum.StrEnum):
    pending = "pending"
    under_review = "under_review"
    approved = "approved"
    rejected = "rejected"


class AdmissionApplicationBase(SQLModel):
    student_first_name: str
    student_last_name: str
    date_of_birth: date
    guardian_name: str
    guardian_email: str
    guardian_phone: str
    applied_for_class_level: int
    status: AdmissionStatus = Field(default=AdmissionStatus.pending)
    notes: str | None = None


class AdmissionApplication(AdmissionApplicationBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
