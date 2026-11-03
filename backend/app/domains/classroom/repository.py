"""Aggregate reads behind the Classroom cards.

Each function returns a dict keyed by `section_id` (or `classroom_id`) so the
service assembles every card with a fixed number of queries instead of one query
per card. Nothing here invents a value: a section with no rows simply does not
appear in the dict, and the card shows "-".
"""

from dataclasses import dataclass
from datetime import date
from uuid import UUID
from sqlalchemy import case, func
from sqlalchemy.orm import aliased
from sqlmodel import Session, select

from app.domains.academics.models import (
    ClassName,
    Classroom,
    Section,
    Subject,
    SubjectTeacher,
    SyllabusProgress,
)
from app.domains.attendance.models import AttendanceRecord, AttendanceStatus
from app.domains.exams.models import Exam, ExamSubject, Mark
from app.domains.finance.models import FeeStructure, FeeTransaction
from app.domains.homework.models import ClassLog, HomeworkAssignment, HomeworkSubmission
from app.domains.staff.models import Employee
from app.domains.students.models import StudentProfile
from app.domains.timetable.models import TimetablePeriod
from app.domains.users.models import User

#: Statuses that count as "the student was there".
_ATTENDED = (
    AttendanceStatus.present,
    AttendanceStatus.late,
    AttendanceStatus.half_day,
)


@dataclass(frozen=True)
class SectionContext:
    """One class-section as the screen needs it.

    A class-section is the school's `classroom` row ("Class 10-A"); the class and
    the section are ids into the two **platform** catalogs, so the wording is read
    through this object rather than stored twice.
    """

    room_id: UUID
    class_id: UUID
    class_name: str
    section_id: UUID
    section_name: str
    class_teacher_id: UUID | None

    @property
    def id(self) -> UUID:
        """The class-section id every other table points at."""
        return self.room_id

    @property
    def label(self) -> str:
        """What the screen calls it: "Class 10-A"."""
        return f"{self.class_name}-{self.section_name}"


# ---------------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------------


def get_classrooms(session: Session) -> list[ClassName]:
    """Every class of the platform catalog (Nursery … Class 12), in school order.

    The classes are platform-wide now, so this reads `classname` rather than the
    school's own rows - a class means the same thing in every school.
    """
    return list(session.exec(select(ClassName).order_by(ClassName.level)).all())


def get_sections(session: Session) -> list[SectionContext]:
    """The school's class-sections (its `classroom` rows), in school order.

    Ordered by the class's level and then the section letter, so the grid reads
    Nursery-A … Class 12-J rather than in whatever order the rows were written.
    """
    statement = (
        select(
            Classroom.id,
            Classroom.class_id,
            ClassName.classname,
            Classroom.section_id,
            Section.section_name,
            Classroom.class_teacher_id,
        )
        .join(ClassName, ClassName.class_id == Classroom.class_id)
        .join(Section, Section.section_id == Classroom.section_id)
        .order_by(ClassName.level, Section.section_name)
    )
    return [SectionContext(*row) for row in session.exec(statement).all()]


# ---------------------------------------------------------------------------
# Per-section roll-ups
# ---------------------------------------------------------------------------


def get_mark(
    session: Session, exam_id: UUID, student_id: UUID, subject_id: UUID
) -> Mark | None:
    """The one mark row for (exam, student, subject) - the key the table is unique on."""
    return session.exec(
        select(Mark).where(
            Mark.exam_id == exam_id,
            Mark.student_id == student_id,
            Mark.subject_id == subject_id,
        )
    ).first()


