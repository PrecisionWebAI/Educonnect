from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission

from . import service
from .schemas import (
    ClassCatalogRead,
    ClassInfoRead,
    ClassMatrixRowRead,
    ClassroomCreate,
    ClassroomRead,
    SectionCreate,
    SectionRead,
)

router = APIRouter()

# Removed AdminOrPrincipal


@router.get("/classes", response_model=list[ClassroomRead])
def read_classes(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("classes.read")),
):
    """
    List all classes. Anyone authenticated can view classes usually,
    but for now we don't strictly protect the GET route or we can.
    """
    return service.get_classes(session=session, skip=skip, limit=limit)


@router.post(
    "/classes", response_model=ClassroomRead, status_code=status.HTTP_201_CREATED
)
def create_class(
    class_in: ClassroomCreate,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("classes.create")),
):
    """
    Create a new class. Admin/Principal only.
    """
    return service.create_class(session=session, class_in=class_in)


@router.get("/classes/{class_id}/sections", response_model=list[SectionRead])
def read_sections(
    class_id: int,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("classes.read")),
):
    """
    List sections for a given class.
    """
    return service.get_sections_by_class(session=session, class_id=class_id)


@router.post(
    "/classes/{class_id}/sections",
    response_model=SectionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_section(
    class_id: int,
    section_in: SectionCreate,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("classes.create")),
):
    """
    Create a new section under a class. Admin/Principal only.
    """
    return service.create_section(
        session=session, class_id=class_id, section_in=section_in
    )


@router.get("/class-info", response_model=list[ClassInfoRead])
def read_class_info(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("classes.read")),
):
    """
    Class cards (class + section) with the real class teacher and strength,
    both read from the database.
    """
    return service.get_class_info(session=session)


@router.get("/class-matrix", response_model=list[ClassMatrixRowRead])
def read_class_matrix(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("classes.read")),
):
    """
    Class matrix: strength / boys / girls / attendance per section, aggregated
    from classroom, section, studentprofile and attendancerecord.
    """
    return service.get_class_matrix(session=session)


@router.get("/catalog", response_model=ClassCatalogRead)
def read_catalog(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("classes.read")),
):
    """
    The class vocabulary: every class with its sections, plus the section names
    and stages in use. Screens read their dropdowns from here instead of keeping
    a hardcoded class list.
    """
    return service.get_catalog(session=session)
