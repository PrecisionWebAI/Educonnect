from uuid import UUID

from fastapi import APIRouter, Depends, status as http_status
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission

from . import service
from .schemas import (
    FeeStructureCreate,
    FeeStructureRead,
    FeeStructureRowCreate,
    FeeStructureRowRead,
    FeeStructureRowUpdate,
    FeeStructureStatusUpdate,
)

router = APIRouter()

_can_read = RequirePermission("fees.read")
_can_manage = RequirePermission("fees.manage_structure")


# ---------------------------------------------------------------------------
# The fee head rows (the table behind the class-wise card)
# ---------------------------------------------------------------------------


@router.get("/structures", response_model=list[FeeStructureRead])
def read_fee_structures(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """Every fee head, oldest first."""
    return service.get_fee_structures(session=session, skip=skip, limit=limit)


@router.post(
    "/structures",
    response_model=FeeStructureRead,
    status_code=http_status.HTTP_201_CREATED,
)
def create_fee_structure(
    structure_in: FeeStructureCreate,
    session: Session = Depends(get_session),
    current_user=Depends(_can_manage),
):
    """Creates a fee head from the raw shape (no class-name resolution)."""
    return service.create_fee_structure(session=session, structure_in=structure_in)


# ---------------------------------------------------------------------------
# The screen itself: the class-wise card
# ---------------------------------------------------------------------------


@router.get("/fee-structures", response_model=list[FeeStructureRowRead])
def read_fee_structure_rows(
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """The class-wise fee card, with live student counts per class."""
    return service.list_fee_structure_rows(session=session)


@router.post("/fee-structures", response_model=FeeStructureRowRead, status_code=201)
def create_fee_structure_row(
    structure_in: FeeStructureRowCreate,
    session: Session = Depends(get_session),
    current_user=Depends(_can_manage),
):
    """Adds a fee head; it stays a Draft until the office publishes it."""
    return service.create_fee_structure_row(session=session, structure_in=structure_in)


@router.put("/fee-structures/{structure_id}", response_model=FeeStructureRowRead)
def update_fee_structure_row(
    structure_id: UUID,
    structure_in: FeeStructureRowUpdate,
    session: Session = Depends(get_session),
    current_user=Depends(_can_manage),
):
    """Edits a fee head's wording, class, frequency, amount or due day."""
    return service.update_fee_structure_row(
        session=session, structure_id=structure_id, structure_in=structure_in
    )


@router.put("/fee-structures/{structure_id}/status", response_model=FeeStructureRowRead)
def set_fee_structure_status(
    structure_id: UUID,
    status_in: FeeStructureStatusUpdate,
    session: Session = Depends(get_session),
    current_user=Depends(_can_manage),
):
    """Publishes or unpublishes a fee head."""
    return service.set_fee_structure_status(
        session=session, structure_id=structure_id, status_in=status_in
    )
