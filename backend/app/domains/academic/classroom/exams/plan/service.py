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
from dataclasses import dataclass
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
    SubjectTeacher,
)
from app.domains.academic.classroom.course import subjects as course_subjects
from app.domains.academic.classroom.course.models import (
    COURSE_ACTIVE,
    ClassroomSubject,
)
from app.domains.academic.classroom.exams.models import (
    EXAM_SCOPES,
    EXAM_STATUSES,
    Exam,
    ExamPaper,
    ExamPaperChapter,
    ExamPaperGroup,
    Mark,
    MarksAudit,
    PaperDraft,
)
from app.domains.academic.classroom.labels import labels_by_section
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

from . import grades, groups
from .schemas import (
    ExamCreateIn,
    ExamPaperRead,
    ExamRead,
    ExamUpdateIn,
    MarkChangeIn,
    MarkEntryIn,
    MarksSavedRead,
    MarksSaveIn,
    PaperGroupRead,
    PaperGroupUpdateIn,
    PaperMarkRowRead,
    PaperScheduleIn,
    ResultMarkRead,
    ResultPaperRead,
    ResultRowRead,
    ResultsRead,
    SkippedSectionRead,
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


def _course_or_404(session: Session, classroom_subject_id: UUID) -> ClassroomSubject:
    """This school's section subject, or a `404` - the one shared lookup."""
    return course_subjects.subject_or_404(session, classroom_subject_id)


def _group_or_404(session: Session, group_id: UUID) -> ExamPaperGroup:
    group = session.get(ExamPaperGroup, group_id)
    school = tenant_of(session)
    if group is None or (school is not None and group.school_id != school):
        raise HTTPException(status_code=404, detail="Shared paper not found")
    return group


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


def _held_course_ids(session: Session, user) -> set[UUID]:
    """The section subjects this teacher holds **right now** (the open history rows).

    "Right now" is `effective_to IS NULL`, so the teacher who left in September cannot
    enter October's marks. One query, whatever the number of subjects.
    """
    employee_id = _employee_of(session, user)
    if employee_id is None:
        return set()
    return {
        course_id
        for course_id in session.exec(
            select(SubjectTeacher.classroom_subject_id).where(
                SubjectTeacher.teacher_id == employee_id,
                SubjectTeacher.effective_to.is_(None),
                SubjectTeacher.classroom_subject_id.is_not(None),
            )
        ).all()
        if course_id is not None
    }


def _holds_course(session: Session, user, classroom_subject_id: UUID) -> bool:
    return classroom_subject_id in _held_course_ids(session, user)


def _may_plan_paper(session: Session, user, paper: ExamPaper) -> bool:
    """The office, or the teacher holding that paper's section subject now."""
    return _is_office(session, user) or _holds_course(
        session, user, paper.classroom_subject_id
    )


def _require_plan_paper(session: Session, user, paper: ExamPaper) -> None:
    if not _may_plan_paper(session, user, paper):
        raise HTTPException(
            status_code=403,
            detail="Only the subject's teacher or the office may change this paper.",
        )


def _paper_course(session: Session, paper: ExamPaper) -> ClassroomSubject:
    return _course_or_404(session, paper.classroom_subject_id)


# ---------------------------------------------------------------------------
# Telling people - one helper, so every exam event reads the same
# ---------------------------------------------------------------------------


def _students_of(
    session: Session,
    *,
    classroom_id: UUID | None = None,
    class_id: UUID | None = None,
    classroom_ids: set[UUID] | None = None,
) -> list[Student]:
    """Every child in one section, in a set of sections, or in a whole class."""
    statement = select(Student).join(Classroom, Classroom.id == Student.classroom_id)
    if classroom_id is not None:
        statement = statement.where(Student.classroom_id == classroom_id)
    if classroom_ids is not None:
        if not classroom_ids:
            return []
        statement = statement.where(Student.classroom_id.in_(classroom_ids))
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


def _marks_entered(session: Session, exam_id: UUID) -> dict[UUID, int]:
    rows = session.exec(
        select(Mark.exam_paper_id, func.count())
        .where(Mark.exam_id == exam_id)
        .group_by(Mark.exam_paper_id)
    ).all()
    return {paper_id: int(count) for paper_id, count in rows if paper_id is not None}


def _paper_reads(
    session: Session, papers: list[ExamPaper], user, entered: dict[UUID, int]
) -> list[ExamPaperRead]:
    """Many papers as the date sheet shows them - a fixed number of queries.

    Names, sections, groups, chapters and the lock are each read once for the whole list.
    """
    if not papers:
        return []
    courses = {
        course.id: course
        for course in session.exec(
            select(ClassroomSubject).where(
                ClassroomSubject.id.in_(
                    {paper.classroom_subject_id for paper in papers}
                )
            )
        ).all()
    }
    rooms = {
        room.id: room
        for room in session.exec(
            select(Classroom).where(
                Classroom.id.in_({course.classroom_id for course in courses.values()})
            )
        ).all()
    }
    labels = labels_by_section(session, list(rooms))

    group_ids = list({paper.paper_group_id for paper in papers if paper.paper_group_id})
    shared = (
        {
            group.id: group
            for group in session.exec(
                select(ExamPaperGroup).where(ExamPaperGroup.id.in_(group_ids))
            ).all()
        }
        if group_ids
        else {}
    )
    shared_chapters = groups.chapter_names(session, group_ids)
    locked = groups.locked_group_ids(session, group_ids)

    own_ids = [paper.id for paper in papers if paper.paper_group_id is None]
    own: dict[UUID, tuple[list[UUID], list[str]]] = {}
    if own_ids:
        for paper_id, chapter_id, name in session.exec(
            select(
                ExamPaperChapter.exam_paper_id,
                ExamPaperChapter.chapter_id,
                Chapter.name,
            )
            .join(Chapter, Chapter.id == ExamPaperChapter.chapter_id)
            .where(ExamPaperChapter.exam_paper_id.in_(own_ids))
            .order_by(Chapter.sequence)
        ).all():
            ids, names = own.setdefault(paper_id, ([], []))
            ids.append(chapter_id)
            names.append(name)

    office = _is_office(session, user)
    held = set() if office else _held_course_ids(session, user)

    reads: list[ExamPaperRead] = []
    for paper in papers:
        course = courses[paper.classroom_subject_id]
        room = rooms.get(course.classroom_id)
        group = shared.get(paper.paper_group_id) if paper.paper_group_id else None
        if group is not None:
            chapter_ids, chapter_list = [], shared_chapters.get(group.id, [])
        else:
            chapter_ids, chapter_list = own.get(paper.id, ([], []))
        can_edit = office or paper.classroom_subject_id in held
        reads.append(
            ExamPaperRead(
                id=paper.id,
                exam_id=paper.exam_id,
                classroom_subject_id=paper.classroom_subject_id,
                classroom_id=course.classroom_id,
                class_id=room.class_id if room is not None else paper.class_id,
                section=labels.get(course.classroom_id, ""),
                subject=course.name,
                title=(
                    group.display_title
                    if group and group.display_title
                    else course.name
                ),
                paper_group_id=paper.paper_group_id,
                group_locked=bool(group and group.id in locked),
                exam_date=paper.exam_date,
                start_time=paper.start_time,
                end_time=paper.end_time,
                max_marks=paper.max_marks,
                passing_marks=paper.passing_marks,
                room=paper.room,
                note=paper.note,
                published_at=paper.published_at,
                chapter_ids=chapter_ids,
                chapters=chapter_list,
                marks_entered=entered.get(paper.id, 0),
                can_edit=can_edit,
                can_detach=bool(group and can_edit),
            )
        )
    return reads


def _paper_read(
    session: Session, paper: ExamPaper, user, entered: int = 0
) -> ExamPaperRead:
    return _paper_reads(session, [paper], user, {paper.id: entered})[0]


def read_exam(session: Session, exam_id: UUID, user) -> ExamRead:
    """One exam, or a `404` when it belongs to another school."""
    return exam_read(session, _exam_or_404(session, exam_id), user)


def exam_read(session: Session, exam: Exam, user) -> ExamRead:
    """The exam with its date sheet, each paper saying whether this caller may edit it."""
    entered = _marks_entered(session, exam.id)
    papers = list(
        session.exec(
            select(ExamPaper)
            .where(ExamPaper.exam_id == exam.id)
            .order_by(ExamPaper.exam_date.nullslast(), ExamPaper.id)
        ).all()
    )
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
        papers=_paper_reads(session, papers, user, entered),
        groups=groups.read_groups(session, exam.id, papers),
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


@dataclass
class _Spec:
    """One date-sheet row once its subject is resolved to real section subjects."""

    row: PaperScheduleIn
    courses: list[ClassroomSubject]
    #: Set when two or more sections sit the same paper: the shared paper's title.
    title: str | None = None


def _check_in_scope(
    session: Session,
    course: ClassroomSubject,
    class_id: UUID | None,
    room: Classroom | None,
) -> None:
    """A named section subject must belong to the exam's section or class, and be live."""
    if course.status != COURSE_ACTIVE:
        raise HTTPException(status_code=409, detail="That subject is archived.")
    if room is not None and course.classroom_id != room.id:
        raise HTTPException(
            status_code=422, detail="That subject belongs to another class-section."
        )
    if class_id is not None:
        course_room = session.get(Classroom, course.classroom_id)
        if course_room is None or course_room.class_id != class_id:
            raise HTTPException(
                status_code=422, detail="That subject belongs to another class."
            )


def _resolve_rows(
    session: Session,
    rows: list[PaperScheduleIn],
    *,
    class_id: UUID | None,
    room: Classroom | None,
    year_id: UUID | None,
) -> tuple[list[_Spec], list[SkippedSectionRead]]:
    """Turn each row into the section subjects that will sit it. Nothing is created.

    A row naming one section subject is that subject. A row naming a subject **by name**
    expands to every section of the class that already has an active subject of that
    name in the exam's year; the sections that do not are returned as skipped - the
    office adds the subject in the Course tab first, an exam never invents one.
    """
    specs: list[_Spec] = []
    skipped: list[SkippedSectionRead] = []
    for row in rows:
        if row.classroom_subject_id is not None:
            course = _course_or_404(session, row.classroom_subject_id)
            _check_in_scope(session, course, class_id, room)
            specs.append(_Spec(row=row, courses=[course]))
            continue

        name = " ".join((row.subject_name or "").split())
        row_class = row.class_id or class_id
        if row_class is None:
            raise HTTPException(
                status_code=422,
                detail="A paper named by subject needs the class that sits it.",
            )
        statement = (
            select(ClassroomSubject)
            .join(Classroom, Classroom.id == ClassroomSubject.classroom_id)
            .where(
                Classroom.class_id == row_class,
                ClassroomSubject.status == COURSE_ACTIVE,
                func.lower(ClassroomSubject.name) == name.lower(),
            )
        )
        room_statement = select(Classroom).where(Classroom.class_id == row_class)
        if year_id is not None:
            statement = statement.where(ClassroomSubject.academic_year_id == year_id)
        if room is not None:
            statement = statement.where(ClassroomSubject.classroom_id == room.id)
            room_statement = room_statement.where(Classroom.id == room.id)
        courses = list(session.exec(statement).all())
        labels = labels_by_section(
            session,
            [course.classroom_id for course in courses]
            + [section.id for section in session.exec(room_statement).all()],
        )
        courses.sort(key=lambda course: labels.get(course.classroom_id, ""))
        taken = {course.classroom_id for course in courses}
        for section in session.exec(room_statement).all():
            if section.id not in taken:
                skipped.append(
                    SkippedSectionRead(
                        classroom_id=section.id,
                        section=labels.get(section.id, ""),
                        subject=name,
                    )
                )
        if not courses:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"No section of this class has an active subject named '{name}'. "
                    "Add it in the Course tab first."
                ),
            )
        specs.append(
            _Spec(row=row, courses=courses, title=name if len(courses) > 1 else None)
        )
    return specs, skipped


