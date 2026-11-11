"""Reports reads: the cards, the data-quality board and the per-class metrics.

`/reports/*` used to answer with invented numbers; the three tables hold them, so
these read the school's own figures.
"""

from sqlmodel import Session, select

from .models import DataQuality, EducationReport, ReportCard as ReportCardModel
from .schemas import DataQualityRow, EducationReportRow, ReportCard


def list_report_cards(session: Session) -> list[ReportCard]:
    """The headline cards at the top of the Reports screen."""
    return [
        ReportCard(
            id=card.id,  # type: ignore[arg-type]
            title=card.title,
            metric=card.metric,
            value=card.value,
            trend=card.trend,
            tone=card.tone,
        )
        for card in session.exec(select(ReportCardModel)).all()
    ]


def list_data_quality(session: Session) -> list[DataQualityRow]:
    """One row per area the data-quality board scores."""
    return [
        DataQualityRow(
            id=row.id,  # type: ignore[arg-type]
            area=row.area,
            score=row.score,
            issue=row.issue,
            status=row.status,
        )
        for row in session.exec(select(DataQuality)).all()
    ]


def list_education_reports(session: Session) -> list[EducationReportRow]:
    """The per-class metrics table."""
    return [
        EducationReportRow(
            id=row.id,  # type: ignore[arg-type]
            metric=row.metric,
            className=row.class_name,
            value=row.value,
            trend=row.trend,
        )
        for row in session.exec(select(EducationReport)).all()
    ]
