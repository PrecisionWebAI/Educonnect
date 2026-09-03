from sqlmodel import Session, select

from .models import ExamPaper, ExamResult, ExamTerm
from .schemas import ExamPaperCreate, ExamResultCreate, ExamTermCreate


def create_term(session: Session, term_in: ExamTermCreate) -> ExamTerm:
    db_term = ExamTerm.model_validate(term_in)
    session.add(db_term)
    session.commit()
    session.refresh(db_term)
    return db_term


def get_terms_by_class(session: Session, class_id: int) -> list[ExamTerm]:
    statement = select(ExamTerm).where(ExamTerm.grade_class_id == class_id)
    return list(session.exec(statement).all())


def create_or_update_paper(session: Session, paper_in: ExamPaperCreate) -> ExamPaper:
    statement = select(ExamPaper).where(
        ExamPaper.exam_term_id == paper_in.exam_term_id,
        ExamPaper.subject_id == paper_in.subject_id,
    )
    existing = session.exec(statement).first()

    if existing:
        existing.status = paper_in.status
        existing.content_json = paper_in.content_json
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing

    db_paper = ExamPaper.model_validate(paper_in)
    session.add(db_paper)
    session.commit()
    session.refresh(db_paper)
    return db_paper


def create_or_update_result(
    session: Session, result_in: ExamResultCreate
) -> ExamResult:
    statement = select(ExamResult).where(
        ExamResult.exam_paper_id == result_in.exam_paper_id,
        ExamResult.student_id == result_in.student_id,
    )
    existing = session.exec(statement).first()

    if existing:
        existing.marks_obtained = result_in.marks_obtained
        existing.ai_feedback = result_in.ai_feedback
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing

    db_result = ExamResult.model_validate(result_in)
    session.add(db_result)
    session.commit()
    session.refresh(db_result)
    return db_result


def get_results_by_student(session: Session, student_id: int) -> list[ExamResult]:
    statement = select(ExamResult).where(ExamResult.student_id == student_id)
    return list(session.exec(statement).all())
