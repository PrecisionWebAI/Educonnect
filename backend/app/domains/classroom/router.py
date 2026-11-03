"""Classroom API - the principal-and-above class grid."""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission
from app.domains.auth.roles import has_role

from . import service
from .schemas import (
    AssignTeacherIn,
    ClassGroup,
    SectionDetail,
    SectionMarkRead,
    SectionMarksSave,
    TeacherOption,
)

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


def _require_school_wide(current_user) -> None:
    """The class grid, its drill-down and its assignments are all school-wide.

    A teacher keeps the per-teacher "My Classes" view instead, so a class-wide
    action is refused rather than silently narrowed to their own sections.
    """
    if not has_role(current_user, *SCHOOL_WIDE_ROLES):
        raise HTTPException(
            status_code=403,
            detail="Only the principal and above can manage the school-wide classes.",
        )


def _require_section_access(session, current_user, section_id) -> None:
    """School-wide roles may open any section; a teacher only the ones they run.

    The student list and the attendance register live on this page, so a teacher
    must be able to open their own class-section even though the grid is
    school-wide.
    """
    if not service.can_open_section(session, current_user, section_id):
        raise HTTPException(
            status_code=403,
            detail=(
                "Only the principal and above, or a teacher of this class-section, "
                "can open it."
            ),
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
    _require_school_wide(current_user)
    return service.overview(session=session)


@router.get("/sections/{section_id}", response_model=SectionDetail)
def read_section_detail(
    section_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("classes.read")),
):
    """One class-section in full: its students, attendance days, timetable, homework,
    diary, marks and its subjects - every list read straight from its own table.

    Open to the principal and above, and to a teacher who runs this section (the
    student list and the attendance register live here).
    """
    _require_section_access(session, current_user, section_id)
    return service.section_detail(session=session, section_id=section_id)


@router.get("/teachers", response_model=list[TeacherOption])
def read_teacher_options(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("classes.read")),
):
    """Every teacher this school can put in front of a class-section."""
    _require_school_wide(current_user)
    return service.teacher_options(session=session)


@router.get("/sections/{section_id}/marks", response_model=list[SectionMarkRead])
def read_section_marks(
    section_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("marks.read")),
):
    """The class-section's marks - one entry per student per exam.

    This is what the Academics tab of a class-section shows: only the marks of the
    students who sit in *this* section, each subject with the maximum the exam
    declared.
    """
    _require_section_access(session, current_user, section_id)
    return service.section_marks(session=session, section_id=section_id)


@router.put("/sections/{section_id}/marks")
def write_section_marks(
    section_id: UUID,
    payload: SectionMarksSave,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("marks.update")),
):
    """Save the scores entered on the Academics tab for this class-section.

    One row per (exam, student, subject): an existing mark is updated, a missing one
    created, so pressing Save twice cannot double a score.
    """
    _require_section_access(session, current_user, section_id)
    written = service.save_section_marks(
        session=session, section_id=section_id, payload=payload, user=current_user
    )
    return {"written": written}


@router.get("/marks", response_model=list[SectionMarkRead])
def read_all_marks(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("marks.read")),
):
    """Every mark the school holds, grouped per student per exam.

    The school-wide view (the Academics screen and the director's dashboard): one
    entry per student per exam, whatever class-section they sit in. A class-section's
    own marks come from `/sections/{id}/marks`.
    """
    _require_school_wide(current_user)
    return service.all_marks(session=session)


@router.put("/sections/{section_id}/class-teacher", status_code=204)
def set_class_teacher(
    section_id: UUID,
    payload: AssignTeacherIn,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("classes.assign_teacher")),
):
    """Assign the section's class teacher, or clear it with `teacherId: null`.

    One per section: sending another id replaces whoever held it, because the
    teacher is a column on the section rather than a row that can be repeated.
    """
    _require_school_wide(current_user)
    service.assign_class_teacher(
        session=session, section_id=section_id, teacher_id=payload.teacherId
    )


@router.put("/sections/{section_id}/subjects/{subject_id}/teacher", status_code=204)
def set_subject_teacher(
    section_id: UUID,
    subject_id: UUID,
    payload: AssignTeacherIn,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("classes.assign_teacher")),
):
    """Assign who takes one subject in one section, or clear it.

    Keyed by section **and** subject: Class 9-A and 9-B can have different
    Mathematics teachers.
    """
    _require_school_wide(current_user)
    service.assign_subject_teacher(
        session=session,
        section_id=section_id,
        subject_id=subject_id,
        teacher_id=payload.teacherId,
    )
