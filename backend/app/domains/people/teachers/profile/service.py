"""What may be written to a profile, and by whom.

The reads are four statements for the whole drawer. The writes are small, and each
one answers the same three questions before touching a row:

* **may this caller see this person?** - out of scope is `404`, never `403`: the
  API must not confirm that a colleague's id exists;
* **may this caller change them?** - `teachers.update` says the caller edits
  profiles at all, `scope.may_edit_profile` says *whose* (all / own department);
* **is the record still open?** - a leaver's profile is read-only (`409`), with a
  message that names the decision (reactivation) which would unlock it.

Everything else is validation the drawer can report: a duplicate degree is `409`
with the degree it found, an unknown subject is `400` naming the id, and a job
that ends before it starts is `400` saying so.
"""

from datetime import date
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException
from sqlmodel import Session, select

from app.domains.academic.classroom.academics.models import Subject
from app.domains.admin.users.models import User
from app.domains.people.staff.models import Employee

from .. import labels, scope
from ..models import StaffAuditLog, StaffDocument, TeacherSubject
from . import documents, repository
from .models import (
    StaffCertification,
    StaffEmploymentHistory,
    StaffExperience,
    StaffQualification,
)
from .schemas import (
    CertificationCreate,
    CertificationRead,
    CertificationUpdate,
    DocumentRead,
    EmploymentUpdate,
    ExperienceCreate,
    ExperienceRead,
    ExperienceUpdate,
    HistoryRead,
    KycRead,
    ProfileLists,
    QualificationCreate,
    QualificationRead,
    QualificationUpdate,
)


def require_employee(
    session: Session, employee_id: UUID, user: User | None = None
) -> Employee:
    """The employee, if this caller may see them (`404` otherwise)."""
    employee = session.get(Employee, employee_id)
    visible = scope.visible_employee_ids(session, user)
    if employee is None or (visible is not None and employee.id not in visible):
        raise HTTPException(status_code=404, detail="Teacher not found")
    return employee


def require_edit(session: Session, employee: Employee, user: User | None) -> None:
    """Refuse the write unless this caller may change this profile."""
    if not scope.may_edit_profile(session, user, employee):
        raise HTTPException(
            status_code=403, detail="Your role may not change this staff record."
        )
    if labels.serves_read_only(
        deactivated_at=employee.deactivated_at, left_on=employee.left_on
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "This staff record is off the roll, so it is read-only. "
                "Reactivate the person first."
            ),
        )


def require_upload(session: Session, employee: Employee, user: User | None) -> None:
    """Refuse a document upload the caller may not make (`403` / `409`).

    Wider than `require_edit` on purpose: the person themselves may file their own
    papers (`scope.may_upload_documents`), the office may file anyone's. The
    leaver rule is the same - an off-roll record is history, so new papers do not
    go into it.
    """
    if not scope.may_upload_documents(session, user, employee):
        raise HTTPException(
            status_code=403, detail="Your role may not file documents on this profile."
        )
    if labels.serves_read_only(
        deactivated_at=employee.deactivated_at, left_on=employee.left_on
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "This staff record is off the roll, so it is read-only. "
                "Reactivate the person first."
            ),
        )


# --- reads ----------------------------------------------------------------


def reads(session: Session, employee_id: UUID) -> ProfileLists:
    """The four lists the drawer's inner tabs show - four statements, not four
    round trips: a profile opened from the directory needs all of them at once,
    and loading them separately would let the tabs disagree while they fill."""
    qualifications = [
        QualificationRead(
            id=row.id,
            degree=row.degree,
            institution=row.institution,
            year_completed=row.year_completed,
            grade=row.grade,
        )
        for row in repository.qualifications(session, employee_id)
    ]
    experiences = [
        ExperienceRead(
            id=row.id,
            employer=row.employer,
            designation=row.designation,
            from_date=row.from_date,
            to_date=row.to_date,
            note=row.note,
        )
        for row in repository.experiences(session, employee_id)
    ]
    certifications = [
        _certification_read(row)
        for row in repository.certifications(session, employee_id)
    ]

    events = repository.history(session, employee_id)
    names = repository.recorder_names(
        session, [row.recorded_by_user_id for row in events]
    )
    history = [
        HistoryRead(
            id=row.id,
            event=row.event,
            effective_on=row.effective_on,
            from_value=row.from_value,
            to_value=row.to_value,
            note=row.note,
            recorded_by=(
                names.get(row.recorded_by_user_id)
                if row.recorded_by_user_id is not None
                else None
            ),
            created_at=row.created_at,
        )
        for row in events
    ]

    return ProfileLists(
        qualifications=qualifications,
        experiences=experiences,
        certifications=certifications,
        history=history,
        documents=document_reads(session, employee_id),
    )


