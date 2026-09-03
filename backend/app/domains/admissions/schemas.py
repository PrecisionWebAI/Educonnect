from datetime import date

from pydantic import BaseModel, EmailStr

from .models import AdmissionApplicationBase, AdmissionStatus


class AdmissionApplicationCreate(BaseModel):
    student_first_name: str
    student_last_name: str
    date_of_birth: date
    guardian_name: str
    guardian_email: EmailStr
    guardian_phone: str
    applied_for_class_level: int


class AdmissionApplicationRead(AdmissionApplicationBase):
    id: int


class AdmissionStatusUpdate(BaseModel):
    status: AdmissionStatus
    notes: str | None = None
