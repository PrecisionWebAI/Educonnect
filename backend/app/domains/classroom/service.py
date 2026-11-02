"""Assembles the Classroom grid from the repository's per-section roll-ups."""

from datetime import date
from uuid import UUID
from fastapi import HTTPException
from sqlmodel import Session

from . import repository
from .schemas import (
    AttendanceDay,
    ClassGroup,
    ClassTeacherInfo,
    DiaryRow,
    ExamRow,
    HomeworkRow,
    SectionCard,
    SectionDetail,
    SectionStudent,
    SubjectMarkRow,
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
        sections_by_class.setdefault(section.classroom_id, []).append(section)

    groups: list[ClassGroup] = []
    for classroom in repository.get_classrooms(session):
        candidates = sections_by_class.get(classroom.id, [])
        # Only the sections the school actually uses. A class that has *no* such
        # section appears only when a teacher assignment was filed against the
        # class without a section - then every section is worth showing.
        shown = [s for s in candidates if s.id in active_sections]
        if not shown:
            if classroom.id not in teacher_classes:
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
                    sectionName=section.name,
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
                classroomId=classroom.id,
                className=classroom.name,
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


def section_detail(session: Session, section_id: UUID) -> SectionDetail:
    """Everything the drill-down shows for one class-section.

    Every list is read straight from its table; a section with no rows yet comes
    back with an empty list rather than a placeholder row.
    """
    section = repository.get_section(session, section_id)
    if section is None:
        raise HTTPException(status_code=404, detail="Section not found")
    classroom = repository.get_classroom(session, section.classroom_id)
    if classroom is None:
        raise HTTPException(status_code=404, detail="Class not found")

    teacher = repository.get_class_teacher_info(session, section_id)
    students = repository.get_students_in_section(session, section_id)
    attendance_by_student = repository.get_student_attendance(session, section_id)
    fees_by_student = repository.get_student_fees(session)
    per_student_fee = repository.get_fee_total_for_class(session, classroom.id)

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
        DiaryRow(
            id=row_id,
            date=day,
            student=student_name,
            teacher=teacher_name,
            note=note,
        )
        for row_id, day, note, student_name, teacher_name in repository.get_diary_rows(
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

    collected = sum(row.feesPaid for row in student_rows)
    expected = per_student_fee * strength
    return SectionDetail(
        sectionId=section.id,
        classLabel=f"{classroom.name}-{section.name}",
        className=classroom.name,
        stage=classroom.stage,
        classTeacher=(
            ClassTeacherInfo(name=teacher[0], email=teacher[1], phone=teacher[2])
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
    )
