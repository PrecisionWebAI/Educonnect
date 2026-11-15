from uuid import UUID

from sqlalchemy import false, func, or_
from sqlmodel import Session, select

from app.core.tenancy import tenant_of
from app.domains.academic.classroom.academics.models import Classroom

from .models import Guardian, Student, StudentGuardianRelationship
from .schemas import StudentCreate


def get_student_by_id(session: Session, student_id: UUID) -> Student | None:
    return session.get(Student, student_id)


def get_student_by_user_id(session: Session, user_id: UUID) -> Student | None:
    statement = select(Student).where(Student.user_id == user_id)
    return session.exec(statement).first()


def visible_student(session: Session, student_id: UUID) -> Student | None:
    """The student **if this session's school owns them**, else `None`.

    `session.get` answers by primary key and therefore skips the `do_orm_execute`
    tenant filter (the lesson the Teachers module's Phase 7 recorded): without this
    check a read with another school's id would hand back that child's record, and a
    write would hit the `before_flush` guard as a `TenantError` (a 500) instead of
    the `404` the API promises. Every path that takes a student id goes through here.
    """
    student = session.get(Student, student_id)
    if student is None:
        return None
    school_id = tenant_of(session)
    if school_id is not None and student.school_id != school_id:
        return None
    return student


def _filters(
    q: str | None,
    classroom_id: UUID | None,
    class_id: UUID | None = None,
    status: str | None = None,
    student_ids: set[UUID] | None = None,
) -> list:
    """The WHERE clauses the directory's search, filters and family scope share.

    Search runs **on the server** now (the browser used to filter the hundred rows it
    had been given): name, admission number and the guardian's name all match, so a
    clerk can find a child by the parent who pays the fees. The class-section scope is
    a real column (`student.classroom_id`), and a whole class is reached through the
    rooms it runs (`classroom.class_id`) - no copy of the class lives on the student.
    `status` reads the roll, not the login: a child who left is `deactivated_at IS NOT
    NULL`. `student_ids` is the family scope: `None` means the whole school, an empty
    set means "nobody" (a parent with no children on file sees nothing, never all).
    """
    clauses: list = []

    if student_ids is not None:
        clauses.append(Student.id.in_(list(student_ids)) if student_ids else false())

    if classroom_id is not None:
        clauses.append(Student.classroom_id == classroom_id)

    if class_id is not None:
        clauses.append(
            Student.classroom_id.in_(
                select(Classroom.id).where(Classroom.class_id == class_id)
            )
        )

    cleaned_status = (status or "").strip().lower()
    if cleaned_status in {"active", "inactive"}:
        clauses.append(
            Student.deactivated_at.is_(None)
            if cleaned_status == "active"
            else Student.deactivated_at.is_not(None)
        )

    cleaned = (q or "").strip().lower()
    if cleaned:
        like = f"%{cleaned}%"
        guardian_students = (
            select(StudentGuardianRelationship.student_id)
            .join(Guardian, Guardian.id == StudentGuardianRelationship.guardian_id)
            .where(func.lower(Guardian.name).like(like))
        )
        clauses.append(
            or_(
                func.lower(Student.full_name).like(like),
                func.lower(Student.admission_number).like(like),
                Student.id.in_(guardian_students),
            )
        )
    return clauses


def get_students(
    session: Session,
    skip: int = 0,
    limit: int | None = None,
    q: str | None = None,
    classroom_id: UUID | None = None,
    class_id: UUID | None = None,
    status: str | None = None,
    student_ids: set[UUID] | None = None,
) -> list[Student]:
    """The roll in admission-number order - `limit=None` is all of it.

    Every filter narrows it in SQL, so a page asks for exactly the rows it shows;
    `count_students` answers how many there are for the pagination control.
    """
    query = select(Student).where(
        *_filters(q, classroom_id, class_id, status, student_ids)
    )
    query = query.order_by(Student.admission_number).offset(skip)
    if limit is not None:
        query = query.limit(limit)
    return list(session.exec(query).all())


def count_students(
    session: Session,
    q: str | None = None,
    classroom_id: UUID | None = None,
    class_id: UUID | None = None,
    status: str | None = None,
    student_ids: set[UUID] | None = None,
) -> int:
    """How many students match the same filters - the page's `X-Total-Count`."""
    statement = (
        select(func.count())
        .select_from(Student)
        .where(*_filters(q, classroom_id, class_id, status, student_ids))
    )
    return int(session.exec(statement).one() or 0)


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
