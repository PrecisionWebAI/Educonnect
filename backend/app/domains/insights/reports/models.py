"""The Reports screen's rows: headline cards, data-quality areas, per-class metrics.

`tone`/`status` are plain text ("green", "Attention") because the stored value is
what the card renders - the UI never maps them back and forth.
"""

from uuid import UUID

from sqlmodel import Field, SQLModel

from app.core.ids import UUIDMixin
from app.core.tenancy import TenantMixin


class ReportCardBase(SQLModel):
    title: str
    metric: str
    value: str
    trend: str
    tone: str  # "green" / "red" / "amber"


class ReportCard(ReportCardBase, TenantMixin, UUIDMixin, table=True):
    pass


class DataQualityBase(SQLModel):
    area: str
    score: int
    issue: str
    status: str  # Healthy / Attention / Critical


class DataQuality(DataQualityBase, TenantMixin, UUIDMixin, table=True):
    pass


class EducationReportBase(SQLModel):
    metric: str
    class_name: str
    #: The class the metric is scoped to - a `classname` row. The wording above is
    #: kept for the report's "Scope" column and for rows written before this column.
    class_id: UUID | None = Field(
        default=None, foreign_key="classname.class_id", index=True
    )
    value: str
    trend: str


class EducationReport(EducationReportBase, TenantMixin, UUIDMixin, table=True):
    pass
