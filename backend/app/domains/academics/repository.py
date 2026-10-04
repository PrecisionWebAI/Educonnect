from sqlalchemy import case, func
from sqlmodel import Session, select

from app.domains.attendance.models import AttendanceRecord, AttendanceStatus
from app.domains.students.models import StudentProfile
from app.domains.teachers.models import ClassTeacherAssignment, TeacherProfile
from app.domains.users.models import User

from .models import Classroom, Section
from .schemas import ClassroomCreate, SectionCreate


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


def get_section(
    session: Session, classroom_id: int, preferred: str | None = None
) -> Section | None:
    """The section to place a student in: the one asked for, else the first one."""
    sections = list(
        session.exec(select(Section).where(Section.classroom_id == classroom_id)).all()
    )
    if not sections:
        return None
    wanted = (preferred or "").strip().upper()
    for section in sections:
        if wanted and section.name.strip().upper() == wanted:
            return section
    return sections[0]


def get_classes(session: Session, skip: int = 0, limit: int = 100) -> list[Classroom]:
    return list(session.exec(select(Classroom).offset(skip).limit(limit)).all())


def get_class_by_id(session: Session, class_id: int) -> Classroom | None:
    return session.get(Classroom, class_id)


def create_class(session: Session, class_in: ClassroomCreate) -> Classroom:
    db_class = Classroom.model_validate(class_in)
    session.add(db_class)
    session.commit()
    session.refresh(db_class)
    return db_class


def get_sections_by_class(session: Session, class_id: int) -> list[Section]:
    statement = select(Section).where(Section.classroom_id == class_id)
    return list(session.exec(statement).all())


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


def get_students_per_section(session: Session) -> dict[int, tuple[int, int, int]]:
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
        int(section_id): (int(total or 0), int(boys or 0), int(girls or 0))
        for section_id, total, boys, girls in session.exec(statement).all()
    }


def get_students_per_class(session: Session) -> dict[int, int]:
    """class_id -> number of students, used when a class has no sections yet."""
    statement = (
        select(StudentProfile.classroom_id, func.count(StudentProfile.id))
        .where(StudentProfile.classroom_id.is_not(None))
        .group_by(StudentProfile.classroom_id)
    )
    return {
        int(class_id): int(total or 0)
        for class_id, total in session.exec(statement).all()
    }


def get_attendance_per_section(session: Session) -> dict[int, float]:
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

    percentages: dict[int, float] = {}
    for section_id, total, attended_count in session.exec(statement).all():
        if not total:
            continue
        percentages[int(section_id)] = round(
            100.0 * float(attended_count or 0) / float(total), 1
        )
    return percentages


def get_class_teachers_by_section(session: Session) -> dict[int, str]:
    """section_id -> class teacher's full name (from classteacherassignment)."""
    statement = (
        select(ClassTeacherAssignment.section_id, User.full_name)
        .join(TeacherProfile, ClassTeacherAssignment.teacher_id == TeacherProfile.id)
        .join(User, TeacherProfile.user_id == User.id)
        .where(ClassTeacherAssignment.section_id.is_not(None))
    )
    return {
        int(section_id): full_name
        for section_id, full_name in session.exec(statement).all()
    }
