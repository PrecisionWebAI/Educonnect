"""The Exams plan: a date sheet, marks entry, publication and results.

Nothing here is the AI-paper builder (`exams/service.py` and its `llm`/`rag` packages) -
that stack makes **question papers**. This package runs the **exam**: which subjects sit
on which day, out of what, who entered the marks, when families may see them, and where
each child stands.

Rules this package keeps
------------------------
* **One writer per fact.** `exam.status` moves only through this module, `marks` is
  written only by `save_marks` / `change_mark`, and a grade or a rank is **derived** on
  read (`grades.py`) - never stored, so it cannot disagree with the scores.
* **Publication is a promise.** After `publish`, a change must go through `change_mark`,
  which writes a `marks_audit` row in the same transaction: a family that has seen a
  result can always be told what moved and who moved it.
* **A teacher plans and marks their own subject.** `classes.update` is the office; a
  teacher may act only on a paper of a subject they hold in a section of that class.
* **Another school is a `404`**, never a `403` that confirms an id.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlmodel import Session, select

from app.core.tenancy import tenant_of
from app.domains.academic.classroom.academics.models import (
    Chapter,
    Classroom,
    Subject,
    SubjectTeacher,
)
from app.domains.academic.classroom.exams.models import (
    EXAM_SCOPES,
    EXAM_STATUSES,
    Exam,
    ExamPaper,
    ExamPaperChapter,
    Mark,
    MarksAudit,
)
from app.domains.academic.classroom.students.models import (
    Guardian,
    Student,
    StudentGuardianRelationship,
)
from app.domains.admin.settings import values as setting_values
from app.domains.admin.settings.academic_year_context import current_academic_year_id
from app.domains.auth.service import AuthorizationService
from app.domains.main.notifications import events
from app.domains.main.notifications.models import Notification
from app.domains.people.staff.models import Employee

from . import grades
from .schemas import (
    ExamCreateIn,
    ExamPaperRead,
    ExamRead,
    ExamUpdateIn,
    MarkChangeIn,
    MarkEntryIn,
    MarksSavedRead,
    MarksSaveIn,
    PaperMarkRowRead,
    PaperScheduleIn,
    ResultMarkRead,
    ResultPaperRead,
    ResultRowRead,
    ResultsRead,
)

logger = logging.getLogger("eduverse.exams.plan")

#: The events this package rings the bell for. Strings, because they are stored.
EVENT_EXAM_SCHEDULED = "exam.scheduled"
EVENT_EXAM_CHANGED = "exam.changed"
EVENT_EXAM_PUBLISHED = "exam.published"
EVENT_EXAM_MARK_CHANGED = "exam.mark_changed"
EVENT_EXAM_REMINDER = "exam.reminder"

#: Statuses that still accept a draft save. `published` is not one of them.
OPEN_FOR_ENTRY = ("draft", "scheduled", "done", "marks_entry")


# ---------------------------------------------------------------------------
# Guards - one place that decides "this id is mine", "this person may"
# ---------------------------------------------------------------------------


def _exam_or_404(session: Session, exam_id: UUID) -> Exam:
    """This school's exam, or a `404` - `session.get` bypasses the tenant filter."""
    exam = session.get(Exam, exam_id)
    school = tenant_of(session)
    if exam is None or (school is not None and exam.school_id != school):
        raise HTTPException(status_code=404, detail="Exam not found")
    return exam


def _paper_or_404(session: Session, paper_id: UUID) -> ExamPaper:
    paper = session.get(ExamPaper, paper_id)
    school = tenant_of(session)
    if paper is None or (school is not None and paper.school_id != school):
        raise HTTPException(status_code=404, detail="Exam paper not found")
    return paper


def _room_or_404(session: Session, classroom_id: UUID) -> Classroom:
    room = session.get(Classroom, classroom_id)
    school = tenant_of(session)
    if room is None or (school is not None and room.school_id != school):
        raise HTTPException(status_code=404, detail="Class-section not found")
    return room


def _subject_or_404(session: Session, subject_id: UUID) -> Subject:
    subject = session.get(Subject, subject_id)
    school = tenant_of(session)
    if subject is None or (school is not None and subject.school_id != school):
        raise HTTPException(status_code=404, detail="Subject not found")
    return subject


def _employee_of(session: Session, user) -> UUID | None:
    """The `employee` row behind a login, when the person is staff."""
    if user is None or getattr(user, "id", None) is None:
        return None
    employee = session.exec(select(Employee).where(Employee.user_id == user.id)).first()
    return employee.id if employee is not None else None


def _is_office(session: Session, user) -> bool:
    """The office: whoever may change classes. The permission, not a role name."""
    if user is None:
        return False
    return AuthorizationService.has_permission(user, "classes.update", session=session)


def _is_leadership(session: Session, user) -> bool:
    """The office, or a principal/vice-principal - who may plan a **school** exam.

    The role list is the same one `events.principal_user_ids` uses to address a
    school-wide alert, so "who is the head" is answered in one place.
    """
    if _is_office(session, user):
        return True
    user_id = getattr(user, "id", None)
    return user_id is not None and user_id in events.principal_user_ids(session)