def get_section_marks(session: Session, section_id: UUID) -> list[tuple]:
    """Every mark of one class-section: (exam, student, subject, score, max).

    One row per (exam, student, subject). The score is on `Mark` and the maximum on
    `ExamSubject`, so the same "out of" number is not repeated on every student's
    row - and a mark cannot claim a maximum the exam never declared.
    """
    statement = (
        select(
            Mark.exam_id,
            Exam.name,
            Mark.student_id,
            Mark.subject_id,
            Subject.name,
            Mark.marks_obtained,
            ExamSubject.max_marks,
        )
        .join(StudentProfile, StudentProfile.id == Mark.student_id)
        .join(Exam, Exam.id == Mark.exam_id)
        .join(Subject, Subject.id == Mark.subject_id)
        .join(
            ExamSubject,
            (ExamSubject.exam_id == Mark.exam_id)
            & (ExamSubject.subject_id == Mark.subject_id),
        )
        .where(StudentProfile.classroom_id == section_id)
        .order_by(Exam.name, StudentProfile.admission_number, Subject.name)
    )
    return list(session.exec(statement).all())


def get_students_per_section(session: Session) -> dict[UUID, tuple[int, int, int]]:
    """section_id -> (strength, boys, girls).

    Students with no recorded gender count towards `strength` only, which is why
    boys + girls can be less than strength.
    """
    statement = (
        select(
            StudentProfile.classroom_id,
            func.count(StudentProfile.id),
            func.sum(case((StudentProfile.gender == "Male", 1), else_=0)),
            func.sum(case((StudentProfile.gender == "Female", 1), else_=0)),
        )
        .where(StudentProfile.classroom_id.is_not(None))
        .group_by(StudentProfile.classroom_id)
    )
    return {
        section_id: (int(total or 0), int(boys or 0), int(girls or 0))
        for section_id, total, boys, girls in session.exec(statement).all()
    }


def get_class_teachers_by_section(session: Session) -> dict[UUID, str]:
    """class-section id -> class teacher's name (`classroom.class_teacher_id`)."""
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


def get_attendance_per_section(
    session: Session,
) -> dict[UUID, tuple[date, int, float]]:
    """section_id -> (latest register date, present that day, overall %).

    One query over the grouped register; the latest day per section is picked in
    Python so this stays portable and readable.
    """
    attended = func.sum(
        case((AttendanceRecord.status.in_(_ATTENDED), 1), else_=0)
    )
    statement = (
        select(
            AttendanceRecord.classroom_id,
            AttendanceRecord.date,
            func.count(AttendanceRecord.id),
            attended,
        )
        .where(AttendanceRecord.classroom_id.is_not(None))
        .group_by(AttendanceRecord.classroom_id, AttendanceRecord.date)
    )

    latest: dict[UUID, date] = {}
    present: dict[UUID, int] = {}
    totals: dict[UUID, list[UUID]] = {}
    for section_id, day, total, attended_count in session.exec(statement).all():
        key = section_id
        if key not in latest or day > latest[key]:
            latest[key] = day
            present[key] = int(attended_count or 0)
        bucket = totals.setdefault(key, [0, 0])
        bucket[0] += int(total or 0)
        bucket[1] += int(attended_count or 0)

    result: dict[UUID, tuple[date, int, float]] = {}
    for key, day in latest.items():
        total, attended_count = totals[key]
        percent = round(100.0 * attended_count / total, 1) if total else 0.0
        result[key] = (day, present[key], percent)
    return result


def get_fees_per_section(session: Session) -> dict[UUID, tuple[float, float]]:
    """section_id -> (collected, expected).

    Expected: every student in the section owes the fee structures filed against
    their class. Collected: the payments recorded for those students.
    """
    per_class = {
        classroom_id: float(amount or 0)
        for classroom_id, amount in session.exec(
            select(FeeStructure.class_id, func.sum(FeeStructure.amount)).group_by(
                FeeStructure.class_id
            )
        ).all()
    }

    expected: dict[UUID, float] = {}
    for section_id, classroom_id in session.exec(
        select(StudentProfile.classroom_id, Classroom.class_id)
        .join(Classroom, Classroom.id == StudentProfile.classroom_id)
        .where(StudentProfile.classroom_id.is_not(None))
    ).all():
        key = section_id
        expected[key] = expected.get(key, 0.0) + per_class.get(
            classroom_id, 0.0
        )

    collected: dict[UUID, float] = {}
    statement = (
        select(StudentProfile.classroom_id, func.sum(FeeTransaction.amount_paid))
        .join(FeeTransaction, FeeTransaction.student_id == StudentProfile.id)
        .where(StudentProfile.classroom_id.is_not(None))
        .group_by(StudentProfile.classroom_id)
    )
    for section_id, amount in session.exec(statement).all():
        collected[section_id] = float(amount or 0)

    return {
        key: (collected.get(key, 0.0), expected.get(key, 0.0))
        for key in set(expected) | set(collected)
    }


