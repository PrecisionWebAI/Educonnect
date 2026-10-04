"""Fill every remaining table so no screen has to invent a value.

Why this file exists:
  The academics and operations seeds cover the school (classes, students,
  attendance) and the four Operations screens. Everything else the product reads
  - subjects, timetables, homework, the subject-teacher map, parent links, the
  chat threads, the content library, the parent/guardian relationships, the
  question-usage ledger - still had one or two rows, or none at all, so those
  screens either looked empty or fell back to hardcoded arrays.

  This script gives every table at least ten varied rows, and deliberately
  spreads each one across the states its screen can show (every attendance
  status, every payment mode, every hiring stage, every paper status, a fee head
  that is still a draft, ...). A demo that only contains happy rows cannot show
  a badge, a filter or a warning.

Idempotent: each block is skipped as soon as its table already holds the target
  number of rows, so this is safe on every container start (bootstrap.py calls
  it) and by hand:

    docker exec eduverse-backend python scripts/seed_sample_data.py

Order: it runs after `seed_academics.py` (classes, sections, students, teachers)
and after `seed_operations.py` (the first fee heads, vacancies, applications).
"""

import hashlib
import os
import re
import sys
from datetime import date, datetime, time, timedelta

from sqlalchemy import func
from sqlmodel import Session, select

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.db import engine
from app.domains.academics.models import Classroom, Section, Subject
from app.domains.admissions.models import (
    STATUS_DRAFT,
    STATUS_REGISTERED,
    AdmissionApplication,
)
from app.domains.attendance.models import (
    AttendanceAuditLog,
    AttendanceRecord,
    AttendanceStatus,
)
from app.domains.auth.models import (
    ImpersonationLog,
    Role,
    UserRole,
)
from app.domains.chat.models import ChatMessage, ChatThread, ChatThreadParticipant
from app.domains.exams.models import (
    CoverageMode,
    ExamSource,
    GenerationJob,
    GenerationJobStatus,
    PaperDraft,
    QuestionUsageLog,
    SourceType,
)
from app.domains.finance.models import (
    FeeFrequency,
    FeeStructure,
    FeeTransaction,
    PaymentMode,
)
from app.domains.hiring.models import HiringCandidate, StaffVacancy
from app.domains.homework.models import (
    ClassDiary,
    HomeworkAssignment,
    HomeworkSubmission,
    SubmissionStatus,
)
from app.domains.students.models import StudentParentRelationship, StudentProfile
from app.domains.teachers.models import (
    TeacherAssignment,
    TeacherProfile,
)
from app.domains.timetable.models import DayOfWeek, TimetablePeriod
from app.domains.users.models import User

#: Every block stops as soon as its table holds this many rows.
TARGET_ROWS = 10

SUBJECTS: tuple[tuple[str, str], ...] = (
    ("English", "ENG"),
    ("Mathematics", "MAT"),
    ("Science", "SCI"),
    ("Physics", "PHY"),
    ("Chemistry", "CHE"),
    ("Biology", "BIO"),
    ("Social Studies", "SOC"),
    ("Computer Science", "CMP"),
    ("Hindi", "HIN"),
    ("Physical Education", "PED"),
    ("Art", "ART"),
    ("Music", "MUS"),
)

WEEKDAYS: tuple[DayOfWeek, ...] = (
    DayOfWeek.monday,
    DayOfWeek.tuesday,
    DayOfWeek.wednesday,
    DayOfWeek.thursday,
    DayOfWeek.friday,
)

#: (start, end, room) - six periods a day, so a timetable actually looks full.
PERIOD_SLOTS: tuple[tuple[time, time, str], ...] = tuple(
    (time(8 + offset, 0), time(8 + offset, 45), f"Room {101 + offset}")
    for offset in range(6)
)

PAYMENT_MODES: tuple[PaymentMode, ...] = (
    PaymentMode.cash,
    PaymentMode.upi,
    PaymentMode.card,
    PaymentMode.cheque,
    PaymentMode.bank_transfer,
)


def _count(session: Session, model: type) -> int:
    """Rows in one table - the guard every block starts with."""
    return int(session.exec(select(func.count()).select_from(model)).one())


def _classrooms(session: Session) -> list[Classroom]:
    return list(session.exec(select(Classroom).order_by(Classroom.level)).all())


def _sections_of(session: Session, classroom_id: int) -> list[Section]:
    return list(
        session.exec(
            select(Section).where(Section.classroom_id == classroom_id)
        ).all()
    )


def _students(session: Session) -> list[StudentProfile]:
    return list(session.exec(select(StudentProfile)).all())


def _teachers(session: Session) -> list[TeacherProfile]:
    return list(session.exec(select(TeacherProfile)).all())


def _users_with_role(session: Session, codename: str) -> list[User]:
    return list(
        session.exec(
            select(User)
            .join(UserRole, UserRole.user_id == User.id)  # type: ignore[arg-type]
            .join(Role, Role.id == UserRole.role_id)  # type: ignore[arg-type]
            .where(Role.codename == codename)
        ).all()
    )


# ---------------------------------------------------------------------------
# 1. Subjects - the catalog every other table points at
# ---------------------------------------------------------------------------