# --- history --------------------------------------------------------------


def record_history(
    session: Session,
    *,
    employee_id: UUID,
    event: str,
    effective_on: date | None = None,
    from_value: str | None = None,
    to_value: str | None = None,
    note: str | None = None,
    user: User | None = None,
    commit: bool = True,
) -> None:
    """Append one employment event. Never rewrites an existing row.

    Shared on purpose: the hire flow (a new employee is `Joined`), a designation
    change here and the appraisal-driven promotion in Phase 8 all write the same
    table through this function, so "why is this row missing?" has one answer.
    """
    session.add(
        StaffEmploymentHistory(
            employee_id=employee_id,
            event=event,
            effective_on=effective_on or date.today(),
            from_value=from_value,
            to_value=to_value,
            note=note,
            recorded_by_user_id=user.id if user is not None else None,
        )
    )
    if commit:
        session.commit()


# --- qualifications -------------------------------------------------------


def add_qualification(
    session: Session, employee: Employee, payload: QualificationCreate
) -> QualificationRead:
    duplicate = repository.same_qualification(
        session,
        employee_id=employee.id,
        degree=payload.degree,
        year_completed=payload.year_completed,
    )
    if duplicate is not None:
        raise HTTPException(
            status_code=409,
            detail=_already_on_profile(payload.degree, payload.year_completed),
        )

    row = StaffQualification(employee_id=employee.id, **payload.model_dump())
    session.add(row)
    session.commit()
    session.refresh(row)
    return _qualification_read(row)