def _chapter_ids_by_name(
    session: Session, course: ClassroomSubject, names: list[str]
) -> list[UUID]:
    """This section subject's chapter ids for `names`; a missing name is a `409`."""
    wanted = groups.clean_names(names)
    if not wanted:
        return []
    have = {
        chapter.name.strip().lower(): chapter.id
        for chapter in session.exec(
            select(Chapter).where(Chapter.classroom_subject_id == course.id)
        ).all()
    }
    missing = [name for name in wanted if name.lower() not in have]
    if missing:
        raise HTTPException(
            status_code=409,
            detail=(
                f"{course.name} has no chapter named: {', '.join(missing)}. "
                "Add them in the Course tab or change the paper's chapters."
            ),
        )
    return [have[name.lower()] for name in wanted]


def _checked_chapter_ids(
    session: Session, course: ClassroomSubject, chapter_ids: list[UUID]
) -> list[UUID]:
    """Chapter ids that really belong to this section subject (else `404` / `422`)."""
    checked: list[UUID] = []
    school = tenant_of(session)
    for chapter_id in dict.fromkeys(chapter_ids):
        chapter = session.get(Chapter, chapter_id)
        if chapter is None or (school is not None and chapter.school_id != school):
            raise HTTPException(status_code=404, detail="Chapter not found")
        if chapter.classroom_subject_id != course.id:
            raise HTTPException(
                status_code=422,
                detail="That chapter belongs to another section's subject.",
            )
        checked.append(chapter_id)
    return checked