def _seed_subjects(session: Session) -> None:
    created = 0
    for name, code in SUBJECTS:
        exists = session.exec(
            select(Subject).where(
                (Subject.name == name) | (Subject.code == code)  # type: ignore[operator]
            )
        ).first()
        if exists is not None:
            continue
        session.add(Subject(name=name, code=code))
        created += 1
    if created:
        session.commit()
        print(f"[seed_sample] {created} subject(s) created")


# ---------------------------------------------------------------------------
# 2. Parent links - which guardian belongs to which student
# ---------------------------------------------------------------------------


def _seed_parent_links(session: Session) -> None:
    if _count(session, StudentParentRelationship) >= 40:
        print("[seed_sample] parent links already exist. Skipping...")
        return

    guardians = _users_with_role(session, "guardian")
    students = _students(session)
    if not guardians or not students:
        print("[seed_sample] no guardians/students yet - parent links skipped")
        return

    relationships = ("Father", "Mother", "Guardian")
    existing = {
        (row.student_id, row.parent_user_id)
        for row in session.exec(select(StudentParentRelationship)).all()
    }
    created = 0
    for index, student in enumerate(students[:20]):
        for offset in range(2):
            parent = guardians[(index + offset) % len(guardians)]
            key = (student.id, parent.id)
            if key in existing:
                continue
            session.add(
                StudentParentRelationship(
                    student_id=student.id,
                    parent_user_id=parent.id,
                    relationship_type=relationships[(index + offset) % 3],
                )
            )
            existing.add(key)
            created += 1
    session.commit()
    print(f"[seed_sample] {created} parent link(s) created")


# ---------------------------------------------------------------------------
# 3. Subject teachers - who teaches what, where
# ---------------------------------------------------------------------------


def _seed_teacher_assignments(session: Session) -> None:
    if _count(session, TeacherAssignment) >= TARGET_ROWS:
        print("[seed_sample] subject-teacher rows already exist. Skipping...")
        return

    teachers = _teachers(session)
    classrooms = _classrooms(session)
    subjects = list(session.exec(select(Subject)).all())
    if not (teachers and classrooms and subjects):
        print("[seed_sample] teachers/classes/subjects missing - skipped")
        return

    # Every (class, section) pair is one slot, and each assignment takes its own
    # slot: two teachers are never put on the same subject in the same section,
    # which would make the Classroom screen show the class twice.
    slots: list[tuple[Classroom, Section]] = [
        (classroom, section)
        for classroom in classrooms
        for section in _sections_of(session, classroom.id)  # type: ignore[arg-type]
    ]
    if not slots:
        print("[seed_sample] no sections yet - subject teachers skipped")
        return

    created = 0
    for index, teacher in enumerate(teachers):
        for offset in range(3):  # three subjects each
            position = index * 3 + offset
            classroom, section = slots[position % len(slots)]
            session.add(
                TeacherAssignment(
                    teacher_id=teacher.id,
                    classroom_id=classroom.id,
                    section_id=section.id,
                    subject_id=subjects[position % len(subjects)].id,
                )
            )
            created += 1
    session.commit()
    print(f"[seed_sample] {created} subject-teacher assignment(s) created")


# ---------------------------------------------------------------------------
# 4. Timetable - a full week for a couple of sections
# ---------------------------------------------------------------------------


def _seed_timetable(session: Session) -> None:
    if _count(session, TimetablePeriod) >= TARGET_ROWS:
        print("[seed_sample] timetable periods already exist. Skipping...")
        return

    classrooms = _classrooms(session)
    teachers = _teachers(session)
    subjects = list(session.exec(select(Subject)).all())
    if not (classrooms and teachers and subjects):
        print("[seed_sample] classes/teachers/subjects missing - timetable skipped")
        return

    # Two sections get a complete week; the others stay empty on purpose, which
    # is what a school that has not finished its timetable actually looks like.
    targets: list[tuple[Classroom, Section]] = []
    for classroom in classrooms[-2:]:
        sections = _sections_of(session, classroom.id)  # type: ignore[arg-type]
        if sections:
            targets.append((classroom, sections[0]))

    created = 0
    for class_index, (classroom, section) in enumerate(targets):
        for day_index, day in enumerate(WEEKDAYS):
            for slot_index, (start, end, room) in enumerate(PERIOD_SLOTS):
                seed = class_index * 100 + day_index * 10 + slot_index
                session.add(
                    TimetablePeriod(
                        classroom_id=classroom.id,
                        section_id=section.id,
                        subject_id=subjects[seed % len(subjects)].id,
                        teacher_id=teachers[seed % len(teachers)].id,
                        day_of_week=day,
                        start_time=start,
                        end_time=end,
                        room=room,
                    )
                )
                created += 1
    session.commit()
    print(f"[seed_sample] {created} timetable period(s) created")



# ---------------------------------------------------------------------------
# 5. Homework, submissions and the class diary
# ---------------------------------------------------------------------------

HOMEWORK_TASKS: tuple[tuple[str, str], ...] = (
    ("Algebra worksheet", "Solve exercises 1-10 from the chapter."),
    ("Electricity circuit lab", "Build a series circuit and record observations."),
    ("Essay - My School", "Write a 300-word essay about your school."),
    ("Map work - Rivers of India", "Mark the major rivers on the outline map."),
    ("Trigonometry practice", "Complete questions 1-15 of the worksheet."),
    ("Photosynthesis diagram", "Draw and label the process in your notebook."),
)


