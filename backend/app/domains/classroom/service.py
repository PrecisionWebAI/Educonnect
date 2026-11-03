"""Assembles the Classroom grid from the repository's per-section roll-ups."""

from datetime import date
from uuid import UUID
from fastapi import HTTPException
from sqlmodel import Session, select

from app.domains.academics.models import Section, Subject, SubjectTeacher
from app.domains.auth.models import utcnow
from app.domains.auth.roles import has_role
from app.domains.exams.models import Mark, MarkDispute
from app.domains.staff.models import Employee
from app.domains.students.models import StudentProfile

from . import repository
from .schemas import (
    AttendanceDay,
    ClassGroup,
    ClassResultRead,
    ClassTeacherInfo,
    DiaryRow,
    DisputeCreate,
    DisputeRead,
    DisputeStatusUpdate,
    ExamOptionRead,
    ExamRow,
    HomeworkRow,
    SectionCard,
    SectionDetail,
    SectionMarkRead,
    SectionMarksSave,
    SectionMarkSubjectRead,
    SectionStudent,
    SubjectMarkRow,
    SubjectTeacherRow,
    TeacherOption,
    TimetableSlot,
)


def _percent(collected: float, expected: float) -> float | None:
    """Collected / expected as a percentage, or None when nothing is expected."""
    if expected <= 0:
        return None
    return round(100.0 * collected / expected, 1)


def overview(session: Session) -> list[ClassGroup]:
    """One group per class the school actually uses, each with its section cards.

    A class appears when it has a student, a class teacher, a timetable period or
    a teacher assignment; a section appears when it has any of the first three.
    Everything else is left out, so the grid is the school's real classrooms.
    """
    today = date.today()

    students = repository.get_students_per_section(session)
    teachers = repository.get_class_teachers_by_section(session)
    attendance = repository.get_attendance_per_section(session)
    fees = repository.get_fees_per_section(session)
    syllabus = repository.get_syllabus_per_section(session)
    homework = repository.get_open_homework_per_section(session, today)
    periods = repository.get_periods_per_section(session)
    marks = repository.get_marks_per_section(session)
    diaries = repository.get_last_diary_per_section(session)

    active_sections = repository.get_active_section_ids(session)
    teacher_classes = repository.get_teacher_assignment_classroom_ids(session)

    sections_by_class: dict[UUID, list] = {}
    for section in repository.get_sections(session):
        sections_by_class.setdefault(section.class_id, []).append(section)

    groups: list[ClassGroup] = []
    for classroom in repository.get_classrooms(session):
        candidates = sections_by_class.get(classroom.class_id, [])
        # Only the sections the school actually uses. A class that has *no* such
        # section appears only when a teacher assignment was filed against the
        # class without a section - then every section is worth showing.
        shown = [s for s in candidates if s.id in active_sections]
        if not shown:
            if classroom.class_id not in teacher_classes:
                continue
            shown = candidates

        cards: list[SectionCard] = []
        for section in shown:
            strength, boys, girls = students.get(section.id, (0, 0, 0))
            day, present, attendance_percent = attendance.get(
                section.id, (None, 0, 0.0)
            )
            collected, expected = fees.get(section.id, (0.0, 0.0))
            syllabus_percent, subjects_tracked = syllabus.get(section.id, (None, 0))
            avg_marks, exams = marks.get(section.id, (None, 0))
            cards.append(
                SectionCard(
                    sectionId=section.id,
                    sectionName=section.section_name,
                    classTeacher=teachers.get(section.id),
                    strength=strength,
                    boys=boys,
                    girls=girls,
                    presentToday=present,
                    attendanceDate=day,
                    attendancePercent=(
                        attendance_percent if day is not None else None
                    ),
                    feesExpected=expected or None,
                    feesCollected=collected,
                    feesPercent=_percent(collected, expected),
                    syllabusPercent=syllabus_percent,
                    subjectsTracked=subjects_tracked,
                    homeworkOpen=homework.get(section.id, 0),
                    timetablePeriods=periods.get(section.id, 0),
                    avgMarksPercent=avg_marks,
                    examsCount=exams,
                    lastDiaryDate=diaries.get(section.id),
                )
            )

        if not cards:
            continue
        groups.append(
            ClassGroup(
                classroomId=classroom.class_id,
                className=classroom.classname,
                level=classroom.level,
                stage=classroom.stage,
                strength=sum(card.strength for card in cards),
                sectionCount=len(cards),
                sections=cards,
            )
        )
    return groups


