from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission

from . import service, staff_service
from .schemas import DataQualityRow, EducationReportRow, ReportCard
from .staff_schemas import StaffSummaryReport

router = APIRouter()


@router.get("/cards", response_model=list[ReportCard])
def read_report_cards(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("reports.read")),
):
    """The headline cards at the top of the Reports screen."""
    return service.list_report_cards(session=session)


@router.get("/staff-summary", response_model=StaffSummaryReport)
def read_staff_summary(
    days: int = Query(
        default=30,
        ge=1,
        le=366,
        description="How far back the attendance share looks.",
    ),
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("reports.read")),
):
    """Staff attendance, workload and appraisal in one payload - all derived.

    Nothing is stored: the numbers are read from the register, the timetable and the
    current season each time, so "does this include last week?" has one answer. The
    payload carries the attendance **window** and its `scope`, so a figure is never
    quietly about fewer people or a different month than the reader assumes.
    """
    return staff_service.staff_summary(session, current_user, days)


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
