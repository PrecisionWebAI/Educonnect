"""Aggregate reads behind the Classroom cards.

Each function returns a dict keyed by `section_id` (or `classroom_id`) so the
service assembles every card with a fixed number of queries instead of one query
per card. Nothing here invents a value: a section with no rows simply does not
appear in the dict, and the card shows "-".
"""

from datetime import date

from sqlalchemy import case, func
from sqlalchemy.orm import aliased
from sqlmodel import Session, select

from app.domains.academics.models import Classroom, Section, Subject, SyllabusProgress
from app.domains.attendance.models import AttendanceRecord, AttendanceStatus
from app.domains.exams.models import Exam, Mark
from app.domains.finance.models import FeeStructure, FeeTransaction
from app.domains.homework.models import ClassDiary, HomeworkAssignment, HomeworkSubmission
from app.domains.staff.models import Employee
from app.domains.students.models import StudentProfile
from app.domains.teachers.models import ClassTeacherAssignment, TeacherAssignment
from app.domains.timetable.models import TimetablePeriod
from app.domains.users.models import User

#: Statuses that count as "the student was there".
_ATTENDED = (
    AttendanceStatus.present,
    AttendanceStatus.late,
    AttendanceStatus.half_day,
)


# ---------------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------------


def get_classrooms(session: Session) -> list[Classroom]:
    """Every class in the (shared) catalog, in school order."""
    return list(session.exec(select(Classroom).order_by(Classroom.level)).all())


def get_sections(session: Session) -> list[Section]:
    return list(
        session.exec(select(Section).order_by(Section.classroom_id, Section.name)).all()
    )


# ---------------------------------------------------------------------------
# Per-section roll-ups
# ---------------------------------------------------------------------------


def get_students_per_section(session: Session) -> dict[int, tuple[int, int, int]]:
    """section_id -> (strength, boys, girls).

    Students with no recorded gender count towards `strength` only, which is why
    boys + girls can be less than strength.
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


def get_class_teachers_by_section(session: Session) -> dict[int, str]:
    """section_id -> class teacher's name (`classteacherassignment`)."""
    statement = (
        select(ClassTeacherAssignment.section_id, User.full_name)
        .join(Employee, ClassTeacherAssignment.teacher_id == Employee.id)
        .join(User, Employee.user_id == User.id)
        .where(ClassTeacherAssignment.section_id.is_not(None))
    )
    return {
        int(section_id): full_name
        for section_id, full_name in session.exec(statement).all()
    }


def get_attendance_per_section(
    session: Session,
) -> dict[int, tuple[date, int, float]]:
    """section_id -> (latest register date, present that day, overall %).

    One query over the grouped register; the latest day per section is picked in
    Python so this stays portable and readable.
    """
    attended = func.sum(
        case((AttendanceRecord.status.in_(_ATTENDED), 1), else_=0)
    )
    statement = (
        select(
            AttendanceRecord.section_id,
            AttendanceRecord.date,
            func.count(AttendanceRecord.id),
            attended,
        )
        .where(AttendanceRecord.section_id.is_not(None))
        .group_by(AttendanceRecord.section_id, AttendanceRecord.date)
    )

    latest: dict[int, date] = {}
    present: dict[int, int] = {}
    totals: dict[int, list[int]] = {}
    for section_id, day, total, attended_count in session.exec(statement).all():
        key = int(section_id)
        if key not in latest or day > latest[key]:
            latest[key] = day
            present[key] = int(attended_count or 0)
        bucket = totals.setdefault(key, [0, 0])
        bucket[0] += int(total or 0)
        bucket[1] += int(attended_count or 0)

    result: dict[int, tuple[date, int, float]] = {}
    for key, day in latest.items():
        total, attended_count = totals[key]
        percent = round(100.0 * attended_count / total, 1) if total else 0.0
        result[key] = (day, present[key], percent)
    return result


