"""Staff documents, KYC masking and the audit trail - the rules, not the pixels.

Every test here is a rule that is invisible in the browser when it is wrong:

* a document's bytes and its row are written **together** - a refused upload
  leaves no orphan file;
* the storage key never reaches a response, and a tampered key resolves to
  nothing (a user-supplied path opened as-is is an arbitrary file read);
* another employee's row id is `404` - not `403`, because an API must not confirm
  that an id exists elsewhere;
* Aadhaar / PAN / bank are **masked** in every profile read, and the full value
  needs the right *and* the request - and that reveal is written down;
* the audit trail is append-only, newest first, and a teacher cannot read it.

Runs on in-memory SQLite like `test_staff_profile.py`, with `UPLOAD_DIR` pointed
at a temporary folder so nothing is written into the repository.
"""

import importlib
import io
from datetime import date
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.config import settings
from app.core.schema import MODEL_MODULES
from app.domains.admin.platform.models import School
from app.domains.admin.users.models import User
from app.domains.auth.models import Role
from app.domains.auth.roles import grant_role
from app.domains.people.staff.models import Employee
from app.domains.people.teachers import labels, scope
from app.domains.people.teachers import service as teachers
from app.domains.people.teachers.models import StaffAuditLog, StaffDocument
from app.domains.people.teachers.profile import service as profile


class _Upload:
    """The three attributes `attach_document` reads off an `UploadFile`."""

    def __init__(
        self,
        filename: str,
        data: bytes = b"%PDF-1.4 test",
        content_type: str = "application/pdf",
    ):
        self.filename = filename
        self.file = io.BytesIO(data)
        self.content_type = content_type


def engine():
    for domain in MODEL_MODULES:
        importlib.import_module(f"app.domains.{domain}.models")
    created = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(created)
    return created


def session_for(created, school_id=None):
    session = Session(created, expire_on_commit=False)
    if school_id is not None:
        session.info["school_id"] = school_id
    return session


def _roles(session: Session) -> None:
    for codename, label in (
        ("principal", "Principal"),
        ("teacher", "Teacher"),
        ("hod", "Head of Department"),
        ("school_admin", "School Administrator"),
    ):
        session.add(Role(codename=codename, label=label))
    session.commit()


