"""Aggregate reads behind the Classroom cards.

Each function returns a dict keyed by `section_id` (or `classroom_id`) so the
service assembles every card with a fixed number of queries instead of one query
per card. Nothing here invents a value: a section with no rows simply does not
appear in the dict, and the card shows "-".
"""

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy import case, func, or_
from sqlmodel import Session, select

from app.domains.academic.classroom.academics.models import (
    ClassName,
    Classroom,
    Section,
    SubjectTeacher,
)
from app.domains.academic.classroom.attendance.models import (
    AttendanceRecord,
    AttendanceStatus,
)
from app.domains.academic.classroom.course.models import ClassroomSubject
from app.domains.academic.classroom.exams.models import Exam, ExamPaper, Mark
from app.domains.academic.classroom.homework.models import (
    ClassLog,
    HomeworkAssignment,
    HomeworkSubmission,
)
from app.domains.academic.classroom.students.models import Student
from app.domains.academic.classroom.timetable.models import TimetablePeriod
from app.domains.admin.settings.academic_year_context import current_academic_year_id
from app.domains.admin.users.models import User
from app.domains.auth.models import Role, UserRole
from app.domains.finance.fees.models import FeeTransaction
from app.domains.operations.fees_structure.models import FeeStructure
from app.domains.people.staff.models import Employee
from app.domains.people.teachers.labels import TEACHING_ROLES

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


def get_section_marks(session: Session, section_id: UUID) -> list[tuple]:
    """Every mark of one class-section: (exam, student, subject, score, max).

    One row per (exam, student, subject). The score is on `Mark` and the maximum on
    the **paper** the student sat (`exam_paper.max_marks`, Phase 7), so the same "out
    of" number is not repeated on every student's row - and a mark cannot claim a
    maximum no date sheet declared.
    """
    statement = (
        select(
            ExamPaper.exam_id,
            Exam.name,
            Mark.student_id,
            ExamPaper.classroom_subject_id,
            ClassroomSubject.name,
            Mark.marks_obtained,
            ExamPaper.max_marks,
        )
        .join(Student, Student.id == Mark.student_id)
        .join(ExamPaper, ExamPaper.id == Mark.exam_paper_id)
        .join(Exam, Exam.id == ExamPaper.exam_id)
        .join(ClassroomSubject, ClassroomSubject.id == ExamPaper.classroom_subject_id)
        .where(Student.classroom_id == section_id)
        .order_by(Exam.name, Student.admission_number, ClassroomSubject.name)
    )
    return list(session.exec(statement).all())


def get_all_marks(session: Session) -> list[tuple]:
    """Every mark the school holds, with the class-section it was earned in.

    `(exam_id, exam, student_id, student, admission, class, section, classroom_subject_id,
    subject, obtained, max)` - the school-wide twin of `get_section_marks`, read by
    the Academics screen and the director's dashboard. The class-section is an
    **outer** join: a student who is not placed yet still has marks, and hiding them
    would be worse than showing a blank class.
    """
    statement = (
        select(
            ExamPaper.exam_id,
            Exam.name,
            Mark.student_id,
            func.coalesce(Student.full_name, User.full_name),
            Student.admission_number,
            ClassName.classname,
            Section.section_name,
            ExamPaper.classroom_subject_id,
            ClassroomSubject.name,
            Mark.marks_obtained,
            ExamPaper.max_marks,
        )
        .join(Student, Student.id == Mark.student_id)
        # Outer: a student without a login still has marks, and their name comes from
        # the profile.
        .join(User, User.id == Student.user_id, isouter=True)
        .join(Classroom, Classroom.id == Student.classroom_id, isouter=True)
        .join(ClassName, ClassName.class_id == Classroom.class_id, isouter=True)
        .join(Section, Section.section_id == Classroom.section_id, isouter=True)
        .join(ExamPaper, ExamPaper.id == Mark.exam_paper_id)
        .join(Exam, Exam.id == ExamPaper.exam_id)
        .join(
            ClassroomSubject,
            ClassroomSubject.id == ExamPaper.classroom_subject_id,
            isouter=True,
        )
        .order_by(Exam.name, Student.admission_number, ClassroomSubject.name)
    )
    return list(session.exec(statement).all())


