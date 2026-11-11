from uuid import UUID

from pydantic import BaseModel


class ReportCard(BaseModel):
    id: UUID
    title: str
    metric: str
    value: str
    trend: str
    tone: str


class DataQualityRow(BaseModel):
    id: UUID
    area: str
    score: int
    issue: str
    status: str


class EducationReportRow(BaseModel):
    id: UUID
    metric: str
    className: str
    value: str
    trend: str
