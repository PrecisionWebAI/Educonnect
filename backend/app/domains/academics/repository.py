from collections import namedtuple
from uuid import UUID
from sqlalchemy import case, func
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.domains.attendance.models import AttendanceRecord, AttendanceStatus
from app.domains.students.models import StudentProfile
from app.domains.staff.models import Employee
from app.domains.users.models import User

from .models import (
    ClassName,
    Classroom,
    Section,
    Subject,
    SubjectTeacher,
    SyllabusProgress,
)
from .schemas import ClassroomCreate


def find_classroom(session: Session, class_name: str | None) -> ClassName | None:
    """Resolve a class the caller named ("Class 6", "Grade 6", "6", "Nursery").

    The classes are a **platform catalog** now, so this reads `classname`. The
    exact name is tried first because that is the stored truth; the number
    fallback mends older wording, so a free-text value captured by the admission
    form ("Class 6", a bare "6", a legacy "Grade 6") still finds the class. It
    lives in the academics domain - the owner of the vocabulary - so the admission
    form, the fee card and the paper builder resolve a class the same way.
    """
    cleaned = (class_name or "").strip()
    if not cleaned:
        return None
    classroom = session.exec(
        select(ClassName).where(func.lower(ClassName.classname) == cleaned.lower())
    ).first()
    if classroom is not None:
        return classroom
    digits = "".join(char for char in cleaned if char.isdigit())
    if not digits:
        return None
    return session.exec(
        select(ClassName).where(
            func.lower(ClassName.classname) == f"class {int(digits)}"
        )
    ).first()


def find_section(session: Session, section_name: str | None) -> Section | None:
    """Resolve a section letter ("A", "b") to the platform catalog row."""
    cleaned = (section_name or "").strip().upper()
    if not cleaned:
        return None
    return session.exec(
        select(Section).where(func.upper(Section.section_name) == cleaned)
    ).first()


def ensure_room(session: Session, class_id: UUID, section_id: UUID) -> Classroom:
    """The school's class-section row, **created the first time it is used**.

    Rooms are deliberately not seeded: registering a student into "Class 10-A"
    (or assigning a class teacher, or adding a timetable period) is what brings
    that row into being, so the Classroom grid shows the class-sections the school
    actually runs instead of 150 empty ones.

    Idempotent and concurrency-safe: two registrations racing for the same new
    class-section produce one row (`UNIQUE(school_id, class_id, section_id)`), and
    the loser reads back what the winner wrote.
    """
    statement = select(Classroom).where(
        Classroom.class_id == class_id, Classroom.section_id == section_id
    )
    found = session.exec(statement).first()
    if found is not None:
        return found

    room = Classroom(class_id=class_id, section_id=section_id)
    session.add(room)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        existing = session.exec(statement).first()
        if existing is None:  # pragma: no cover - the unique index guarantees one
            raise
        return existing
    session.refresh(room)
    return room


def room_label(session: Session, room_id: UUID | None) -> str:
    """What the school calls a class-section: "Class 10-A" ("" when unknown)."""
    if room_id is None:
        return ""
    room = session.get(Classroom, room_id)
    if room is None:
        return ""
    classroom = session.get(ClassName, room.class_id)
    section = session.get(Section, room.section_id)
    if classroom is None or section is None:
        return ""
    return f"{classroom.classname}-{section.section_name}"


def delete_room_if_unused(session: Session, room_id: UUID | None) -> str | None:
    """Delete the class-section once its **last student** has gone - the mirror of
    `ensure_room`.

    A room is the school's class-section ("Class 10-A"), so a room nobody sits in
    is not a class-section any more: it is deleted together with everything it
    owns - its attendance register, timetable, homework, class diary, syllabus
    progress and the teacher assignments filed against it. The class-level tables
    (`feestructure`, `paperdraft`, `examsource`) point at `classname`, so they are
    untouched.

    Runs in the **caller's transaction** (the caller has just deleted the last
    student), so the student and their class-section go together or not at all.
    Returns the room's label when it deleted one, `None` when the room still has
    students or does not exist.

    Any future path that moves a student between class-sections must call this for
    the class-section they left, exactly as the registration path calls
    `ensure_room` for the one they join.
    """
    if room_id is None:
        return None

    still_there = session.exec(
        select(StudentProfile.id).where(StudentProfile.classroom_id == room_id)
    ).first()
    if still_there is not None:
        return None

    room = session.get(Classroom, room_id)
    if room is None:
        return None
    label = room_label(session, room_id)

    # Imported here: the homework/timetable domains import this one, so a module
    # level import would be a cycle. Order matters - each of them holds a foreign
    # key to `classroom.id`, so they go before the room itself.
    from app.domains.homework.models import ClassLog, HomeworkAssignment
    from app.domains.timetable.models import TimetablePeriod

    for model in (
        SyllabusProgress,
        HomeworkAssignment,
        ClassLog,
        AttendanceRecord,
        TimetablePeriod,
        SubjectTeacher,
    ):
        for row in session.exec(
            select(model).where(model.classroom_id == room_id)  # type: ignore[attr-defined]
        ).all():
            session.delete(row)
        # Flush per table: the room may only go once every table that points at it
        # is empty, and flushing here makes that order explicit instead of leaving
        # it to the unit of work's sort.
        session.flush()

    session.delete(room)
    return label