def get_syllabus_per_section(session: Session) -> dict[UUID, tuple[float, int]]:
    """section_id -> (percent complete, subjects tracked)."""
    statement = (
        select(
            SyllabusProgress.classroom_id,
            func.sum(SyllabusProgress.chapters_total),
            func.sum(SyllabusProgress.chapters_done),
            func.count(SyllabusProgress.id),
        ).group_by(SyllabusProgress.classroom_id)
    )
    result: dict[UUID, tuple[float, int]] = {}
    for section_id, total, done, subjects in session.exec(statement).all():
        if not total:
            continue
        result[section_id] = (
            round(100.0 * float(done or 0) / float(total), 1),
            int(subjects or 0),
        )
    return result


def get_open_homework_per_section(session: Session, today: date) -> dict[UUID, int]:
    """section_id -> assignments whose due date has not passed."""
    statement = (
        select(HomeworkAssignment.classroom_id, func.count(HomeworkAssignment.id))
        .where(
            HomeworkAssignment.classroom_id.is_not(None),
            HomeworkAssignment.due_date >= today,
        )
        .group_by(HomeworkAssignment.classroom_id)
    )
    return {
        section_id: int(count) for section_id, count in session.exec(statement).all()
    }


def get_periods_per_section(session: Session) -> dict[UUID, int]:
    """section_id -> timetable periods in the week."""
    statement = (
        select(TimetablePeriod.classroom_id, func.count(TimetablePeriod.id))
        .where(TimetablePeriod.classroom_id.is_not(None))
        .group_by(TimetablePeriod.classroom_id)
    )
    return {
        section_id: int(count) for section_id, count in session.exec(statement).all()
    }


def get_marks_per_section(session: Session) -> dict[UUID, tuple[float, int]]:
    """section_id -> (average %, number of exams with marks).

    The maximum comes from `ExamSubject` - the exam says what each subject is out
    of, so a mark row carries only the score.
    """
    percent = Mark.marks_obtained * 100.0 / func.nullif(ExamSubject.max_marks, 0)
    statement = (
        select(
            StudentProfile.classroom_id,
            func.avg(percent),
            func.count(func.distinct(Mark.exam_id)),
        )
        .join(Mark, Mark.student_id == StudentProfile.id)
        .join(
            ExamSubject,
            (ExamSubject.exam_id == Mark.exam_id)
            & (ExamSubject.subject_id == Mark.subject_id),
        )
        .where(StudentProfile.classroom_id.is_not(None))
        .group_by(StudentProfile.classroom_id)
    )
    return {
        section_id: (round(float(average or 0), 1), int(exams or 0))
        for section_id, average, exams in session.exec(statement).all()
    }


def get_last_diary_per_section(session: Session) -> dict[UUID, date]:
    """section_id -> the date of its most recent class-log entry."""
    statement = select(ClassLog.classroom_id, func.max(ClassLog.date)).group_by(
        ClassLog.classroom_id
    )
    return {
        section_id: day
        for section_id, day in session.exec(statement).all()
        if day is not None
    }