def get_students_per_section(session: Session) -> dict[UUID, tuple[int, int, int]]:
    """section_id -> (strength, boys, girls).

    Students with no recorded gender count towards `strength` only, which is why
    boys + girls can be less than strength.
    """
    statement = (
        select(
            Student.classroom_id,
            func.count(Student.id),
            func.sum(case((func.lower(Student.gender) == "male", 1), else_=0)),
            func.sum(case((func.lower(Student.gender) == "female", 1), else_=0)),
        )
        .where(Student.classroom_id.is_not(None))
        .group_by(Student.classroom_id)
    )
    return {
        section_id: (int(total or 0), int(boys or 0), int(girls or 0))
        for section_id, total, boys, girls in session.exec(statement).all()
    }


def get_class_teachers_by_section(session: Session) -> dict[UUID, str]:
    """class-section id -> current year's class teacher name."""
    from app.domains.academic.classroom.students.promotion.class_teacher import (
        current_class_teacher_id,
    )

    result: dict[UUID, str] = {}
    rooms = session.exec(select(Classroom.id)).all()
    for room_id in rooms:
        teacher_id = current_class_teacher_id(session, room_id)
        if teacher_id is None:
            continue
        row = session.exec(
            select(User.full_name)
            .select_from(Employee)
            .join(User, Employee.user_id == User.id)
            .where(Employee.id == teacher_id)
        ).first()
        if row:
            result[room_id] = row
    return result


def get_attendance_per_section(
    session: Session,
) -> dict[UUID, tuple[date, int, float]]:
    """section_id -> (latest register date, present that day, overall %).

    One query over the grouped register; the latest day per section is picked in
    Python so this stays portable and readable.
    """
    attended = func.sum(case((AttendanceRecord.status.in_(_ATTENDED), 1), else_=0))
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
        select(Student.classroom_id, Classroom.class_id)
        .join(Classroom, Classroom.id == Student.classroom_id)
        .where(Student.classroom_id.is_not(None))
    ).all():
        key = section_id
        expected[key] = expected.get(key, 0.0) + per_class.get(classroom_id, 0.0)

    collected: dict[UUID, float] = {}
    statement = (
        select(Student.classroom_id, func.sum(FeeTransaction.amount_paid))
        .join(FeeTransaction, FeeTransaction.student_id == Student.id)
        .where(Student.classroom_id.is_not(None))
        .group_by(Student.classroom_id)
    )
    for section_id, amount in session.exec(statement).all():
        collected[section_id] = float(amount or 0)

    return {
        key: (collected.get(key, 0.0), expected.get(key, 0.0))
        for key in set(expected) | set(collected)
    }


def get_pending_approvals_per_section(session: Session) -> dict[UUID, int]:
    """{section_id: submitted weekly plans} for the Classroom card's badge."""
    from app.domains.academic.classroom.course.models import (
        PLAN_SUBMITTED,
        ClassroomSubject,
        LessonPlan,
    )

    rows = session.exec(
        select(LessonPlan.classroom_subject_id, func.count(LessonPlan.id))
        .where(LessonPlan.status == PLAN_SUBMITTED)
        .group_by(LessonPlan.classroom_subject_id)
    ).all()
    if not rows:
        return {}
    rooms = dict(
        session.exec(select(ClassroomSubject.id, ClassroomSubject.classroom_id)).all()
    )
    pending: dict[UUID, int] = {}
    for course_id, count in rows:
        room_id = rooms.get(course_id)
        if room_id is not None:
            pending[room_id] = pending.get(room_id, 0) + int(count)
    return pending


def get_syllabus_per_section(session: Session) -> dict[UUID, tuple[float, int]]:
    """section_id -> (subject-average %, subjects with a plan), from `chapter_progress`.

    The number comes from `course.completion.subject_average_by_section` - the same D7
    calculation the Course tab's top card shows - so the Classroom card cannot disagree
    with the tab. A subject with no chapters is not part of the average.
    """
    from app.domains.academic.classroom.course import completion

    return completion.subject_average_by_section(session)


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
    """section_id -> timetable periods in the current academic year's week."""
    statement = select(
        TimetablePeriod.classroom_id, func.count(TimetablePeriod.id)
    ).where(TimetablePeriod.classroom_id.is_not(None))
    year_id = current_academic_year_id(session)
    if year_id is not None:
        statement = statement.where(
            or_(
                TimetablePeriod.academic_year_id == year_id,
                TimetablePeriod.academic_year_id.is_(None),
            )
        )
    statement = statement.group_by(TimetablePeriod.classroom_id)
    return {
        section_id: int(count) for section_id, count in session.exec(statement).all()
    }


