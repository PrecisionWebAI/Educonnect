from uuid import UUID
from sqlalchemy import case, func
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.domains.attendance.models import AttendanceRecord, AttendanceStatus
from app.domains.students.models import StudentProfile
from app.domains.staff.models import Employee
from app.domains.users.models import User

from .models import Classroom, Section, Subject
from .schemas import ClassroomCreate, SectionCreate
from .seed import CLASS_CATALOG

#: The platform class list, keyed by lower-cased name: `"class 6"` ->
#: `("Class 6", 8, "middle")`. `seed.py` owns this table, so a classroom created
#: on the fly carries exactly the level and stage the seeder would have written.
_CATALOG_CLASSES: dict[str, tuple[str, int, str]] = {
    name.lower(): (name, level, stage) for name, level, stage in CLASS_CATALOG
}

#: The section a class gets when a form named none - every school runs "A".
DEFAULT_SECTION_NAME = "A"


def find_classroom(session: Session, class_name: str | None) -> Classroom | None:
    """Resolve a class the caller named ("Class 6", "Grade 6", "6", "Nursery").

    The exact name is tried first because that is the stored truth. The number
    fallback mends older wording, so a free-text value captured by the admission
    form ("Class 6", a bare "6", a legacy "Grade 6") still finds the class. It
    lives in the academics domain - the owner of the vocabulary - so the
    admission form and the fee card resolve a class the same way.
    """
    cleaned = (class_name or "").strip()
    if not cleaned:
        return None
    classroom = session.exec(
        select(Classroom).where(func.lower(Classroom.name) == cleaned.lower())
    ).first()
    if classroom is not None:
        return classroom
    digits = "".join(char for char in cleaned if char.isdigit())
    if not digits:
        return None
    return session.exec(
        select(Classroom).where(Classroom.name == f"Class {int(digits)}")
    ).first()


def _digits(value: str | None) -> str:
    """The number in a class name: `"Grade 6"` -> `"6"`, `"Nursery"` -> `""`."""
    return "".join(char for char in (value or "") if char.isdigit())


def _catalog_class(class_name: str | None) -> tuple[str, int, str] | None:
    """The catalog's `(name, level, stage)` for a class the caller named, or None.

    Accepts the wording `find_classroom` accepts - "Class 6", a bare "6", a legacy
    "Grade 6" - because the number is what identifies a numbered class.
    """
    cleaned = (class_name or "").strip()
    if not cleaned:
        return None
    known = _CATALOG_CLASSES.get(cleaned.lower())
    if known is not None:
        return known
    digits = _digits(cleaned)
    if not digits:
        return None
    return _CATALOG_CLASSES.get(f"class {int(digits)}")


def ensure_classroom(session: Session, class_name: str | None) -> Classroom | None:
    """The school's row for a named class - **created** when the school has none.

    Every school is seeded with all 15 classes, so this normally just reads one
    back. It exists for the registration path: a student who registers for a class
    the school has no row for still has to end up in a real class-section, or the
    Classroom screen has nothing to show for them.

    Only a name the platform list knows is created. A typo ("Classs 6") returns
    None and the caller leaves the student unplaced, rather than inventing a class
    out of whatever was typed.
    """
    classroom = find_classroom(session, class_name)
    if classroom is not None:
        return classroom

    known = _catalog_class(class_name)
    if known is None:
        return None
    name, level, stage = known

    # A school that still spells a class "Grade 6" must not end up with a second
    # row for the same class: the number is matched before anything is created.
    digits = _digits(name)
    if digits:
        for candidate in session.exec(select(Classroom)).all():
            if _digits(candidate.name) == digits:
                return candidate

    classroom = Classroom(name=name, level=level, stage=stage)
    session.add(classroom)
    try:
        session.commit()
    except IntegrityError:
        # Another registration created the same class at the same instant; the row
        # is there now, so read it back instead of failing the registration.
        session.rollback()
        return find_classroom(session, name)
    session.refresh(classroom)
    return classroom


def _section_named(session: Session, classroom_id: UUID, name: str) -> Section | None:
    """The section of that class with that name, compared case-insensitively."""
    return session.exec(
        select(Section).where(
            Section.classroom_id == classroom_id,
            func.upper(Section.name) == name,
        )
    ).first()