# ---------------------------------------------------------------------------
# Phase 2 - one class-section in full
# ---------------------------------------------------------------------------


#: Roles that look after the whole school, so they may open any class-section.
SCHOOL_WIDE_ROLES = ("system_admin", "school_admin", "principal", "vice_principal", "hod")


def can_open_section(session: Session, user, section_id: UUID) -> bool:
    """May this person open that class-section?

    School-wide roles may open any of them. A teacher may open the ones they
    actually run - the section they are the class teacher of, or one they take a
    subject in. Attendance and the student list live on this page, so a teacher
    who could not open their own section could not take the register at all.
    """
    if has_role(user, *SCHOOL_WIDE_ROLES):
        return True

    section = repository.get_section(session, section_id)
    if section is None:
        return False
    employee = session.exec(
        select(Employee).where(Employee.user_id == user.id)
    ).first()
    if employee is None:
        return False
    if section.class_teacher_id == employee.id:
        return True
    return (
        session.exec(
            select(SubjectTeacher).where(
                SubjectTeacher.classroom_id == section_id,
                SubjectTeacher.teacher_id == employee.id,
            )
        ).first()
        is not None
    )


def section_detail(session: Session, section_id: UUID) -> SectionDetail:
    """Everything the drill-down shows for one class-section.

    Every list is read straight from its table; a section with no rows yet comes
    back with an empty list rather than a placeholder row.
    """
    section = repository.get_section(session, section_id)
    if section is None:
        raise HTTPException(status_code=404, detail="Section not found")
    classroom = repository.get_classroom(session, section.class_id)
    if classroom is None:
        raise HTTPException(status_code=404, detail="Class not found")

    teacher = repository.get_class_teacher_info(session, section_id)
    students = repository.get_students_in_section(session, section_id)
    attendance_by_student = repository.get_student_attendance(session, section_id)
    fees_by_student = repository.get_student_fees(session)
    per_student_fee = repository.get_fee_total_for_class(session, classroom.class_id)

    student_rows: list[SectionStudent] = []
    boys = girls = 0
    for profile, user in students:
        if profile.gender == "Male":
            boys += 1
        elif profile.gender == "Female":
            girls += 1
        paid = fees_by_student.get(profile.id, 0.0)
        student_rows.append(
            SectionStudent(
                studentId=profile.id,
                name=user.full_name,
                admissionNumber=profile.admission_number,
                guardian=profile.guardian_name,
                gender=profile.gender,
                attendancePercent=attendance_by_student.get(profile.id),
                feesPaid=paid,
                feesDue=max(0.0, per_student_fee - paid),
            )
        )

    strength = len(student_rows)
    summary = repository.get_attendance_per_section(session).get(section_id)
    overall_attendance = summary[2] if summary else None

    attendance_rows = [
        AttendanceDay(
            date=day,
            present=int(present or 0),
            absent=int(absent or 0),
            leave=int(leave or 0),
            late=int(late or 0),
            total=int(total or 0),
            percent=(
                round(100.0 * (int(present or 0) + int(late or 0)) / int(total), 1)
                if total
                else 0.0
            ),
        )
        for day, present, absent, leave, late, total in repository.get_attendance_days(
            session, section_id
        )
    ]

    timetable_rows = [
        TimetableSlot(
            day=str(day),
            startTime=start.strftime("%H:%M"),
            endTime=end.strftime("%H:%M"),
            subject=subject,
            teacher=teacher_name,
            room=room,
        )
        for day, start, end, subject, teacher_name, room in repository.get_timetable_rows(
            session, section_id
        )
    ]

    submissions = repository.get_submission_counts(session)
    homework_rows = [
        HomeworkRow(
            id=homework_id,
            title=title,
            subject=subject,
            teacher=teacher_name,
            dueDate=due_date,
            submitted=submissions.get(homework_id, 0),
            total=strength,
        )
        for homework_id, title, subject, teacher_name, due_date in repository.get_homework_rows(
            session, section_id
        )
    ]

    diary_rows = [
        DiaryRow(id=row_id, date=day, note=note, teacher=teacher_name)
        for row_id, day, note, teacher_name in repository.get_diary_rows(
            session, section_id
        )
    ]

    exam_rows = [
        ExamRow(
            id=exam.id,
            name=exam.name,
            term=exam.term,
            status=exam.status,
            averagePercent=round(float(average or 0), 1),
            marksEntered=int(count or 0),
        )
        for exam, average, count in repository.get_exam_rows(session, section_id)
    ]

    mark_rows = [
        SubjectMarkRow(
            subject=subject,
            averagePercent=round(float(average or 0), 1),
            highest=round(float(highest or 0), 1),
            lowest=round(float(lowest or 0), 1),
            entries=int(entries or 0),
        )
        for subject, average, highest, lowest, entries in repository.get_subject_mark_rows(
            session, section_id
        )
    ]

    subject_rows = [
        SubjectTeacherRow(
            subjectId=subject_id,
            name=name,
            code=code,
            teacherId=teacher_id,
            teacherName=teacher_name,
        )
        for subject_id, name, code, teacher_id, teacher_name in repository.get_subject_rows(
            session, section_id
        )
    ]

    collected = sum(row.feesPaid for row in student_rows)
    expected = per_student_fee * strength
    return SectionDetail(
        sectionId=section.id,
        classLabel=f"{classroom.classname}-{section.section_name}",
        className=classroom.classname,
        classroomId=classroom.class_id,
        #: The section letter on its own ("J"). The Students and Attendance views
        #: inside this page scope themselves by class **and** section, so they need
        #: the two names apart, not just the joined label.
        sectionName=section.section_name,
        stage=classroom.stage,
        classTeacher=(
            ClassTeacherInfo(
                employeeId=teacher[0],
                name=teacher[1],
                email=teacher[2],
                phone=teacher[3],
            )
            if teacher
            else None
        ),
        strength=strength,
        boys=boys,
        girls=girls,
        attendancePercent=overall_attendance,
        syllabusPercent=repository.get_syllabus_percent(session, section_id),
        feesExpected=expected or None,
        feesCollected=collected,
        feesPercent=_percent(collected, expected),
        students=student_rows,
        attendance=attendance_rows,
        timetable=timetable_rows,
        homework=homework_rows,
        diary=diary_rows,
        exams=exam_rows,
        marks=mark_rows,
        subjects=subject_rows,
    )