def get_marks_per_section(session: Session) -> dict[UUID, tuple[float, int]]:
    """section_id -> (average %, number of exams with marks).

    The maximum comes from the paper each student sat (`exam_paper.max_marks`), so a
    mark row carries only the score. An **absent** row has no score and is left out of
    the average rather than counted as a zero.
    """
    percent = Mark.marks_obtained * 100.0 / func.nullif(ExamPaper.max_marks, 0)
    statement = (
        select(
            Student.classroom_id,
            func.avg(percent),
            func.count(func.distinct(ExamPaper.exam_id)),
        )
        .join(Mark, Mark.student_id == Student.id)
        .join(ExamPaper, ExamPaper.id == Mark.exam_paper_id)
        .where(Student.classroom_id.is_not(None), Mark.is_absent.is_(False))
        .group_by(Student.classroom_id)
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
    year_id = current_academic_year_id(session)
    period_statement = select(TimetablePeriod.classroom_id).where(
        TimetablePeriod.classroom_id.is_not(None)
    )
    if year_id is not None:
        period_statement = period_statement.where(
            or_(
                TimetablePeriod.academic_year_id == year_id,
                TimetablePeriod.academic_year_id.is_(None),
            )
        )
    for statement in (
        select(Student.classroom_id)
        .where(Student.classroom_id.is_not(None))
        .distinct(),
        select(Classroom.id).where(Classroom.class_teacher_id.is_not(None)).distinct(),
        period_statement.distinct(),
    ):
        ids.update(session.exec(statement).all())
    return ids


def get_teacher_assignment_classroom_ids(session: Session) -> set[UUID]:
    """Classes with at least one teacher assignment (even with no students yet)."""
    statement = (
        select(ClassroomSubject.classroom_id)
        .join(
            SubjectTeacher, SubjectTeacher.classroom_subject_id == ClassroomSubject.id
        )
        .distinct()
    )
    return set(session.exec(statement).all())


# ---------------------------------------------------------------------------
# Phase 2 - the drill-down behind one class-section
# ---------------------------------------------------------------------------


def get_section(session: Session, section_id: UUID) -> SectionContext | None:
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
    """(employee_id, name, email, phone) of the current year's class teacher."""
    from app.domains.academic.classroom.students.promotion.class_teacher import (
        current_class_teacher_id,
    )

    teacher_id = current_class_teacher_id(session, section_id)
    if teacher_id is None:
        return None
    statement = (
        select(Employee.id, User.full_name, User.email, Employee.phone)
        .select_from(Employee)
        .join(User, Employee.user_id == User.id)
        .where(Employee.id == teacher_id)
    )
    return session.exec(statement).first()


def get_students_in_section(
    session: Session, section_id: UUID
) -> list[tuple[Student, User | None]]:
    """(profile, login) for every student in the section, alphabetical.

    The login is an **outer** join: a student whose admission form gave no email has
    none, and still belongs on the roll - their name comes from the profile.
    """
    statement = (
        select(Student, User)
        .join(User, User.id == Student.user_id, isouter=True)
        .where(Student.classroom_id == section_id)
        .order_by(func.coalesce(Student.full_name, User.full_name))
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
        result[student_id] = round(100.0 * float(attended_count or 0) / float(total), 1)
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
    """The section's D7 completion: the average of each subject's own percentage.

    Read from `course.completion` - the same function the Course tab's top card uses -
    so the header and the tab agree by construction. A section with no planned subject
    is None ("no data"), never 0%.
    """
    from app.domains.academic.classroom.course import completion

    average = completion.for_section_average(session, section_id)
    return average[0] if average is not None else None


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
            ClassroomSubject.name,
            User.full_name,
            TimetablePeriod.room,
        )
        .join(
            ClassroomSubject,
            ClassroomSubject.id == TimetablePeriod.classroom_subject_id,
        )
        .join(Employee, Employee.id == TimetablePeriod.teacher_id)
        .join(User, User.id == Employee.user_id)
        .where(TimetablePeriod.classroom_id == section_id)
        .order_by(TimetablePeriod.day_of_week, TimetablePeriod.start_time)
    )
    year_id = current_academic_year_id(session)
    if year_id is not None:
        statement = statement.where(
            or_(
                TimetablePeriod.academic_year_id == year_id,
                TimetablePeriod.academic_year_id.is_(None),
            )
        )
    return list(session.exec(statement).all())