def _seed_homework(session: Session) -> None:
    if _count(session, HomeworkAssignment) >= TARGET_ROWS:
        print("[seed_sample] homework already exists. Skipping...")
    else:
        classrooms = _classrooms(session)
        teachers = _teachers(session)
        subjects = list(session.exec(select(Subject)).all())
        created = 0
        for class_index, classroom in enumerate(classrooms[:6]):
            sections = _sections_of(session, classroom.id)  # type: ignore[arg-type]
            if not (sections and teachers and subjects):
                continue
            for offset in range(3):
                title, description = HOMEWORK_TASKS[
                    (class_index + offset) % len(HOMEWORK_TASKS)
                ]
                session.add(
                    HomeworkAssignment(
                        title=f"{title} - {classroom.name}",
                        description=description,
                        classroom_id=classroom.id,
                        section_id=sections[0].id,
                        subject_id=subjects[(class_index + offset) % len(subjects)].id,
                        teacher_id=teachers[(class_index + offset) % len(teachers)].id,
                        due_date=date.today() + timedelta(days=offset + 1),
                    )
                )
                created += 1
        session.commit()
        print(f"[seed_sample] {created} homework assignment(s) created")

    if _count(session, HomeworkSubmission) >= 30:
        print("[seed_sample] submissions already exist. Skipping...")
        return

    statuses = (
        SubmissionStatus.submitted,
        SubmissionStatus.graded,
        SubmissionStatus.pending,
    )
    created = 0
    for index, homework in enumerate(session.exec(select(HomeworkAssignment)).all()):
        classmates = list(
            session.exec(
                select(StudentProfile)
                .where(StudentProfile.classroom_id == homework.classroom_id)
                .order_by(StudentProfile.id)  # type: ignore[arg-type]
            ).all()
        )
        for offset, student in enumerate(classmates[:2]):
            status = statuses[(index + offset) % len(statuses)]
            session.add(
                HomeworkSubmission(
                    homework_id=homework.id,
                    student_id=student.id,
                    content_url=(
                        None
                        if status is SubmissionStatus.pending
                        else f"https://files.educonnect.local/homework/"
                        f"{homework.id}-{student.id}.pdf"
                    ),
                    status=status,
                    teacher_feedback=(
                        "Well written, keep it up."
                        if status is SubmissionStatus.graded
                        else None
                    ),
                )
            )
            created += 1
    session.commit()
    print(f"[seed_sample] {created} homework submission(s) created")


def _seed_diary(session: Session) -> None:
    if _count(session, ClassDiary) >= TARGET_ROWS:
        print("[seed_sample] diary notes already exist. Skipping...")
        return

    teachers = _teachers(session)
    students = _students(session)
    if not (teachers and students):
        print("[seed_sample] teachers/students missing - diary skipped")
        return

    notes = (
        "Helped with the maths doubts after class.",
        "Answered the science question well today.",
        "Needs to complete the pending notebook work.",
        "Read aloud confidently in the English period.",
        "Forgot the sports kit; reminded about the timetable.",
    )
    created = 0
    for index, student in enumerate(students[:15]):
        session.add(
            ClassDiary(
                student_id=student.id,
                teacher_id=teachers[index % len(teachers)].id,
                date=date.today() - timedelta(days=index % 7),
                note=notes[index % len(notes)],
            )
        )
        created += 1
    session.commit()
    print(f"[seed_sample] {created} diary note(s) created")



# ---------------------------------------------------------------------------
# 6. Attendance audit trail - who corrected what
# ---------------------------------------------------------------------------


def _seed_attendance_audit(session: Session) -> None:
    if _count(session, AttendanceAuditLog) >= TARGET_ROWS:
        print("[seed_sample] attendance audit rows already exist. Skipping...")
        return

    staff = _users_with_role(session, "teacher") or list(
        session.exec(select(User)).all()
    )
    if not staff:
        print("[seed_sample] no staff logins - attendance audit skipped")
        return

    # Only records that are *not* `present` are interesting: those are the ones
    # an office actually corrects.
    candidates = list(
        session.exec(
            select(AttendanceRecord)
            .where(AttendanceRecord.status != AttendanceStatus.present)
            .order_by(AttendanceRecord.id)  # type: ignore[arg-type]
        ).all()
    )
    if not candidates:
        print("[seed_sample] no correctable attendance rows - audit skipped")
        return

    created = 0
    for index, record in enumerate(candidates[:24]):
        corrected = index % 3 == 0  # two thirds stay as they are
        session.add(
            AttendanceAuditLog(
                attendance_record_id=record.id,
                changed_by_id=staff[index % len(staff)].id,
                changed_at=datetime(2026, 4, 1, 9, 30) + timedelta(hours=index),
                previous_status=record.status,
                new_status=(AttendanceStatus.present if corrected else record.status),
                previous_remarks=record.remarks,
                new_remarks=(
                    "Marked present after the leave note was produced."
                    if corrected
                    else record.remarks
                ),
            )
        )
        created += 1
    session.commit()
    print(f"[seed_sample] {created} attendance audit row(s) created")