def _holds_subject(
    session: Session,
    user,
    *,
    subject_id: UUID,
    class_id: UUID | None = None,
    classroom_id: UUID | None = None,
) -> bool:
    """True when this teacher **currently** holds the subject in a section of that class.

    "Currently" is `effective_to IS NULL` (Phase 5's timeline), so the teacher who left
    in September cannot enter October's marks.
    """
    employee_id = _employee_of(session, user)
    if employee_id is None:
        return False
    statement = (
        select(SubjectTeacher.id)
        .join(Classroom, Classroom.id == SubjectTeacher.classroom_id)
        .where(
            SubjectTeacher.teacher_id == employee_id,
            SubjectTeacher.subject_id == subject_id,
            SubjectTeacher.effective_to.is_(None),
        )
    )
    if classroom_id is not None:
        statement = statement.where(SubjectTeacher.classroom_id == classroom_id)
    if class_id is not None:
        statement = statement.where(Classroom.class_id == class_id)
    return session.exec(statement).first() is not None


def _may_plan_paper(session: Session, user, paper: ExamPaper) -> bool:
    """The office, or the teacher holding that paper's subject in that class."""
    return _is_office(session, user) or _holds_subject(
        session, user, subject_id=paper.subject_id, class_id=paper.class_id
    )


def _require_plan_paper(session: Session, user, paper: ExamPaper) -> None:
    if not _may_plan_paper(session, user, paper):
        raise HTTPException(
            status_code=403,
            detail="Only the subject's teacher or the office may change this paper.",
        )


# ---------------------------------------------------------------------------
# Telling people - one helper, so every exam event reads the same
# ---------------------------------------------------------------------------


def _students_of(
    session: Session, *, classroom_id: UUID | None = None, class_id: UUID | None = None
) -> list[Student]:
    """Every child in one section, or in every section of one class."""
    statement = select(Student).join(Classroom, Classroom.id == Student.classroom_id)
    if classroom_id is not None:
        statement = statement.where(Student.classroom_id == classroom_id)
    if class_id is not None:
        statement = statement.where(Classroom.class_id == class_id)
    return list(session.exec(statement).all())


def _tell_students(
    session: Session,
    students: list[Student],
    *,
    event: str,
    title: str,
    body: str,
    dedupe_key: str,
    entity_type: str,
    entity_id: UUID,
) -> int:
    """Ring the bell once per family, for a list of children.

    The recipients come from the data (`events.audience`): each child's guardians and,
    when they have one, their own login. `notify` never raises, so a date sheet that
    saved cannot fail on the bell.
    """
    recipients: list[UUID] = []
    for student in students:
        recipients.extend(
            events.audience(
                session, roles={events.GUARDIANS, events.STUDENT}, student_id=student.id
            )
        )
    return events.notify(
        session,
        event=event,
        recipients=list(dict.fromkeys(recipients)),
        title=title,
        body=body,
        entity_type=entity_type,
        entity_id=entity_id,
        dedupe_key=dedupe_key,
    )


def _notify_class_teacher(
    session: Session,
    classroom_id: UUID | None,
    *,
    event: str,
    title: str,
    body: str,
    dedupe_key: str,
    entity_type: str,
    entity_id: UUID,
) -> int:
    """Tell the section's class teacher (when the exam belongs to one section)."""
    if classroom_id is None:
        return 0
    recipients = events.audience(
        session, roles={events.CLASS_TEACHER}, classroom_id=classroom_id
    )
    return events.notify(
        session,
        event=event,
        recipients=recipients,
        title=title,
        body=body,
        entity_type=entity_type,
        entity_id=entity_id,
        dedupe_key=dedupe_key,
    )


# ---------------------------------------------------------------------------
# Reading an exam back
# ---------------------------------------------------------------------------


def _chapter_names(session: Session, paper_id: UUID) -> tuple[list[UUID], list[str]]:
    rows = session.exec(
        select(ExamPaperChapter.chapter_id, Chapter.name)
        .join(Chapter, Chapter.id == ExamPaperChapter.chapter_id)
        .where(ExamPaperChapter.exam_paper_id == paper_id)
        .order_by(Chapter.sequence)
    ).all()
    return [row[0] for row in rows], [row[1] for row in rows]


def _marks_entered(session: Session, exam_id: UUID) -> dict[UUID, int]:
    rows = session.exec(
        select(Mark.exam_paper_id, func.count())
        .where(Mark.exam_id == exam_id)
        .group_by(Mark.exam_paper_id)
    ).all()
    return {paper_id: int(count) for paper_id, count in rows if paper_id is not None}


def _paper_read(
    session: Session, paper: ExamPaper, user, entered: int = 0
) -> ExamPaperRead:
    subject = session.get(Subject, paper.subject_id)
    chapter_ids, names = _chapter_names(session, paper.id)
    return ExamPaperRead(
        id=paper.id,
        exam_id=paper.exam_id,
        subject_id=paper.subject_id,
        subject=subject.name if subject is not None else "",
        class_id=paper.class_id,
        exam_date=paper.exam_date,
        start_time=paper.start_time,
        end_time=paper.end_time,
        max_marks=paper.max_marks,
        passing_marks=paper.passing_marks,
        room=paper.room,
        note=paper.note,
        published_at=paper.published_at,
        chapter_ids=chapter_ids,
        chapters=names,
        marks_entered=entered,
        can_edit=_may_plan_paper(session, user, paper),
    )


def read_exam(session: Session, exam_id: UUID, user) -> ExamRead:
    """One exam, or a `404` when it belongs to another school."""
    return exam_read(session, _exam_or_404(session, exam_id), user)