def get_homework_rows(session: Session, section_id: UUID) -> list[tuple]:
    """(id, title, subject, teacher, due_date) newest due date first."""
    statement = (
        select(
            HomeworkAssignment.id,
            HomeworkAssignment.title,
            ClassroomSubject.name,
            User.full_name,
            HomeworkAssignment.due_date,
        )
        .join(
            ClassroomSubject,
            ClassroomSubject.id == HomeworkAssignment.classroom_subject_id,
        )
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
        homework_id: int(count) for homework_id, count in session.exec(statement).all()
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
    percent = Mark.marks_obtained * 100.0 / func.nullif(ExamPaper.max_marks, 0)
    statement = (
        select(Exam, func.avg(percent), func.count(Mark.id))
        .join(ExamPaper, ExamPaper.exam_id == Exam.id)
        .join(Mark, Mark.exam_paper_id == ExamPaper.id)
        .join(Student, Student.id == Mark.student_id)
        .where(Student.classroom_id == section_id, Mark.is_absent.is_(False))
        .group_by(Exam.id)
        .order_by(Exam.start_date.desc().nullslast(), Exam.name)
    )
    return list(session.exec(statement).all())


def get_subject_mark_rows(session: Session, section_id: UUID) -> list[tuple]:
    """(subject, average %, highest %, lowest %, entries) per subject."""
    percent = Mark.marks_obtained * 100.0 / func.nullif(ExamPaper.max_marks, 0)
    statement = (
        select(
            ClassroomSubject.name,
            func.avg(percent),
            func.max(percent),
            func.min(percent),
            func.count(Mark.id),
        )
        .join(ExamPaper, ExamPaper.classroom_subject_id == ClassroomSubject.id)
        .join(Mark, Mark.exam_paper_id == ExamPaper.id)
        .join(Student, Student.id == Mark.student_id)
        .where(
            Student.classroom_id == section_id,
            ClassroomSubject.classroom_id == section_id,
            Mark.is_absent.is_(False),
        )
        .group_by(ClassroomSubject.name)
        .order_by(ClassroomSubject.name)
    )
    return list(session.exec(statement).all())


# ---------------------------------------------------------------------------
# Assignments - who runs the section, and who takes each subject
# ---------------------------------------------------------------------------


def get_subject_rows(session: Session, section_id: UUID) -> list[tuple]:
    """(classroom_subject_id, name, code, teacher_id, teacher_name) for this section.

    The id is the **section subject** id, not the old school-wide `subject.id`:
    timetable, homework and attendance all write that id. The join onto
    `subjectteacher` is outer and carries the section in its ON clause so subjects
    without a teacher still appear.
    """
    from app.domains.academic.classroom.course.models import ClassroomSubject

    statement = (
        select(
            ClassroomSubject.id,
            ClassroomSubject.name,
            ClassroomSubject.code,
            SubjectTeacher.teacher_id,
            User.full_name,
        )
        .join(
            SubjectTeacher,
            (SubjectTeacher.classroom_subject_id == ClassroomSubject.id)
            & SubjectTeacher.effective_to.is_(None),
            isouter=True,
        )
        .join(Employee, Employee.id == SubjectTeacher.teacher_id, isouter=True)
        .join(User, User.id == Employee.user_id, isouter=True)
        .where(
            ClassroomSubject.classroom_id == section_id,
            ClassroomSubject.status == "Active",
        )
        .order_by(ClassroomSubject.name)
    )
    year_id = current_academic_year_id(session)
    if year_id is not None:
        statement = statement.where(ClassroomSubject.academic_year_id == year_id)
    return list(session.exec(statement).all())


def get_active_teacher_options(session: Session) -> list[tuple]:
    """(employee_id, name, email) for the people who can teach **today**.

    Only a teaching role counts (an accountant is not a subject teacher), and a leaver
    or a deactivated employee is gone: `employee.left_on` / `deactivated_at` NULL plus an
    active login. The tenant filter keeps the list inside this school.
    """
    teaching_users = (
        select(UserRole.user_id)
        .join(Role, Role.id == UserRole.role_id)
        .where(Role.codename.in_(list(TEACHING_ROLES)))
    )
    statement = (
        select(Employee.id, User.full_name, User.email)
        .join(User, User.id == Employee.user_id)
        .where(
            Employee.left_on.is_(None),
            Employee.deactivated_at.is_(None),
            User.is_active == True,  # noqa: E712
            Employee.user_id.in_(teaching_users),
        )
        .order_by(User.full_name)
    )
    return list(session.exec(statement).all())


def get_teacher_options(session: Session) -> list[tuple]:
    """Backward-compatible name for the active-teacher list (same tuple shape)."""
    return get_active_teacher_options(session)
