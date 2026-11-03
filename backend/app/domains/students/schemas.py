from datetime import date
from uuid import UUID
from pydantic import BaseModel

from .models import StudentProfileBase


class StudentCreate(StudentProfileBase):
    pass


class StudentRead(StudentProfileBase):
    id: UUID
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
    guardianUserId: UUID | None = None


class StudentUpdate(BaseModel):
    date_of_birth: date | None = None
    guardian_name: str | None = None
    section_id: UUID | None = None


class StudentDeleteResult(BaseModel):
    """What deleting a student actually removed.

    A class-section exists because students sit in it, so when the **last** one
    goes the class-section goes with them - and `classroomRemoved` names it
    ("Class 10-A"), which is what the screen tells the operator. `None` means the
    student's class-section is still in use (or they had none).
    """

    deleted: bool = True
    id: UUID
    classroomRemoved: str | None = None
