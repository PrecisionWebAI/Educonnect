"""The only writer for a classroom-owned subject.

A subject is identified by the section row itself. Its name is not copied from a
school-wide list and a rename here can never touch another section.
"""

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func
from sqlmodel import Session, select

from app.core.tenancy import tenant_of
from app.domains.academic.classroom.academics.models import Classroom
from app.domains.auth.models import utcnow

from . import completion, scope
from .models import COURSE_ACTIVE, COURSE_ARCHIVED, ClassroomSubject

SUBJECT_NAME_MAX = 120
SUBJECT_CODE_MAX = 20


def normalise_name(value: str | None) -> str:
    """Trim, collapse spaces and lower-case before comparing or storing a name."""
    name = " ".join((value or "").split()).lower()
    if not name:
        raise HTTPException(status_code=422, detail="Type a subject name.")
    if len(name) > SUBJECT_NAME_MAX:
        raise HTTPException(
            status_code=422,
            detail=f"A subject name cannot be longer than {SUBJECT_NAME_MAX} characters.",
        )
    return name


def clean_code(value: str | None) -> str | None:
    code = (value or "").strip().upper()
    if not code:
        return None
    if len(code) > SUBJECT_CODE_MAX:
        raise HTTPException(
            status_code=422,
            detail=f"A subject code cannot be longer than {SUBJECT_CODE_MAX} characters.",
        )
    return code


def require_manage(session: Session, user) -> None:
    if not scope.can_manage_course(session, user):
        raise HTTPException(
            status_code=403,
            detail=(
                "Only the office can add, rename, archive or remove a section subject."
            ),
        )


def room_or_404(session: Session, section_id: UUID) -> Classroom:
    room = session.exec(select(Classroom).where(Classroom.id == section_id)).first()
    school = tenant_of(session)
    if room is None or (school is not None and room.school_id != school):
        raise HTTPException(status_code=404, detail="Class-section not found")
    return room


def subject_or_404(session: Session, classroom_subject_id: UUID) -> ClassroomSubject:
    row = session.exec(
        select(ClassroomSubject).where(ClassroomSubject.id == classroom_subject_id)
    ).first()
    school = tenant_of(session)
    if row is None or (school is not None and row.school_id != school):
        raise HTTPException(status_code=404, detail="Section subject not found")
    return row


def _active_with_name(
    session: Session,
    *,
    classroom_id: UUID,
    academic_year_id: UUID,
    name: str,
    exclude_id: UUID | None = None,
) -> ClassroomSubject | None:
    statement = select(ClassroomSubject).where(
        ClassroomSubject.classroom_id == classroom_id,
        ClassroomSubject.academic_year_id == academic_year_id,
        ClassroomSubject.status == COURSE_ACTIVE,
        func.lower(ClassroomSubject.name) == name,
    )
    if exclude_id is not None:
        statement = statement.where(ClassroomSubject.id != exclude_id)
    return session.exec(statement).first()


def _current_year(session: Session):
    year = completion.current_academic_year(session)
    if year is None:
        raise HTTPException(
            status_code=409,
            detail="Open the current academic year before adding a subject.",
        )
    return year


def create_subject(
    session: Session,
    *,
    section_id: UUID,
    name: str,
    code: str | None = None,
    user=None,
) -> ClassroomSubject:
    require_manage(session, user)
    room = room_or_404(session, section_id)
    year = _current_year(session)
    clean = normalise_name(name)
    if _active_with_name(
        session,
        classroom_id=room.id,
        academic_year_id=year.id,
        name=clean,
    ):
        raise HTTPException(
            status_code=409,
            detail=f"'{clean}' is already in this classroom for {year.name}.",
        )

    row = ClassroomSubject(
        classroom_id=room.id,
        name=clean,
        code=clean_code(code),
        academic_year_id=year.id,
        status=COURSE_ACTIVE,
        created_by_user_id=getattr(user, "id", None),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def rename_subject(
    session: Session,
    *,
    classroom_subject_id: UUID,
    name: str,
    code: str | object | None = ...,
    user=None,
) -> ClassroomSubject:
    require_manage(session, user)
    row = subject_or_404(session, classroom_subject_id)
    clean = normalise_name(name)
    if row.status == COURSE_ACTIVE and _active_with_name(
        session,
        classroom_id=row.classroom_id,
        academic_year_id=row.academic_year_id,
        name=clean,
        exclude_id=row.id,
    ):
        raise HTTPException(
            status_code=409,
            detail=f"'{clean}' is already in this classroom for this academic year.",
        )

    row.name = clean
    if code is not ...:
        row.code = clean_code(code if isinstance(code, str) else None)
    row.updated_at = utcnow()
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def archive_subject(
    session: Session, *, classroom_subject_id: UUID, user=None
) -> ClassroomSubject:
    require_manage(session, user)
    row = subject_or_404(session, classroom_subject_id)
    if row.status != COURSE_ARCHIVED:
        row.status = COURSE_ARCHIVED
        row.archived_at = utcnow()
        row.archived_by_user_id = getattr(user, "id", None)
        row.updated_at = utcnow()
        session.add(row)
        session.commit()
        session.refresh(row)
    return row


def restore_subject(
    session: Session, *, classroom_subject_id: UUID, user=None
) -> ClassroomSubject:
    require_manage(session, user)
    row = subject_or_404(session, classroom_subject_id)
    if row.status == COURSE_ARCHIVED and _active_with_name(
        session,
        classroom_id=row.classroom_id,
        academic_year_id=row.academic_year_id,
        name=row.name,
        exclude_id=row.id,
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                f"'{row.name}' is already active in this classroom. Rename or archive "
                "that subject first."
            ),
        )
    if row.status != COURSE_ACTIVE:
        row.status = COURSE_ACTIVE
        row.archived_at = None
        row.archived_by_user_id = None
        row.updated_at = utcnow()
        session.add(row)
        session.commit()
        session.refresh(row)
    return row


def require_section_subject(
    session: Session, section_id: UUID, classroom_subject_id: UUID
) -> ClassroomSubject:
    """The one check every writer uses: this subject is an active subject of this section.

    Timetable, homework, class log and attendance all name a section subject; none of
    them may point at another section's row (422) or at an archived one (409). A row of
    another school is a 404, like everywhere else.
    """
    row = subject_or_404(session, classroom_subject_id)
    if row.classroom_id != section_id:
        raise HTTPException(
            status_code=422,
            detail="That subject does not belong to this class-section.",
        )
    if row.status != COURSE_ACTIVE:
        raise HTTPException(status_code=409, detail="That subject is archived.")
    return row
