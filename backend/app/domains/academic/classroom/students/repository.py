from uuid import UUID
from sqlmodel import Session, select

from .models import Guardian, Student, StudentGuardianRelationship
from .schemas import StudentCreate


def get_student_by_id(session: Session, student_id: UUID) -> Student | None:
    return session.get(Student, student_id)


def get_student_by_user_id(session: Session, user_id: UUID) -> Student | None:
    statement = select(Student).where(Student.user_id == user_id)
    return session.exec(statement).first()


def get_students(
    session: Session, skip: int = 0, limit: int | None = None
) -> list[Student]:
    """The roll in admission-number order - `limit=None` is all of it.

    The directory filters and paginates on the client, so a cap here would hide
    students; a caller that wants a page passes `skip`/`limit`.
    """
    query = select(Student).order_by(Student.admission_number).offset(skip)
    if limit is not None:
        query = query.limit(limit)
    return list(session.exec(query).all())


def create_student(session: Session, student_in: StudentCreate) -> Student:
    db_student = Student.model_validate(student_in)
    session.add(db_student)
    session.commit()
    session.refresh(db_student)
    return db_student


def primary_guardian_links(session: Session) -> dict[UUID, tuple[Guardian, str]]:
    """{student_id: (the guardian the school records first, their relation)}.

    One query for a whole screen. It returns the **primary** guardian (`is_primary`
    first, then the order guardians were added) together with the relation recorded
    for *this* child - "father" for one sibling can be "guardian" for another,
    because the relation belongs to the link and not to the person.

    Both screens that list children need it (the directory shows the person, the
    admission list shows the person and the relation), so it lives here rather than
    being written twice.
    """
    rows = session.exec(
        select(
            StudentGuardianRelationship.student_id,
            Guardian,
            StudentGuardianRelationship.relationship_type,
        )
        .join(Guardian, Guardian.id == StudentGuardianRelationship.guardian_id)
        .order_by(StudentGuardianRelationship.is_primary.desc(), Guardian.created_at)
    ).all()
    links: dict[UUID, tuple[Guardian, str]] = {}
    for student_id, guardian, relation in rows:
        if student_id is not None and student_id not in links:
            links[student_id] = (guardian, relation)
    return links


def guardian_names(session: Session, student_ids: list[UUID]) -> dict[UUID, str]:
    """{student_id: guardian name} for the students asked about.

    The guardian is a row of its own now, so a screen that lists children (the
    class-section view) reads the name through the link instead of from a column on
    the student. A student with no guardian simply does not appear in the result;
    a student with several keeps the **primary** one.
    """
    if not student_ids:
        return {}
    rows = session.exec(
        select(StudentGuardianRelationship.student_id, Guardian.name)
        .join(Guardian, Guardian.id == StudentGuardianRelationship.guardian_id)
        .where(StudentGuardianRelationship.student_id.in_(student_ids))
        .order_by(StudentGuardianRelationship.is_primary.desc())
    ).all()
    names: dict[UUID, str] = {}
    for student_id, name in rows:
        if student_id is not None and student_id not in names:
            names[student_id] = name
    return names
