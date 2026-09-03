from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RoleChecker
from app.domains.users.models import RoleEnum

from . import service
from .schemas import (
    BulkExamResultCreate,
    ExamPaperCreate,
    ExamPaperRead,
    ExamResultRead,
    ExamTermCreate,
    ExamTermRead,
)

router = APIRouter()

AdminPrincipalDirector = RoleChecker(
    [RoleEnum.admin, RoleEnum.principal, RoleEnum.director]
)
StaffRoles = RoleChecker(
    [
        RoleEnum.admin,
        RoleEnum.principal,
        RoleEnum.director,
        RoleEnum.teacher,
        RoleEnum.hod,
    ]
)


@router.post("/terms", response_model=ExamTermRead, status_code=status.HTTP_201_CREATED)
def create_exam_term(
    term_in: ExamTermCreate,
    session: Session = Depends(get_session),
    current_user=Depends(AdminPrincipalDirector),
):
    """
    Create an exam term.
    """
    return service.create_term(session=session, term_in=term_in)


@router.get("/terms/class/{class_id}", response_model=list[ExamTermRead])
def read_exam_terms(class_id: int, session: Session = Depends(get_session)):
    """
    Fetch exam terms for a specific class.
    """
    return service.get_terms_by_class(session=session, class_id=class_id)


@router.post(
    "/papers", response_model=ExamPaperRead, status_code=status.HTTP_201_CREATED
)
def create_exam_paper(
    paper_in: ExamPaperCreate,
    session: Session = Depends(get_session),
    current_user=Depends(StaffRoles),
):
    """
    Save an Exam Paper draft (AI generated JSON content).
    """
    return service.create_or_update_paper(session=session, paper_in=paper_in)


@router.post(
    "/results/bulk",
    response_model=list[ExamResultRead],
    status_code=status.HTTP_201_CREATED,
)
def bulk_upload_results(
    bulk_data: BulkExamResultCreate,
    session: Session = Depends(get_session),
    current_user=Depends(StaffRoles),
):
    """
    Upload student marks for a specific paper.
    """
    return service.bulk_upload_results(session=session, bulk_data=bulk_data)


@router.get("/results/student/{student_id}", response_model=list[ExamResultRead])
def read_student_results(student_id: int, session: Session = Depends(get_session)):
    """
    Fetch a student's report card data.
    """
    return service.get_results_by_student(session=session, student_id=student_id)
