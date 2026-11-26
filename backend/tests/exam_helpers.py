"""Test helper: a paper can only be published once every child has a score or an absence."""

from app.domains.academic.classroom.exams.models import ExamPaper, Mark
from app.domains.academic.classroom.exams.plan import service
from app.domains.academic.classroom.exams.plan.schemas import MarkEntryIn, MarksSaveIn
from sqlmodel import select


def publish(session, paper_id, user):
    """Mark every child who has nothing yet as absent, then publish the paper."""
    paper = session.get(ExamPaper, paper_id)
    have = {
        m.student_id
        for m in session.exec(select(Mark).where(Mark.exam_paper_id == paper_id)).all()
        if m.is_absent or m.marks_obtained is not None
    }
    rest = [
        MarkEntryIn(student_id=student.id, absent=True)
        for student in service._section_students(session, paper).values()
        if student.id not in have
    ]
    if rest:
        service.save_marks(session, paper_id, MarksSaveIn(entries=rest), user)
    return service.publish_paper(session, paper_id, user)
