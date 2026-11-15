"""The Course tab's two endpoints, mounted on the paths the plan names.

* `GET /classroom/sections/{id}/course` - the whole tab (plan + teachers + progress).
* `PATCH /course/chapters/{chapter_id}/progress` - tick one chapter for one section.

Two routers because the two paths live under different prefixes; both are this one
module's, so the rules (`service.py`) and the shapes (`schemas.py`) stay in one place.
"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission

from . import service
from .schemas import ChapterRowRead, ChapterTickIn, SectionCourseRead

#: Mounted at `/classroom` (the section's course).
classroom_router = APIRouter()

#: Mounted at `/course` (a chapter's progress).
router = APIRouter()


@classroom_router.get("/sections/{section_id}/course", response_model=SectionCourseRead)
def read_section_course(
    section_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("classes.read")),
):
    """The Course tab for one class-section.

    Per subject: who teaches it now, everyone who has taught it (with what each of them
    finished), the chapter list with its status and dates, the percentage, the next
    chapter and how many are behind plan. An empty list means "no plan yet" - the tab
    says so rather than drawing 0%.
    """
    return service.section_course(
        session=session, section_id=section_id, user=current_user
    )


@router.patch("/chapters/{chapter_id}/progress", response_model=ChapterRowRead)
def tick_chapter_progress(
    chapter_id: UUID,
    payload: ChapterTickIn,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("classes.read")),
):
    """Move a chapter's status for one class-section (Pending / In progress / Completed).

    `classes.read` opens the door because the Course tab is part of the class screen;
    the **service** then refuses anyone who is neither the office (`classes.update`) nor
    the person currently holding that subject in that section (`403`).
    """
    return service.tick_chapter(
        session=session, chapter_id=chapter_id, payload=payload, user=current_user
    )