def exam_read(session: Session, exam: Exam, user) -> ExamRead:
    """The exam with its date sheet, each paper saying whether this caller may edit it."""
    entered = _marks_entered(session, exam.id)
    papers = session.exec(
        select(ExamPaper)
        .where(ExamPaper.exam_id == exam.id)
        .order_by(ExamPaper.exam_date.nullslast(), ExamPaper.id)
    ).all()
    return ExamRead(
        id=exam.id,
        name=exam.name,
        term=exam.term,
        exam_type=exam.exam_type,
        scope=exam.scope,
        status=exam.status,
        class_id=exam.class_id,
        classroom_id=exam.classroom_id,
        academic_year_id=exam.academic_year_id,
        start_date=exam.start_date,
        end_date=exam.end_date,
        note=exam.note,
        published_at=exam.published_at,
        papers=[
            _paper_read(session, paper, user, entered.get(paper.id, 0))
            for paper in papers
        ],
    )


# ---------------------------------------------------------------------------
# Planning - POST /exams, PATCH /exams/{id}, GET /exams
# ---------------------------------------------------------------------------


def _validate_words(status: str | None, scope: str | None = None) -> None:
    if status is not None and status not in EXAM_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown exam status '{status}'. Use: {', '.join(EXAM_STATUSES)}.",
        )
    if scope is not None and scope not in EXAM_SCOPES:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown exam scope '{scope}'. Use: {', '.join(EXAM_SCOPES)}.",
        )


def _paper_from_row(
    session: Session,
    *,
    exam_id: UUID,
    default_class_id: UUID | None,
    row: PaperScheduleIn,
    existing: ExamPaper | None = None,
) -> ExamPaper:
    """Build (or update) one sitting and its chapter list, refusing what cannot be true."""
    _subject_or_404(session, row.subject_id)
    paper_class = (
        row.class_id or (existing.class_id if existing else None) or default_class_id
    )
    if paper_class is None:
        raise HTTPException(
            status_code=422, detail="A paper needs the class that sits it."
        )
    maximum = Decimal(str(row.max_marks))
    if maximum <= 0:
        raise HTTPException(
            status_code=422, detail="A paper must be out of more than 0."
        )
    if row.passing_marks is not None and Decimal(str(row.passing_marks)) > maximum:
        raise HTTPException(
            status_code=422, detail="The passing marks cannot exceed the maximum."
        )
    if row.start_time and row.end_time and row.end_time <= row.start_time:
        raise HTTPException(
            status_code=422, detail="A paper cannot end before it starts."
        )

    paper = existing or ExamPaper(
        exam_id=exam_id, class_id=paper_class, subject_id=row.subject_id
    )
    paper.exam_date = row.exam_date
    paper.start_time = row.start_time
    paper.end_time = row.end_time
    paper.max_marks = maximum
    paper.passing_marks = (
        Decimal(str(row.passing_marks)) if row.passing_marks is not None else None
    )
    paper.room = row.room
    paper.note = row.note
    if existing is None:
        session.add(paper)
        session.flush()

    # The syllabus is the set of chapters sent: replaced as a set, so unticking a
    # chapter really removes it.
    for link in session.exec(
        select(ExamPaperChapter).where(ExamPaperChapter.exam_paper_id == paper.id)
    ).all():
        session.delete(link)
    session.flush()
    seen: set[UUID] = set()
    for chapter_id in row.chapter_ids:
        if chapter_id in seen:
            continue
        seen.add(chapter_id)
        chapter = session.get(Chapter, chapter_id)
        school = tenant_of(session)
        if chapter is None or (school is not None and chapter.school_id != school):
            raise HTTPException(status_code=404, detail="Chapter not found")
        if chapter.subject_id != paper.subject_id or chapter.class_id != paper.class_id:
            raise HTTPException(
                status_code=422,
                detail="That chapter belongs to another class or subject.",
            )
        session.add(ExamPaperChapter(exam_paper_id=paper.id, chapter_id=chapter_id))
    session.flush()
    return paper


def _revision(session: Session, event: str, exam_id: UUID) -> int:
    """How many messages of this kind this exam has already sent.

    It is the dedupe key's tail: the first "date sheet changed" tells each family once,
    and a *second* move tells them again - without the first one double-ringing.
    """
    return int(
        session.exec(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.event_type == event,
                Notification.entity_id == exam_id,
            )
        ).one()
    )


def _announce(session: Session, exam: Exam, *, event: str, changed: bool) -> int:
    """Tell the families (and the class teacher) that the date sheet exists or moved."""
    students = _students_of(
        session, classroom_id=exam.classroom_id, class_id=exam.class_id
    )
    title = f"{exam.name} {'changed' if changed else 'is scheduled'}"
    body = (
        f"The date sheet for {exam.name} has changed. Open Exams to see the new dates."
        if changed
        else f"{exam.name} is scheduled. Open Exams to see the date sheet."
    )
    # "Scheduled" is one event per exam, however often it is announced. A **move** is a
    # new event each time, so its key carries how many moves this exam has already sent -
    # otherwise the second move would be swallowed by the first one's dedupe key.
    tail = (
        f"{event}:{exam.id}:{_revision(session, event, exam.id)}"
        if changed
        else f"{event}:{exam.id}"
    )
    told = _tell_students(
        session,
        students,
        event=event,
        title=title,
        body=body,
        dedupe_key=tail,
        entity_type="exam",
        entity_id=exam.id,
    )
    _notify_class_teacher(
        session,
        exam.classroom_id,
        event=event,
        title=title,
        body=body,
        dedupe_key=f"{tail}:teacher",
        entity_type="exam",
        entity_id=exam.id,
    )
    return told


