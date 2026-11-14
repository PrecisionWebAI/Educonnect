from datetime import date, datetime
from uuid import UUID

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.ids import UUIDMixin
from app.core.tenancy import TenantMixin
from app.domains.auth.models import utcnow


class TeacherSubjectBase(SQLModel):
    """One subject a teacher can teach - many rows per teacher.

    This is the teacher's own subject list (what the hire form collects), not
    *where* they teach: who actually takes a subject in a class-section is
    `academics.SubjectTeacher`, and who runs a section is
    `academics.Section.class_teacher_id`. Keeping the three apart means a teacher
    can be listed against five subjects before any class has been assigned to them.
    """

    teacher_id: UUID = Field(foreign_key="employee.id")
    subject_id: UUID = Field(foreign_key="subject.id")


class TeacherSubject(TeacherSubjectBase, TenantMixin, UUIDMixin, table=True):
    """`UNIQUE(teacher_id, subject_id)` - the same subject is not listed twice."""

    __table_args__ = (
        UniqueConstraint(
            "teacher_id", "subject_id", name="uq_teachersubject_teacher_subject"
        ),
    )


class TeacherReviewBase(SQLModel):
    """A single anonymous review/rating of a teacher (Tab 9.4 — Performance & Review).

    The screen shows a per-teacher summary (average star rating, review count,
    trend, score), so we store the individual ratings and aggregate them rather
    than keeping a denormalised snapshot. `reviewer_role` records who left the
    rating (\"Parent\" / \"Principal\" / \"HOD\") without storing their identity,
    which is what \"anonymous ratings\" means in the blueprint.
    """

    teacher_id: UUID = Field(foreign_key="employee.id")
    rating: int = Field(ge=1, le=5)
    reviewer_role: str = Field(default="Parent")
    comment: str | None = None


class TeacherReview(TeacherReviewBase, TenantMixin, UUIDMixin, table=True):
    created_at: datetime = Field(default_factory=datetime.utcnow)


class StaffDocumentBase(SQLModel):
    """One file the school keeps about a person - a scan, a certificate, a contract.

    The **file is not in the database**. `storage_key` is a relative path under
    `settings.UPLOAD_DIR` (`staff-docs/<school_id>/<employee_id>/<uuid>.pdf`), and
    it is the only thing written down. Three consequences, each the reason for
    this shape rather than a `bytes` column:

    * a dossier folder can be moved, copied or re-mounted without rewriting rows;
    * no response can leak the server's filesystem layout (the absolute path never
      exists to be serialised);
    * a school's documents sit in that school's own folder, so a mis-scoped query
      cannot serve a signed scan across the tenant boundary - and the download
      route re-checks the resolved path against the employee's folder anyway.

    `file_name` keeps what the file was called when it was uploaded: that is what
    a download has to be named, and it is a fact about the document, not about
    where it happens to live. `doc_type` is the closed vocabulary in
    `labels.DOC_TYPES` - an Aadhaar scan and a degree certificate are different
    asks, and the verification rule differs.
    """

    employee_id: UUID = Field(foreign_key="employee.id", index=True)
    doc_type: str
    #: Free text the office adds to tell two degree scans apart.
    title: str | None = None
    file_name: str
    #: Relative to `settings.UPLOAD_DIR`. Never an absolute path, never in a read.
    storage_key: str
    content_type: str | None = None
    size_bytes: int = 0
    uploaded_by_user_id: UUID | None = Field(default=None, foreign_key="app_user.id")
    #: `verified_on` is NULL until somebody with `teachers.update` has seen the
    #: original. It is a date, not a status: a status is a word to remember to
    #: change, a date cannot go stale silently.
    verified_on: date | None = None
    verified_by_user_id: UUID | None = Field(default=None, foreign_key="app_user.id")
    note: str | None = None


class StaffDocument(StaffDocumentBase, TenantMixin, UUIDMixin, table=True):
    """`UNIQUE(employee_id, doc_type, file_name)` - the same scan is not filed twice.

    Two scans of the same Aadhaar under different names are allowed on purpose
    (front and back are the same document type); an identical re-upload is
    refused, because it is the same file and a second row would only hide which
    one is current.
    """

    __table_args__ = (
        UniqueConstraint(
            "employee_id",
            "doc_type",
            "file_name",
            name="uq_staffdocument_employee_type_name",
        ),
    )
    created_at: datetime = Field(default_factory=utcnow)


class StaffAuditLogBase(SQLModel):
    """Who changed what on a profile, and when - append-only.

    A qualification the office edits a year after joining is the fact a
    disciplinary or a promotion argument turns on, and `staffemploymenthistory`
    only covers the post itself. This table covers everything else: a document
    verified, an Aadhaar unmasked, a certification deleted.

    `summary` is written in words a person reads ("Designation: Teacher ->
    Senior Teacher") rather than as a diff of column names, because the reader is
    an auditor with the drawer open, not a script. `row_id` points at the row that
    changed so a future screen can follow the thread after the row itself is gone.

    Append-only by policy: there is no endpoint that updates or deletes a row, the
    way `staffemploymenthistory` is corrected by adding the next event.
    """

    employee_id: UUID = Field(foreign_key="employee.id", index=True)
    #: `employment` / `subjects` / `qualification` / `experience` /
    #: `certification` / `document` / `kyc` - `labels.AUDIT_SECTIONS`.
    section: str
    #: `created` / `updated` / `deleted` / `uploaded` / `verified` / `downloaded`
    #: / `revealed` - `labels.AUDIT_ACTIONS`.
    action: str
    row_id: UUID | None = None
    summary: str
    #: NULL when no login is to be credited (a migration, the seed).
    changed_by_user_id: UUID | None = Field(default=None, foreign_key="app_user.id")


class StaffAuditLog(StaffAuditLogBase, TenantMixin, UUIDMixin, table=True):
    created_at: datetime = Field(default_factory=utcnow)