def get_fees_per_section(session: Session) -> dict[int, tuple[float, float]]:
    """section_id -> (collected, expected).

    Expected: every student in the section owes the fee structures filed against
    their class. Collected: the payments recorded for those students.
    """
    per_class = {
        int(classroom_id): float(amount or 0)
        for classroom_id, amount in session.exec(
            select(FeeStructure.classroom_id, func.sum(FeeStructure.amount)).group_by(
                FeeStructure.classroom_id
            )
        ).all()
    }

    expected: dict[int, float] = {}
    for section_id, classroom_id in session.exec(
        select(StudentProfile.section_id, StudentProfile.classroom_id).where(
            StudentProfile.section_id.is_not(None)
        )
    ).all():
        key = int(section_id)
        expected[key] = expected.get(key, 0.0) + per_class.get(
            int(classroom_id or 0), 0.0
        )

    collected: dict[int, float] = {}
    statement = (
        select(StudentProfile.section_id, func.sum(FeeTransaction.amount_paid))
        .join(FeeTransaction, FeeTransaction.student_id == StudentProfile.id)
        .where(StudentProfile.section_id.is_not(None))
        .group_by(StudentProfile.section_id)
    )
    for section_id, amount in session.exec(statement).all():
        collected[int(section_id)] = float(amount or 0)

    return {
        key: (collected.get(key, 0.0), expected.get(key, 0.0))
        for key in set(expected) | set(collected)
    }


def get_syllabus_per_section(session: Session) -> dict[int, tuple[float, int]]:
    """section_id -> (percent complete, subjects tracked)."""
    statement = (
        select(
            SyllabusProgress.section_id,
            func.sum(SyllabusProgress.chapters_total),
            func.sum(SyllabusProgress.chapters_done),
            func.count(SyllabusProgress.id),
        ).group_by(SyllabusProgress.section_id)
    )
    result: dict[int, tuple[float, int]] = {}
    for section_id, total, done, subjects in session.exec(statement).all():
        if not total:
            continue
        result[int(section_id)] = (
            round(100.0 * float(done or 0) / float(total), 1),
            int(subjects or 0),
        )
    return result


def get_open_homework_per_section(session: Session, today: date) -> dict[int, int]:
    """section_id -> assignments whose due date has not passed."""
    statement = (
        select(HomeworkAssignment.section_id, func.count(HomeworkAssignment.id))
        .where(
            HomeworkAssignment.section_id.is_not(None),
            HomeworkAssignment.due_date >= today,
        )
        .group_by(HomeworkAssignment.section_id)
    )
    return {
        int(section_id): int(count) for section_id, count in session.exec(statement).all()
    }


def get_periods_per_section(session: Session) -> dict[int, int]:
    """section_id -> timetable periods in the week."""
    statement = (
        select(TimetablePeriod.section_id, func.count(TimetablePeriod.id))
        .where(TimetablePeriod.section_id.is_not(None))
        .group_by(TimetablePeriod.section_id)
    )
    return {
        int(section_id): int(count) for section_id, count in session.exec(statement).all()
    }


def get_marks_per_section(session: Session) -> dict[int, tuple[float, int]]:
    """section_id -> (average %, number of exams with marks)."""
    percent = Mark.marks_obtained * 100.0 / func.nullif(Mark.max_marks, 0)
    statement = (
        select(
            StudentProfile.section_id,
            func.avg(percent),
            func.count(func.distinct(Mark.exam_id)),
        )
        .join(Mark, Mark.student_id == StudentProfile.id)
        .where(StudentProfile.section_id.is_not(None))
        .group_by(StudentProfile.section_id)
    )
    return {
        int(section_id): (round(float(average or 0), 1), int(exams or 0))
        for section_id, average, exams in session.exec(statement).all()
    }


def get_last_diary_per_section(session: Session) -> dict[int, date]:
    """section_id -> the newest diary date."""
    statement = (
        select(ClassDiary.section_id, func.max(ClassDiary.date))
        .where(ClassDiary.section_id.is_not(None))
        .group_by(ClassDiary.section_id)
    )
    return {
        int(section_id): day
        for section_id, day in session.exec(statement).all()
        if day is not None
    }