def create_exam(session: Session, payload: ExamCreateIn, user) -> ExamRead:
    """Plan an exam and its date sheet.

    * a **class** exam is the office's, or the subject teacher's (they must hold the
      subject in a section of that class);
    * a **school** exam is the office's only - it writes a paper per class.
    """
    _validate_words(payload.status, payload.scope)
    if payload.status in ("published", "marks_entry"):
        raise HTTPException(
            status_code=422,
            detail="An exam starts as a draft or scheduled; marks are published later.",
        )
    if not payload.papers:
        raise HTTPException(status_code=422, detail="An exam needs at least one paper.")

    room: Classroom | None = None
    class_id = payload.class_id
    if payload.classroom_id is not None:
        room = _room_or_404(session, payload.classroom_id)
        if class_id is not None and class_id != room.class_id:
            raise HTTPException(
                status_code=422,
                detail="That class-section belongs to a different class.",
            )
        class_id = room.class_id

    office = _is_office(session, user)
    if payload.scope == "school":
        if not _is_leadership(session, user):
            raise HTTPException(
                status_code=403, detail="Only the office may plan a school-wide exam."
            )
    else:
        if class_id is None:
            raise HTTPException(
                status_code=422, detail="A class exam needs a class or a class-section."
            )
        if not office:
            for row in payload.papers:
                if not _holds_subject(
                    session,
                    user,
                    subject_id=row.subject_id,
                    class_id=class_id,
                    classroom_id=room.id if room is not None else None,
                ):
                    raise HTTPException(
                        status_code=403,
                        detail="A teacher may plan only the subjects they teach.",
                    )

    exam = Exam(
        name=payload.name,
        term=payload.term,
        exam_type=payload.exam_type,
        scope=payload.scope,
        class_id=class_id,
        classroom_id=room.id if room is not None else payload.classroom_id,
        academic_year_id=payload.academic_year_id
        or current_academic_year_id(session),
        start_date=payload.start_date,
        end_date=payload.end_date,
        status=payload.status,
        note=payload.note,
        created_by_user_id=getattr(user, "id", None),
    )
    session.add(exam)
    session.flush()

    seen: set[tuple[UUID, UUID]] = set()
    for row in payload.papers:
        paper_class = row.class_id or class_id
        if paper_class is None:
            raise HTTPException(status_code=422, detail="A paper needs a class.")
        key = (paper_class, row.subject_id)
        if key in seen:
            raise HTTPException(
                status_code=409, detail="That subject already has a paper in this exam."
            )
        seen.add(key)
        _paper_from_row(session, exam_id=exam.id, default_class_id=class_id, row=row)

    session.commit()
    session.refresh(exam)

    if payload.status == "scheduled":
        _announce(session, exam, event=EVENT_EXAM_SCHEDULED, changed=False)
    return exam_read(session, exam, user)


def update_exam(
    session: Session, exam_id: UUID, payload: ExamUpdateIn, user
) -> ExamRead:
    """Change the dates, the syllabus or the note - and tell the families when it moved.

    The date sheet, when sent, is **replaced**: a paper missing from the payload is
    deleted, so an unticked subject really disappears. A paper whose marks are already
    published is refused with a `409` rather than silently re-cut.
    """
    exam = _exam_or_404(session, exam_id)
    _validate_words(payload.status)
    office = _is_office(session, user)
    if exam.scope == "school" and not _is_leadership(session, user):
        raise HTTPException(
            status_code=403, detail="Only the office may change a school-wide exam."
        )
    if not office:
        papers = session.exec(
            select(ExamPaper).where(ExamPaper.exam_id == exam.id)
        ).all()
        if not papers or not all(
            _may_plan_paper(session, user, paper) for paper in papers
        ):
            raise HTTPException(
                status_code=403, detail="Only the office may change this exam."
            )

    moved = False
    for field in ("name", "term", "exam_type", "start_date", "end_date", "note"):
        value = getattr(payload, field)
        if value is not None and getattr(exam, field) != value:
            setattr(exam, field, value)
            moved = moved or field in ("start_date", "end_date")
    if payload.status is not None and payload.status != exam.status:
        if payload.status == "published":
            raise HTTPException(
                status_code=422, detail="Marks are published from the paper, not here."
            )
        exam.status = payload.status
        moved = True

    if payload.papers is not None:
        if not payload.papers:
            raise HTTPException(
                status_code=422, detail="An exam needs at least one paper."
            )
        existing = {
            (paper.class_id, paper.subject_id): paper
            for paper in session.exec(
                select(ExamPaper).where(ExamPaper.exam_id == exam.id)
            ).all()
        }
        kept: set[tuple[UUID, UUID]] = set()
        for row in payload.papers:
            paper_class = row.class_id or exam.class_id
            key = (paper_class, row.subject_id)
            if key in existing:
                if existing[key].published_at is not None:
                    raise HTTPException(
                        status_code=409,
                        detail="That paper's marks are published; they cannot be re-cut.",
                    )
                if existing[key].exam_date != row.exam_date:
                    moved = True
                _paper_from_row(
                    session,
                    exam_id=exam.id,
                    default_class_id=exam.class_id,
                    row=row,
                    existing=existing[key],
                )
                kept.add(key)
            else:
                if paper_class is None:
                    raise HTTPException(
                        status_code=422, detail="A paper needs the class that sits it."
                    )
                _paper_from_row(
                    session, exam_id=exam.id, default_class_id=exam.class_id, row=row
                )
                moved = True
        for key, paper in existing.items():
            if key in kept:
                continue
            if paper.published_at is not None:
                raise HTTPException(
                    status_code=409,
                    detail="A published paper cannot be removed from the date sheet.",
                )
            for link in session.exec(
                select(ExamPaperChapter).where(
                    ExamPaperChapter.exam_paper_id == paper.id
                )
            ).all():
                session.delete(link)
            session.delete(paper)
            moved = True

    session.commit()
    session.refresh(exam)
    if moved and exam.status == "scheduled":
        _announce(session, exam, event=EVENT_EXAM_CHANGED, changed=True)
    return exam_read(session, exam, user)


