from datetime import date

from pydantic import BaseModel, Field

from .models import TeacherProfileBase


class TeacherCreate(TeacherProfileBase):
    pass


class TeacherRead(TeacherProfileBase):
    id: int
    staffCode: str | None = None
    name: str | None = None
    subject: str | None = None
    phone: str | None = None
    email: str | None = None
    status: str = "Active"
    classes: list[str] = Field(default_factory=list)
    workload: int = 18


class TeacherUpdate(BaseModel):
    department: str | None = None
    qualification: str | None = None
    joining_date: date | None = None


class WorkloadMatrixRow(BaseModel):
    staff: str
    subject: str
    classes: list[str]
    periods: int
    utilisation: int


class StaffPerformance(BaseModel):
    id: int
    staff: str
    rating: float
    reviews: int
    trend: str
    score: int