# ---------------------------------------------------------------------------
# 7. Chat - two group threads and a history of messages
# ---------------------------------------------------------------------------

GROUP_THREADS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Class 10-A Parents", ("parent@educonnect.com", "teacher@educonnect.com")),
    ("Science Department", ("principal@educonnect.com", "hod@educonnect.com")),
    ("Class 9-B Parents", ("parent@educonnect.com", "teacher@educonnect.com")),
    ("Front Office", ("admin@educonnect.com", "accountant@educonnect.com")),
    ("Transport Desk", ("transport@educonnect.com", "admin@educonnect.com")),
    ("Senior Secondary Staff", ("viceprincipal@educonnect.com", "hod@educonnect.com")),
)

CHAT_LINES: tuple[str, ...] = (
    "Good morning everyone.",
    "Please check the updated timetable for this week.",
    "The unit test syllabus is on the notice board.",
    "Homework submissions close on Friday.",
    "Can we move the lab session to Thursday?",
    "The fee receipt has been shared with the office.",
    "Thanks for the quick response.",
    "Noted, I will pass it on to the class.",
)


def _seed_chat(session: Session) -> None:
    users = list(session.exec(select(User).order_by(User.id)).all())  # type: ignore[arg-type]
    if not users:
        print("[seed_sample] no logins - chat skipped")
        return

    by_email = {user.email: user for user in users}
    for name, emails in GROUP_THREADS:
        thread = session.exec(select(ChatThread).where(ChatThread.name == name)).first()
        if thread is not None:
            continue
        thread = ChatThread(name=name, is_group=True)
        session.add(thread)
        session.commit()
        session.refresh(thread)
        for email in emails:
            user = by_email.get(email)
            if user is None:
                continue
            session.add(
                ChatThreadParticipant(thread_id=thread.id, user_id=user.id)
            )
        session.commit()
        print(f"[seed_sample] group thread '{name}' created")

    if _count(session, ChatMessage) >= 30:
        print("[seed_sample] chat messages already exist. Skipping...")
        return

    threads = list(session.exec(select(ChatThread)).all())
    created = 0
    for thread_index, thread in enumerate(threads):
        participants = [
            row.user_id
            for row in session.exec(
                select(ChatThreadParticipant).where(
                    ChatThreadParticipant.thread_id == thread.id
                )
            ).all()
        ] or [user.id for user in users[:2]]
        for offset in range(8):
            session.add(
                ChatMessage(
                    thread_id=thread.id,
                    sender_id=participants[offset % len(participants)],
                    content_text=CHAT_LINES[(thread_index + offset) % len(CHAT_LINES)],
                    created_at=datetime(2026, 4, 2, 9, 0)
                    + timedelta(hours=offset, days=thread_index),
                )
            )
            created += 1
    session.commit()
    print(f"[seed_sample] {created} chat message(s) created")



# ---------------------------------------------------------------------------
# 8. Content library (RAG sources) + the anti-repeat ledger
# ---------------------------------------------------------------------------

#: (source type, title, status, kind, strictness). One of each status, because
#: the library screen filters on them and a stuck "failed" row is a real state.
EXAM_SOURCES: tuple[tuple[SourceType, str, str, str, str], ...] = (
    (SourceType.pdf, "Class 10 Science - chapter pack", "ready", "knowledge", "Strict"),
    (SourceType.pdf, "Class 9 Mathematics - question bank", "ready", "knowledge", "Strict"),
    (SourceType.image, "Class 8 Science - lab manual page", "ready", "knowledge", "Flexible"),
    (SourceType.url, "CBSE sample paper portal", "ready", "pattern", "Strict"),
    (SourceType.text, "Class 12 Physics - formula sheet", "ready", "knowledge", "Creative"),
    (SourceType.bank, "Class 7 English - grammar bank", "ready", "pattern", "Strict"),
    (SourceType.pdf, "Class 11 Chemistry - organic notes", "pending", "knowledge", "Strict"),
    (SourceType.image, "Class 6 History - map scan", "pending", "knowledge", "Flexible"),
    (SourceType.url, "Class 5 EVS - reading list", "failed", "knowledge", "Strict"),
    (SourceType.text, "Class 4 Mathematics - tables", "ready", "knowledge", "Strict"),
    (SourceType.bank, "Class 3 English - sight words", "ready", "pattern", "Flexible"),
    (SourceType.pdf, "Class 12 Biology - genetics diagrams", "ingesting", "knowledge", "Strict"),
)

CHAPTERS: tuple[str, ...] = (
    "Real Numbers",
    "Light - Reflection and Refraction",
    "Life Processes",
    "Force and Pressure",
    "Trigonometry",
    "Chemical Reactions",
)


def _class_from_title(title: str, by_name: dict[str, Classroom]) -> Classroom | None:
    """The class a source title names ("Class 10 Science - ..."), if it names one."""
    match = re.search(r"Class\s+(\d+)", title)
    return by_name.get(f"Class {match.group(1)}") if match else None


def _subject_named(title: str, subjects: list[Subject]) -> Subject | None:
    """The subject a source title mentions, so the filter and the title agree."""
    lowered = title.lower()
    for subject in subjects:
        if subject.name.lower() in lowered:
            return subject
    return None