def update_qualification(
    session: Session, employee: Employee, row_id: UUID, payload: QualificationUpdate
) -> QualificationRead:
    row = repository.qualification(session, employee_id=employee.id, row_id=row_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Qualification not found")

    changes = payload.model_dump(exclude_unset=True)
    degree = changes.get("degree", row.degree)
    year = changes.get("year_completed", row.year_completed)
    duplicate = repository.same_qualification(
        session,
        employee_id=employee.id,
        degree=degree,
        year_completed=year,
        exclude_id=row.id,
    )
    if duplicate is not None:
        raise HTTPException(status_code=409, detail=_already_on_profile(degree, year))

    for field, value in changes.items():
        setattr(row, field, value)
    session.add(row)
    session.commit()
    session.refresh(row)
    return _qualification_read(row)


def delete_qualification(session: Session, employee: Employee, row_id: UUID) -> None:
    row = repository.qualification(session, employee_id=employee.id, row_id=row_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Qualification not found")
    session.delete(row)
    session.commit()


def _qualification_read(row: StaffQualification) -> QualificationRead:
    return QualificationRead(
        id=row.id,
        degree=row.degree,
        institution=row.institution,
        year_completed=row.year_completed,
        grade=row.grade,
    )


def _already_on_profile(degree: str, year: int | None) -> str:
    """The 409's sentence: name the pair, not just "duplicate"."""
    when = f" ({year})" if year else ""
    return f"{degree}{when} is already on this profile."


# --- experience -----------------------------------------------------------


def add_experience(
    session: Session, employee: Employee, payload: ExperienceCreate
) -> ExperienceRead:
    _check_period(payload.from_date, payload.to_date)
    row = StaffExperience(employee_id=employee.id, **payload.model_dump())
    session.add(row)
    session.commit()
    session.refresh(row)
    return _experience_read(row)


def update_experience(
    session: Session, employee: Employee, row_id: UUID, payload: ExperienceUpdate
) -> ExperienceRead:
    row = repository.experience(session, employee_id=employee.id, row_id=row_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Experience not found")

    changes = payload.model_dump(exclude_unset=True)
    _check_period(
        changes.get("from_date", row.from_date), changes.get("to_date", row.to_date)
    )
    for field, value in changes.items():
        setattr(row, field, value)
    session.add(row)
    session.commit()
    session.refresh(row)
    return _experience_read(row)


def delete_experience(session: Session, employee: Employee, row_id: UUID) -> None:
    row = repository.experience(session, employee_id=employee.id, row_id=row_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Experience not found")
    session.delete(row)
    session.commit()


def _experience_read(row: StaffExperience) -> ExperienceRead:
    return ExperienceRead(
        id=row.id,
        employer=row.employer,
        designation=row.designation,
        from_date=row.from_date,
        to_date=row.to_date,
        note=row.note,
    )


def _check_period(start: date | None, end: date | None) -> None:
    """A job or a certificate that ends before it starts cannot be stored."""
    if start is not None and end is not None and end < start:
        raise HTTPException(status_code=400, detail="This ends before it starts.")


# --- certifications -------------------------------------------------------


def add_certification(
    session: Session, employee: Employee, payload: CertificationCreate
) -> CertificationRead:
    _check_period(payload.issued_on, payload.valid_till)
    duplicate = repository.same_certification(
        session,
        employee_id=employee.id,
        name=payload.name,
        issued_on=payload.issued_on,
    )
    if duplicate is not None:
        raise HTTPException(
            status_code=409,
            detail=f"{payload.name} is already on this profile with that issue date.",
        )

    row = StaffCertification(employee_id=employee.id, **payload.model_dump())
    session.add(row)
    session.commit()
    session.refresh(row)
    return _certification_read(row)


def update_certification(
    session: Session, employee: Employee, row_id: UUID, payload: CertificationUpdate
) -> CertificationRead:
    row = repository.certification(session, employee_id=employee.id, row_id=row_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Certification not found")

    changes = payload.model_dump(exclude_unset=True)
    _check_period(
        changes.get("issued_on", row.issued_on),
        changes.get("valid_till", row.valid_till),
    )
    name = changes.get("name", row.name)
    issued_on = changes.get("issued_on", row.issued_on)
    duplicate = repository.same_certification(
        session,
        employee_id=employee.id,
        name=name,
        issued_on=issued_on,
        exclude_id=row.id,
    )
    if duplicate is not None:
        raise HTTPException(
            status_code=409,
            detail=f"{name} is already on this profile with that issue date.",
        )

    for field, value in changes.items():
        setattr(row, field, value)
    session.add(row)
    session.commit()
    session.refresh(row)
    return _certification_read(row)


def delete_certification(session: Session, employee: Employee, row_id: UUID) -> None:
    row = repository.certification(session, employee_id=employee.id, row_id=row_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Certification not found")
    session.delete(row)
    session.commit()


def _certification_read(row: StaffCertification) -> CertificationRead:
    return CertificationRead(
        id=row.id,
        name=row.name,
        issuer=row.issuer,
        issued_on=row.issued_on,
        valid_till=row.valid_till,
        reference_no=row.reference_no,
    )


# --- subjects (the teacher's own list, `teachersubject`) -------------------


def set_subjects(
    session: Session, employee: Employee, subject_ids: list[UUID]
) -> list[str]:
    """Replace the teacher's subject list with exactly these subjects.

    A replace, not a merge: the drawer's form shows the whole list, so "these are
    the subjects" is the request it can actually make - and the only shape that
    can remove one. Ids are de-duplicated, and an id from another school is `400`
    rather than silently dropped: a hidden half-applied save is worse than a
    refusal.
    """
    wanted = list(dict.fromkeys(subject_ids))
    if wanted:
        found = set(
            session.exec(select(Subject.id).where(Subject.id.in_(wanted))).all()
        )
        missing = [str(subject_id) for subject_id in wanted if subject_id not in found]
        if missing:
            raise HTTPException(
                status_code=400, detail=f"Unknown subject: {', '.join(missing)}."
            )

    for row in session.exec(
        select(TeacherSubject).where(TeacherSubject.teacher_id == employee.id)
    ).all():
        session.delete(row)
    for subject_id in wanted:
        session.add(TeacherSubject(teacher_id=employee.id, subject_id=subject_id))
    session.commit()

    return subject_names(session, employee.id)


def subject_names(session: Session, employee_id: UUID) -> list[str]:
    """The teacher's subject names, alphabetically - what the drawer prints."""
    names = session.exec(
        select(Subject.name)
        .join(TeacherSubject, TeacherSubject.subject_id == Subject.id)
        .where(TeacherSubject.teacher_id == employee_id)
        .order_by(Subject.name)
    ).all()
    return list(names)


# --- the post -------------------------------------------------------------


def update_employment(
    session: Session, employee: Employee, payload: EmploymentUpdate, user: User | None
) -> None:
    """Set the post's own detail, and record a designation change as history.

    `probation_end`, `employment_type` and who they report to are corrections to
    the record, so they are written. A **designation** change is a different thing
    - it is the event a salary or a seniority claim is argued from later - so it
    appends a `Designation changed` row rather than silently overwriting the old
    one.
    """
    changes = payload.model_dump(exclude_unset=True)

    reports_to = changes.get("reports_to_employee_id")
    if reports_to is not None:
        if reports_to == employee.id:
            raise HTTPException(
                status_code=400, detail="A person cannot report to themselves."
            )
        if session.get(Employee, reports_to) is None:
            raise HTTPException(
                status_code=400,
                detail="That reporting manager is not on this school's staff.",
            )

    before = employee.designation
    for field, value in changes.items():
        setattr(employee, field, value)
    session.add(employee)
    session.commit()
    session.refresh(employee)

    if "designation" in changes and labels.differs(before, employee.designation):
        record_history(
            session,
            employee_id=employee.id,
            event="Designation changed",
            from_value=before,
            to_value=employee.designation,
            note="Changed from the staff profile.",
            user=user,
        )
        record_audit(
            session,
            employee_id=employee.id,
            section="employment",
            action="updated",
            summary=f"Designation: {before or '—'} -> {employee.designation or '—'}",
            user=user,
        )


# --- the audit trail -------------------------------------------------------


def record_audit(
    session: Session,
    *,
    employee_id: UUID,
    section: str,
    action: str,
    summary: str,
    row_id: UUID | None = None,
    user: User | None = None,
    commit: bool = True,
) -> None:
    """Append one line to `staffauditlog`. Never rewrites an existing line.

    `section` and `action` are checked against the closed vocabularies in
    `labels`: a typo in a string literal is a row no filter will ever find, and
    the check costs one tuple lookup. A caller with more work to commit passes
    `commit=False`, so the line lands in the same transaction as the change it
    describes - an audit that can be committed without its change is worse than
    no audit at all.
    """
    if section not in labels.AUDIT_SECTIONS:
        raise ValueError(f"Unknown audit section {section!r}.")
    if action not in labels.AUDIT_ACTIONS:
        raise ValueError(f"Unknown audit action {action!r}.")

    session.add(
        StaffAuditLog(
            employee_id=employee_id,
            section=section,
            action=action,
            row_id=row_id,
            summary=summary,
            changed_by_user_id=user.id if user is not None else None,
        )
    )
    if commit:
        session.commit()


# --- documents -------------------------------------------------------------


def document_reads(session: Session, employee_id: UUID) -> list[DocumentRead]:
    """The drawer's Documents list - uploader/verifier names in one extra query.

    `storage_key` is deliberately absent from the answer: the drawer addresses a
    file by its row id and the download route resolves the path itself, so a
    client can never compose a path of its own.
    """
    rows = repository.documents(session, employee_id)
    names = repository.recorder_names(
        session,
        [row.uploaded_by_user_id for row in rows]
        + [row.verified_by_user_id for row in rows],
    )
    return [
        DocumentRead(
            id=row.id,
            doc_type=row.doc_type,
            doc_type_label=labels.DOC_TYPE_LABELS.get(row.doc_type, "Document"),
            title=row.title,
            file_name=row.file_name,
            content_type=row.content_type,
            size_bytes=row.size_bytes,
            verified_on=row.verified_on,
            verified_by=(
                names.get(row.verified_by_user_id)
                if row.verified_by_user_id is not None
                else None
            ),
            uploaded_by=(
                names.get(row.uploaded_by_user_id)
                if row.uploaded_by_user_id is not None
                else None
            ),
            created_at=row.created_at,
        )
        for row in rows
    ]


def one_document(session: Session, employee_id: UUID, row_id: UUID) -> DocumentRead:
    """The single row a write answers with, in the same shape the list uses."""
    for read in document_reads(session, employee_id):
        if read.id == row_id:
            return read
    raise HTTPException(status_code=404, detail="Document not found")


def attach_document(
    session: Session,
    employee: Employee,
    *,
    doc_type: str,
    title: str | None,
    file,
    user: User | None,
) -> DocumentRead:
    """File one document: row and bytes, or neither.

    The duplicate check runs **before** anything is written, so a `409` leaves no
    orphan file; and a failed commit removes the file it just wrote, because a
    dossier folder is not a place to keep papers the list cannot show. `doc_type`
    is checked against the closed vocabulary here rather than trusted - the
    request body is the one place a word outside `labels.DOC_TYPES` can enter.
    """
    if doc_type not in labels.DOC_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown document type '{doc_type}'. "
            f"Expected one of: {', '.join(labels.DOC_TYPES)}",
        )

    file_name = (getattr(file, "filename", None) or "").strip()
    if repository.same_document(
        session, employee_id=employee.id, doc_type=doc_type, file_name=file_name
    ):
        raise HTTPException(
            status_code=409,
            detail=f"This profile already holds '{file_name}' as a {doc_type}.",
        )

    storage_key, content_type, size = documents.save(
        school_id=employee.school_id, employee_id=employee.id, file=file
    )
    row = StaffDocument(
        employee_id=employee.id,
        doc_type=doc_type,
        title=(title or "").strip() or None,
        file_name=file_name,
        storage_key=storage_key,
        content_type=content_type,
        size_bytes=size,
        uploaded_by_user_id=user.id if user is not None else None,
    )
    try:
        session.add(row)
        session.commit()
        session.refresh(row)
    except Exception:
        documents.remove(
            storage_key, school_id=employee.school_id, employee_id=employee.id
        )
        raise

    record_audit(
        session,
        employee_id=employee.id,
        section="document",
        action="uploaded",
        row_id=row.id,
        summary=(
            f"Uploaded {labels.DOC_TYPE_LABELS.get(doc_type, doc_type)}: {file_name}"
        ),
        user=user,
    )
    return one_document(session, employee.id, row.id)


def verify_document(
    session: Session,
    employee: Employee,
    row_id: UUID,
    *,
    verified: bool,
    note: str | None,
    user: User | None,
) -> DocumentRead:
    """Record that somebody saw the original - or take that back.

    "Verified" is a date and a person, never a status word: un-verifying writes
    NULLs and its own audit line, exactly as verifying does, so the column cannot
    disagree with itself after a re-scan.

    **Not your own document.** Verification means the school saw the original, and
    the point of it is four eyes: the principal's own Aadhaar is verified by the
    school administrator, not by the principal. That is the one write on a profile
    that refuses the person themselves.
    """
    if user is not None and employee.user_id == user.id:
        raise HTTPException(
            status_code=403,
            detail="A document is verified by somebody else, not by the person it belongs to.",
        )

    row = repository.document(session, employee_id=employee.id, row_id=row_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Document not found")

    row.verified_on = date.today() if verified else None
    row.verified_by_user_id = (
        (user.id if user is not None else None) if verified else None
    )
    if note is not None:
        row.note = note.strip() or None
    session.add(row)
    session.commit()

    record_audit(
        session,
        employee_id=employee.id,
        section="document",
        action="verified",
        row_id=row.id,
        summary=(
            f"{'Verified' if verified else 'Un-verified'} "
            f"{labels.DOC_TYPE_LABELS.get(row.doc_type, row.doc_type)}: {row.file_name}"
        ),
        user=user,
    )
    return one_document(session, employee.id, row.id)


def document_file(
    session: Session, employee: Employee, row_id: UUID, user: User | None
) -> tuple[Path, StaffDocument]:
    """The stored file for one document, plus the row the route names it with.

    Opening a signed scan **is** an access event, so it is audited: "who opened
    this Aadhaar" is the question a dossier trail exists to answer. The path is
    rebuilt from the stored key and re-checked to be inside this employee's folder
    before anything is opened.
    """
    row = repository.document(session, employee_id=employee.id, row_id=row_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Document not found")

    path = documents.path_of(
        row.storage_key, school_id=employee.school_id, employee_id=employee.id
    )
    record_audit(
        session,
        employee_id=employee.id,
        section="document",
        action="downloaded",
        row_id=row.id,
        summary=f"Downloaded {row.file_name}",
        user=user,
    )
    return path, row


def remove_document(
    session: Session, employee: Employee, row_id: UUID, user: User | None
) -> None:
    """Delete the row and the file. The audit line keeps the story.

    The file goes first, and a missing file is **not** an error (a backup restored
    from before the upload, a volume that never had it): the row is the record, and
    refusing to delete a row because its bytes are gone would leave a document
    nobody can open and nobody can remove.
    """
    row = repository.document(session, employee_id=employee.id, row_id=row_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Document not found")

    file_name, doc_type = row.file_name, row.doc_type
    documents.remove(
        row.storage_key, school_id=employee.school_id, employee_id=employee.id
    )
    session.delete(row)
    session.commit()

    record_audit(
        session,
        employee_id=employee.id,
        section="document",
        action="deleted",
        row_id=row_id,
        summary=(
            f"Deleted {labels.DOC_TYPE_LABELS.get(doc_type, doc_type)}: {file_name}"
        ),
        user=user,
    )


# --- KYC (Aadhaar / PAN / bank) --------------------------------------------


def kyc_read(
    session: Session, employee: Employee, user: User | None, *, reveal: bool
) -> KycRead:
    """The three sensitive fields, masked unless this caller asked **and** may.

    Two independent gates on purpose: the right (`teachers.view_kyc`) and the
    request (`reveal`). One gate would mean every screen that opens a profile
    prints a full Aadhaar because somebody happened to hold the right; two mean
    the reveal is a deliberate act - and a deliberate act is worth writing to the
    audit trail, which is what happens here.

    `ifsc` and the bank's name are not masked: they identify a branch, not an
    account, and payroll cannot pay without them.
    """
    allowed = scope.may_view_kyc(session, user)
    if reveal and not allowed:
        raise HTTPException(
            status_code=403,
            detail="Your role may not view full Aadhaar, PAN or bank numbers.",
        )

    unmasked = reveal and allowed
    if unmasked:
        record_audit(
            session,
            employee_id=employee.id,
            section="kyc",
            action="revealed",
            summary="Aadhaar, PAN and bank account shown in full",
            user=user,
        )

    return KycRead(
        aadhaar_no=(
            employee.aadhaar_no
            if unmasked
            else labels.mask_aadhaar(employee.aadhaar_no)
        ),
        pan_no=employee.pan_no if unmasked else labels.mask_pan(employee.pan_no),
        bank_name=employee.bank_name,
        bank_account_no=(
            employee.bank_account_no
            if unmasked
            else labels.mask_account(employee.bank_account_no)
        ),
        ifsc=employee.ifsc,
        masked=not unmasked,
        can_reveal=allowed,
    )
