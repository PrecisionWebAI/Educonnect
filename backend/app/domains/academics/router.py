from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RoleChecker
from app.domains.users.models import RoleEnum

from . import service
from .schemas import GradeClassCreate, GradeClassRead, SectionCreate, SectionRead

router = APIRouter()

# Allow admins and principals to manage classes
AdminOrPrincipal = RoleChecker([RoleEnum.admin, RoleEnum.principal, RoleEnum.director])


@router.get("/classes", response_model=list[GradeClassRead])
def read_classes(
    skip: int = 0, limit: int = 100, session: Session = Depends(get_session)
):
    """
    List all classes. Anyone authenticated can view classes usually,
    but for now we don't strictly protect the GET route or we can.
    """
    return service.get_classes(session=session, skip=skip, limit=limit)


@router.post(
    "/classes", response_model=GradeClassRead, status_code=status.HTTP_201_CREATED
)
def create_class(
    class_in: GradeClassCreate,
    session: Session = Depends(get_session),
    current_user=Depends(AdminOrPrincipal),
):
    """
    Create a new class. Admin/Principal only.
    """
    return service.create_class(session=session, class_in=class_in)


@router.get("/classes/{class_id}/sections", response_model=list[SectionRead])
def read_sections(class_id: int, session: Session = Depends(get_session)):
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
    current_user=Depends(AdminOrPrincipal),
):
    """
    Create a new section under a class. Admin/Principal only.
    """
    return service.create_section(
        session=session, class_id=class_id, section_in=section_in
    )
