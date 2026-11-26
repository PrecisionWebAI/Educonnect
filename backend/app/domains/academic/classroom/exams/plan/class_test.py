"""Class Test: schedule, edit, cancel and delete one test for one or several sections.

A class test is an `exam` (`exam_type = class_test`, `scope = class`) with **one paper per
section that sits it**, all of one class. There is no date sheet: the test has one date, on
each of its papers. Marks, publication and results reuse the exam machinery unchanged.

Rules this module keeps
-----------------------
* **Who may schedule:** the teacher holding the subject, the class teacher of the section,
  or leadership (office, principal, vice principal). A teacher needs one of those for
  **every** chosen section.
* **One class only.** Sections of different classes cannot share a test.
* **Subject from existing courses.** A section subject has no school-wide identity, so the
  teacher names it once (the anchor section's row) and the other sections are matched by
  that subject's name; a section without it is refused, never invented.
* **Who takes it.** `taken_by_employee_id` NULL means each section's assigned teacher; a
  different teacher is a *temporary* teacher (derived live, never stored). A section with
  no assigned teacher needs somebody picked.
* **Its own pass line**, set at scheduling (`marking.py`); a test cannot be saved without
  one.
* **A duplicate is a warning, not a wall:** same section subject on the same date is
  answered with `409 DUPLICATE_EXAM` and the existing test's details; the teacher resends
  with `confirm_duplicate` to create it anyway.
* **What a notification says:** a *new date* is a reschedule (it states the new date);
  any other edit says **what** changed; a changed family note only says the note changed.
* **Delete vs cancel:** a test with marks cannot be deleted - it is cancelled (the record
  and the marks stay); a test with no marks may be deleted. Both tell the families.
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func
from sqlmodel import Session, select

from app.domains.academic.classroom.academics.models import Classroom
from app.domains.academic.classroom.course.models import COURSE_ACTIVE, ClassroomSubject
from app.domains.academic.classroom.exams.models import Exam, ExamPaper, Mark
from app.domains.academic.classroom.labels import labels_by_section
from app.domains.academic.classroom.repository import get_active_teacher_options
from app.domains.academic.classroom.students.models import Student
from app.domains.admin.users.models import User

from . import marking, people, setup
from .schemas import (
    ClassTestCreateIn,
    ClassTestUpdateIn,
    DuplicateExamRead,
    ExamRead,
)
from .service import (
    _course_or_404,
    _exam_or_404,
    _held_course_ids,
    _is_leadership,
    _revision,
    _room_or_404,
    _students_of,
    _tell_students,
    exam_read,
)

CLASS_TEST = "class_test"

EVENT_SCHEDULED = "class_test.scheduled"
EVENT_RESCHEDULED = "class_test.rescheduled"
EVENT_UPDATED = "class_test.updated"
EVENT_NOTE_CHANGED = "class_test.note_changed"
EVENT_DELETED = "class_test.deleted"
EVENT_CANCELLED = "class_test.cancelled"

#: Fields that change the pass line (any of them being sent means "look at it again").
_PASS_FIELDS = {"pass_mode", "passing_marks", "passing_grade", "custom_min_percent"}


# ------------------------------------------------------------------ small words


def _pretty(name: str) -> str:
    """`mathematics` -> `Mathematics` (subject names are stored lower-case)."""
    return " ".join(word.capitalize() for word in name.split())


def _day(value: date | None) -> str:
    return f"{value.day} {value:%b %Y}" if value is not None else "a date to be set"


def _figure(value: Decimal | None) -> str:
    """`50.00` -> `50`, `16.50` -> `16.5` - how a mark reads in a sentence."""
    if value is None:
        return "-"
    return f"{Decimal(str(value)).normalize():f}"


GRADE_MODES = ("na", "auto", "manual")


def _grade_mode(value: str | None, default: str = "na") -> str:
    mode = (value or default).strip().lower()
    if mode not in GRADE_MODES:
        raise HTTPException(
            status_code=422, detail="The grade column must be NA, Auto or Manual."
        )
    return mode


def _clean_syllabus(value: str | None) -> str | None:
    text = (value or "").strip() or None
    if text is not None and len(text) > 5000:
        raise HTTPException(
            status_code=422, detail="The syllabus can be at most 5000 characters."
        )
    return text


def _clean_note(value: str | None) -> str | None:
    text = (value or "").strip()
    return text or None


# ------------------------------------------------------------------- guards


def _class_test_or_404(session: Session, exam_id: UUID) -> Exam:
    exam = _exam_or_404(session, exam_id)
    if exam.exam_type != CLASS_TEST:
        raise HTTPException(status_code=404, detail="Class test not found")
    return exam


def _papers_of(session: Session, exam: Exam) -> list[ExamPaper]:
    return list(
        session.exec(
            select(ExamPaper)
            .where(ExamPaper.exam_id == exam.id)
            .order_by(ExamPaper.id)
        ).all()
    )


def _courses_of(session: Session, papers: list[ExamPaper]) -> dict[UUID, ClassroomSubject]:
    if not papers:
        return {}
    return {
        course.id: course
        for course in session.exec(
            select(ClassroomSubject).where(
                ClassroomSubject.id.in_({p.classroom_subject_id for p in papers})
            )
        ).all()
    }


def _may_manage(session: Session, user, courses: list[ClassroomSubject]) -> bool:
    """Leadership, or - for **every** chosen section - the subject teacher or class teacher."""
    if _is_leadership(session, user):
        return True
    held = _held_course_ids(session, user)
    rooms = people.class_teacher_room_ids(session, user)
    return bool(courses) and all(
        course.id in held or course.classroom_id in rooms for course in courses
    )


def _require_manage(session: Session, user, courses: list[ClassroomSubject]) -> None:
    if not _may_manage(session, user, courses):
        raise HTTPException(
            status_code=403,
            detail=(
                "Only the subject's teacher, the class teacher or the school's "
                "leadership may schedule this test."
            ),
        )


def _resolve_courses(
    session: Session,
    anchor: ClassroomSubject,
    section_ids: list[UUID],
    *,
    anchor_must_sit: bool,
) -> tuple[list[ClassroomSubject], dict[UUID, Classroom]]:
    """The section subjects that will sit the test, one per chosen section (in order).

    All sections must be of the anchor's class, and each must already have an active
    subject of the anchor's name in the anchor's year.
    """
    wanted = list(dict.fromkeys(section_ids))
    if anchor_must_sit and anchor.classroom_id not in wanted:
        raise HTTPException(
            status_code=422,
            detail="Pick the section that studies this subject for the test.",
        )
    anchor_room = _room_or_404(session, anchor.classroom_id)
    rooms = {sid: _room_or_404(session, sid) for sid in wanted}
    for room in rooms.values():
        if room.class_id != anchor_room.class_id:
            raise HTTPException(
                status_code=422,
                detail="All sections of one test must belong to the same class.",
            )
    labels = labels_by_section(session, wanted)
    name = " ".join(anchor.name.split()).lower()
    courses: list[ClassroomSubject] = []
    missing: list[str] = []
    for sid in wanted:
        course = session.exec(
            select(ClassroomSubject).where(
                ClassroomSubject.classroom_id == sid,
                ClassroomSubject.status == COURSE_ACTIVE,
                ClassroomSubject.academic_year_id == anchor.academic_year_id,
                func.lower(ClassroomSubject.name) == name,
            )
        ).first()
        if course is None:
            missing.append(labels.get(sid, "That section"))
        else:
            courses.append(course)
    if missing:
        raise HTTPException(
            status_code=422,
            detail=(
                f"{', '.join(missing)} has no subject named '{_pretty(anchor.name)}'. "
                "Add it in the Course tab first."
            ),
        )
    return courses, rooms


def _check_taker(
    session: Session,
    taken_by: UUID | None,
    courses: list[ClassroomSubject],
) -> None:
    """A picked teacher must be teaching now; with none picked every section needs an
    assigned teacher (otherwise nobody takes the test)."""
    if taken_by is not None:
        if taken_by not in {row[0] for row in get_active_teacher_options(session)}:
            raise HTTPException(
                status_code=422, detail="Pick a teacher who is teaching now."
            )
        return
    assigned = people.assigned_teachers(session, {course.id for course in courses})
    unstaffed = [course for course in courses if course.id not in assigned]
    if unstaffed:
        labels = labels_by_section(session, [c.classroom_id for c in unstaffed])
        names = ", ".join(labels.get(c.classroom_id, "A section") for c in unstaffed)
        raise HTTPException(
            status_code=422,
            detail=(
                f"No teacher is assigned to this subject in {names}. "
                "Pick who takes the test."
            ),
        )


def _pass_line(
    session: Session,
    total: Decimal,
    *,
    mode: str | None,
    passing_marks: Decimal | None,
    passing_grade: str | None,
    custom_min_percent: Decimal | None,
    ladder: marking.Ladder | None = None,
) -> marking.PassLine:
    try:
        return marking.resolve_pass_line(
            mode=mode,
            total=total,
            ladder=ladder or setup.school_ladder(session),
            passing_marks=passing_marks,
            passing_grade=passing_grade,
            custom_min_percent=custom_min_percent,
            default_percent=setup.school_pass_percent(session),
        )
    except marking.MarkingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _apply_line(paper: ExamPaper, line: marking.PassLine, total: Decimal) -> None:
    paper.max_marks = total
    paper.passing_marks = line.passing_marks
    paper.pass_mode = line.mode
    paper.pass_percent = line.pass_percent
    paper.passing_grade = line.passing_grade
    paper.grading_scale = marking.ladder_to_json(line.ladder)


# --------------------------------------------------------------- duplicates


def _duplicates(
    session: Session,
    course_ids: set[UUID],
    on: date,
    *,
    exclude_exam: UUID | None = None,
) -> list[DuplicateExamRead]:
    """Tests already set for the same section subject on the same date (not cancelled)."""
    if not course_ids:
        return []
    statement = (
        select(ExamPaper, Exam, ClassroomSubject)
        .join(Exam, Exam.id == ExamPaper.exam_id)
        .join(ClassroomSubject, ClassroomSubject.id == ExamPaper.classroom_subject_id)
        .where(
            ExamPaper.classroom_subject_id.in_(course_ids),
            ExamPaper.exam_date == on,
            Exam.status != "cancelled",
        )
    )
    if exclude_exam is not None:
        statement = statement.where(Exam.id != exclude_exam)
    rows = session.exec(statement).all()
    if not rows:
        return []
    labels = labels_by_section(session, [course.classroom_id for _, _, course in rows])
    creator_ids = {exam.created_by_user_id for _, exam, _ in rows if exam.created_by_user_id}
    creators = (
        {
            uid: name
            for uid, name in session.exec(
                select(User.id, User.full_name).where(User.id.in_(creator_ids))
            ).all()
        }
        if creator_ids
        else {}
    )
    return [
        DuplicateExamRead(
            exam_id=exam.id,
            name=exam.name,
            exam_date=paper.exam_date,
            subject=course.name,
            total_marks=paper.max_marks,
            section=labels.get(course.classroom_id, ""),
            created_by=creators.get(exam.created_by_user_id),
            status=exam.status,
        )
        for paper, exam, course in rows
    ]


def _refuse_duplicates(found: list[DuplicateExamRead]) -> None:
    """`409` carrying the existing tests, so the screen can show them in a popup."""
    raise HTTPException(
        status_code=409,
        detail={
            "code": "DUPLICATE_EXAM",
            "message": (
                "A test for this class, section, subject and date already exists. "
                "Create it anyway?"
            ),
            "existing": [item.model_dump(mode="json") for item in found],
        },
    )


# ------------------------------------------------------------- notifications


def _families(session: Session, room_ids: set[UUID]) -> list[Student]:
    return _students_of(session, classroom_ids=set(room_ids)) if room_ids else []


def _tell(
    session: Session,
    exam_id: UUID,
    students: list[Student],
    *,
    event: str,
    title: str,
    body: str,
    key: str,
) -> int:
    return _tell_students(
        session,
        students,
        event=event,
        title=title,
        body=body,
        dedupe_key=key,
        entity_type="exam",
        entity_id=exam_id,
    )


# -------------------------------------------------------------------- create


def create_class_test(session: Session, payload: ClassTestCreateIn, user) -> ExamRead:
    """Schedule a class test for one or several sections and tell their families."""
    anchor = _course_or_404(session, payload.classroom_subject_id)
    courses, rooms = _resolve_courses(
        session, anchor, payload.section_ids, anchor_must_sit=True
    )
    _require_manage(session, user, courses)
    _check_taker(session, payload.taken_by_employee_id, courses)
    total = Decimal(str(payload.total_marks))
    line = _pass_line(
        session,
        total,
        mode=payload.pass_mode,
        passing_marks=payload.passing_marks,
        passing_grade=payload.passing_grade,
        custom_min_percent=payload.custom_min_percent,
    )

    found = _duplicates(session, {c.id for c in courses}, payload.exam_date)
    if found and not payload.confirm_duplicate:
        _refuse_duplicates(found)

    note = _clean_note(payload.family_note)
    syllabus = _clean_syllabus(payload.syllabus_text)
    exam = Exam(
        name=f"Class Test - {_pretty(anchor.name)}",
        exam_type=CLASS_TEST,
        scope="class",
        class_id=next(iter(rooms.values())).class_id,
        classroom_id=None,
        academic_year_id=payload.academic_year_id or anchor.academic_year_id,
        status="scheduled",
        family_note=note,
        created_by_user_id=getattr(user, "id", None),
    )
    session.add(exam)
    session.flush()
    for course in courses:
        paper = ExamPaper(
            exam_id=exam.id,
            classroom_subject_id=course.id,
            exam_date=payload.exam_date,
            taken_by_employee_id=payload.taken_by_employee_id,
            syllabus_text=syllabus,
            grade_mode=_grade_mode(payload.grade_mode),
        )
        _apply_line(paper, line, total)
        session.add(paper)
    session.commit()
    session.refresh(exam)

    subject = _pretty(anchor.name)
    body = (
        f"{subject} class test on {_day(payload.exam_date)}. "
        f"Total marks: {_figure(total)}."
    )
    if syllabus:
        body += " Syllabus is added."
    if note:
        body += f" Note: {note}"
    _tell(
        session,
        exam.id,
        _families(session, {c.classroom_id for c in courses}),
        event=EVENT_SCHEDULED,
        title=f"Class Test: {subject}",
        body=body,
        key=f"{EVENT_SCHEDULED}:{exam.id}",
    )
    return exam_read(session, exam, user)


# -------------------------------------------------------------------- update


def update_class_test(
    session: Session, exam_id: UUID, payload: ClassTestUpdateIn, user
) -> ExamRead:
    """Change a class test; tell the families what changed (and only that).

    A new date is a **reschedule**. Any other change (total marks, pass line, who takes
    it, sections) says what changed. A changed family note only says the note changed.
    """
    exam = _class_test_or_404(session, exam_id)
    if exam.status == "cancelled":
        raise HTTPException(
            status_code=409, detail="This test was cancelled and cannot be changed."
        )
    papers = _papers_of(session, exam)
    if not papers:
        raise HTTPException(status_code=409, detail="This test has no sections left.")
    courses = _courses_of(session, papers)
    _require_manage(session, user, list(courses.values()))

    sent = payload.model_fields_set
    first = papers[0]
    subject = _pretty(courses[first.classroom_subject_id].name)
    old_date = first.exam_date
    old_total = Decimal(str(first.max_marks))
    changes: list[str] = []

    # --- date -> a reschedule
    new_date = payload.exam_date if payload.exam_date is not None else old_date
    date_changed = new_date != old_date

    # --- total marks (never below a mark already entered)
    new_total = (
        Decimal(str(payload.total_marks)) if payload.total_marks is not None else old_total
    )
    total_changed = new_total != old_total
    if total_changed:
        above = session.exec(
            select(func.count())
            .select_from(Mark)
            .where(
                Mark.exam_paper_id.in_([p.id for p in papers]),
                Mark.marks_obtained > new_total,
            )
        ).one()
        if above:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"{above} mark(s) already entered are above {_figure(new_total)}. "
                    "Correct those marks before lowering the total."
                ),
            )
        changes.append(f"total marks {_figure(old_total)} -> {_figure(new_total)}")

    # --- pass line
    line: marking.PassLine | None = None
    if (sent & _PASS_FIELDS) or total_changed:
        stored = marking.ladder_from_json(first.grading_scale)
        mode = payload.pass_mode or first.pass_mode or marking.MODE_MARKS
        passing_marks = payload.passing_marks
        if (
            passing_marks is None
            and "passing_marks" not in sent
            and total_changed
            and mode == marking.MODE_MARKS
            and first.passing_marks is not None
            and Decimal(str(first.passing_marks))
            != marking.default_pass_marks(old_total, setup.school_pass_percent(session))
        ):
            passing_marks = Decimal(str(first.passing_marks))  # the teacher's own number stays
        line = _pass_line(
            session,
            new_total,
            mode=mode,
            passing_marks=passing_marks,
            passing_grade=payload.passing_grade
            if "passing_grade" in sent
            else first.passing_grade,
            custom_min_percent=payload.custom_min_percent,
            ladder=stored or None,
        )
        if (line.mode, line.passing_marks, line.passing_grade) != (
            first.pass_mode,
            first.passing_marks,
            first.passing_grade,
        ):
            changes.append(
                f"passing marks {_figure(first.passing_marks)} -> {_figure(line.passing_marks)}"
                if line.mode == marking.MODE_MARKS
                else f"passing grade {line.passing_grade}"
            )

    # --- who takes it
    taken_by = first.taken_by_employee_id
    if "taken_by_employee_id" in sent:
        taken_by = payload.taken_by_employee_id
    sections_in_play = list(courses.values())

    # --- sections
    labels_now = labels_by_section(session, [c.classroom_id for c in courses.values()])
    kept_by_room = {
        courses[p.classroom_subject_id].classroom_id: p for p in papers
    }
    removed_rooms: set[UUID] = set()
    added_courses: list[ClassroomSubject] = []
    if payload.section_ids is not None:
        desired = list(dict.fromkeys(payload.section_ids))
        anchor = courses[first.classroom_subject_id]
        resolved, _ = _resolve_courses(session, anchor, desired, anchor_must_sit=False)
        by_room = {course.classroom_id: course for course in resolved}
        added_courses = [c for room, c in by_room.items() if room not in kept_by_room]
        removed_rooms = {room for room in kept_by_room if room not in by_room}
        for room in removed_rooms:
            if session.exec(
                select(Mark.id).where(Mark.exam_paper_id == kept_by_room[room].id)
            ).first():
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"{labels_now.get(room, 'That section')} already has marks, so it "
                        "cannot be taken off this test."
                    ),
                )
        sections_in_play = [
            c for c in courses.values() if c.classroom_id not in removed_rooms
        ] + added_courses
        if added_courses or removed_rooms:
            _require_manage(session, user, added_courses)
            added_labels = labels_by_section(
                session, [c.classroom_id for c in added_courses]
            )
            parts = []
            if added_courses:
                parts.append(
                    "added " + ", ".join(added_labels.get(c.classroom_id, "") for c in added_courses)
                )
            if removed_rooms:
                parts.append(
                    "removed " + ", ".join(labels_now.get(r, "") for r in removed_rooms)
                )
            changes.append("sections " + " and ".join(parts))

    if "taken_by_employee_id" in sent or added_courses:
        _check_taker(session, taken_by, sections_in_play)
    if taken_by != first.taken_by_employee_id:
        changes.append("who takes the test")

    # --- syllabus (free text): says it changed, never the text itself
    syllabus = first.syllabus_text
    if "syllabus_text" in sent:
        syllabus = _clean_syllabus(payload.syllabus_text)
        if syllabus != (first.syllabus_text or None):
            changes.append("syllabus")

    # --- family note: its own message, never a reschedule
    note_changed = False
    if "family_note" in sent:
        note = _clean_note(payload.family_note)
        note_changed = note != exam.family_note
        exam.family_note = note

    # --- the Grade column's mode (only while no paper is published; after that the marks
    # sheet changes it)
    mode_changed = False
    if "grade_mode" in sent and payload.grade_mode is not None:
        new_mode = _grade_mode(payload.grade_mode)
        if new_mode != (first.grade_mode or "na"):
            if any(paper.published_at is not None for paper in papers):
                raise HTTPException(
                    status_code=409,
                    detail="The marks are published; change the Grade column on the marks sheet.",
                )
            for paper in papers:
                paper.grade_mode = new_mode
                session.add(paper)
            mode_changed = True

    nothing = not (date_changed or changes or note_changed)
    if nothing:
        if mode_changed:
            session.commit()
            session.refresh(exam)
        return exam_read(session, exam, user)

    # --- duplicates: only for what is new (a new date, or a section just added)
    check_ids: set[UUID] = set()
    if date_changed:
        check_ids |= {c.id for c in sections_in_play}
    else:
        check_ids |= {c.id for c in added_courses}
    found = (
        _duplicates(session, check_ids, new_date, exclude_exam=exam.id)
        if check_ids and new_date is not None
        else []
    )
    if found and not payload.confirm_duplicate:
        session.rollback()
        _refuse_duplicates(found)

    # --- write
    removed_students = _families(session, removed_rooms)
    for room in removed_rooms:
        session.delete(kept_by_room[room])
    for paper in papers:
        if courses[paper.classroom_subject_id].classroom_id in removed_rooms:
            continue
        paper.exam_date = new_date
        paper.taken_by_employee_id = taken_by
        paper.syllabus_text = syllabus
        if line is not None:
            _apply_line(paper, line, new_total)
        session.add(paper)
    base_line = line or marking.PassLine(
        first.pass_mode or marking.MODE_MARKS,
        Decimal(str(first.passing_marks or 0)),
        first.passing_grade,
        Decimal(str(first.pass_percent or 0)),
        marking.ladder_from_json(first.grading_scale),
    )
    for course in added_courses:
        paper = ExamPaper(
            exam_id=exam.id,
            classroom_subject_id=course.id,
            exam_date=new_date,
            taken_by_employee_id=taken_by,
            syllabus_text=syllabus,
            grade_mode=first.grade_mode or "na",
        )
        _apply_line(paper, base_line, new_total)
        session.add(paper)
    session.add(exam)
    session.commit()
    session.refresh(exam)

    # --- tell the families
    families = _families(session, {c.classroom_id for c in sections_in_play})
    revision = _revision(session, EVENT_RESCHEDULED, exam.id) + _revision(
        session, EVENT_UPDATED, exam.id
    ) + _revision(session, EVENT_NOTE_CHANGED, exam.id)
    if date_changed:
        body = f"The {subject} class test has moved to {_day(new_date)} (was {_day(old_date)})."
        if changes:
            body += " Also changed: " + "; ".join(changes) + "."
        if note_changed:
            body += " The note for families changed."
        _tell(
            session, exam.id, families,
            event=EVENT_RESCHEDULED,
            title=f"Class Test rescheduled: {subject}",
            body=body,
            key=f"{EVENT_RESCHEDULED}:{exam.id}:{revision}",
        )
    elif changes:
        body = f"The {subject} class test on {_day(new_date)} changed: " + "; ".join(changes) + "."
        if note_changed:
            body += " The note for families changed."
        _tell(
            session, exam.id, families,
            event=EVENT_UPDATED,
            title=f"Class Test updated: {subject}",
            body=body,
            key=f"{EVENT_UPDATED}:{exam.id}:{revision}",
        )
    elif note_changed:
        _tell(
            session, exam.id, families,
            event=EVENT_NOTE_CHANGED,
            title=f"Class Test note changed: {subject}",
            body=f"The note for families on the {subject} class test has changed.",
            key=f"{EVENT_NOTE_CHANGED}:{exam.id}:{revision}",
        )
    if removed_students:
        _tell(
            session, exam.id, removed_students,
            event=EVENT_CANCELLED,
            title=f"Class Test cancelled: {subject}",
            body=f"The {subject} class test on {_day(old_date)} no longer includes your section.",
            key=f"{EVENT_CANCELLED}:{exam.id}:removed:{revision}",
        )
    return exam_read(session, exam, user)


# ------------------------------------------------------ cancel and delete


def archive_class_test(
    session: Session, exam_id: UUID, user, *, archive: bool = True
) -> ExamRead:
    """Hide a class test from the list (or bring it back). The families already know about
    a scheduled test, so it must be **cancelled first**; nothing is deleted or announced."""
    exam = _class_test_or_404(session, exam_id)
    papers = _papers_of(session, exam)
    courses = _courses_of(session, papers)
    _require_manage(session, user, list(courses.values()))
    if archive and exam.status != "cancelled":
        raise HTTPException(
            status_code=409,
            detail="This test is scheduled. Cancel it first; then it can be archived.",
        )
    exam.archived_at = datetime.utcnow() if archive else None
    session.add(exam)
    session.commit()
    session.refresh(exam)
    return exam_read(session, exam, user)


def cancel_class_test(session: Session, exam_id: UUID, user) -> ExamRead:
    """Call the test off. The record and any marks stay; the families are told."""
    exam = _class_test_or_404(session, exam_id)
    if exam.status == "cancelled":
        raise HTTPException(status_code=409, detail="This test is already cancelled.")
    papers = _papers_of(session, exam)
    courses = _courses_of(session, papers)
    _require_manage(session, user, list(courses.values()))
    subject = _pretty(next(iter(courses.values())).name) if courses else "Class"
    on = papers[0].exam_date if papers else None
    exam.status = "cancelled"
    session.add(exam)
    session.commit()
    session.refresh(exam)
    _tell(
        session,
        exam.id,
        _families(session, {c.classroom_id for c in courses.values()}),
        event=EVENT_CANCELLED,
        title=f"Class Test cancelled: {subject}",
        body=f"The {subject} class test on {_day(on)} has been cancelled.",
        key=f"{EVENT_CANCELLED}:{exam.id}",
    )
    return exam_read(session, exam, user)


def delete_class_test(session: Session, exam_id: UUID, user) -> None:
    """Remove a test nobody has marks for; tell the families it is gone.

    A test with marks is never deleted (the marks would go with it): cancel it instead.
    """
    exam = _class_test_or_404(session, exam_id)
    papers = _papers_of(session, exam)
    courses = _courses_of(session, papers)
    _require_manage(session, user, list(courses.values()))
    if papers and session.exec(
        select(Mark.id).where(Mark.exam_paper_id.in_([p.id for p in papers]))
    ).first():
        raise HTTPException(
            status_code=409,
            detail="Marks are already entered for this test, so it cannot be deleted. Cancel it instead.",
        )
    subject = _pretty(next(iter(courses.values())).name) if courses else "Class"
    on = papers[0].exam_date if papers else None
    # Who to tell is read **before** the rows go; the message is sent after the delete
    # committed, so a failed delete never announces a deletion.
    families = _families(session, {c.classroom_id for c in courses.values()})
    was = (exam.id,)
    for paper in papers:
        session.delete(paper)
    session.flush()
    session.delete(exam)
    session.commit()
    _tell(
        session,
        was[0],
        families,
        event=EVENT_DELETED,
        title=f"Class Test deleted: {subject}",
        body=f"The {subject} class test on {_day(on)} has been deleted.",
        key=f"{EVENT_DELETED}:{was[0]}",
    )
