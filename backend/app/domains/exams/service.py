from sqlmodel import Session

from app.domains.students import repository as student_repository

from . import repository
from .models import ExamPaper, ExamResult, ExamTerm
from .schemas import (
    BulkExamResultCreate,
    ExamPaperCreate,
    ExamResultCreate,
    ExamTermCreate,
)


def create_term(session: Session, term_in: ExamTermCreate) -> ExamTerm:
    return repository.create_term(session, term_in)


def get_terms_by_class(session: Session, class_id: int) -> list[ExamTerm]:
    return repository.get_terms_by_class(session, class_id)


def create_or_update_paper(session: Session, paper_in: ExamPaperCreate) -> ExamPaper:
    return repository.create_or_update_paper(session, paper_in)


def bulk_upload_results(
    session: Session, bulk_data: BulkExamResultCreate, current_user=None
) -> list[ExamResult]:
    from app.domains.exams.models import ResultStatus

    results = []
    for item in bulk_data.results:
        # Validate student exists
        student = student_repository.get_student_by_id(session, item["student_id"])
        if not student:
            continue  # Or raise error

        res_in = ExamResultCreate(
            exam_paper_id=bulk_data.exam_paper_id,
            student_id=item["student_id"],
            marks_obtained=item["marks_obtained"],
            ai_feedback=item.get("ai_feedback"),
            status=ResultStatus.entered,
            entered_by_id=current_user.id if current_user else None,
        )
        # Note: similar logic for tracking updates vs creations should be added here
        saved = repository.create_or_update_result(session, res_in)
        results.append(saved)
    return results


def get_results_by_paper(session: Session, paper_id: int) -> list[ExamResult]:
    return repository.get_results_by_paper(session, paper_id)


def approve_paper_results(
    session: Session, paper_id: int, current_user=None
) -> list[ExamResult]:
    from fastapi import HTTPException

    from app.domains.exams.models import ResultStatus

    paper = session.get(ExamPaper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    results = repository.get_results_by_paper(session, paper_id)
    if not results:
        raise HTTPException(
            status_code=400, detail="No marks entered for this exam paper yet."
        )

    if any(r.status == ResultStatus.published for r in results):
        raise HTTPException(
            status_code=400,
            detail="Cannot approve results that have already been published.",
        )

    user_id = current_user.id if current_user else None
    return repository.update_paper_results_status(
        session, paper_id, ResultStatus.approved, user_id
    )


def publish_paper_results(
    session: Session, paper_id: int, current_user=None
) -> list[ExamResult]:
    from fastapi import HTTPException

    from app.domains.exams.models import ResultStatus

    paper = session.get(ExamPaper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    results = repository.get_results_by_paper(session, paper_id)
    if not results:
        raise HTTPException(
            status_code=400, detail="No marks entered for this exam paper yet."
        )

    if any(r.status == ResultStatus.entered for r in results):
        raise HTTPException(
            status_code=400,
            detail="Cannot publish results: marks must be approved by the class teacher first.",
        )

    user_id = current_user.id if current_user else None
    return repository.update_paper_results_status(
        session, paper_id, ResultStatus.published, user_id
    )


def get_results_by_student(
    session: Session, student_id: int, current_user=None
) -> list[ExamResult]:
    from app.domains.exams.models import ResultStatus
    from app.domains.users.models import RoleEnum

    results = repository.get_results_by_student(session, student_id)
    if current_user and current_user.role in [RoleEnum.student, RoleEnum.guardian]:
        results = [r for r in results if r.status == ResultStatus.published]
    return results
