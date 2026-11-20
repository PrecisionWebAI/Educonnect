"""The Exams plan's HTTP surface, mounted on `/exams` beside the AI-paper routes.

Paths (deliberately **not** under `/exams/papers/{id}` bare, which the question-paper
stack already owns):

* `POST /exams` - plan an exam with its date sheet;
* `GET /exams` - the exams this caller may see;
* `PATCH /exams/{exam_id}` - move the dates, replace the syllabus (families are told);
* `GET /exams/{exam_id}/papers` - the exam and its date sheet;
* `GET /exams/papers/{paper_id}/marks` - the sheet to fill in;
* `POST /exams/papers/{paper_id}/marks` - save a draft;
* `POST /exams/papers/{paper_id}/publish` - publish that sitting;
* `PATCH /exams/papers/{paper_id}/marks/{student_id}` - correct a published mark (audited);
* `GET /exams/{exam_id}/results` - marks, grades and ranks, narrowed to the caller.

Reading needs `marks.read`, writing needs `marks.update`; the **service** then narrows
further (a teacher only acts on a subject they hold, a family only sees its own child).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission

from . import service
from .schemas import (
    ExamCreateIn,
    ExamPaperRead,
    ExamRead,
    ExamUpdateIn,
    MarkChangeIn,
    MarksSavedRead,
    MarksSaveIn,
    PaperMarkRowRead,
    ResultsRead,
)

router = APIRouter()


@router.post("", response_model=ExamRead, status_code=status.HTTP_201_CREATED)
def create_exam(
    payload: ExamCreateIn,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("marks.update")),
):
    """Plan an exam (class exam: its teacher or the office; school exam: the office)."""
    return service.create_exam(session=session, payload=payload, user=current_user)


@router.get("", response_model=list[ExamRead])
def list_exams(
    classroom_id: UUID | None = Query(default=None),
    class_id: UUID | None = Query(default=None),
    exam_status: str | None = Query(default=None, alias="status"),
    academic_year_id: UUID | None = Query(default=None),
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("marks.read")),
):
    """The exams this caller may see (current year by default)."""
    return service.list_exams(
        session,
        current_user,
        classroom_id=classroom_id,
        class_id=class_id,
        status=exam_status,
        academic_year_id=academic_year_id,
    )


@router.get("/{exam_id}/papers", response_model=ExamRead)
def read_exam(
    exam_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("marks.read")),
):
    """One exam with its date sheet, each paper saying whether this caller may edit it."""
    return service.read_exam(session=session, exam_id=exam_id, user=current_user)


@router.patch("/{exam_id}", response_model=ExamRead)
def update_exam(
    exam_id: UUID,
    payload: ExamUpdateIn,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("marks.update")),
):
    """Change the dates or the syllabus. A published paper is never silently re-cut."""
    return service.update_exam(
        session=session, exam_id=exam_id, payload=payload, user=current_user
    )


@router.get("/papers/{paper_id}/marks", response_model=list[PaperMarkRowRead])
def read_paper_marks(
    paper_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("marks.read")),
):
    """The sheet for one paper: every child in its class, marked or not."""
    return service.paper_marks(session, paper_id, current_user)


@router.post("/papers/{paper_id}/marks", response_model=MarksSavedRead)
def save_paper_marks(
    paper_id: UUID,
    payload: MarksSaveIn,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("marks.update")),
):
    """Save a draft of one paper's scores (refused with `409` once published)."""
    return service.save_marks(
        session=session, paper_id=paper_id, payload=payload, user=current_user
    )


@router.post("/papers/{paper_id}/publish", response_model=ExamPaperRead)
def publish_paper_marks(
    paper_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("marks.update")),
):
    """Publish one sitting's marks - the moment families may see them."""
    return service.publish_paper(session=session, paper_id=paper_id, user=current_user)


@router.patch("/papers/{paper_id}/marks/{student_id}", response_model=PaperMarkRowRead)
def change_published_mark(
    paper_id: UUID,
    student_id: UUID,
    payload: MarkChangeIn,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("marks.update")),
):
    """Correct one published mark. Writes `marks_audit` and tells the family."""
    return service.change_mark(
        session=session,
        paper_id=paper_id,
        student_id=student_id,
        payload=payload,
        user=current_user,
    )


@router.get("/{exam_id}/results", response_model=ResultsRead)
def read_results(
    exam_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("marks.read")),
):
    """Marks, grades and ranks - narrowed to the caller (a family sees its own child)."""
    return service.results(session=session, exam_id=exam_id, user=current_user)