def _seed_exam_sources(session: Session) -> None:
    if _count(session, ExamSource) >= TARGET_ROWS:
        print("[seed_sample] content library already populated. Skipping...")
        return

    classrooms = _classrooms(session)
    by_name = {classroom.name: classroom for classroom in classrooms}
    subjects = list(session.exec(select(Subject)).all())
    staff = _users_with_role(session, "teacher") or list(
        session.exec(select(User)).all()
    )
    created = 0
    for index, (source_type, title, status, kind, strictness) in enumerate(EXAM_SOURCES):
        # The class and the subject come from the title whenever it says them -
        # otherwise the library would file a Class 10 chapter pack under Nursery.
        classroom = _class_from_title(title, by_name)
        if classroom is None and classrooms:
            classroom = classrooms[index % len(classrooms)]
        subject = _subject_named(title, subjects)
        if subject is None and subjects:
            subject = subjects[index % len(subjects)]
        content_hash = hashlib.sha256(title.encode("utf-8")).hexdigest()
        session.add(
            ExamSource(
                source_type=source_type,
                title=title,
                kind=kind,
                strictness=strictness,
                status=status,
                class_name=classroom.name if classroom else "",
                subject=subject.name if subject else "",
                board=("CBSE", "ICSE", "State")[index % 3],
                teacher_name=(
                    session.get(User, staff[index % len(staff)].id).full_name  # type: ignore[union-attr]
                    if staff
                    else ""
                ),
                tags=["demo", source_type.value],
                chapters=list(CHAPTERS[: 2 + index % 3]),
                classroom_id=classroom.id if classroom else None,
                subject_id=subject.id if subject else None,
                created_by=staff[index % len(staff)].id if staff else None,
                chunk_count=0 if status in {"pending", "failed"} else 12 + index,
                error=(
                    "Could not reach the URL (timeout after 30s)."
                    if status == "failed"
                    else None
                ),
                content_hash=content_hash,
            )
        )
        created += 1
    session.commit()
    print(f"[seed_sample] {created} content-library source(s) created")


#: (quality type, marks, chapter/topic pair)
USED_QUESTIONS: tuple[tuple[str, int, str, str], ...] = (
    ("MCQ", 1, "Real Numbers", "Euclid's division lemma"),
    ("Short", 2, "Light - Reflection and Refraction", "Mirror formula"),
    ("Long", 5, "Life Processes", "Human digestive system"),
    ("MCQ", 1, "Force and Pressure", "Units of pressure"),
    ("Short", 2, "Trigonometry", "Values of standard angles"),
    ("Long", 5, "Chemical Reactions", "Balancing equations"),
)


def _seed_question_usage(session: Session) -> None:
    if _count(session, QuestionUsageLog) >= TARGET_ROWS:
        print("[seed_sample] question-usage ledger already populated. Skipping...")
        return

    classrooms = _classrooms(session)
    subjects = list(session.exec(select(Subject)).all())
    staff = _users_with_role(session, "teacher") or list(
        session.exec(select(User)).all()
    )
    papers = list(session.exec(select(PaperDraft).order_by(PaperDraft.id)).all())  # type: ignore[arg-type])
    created = 0
    for index in range(18):
        qtype, marks, chapter, topic = USED_QUESTIONS[index % len(USED_QUESTIONS)]
        text = f"[{chapter}] {topic} - question {index + 1}."
        classroom = classrooms[index % len(classrooms)] if classrooms else None
        subject = subjects[index % len(subjects)] if subjects else None
        session.add(
            QuestionUsageLog(
                fingerprint=hashlib.sha256(text.encode("utf-8")).hexdigest(),
                text=text,
                paper_id=papers[index % len(papers)].id if papers else None,
                class_name=classroom.name if classroom else "",
                subject=subject.name if subject else "",
                chapter=chapter,
                topic=topic,
                qtype=qtype,
                marks=marks,
                created_by=staff[index % len(staff)].id if staff else None,
                used_at=datetime(2026, 3, 1, 10, 0) + timedelta(days=index),
            )
        )
        created += 1
    session.commit()
    print(f"[seed_sample] {created} question-usage row(s) created")



# ---------------------------------------------------------------------------
# 9. Fees - a head for more classes and a payment history
# ---------------------------------------------------------------------------

#: (head, class, frequency, amount, due day, status). Two stay drafts, because
#: the fee screen publishes and the "Draft" badge has to mean something.
EXTRA_FEE_HEADS: tuple[tuple[str, str, FeeFrequency, float, str, str], ...] = (
    ("Tuition Fee", "Class 11", FeeFrequency.monthly, 7400, "10th of month", "Active"),
    ("Tuition Fee", "Class 12", FeeFrequency.monthly, 7800, "10th of month", "Active"),
    ("Transport Fee", "Class 7", FeeFrequency.term, 9000, "5th of term", "Active"),
    ("Transport Fee", "Class 9", FeeFrequency.term, 9500, "5th of term", "Draft"),
    ("Library Fee", "Class 8", FeeFrequency.yearly, 1500, "1st July", "Active"),
    ("Exam Fee", "Class 10", FeeFrequency.yearly, 2200, "1st December", "Active"),
    ("Sports Fee", "Class 6", FeeFrequency.yearly, 1800, "1st July", "Active"),
    ("Hostel Fee", "Class 12", FeeFrequency.term, 42000, "5th of term", "Draft"),
)