def _has_marks(session: Session, paper_id: UUID) -> bool:
    return (
        session.exec(select(Mark.id).where(Mark.exam_paper_id == paper_id)).first()
        is not None
    )


def _write_paper(
    session: Session,
    *,
    exam: Exam,
    course: ClassroomSubject,
    row: PaperScheduleIn,
    group_id: UUID | None,
    chapter_ids: list[UUID] | None,
    existing: ExamPaper | None = None,
) -> ExamPaper:
    """Build (or update) one section's sitting, refusing what cannot be true."""
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

    # What a score means must not change under marks already entered.
    if (
        existing is not None
        and Decimal(str(existing.max_marks)) != maximum
        and _has_marks(session, existing.id)
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                f"{course.name} already has marks entered, so its maximum cannot "
                "change. Clear the marks or correct them one by one."
            ),
        )

    paper = existing or ExamPaper(
        exam_id=exam.id, classroom_subject_id=course.id, paper_group_id=group_id
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

    # A shared paper's chapters live on its group; an own paper's are real chapter rows
    # of this section subject, replaced as a set so unticking a chapter removes it.
    if paper.paper_group_id is None and chapter_ids is not None:
        for link in session.exec(
            select(ExamPaperChapter).where(ExamPaperChapter.exam_paper_id == paper.id)
        ).all():
            session.delete(link)
        session.flush()
        for chapter_id in chapter_ids:
            session.add(ExamPaperChapter(exam_paper_id=paper.id, chapter_id=chapter_id))
        session.flush()
    return paper


def _build_spec(
    session: Session,
    exam: Exam,
    spec: _Spec,
    *,
    existing: dict[UUID, ExamPaper],
    user,
) -> tuple[list[ExamPaper], bool]:
    """Create or update the papers one resolved row stands for. Returns (papers, moved)."""
    row = spec.row
    moved = False
    papers: list[ExamPaper] = []

    new_courses = [course for course in spec.courses if course.id not in existing]
    group: ExamPaperGroup | None = None
    if row.classroom_subject_id is None and len(new_courses) > 1:
        group = groups.create_group(
            session,
            exam_id=exam.id,
            title=spec.title,
            chapter_names=row.chapters,
            user=user,
            school_id=exam.school_id,
        )

    for course in spec.courses:
        found = existing.get(course.id)
        if found is not None:
            if found.published_at is not None:
                raise HTTPException(
                    status_code=409,
                    detail=f"{course.name}: the marks are published; the paper cannot be re-cut.",
                )
            if found.exam_date != row.exam_date:
                moved = True
            papers.append(
                _write_paper(
                    session,
                    exam=exam,
                    course=course,
                    row=row,
                    group_id=found.paper_group_id,
                    chapter_ids=_own_chapter_ids(session, course, row, found),
                    existing=found,
                )
            )
            continue
        moved = True
        papers.append(
            _write_paper(
                session,
                exam=exam,
                course=course,
                row=row,
                group_id=group.id if group is not None else None,
                chapter_ids=None
                if group is not None
                else _own_chapter_ids(session, course, row, None),
            )
        )
    return papers, moved


def _own_chapter_ids(
    session: Session,
    course: ClassroomSubject,
    row: PaperScheduleIn,
    existing: ExamPaper | None,
) -> list[UUID] | None:
    """The chapter rows of an own (ungrouped) paper, or None to leave them alone."""
    if existing is not None and existing.paper_group_id is not None:
        return None
    if row.classroom_subject_id is not None:
        return _checked_chapter_ids(session, course, row.chapter_ids)
    return _chapter_ids_by_name(session, course, row.chapters)


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

    * a **class** exam is the office's, or the teacher's of every subject it lists;
    * a **school** exam is the office's only;
    * each row becomes one paper per section; sections sharing a paper share a group;
    * a section without a requested subject is reported in `skipped` - never invented.
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
    elif class_id is None:
        raise HTTPException(
            status_code=422, detail="A class exam needs a class or a class-section."
        )

    year_id = payload.academic_year_id or current_academic_year_id(session)
    specs, skipped = _resolve_rows(
        session,
        payload.papers,
        class_id=class_id if payload.scope != "school" else None,
        room=room,
        year_id=year_id,
    )
    if payload.scope != "school" and not office:
        held = _held_course_ids(session, user)
        for spec in specs:
            if any(course.id not in held for course in spec.courses):
                raise HTTPException(
                    status_code=403,
                    detail="A teacher may plan only the subjects they teach.",
                )

    seen: set[UUID] = set()
    for spec in specs:
        for course in spec.courses:
            if course.id in seen:
                raise HTTPException(
                    status_code=409,
                    detail=f"{course.name} already has a paper in this exam.",
                )
            seen.add(course.id)

    exam = Exam(
        name=payload.name,
        term=payload.term,
        exam_type=payload.exam_type,
        scope=payload.scope,
        class_id=class_id,
        classroom_id=room.id if room is not None else payload.classroom_id,
        academic_year_id=year_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        status=payload.status,
        note=payload.note,
        created_by_user_id=getattr(user, "id", None),
    )
    session.add(exam)
    session.flush()

    for spec in specs:
        _build_spec(session, exam, spec, existing={}, user=user)

    session.commit()
    session.refresh(exam)

    if payload.status == "scheduled":
        _announce(session, exam, event=EVENT_EXAM_SCHEDULED, changed=False)
    result = exam_read(session, exam, user)
    result.skipped = skipped
    return result


def _drop_paper(session: Session, paper: ExamPaper, name: str) -> None:
    """Remove a paper from the date sheet - only when nothing depends on it."""
    if paper.published_at is not None:
        raise HTTPException(
            status_code=409,
            detail=f"{name}: a published paper cannot be removed from the date sheet.",
        )
    if _has_marks(session, paper.id):
        raise HTTPException(
            status_code=409,
            detail=f"{name} already has marks entered, so its paper cannot be removed.",
        )
    group_id = paper.paper_group_id
    for link in session.exec(
        select(ExamPaperChapter).where(ExamPaperChapter.exam_paper_id == paper.id)
    ).all():
        session.delete(link)
    for draft in session.exec(
        select(PaperDraft).where(PaperDraft.exam_paper_id == paper.id)
    ).all():
        draft.exam_paper_id = None
        session.add(draft)
    session.delete(paper)
    session.flush()
    if group_id is not None:
        left = session.exec(
            select(ExamPaper.id).where(ExamPaper.paper_group_id == group_id)
        ).first()
        if left is None:
            _delete_group(session, group_id)


def _delete_group(session: Session, group_id: UUID) -> None:
    group = session.get(ExamPaperGroup, group_id)
    if group is None:
        return
    groups.set_chapters(session, group, [])
    for draft in session.exec(
        select(PaperDraft).where(PaperDraft.paper_group_id == group_id)
    ).all():
        draft.paper_group_id = None
        session.add(draft)
    session.flush()
    session.delete(group)
    session.flush()


def update_exam(
    session: Session, exam_id: UUID, payload: ExamUpdateIn, user
) -> ExamRead:
    """Change the dates, the syllabus or the note - and tell the families when it moved.

    The date sheet, when sent, is **replaced** by section subject: a paper missing from
    the payload is removed, so an unticked subject really disappears. A published paper,
    or one that already has marks, is refused with a `409` rather than silently re-cut.
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

    skipped: list[SkippedSectionRead] = []
    if payload.papers is not None:
        if not payload.papers:
            raise HTTPException(
                status_code=422, detail="An exam needs at least one paper."
            )
        room = session.get(Classroom, exam.classroom_id) if exam.classroom_id else None
        specs, skipped = _resolve_rows(
            session,
            payload.papers,
            class_id=exam.class_id if exam.scope != "school" else None,
            room=room,
            year_id=exam.academic_year_id,
        )
        existing = {
            paper.classroom_subject_id: paper
            for paper in session.exec(
                select(ExamPaper).where(ExamPaper.exam_id == exam.id)
            ).all()
        }
        kept: set[UUID] = set()
        for spec in specs:
            for course in spec.courses:
                if course.id in kept:
                    raise HTTPException(
                        status_code=409,
                        detail=f"{course.name} already has a paper in this exam.",
                    )
                kept.add(course.id)
            _, changed = _build_spec(session, exam, spec, existing=existing, user=user)
            moved = moved or changed

        names = {
            course.id: course.name
            for course in session.exec(
                select(ClassroomSubject).where(
                    ClassroomSubject.id.in_(set(existing) - kept or {None})
                )
            ).all()
        }
        for course_id, paper in existing.items():
            if course_id in kept:
                continue
            _drop_paper(session, paper, names.get(course_id, "That paper"))
            moved = True

    session.commit()
    session.refresh(exam)
    if moved and exam.status == "scheduled":
        _announce(session, exam, event=EVENT_EXAM_CHANGED, changed=True)
    result = exam_read(session, exam, user)
    result.skipped = skipped
    return result


# ---------------------------------------------------------------------------
# Shared papers - PATCH /exams/paper-groups/{id} and the detach action
# ---------------------------------------------------------------------------


def _group_papers(session: Session, group_id: UUID) -> list[ExamPaper]:
    return list(
        session.exec(
            select(ExamPaper).where(ExamPaper.paper_group_id == group_id)
        ).all()
    )


def _group_read(session: Session, group: ExamPaperGroup) -> PaperGroupRead:
    papers = _group_papers(session, group.id)
    for item in groups.read_groups(session, group.exam_id, papers):
        if item.id == group.id:
            return item
    return PaperGroupRead(
        id=group.id,
        exam_id=group.exam_id,
        display_title=group.display_title,
        chapters=groups.chapter_names(session, [group.id]).get(group.id, []),
        paper_ids=[paper.id for paper in papers],
        locked=groups.is_locked(session, group.id),
    )


def update_group(
    session: Session, group_id: UUID, payload: PaperGroupUpdateIn, user
) -> PaperGroupRead:
    """Edit what every section of a shared paper has in common.

    The office, or a teacher who holds **every** section's subject. Refused with `409`
    once any of its papers has a mark or is published: the question paper has been sat,
    so its title, chapters and maximum no longer change under the results. A section can
    still be detached to get a paper of its own.
    """
    group = _group_or_404(session, group_id)
    papers = _group_papers(session, group.id)
    if not _is_office(session, user):
        held = _held_course_ids(session, user)
        if not papers or any(
            paper.classroom_subject_id not in held for paper in papers
        ):
            raise HTTPException(
                status_code=403,
                detail="Only the office, or the teacher of every section, may edit a shared paper.",
            )
    if groups.is_locked(session, group.id):
        raise HTTPException(
            status_code=409,
            detail=(
                "Marks are entered or published for this shared paper, so it can no "
                "longer be edited. Give a section its own paper instead."
            ),
        )

    maximum = Decimal(str(payload.max_marks)) if payload.max_marks is not None else None
    if maximum is not None and maximum <= 0:
        raise HTTPException(
            status_code=422, detail="A paper must be out of more than 0."
        )
    passing = (
        Decimal(str(payload.passing_marks))
        if payload.passing_marks is not None
        else None
    )
    for paper in papers:
        top = maximum if maximum is not None else Decimal(str(paper.max_marks))
        if passing is not None and passing > top:
            raise HTTPException(
                status_code=422, detail="The passing marks cannot exceed the maximum."
            )

    if "display_title" in payload.model_fields_set:
        title = " ".join((payload.display_title or "").split())
        group.display_title = title or None
    if payload.chapters is not None:
        groups.set_chapters(session, group, payload.chapters)
    for paper in papers:
        if maximum is not None:
            paper.max_marks = maximum
        if passing is not None:
            paper.passing_marks = passing
        session.add(paper)
    group.updated_at = datetime.utcnow()
    session.add(group)
    session.commit()
    session.refresh(group)
    return _group_read(session, group)


def detach_paper(
    session: Session, group_id: UUID, paper_id: UUID, user
) -> ExamPaperRead:
    """Give one section its own paper, leaving the group for everyone else.

    The group's chapters are matched, by name, to this section subject's own chapters;
    a name with no match is a `409` that lists it - nothing is guessed or created. The
    group's question-paper draft, if any, is cloned for this paper. Allowed even when the
    group is locked: a detached paper is simply independent from then on.
    """
    paper = _paper_or_404(session, paper_id)
    if paper.paper_group_id != group_id:
        raise HTTPException(
            status_code=404, detail="That paper is not in this shared paper."
        )
    _require_plan_paper(session, user, paper)
    course = _paper_course(session, paper)

    names = groups.chapter_names(session, [group_id]).get(group_id, [])
    chapter_ids = _chapter_ids_by_name(session, course, names)

    paper.paper_group_id = None
    session.add(paper)
    session.flush()
    for link in session.exec(
        select(ExamPaperChapter).where(ExamPaperChapter.exam_paper_id == paper.id)
    ).all():
        session.delete(link)
    session.flush()
    for chapter_id in chapter_ids:
        session.add(ExamPaperChapter(exam_paper_id=paper.id, chapter_id=chapter_id))

    draft = session.exec(
        select(PaperDraft).where(PaperDraft.paper_group_id == group_id)
    ).first()
    if draft is not None:
        skip = {
            "id",
            "paper_group_id",
            "exam_paper_id",
            "classroom_subject_id",
            "created_at",
            "updated_at",
        }
        values = {
            column.name: getattr(draft, column.name)
            for column in PaperDraft.__table__.columns
            if column.name not in skip
        }
        session.add(
            PaperDraft(**values, classroom_subject_id=course.id, exam_paper_id=paper.id)
        )
    session.commit()
    session.refresh(paper)
    return _paper_read(
        session, paper, user, _marks_entered(session, paper.exam_id).get(paper.id, 0)
    )


def _teaches_exam(session: Session, user, course_ids: set[UUID]) -> bool:
    """True when this teacher holds one of the exam's section subjects right now."""
    return bool(_held_course_ids(session, user) & course_ids)


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

    A teacher sees the exams that have a paper of a subject they hold now; the office
    sees every exam of the school. The filter is read from the **assignments**, not from a
    client's list of ids.
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
        held = _held_course_ids(session, user)
        if not held or not exams:
            return []
        visible_ids = set(
            session.exec(
                select(ExamPaper.exam_id).where(
                    ExamPaper.exam_id.in_([exam.id for exam in exams]),
                    ExamPaper.classroom_subject_id.in_(held),
                )
            ).all()
        )
        exams = [exam for exam in exams if exam.id in visible_ids]
    return [exam_read(session, exam, user) for exam in exams]


# ---------------------------------------------------------------------------
# Marks - one writer, a draft, a publication, and an audited correction
# ---------------------------------------------------------------------------


def _section_students(session: Session, paper: ExamPaper) -> dict[UUID, Student]:
    """Every child in the paper's own section - who may be marked on it.

    A class exam has one paper per section, so a child is marked on exactly the paper of
    the section they sit in; another section's paper is another sheet.
    """
    course = _paper_course(session, paper)
    return {
        student.id: student
        for student in _students_of(session, classroom_id=course.classroom_id)
    }


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
    """The sheet for one paper: every child in its section, marked or not."""
    paper = _paper_or_404(session, paper_id)
    _require_plan_paper(session, user, paper)
    students = _section_students(session, paper)
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
    * every student must sit in the paper's section - a mark filed for somebody else's
      section would put them in two places at once;
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

    allowed = _section_students(session, paper)
    written = 0
    absent = 0
    for entry in payload.entries:
        student = allowed.get(entry.student_id)
        if student is None:
            raise HTTPException(
                status_code=422, detail="That student is not in this paper's section."
            )
        value, is_absent = _checked_score(paper, entry)
        mark = _mark_of(session, paper, entry.student_id)
        if mark is None:
            # The paper is the authority for the subject: the mark names only the paper
            # (and, until M5, the exam it hangs from).
            mark = Mark(
                exam_id=paper.exam_id,
                student_id=student.id,
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

    course = _paper_course(session, paper)
    students = [
        student
        for student_id in {mark.student_id for mark in marks}
        if (student := session.get(Student, student_id)) is not None
    ]
    _tell_students(
        session,
        students,
        event=EVENT_EXAM_PUBLISHED,
        title=f"{exam.name}: {course.name} published",
        body=(
            f"The {course.name} result for {exam.name} is out. "
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
    subject = _paper_course(session, paper)
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
    courses = {
        course.id: course
        for course in session.exec(
            select(ClassroomSubject).where(
                ClassroomSubject.id.in_(
                    {paper.classroom_subject_id for paper in papers}
                )
                if papers
                else ClassroomSubject.id.is_(None)
            )
        ).all()
    }
    paper_rooms = {course.classroom_id for course in courses.values()}
    section_labels = labels_by_section(session, list(paper_rooms))
    # The cohort is whoever sits one of this exam's section papers.
    students = {
        student.id: student
        for student in _students_of(session, classroom_ids=paper_rooms)
    }
    marks_by_student: dict[UUID, dict[UUID, Mark]] = {}
    for mark in session.exec(select(Mark).where(Mark.exam_id == exam.id)).all():
        if mark.exam_paper_id is None:
            continue
        marks_by_student.setdefault(mark.student_id, {})[mark.exam_paper_id] = mark

    cohort = set(students) | set(marks_by_student)
    staff = _is_leadership(session, user) or _teaches_exam(
        session, user, {paper.classroom_subject_id for paper in papers}
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
                    classroom_subject_id=paper.classroom_subject_id,
                    subject=courses[paper.classroom_subject_id].name,
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
                classroom_subject_id=paper.classroom_subject_id,
                classroom_id=courses[paper.classroom_subject_id].classroom_id,
                section=section_labels.get(
                    courses[paper.classroom_subject_id].classroom_id, ""
                ),
                subject=courses[paper.classroom_subject_id].name,
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
        course = session.get(ClassroomSubject, paper.classroom_subject_id)
        if course is None:
            continue
        shared = (
            session.get(ExamPaperGroup, paper.paper_group_id)
            if paper.paper_group_id
            else None
        )
        title = shared.display_title if shared and shared.display_title else course.name
        students = _students_of(session, classroom_id=course.classroom_id)
        told += _tell_students(
            session,
            students,
            event=EVENT_EXAM_REMINDER,
            title=f"{exam.name}: {title} is tomorrow",
            body=(
                f"{title} is scheduled for tomorrow"
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
