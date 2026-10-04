from datetime import date

from pydantic import BaseModel

from .models import StudentProfileBase


class StudentCreate(StudentProfileBase):
    pass


class StudentRead(StudentProfileBase):
    id: int
    name: str | None = None
    admissionNo: str | None = None
    className: str | None = None
    section: str | None = None
    gender: str = "Male"
    guardian: str | None = None
    phone: str | None = None
    email: str | None = None
    status: str = "Active"
    #: The guardian's login (via `studentparentrelationship`), when one exists.
    #: The directory counts these to show how many parents actually have an
    #: account, and shows the address so the office can hand it over.
    guardianEmail: str | None = None
    guardianUserId: int | None = None


class StudentUpdate(BaseModel):
    date_of_birth: date | None = None
    guardian_name: str | None = None
    classroom_id: int | None = None
    section_id: int | None = None
