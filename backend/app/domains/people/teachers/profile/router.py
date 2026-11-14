"""The profile's API - the drawer's inner tabs, one list each.

Every write takes the **same two steps**: `_employee(...)` resolves the person the
caller may see (`404` otherwise) and `service.require_edit` decides whether this
caller may change them (`403`, or `409` for a leaver). The rule lives in the
service, not in a decorator, so it cannot be forgotten on a new route - and it is
checked on the server, because the drawer hiding an Edit button is a courtesy,
not a permission.

The row id is always looked up **within the employee** (`repository.qualification`
takes both), so a caller who may edit one profile cannot delete another's row by
guessing its id.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi import status as http
from fastapi.responses import FileResponse
from sqlmodel import Session

from app.core.db import get_session
from app.domains.admin.users.models import User
from app.domains.auth.dependencies import RequirePermission
from app.domains.people.staff.models import Employee

from . import service
from .schemas import (
    CertificationCreate,
    CertificationRead,
    CertificationUpdate,
    DocumentRead,
    DocumentVerify,
    EmploymentUpdate,
    ExperienceCreate,
    ExperienceRead,
    ExperienceUpdate,
    ProfileLists,
    QualificationCreate,
    QualificationRead,
    QualificationUpdate,
    SubjectsUpdate,
)

router = APIRouter()

_can_read = RequirePermission("teachers.read")
_can_edit = RequirePermission("teachers.update")


def _employee(session: Session, employee_id: UUID, user: User) -> Employee:
    """The person, if this caller may see them - `404` otherwise."""
    return service.require_employee(session, employee_id, user)


# --- the whole profile ----------------------------------------------------
#
# There is deliberately **no `GET /profile/{id}`** here: the drawer reads the
# person and all four lists in one call (`GET /teachers/{id}/profile`, in the
# hub), so a second read endpoint would be the same answer under a second name -
# and two reads that can disagree. This sub-router owns the *writes*.


@router.put("/{employee_id}/employment", response_model=ProfileLists)
def update_employment(
    employee_id: UUID,
    payload: EmploymentUpdate,
    session: Session = Depends(get_session),
    current_user=Depends(_can_edit),
):
    """The post itself: designation, employment type, probation, reporting line.

    Returns the whole profile rather than the four edited fields: a designation
    change also appends a history row, and the drawer would otherwise have to
    refetch to see the row its own save created.
    """
    employee = _employee(session, employee_id, current_user)
    service.require_edit(session, employee, current_user)
    service.update_employment(session, employee, payload, current_user)
    return service.reads(session, employee_id)


@router.put("/{employee_id}/subjects", response_model=list[str])
def replace_subjects(
    employee_id: UUID,
    payload: SubjectsUpdate,
    session: Session = Depends(get_session),
    current_user=Depends(_can_edit),
):
    """The teacher's subject list, replaced. Answers with the stored names."""
    employee = _employee(session, employee_id, current_user)
    service.require_edit(session, employee, current_user)
    return service.set_subjects(session, employee, payload.subject_ids)


# --- qualifications -------------------------------------------------------


@router.post(
    "/{employee_id}/qualifications",
    response_model=QualificationRead,
    status_code=http.HTTP_201_CREATED,
)
def add_qualification(
    employee_id: UUID,
    payload: QualificationCreate,
    session: Session = Depends(get_session),
    current_user=Depends(_can_edit),
):
    """`409` when the degree (and year) is already on the profile."""
    employee = _employee(session, employee_id, current_user)
    service.require_edit(session, employee, current_user)
    return service.add_qualification(session, employee, payload)


@router.patch(
    "/{employee_id}/qualifications/{row_id}", response_model=QualificationRead
)
def update_qualification(
    employee_id: UUID,
    row_id: UUID,
    payload: QualificationUpdate,
    session: Session = Depends(get_session),
    current_user=Depends(_can_edit),
):
    employee = _employee(session, employee_id, current_user)
    service.require_edit(session, employee, current_user)
    return service.update_qualification(session, employee, row_id, payload)


@router.delete(
    "/{employee_id}/qualifications/{row_id}", status_code=http.HTTP_204_NO_CONTENT
)
def delete_qualification(
    employee_id: UUID,
    row_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(_can_edit),
):
    employee = _employee(session, employee_id, current_user)
    service.require_edit(session, employee, current_user)
    service.delete_qualification(session, employee, row_id)


# --- experience -----------------------------------------------------------


@router.post(
    "/{employee_id}/experiences",
    response_model=ExperienceRead,
    status_code=http.HTTP_201_CREATED,
)
def add_experience(
    employee_id: UUID,
    payload: ExperienceCreate,
    session: Session = Depends(get_session),
    current_user=Depends(_can_edit),
):
    employee = _employee(session, employee_id, current_user)
    service.require_edit(session, employee, current_user)
    return service.add_experience(session, employee, payload)


