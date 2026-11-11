"""The Operations group's router: admission, staff hiring, fees structure, salary."""

from fastapi import APIRouter

from .admission.router import router as admission
from .fees_structure.router import router as fees_structure
from .salary.router import router as salary
from .staff_hiring.router import router as staff_hiring

router = APIRouter()
router.include_router(admission, prefix="/admissions", tags=["Admissions"])
router.include_router(staff_hiring, prefix="/hiring", tags=["Staff Hiring"])
router.include_router(salary, prefix="/salary", tags=["Staff Salary"])
router.include_router(fees_structure, prefix="/finance", tags=["Finance"])