# ---------------------------------------------------------------------------
# Marks of one class-section - the Academics tab
# ---------------------------------------------------------------------------


def section_marks(session: Session, section_id: UUID) -> list[SectionMarkRead]:
    """The class-section's marks: one entry per student per exam.

    Grouped here rather than in the client, so a screen renders rows it can trust.
    Each subject row carries its own `max`, straight from the exam - the score and
    the "out of" number can never disagree.
    """
    section = repository.get_section(session, section_id)
    if section is None:
        raise HTTPException(status_code=404, detail="Section not found")
    classroom = repository.get_classroom(session, section.class_id)
    label = f"{classroom.classname}-{section.section_name}" if classroom else section.section_name

    people = {
        profile.id: (user.full_name, profile.admission_number)
        for profile, user in repository.get_students_in_section(session, section_id)
    }

    grouped: dict[tuple[UUID, UUID], SectionMarkRead] = {}
    for (
        exam_id,
        exam_name,
        student_id,
        subject_id,
        subject_name,
        obtained,
        max_marks,
    ) in repository.get_section_marks(session, section_id):
        key = (exam_id, student_id)
        entry = grouped.get(key)
        if entry is None:
            name, admission = people.get(student_id, ("", ""))
            entry = SectionMarkRead(
                studentId=student_id,
                studentName=name,
                admissionNumber=admission,
                className=label,
                examId=exam_id,
                exam=exam_name,
                rows=[],
            )
            grouped[key] = entry
        entry.rows.append(
            SectionMarkSubjectRead(
                subjectId=subject_id,
                subject=subject_name,
                obtained=float(obtained),
                max=float(max_marks),
            )
        )
    return list(grouped.values())


