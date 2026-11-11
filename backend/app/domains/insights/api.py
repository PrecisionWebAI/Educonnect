"""The Insights group's router: reports."""

from fastapi import APIRouter

from .reports.router import router as reports

router = APIRouter()
router.include_router(reports, prefix="/reports", tags=["Reports"])
