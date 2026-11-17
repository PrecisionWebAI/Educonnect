"""The one route: `GET /teachers/performance`.

Nothing writes a score - it is derived on every read (`service.py`), so there is no
POST, no PATCH and no table. The path is spelled out in full because the screen has
called it since Phase 1 and a rename would break the client for no product reason;
`teachers/api.py` mounts this router with **no** prefix.
"""

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission
from app.domains.people.teachers.schemas import StaffPerformance

from . import service

router = APIRouter()


@router.get("/teachers/performance", response_model=list[StaffPerformance])
def read_staff_performance(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("teachers.read")),
):
    """Attendance, workload and course completion, over the school's session.

    Reading it is reading the directory: `teachers.read`. There is no narrower right
    because there is no write to protect - the number is whatever the register, the
    timetable and the chapter plan already say.
    """
    return service.performance(session)