def get_active_section_ids(session: Session) -> set[UUID]:
    """Sections the school actually uses: a student, a class teacher or a period.

    A class-section with none of those is left out of the grid entirely. In practice
    a room cannot stay empty for long: the moment its last student is deleted the
    room itself is deleted too (`delete_room_if_unused`), so the student branch here
    is what normally keeps a card on the screen.
    """
    ids: set[UUID] = set()
    for statement in (
        select(StudentProfile.classroom_id)
        .where(StudentProfile.classroom_id.is_not(None))
        .distinct(),
        select(Classroom.id)
        .where(Classroom.class_teacher_id.is_not(None))
        .distinct(),
        select(TimetablePeriod.classroom_id)
        .where(TimetablePeriod.classroom_id.is_not(None))
        .distinct(),
    ):
        ids.update(session.exec(statement).all())
    return ids


def get_teacher_assignment_classroom_ids(session: Session) -> set[UUID]:
    """Classes with at least one teacher assignment (even with no students yet)."""
    statement = (
        select(SubjectTeacher.classroom_id)
        .where(SubjectTeacher.classroom_id.is_not(None))
        .distinct()
    )
    return {value for value in session.exec(statement).all()}


# ---------------------------------------------------------------------------
# Phase 2 - the drill-down behind one class-section
# ---------------------------------------------------------------------------


def get_section(session: Session, section_id: UUID) -> "SectionContext | None":
    """One class-section: the school's room plus the wording from the catalogs.

    A class-section is a `classroom` row now (the class and the section are ids
    into the two platform catalogs), so everything the screen shows about it -
    "Class 10", "A", the class teacher - is read through this one object.
    """
    statement = (
        select(
            Classroom.id,
            ClassName.class_id,
            ClassName.classname,
            Section.section_id,
            Section.section_name,
            Classroom.class_teacher_id,
        )
        .join(ClassName, ClassName.class_id == Classroom.class_id)
        .join(Section, Section.section_id == Classroom.section_id)
        .where(Classroom.id == section_id)
    )
    row = session.exec(statement).first()
    if row is None:
        return None
    return SectionContext(
        room_id=row[0],
        class_id=row[1],
        class_name=row[2],
        section_id=row[3],
        section_name=row[4],
        class_teacher_id=row[5],
    )


def get_classroom(session: Session, classroom_id: UUID) -> ClassName | None:
    """One class of the platform catalog ("Class 10") by its id."""
    return session.get(ClassName, classroom_id)


def get_class_teacher_info(
    session: Session, section_id: UUID
) -> tuple[UUID, str, str, str | None] | None:
    """(employee_id, name, email, phone) of the class-section's class teacher, or None."""
    statement = (
        select(Employee.id, User.full_name, User.email, Employee.phone)
        # `select_from` pins the driving table: without it SQLAlchemy cannot tell
        # where the join starts and adds a second FROM, which cross-joins every row.
        .select_from(Classroom)
        .join(Employee, Classroom.class_teacher_id == Employee.id)
        .join(User, Employee.user_id == User.id)
        .where(Classroom.id == section_id)
    )
    return session.exec(statement).first()


def get_students_in_section(
    session: Session, section_id: UUID
) -> list[tuple[StudentProfile, User]]:
    """(profile, login) for every student in the section, alphabetical."""
    statement = (
        select(StudentProfile, User)
        .join(User, User.id == StudentProfile.user_id)
        .where(StudentProfile.classroom_id == section_id)
        .order_by(User.full_name)
    )
    return list(session.exec(statement).all())


def get_student_attendance(session: Session, section_id: UUID) -> dict[UUID, float]:
    """student_id -> attendance % for this section."""
    attended = func.sum(case((AttendanceRecord.status.in_(_ATTENDED), 1), else_=0))
    statement = (
        select(AttendanceRecord.student_id, func.count(AttendanceRecord.id), attended)
        .where(AttendanceRecord.classroom_id == section_id)
        .group_by(AttendanceRecord.student_id)
    )
    result: dict[UUID, float] = {}
    for student_id, total, attended_count in session.exec(statement).all():
        if not total:
            continue
        result[student_id] = round(
            100.0 * float(attended_count or 0) / float(total), 1
        )
    return result