def save_section_marks(
    session: Session, section_id: UUID, payload: SectionMarksSave, user
) -> int:
    """Write the scores entered for this class-section. Returns the rows written.

    Every student is checked against the section first: a mark filed for a student
    of another class-section would put them in two places at once. An existing row
    is updated and a missing one created - the table is unique on
    (exam, student, subject), so saving twice can never double a score.
    """
    if repository.get_section(session, section_id) is None:
        raise HTTPException(status_code=404, detail="Section not found")

    allowed = {
        profile.id
        for profile, _ in repository.get_students_in_section(session, section_id)
    }
    written = 0
    for entry in payload.entries:
        if entry.student_id not in allowed:
            raise HTTPException(
                status_code=422,
                detail="That student is not in this class-section.",
            )
        mark = repository.get_mark(
            session, payload.exam_id, entry.student_id, entry.subject_id
        )
        if mark is None:
            mark = Mark(
                exam_id=payload.exam_id,
                student_id=entry.student_id,
                subject_id=entry.subject_id,
                marks_obtained=entry.marks_obtained,
                entered_by=user.id,
            )
        else:
            mark.marks_obtained = entry.marks_obtained
            mark.entered_by = user.id
        session.add(mark)
        written += 1
    session.commit()
    return written


# ---------------------------------------------------------------------------
# School-wide results and mark disputes - the Classroom grid's tabs
# ---------------------------------------------------------------------------

#: A mark passes at this percentage of the maximum the exam declared.
PASS_PERCENT = 40.0

#: Where a challenge can be: the wording the screen shows is the stored value.
DISPUTE_STATUSES = ("Open", "Under Review", "Resolved")


def results(session: Session) -> list[ClassResultRead]:
    """Pass rate, average and topper per class, exam by exam.

    A mark passes at 40% of the maximum its exam declared for that subject; the
    topper is the student with the highest total percentage in that class's exam.
    A class with no marks simply does not appear.
    """
    buckets: dict[tuple[UUID, UUID], dict] = {}
    for (
        exam_id,
        exam_name,
        classroom_id,
        classroom_name,
        student_id,
        student_name,
        obtained,
        max_marks,
    ) in repository.get_marks_for_results(session):
        bucket = buckets.setdefault(
            (exam_id, classroom_id),
            {
                "exam": exam_name,
                "class": classroom_name,
                "passed": 0,
                "count": 0,
                "sum": 0.0,
                "students": {},
            },
        )
        percent = (obtained * 100.0 / max_marks) if max_marks else 0.0
        bucket["count"] += 1
        bucket["sum"] += percent
        if percent >= PASS_PERCENT:
            bucket["passed"] += 1
        student = bucket["students"].setdefault(
            student_id, {"name": student_name, "obtained": 0.0, "max": 0.0}
        )
        student["obtained"] += obtained
        student["max"] += max_marks

    rows: list[ClassResultRead] = []
    for (exam_id, classroom_id), bucket in buckets.items():
        count = bucket["count"]
        topper = max(
            bucket["students"].values(),
            key=lambda s: (s["obtained"] / s["max"]) if s["max"] else 0.0,
            default=None,
        )
        rows.append(
            ClassResultRead(
                id=f"{exam_id}:{classroom_id}",
                exam=bucket["exam"],
                className=bucket["class"],
                passRate=round(100.0 * bucket["passed"] / count, 1) if count else 0.0,
                avgScore=round(bucket["sum"] / count, 1) if count else 0.0,
                topper=topper["name"] if topper else "",
            )
        )
    return sorted(rows, key=lambda row: (row.exam, row.className))


def exams(session: Session) -> list[ExamOptionRead]:
    """The exams a dispute can be filed against."""
    return [
        ExamOptionRead(id=exam.id, name=exam.name)
        for exam in repository.get_exams(session)
    ]


def _dispute_read(row) -> DisputeRead:
    return DisputeRead(
        id=row[0],
        student=row[1],
        exam=row[2],
        subject=row[3],
        reason=row[4],
        status=row[5],
    )


def disputes(session: Session) -> list[DisputeRead]:
    """Every challenge, newest first."""
    return [_dispute_read(row) for row in repository.get_disputes(session)]


