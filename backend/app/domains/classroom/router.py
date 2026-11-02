"""Classroom API - the principal-and-above class grid."""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission
from app.domains.auth.roles import has_role

from . import service
from .schemas import ClassGroup, SectionDetail

router = APIRouter()

#: Roles that look after the whole school, so they may see every class. A teacher
#: keeps the per-teacher "My Classes" view instead - this grid is school-wide.
SCHOOL_WIDE_ROLES = (
    "system_admin",
    "school_admin",
    "principal",
    "vice_principal",
    "hod",
)


@router.get("/overview", response_model=list[ClassGroup])
def read_overview(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("classes.read")),
):
    """A group per class, a card per class-section, with the real aggregates.

    Every number (attendance, fees, syllabus, marks, homework, strength) is read
    from the database - a figure with no data behind it comes back null.
    """
    if not has_role(current_user, *SCHOOL_WIDE_ROLES):
        raise HTTPException(
            status_code=403,
            detail="Only the principal and above can see the school-wide class grid.",
        )
    return service.overview(session=session)


@router.get("/sections/{section_id}", response_model=SectionDetail)
def read_section_detail(
    section_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("classes.read")),
):
    """One class-section in full: students, attendance, timetable, homework,
    diary and marks - every list read straight from its own table."""
    if not has_role(current_user, *SCHOOL_WIDE_ROLES):
        raise HTTPException(
            status_code=403,
            detail="Only the principal and above can open a class-section.",
        )
    return service.section_detail(session=session, section_id=section_id)