def get_student_fees(session: Session) -> dict[UUID, float]:
    """student_id -> total paid (the caller picks the students it needs)."""
    statement = select(
        FeeTransaction.student_id, func.sum(FeeTransaction.amount_paid)
    ).group_by(FeeTransaction.student_id)
    return {
        student_id: float(amount or 0)
        for student_id, amount in session.exec(statement).all()
    }


def get_fee_total_for_class(session: Session, classroom_id: UUID) -> float:
    """What one student in this class owes: the sum of its fee structures."""
    total = session.exec(
        select(func.sum(FeeStructure.amount)).where(
            FeeStructure.class_id == classroom_id
        )
    ).one()
    return float(total or 0)


def get_syllabus_percent(session: Session, section_id: UUID) -> float | None:
    """`chapters_done / chapters_total` for the section, or None when untracked."""
    total, done = session.exec(
        select(
            func.sum(SyllabusProgress.chapters_total),
            func.sum(SyllabusProgress.chapters_done),
        ).where(SyllabusProgress.classroom_id == section_id)
    ).one()
    if not total:
        return None
    return round(100.0 * float(done or 0) / float(total), 1)


def get_attendance_days(
    session: Session, section_id: UUID, limit: int = 30
) -> list[tuple]:
    """Newest first: (date, present, absent, leave, late, total)."""
    statement = (
        select(
            AttendanceRecord.date,
            func.sum(
                case((AttendanceRecord.status == AttendanceStatus.present, 1), else_=0)
            ),
            func.sum(
                case((AttendanceRecord.status == AttendanceStatus.absent, 1), else_=0)
            ),
            func.sum(
                case((AttendanceRecord.status == AttendanceStatus.leave, 1), else_=0)
            ),
            func.sum(
                case((AttendanceRecord.status == AttendanceStatus.late, 1), else_=0)
            ),
            func.count(AttendanceRecord.id),
        )
        .where(AttendanceRecord.classroom_id == section_id)
        .group_by(AttendanceRecord.date)
        .order_by(AttendanceRecord.date.desc())
        .limit(limit)
    )
    return list(session.exec(statement).all())


def get_timetable_rows(session: Session, section_id: UUID) -> list[tuple]:
    """(day, start, end, subject, teacher, room) in week order."""
    statement = (
        select(
            TimetablePeriod.day_of_week,
            TimetablePeriod.start_time,
            TimetablePeriod.end_time,
            Subject.name,
            User.full_name,
            TimetablePeriod.room,
        )
        .join(Subject, Subject.id == TimetablePeriod.subject_id)
        .join(Employee, Employee.id == TimetablePeriod.teacher_id)
        .join(User, User.id == Employee.user_id)
        .where(TimetablePeriod.classroom_id == section_id)
        .order_by(TimetablePeriod.day_of_week, TimetablePeriod.start_time)
    )
    return list(session.exec(statement).all())


def get_homework_rows(session: Session, section_id: UUID) -> list[tuple]:
    """(id, title, subject, teacher, due_date) newest due date first."""
    statement = (
        select(
            HomeworkAssignment.id,
            HomeworkAssignment.title,
            Subject.name,
            User.full_name,
            HomeworkAssignment.due_date,
        )
        .join(Subject, Subject.id == HomeworkAssignment.subject_id)
        .join(Employee, Employee.id == HomeworkAssignment.teacher_id)
        .join(User, User.id == Employee.user_id)
        .where(HomeworkAssignment.classroom_id == section_id)
        .order_by(HomeworkAssignment.due_date.desc(), HomeworkAssignment.id.desc())
    )
    return list(session.exec(statement).all())