def _seed_fee_heads(session: Session) -> None:
    by_name = {classroom.name: classroom for classroom in _classrooms(session)}
    created = 0
    for head, class_name, frequency, amount, due_day, status in EXTRA_FEE_HEADS:
        classroom = by_name.get(class_name)
        if classroom is None:
            continue
        exists = session.exec(
            select(FeeStructure).where(
                FeeStructure.name == head,
                FeeStructure.classroom_id == classroom.id,
            )
        ).first()
        if exists is not None:
            continue
        session.add(
            FeeStructure(
                name=head,
                amount=amount,
                classroom_id=classroom.id,
                frequency=frequency,
                due_day=due_day,
                status=status,
            )
        )
        created += 1
    if created:
        session.commit()
        print(f"[seed_sample] {created} fee head(s) created")


def _seed_fee_transactions(session: Session) -> None:
    if _count(session, FeeTransaction) >= 30:
        print("[seed_sample] fee payments already exist. Skipping...")
        return

    # One head per class is enough for a payment history; the first head wins so
    # the same pick is made on every run.
    by_class: dict[int, FeeStructure] = {}
    structures = session.exec(
        select(FeeStructure).order_by(FeeStructure.id)  # type: ignore[arg-type]
    ).all()
    for structure in structures:
        by_class.setdefault(structure.classroom_id, structure)

    created = 0
    serial = 2000
    for index, student in enumerate(_students(session)):
        structure = by_class.get(student.classroom_id) if student.classroom_id else None
        if structure is None:
            continue
        # Every third payment is part-paid: the collection report has to cope
        # with a student who paid less than the card says.
        part_paid = index % 3 == 0
        serial += 1
        session.add(
            FeeTransaction(
                student_id=student.id,
                fee_structure_id=structure.id,
                amount_paid=(
                    round(structure.amount / 2, 2) if part_paid else structure.amount
                ),
                date=date.today() - timedelta(days=index % 30),
                payment_mode=PAYMENT_MODES[index % len(PAYMENT_MODES)],
                receipt_number=f"RCPT-2026-{serial:05d}",
            )
        )
        created += 1
        if created >= 45:
            break
    session.commit()
    print(f"[seed_sample] {created} fee payment(s) created")



# ---------------------------------------------------------------------------
# 10. Hiring - more open posts and a fuller pipeline
# ---------------------------------------------------------------------------

EXTRA_VACANCIES: tuple[tuple[str, str, int], ...] = (
    ("Chemistry Teacher", "Science", 2),
    ("Hindi Teacher", "Languages", 1),
    ("Computer Teacher", "Computer Science", 1),
    ("Sports Coach", "Sports", 1),
    ("Librarian", "Library", 1),
    ("Counsellor", "Student Support", 1),
    ("Bus Driver", "Transport", 3),
    ("Lab Technician", "Science", 1),
    ("Mathematics Teacher", "Mathematics", 1),
    ("English Teacher", "Languages", 1),
)

#: (candidate no, name, role, department, qualification, experience, status,
#:  emp id) - one row per pipeline stage, including two who were hired.
EXTRA_CANDIDATES: tuple[tuple[str, str, str, str, str, int, str, str | None], ...] = (
    ("CAN-2026-0040", "Neha Bhatt", "Chemistry Teacher", "Science", "M.Sc. Chemistry, B.Ed.", 7, "Hired", "EMP-0040"),
    ("CAN-2026-0041", "Vikram Singh", "Computer Teacher", "Computer Science", "MCA", 5, "Hired", "EMP-0041"),
    ("CAN-2026-0042", "Asha Pillai", "Hindi Teacher", "Languages", "M.A. Hindi, B.Ed.", 9, "Interview", None),
    ("CAN-2026-0043", "Rahul Bose", "Sports Coach", "Sports", "B.P.Ed.", 3, "Shortlisted", None),
    ("CAN-2026-0044", "Meenal Joshi", "Librarian", "Library", "M.Lib.Sc.", 6, "Shortlisted", None),
    ("CAN-2026-0045", "Firoz Khan", "Lab Technician", "Science", "B.Sc. Chemistry", 2, "Resume", None),
    ("CAN-2026-0046", "Kavya Reddy", "Counsellor", "Student Support", "M.A. Psychology", 4, "Interview", None),
    ("CAN-2026-0047", "Suresh Yadav", "Bus Driver", "Transport", "HMV Licence", 12, "Rejected", None),
)


