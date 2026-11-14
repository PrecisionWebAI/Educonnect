"""The People group's router: teachers and the staff roster.

`teachers` is a **hub** (`teachers/api.py`), not a single router: the screen opens
sub-features (today the profile, later workload, attendance, substitutions and
appraisals), and the hub spells out its own `/teachers` segment so it can decide
the mount order - the directory's `/{teacher_id}` must never shadow a fixed path.
"""

from fastapi import APIRouter

from .staff.router import router as staff
from .teachers.api import router as teachers

router = APIRouter()
router.include_router(teachers)
router.include_router(staff, prefix="/staff", tags=["Staff"])