def _teaches_exam(
    session: Session, employee_id: UUID, exam: Exam, paper_subjects: set[UUID]
) -> bool:
    """True when this teacher holds one of the exam's subjects in a section that sits it."""
    held = session.exec(
        select(SubjectTeacher.classroom_id, SubjectTeacher.subject_id).where(
            SubjectTeacher.teacher_id == employee_id,
            SubjectTeacher.effective_to.is_(None),
        )
    ).all()
    if exam.classroom_id is not None:
        return any(
            room == exam.classroom_id and subject in paper_subjects
            for room, subject in held
        )
    rooms_of_class = set(
        session.exec(
            select(Classroom.id).where(Classroom.class_id == exam.class_id)
        ).all()
    )
    return any(
        room in rooms_of_class and subject in paper_subjects for room, subject in held
    )


def list_exams(
    session: Session,
    user,
    *,
    classroom_id: UUID | None = None,
    class_id: UUID | None = None,
    status: str | None = None,
    academic_year_id: UUID | None = None,
) -> list[ExamRead]:
    """The exams this caller may see, newest first.

    A teacher sees the exams they take a subject in; the office sees every exam of the
    school. The filter is read from the **assignments**, not from a client's list of ids.
    """
    _validate_words(status)
    statement = select(Exam)
    year_id = academic_year_id or current_academic_year_id(session)
    if year_id is not None:
        statement = statement.where(
            or_(
                Exam.academic_year_id == year_id,
                Exam.academic_year_id.is_(None),
            )
        )
    if classroom_id is not None:
        room = _room_or_404(session, classroom_id)
        statement = statement.where(
            (Exam.classroom_id == room.id)
            | ((Exam.classroom_id.is_(None)) & (Exam.class_id == room.class_id))
        )
    if class_id is not None:
        statement = statement.where(Exam.class_id == class_id)
    if status is not None:
        statement = statement.where(Exam.status == status)
    exams = list(
        session.exec(statement.order_by(Exam.start_date.desc().nullslast())).all()
    )

    if not _is_leadership(session, user):
        employee_id = _employee_of(session, user)
        if employee_id is None:
            return []
        visible: list[Exam] = []
        for exam in exams:
            subjects = {
                paper.subject_id
                for paper in session.exec(
                    select(ExamPaper).where(ExamPaper.exam_id == exam.id)
                ).all()
            }
            if _teaches_exam(session, employee_id, exam, subjects):
                visible.append(exam)
        exams = visible
    return [exam_read(session, exam, user) for exam in exams]


# ---------------------------------------------------------------------------
# Marks - one writer, a draft, a publication, and an audited correction
# ---------------------------------------------------------------------------


def _class_students(session: Session, class_id: UUID) -> dict[UUID, Student]:
    """Every child in every section of one class - who may be marked on a paper."""
    return {student.id: student for student in _students_of(session, class_id=class_id)}


def _mark_of(session: Session, paper: ExamPaper, student_id: UUID) -> Mark | None:
    return session.exec(
        select(Mark).where(
            Mark.exam_paper_id == paper.id, Mark.student_id == student_id
        )
    ).first()


def _audit_count(session: Session, marks_id: UUID) -> int:
    return int(
        session.exec(
            select(func.count())
            .select_from(MarksAudit)
            .where(MarksAudit.marks_id == marks_id)
        ).one()
    )


def _name_of(student: Student) -> str:
    return student.full_name or student.student_first_name or ""


def _row_read(
    session: Session, paper: ExamPaper, mark: Mark, student: Student
) -> PaperMarkRowRead:
    obtained = mark.marks_obtained
    percent = (
        Decimal(str(obtained)) * 100 / Decimal(str(paper.max_marks))
        if obtained is not None and paper.max_marks
        else None
    )
    return PaperMarkRowRead(
        student_id=student.id,
        name=_name_of(student),
        admission_number=student.admission_number,
        marks_obtained=obtained,
        absent=mark.is_absent,
        grade=None if mark.is_absent else grades.grade_for(session, percent),
        changed_after_publish=_audit_count(session, mark.id) > 0,
    )


def paper_marks(session: Session, paper_id: UUID, user) -> list[PaperMarkRowRead]:
    """The sheet for one paper: every child in its class, marked or not."""
    paper = _paper_or_404(session, paper_id)
    _require_plan_paper(session, user, paper)
    students = _class_students(session, paper.class_id)
    marks = {
        mark.student_id: mark
        for mark in session.exec(
            select(Mark).where(Mark.exam_paper_id == paper.id)
        ).all()
    }
    rows: list[PaperMarkRowRead] = []
    for student in sorted(
        students.values(), key=lambda row: row.admission_number or ""
    ):
        mark = marks.get(student.id)
        if mark is None:
            rows.append(
                PaperMarkRowRead(
                    student_id=student.id,
                    name=_name_of(student),
                    admission_number=student.admission_number,
                )
            )
        else:
            rows.append(_row_read(session, paper, mark, student))
    return rows