def get_active_section_ids(session: Session) -> set[int]:
    """Sections the school actually uses: a student, a class teacher or a period.

    A class with none of those is left out of the grid entirely, which is what
    "show the classroom if any student or teacher is registered for it" means.
    """
    ids: set[int] = set()
    for statement in (
        select(StudentProfile.section_id)
        .where(StudentProfile.section_id.is_not(None))
        .distinct(),
        select(ClassTeacherAssignment.section_id)
        .where(ClassTeacherAssignment.section_id.is_not(None))
        .distinct(),
        select(TimetablePeriod.section_id)
        .where(TimetablePeriod.section_id.is_not(None))
        .distinct(),
    ):
        ids.update(int(value) for value in session.exec(statement).all())
    return ids


def get_teacher_assignment_classroom_ids(session: Session) -> set[int]:
    """Classes with at least one teacher assignment (even with no students yet)."""
    return {
        int(value)
        for value in session.exec(select(TeacherAssignment.classroom_id).distinct()).all()
    }


# ---------------------------------------------------------------------------
# Phase 2 - the drill-down behind one class-section
# ---------------------------------------------------------------------------


def get_section(session: Session, section_id: int) -> Section | None:
    return session.get(Section, section_id)


def get_classroom(session: Session, classroom_id: int) -> Classroom | None:
    return session.get(Classroom, classroom_id)


def get_class_teacher_info(
    session: Session, section_id: int
) -> tuple[str, str, str | None] | None:
    """(name, email, phone) of the section's class teacher, or None."""
    statement = (
        select(User.full_name, User.email, Employee.phone)
        # `select_from` pins the driving table: without it SQLAlchemy cannot tell
        # where the join starts and adds `classteacherassignment` as a second
        # FROM, which cross-joins every row.
        .select_from(ClassTeacherAssignment)
        .join(Employee, ClassTeacherAssignment.teacher_id == Employee.id)
        .join(User, Employee.user_id == User.id)
        .where(ClassTeacherAssignment.section_id == section_id)
        .order_by(ClassTeacherAssignment.id)
    )
    return session.exec(statement).first()


def get_students_in_section(
    session: Session, section_id: int
) -> list[tuple[StudentProfile, User]]:
    """(profile, login) for every student in the section, alphabetical."""
    statement = (
        select(StudentProfile, User)
        .join(User, User.id == StudentProfile.user_id)
        .where(StudentProfile.section_id == section_id)
        .order_by(User.full_name)
    )
    return list(session.exec(statement).all())


def get_student_attendance(session: Session, section_id: int) -> dict[int, float]:
    """student_id -> attendance % for this section."""
    attended = func.sum(case((AttendanceRecord.status.in_(_ATTENDED), 1), else_=0))
    statement = (
        select(AttendanceRecord.student_id, func.count(AttendanceRecord.id), attended)
        .where(AttendanceRecord.section_id == section_id)
        .group_by(AttendanceRecord.student_id)
    )
    result: dict[int, float] = {}
    for student_id, total, attended_count in session.exec(statement).all():
        if not total:
            continue
        result[int(student_id)] = round(
            100.0 * float(attended_count or 0) / float(total), 1
        )
    return result


def get_student_fees(session: Session) -> dict[int, float]:
    """student_id -> total paid (the caller picks the students it needs)."""
    statement = select(
        FeeTransaction.student_id, func.sum(FeeTransaction.amount_paid)
    ).group_by(FeeTransaction.student_id)
    return {
        int(student_id): float(amount or 0)
        for student_id, amount in session.exec(statement).all()
    }


def get_fee_total_for_class(session: Session, classroom_id: int) -> float:
    """What one student in this class owes: the sum of its fee structures."""
    total = session.exec(
        select(func.sum(FeeStructure.amount)).where(
            FeeStructure.classroom_id == classroom_id
        )
    ).one()
    return float(total or 0)