def get_submission_counts(session: Session) -> dict[UUID, int]:
    """homework_id -> how many submissions were handed in."""
    statement = select(
        HomeworkSubmission.homework_id, func.count(HomeworkSubmission.id)
    ).group_by(HomeworkSubmission.homework_id)
    return {
        homework_id: int(count)
        for homework_id, count in session.exec(statement).all()
    }


def get_diary_rows(session: Session, section_id: UUID, limit: int = 50) -> list[tuple]:
    """(id, date, note, teacher name) for the section's class log, newest first."""
    statement = (
        select(ClassLog.id, ClassLog.date, ClassLog.note, User.full_name)
        .join(Employee, Employee.id == ClassLog.teacher_id)
        .join(User, User.id == Employee.user_id)
        .where(ClassLog.classroom_id == section_id)
        .order_by(ClassLog.date.desc(), ClassLog.id.desc())
        .limit(limit)
    )
    return list(session.exec(statement).all())


def get_exam_rows(session: Session, section_id: UUID) -> list[tuple]:
    """(exam, average %, marks entered) for exams this section has marks for."""
    percent = Mark.marks_obtained * 100.0 / func.nullif(ExamSubject.max_marks, 0)
    statement = (
        select(Exam, func.avg(percent), func.count(Mark.id))
        .join(Mark, Mark.exam_id == Exam.id)
        .join(
            ExamSubject,
            (ExamSubject.exam_id == Mark.exam_id)
            & (ExamSubject.subject_id == Mark.subject_id),
        )
        .join(StudentProfile, StudentProfile.id == Mark.student_id)
        .where(StudentProfile.classroom_id == section_id)
        .group_by(Exam.id)
        .order_by(Exam.start_date.desc().nullslast(), Exam.name)
    )
    return list(session.exec(statement).all())


def get_subject_mark_rows(session: Session, section_id: UUID) -> list[tuple]:
    """(subject, average %, highest %, lowest %, entries) per subject."""
    percent = Mark.marks_obtained * 100.0 / func.nullif(ExamSubject.max_marks, 0)
    statement = (
        select(
            Subject.name,
            func.avg(percent),
            func.max(percent),
            func.min(percent),
            func.count(Mark.id),
        )
        .join(Mark, Mark.subject_id == Subject.id)
        .join(
            ExamSubject,
            (ExamSubject.exam_id == Mark.exam_id)
            & (ExamSubject.subject_id == Mark.subject_id),
        )
        .join(StudentProfile, StudentProfile.id == Mark.student_id)
        .where(StudentProfile.classroom_id == section_id)
        .group_by(Subject.name)
        .order_by(Subject.name)
    )
    return list(session.exec(statement).all())


# ---------------------------------------------------------------------------
# Assignments - who runs the section, and who takes each subject
# ---------------------------------------------------------------------------


def get_subject_rows(session: Session, section_id: UUID) -> list[tuple]:
    """(subject_id, name, code, teacher_id, teacher_name) for **every** subject.

    The join onto `subjectteacher` is an outer one **and** carries the section in
    its ON clause: putting `section_id` in the WHERE instead would drop every
    subject that has no teacher yet, and those empty slots are exactly what the
    screen assigns into.
    """
    statement = (
        select(
            Subject.id,
            Subject.name,
            Subject.code,
            SubjectTeacher.teacher_id,
            User.full_name,
        )
        .join(
            SubjectTeacher,
            (SubjectTeacher.subject_id == Subject.id)
            & (SubjectTeacher.classroom_id == section_id),
            isouter=True,
        )
        .join(Employee, Employee.id == SubjectTeacher.teacher_id, isouter=True)
        .join(User, User.id == Employee.user_id, isouter=True)
        .order_by(Subject.name)
    )
    return list(session.exec(statement).all())


def get_teacher_options(session: Session) -> list[tuple]:
    """(employee_id, name, email) for every staff member, alphabetical."""
    statement = (
        select(Employee.id, User.full_name, User.email)
        .join(User, User.id == Employee.user_id)
        .order_by(User.full_name)
    )
    return list(session.exec(statement).all())

