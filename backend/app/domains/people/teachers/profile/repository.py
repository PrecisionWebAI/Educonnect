"""Reads and lookups for the profile's four lists.

Every statement is scoped **by `employee_id`**, not only by row id: the path is
`/teachers/profile/{employee_id}/qualifications/{row_id}`, and looking the row up
by its id alone would let a caller who may edit employee A delete a row that
happens to belong to employee B. The tenant listener then narrows both to the
session's school, so a cross-school id finds nothing (`404`).
"""

from uuid import UUID

from sqlmodel import Session, select

from app.domains.admin.users.models import User
from app.domains.people.staff.models import Employee

from ..models import StaffAuditLog, StaffDocument
from .models import (
    StaffCertification,
    StaffEmploymentHistory,
    StaffExperience,
    StaffQualification,
)


def qualifications(session: Session, employee_id: UUID) -> list[StaffQualification]:
    """Newest first; a row with no year sorts last rather than first.

    `nullslast()` is explicit because PostgreSQL and SQLite disagree about where
    NULLs go in a DESC order, and the drawer's order must not depend on the
    database that happens to serve the request.
    """
    return list(
        session.exec(
            select(StaffQualification)
            .where(StaffQualification.employee_id == employee_id)
            .order_by(
                StaffQualification.year_completed.desc().nullslast(),
                StaffQualification.degree,
            )
        ).all()
    )


def experiences(session: Session, employee_id: UUID) -> list[StaffExperience]:
    """Most recent first; a job with no end date is the one still held."""
    return list(
        session.exec(
            select(StaffExperience)
            .where(StaffExperience.employee_id == employee_id)
            .order_by(
                StaffExperience.from_date.desc(),
                StaffExperience.employer,
            )
        ).all()
    )


def certifications(session: Session, employee_id: UUID) -> list[StaffCertification]:
    """Longest-lived first, undated ones last."""
    return list(
        session.exec(
            select(StaffCertification)
            .where(StaffCertification.employee_id == employee_id)
            .order_by(
                StaffCertification.valid_till.desc().nullslast(),
                StaffCertification.name,
            )
        ).all()
    )


def history(session: Session, employee_id: UUID) -> list[StaffEmploymentHistory]:
    """Newest event first - the same order the drawer reads it in."""
    return list(
        session.exec(
            select(StaffEmploymentHistory)
            .where(StaffEmploymentHistory.employee_id == employee_id)
            .order_by(
                StaffEmploymentHistory.effective_on.desc(),
                StaffEmploymentHistory.created_at.desc(),
            )
        ).all()
    )


def recorder_names(session: Session, user_ids: list[UUID]) -> dict[UUID, str]:
    """`{user_id: full_name}` for whoever recorded the events, in one query."""
    wanted = [user_id for user_id in user_ids if user_id is not None]
    if not wanted:
        return {}
    rows = session.exec(
        select(User.id, User.full_name).where(User.id.in_(wanted))
    ).all()
    return dict(rows)


def qualification(
    session: Session, *, employee_id: UUID, row_id: UUID
) -> StaffQualification | None:
    return session.exec(
        select(StaffQualification).where(
            StaffQualification.id == row_id,
            StaffQualification.employee_id == employee_id,
        )
    ).first()


def same_qualification(
    session: Session,
    *,
    employee_id: UUID,
    degree: str,
    year_completed: int | None,
    exclude_id: UUID | None = None,
) -> StaffQualification | None:
    """Is this degree (and year) already on the profile?

    The comparison is on the canonical stored form, so "B.Ed" and "b.ed" are one
    qualification; `exclude_id` keeps an edit from colliding with itself.
    """
    statement = select(StaffQualification).where(
        StaffQualification.employee_id == employee_id,
        StaffQualification.degree == degree,
        StaffQualification.year_completed == year_completed,
    )
    if exclude_id is not None:
        statement = statement.where(StaffQualification.id != exclude_id)
    return session.exec(statement).first()


def experience(
    session: Session, *, employee_id: UUID, row_id: UUID
) -> StaffExperience | None:
    return session.exec(
        select(StaffExperience).where(
            StaffExperience.id == row_id,
            StaffExperience.employee_id == employee_id,
        )
    ).first()


def certification(
    session: Session, *, employee_id: UUID, row_id: UUID
) -> StaffCertification | None:
    return session.exec(
        select(StaffCertification).where(
            StaffCertification.id == row_id,
            StaffCertification.employee_id == employee_id,
        )
    ).first()


def same_certification(
    session: Session,
    *,
    employee_id: UUID,
    name: str,
    issued_on,
    exclude_id: UUID | None = None,
) -> StaffCertification | None:
    """A certificate with the same name and issue date is the same certificate.

    Re-certifying produces a **new** issue date, which is exactly why the date is
    part of the key instead of a rule that hides the renewal.
    """
    statement = select(StaffCertification).where(
        StaffCertification.employee_id == employee_id,
        StaffCertification.name == name,
        StaffCertification.issued_on == issued_on,
    )
    if exclude_id is not None:
        statement = statement.where(StaffCertification.id != exclude_id)
    return session.exec(statement).first()


# --- documents -------------------------------------------------------------


def documents(session: Session, employee_id: UUID) -> list[StaffDocument]:
    """The person's files, **alphabetically by type, then name**.

    A typed order rather than "newest first": a drawer is a filing cabinet, and
    the office looks for "the Aadhaar" by its name, not by the day it was scanned.
    """
    rows = list(
        session.exec(
            select(StaffDocument).where(StaffDocument.employee_id == employee_id)
        ).all()
    )
    return sorted(rows, key=lambda row: (row.doc_type, (row.file_name or "").lower()))


def document(
    session: Session, *, employee_id: UUID, row_id: UUID
) -> StaffDocument | None:
    """One file **within the employee in the path** - the cross-profile guard."""
    return session.exec(
        select(StaffDocument).where(
            StaffDocument.id == row_id,
            StaffDocument.employee_id == employee_id,
        )
    ).first()


def same_document(
    session: Session, *, employee_id: UUID, doc_type: str, file_name: str
) -> StaffDocument | None:
    """The same file filed twice (same type, same name) - a `409`, not a copy."""
    return session.exec(
        select(StaffDocument).where(
            StaffDocument.employee_id == employee_id,
            StaffDocument.doc_type == doc_type,
            StaffDocument.file_name == file_name,
        )
    ).first()


# --- the audit trail -------------------------------------------------------


def audit_rows(
    session: Session,
    *,
    employee_id: UUID | None = None,
    section: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[StaffAuditLog]:
    """Newest first - an audit feed is read from the top.

    Chronology is the one list in this feature that is *not* alphabetical: "what
    happened last" is the question, and a name-ordered audit trail answers a
    question nobody asked.
    """
    statement = select(StaffAuditLog)
    if employee_id is not None:
        statement = statement.where(StaffAuditLog.employee_id == employee_id)
    if section:
        statement = statement.where(StaffAuditLog.section == section)
    return list(
        session.exec(
            statement.order_by(StaffAuditLog.created_at.desc(), StaffAuditLog.id.desc())
            .offset(offset)
            .limit(limit)
        ).all()
    )


def employee_names(session: Session, employee_ids: list[UUID]) -> dict[UUID, str]:
    """`{employee_id: full_name}` in one query, for the audit feed."""
    wanted = [employee_id for employee_id in employee_ids if employee_id is not None]
    if not wanted:
        return {}
    rows = session.exec(
        select(Employee.id, User.full_name)
        .join(User, User.id == Employee.user_id)
        .where(Employee.id.in_(wanted))
    ).all()
    return dict(rows)
