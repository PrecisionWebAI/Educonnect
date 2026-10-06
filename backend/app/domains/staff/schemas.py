"""Request/response models for the staff registration flow."""

import datetime as dt

from pydantic import BaseModel

from app.domains.staff.models import StaffRegistrationBase


class StaffRegistrationCreate(StaffRegistrationBase):
    """Body of the short registration form on the Staff Hiring screen."""

    # The office may leave the joining date blank; the server stores today.
    joining_date: dt.date | None = None


class LoginCredential(BaseModel):
    """One login handed over at hire time (password shown exactly once)."""

    role: str
    full_name: str
    email: str
    password: str | None = None
    created: bool = True


class StaffPasswordResetRead(BaseModel):
    full_name: str
    email: str
    password: str


class StaffProfileRead(BaseModel):
    id: int
    user_id: int
    employee_code: str
    full_name: str
    email: str
    role_codename: str
    department: str
    qualification: str | None = None
    experience_years: int = 0
    joining_date: dt.date
    is_teacher: bool


class StaffRegistrationRead(StaffRegistrationBase):
    """A registration row, plus the login it created (if promoted)."""

    id: int
    created_at: dt.datetime
    staff_profile_id: int | None = None
    user_id: int | None = None
    promoted_at: dt.datetime | None = None
    login_email: str | None = None
    credentials: list[LoginCredential] | None = None