def raise_dispute(session: Session, payload: DisputeCreate, user) -> DisputeRead:
    """Log a challenge against one student's mark in one exam + subject.

    The student must be on the roll (a challenge about nobody is a typo), but the
    *mark* does not have to exist yet: a family can question a score before it is
    entered, and the office still has to answer it.
    """
    if session.get(StudentProfile, payload.student_id) is None:
        raise HTTPException(status_code=422, detail="That student is not on the roll.")
    if not payload.reason.strip():
        raise HTTPException(status_code=422, detail="A reason is required.")

    dispute = MarkDispute(
        student_id=payload.student_id,
        exam_id=payload.exam_id,
        subject_id=payload.subject_id,
        reason=payload.reason.strip(),
        status=DISPUTE_STATUSES[0],
        raised_by=user.id,
    )
    session.add(dispute)
    session.commit()
    session.refresh(dispute)
    row = repository.get_dispute_read(session, dispute.id)
    if row is None:  # pragma: no cover - the row was just written
        raise HTTPException(status_code=404, detail="Dispute not found")
    return _dispute_read(row)


def set_dispute_status(
    session: Session, dispute_id: UUID, update: DisputeStatusUpdate
) -> DisputeRead:
    """Move a challenge along: Open -> Under Review -> Resolved."""
    if update.status not in DISPUTE_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown dispute status '{update.status}'. "
            f"Expected one of: {', '.join(DISPUTE_STATUSES)}",
        )
    dispute = repository.get_dispute(session, dispute_id)
    if dispute is None:
        raise HTTPException(status_code=404, detail="Dispute not found")
    dispute.status = update.status
    dispute.resolved_at = utcnow() if update.status == "Resolved" else None
    session.add(dispute)
    session.commit()
    row = repository.get_dispute_read(session, dispute_id)
    if row is None:  # pragma: no cover - the row exists
        raise HTTPException(status_code=404, detail="Dispute not found")
    return _dispute_read(row)


# ---------------------------------------------------------------------------
# Assignments - the two things a class-section needs from a teacher
# ---------------------------------------------------------------------------


def _require_employee(session: Session, employee_id: UUID) -> Employee:
    """The teacher must exist in this school.

    `session.get` runs through the tenant filter, so another school's employee id
    reads as missing rather than being assignable.
    """
    employee = session.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(status_code=404, detail="Teacher not found")
    return employee


def assign_class_teacher(
    session: Session, section_id: UUID, teacher_id: UUID | None
) -> None:
    """Set (or clear, with `None`) the section's class teacher.

    One column, so "at most one class teacher per section" is the schema's rule
    rather than something this function has to enforce.
    """
    section = repository.get_section(session, section_id)
    if section is None:
        raise HTTPException(status_code=404, detail="Class-section not found")
    if teacher_id is not None:
        _require_employee(session, teacher_id)
    section.class_teacher_id = teacher_id
    session.add(section)
    session.commit()


def assign_subject_teacher(
    session: Session, section_id: UUID, subject_id: UUID, teacher_id: UUID | None
) -> None:
    """Set (or clear, with `None`) who takes one subject in one section."""
    if repository.get_section(session, section_id) is None:
        raise HTTPException(status_code=404, detail="Class-section not found")
    if session.get(Subject, subject_id) is None:
        raise HTTPException(status_code=404, detail="Subject not found")

    existing = session.exec(
        select(SubjectTeacher).where(
            SubjectTeacher.classroom_id == section_id,
            SubjectTeacher.subject_id == subject_id,
        )
    ).first()

    if teacher_id is None:
        if existing is not None:
            session.delete(existing)
            session.commit()
        return

    _require_employee(session, teacher_id)
    if existing is None:
        session.add(
            SubjectTeacher(
                section_id=section_id, subject_id=subject_id, teacher_id=teacher_id
            )
        )
    else:
        existing.teacher_id = teacher_id
        session.add(existing)
    session.commit()


def teacher_options(session: Session) -> list[TeacherOption]:
    """Every teacher this school can put in front of a class."""
    return [
        TeacherOption(employeeId=employee_id, name=name, email=email)
        for employee_id, name, email in repository.get_teacher_options(session)
    ]
