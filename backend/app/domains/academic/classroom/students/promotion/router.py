from uuid import UUID

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission

from . import direct, service
from .schemas import (
    ClassTeacherAssignmentRead,
    ClassTeacherAssignmentWrite,
    DemoteIn,
    DepromoteIn,
    DepromotePreviewRead,
    PromoteIn,
    PromotionBatchCreate,
    PromotionBatchRead,
    PromotionDecisionWrite,
    PromotionResultRead,
    StudentIdsIn,
    UndoIn,
)

router = APIRouter()
_manage = RequirePermission("students.promote")


def _user_id(current_user) -> UUID | None:
    return getattr(current_user, "id", None)


@router.get("", response_model=list[PromotionBatchRead])
def read_batches(
    session: Session = Depends(get_session),
    current_user=Depends(_manage),
):
    return service.list_batches(session)


@router.post("", response_model=PromotionBatchRead, status_code=201)
def create_batch(
    payload: PromotionBatchCreate,
    session: Session = Depends(get_session),
    current_user=Depends(_manage),
):
    return service.create_batch(session, payload, _user_id(current_user))


@router.get("/class-teachers", response_model=list[ClassTeacherAssignmentRead])
def read_class_teachers(
    academic_year_id: UUID | None = None,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("students.read")),
):
    return service.list_class_teachers(session, academic_year_id)


@router.post(
    "/class-teachers", response_model=ClassTeacherAssignmentRead, status_code=201
)
def assign_class_teacher(
    payload: ClassTeacherAssignmentWrite,
    session: Session = Depends(get_session),
    current_user=Depends(_manage),
):
    return service.assign_class_teacher(session, payload, _user_id(current_user))


@router.get("/{batch_id}", response_model=PromotionBatchRead)
def read_batch(
    batch_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(_manage),
):
    return service.get_batch(session, batch_id)


@router.put("/{batch_id}/decisions", response_model=PromotionBatchRead)
def put_decisions(
    batch_id: UUID,
    payload: list[PromotionDecisionWrite],
    session: Session = Depends(get_session),
    current_user=Depends(_manage),
):
    return service.put_decisions(session, batch_id, payload, _user_id(current_user))


@router.post("/{batch_id}/apply", response_model=PromotionBatchRead)
def apply_batch(
    batch_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(_manage),
):
    return service.apply_batch(session, batch_id, _user_id(current_user))


# ---- direct actions from the Students tab (one transaction each) -------------------------
@router.post("/promote", response_model=PromotionResultRead)
def promote_students(
    payload: PromoteIn,
    session: Session = Depends(get_session),
    current_user=Depends(_manage),
):
    """New enrollment in the next year, in the chosen (default: next) class."""
    return direct.promote(
        session, payload.student_ids, payload.target_class_id, payload.target_section
    )


@router.post("/retain", response_model=PromotionResultRead)
def retain_students(
    payload: StudentIdsIn,
    session: Session = Depends(get_session),
    current_user=Depends(_manage),
):
    """New enrollment in the next year, same class-section."""
    return direct.retain(session, payload.student_ids)


@router.post("/complete", response_model=PromotionResultRead)
def complete_students(
    payload: StudentIdsIn,
    session: Session = Depends(get_session),
    current_user=Depends(_manage),
):
    """Highest class only: mark the current record COMPLETED."""
    return direct.complete(session, payload.student_ids)


@router.post("/demote", response_model=PromotionResultRead)
def demote_students(
    payload: DemoteIn,
    session: Session = Depends(get_session),
    current_user=Depends(_manage),
):
    """One class down (the class they came from), into the chosen section."""
    return direct.demote(session, payload.student_ids, payload.target_section)


@router.post("/undo/preview", response_model=DepromotePreviewRead)
def preview_undo(
    payload: StudentIdsIn,
    session: Session = Depends(get_session),
    current_user=Depends(_manage),
):
    """What undoing the last promote / retain / move down would delete."""
    return direct.preview_undo(session, payload.student_ids)


@router.post("/undo", response_model=PromotionResultRead)
def undo_students(
    payload: UndoIn,
    session: Session = Depends(get_session),
    current_user=Depends(_manage),
):
    """Undo the last promote, retain or move down; deletes only with `confirm: true`."""
    return direct.undo(session, payload.student_ids, payload.confirm)


@router.post("/depromote/preview", response_model=DepromotePreviewRead)
def preview_depromote(
    payload: StudentIdsIn,
    session: Session = Depends(get_session),
    current_user=Depends(_manage),
):
    """What de-promoting would permanently delete (nothing is changed)."""
    return direct.preview_depromote(session, payload.student_ids)


@router.post("/depromote", response_model=PromotionResultRead)
def depromote_students(
    payload: DepromoteIn,
    session: Session = Depends(get_session),
    current_user=Depends(_manage),
):
    """Undo promote / retain / complete; deletes only with `confirm: true`."""
    return direct.depromote(session, payload.student_ids, payload.confirm)
