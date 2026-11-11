from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission

from . import service
from .schemas import DataQualityRow, EducationReportRow, ReportCard

router = APIRouter()


@router.get("/cards", response_model=list[ReportCard])
def read_report_cards(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("reports.read")),
):
    """The headline cards at the top of the Reports screen."""
    return service.list_report_cards(session=session)


@router.get("/data-quality", response_model=list[DataQualityRow])
def read_data_quality(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("analytics.read")),
):
    """One row per area the data-quality board scores."""
    return service.list_data_quality(session=session)


@router.get("/education", response_model=list[EducationReportRow])
def read_education_reports(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("reports.read")),
):
    """The per-class metrics table."""
    return service.list_education_reports(session=session)