@router.patch("/{employee_id}/experiences/{row_id}", response_model=ExperienceRead)
def update_experience(
    employee_id: UUID,
    row_id: UUID,
    payload: ExperienceUpdate,
    session: Session = Depends(get_session),
    current_user=Depends(_can_edit),
):
    employee = _employee(session, employee_id, current_user)
    service.require_edit(session, employee, current_user)
    return service.update_experience(session, employee, row_id, payload)


@router.delete(
    "/{employee_id}/experiences/{row_id}", status_code=http.HTTP_204_NO_CONTENT
)
def delete_experience(
    employee_id: UUID,
    row_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(_can_edit),
):
    employee = _employee(session, employee_id, current_user)
    service.require_edit(session, employee, current_user)
    service.delete_experience(session, employee, row_id)


# --- certifications -------------------------------------------------------


@router.post(
    "/{employee_id}/certifications",
    response_model=CertificationRead,
    status_code=http.HTTP_201_CREATED,
)
def add_certification(
    employee_id: UUID,
    payload: CertificationCreate,
    session: Session = Depends(get_session),
    current_user=Depends(_can_edit),
):
    employee = _employee(session, employee_id, current_user)
    service.require_edit(session, employee, current_user)
    return service.add_certification(session, employee, payload)


@router.patch(
    "/{employee_id}/certifications/{row_id}", response_model=CertificationRead
)
def update_certification(
    employee_id: UUID,
    row_id: UUID,
    payload: CertificationUpdate,
    session: Session = Depends(get_session),
    current_user=Depends(_can_edit),
):
    employee = _employee(session, employee_id, current_user)
    service.require_edit(session, employee, current_user)
    return service.update_certification(session, employee, row_id, payload)


@router.delete(
    "/{employee_id}/certifications/{row_id}", status_code=http.HTTP_204_NO_CONTENT
)
def delete_certification(
    employee_id: UUID,
    row_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(_can_edit),
):
    employee = _employee(session, employee_id, current_user)
    service.require_edit(session, employee, current_user)
    service.delete_certification(session, employee, row_id)


# --- documents ------------------------------------------------------------
#
# Four routes and one rule each:
#
# * **upload** - the person may file their own papers, the office anyone's
#   (`require_upload`); the bytes and the row are written together or not at all;
# * **download** - the same scope as reading the profile (`_employee` answers
#   `404` out of scope), and the file is resolved from the stored key, never
#   from anything the caller sent;
# * **verify** / **delete** - `teachers.update` in scope, because both change the
#   school's record. A teacher cannot verify their own Aadhaar: verification is
#   the office saying it saw the original.
#
# None of the four answers with a path or a storage key - only `DocumentRead`,
# which has neither.


@router.post(
    "/{employee_id}/documents",
    response_model=DocumentRead,
    status_code=http.HTTP_201_CREATED,
)
def upload_document(
    employee_id: UUID,
    doc_type: str = Form(...),
    title: str | None = Form(default=None),
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(_can_read),
):
    """File one document (PDF, Word document or image) against this person."""
    employee = _employee(session, employee_id, current_user)
    service.require_upload(session, employee, current_user)
    return service.attach_document(
        session,
        employee,
        doc_type=doc_type,
        title=title,
        file=file,
        user=current_user,
    )


@router.get("/{employee_id}/documents/{row_id}/download")
def download_document(
    employee_id: UUID,
    row_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(_can_read),
):
    """Stream the stored file, named as it was uploaded.

    The row is looked up **within** the employee in the path, and the path is
    rebuilt from the stored key and checked to be inside that employee's folder -
    so a tampered key cannot read a file outside it.
    """
    employee = _employee(session, employee_id, current_user)
    path, row = service.document_file(session, employee, row_id, current_user)
    return FileResponse(
        path=path,
        media_type=row.content_type or "application/octet-stream",
        filename=row.file_name,
    )


@router.patch("/{employee_id}/documents/{row_id}", response_model=DocumentRead)
def verify_document(
    employee_id: UUID,
    row_id: UUID,
    payload: DocumentVerify,
    session: Session = Depends(get_session),
    current_user: User = Depends(_can_edit),
):
    """Mark a document as seen against the original (or take that back)."""
    employee = _employee(session, employee_id, current_user)
    service.require_edit(session, employee, current_user)
    return service.verify_document(
        session,
        employee,
        row_id,
        verified=payload.verified,
        note=payload.note,
        user=current_user,
    )


@router.delete(
    "/{employee_id}/documents/{row_id}", status_code=http.HTTP_204_NO_CONTENT
)
def delete_document(
    employee_id: UUID,
    row_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(_can_edit),
):
    """Delete the row and the file; the audit trail keeps the line."""
    employee = _employee(session, employee_id, current_user)
    service.require_edit(session, employee, current_user)
    service.remove_document(session, employee, row_id, current_user)