def get_classes(
    session: Session, skip: int = 0, limit: int = 100
) -> list[ClassName]:
    """The platform's class list (Nursery … Class 12), in school order."""
    return list(
        session.exec(
            select(ClassName).order_by(ClassName.level).offset(skip).limit(limit)
        ).all()
    )


def get_class_by_id(session: Session, class_id: UUID) -> ClassName | None:
    return session.get(ClassName, class_id)


def create_class(session: Session, class_in: ClassroomCreate) -> ClassName:
    """Add a class to the **platform catalog** - what "add a class" means now.

    Classes are the same 15 rows in every school, so this writes `classname`
    rather than a per-school row.
    """
    db_class = ClassName(
        classname=class_in.name, level=class_in.level, stage=class_in.stage
    )
    session.add(db_class)
    session.commit()
    session.refresh(db_class)
    return db_class


#: One class-section of a school: the room, plus the section letter it runs.
#: The screen reads `.id`, `.section_name` and `.class_id`, so a row is handed
#: over as this tuple rather than as two joined tables.
ClassSectionRow = namedtuple("ClassSectionRow", "id section_name class_id")


def get_sections_by_class(session: Session, class_id: UUID) -> list[ClassSectionRow]:
    """The school's class-sections of one class, in section order (A, B, C …).

    A class-section exists because the school uses it (a student sits in it, a
    teacher runs it, a period is scheduled), so this reads the school's `classroom`
    rows rather than the platform's section list.
    """
    statement = (
        select(Classroom.id, Section.section_name, Classroom.class_id)
        .join(Section, Section.section_id == Classroom.section_id)
        .where(Classroom.class_id == class_id)
        .order_by(Section.section_name)
    )
    return [ClassSectionRow(*row) for row in session.exec(statement).all()]


def get_all_sections(session: Session) -> list[Section]:
    """The platform's section list (A … J), in order - what a dropdown offers."""
    return list(
        session.exec(select(Section).order_by(Section.section_name)).all()
    )


def get_subjects(session: Session) -> list[Subject]:
    """Every subject this school offers, alphabetical."""
    return list(session.exec(select(Subject).order_by(Subject.name)).all())


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
            StudentProfile.classroom_id,
            func.count(StudentProfile.id),
            func.sum(case((func.lower(StudentProfile.gender) == "male", 1), else_=0)),
            func.sum(case((func.lower(StudentProfile.gender) == "female", 1), else_=0)),
        )
        .where(StudentProfile.classroom_id.is_not(None))
        .group_by(StudentProfile.classroom_id)
    )
    return {
        section_id: (int(total or 0), int(boys or 0), int(girls or 0))
        for section_id, total, boys, girls in session.exec(statement).all()
    }


def get_students_per_class(session: Session) -> dict[UUID, int]:
    """class_id -> number of students, used when a class has no sections yet.

    The class comes from the student's class-section (`classroom.class_id`), so
    this joins through the room rather than reading a copy on the student row.
    """
    statement = (
        select(Classroom.class_id, func.count(StudentProfile.id))
        .select_from(StudentProfile)
        .join(Classroom, Classroom.id == StudentProfile.classroom_id)
        .group_by(Classroom.class_id)
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
        AttendanceRecord.classroom_id, func.count(AttendanceRecord.id), attended
    ).group_by(AttendanceRecord.classroom_id)

    percentages: dict[UUID, float] = {}
    for section_id, total, attended_count in session.exec(statement).all():
        if not total:
            continue
        percentages[section_id] = round(
            100.0 * float(attended_count or 0) / float(total), 1
        )
    return percentages


def get_class_teachers_by_section(session: Session) -> dict[UUID, str]:
    """class-section id -> class teacher's full name (`classroom.class_teacher_id`)."""
    statement = (
        select(Classroom.id, User.full_name)
        .select_from(Classroom)
        .join(Employee, Classroom.class_teacher_id == Employee.id)
        .join(User, Employee.user_id == User.id)
        .where(Classroom.class_teacher_id.is_not(None))
    )
    return {
        section_id: full_name
        for section_id, full_name in session.exec(statement).all()
    }
