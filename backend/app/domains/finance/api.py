"""The Finance group's router: fees."""

from fastapi import APIRouter

from .fees.router import router as fees

router = APIRouter()
router.include_router(fees, prefix="/finance", tags=["Finance"])
