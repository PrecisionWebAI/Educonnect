from uuid import UUID

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission

from . import service
from .schemas import (
    ClassTeacherAssignmentRead,
    ClassTeacherAssignmentWrite,
    PromotionBatchCreate,
    PromotionBatchRead,
    PromotionDecisionWrite,
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


@router.post("/class-teachers", response_model=ClassTeacherAssignmentRead, status_code=201)
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
