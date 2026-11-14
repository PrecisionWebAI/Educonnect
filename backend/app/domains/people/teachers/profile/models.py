"""The parts of a staff profile that are a list, not a column.

`employee` holds what is true of a person **today**: their department, their
designation, the date they joined. A profile also holds what *accumulated* - three
degrees, two past employers, certificates that expire, and the events that explain
a seniority claim years later. Those are four tables rather than forty columns,
because a teacher can hold four qualifications and one person can be re-hired.

Every table here is school-owned (`TenantMixin`), so a profile can never be read
across schools, and none of them stores a file: documents arrive in Phase 3 in
`staffdocument`, where the size, extension and folder rules live in one place.

`staffemploymenthistory` is **append-only** by design. It is the record of what
happened - joined, promoted, transferred, designation changed, left - and the API
has no endpoint that rewrites or deletes a row. A mistake is corrected by adding
the correction, the way a ledger is corrected.
"""

from datetime import date, datetime
from uuid import UUID

from sqlmodel import Field, SQLModel

from app.core.ids import UUIDMixin
from app.core.tenancy import TenantMixin
from app.domains.auth.models import utcnow


class StaffQualificationBase(SQLModel):
    """One degree or diploma the school has seen evidence for.

    `institution` and `year_completed` are optional because an office often
    records the degree first and fills the rest in later; a mandatory column here
    would push people to type a placeholder ("N/A") that later reads as fact.
    """

    employee_id: UUID = Field(foreign_key="employee.id", index=True)
    degree: str
    institution: str | None = None
    year_completed: int | None = None
    grade: str | None = None


class StaffQualification(StaffQualificationBase, TenantMixin, UUIDMixin, table=True):
    """No `UNIQUE(employee_id, degree, year_completed)` on purpose.

    PostgreSQL treats two NULL years as different values, so the constraint would
    let the duplicate straight through; the duplicate check therefore lives in
    `service.add_qualification`, which answers `409` with the pair it found.
    """

    created_at: datetime = Field(default_factory=utcnow)


class StaffExperienceBase(SQLModel):
    """One earlier job. `to_date` NULL means "still here" - i.e. the current post."""

    employee_id: UUID = Field(foreign_key="employee.id", index=True)
    employer: str
    designation: str | None = None
    from_date: date
    to_date: date | None = None
    note: str | None = None


class StaffExperience(StaffExperienceBase, TenantMixin, UUIDMixin, table=True):
    created_at: datetime = Field(default_factory=utcnow)


class StaffCertificationBase(SQLModel):
    """A certificate, licence or training the person holds.

    `valid_till` is what makes this table worth having: a first-aid certificate
    that expired is a fact the principal needs, and it is a date, not a status
    somebody has to remember to change.
    """

    employee_id: UUID = Field(foreign_key="employee.id", index=True)
    name: str
    issuer: str | None = None
    issued_on: date | None = None
    valid_till: date | None = None
    #: The number on the certificate. Kept as typed - a certificate id is read
    #: aloud to a verifier, so it is not canonicalised.
    reference_no: str | None = None


class StaffCertification(StaffCertificationBase, TenantMixin, UUIDMixin, table=True):
    created_at: datetime = Field(default_factory=utcnow)


class StaffEmploymentHistoryBase(SQLModel):
    """One thing that happened to this employment, and when.

    `from_value` / `to_value` carry the change itself ("Teacher" -> "Senior
    Teacher"), so the row explains the salary or the seniority without a second
    lookup of a field that has since moved on.
    """

    employee_id: UUID = Field(foreign_key="employee.id", index=True)
    event: str
    effective_on: date
    from_value: str | None = None
    to_value: str | None = None
    note: str | None = None
    #: Who recorded it. NULL when the seed or a migration wrote the row and no
    #: login is to be credited (or blamed) for it.
    recorded_by_user_id: UUID | None = Field(default=None, foreign_key="app_user.id")


class StaffEmploymentHistory(
    StaffEmploymentHistoryBase, TenantMixin, UUIDMixin, table=True
):
    created_at: datetime = Field(default_factory=utcnow)