def _user(session: Session, name: str, school_id, roles: tuple[str, ...]) -> User:
    user = User(
        email=f"{name.lower().replace(' ', '.')}@test",
        full_name=name,
        hashed_password="x",
        school_id=school_id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    for codename in roles:
        grant_role(session, user, codename)
    return user


def _employee(session: Session, user: User, code: str, **extra) -> Employee:
    employee = Employee(
        user_id=user.id,
        employee_code=code,
        department=extra.pop("department", "Science"),
        joining_date=extra.pop("joining_date", date(2023, 6, 1)),
        email=f"{code.lower()}@test",
        **extra,
    )
    session.add(employee)
    session.commit()
    session.refresh(employee)
    return employee


def _person(
    session: Session, school_id, code: str, *, name=None, roles=("teacher",), **extra
):
    """A login **and** its employee row.

    `employee.user_id` is unique, so two staff records need two logins: a test that
    wants a colleague has to make a person, not a second row on the same account.
    """
    user = _user(session, name or f"Staff {code}", school_id, roles)
    return user, _employee(session, user, code, **extra)


@pytest.fixture()
def school_session(monkeypatch, tmp_path):
    """A school, its roles, and `UPLOAD_DIR` pointed at a temporary folder."""
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    created = engine()
    school = School(
        name="Test School",
        code="TST-0001",
        email="office@test.school",
        phone="9999999999",
        address="1 Test Road",
    )
    session = session_for(created)
    session.add(school)
    session.commit()
    _roles(session)
    session.info["school_id"] = school.id
    return session, school, tmp_path


# --- the masks -------------------------------------------------------------


def test_masks_keep_only_the_telling_part():
    """Aadhaar, PAN and the account keep their last characters and nothing else."""
    assert labels.mask_aadhaar("1234 5678 9012") == "XXXX XXXX 9012"
    assert labels.mask_pan("abcde1234f") == "XXXXX1234F"
    assert labels.mask_account("50100123456789") == "XXXX 6789"
    # A value shorter than the visible tail does not leak itself.
    assert labels.mask_aadhaar("123") == "XXX"
    assert labels.mask_account("12") == "XX"
    # Nothing recorded is None, not a row of Xs.
    assert labels.mask_aadhaar(None) is None
    assert labels.mask_pan("") is None


# --- documents -------------------------------------------------------------


def test_upload_files_the_bytes_under_the_employees_own_folder(school_session):
    """The file lands in `staff-docs/<school>/<employee>/` and the read hides the key."""
    session, school, root = school_session
    user = _user(session, "Prashant Saxena", school.id, ("principal",))
    employee = _employee(session, user, "EMP-0001")

    read = profile.attach_document(
        session,
        employee,
        doc_type="aadhaar",
        title="Front side",
        file=_Upload("aadhaar.pdf"),
        user=user,
    )

    assert read.doc_type == "aadhaar"
    assert read.doc_type_label == "Aadhaar Card"
    # The response carries no path and no key: only the row's own fields.
    assert not hasattr(read, "storage_key")
    assert "staff-docs" not in read.model_dump_json()

    stored = list((root / "staff-docs" / str(school.id) / str(employee.id)).iterdir())
    assert len(stored) == 1
    assert stored[0].suffix == ".pdf"

    row = session.exec(select(StaffDocument)).one()
    # A **relative** key, and the file is exactly where the key says it is.
    assert row.storage_key == f"staff-docs/{school.id}/{employee.id}/{stored[0].name}"
    assert not Path(row.storage_key).is_absolute()


def test_upload_refuses_a_file_that_is_not_a_document(school_session):
    session, school, root = school_session
    user = _user(session, "Prashant Saxena", school.id, ("principal",))
    employee = _employee(session, user, "EMP-0002")

    with pytest.raises(HTTPException) as refused:
        profile.attach_document(
            session,
            employee,
            doc_type="other",
            title=None,
            file=_Upload("payload.exe", b"MZ"),
            user=user,
        )
    assert refused.value.status_code == 422
    assert "PDF" in refused.value.detail
    # Nothing was written: the refusal happened before the disk was touched.
    assert not (root / "staff-docs").exists()


def test_upload_refuses_an_oversized_file(school_session, monkeypatch):
    monkeypatch.setattr(settings, "UPLOAD_MAX_MB", 1)
    session, school, _root = school_session
    user = _user(session, "Prashant Saxena", school.id, ("principal",))
    employee = _employee(session, user, "EMP-0003")

    with pytest.raises(HTTPException) as refused:
        profile.attach_document(
            session,
            employee,
            doc_type="degree",
            title=None,
            file=_Upload("degree.pdf", b"x" * (2 * 1024 * 1024)),
            user=user,
        )
    assert refused.value.status_code == 413
    assert "1 MB" in refused.value.detail


def test_the_same_file_is_not_filed_twice(school_session):
    """`UNIQUE(employee, type, name)` answered as a `409` naming the file."""
    session, school, root = school_session
    user = _user(session, "Prashant Saxena", school.id, ("principal",))
    employee = _employee(session, user, "EMP-0004")

    profile.attach_document(
        session,
        employee,
        doc_type="pan",
        title=None,
        file=_Upload("pan.pdf"),
        user=user,
    )
    before = len(list((root / "staff-docs").rglob("*.pdf")))

    with pytest.raises(HTTPException) as refused:
        profile.attach_document(
            session,
            employee,
            doc_type="pan",
            title=None,
            file=_Upload("pan.pdf"),
            user=user,
        )
    assert refused.value.status_code == 409
    assert "pan.pdf" in refused.value.detail
    # Refused **before** the second file was written: no orphan on disk.
    assert len(list((root / "staff-docs").rglob("*.pdf"))) == before


def test_download_resolves_a_tampered_key_to_nothing(school_session):
    """A key that walks out of the folder is a `404`, not a file read."""
    session, school, _root = school_session
    user = _user(session, "Prashant Saxena", school.id, ("principal",))
    employee = _employee(session, user, "EMP-0005")

    read = profile.attach_document(
        session,
        employee,
        doc_type="degree",
        title=None,
        file=_Upload("degree.pdf"),
        user=user,
    )

    row = session.get(StaffDocument, read.id)
    row.storage_key = "../../../../../etc/passwd"
    session.add(row)
    session.commit()

    with pytest.raises(HTTPException) as refused:
        profile.document_file(session, employee, read.id, user)
    assert refused.value.status_code == 404


def test_a_rows_id_from_another_profile_is_a_404(school_session):
    """The row is looked up **within** the employee in the path."""
    session, school, _root = school_session
    principal = _user(session, "Prashant Saxena", school.id, ("principal",))
    mine = _employee(session, principal, "EMP-0006")
    _colleague_user, colleague = _person(
        session, school.id, "EMP-0007", name="Colleague Two"
    )

    read = profile.attach_document(
        session,
        mine,
        doc_type="contract",
        title=None,
        file=_Upload("contract.pdf"),
        user=principal,
    )

    with pytest.raises(HTTPException) as refused:
        profile.document_file(session, colleague, read.id, principal)
    assert refused.value.status_code == 404


def test_delete_removes_the_row_and_the_file(school_session):
    """A deleted document leaves neither a row nor bytes; the audit line stays."""
    session, school, root = school_session
    user = _user(session, "Prashant Saxena", school.id, ("principal",))
    employee = _employee(session, user, "EMP-0008")

    read = profile.attach_document(
        session,
        employee,
        doc_type="medical",
        title=None,
        file=_Upload("fit.pdf"),
        user=user,
    )
    files = list((root / "staff-docs").rglob("*.pdf"))
    assert len(files) == 1

    profile.remove_document(session, employee, read.id, user)

    assert session.get(StaffDocument, read.id) is None
    assert not files[0].exists()
    lines = session.exec(select(StaffAuditLog)).all()
    assert any(line.action == "deleted" and line.row_id == read.id for line in lines)

    with pytest.raises(HTTPException) as refused:
        profile.remove_document(session, employee, read.id, user)
    assert refused.value.status_code == 404


def test_documents_are_listed_alphabetically_by_type(school_session):
    """A drawer is a filing cabinet: the list is ordered by type, then name."""
    session, school, _root = school_session
    user = _user(session, "Prashant Saxena", school.id, ("principal",))
    employee = _employee(session, user, "EMP-0009")

    for name, doc_type in (("pan.pdf", "pan"), ("aadhaar.pdf", "aadhaar")):
        profile.attach_document(
            session,
            employee,
            doc_type=doc_type,
            title=None,
            file=_Upload(name),
            user=user,
        )

    listed = [read.doc_type for read in profile.document_reads(session, employee.id)]
    assert listed == sorted(listed) == ["aadhaar", "pan"]


# --- who may do what -------------------------------------------------------


def test_a_teacher_may_file_their_own_papers_but_not_a_colleagues(school_session):
    """The matrix's "own docs only" row, enforced on the server."""
    session, school, _root = school_session
    me = _user(session, "Teacher One", school.id, ("teacher",))
    mine = _employee(session, me, "EMP-0010")
    _other_user, other = _person(session, school.id, "EMP-0011", name="Teacher Two")

    assert scope.may_upload_documents(session, me, mine) is True
    assert scope.may_upload_documents(session, me, other) is False
    # ... and a teacher is not an editor of a profile either.
    assert scope.may_edit_profile(session, me, mine) is False


def test_an_hod_files_inside_the_department_and_never_verifies_their_own(
    school_session,
):
    """`require_edit` is the verify/delete gate: HOD in scope, self is not scope."""
    session, school, _root = school_session
    hod = _user(session, "Head Of Department", school.id, ("hod",))
    hod_employee = _employee(session, hod, "EMP-0012", department="Science")
    _c, colleague = _person(session, school.id, "EMP-0013", name="Science Teacher")
    _o, outsider = _person(
        session, school.id, "EMP-0014", name="Commerce Teacher", department="Commerce"
    )

    assert scope.may_upload_documents(session, hod, colleague) is True
    assert scope.may_upload_documents(session, hod, outsider) is False
    profile.require_edit(session, colleague, hod)
    # ... but nobody verifies a document that belongs to themselves: the control
    # is four eyes (the principal's own Aadhaar is checked by the school admin).
    with pytest.raises(HTTPException) as refused:
        profile.verify_document(
            session,
            hod_employee,
            uuid4(),
            verified=True,
            note=None,
            user=hod,
        )
    assert refused.value.status_code == 403


def test_a_leaver_is_read_only_for_documents(school_session):
    """New papers do not go into a record the school has closed."""
    session, school, _root = school_session
    user = _user(session, "Prashant Saxena", school.id, ("principal",))
    leaver = _employee(
        session,
        user,
        "EMP-0015",
        department="Science",
        deactivated_at=date(2026, 3, 31),
    )

    with pytest.raises(HTTPException) as refused:
        profile.require_upload(session, leaver, user)
    assert refused.value.status_code == 409
    assert "Reactivate" in refused.value.detail


# --- KYC -------------------------------------------------------------------


def _with_kyc(session: Session, user: User, code: str) -> Employee:
    return _employee(
        session,
        user,
        code,
        aadhaar_no="123456789012",
        pan_no="ABCDE1234F",
        bank_name="State Bank",
        bank_account_no="50100123456789",
        ifsc="SBIN0001234",
    )


def test_kyc_is_masked_even_for_the_office_by_default(school_session):
    """Masked is the default answer; `can_reveal` says whether asking would work."""
    session, school, _root = school_session
    principal = _user(session, "Prashant Saxena", school.id, ("principal",))
    employee = _with_kyc(session, principal, "EMP-0016")

    masked = profile.kyc_read(session, employee, principal, reveal=False)
    assert masked.masked is True
    assert masked.aadhaar_no == "XXXX XXXX 9012"
    assert masked.pan_no == "XXXXX1234F"
    assert masked.bank_account_no == "XXXX 6789"
    # The bank's name and the branch code are not secrets: payroll needs them.
    assert masked.bank_name == "State Bank"
    assert masked.ifsc == "SBIN0001234"
    assert masked.can_reveal is True


def test_kyc_reveal_needs_the_right_and_a_revealed_read_is_audited(school_session):
    """A HOD is refused; the principal gets the number **and** an audit line."""
    session, school, _root = school_session
    principal = _user(session, "Prashant Saxena", school.id, ("principal",))
    employee = _with_kyc(session, principal, "EMP-0017")
    hod = _user(session, "Head Of Department", school.id, ("hod",))

    with pytest.raises(HTTPException) as refused:
        profile.kyc_read(session, employee, hod, reveal=True)
    assert refused.value.status_code == 403

    full = profile.kyc_read(session, employee, principal, reveal=True)
    assert full.masked is False
    assert full.aadhaar_no == "123456789012"
    assert full.bank_account_no == "50100123456789"

    lines = session.exec(select(StaffAuditLog)).all()
    assert any(line.section == "kyc" and line.action == "revealed" for line in lines)


def test_a_hod_reads_the_profile_without_ever_seeing_the_number(school_session):
    """The HOD's ordinary read is masked *and* says it cannot be unmasked."""
    session, school, _root = school_session
    principal = _user(session, "Prashant Saxena", school.id, ("principal",))
    employee = _with_kyc(session, principal, "EMP-0018")
    hod = _user(session, "Head Of Department", school.id, ("hod",))

    read = profile.kyc_read(session, employee, hod, reveal=False)
    assert read.masked is True
    assert read.can_reveal is False
    assert read.aadhaar_no == "XXXX XXXX 9012"


def test_verify_records_the_day_and_the_person(school_session):
    """A verified document carries the date and who checked it - not a status word."""
    session, school, _root = school_session
    office = _user(session, "Prashant Saxena", school.id, ("principal",))
    _teacher_user, teacher = _person(
        session, school.id, "EMP-0023", name="Teacher Three"
    )

    read = profile.attach_document(
        session,
        teacher,
        doc_type="degree",
        title=None,
        file=_Upload("degree.pdf"),
        user=office,
    )
    verified = profile.verify_document(
        session, teacher, read.id, verified=True, note=None, user=office
    )

    assert verified.verified_on is not None
    assert verified.verified_by == "Prashant Saxena"

    # Taking it back is the same write in the other direction, and it is audited.
    taken_back = profile.verify_document(
        session, teacher, read.id, verified=False, note=None, user=office
    )
    assert taken_back.verified_on is None
    assert taken_back.verified_by is None


# --- the audit trail -------------------------------------------------------


def test_the_audit_feed_is_newest_first_and_can_be_narrowed(school_session):
    """Two writes make two lines; the feed reads from the top, per person."""
    session, school, _root = school_session
    principal = _user(session, "Prashant Saxena", school.id, ("principal",))
    mine = _employee(session, principal, "EMP-0019")
    _other_user, other = _person(session, school.id, "EMP-0020", name="Second Person")

    profile.record_audit(
        session,
        employee_id=mine.id,
        section="qualification",
        action="created",
        summary="Added B.Ed",
        user=principal,
    )
    profile.record_audit(
        session,
        employee_id=other.id,
        section="document",
        action="uploaded",
        summary="Uploaded Aadhaar Card: aadhaar.pdf",
        user=principal,
    )

    feed = teachers.staff_audit(session)
    assert [line.section for line in feed] == ["document", "qualification"]
    assert feed[1].employee_name == "Prashant Saxena"
    assert feed[1].changed_by == "Prashant Saxena"

    narrowed = teachers.staff_audit(session, employee_id=mine.id)
    assert [line.summary for line in narrowed] == ["Added B.Ed"]


def test_the_audit_trail_refuses_a_word_outside_the_vocabulary(school_session):
    """A typo in a section is a row no filter would ever find - so it raises."""
    session, school, _root = school_session
    principal = _user(session, "Prashant Saxena", school.id, ("principal",))
    employee = _employee(session, principal, "EMP-0021")

    with pytest.raises(ValueError):
        profile.record_audit(
            session,
            employee_id=employee.id,
            section="qualifications",  # plural: not in `labels.AUDIT_SECTIONS`
            action="created",
            summary="Added B.Ed",
            user=principal,
        )


def test_a_document_download_writes_a_line(school_session):
    """Opening a signed scan is an access event - the trail has to say who."""
    session, school, _root = school_session
    principal = _user(session, "Prashant Saxena", school.id, ("principal",))
    employee = _employee(session, principal, "EMP-0022")

    read = profile.attach_document(
        session,
        employee,
        doc_type="aadhaar",
        title=None,
        file=_Upload("aadhaar.pdf"),
        user=principal,
    )
    profile.document_file(session, employee, read.id, principal)

    actions = [
        line.action
        for line in session.exec(
            select(StaffAuditLog).where(StaffAuditLog.section == "document")
        ).all()
    ]
    assert "uploaded" in actions
    assert "downloaded" in actions