def get_syllabus_percent(session: Session, section_id: int) -> float | None:
    """`chapters_done / chapters_total` for the section, or None when untracked."""
    total, done = session.exec(
        select(
            func.sum(SyllabusProgress.chapters_total),
            func.sum(SyllabusProgress.chapters_done),
        ).where(SyllabusProgress.section_id == section_id)
    ).one()
    if not total:
        return None
    return round(100.0 * float(done or 0) / float(total), 1)


def get_attendance_days(
    session: Session, section_id: int, limit: int = 30
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
        .where(AttendanceRecord.section_id == section_id)
        .group_by(AttendanceRecord.date)
        .order_by(AttendanceRecord.date.desc())
        .limit(limit)
    )
    return list(session.exec(statement).all())


def get_timetable_rows(session: Session, section_id: int) -> list[tuple]:
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
        .where(TimetablePeriod.section_id == section_id)
        .order_by(TimetablePeriod.day_of_week, TimetablePeriod.start_time)
    )
    return list(session.exec(statement).all())


def get_homework_rows(session: Session, section_id: int) -> list[tuple]:
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
        .where(HomeworkAssignment.section_id == section_id)
        .order_by(HomeworkAssignment.due_date.desc(), HomeworkAssignment.id.desc())
    )
    return list(session.exec(statement).all())


def get_submission_counts(session: Session) -> dict[int, int]:
    """homework_id -> how many submissions were handed in."""
    statement = select(
        HomeworkSubmission.homework_id, func.count(HomeworkSubmission.id)
    ).group_by(HomeworkSubmission.homework_id)
    return {
        int(homework_id): int(count)
        for homework_id, count in session.exec(statement).all()
    }


def get_diary_rows(session: Session, section_id: int, limit: int = 50) -> list[tuple]:
    """(id, date, note, student name, teacher name) newest first."""
    student_user = aliased(User)
    teacher_user = aliased(User)
    statement = (
        select(
            ClassDiary.id,
            ClassDiary.date,
            ClassDiary.note,
            student_user.full_name,
            teacher_user.full_name,
        )
        .join(StudentProfile, StudentProfile.id == ClassDiary.student_id)
        .join(student_user, student_user.id == StudentProfile.user_id)
        .join(Employee, Employee.id == ClassDiary.teacher_id)
        .join(teacher_user, teacher_user.id == Employee.user_id)
        .where(ClassDiary.section_id == section_id)
        .order_by(ClassDiary.date.desc(), ClassDiary.id.desc())
        .limit(limit)
    )
    return list(session.exec(statement).all())


def get_exam_rows(session: Session, section_id: int) -> list[tuple]:
    """(exam, average %, marks entered) for exams this section has marks for."""
    percent = Mark.marks_obtained * 100.0 / func.nullif(Mark.max_marks, 0)
    statement = (
        select(Exam, func.avg(percent), func.count(Mark.id))
        .join(Mark, Mark.exam_id == Exam.id)
        .join(StudentProfile, StudentProfile.id == Mark.student_id)
        .where(StudentProfile.section_id == section_id)
        .group_by(Exam.id)
        .order_by(Exam.start_date.desc().nullslast(), Exam.name)
    )
    return list(session.exec(statement).all())


def get_subject_mark_rows(session: Session, section_id: int) -> list[tuple]:
    """(subject, average %, highest %, lowest %, entries) per subject."""
    percent = Mark.marks_obtained * 100.0 / func.nullif(Mark.max_marks, 0)
    statement = (
        select(
            Subject.name,
            func.avg(percent),
            func.max(percent),
            func.min(percent),
            func.count(Mark.id),
        )
        .join(Mark, Mark.subject_id == Subject.id)
        .join(StudentProfile, StudentProfile.id == Mark.student_id)
        .where(StudentProfile.section_id == section_id)
        .group_by(Subject.name)
        .order_by(Subject.name)
    )
    return list(session.exec(statement).all())

