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
    session: Session, bulk_data: BulkExamResultCreate
) -> list[ExamResult]:
    saved_results = []
    for res in bulk_data.results:
        # Validate student exists
        student = student_repository.get_student_by_id(session, res["student_id"])
        if not student:
            continue  # Or raise error

        result_in = ExamResultCreate(
            exam_paper_id=bulk_data.exam_paper_id,
            student_id=res["student_id"],
            marks_obtained=res["marks_obtained"],
            ai_feedback=res.get("ai_feedback"),
        )
        saved = repository.create_or_update_result(session, result_in)
        saved_results.append(saved)
    return saved_results


def get_results_by_student(session: Session, student_id: int) -> list[ExamResult]:
    return repository.get_results_by_student(session, student_id)