def ensure_section(
    session: Session, classroom_id: UUID, name: str | None = None
) -> Section | None:
    """The class-section to place a student in - **created** when it is missing.

    Three cases, in order:

    * the form named a section ("B") and the class has it -> that one;
    * the form named one the class does not have yet -> it is created, because the
      family applied for it and the office expects that class-section to exist;
    * the form named none -> the class's first section, or a new "A" when the class
      has no sections at all.

    This is what makes a class-section appear on the Classroom screen the moment a
    student is registered for it, instead of waiting for a teacher to be assigned.
    """
    wanted = (name or "").strip().upper()
    if wanted:
        existing = _section_named(session, classroom_id, wanted)
        if existing is not None:
            return existing

    sections = list(
        session.exec(select(Section).where(Section.classroom_id == classroom_id)).all()
    )
    if not wanted and sections:
        return sections[0]

    section_name = wanted or DEFAULT_SECTION_NAME
    section = Section(name=section_name, classroom_id=classroom_id)
    session.add(section)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        return _section_named(session, classroom_id, section_name)
    session.refresh(section)
    return section


def get_classes(session: Session, skip: int = 0, limit: int = 100) -> list[Classroom]:
    return list(session.exec(select(Classroom).offset(skip).limit(limit)).all())


def get_class_by_id(session: Session, class_id: UUID) -> Classroom | None:
    return session.get(Classroom, class_id)


def create_class(session: Session, class_in: ClassroomCreate) -> Classroom:
    db_class = Classroom.model_validate(class_in)
    session.add(db_class)
    session.commit()
    session.refresh(db_class)
    return db_class


def get_sections_by_class(session: Session, class_id: UUID) -> list[Section]:
    statement = select(Section).where(Section.classroom_id == class_id)
    return list(session.exec(statement).all())


def get_subjects(session: Session) -> list[Subject]:
    """Every subject this school offers, alphabetical."""
    return list(session.exec(select(Subject).order_by(Subject.name)).all())


def create_section(session: Session, section_in: SectionCreate) -> Section:
    db_section = Section.model_validate(section_in)
    session.add(db_section)
    session.commit()
    session.refresh(db_section)
    return db_section


# ---------------------------------------------------------------------------
# Aggregations for the class views
#
# These replace numbers that used to be hardcoded in the router. Everything is
# computed from the real tables so the screens show what the school actually has.
# ---------------------------------------------------------------------------


def get_students_per_section(session: Session) -> dict[UUID, tuple[int, int, int]]:
    """section_id -> (strength, boys, girls).

    Students with an unknown gender (column is nullable) count towards
    `strength` but not towards boys or girls, which is why the three numbers
    can add up differently.
    """
    statement = (
        select(
            StudentProfile.section_id,
            func.count(StudentProfile.id),
            func.sum(case((StudentProfile.gender == "Male", 1), else_=0)),
            func.sum(case((StudentProfile.gender == "Female", 1), else_=0)),
        )
        .where(StudentProfile.section_id.is_not(None))
        .group_by(StudentProfile.section_id)
    )
    return {
        section_id: (int(total or 0), int(boys or 0), int(girls or 0))
        for section_id, total, boys, girls in session.exec(statement).all()
    }


def get_students_per_class(session: Session) -> dict[UUID, int]:
    """class_id -> number of students, used when a class has no sections yet.

    The class comes from the student's section (`section.classroom_id`), so this
    joins through it rather than reading a copy on the student row.
    """
    statement = (
        select(Section.classroom_id, func.count(StudentProfile.id))
        .select_from(StudentProfile)
        .join(Section, Section.id == StudentProfile.section_id)
        .group_by(Section.classroom_id)
    )
    return {
        class_id: int(total or 0)
        for class_id, total in session.exec(statement).all()
    }


def get_attendance_per_section(session: Session) -> dict[UUID, float]:
    """section_id -> attendance percentage.

    A student counts as attended when the status is `present`, `late` or
    `half_day`. Sections with no attendance rows are absent from the result.
    """
    attended = func.sum(
        case(
            (
                AttendanceRecord.status.in_(
                    [
                        AttendanceStatus.present,
                        AttendanceStatus.late,
                        AttendanceStatus.half_day,
                    ]
                ),
                1,
            ),
            else_=0,
        )
    )
    statement = select(
        AttendanceRecord.section_id, func.count(AttendanceRecord.id), attended
    ).group_by(AttendanceRecord.section_id)

    percentages: dict[UUID, float] = {}
    for section_id, total, attended_count in session.exec(statement).all():
        if not total:
            continue
        percentages[section_id] = round(
            100.0 * float(attended_count or 0) / float(total), 1
        )
    return percentages


def get_class_teachers_by_section(session: Session) -> dict[UUID, str]:
    """section_id -> class teacher's full name (`section.class_teacher_id`)."""
    statement = (
        select(Section.id, User.full_name)
        .join(Employee, Section.class_teacher_id == Employee.id)
        .join(User, Employee.user_id == User.id)
        .where(Section.class_teacher_id.is_not(None))
    )
    return {
        section_id: full_name
        for section_id, full_name in session.exec(statement).all()
    }