def _checked_score(paper: ExamPaper, entry: MarkEntryIn) -> tuple[Decimal | None, bool]:
    """The value to store, or a `422` when it cannot be true on this paper."""
    if entry.absent:
        return None, True
    if entry.marks_obtained is None:
        return None, False
    value = Decimal(str(entry.marks_obtained))
    if value < 0:
        raise HTTPException(status_code=422, detail="A mark cannot be below zero.")
    if value > Decimal(str(paper.max_marks)):
        raise HTTPException(
            status_code=422,
            detail=f"That paper is out of {paper.max_marks}; {value} is too many marks.",
        )
    return value, False


def save_marks(
    session: Session, paper_id: UUID, payload: MarksSaveIn, user
) -> MarksSavedRead:
    """Save a draft of one paper's scores.

    * only the paper's subject teacher or the office may write it;
    * every student must sit in the paper's class - a mark filed for somebody else's
      class would put them in two places at once;
    * once the paper is published this refuses (`409`) and points at `change_mark`,
      which audits.
    """
    paper = _paper_or_404(session, paper_id)
    _require_plan_paper(session, user, paper)
    if not payload.entries:
        raise HTTPException(status_code=422, detail="Send at least one entry.")
    exam = _exam_or_404(session, paper.exam_id)
    if paper.published_at is not None:
        raise HTTPException(
            status_code=409,
            detail="These marks are published; change one through its own endpoint so "
            "the change is audited.",
        )
    if exam.status not in OPEN_FOR_ENTRY:
        raise HTTPException(
            status_code=409,
            detail=f"This exam is '{exam.status}' and no longer takes marks.",
        )

    allowed = _class_students(session, paper.class_id)
    written = 0
    absent = 0
    for entry in payload.entries:
        student = allowed.get(entry.student_id)
        if student is None:
            raise HTTPException(
                status_code=422, detail="That student is not in this paper's class."
            )
        value, is_absent = _checked_score(paper, entry)
        mark = _mark_of(session, paper, entry.student_id)
        if mark is None:
            mark = Mark(
                exam_id=paper.exam_id,
                student_id=student.id,
                subject_id=paper.subject_id,
                exam_paper_id=paper.id,
            )
        mark.marks_obtained = value
        mark.is_absent = is_absent
        mark.entered_by = getattr(user, "id", None)
        session.add(mark)
        written += 1
        absent += 1 if is_absent else 0

    if exam.status in ("draft", "scheduled", "done"):
        exam.status = "marks_entry"
    session.commit()
    session.refresh(exam)
    return MarksSavedRead(
        paper_id=paper.id,
        exam_id=exam.id,
        exam_status=exam.status,
        written=written,
        absent=absent,
        rows=paper_marks(session, paper.id, user),
    )


def publish_paper(session: Session, paper_id: UUID, user) -> ExamPaperRead:
    """Publish one sitting's marks: families can see them from now on.

    Publishing twice is a `409` (nothing to do, and a second bell would be noise).
    `exam.published_at` is set the first time **any** of its papers is published, so the
    exam list can say "published" without walking every paper.
    """
    paper = _paper_or_404(session, paper_id)
    _require_plan_paper(session, user, paper)
    if paper.published_at is not None:
        raise HTTPException(
            status_code=409, detail="These marks are already published."
        )
    marks = session.exec(select(Mark).where(Mark.exam_paper_id == paper.id)).all()
    if not marks:
        raise HTTPException(
            status_code=422, detail="There are no marks to publish on this paper."
        )

    exam = _exam_or_404(session, paper.exam_id)
    now = datetime.utcnow()
    paper.published_at = now
    if exam.published_at is None:
        exam.published_at = now
    exam.status = "published"
    session.add(paper)
    session.add(exam)
    session.commit()
    session.refresh(paper)

    subject = session.get(Subject, paper.subject_id)
    students = [
        student
        for student_id in {mark.student_id for mark in marks}
        if (student := session.get(Student, student_id)) is not None
    ]
    _tell_students(
        session,
        students,
        event=EVENT_EXAM_PUBLISHED,
        title=f"{exam.name}: {subject.name if subject else 'marks'} published",
        body=(
            f"The {subject.name if subject else 'marks'} result for {exam.name} is out. "
            "Open Exams to see the marks and the grade."
        ),
        dedupe_key=f"{EVENT_EXAM_PUBLISHED}:{paper.id}",
        entity_type="exam_paper",
        entity_id=paper.id,
    )
    return _paper_read(session, paper, user, len(marks))


