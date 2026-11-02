from datetime import date

from pydantic import BaseModel, Field


class TeacherCreate(BaseModel):
    user_id: int
    department: str
    qualification: str
    joining_date: date


class TeacherRead(BaseModel):
    id: int
    user_id: int
    department: str
    qualification: str
    joining_date: date
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