def _seed_hiring(session: Session) -> None:
    created = 0
    for role, department, openings in EXTRA_VACANCIES:
        exists = session.exec(
            select(StaffVacancy).where(
                StaffVacancy.role == role, StaffVacancy.department == department
            )
        ).first()
        if exists is not None:
            continue
        session.add(
            StaffVacancy(
                role=role,
                department=department,
                openings=openings,
                # One closed post stays on the register, like a real HR sheet.
                status="Closed" if created in (2, 5) else "Open",
            )
        )
        created += 1
    if created:
        session.commit()
        print(f"[seed_sample] {created} staff vacancy(ies) created")

    created = 0
    for (
        candidate_no,
        name,
        role,
        department,
        qualification,
        experience,
        status,
        emp_id,
    ) in EXTRA_CANDIDATES:
        if session.exec(
            select(HiringCandidate).where(
                HiringCandidate.candidate_no == candidate_no
            )
        ).first():
            continue
        session.add(
            HiringCandidate(
                candidate_no=candidate_no,
                candidate_name=name,
                role=role,
                department=department,
                qualification=qualification,
                experience=experience,
                applied_on=date(2026, 3, 2) + timedelta(days=created),
                interview_on=(
                    date(2026, 3, 20) + timedelta(days=created)
                    if status in {"Interview", "Hired", "Rejected"}
                    else None
                ),
                emp_id=emp_id,
                status=status,
            )
        )
        created += 1
    if created:
        session.commit()
        print(f"[seed_sample] {created} hiring candidate(s) created")



# ---------------------------------------------------------------------------
# 11. Admissions - more applications, including the awkward ones
# ---------------------------------------------------------------------------

#: A draft that is barely started, a registered child, and one who left again -
#: the three states the Admission screen has to render.
EXTRA_APPLICATIONS: tuple[dict, ...] = (
    {
        "status": STATUS_REGISTERED,
        "created_on": date(2026, 3, 4),
        "student_first_name": "Ishaan",
        "student_last_name": "Rao",
        "date_of_birth": date(2019, 7, 18),
        "gender": "Male",
        "blood_group": "O+",
        "category": "General",
        "nationality": "Indian",
        "father_name": "Vijay Rao",
        "father_occupation": "Business",
        "father_phone": "+91 98200 33445",
        "mother_name": "Neha Rao",
        "mother_phone": "+91 98200 33446",
        "applied_for_class_level": "Class 1",
        "applied_section_preference": "A",
        "needs_transport": "Yes",
        "transport_route": "Route 4 - Kothrud",
    },
    {
        "status": STATUS_REGISTERED,
        "created_on": date(2026, 3, 5),
        "student_first_name": "Diya",
        "student_last_name": "Kulkarni",
        "date_of_birth": date(2015, 2, 9),
        "gender": "Female",
        "blood_group": "A+",
        "category": "OBC",
        "nationality": "Indian",
        "father_name": "Manoj Kulkarni",
        "father_phone": "+91 98200 33447",
        "mother_name": "Shalini Kulkarni",
        "applied_for_class_level": "Class 5",
        "needs_hostel": "No",
    },
    {
        "status": STATUS_REGISTERED,
        "created_on": date(2026, 3, 6),
        "student_first_name": "Kabir",
        "student_last_name": "Sheikh",
        "date_of_birth": date(2010, 11, 30),
        "gender": "Male",
        "category": "General",
        "nationality": "Indian",
        "previous_school_name": "City Public School",
        "previous_class_passed": "Class 9",
        "previous_board": "CBSE",
        "transfer_certificate_no": "TC-2026-8891",
        "father_name": "Ashok Sheikh",
        "mother_name": "Kiran Sheikh",
        "applied_for_class_level": "Class 10",
        "applied_section_preference": "B",
    },
    {
        "status": STATUS_DRAFT,
        "created_on": date(2026, 3, 7),
        "student_first_name": "Tara",
        "student_last_name": "Menon",
        "gender": "Female",
        "applied_for_class_level": "Nursery",
        "notes": "Form started at the front desk; parents will return with papers.",
    },
    {
        "status": STATUS_DRAFT,
        "created_on": date(2026, 3, 8),
        "student_first_name": "Om",
        "student_last_name": "Patil",
    },
    {
        "status": STATUS_REGISTERED,
        "created_on": date(2026, 3, 9),
        "student_first_name": "Riya",
        "student_last_name": "Das",
        "date_of_birth": date(2013, 5, 21),
        "gender": "Female",
        "category": "General",
        "nationality": "Indian",
        "father_name": "Deepak Das",
        "mother_name": "Anita Das",
        "applied_for_class_level": "Class 7",
        "separation_dropped_class": "Class 7",
        "separation_reason": "Family relocated to another city.",
        "separation_session": "2026-27",
        "separation_date": date(2026, 3, 9),
    },
    {
        "status": STATUS_REGISTERED,
        "created_on": date(2026, 3, 10),
        "student_first_name": "Neel",
        "student_last_name": "Verma",
        "date_of_birth": date(2018, 1, 14),
        "gender": "Male",
        "blood_group": "B+",
        "category": "SC",
        "nationality": "Indian",
        "guardian_name": "Ravi Verma",
        "guardian_relation": "Uncle",
        "guardian_phone": "+91 98200 33448",
        "applied_for_class_level": "UKG",
        "needs_transport": "Yes",
        "transport_route": "Route 2 - Baner",
    },
)


def _seed_admissions(session: Session) -> None:
    if _count(session, AdmissionApplication) >= 12:
        print("[seed_sample] admission applications already exist. Skipping...")
        return

    created = 0
    for index, row in enumerate(EXTRA_APPLICATIONS):
        application_no = f"ADM-{date.today().year}-{1600 + index:04d}"
        if session.exec(
            select(AdmissionApplication).where(
                AdmissionApplication.application_no == application_no
            )
        ).first():
            continue
        session.add(AdmissionApplication(application_no=application_no, **row))
        created += 1
    session.commit()
    print(f"[seed_sample] {created} admission application(s) created")