def change_mark(
    session: Session, paper_id: UUID, student_id: UUID, payload: MarkChangeIn, user
) -> PaperMarkRowRead:
    """Correct one published mark - and leave a trail.

    Before publication, use `save_marks`: there is nobody to tell yet. After it, the
    change is written to `marks_audit` **in the same transaction** as the new value, so
    a family that has already seen a result can be told what moved.
    """
    paper = _paper_or_404(session, paper_id)
    _require_plan_paper(session, user, paper)
    if paper.published_at is None:
        raise HTTPException(
            status_code=409,
            detail="These marks are not published yet; save them as a draft instead.",
        )
    mark = _mark_of(session, paper, student_id)
    if mark is None:
        raise HTTPException(status_code=404, detail="That student has no mark here.")
    student = session.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")

    entry = MarkEntryIn(
        student_id=student_id,
        marks_obtained=payload.marks_obtained,
        absent=bool(payload.absent) if payload.absent is not None else mark.is_absent,
    )
    value, is_absent = _checked_score(paper, entry)
    if value == mark.marks_obtained and is_absent == mark.is_absent:
        raise HTTPException(status_code=409, detail="That is the mark already on file.")

    session.add(
        MarksAudit(
            marks_id=mark.id,
            old_value=mark.marks_obtained,
            new_value=value,
            old_absent=mark.is_absent,
            new_absent=is_absent,
            changed_by_user_id=getattr(user, "id", None),
            reason=payload.reason,
        )
    )
    mark.marks_obtained = value
    mark.is_absent = is_absent
    mark.entered_by = getattr(user, "id", None)
    session.add(mark)
    session.commit()
    session.refresh(mark)

    exam = _exam_or_404(session, paper.exam_id)
    subject = session.get(Subject, paper.subject_id)
    revision = _audit_count(session, mark.id)
    _tell_students(
        session,
        [student],
        event=EVENT_EXAM_MARK_CHANGED,
        title=f"{exam.name}: a mark was corrected",
        body=(
            f"The {subject.name if subject else 'subject'} mark for {exam.name} was "
            "corrected. Open Exams to see the updated result."
        ),
        dedupe_key=f"{EVENT_EXAM_MARK_CHANGED}:{mark.id}:{revision}",
        entity_type="marks",
        entity_id=mark.id,
    )
    return _row_read(session, paper, mark, student)


# ---------------------------------------------------------------------------
# Results - marks, grades and ranks, narrowed to what the caller may see
# ---------------------------------------------------------------------------


def _own_student_ids(session: Session, user, cohort: set[UUID]) -> set[UUID]:
    """The children this login is a student or a guardian of, within this exam."""
    if user is None or getattr(user, "id", None) is None:
        return set()
    own = {
        student_id
        for student_id in session.exec(
            select(Student.id).where(Student.user_id == user.id)
        ).all()
        if student_id in cohort
    }
    guardian_children = session.exec(
        select(StudentGuardianRelationship.student_id)
        .join(Guardian, Guardian.id == StudentGuardianRelationship.guardian_id)
        .where(Guardian.user_id == user.id)
    ).all()
    own.update(child for child in guardian_children if child in cohort)
    return own


