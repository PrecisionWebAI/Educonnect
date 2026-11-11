from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission

from . import guardians, lifecycle, service
from .schemas import (
    GuardianLinkRead,
    GuardianRemoveResult,
    GuardianWrite,
    LifecycleRequest,
    StudentCreate,
    StudentDeleteResult,
    StudentLifecycleRead,
    StudentRead,
)

router = APIRouter()

# The guardians of a student are part of that student's record: reading them needs the
# same permission the directory does, editing them the same one a student edit needs.
_guardians_read = RequirePermission("students.read")
_guardians_write = RequirePermission("students.update")


@router.get("", response_model=list[StudentRead])
def read_students(
    skip: int = 0,
    limit: int | None = None,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("students.read")),
):
    """
    List all students. Staff only.

    No default limit, because the directory paginates and filters on the client:
    a limit below the roll silently hides students. Ask for a page explicitly
    (`?skip=100&limit=50`) when one is wanted.
    """
    return service.get_students(session=session, skip=skip, limit=limit)


@router.post("", response_model=StudentRead, status_code=status.HTTP_201_CREATED)
def create_student(
    student_in: StudentCreate,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("students.create")),
):
    """
    Create a student profile. Admin/Principal only.
    """
    return service.create_student(session=session, student_in=student_in)


@router.get("/{student_id}", response_model=StudentRead)
def read_student(
    student_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("students.read")),
):
    """
    Get a specific student profile.
    """
    return service.get_student(session=session, student_id=student_id)


@router.delete("/{student_id}", response_model=StudentDeleteResult)
def delete_student(
    student_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("students.delete")),
):
    """
    Permanently delete a student and their records (requires `students.delete`).

    When the student was the last one in their class-section, that class-section is
    deleted too, together with everything it owned (attendance register, timetable,
    homework, diary, syllabus progress and teacher assignments); the response names
    it so the screen can say so.
    """
    return service.delete_student(session=session, student_id=student_id)


# ---------------------------------------------------------------------------
# The guardians of a student (the card on the student's screen)
# ---------------------------------------------------------------------------


@router.post("/{student_id}/deactivate", response_model=StudentLifecycleRead)
def deactivate_student(
    student_id: UUID,
    payload: LifecycleRequest | None = None,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("students.update")),
):
    """Take a child off the roll (the directory's "Mark as left").

    Nothing is deleted and **no login is switched off**: the registers, marks and fees of
    the years they were here stay readable, and a child who left is still a family's
    child - the account that signs in is usually their guardian's anyway.
    """
    return lifecycle.deactivate_student(
        session=session, student_id=student_id, payload=payload
    )


@router.post("/{student_id}/reactivate", response_model=StudentLifecycleRead)
def reactivate_student(
    student_id: UUID,
    payload: LifecycleRequest | None = None,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("students.update")),
):
    """Put the child back on the roll, with everything that was already theirs."""
    return lifecycle.reactivate_student(
        session=session, student_id=student_id, payload=payload
    )


@router.get("/{student_id}/guardians", response_model=list[GuardianLinkRead])
def read_guardians(
    student_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(_guardians_read),
):
    """Every guardian of this student, the primary contact first."""
    return guardians.list_guardians(session=session, student_id=student_id)


@router.post(
    "/{student_id}/guardians",
    response_model=GuardianLinkRead,
    status_code=status.HTTP_201_CREATED,
)
def add_guardian(
    student_id: UUID,
    guardian_in: GuardianWrite,
    session: Session = Depends(get_session),
    current_user=Depends(_guardians_write),
):
    """Add a guardian - or link one the school already has (a sibling's parent).

    A contact that belongs to a guardian on file links **that** person, so a family
    keeps one row, one login and one number however many children it has. When the
    contact is new, their login is created and its first-time password comes back here,
    once. A contact somebody else holds is refused (`409`), naming them.
    """
    return guardians.add_guardian(
        session=session, student_id=student_id, payload=guardian_in
    )


@router.put("/{student_id}/guardians/{guardian_id}", response_model=GuardianLinkRead)
def update_guardian(
    student_id: UUID,
    guardian_id: UUID,
    guardian_in: GuardianWrite,
    session: Session = Depends(get_session),
    current_user=Depends(_guardians_write),
):
    """Edit a guardian: their contact, their name, and this child's relation.

    The change follows the person everywhere (`contacts.sync_contact`), so their login
    and - when they also work here - their staff record never disagree with the card.
    """
    return guardians.update_guardian(
        session=session,
        student_id=student_id,
        guardian_id=guardian_id,
        payload=guardian_in,
    )


@router.delete(
    "/{student_id}/guardians/{guardian_id}", response_model=GuardianRemoveResult
)
def remove_guardian(
    student_id: UUID,
    guardian_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(_guardians_write),
):
    """Unlink a guardian from this student (the person and their login stay)."""
    return guardians.remove_guardian(
        session=session, student_id=student_id, guardian_id=guardian_id
    )