# ---------------------------------------------------------------------------
# 12. Paper generation jobs - one of each lifecycle state
# ---------------------------------------------------------------------------

#: (status, note, error). The jobs screen polls `status`, so all four states
#: have to exist or the timeline, retry and error paths never render.
GENERATION_JOBS: tuple[tuple[GenerationJobStatus, str, str | None], ...] = (
    (GenerationJobStatus.done, "Completed in 41s; 24 questions in Part A.", None),
    (GenerationJobStatus.running, "Sources retrieved; writing questions.", None),
    (GenerationJobStatus.queued, "Waiting for a free worker.", None),
    (GenerationJobStatus.failed, "Generation stopped.", "LLM timeout: no response in 180s."),
)


def _seed_generation_jobs(session: Session) -> None:
    if _count(session, GenerationJob) >= 12:
        print("[seed_sample] generation jobs already exist. Skipping...")
        return

    papers = list(session.exec(select(PaperDraft).order_by(PaperDraft.id)).all())  # type: ignore[arg-type]
    created = 0
    for index, (status, note, error) in enumerate(GENERATION_JOBS):
        paper = papers[index % len(papers)] if papers else None
        session.add(
            GenerationJob(
                paper_id=paper.id if paper else None,
                status=status,
                stages={
                    "retrieve": "done" if status is not GenerationJobStatus.queued else "pending",
                    "write": "running" if status is GenerationJobStatus.running else "pending",
                    "judge": "done" if status is GenerationJobStatus.done else "pending",
                },
                blueprint_snapshot={"total_marks": 40, "duration_minutes": 90},
                coverage_snapshot={
                    "mode": CoverageMode.marks.value,
                    "chapters": list(CHAPTERS[:2]),
                },
                config_snapshot={
                    "class_name": paper.class_name if paper else "Class 10",
                    "subject": paper.subject if paper else "Science",
                    "coverage_mode": CoverageMode.marks.value,
                    "note": note,
                },
                result_snapshot=(
                    {"questions": 24, "summary": note}
                    if status is GenerationJobStatus.done
                    else {}
                ),
                model_info={"provider": "ollama", "model": "qwen2.5:latest"},
                error=error,
                trace_id=f"job-2026-{index + 1:04d}",
                created_at=datetime(2026, 4, 3, 8, 0) + timedelta(hours=index),
                updated_at=datetime(2026, 4, 3, 8, 30) + timedelta(hours=index),
            )
        )
        created += 1
    session.commit()
    print(f"[seed_sample] {created} generation job(s) created")


# ---------------------------------------------------------------------------
# 13. Impersonation audit - a short history, one session still open
# ---------------------------------------------------------------------------

IMPERSONATION_REASONS: tuple[str, ...] = (
    "Verifying the parent view reported by the help desk.",
    "Checking why a teacher cannot see the attendance register.",
    "Reproducing the fee receipt issue on the student login.",
    "Confirming the timetable shows the new periods.",
)


def _seed_impersonation_logs(session: Session) -> None:
    if _count(session, ImpersonationLog) >= 10:
        print("[seed_sample] impersonation history already exists. Skipping...")
        return

    actors = _users_with_role(session, "system_admin")
    if not actors:
        print("[seed_sample] no super admin - impersonation history skipped")
        return
    actor = actors[0]

    logged = {
        row.target_user_id
        for row in session.exec(select(ImpersonationLog)).all()
    }
    created = 0
    for index, target in enumerate(
        session.exec(select(User).where(User.id != actor.id)).all()  # type: ignore[arg-type]
    ):
        if target.id in logged:
            continue
        started = datetime(2026, 4, 1, 10, 0) + timedelta(hours=index)
        session.add(
            ImpersonationLog(
                actor_user_id=actor.id,
                target_user_id=target.id,
                started_at=started,
                # One session is left open on purpose: "Return to my account"
                # has to work for a session that was never closed.
                ended_at=(None if index % 5 == 0 else started + timedelta(minutes=15)),
                reason=IMPERSONATION_REASONS[index % len(IMPERSONATION_REASONS)],
            )
        )
        created += 1
        if created >= 8:
            break
    session.commit()
    print(f"[seed_sample] {created} impersonation log row(s) created")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def seed_sample_data() -> None:
    """Every block checks its own table first, so this is safe to re-run."""
    with Session(engine) as session:
        _seed_subjects(session)
        _seed_parent_links(session)
        _seed_teacher_assignments(session)
        _seed_timetable(session)
        _seed_homework(session)
        _seed_diary(session)
        _seed_attendance_audit(session)
        _seed_chat(session)
        _seed_exam_sources(session)
        _seed_question_usage(session)
        _seed_fee_heads(session)
        _seed_fee_transactions(session)
        _seed_hiring(session)
        _seed_admissions(session)
        _seed_generation_jobs(session)
        _seed_impersonation_logs(session)
    print("[seed_sample] Sample data ready")


if __name__ == "__main__":
    seed_sample_data()

