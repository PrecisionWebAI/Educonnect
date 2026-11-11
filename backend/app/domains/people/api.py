"""The People group's router: teachers and the staff roster."""

from fastapi import APIRouter

from .staff.router import router as staff
from .teachers.router import router as teachers

router = APIRouter()
router.include_router(teachers, prefix="/teachers", tags=["Teachers"])
router.include_router(staff, prefix="/staff", tags=["Staff"])