def results(session: Session, exam_id: UUID, user) -> ResultsRead:
    """The result sheet for one exam, narrowed by who is asking.

    * **office / principal**: every child, every paper, the averages and the papers still
      unpublished;
    * **teacher**: the same, for the classes they teach (they are the ones entering marks);
    * **student / parent**: their own line only, and **only published papers**.

    Ranks are competition ranks (`1, 2, 2, 4`) over the cohort the `exam.rank_display`
    setting names; an absent child is not ranked, because an absence is not a zero.
    """
    exam = _exam_or_404(session, exam_id)
    rank_display = (
        setting_values.get_value(session, "exam.rank_display") or "section"
    ).strip()
    grade_scale = (
        setting_values.get_value(session, "exam.grade_scale") or "percentage"
    ).strip()

    papers = list(
        session.exec(
            select(ExamPaper)
            .where(ExamPaper.exam_id == exam.id)
            .order_by(ExamPaper.exam_date.nullslast(), ExamPaper.id)
        ).all()
    )
    subject_names = dict(
        session.exec(
            select(Subject.id, Subject.name).where(
                Subject.id.in_({paper.subject_id for paper in papers} or {None})
            )
        ).all()
    )
    students = {
        student.id: student
        for student in _students_of(
            session, classroom_id=exam.classroom_id, class_id=exam.class_id
        )
    }
    marks_by_student: dict[UUID, dict[UUID, Mark]] = {}
    for mark in session.exec(select(Mark).where(Mark.exam_id == exam.id)).all():
        if mark.exam_paper_id is None:
            continue
        marks_by_student.setdefault(mark.student_id, {})[mark.exam_paper_id] = mark

    cohort = set(students) | set(marks_by_student)
    employee_id = _employee_of(session, user)
    staff = _is_leadership(session, user) or (
        employee_id is not None
        and _teaches_exam(
            session, employee_id, exam, {paper.subject_id for paper in papers}
        )
    )
    own = set() if staff else _own_student_ids(session, user, cohort)
    if not staff and not own:
        raise HTTPException(
            status_code=403, detail="You cannot see this exam's results."
        )
    if not staff:
        # A family sees what was published, and nothing else.
        papers = [paper for paper in papers if paper.published_at is not None]
        if not papers:
            raise HTTPException(
                status_code=404, detail="These results are not published yet."
            )

    rows: list[ResultRowRead] = []
    scored: dict[UUID, Decimal] = {}
    for student_id in sorted(
        (own or cohort),
        key=lambda key: (
            (students[key].admission_number or "") if key in students else ""
        ),
    ):
        student = students.get(student_id)
        if student is None:
            continue
        own_marks = marks_by_student.get(student_id, {})
        subject_marks: list[ResultMarkRead] = []
        total = Decimal("0")
        out_of = Decimal("0")
        absent_count = 0
        passed_all = True
        for paper in papers:
            mark = own_marks.get(paper.id)
            if mark is None:
                continue
            maximum = Decimal(str(paper.max_marks))
            obtained = mark.marks_obtained
            absent_count += 1 if mark.is_absent else 0
            passed: bool | None = None
            if obtained is not None:
                total += Decimal(str(obtained))
                out_of += maximum
                if paper.passing_marks is not None:
                    passed = Decimal(str(obtained)) >= Decimal(str(paper.passing_marks))
                    passed_all = passed_all and passed
            percent = (
                Decimal(str(obtained)) * 100 / maximum
                if obtained is not None and maximum
                else None
            )
            subject_marks.append(
                ResultMarkRead(
                    paper_id=paper.id,
                    subject_id=paper.subject_id,
                    subject=subject_names.get(paper.subject_id, ""),
                    max_marks=maximum,
                    obtained=Decimal(str(obtained)) if obtained is not None else None,
                    absent=mark.is_absent,
                    grade=None
                    if mark.is_absent
                    else grades.grade_for(session, percent),
                    passed=None if mark.is_absent else passed,
                )
            )
        percent = (total * 100 / out_of) if out_of else None
        if percent is not None:
            scored[student_id] = percent.quantize(Decimal("0.01"))
        rows.append(
            ResultRowRead(
                student_id=student_id,
                name=_name_of(student),
                admission_number=student.admission_number,
                marks=subject_marks,
                total=total,
                out_of=out_of,
                percent=percent.quantize(Decimal("0.01"))
                if percent is not None
                else None,
                grade=grades.grade_for(session, percent),
                absent_count=absent_count,
                passed_all=passed_all if subject_marks else None,
            )
        )

    # Ranks: competition ranks within the cohort the setting names. A student with no
    # scored paper is not in `scored`, so an all-absent child gets no rank at all.
    if rank_display == "section":
        groups: dict[UUID | None, dict[UUID, Decimal]] = {}
        for student_id, percent in scored.items():
            room = students[student_id].classroom_id if student_id in students else None
            groups.setdefault(room, {})[student_id] = percent
        ranks: dict[UUID, int] = {}
        for group in groups.values():
            ranks.update(grades.competition_ranks(group))
    elif rank_display in ("class", "school"):
        ranks = grades.competition_ranks(scored)
    else:
        ranks = {}
    for row in rows:
        row.rank = ranks.get(row.student_id)

    paper_rows: list[ResultPaperRead] = []
    for paper in papers:
        numbers: list[Decimal] = []
        absent = 0
        for marks in marks_by_student.values():
            mark = marks.get(paper.id)
            if mark is None:
                continue
            if mark.is_absent:
                absent += 1
            elif mark.marks_obtained is not None:
                numbers.append(Decimal(str(mark.marks_obtained)))
        paper_rows.append(
            ResultPaperRead(
                paper_id=paper.id,
                subject_id=paper.subject_id,
                subject=subject_names.get(paper.subject_id, ""),
                exam_date=paper.exam_date,
                max_marks=Decimal(str(paper.max_marks)),
                passing_marks=(
                    Decimal(str(paper.passing_marks))
                    if paper.passing_marks is not None
                    else None
                ),
                published=paper.published_at is not None,
                average=(
                    (sum(numbers) / len(numbers)).quantize(Decimal("0.01"))
                    if numbers
                    else None
                ),
                highest=max(numbers) if numbers else None,
                lowest=min(numbers) if numbers else None,
                entered=len(numbers) + absent,
                absent=absent,
            )
        )

    unpublished = (
        [paper.id for paper in papers if paper.published_at is None] if staff else []
    )
    return ResultsRead(
        exam_id=exam.id,
        name=exam.name,
        status=exam.status,
        rank_display=rank_display,
        grade_scale=grade_scale,
        papers=paper_rows,
        rows=rows,
        unpublished=unpublished,
        own_only=not staff,
    )


# ---------------------------------------------------------------------------
# The reminder - the one job the scheduler runs for exams
# ---------------------------------------------------------------------------


def _reminder_hour(session: Session) -> int:
    """The hour the school wants its exam reminder (`exam.reminder_time`, "18:00")."""
    raw = setting_values.get_value(session, "exam.reminder_time") or "18:00"
    try:
        return int(str(raw).split(":")[0])
    except TypeError, ValueError:
        return 18


def reminder_job(session: Session) -> int:
    """Tell each family the day before a scheduled paper. Returns how many were told.

    Registered on the Phase 3 scheduler, so it runs every tick; the dedupe key
    (`exam.reminder:<paper>`) is what makes "once per paper" true however often it runs.
    Only `status = scheduled` papers are reminded - a draft is nobody's business yet, and
    a published one is history.
    """
    now = datetime.utcnow()
    if now.hour < _reminder_hour(session):
        return 0
    tomorrow = (now + timedelta(days=1)).date()
    papers = session.exec(
        select(ExamPaper).where(
            ExamPaper.exam_date == tomorrow, ExamPaper.published_at.is_(None)
        )
    ).all()
    told = 0
    for paper in papers:
        exam = session.get(Exam, paper.exam_id)
        if exam is None or exam.status != "scheduled":
            continue
        subject = session.get(Subject, paper.subject_id)
        students = _students_of(session, class_id=paper.class_id)
        told += _tell_students(
            session,
            students,
            event=EVENT_EXAM_REMINDER,
            title=f"{exam.name}: {subject.name if subject else 'paper'} is tomorrow",
            body=(
                f"{subject.name if subject else 'The paper'} is scheduled for tomorrow"
                f" ({tomorrow.strftime('%d %b %Y')})"
                + (
                    f" at {paper.start_time.strftime('%H:%M')}"
                    if paper.start_time
                    else ""
                )
                + f" for {exam.name}. Room: {paper.room or 'as announced'}."
            ),
            dedupe_key=f"{EVENT_EXAM_REMINDER}:{paper.id}",
            entity_type="exam_paper",
            entity_id=paper.id,
        )
    return told
