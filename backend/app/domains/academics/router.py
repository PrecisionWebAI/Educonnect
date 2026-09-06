from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RoleChecker
from app.domains.users.models import RoleEnum

from . import service
from .schemas import (
    ClassInfoRead,
    ClassMatrixRowRead,
    GradeClassCreate,
    GradeClassRead,
    SectionCreate,
    SectionRead,
)

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


@router.get("/class-info", response_model=list[ClassInfoRead])
def read_class_info(session: Session = Depends(get_session)):
    classes = service.get_classes(session=session)
    result = []
    for c in classes:
        secs = service.get_sections_by_class(session=session, class_id=c.id)
        if secs:
            for s in secs:
                result.append(
                    ClassInfoRead(
                        id=s.id or c.id,
                        name=c.name.replace("Grade ", ""),
                        section=s.name,
                        classTeacher="M. Iyer",
                        strength=40,
                    )
                )
        else:
            result.append(
                ClassInfoRead(
                    id=c.id,
                    name=c.name.replace("Grade ", ""),
                    section="A",
                    classTeacher="M. Iyer",
                    strength=40,
                )
            )
    return result


@router.get("/class-matrix", response_model=list[ClassMatrixRowRead])
def read_class_matrix(session: Session = Depends(get_session)):
    return [
        ClassMatrixRowRead(
            id=1, className="6A", strength=42, boys=22, girls=20, avgAttendance=95
        ),
        ClassMatrixRowRead(
            id=2, className="7B", strength=40, boys=19, girls=21, avgAttendance=93
        ),
        ClassMatrixRowRead(
            id=3, className="8A", strength=44, boys=24, girls=20, avgAttendance=91
        ),
        ClassMatrixRowRead(
            id=4, className="9C", strength=38, boys=20, girls=18, avgAttendance=89
        ),
        ClassMatrixRowRead(
            id=5, className="10B", strength=41, boys=21, girls=20, avgAttendance=94
        ),
    ]
