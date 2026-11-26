"""School Exam: one section's date sheet, its syllabus, and its publication.

A school exam is an `exam` of a school-exam type (`unit_test` ... `custom`) that belongs to
**one section** (`classroom_id`), with **one paper per subject** of that section: its
date, its total marks, its own pass line (marks or grade) and, written separately by the
subject teacher, its syllabus. There is no first or last day and no clock time.

Rules this module keeps
-----------------------
* **Who sets the date sheet:** the class teacher of that section, or leadership. The
  subject teacher does **not** (they write their own subject's syllabus).
* **Who writes a syllabus:** the subject's teacher, the class teacher, or leadership. It
  is free text - what will come in the exam.
* **Publication is the class teacher's** (or leadership's). Until then the sheet is a
  `draft`: families cannot see it (`service._visible_exam_ids`) and **nobody is
  notified**. Publishing tells the section's families once.
* **After publishing**, a changed date or total, a subject added or taken off, a changed
  note or a changed syllabus tells the families what changed.
* **One of a kind per section and year:** a second "Half Yearly" sheet for the same
  section is refused, not silently doubled. A custom exam is told apart by its name.
* **Marks protect the sheet:** a subject that has marks cannot be taken off, and a total
  cannot go below a mark already entered.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func
from sqlmodel import Session, select

from app.domains.academic.classroom.academics.models import Classroom
from app.domains.academic.classroom.course.models import COURSE_ACTIVE, ClassroomSubject
from app.domains.academic.classroom.exams.models import (
    SCHOOL_EXAM_TYPES,
    ExamType,
    Exam,
    ExamPaper,
    Mark,
)
from app.domains.academic.classroom.labels import labels_by_section
from app.domains.academic.classroom.repository import get_active_teacher_options

from . import marking, people
from .class_test import (
    _duplicates,
    _refuse_duplicates,
    _grade_mode,
    _apply_line,
    _clean_note,
    _day,
    _families,
    _figure,
    _pass_line,
    _pretty,
    _tell,
)
from .schemas import (
    ExamRead,
    SchoolExamCreateIn,
    SchoolExamRowIn,
    SchoolExamUpdateIn,
    SectionChoiceRead,
    SyllabusIn,
    SyllabusRead,
)
from .service import (
    _course_or_404,
    _exam_or_404,
    _held_course_ids,
    _is_leadership,
    _paper_or_404,
    _revision,
    _room_or_404,
    _visible_exam_ids,
    exam_read,
)

EVENT_PUBLISHED = "school_exam.published"
EVENT_CHANGED = "school_exam.changed"
EVENT_SYLLABUS = "school_exam.syllabus_changed"
EVENT_CANCELLED = "school_exam.cancelled"

#: How a type is written on a date sheet ("Mid Term Test"). `custom` uses the typed name.
TYPE_LABELS = {
    "unit_test": "Unit Test",
    "periodic_test": "Periodic Test",
    "mid_term_test": "Mid Term Test",
    "half_yearly": "Half Yearly",
    "annual": "Annual",
    "pre_board": "Pre-Board",
    "practical": "Practical",
    "custom": "Custom",
}


# ------------------------------------------------------------------ guards


def _school_exam_or_404(session: Session, exam_id: UUID) -> Exam:
    exam = _exam_or_404(session, exam_id)
    if exam.exam_type not in SCHOOL_EXAM_TYPES or exam.classroom_id is None:
        raise HTTPException(status_code=404, detail="School exam not found")
    return exam


def _require_date_sheet(session: Session, user, classroom_id: UUID) -> None:
    """The class teacher of the section, or leadership - never the subject teacher."""
    if _is_leadership(session, user):
        return
    if classroom_id in people.class_teacher_room_ids(session, user):
        return
    raise HTTPException(
        status_code=403,
        detail="Only the class teacher or the school's leadership may set the date sheet.",
    )


def _check_picked_taker(session: Session, taken_by: UUID | None) -> None:
    """A teacher picked to take a subject's paper must be teaching now. Nobody picked is
    fine on a date sheet: the subject's assigned teacher takes it, when there is one."""
    if taken_by is not None and taken_by not in {
        row[0] for row in get_active_teacher_options(session)
    }:
        raise HTTPException(status_code=422, detail="Pick a teacher who is teaching now.")


def _may_write_syllabus(
    session: Session, user, course: ClassroomSubject, paper: ExamPaper | None = None
) -> bool:
    """The subject's teacher, the teacher picked to write it, the class teacher of its
    section, or leadership."""
    if _is_leadership(session, user):
        return True
    if (
        paper is not None
        and paper.syllabus_by_employee_id is not None
        and paper.syllabus_by_employee_id == people.employee_of(session, user)
    ):
        return True
    if course.id in _held_course_ids(session, user):
        return True
    return course.classroom_id in people.class_teacher_room_ids(session, user)


# ------------------------------------------------------------- type and name


def _type_and_name(exam_type: str | None, custom_name: str | None) -> tuple[str, str]:
    kind = (exam_type or "").strip().lower()
    if kind not in SCHOOL_EXAM_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Pick a type: {', '.join(TYPE_LABELS[t] for t in SCHOOL_EXAM_TYPES)}.",
        )
    if kind == ExamType.custom:
        name = " ".join((custom_name or "").split())
        if not name:
            raise HTTPException(
                status_code=422, detail="Type the name of this exam."
            )
        if len(name) > 80:
            raise HTTPException(
                status_code=422, detail="The exam name can be at most 80 characters."
            )
        return kind, name
    return kind, TYPE_LABELS[kind]


def _refuse_twin(
    session: Session,
    classroom_id: UUID,
    year_id: UUID | None,
    kind: str,
    name: str,
    *,
    exclude: UUID | None = None,
) -> None:
    """One of a kind per section and year: not two Half Yearly sheets for 9-A."""
    statement = select(Exam.id).where(
        Exam.classroom_id == classroom_id,
        Exam.status != "cancelled",
        Exam.exam_type != "class_test",
    )
    if year_id is not None:
        statement = statement.where(Exam.academic_year_id == year_id)
    if kind == ExamType.custom:
        statement = statement.where(
            Exam.exam_type == ExamType.custom, func.lower(Exam.name) == name.lower()
        )
    else:
        statement = statement.where(Exam.exam_type == kind)
    if exclude is not None:
        statement = statement.where(Exam.id != exclude)
    if session.exec(statement).first() is not None:
        raise HTTPException(
            status_code=409,
            detail=f"A {name} date sheet already exists for this section.",
        )


# ---------------------------------------------------------------- the rows


def _check_rows(
    session: Session, room: Classroom, rows: list[SchoolExamRowIn]
) -> list[tuple[SchoolExamRowIn, ClassroomSubject]]:
    """Each row's subject must be an active subject of **this** section, once, in one year."""
    pairs: list[tuple[SchoolExamRowIn, ClassroomSubject]] = []
    seen: set[UUID] = set()
    for row in rows:
        course = _course_or_404(session, row.classroom_subject_id)
        if course.classroom_id != room.id:
            raise HTTPException(
                status_code=422,
                detail=f"{_pretty(course.name)} is not a subject of this section.",
            )
        if course.status != COURSE_ACTIVE:
            raise HTTPException(
                status_code=422,
                detail=f"{_pretty(course.name)} is archived and cannot be on a date sheet.",
            )
        if course.id in seen:
            raise HTTPException(
                status_code=422,
                detail=f"{_pretty(course.name)} is on the date sheet twice.",
            )
        seen.add(course.id)
        pairs.append((row, course))
    if len({course.academic_year_id for _, course in pairs}) > 1:
        raise HTTPException(
            status_code=422, detail="The subjects belong to different academic years."
        )
    return pairs


def _line_for(
    session: Session, row: SchoolExamRowIn, *, ladder: marking.Ladder | None = None
) -> marking.PassLine:
    return _pass_line(
        session,
        Decimal(str(row.total_marks)),
        mode=row.pass_mode,
        passing_marks=row.passing_marks,
        passing_grade=row.passing_grade,
        custom_min_percent=row.custom_min_percent,
        ladder=ladder,
    )


# ------------------------------------------------------------------- create


def _start_sheet(session: Session, payload: SchoolExamCreateIn, user) -> Exam:
    """Check and add one section's draft date sheet to the session (no commit)."""
    room = _room_or_404(session, payload.classroom_id)
    _require_date_sheet(session, user, room.id)
    kind, name = _type_and_name(payload.exam_type, payload.custom_name)
    pairs = _check_rows(session, room, payload.rows)
    year_id = payload.academic_year_id or pairs[0][1].academic_year_id
    _refuse_twin(session, room.id, year_id, kind, name)
    lines = [_line_for(session, row) for row, _ in pairs]
    for row, course in pairs:
        _check_picked_taker(session, row.taken_by_employee_id)
    if not payload.confirm_duplicate:
        found = []
        for row, course in pairs:
            found += _duplicates(session, {course.id}, row.exam_date)
        if found:
            _refuse_duplicates(found)

    exam = Exam(
        name=name,
        exam_type=kind,
        scope="class",
        class_id=room.class_id,
        classroom_id=room.id,
        academic_year_id=year_id,
        status="draft",
        family_note=_clean_note(payload.family_note),
        created_by_user_id=getattr(user, "id", None),
    )
    session.add(exam)
    session.flush()
    for (row, course), line in zip(pairs, lines, strict=True):
        paper = ExamPaper(
            exam_id=exam.id,
            classroom_subject_id=course.id,
            exam_date=row.exam_date,
            taken_by_employee_id=row.taken_by_employee_id,
        )
        _apply_line(paper, line, Decimal(str(row.total_marks)))
        paper.grade_mode = _grade_mode(row.grade_mode)
        session.add(paper)
    return exam


def _rows_for_section(
    session: Session, room: Classroom, anchor_pairs, label: str
) -> list[SchoolExamRowIn]:
    """The anchor sheet's rows, moved onto `room`'s own subjects by name."""
    own = {
        " ".join(course.name.split()).lower(): course
        for course in session.exec(
            select(ClassroomSubject).where(
                ClassroomSubject.classroom_id == room.id,
                ClassroomSubject.status == COURSE_ACTIVE,
            )
        ).all()
    }
    rows: list[SchoolExamRowIn] = []
    for row, course in anchor_pairs:
        match = own.get(" ".join(course.name.split()).lower())
        if match is not None and match.academic_year_id == course.academic_year_id:
            rows.append(row.model_copy(update={"classroom_subject_id": match.id}))
    if not rows:
        raise HTTPException(
            status_code=422,
            detail=f"{label} has none of the subjects on this date sheet.",
        )
    return rows


def create_school_exam(
    session: Session, payload: SchoolExamCreateIn, user
) -> ExamRead:
    """Set a section's date sheet - a **draft** nobody outside the school can see yet.

    With `section_ids` the same sheet is made for each of those sections of the class too
    (all or none: one section failing leaves nothing behind)."""
    first = _start_sheet(session, payload.model_copy(update={"section_ids": None}), user)
    others = [sid for sid in dict.fromkeys(payload.section_ids or []) if sid != payload.classroom_id]
    if others:
        room = _room_or_404(session, payload.classroom_id)
        anchor_pairs = _check_rows(session, room, payload.rows)
        labels = labels_by_section(session, others)
        for sid in others:
            other = _room_or_404(session, sid)
            if other.class_id != room.class_id:
                raise HTTPException(
                    status_code=422,
                    detail="All sections of one date sheet must belong to the same class.",
                )
            rows = _rows_for_section(session, other, anchor_pairs, labels.get(sid, "That section"))
            _start_sheet(
                session,
                payload.model_copy(
                    update={"classroom_id": sid, "rows": rows, "section_ids": None}
                ),
                user,
            )
    session.commit()
    session.refresh(first)
    return exam_read(session, first, user)


def sections_of_class(session: Session, classroom_id: UUID) -> list[SectionChoiceRead]:
    """Every class-section of this section's class that exists in this school, with its
    subjects - what the "Sections" pickers offer (a section nobody uses has no row yet)."""
    room = _room_or_404(session, classroom_id)
    rooms = session.exec(
        select(Classroom).where(Classroom.class_id == room.class_id)
    ).all()
    labels = labels_by_section(session, [r.id for r in rooms])
    names: dict[UUID, list[str]] = {r.id: [] for r in rooms}
    for owner, name in session.exec(
        select(ClassroomSubject.classroom_id, ClassroomSubject.name).where(
            ClassroomSubject.classroom_id.in_(list(names)),
            ClassroomSubject.status == COURSE_ACTIVE,
        )
    ).all():
        names[owner].append(name)
    return sorted(
        (
            SectionChoiceRead(
                classroom_id=r.id, label=labels.get(r.id, ""), subjects=sorted(names[r.id])
            )
            for r in rooms
        ),
        key=lambda item: item.label,
    )


# ------------------------------------------------------------------- update


def update_school_exam(
    session: Session, exam_id: UUID, payload: SchoolExamUpdateIn, user
) -> ExamRead:
    """Change a date sheet. Before it is published this is silent; after, the families
    are told what changed."""
    exam = _school_exam_or_404(session, exam_id)
    _require_date_sheet(session, user, exam.classroom_id)
    if exam.status == "cancelled":
        raise HTTPException(
            status_code=409, detail="This exam was cancelled and cannot be changed."
        )
    sent = payload.model_fields_set
    changes: list[str] = []

    # --- type and name
    if "exam_type" in sent or "custom_name" in sent:
        kind, name = _type_and_name(
            payload.exam_type or exam.exam_type,
            payload.custom_name if "custom_name" in sent else exam.name,
        )
        if (kind, name) != (exam.exam_type, exam.name):
            _refuse_twin(
                session, exam.classroom_id, exam.academic_year_id, kind, name, exclude=exam.id
            )
            changes.append(f"exam is now {name}")
            exam.exam_type, exam.name = kind, name

    # --- the note for families
    note_changed = False
    if "family_note" in sent:
        note = _clean_note(payload.family_note)
        note_changed = note != exam.family_note
        exam.family_note = note

    # --- the rows
    papers = list(session.exec(select(ExamPaper).where(ExamPaper.exam_id == exam.id)).all())
    if payload.rows is not None:
        room = _room_or_404(session, exam.classroom_id)
        pairs = _check_rows(session, room, payload.rows)
        if not payload.confirm_duplicate:
            held_dates = {paper.classroom_subject_id: paper.exam_date for paper in papers}
            found = []
            for row, course in pairs:
                if held_dates.get(course.id) != row.exam_date:
                    found += _duplicates(
                        session, {course.id}, row.exam_date, exclude_exam=exam.id
                    )
            if found:
                _refuse_duplicates(found)
        existing = {paper.classroom_subject_id: paper for paper in papers}
        names = {course.id: _pretty(course.name) for _, course in pairs}
        keep = {course.id for _, course in pairs}

        for paper in papers:
            if paper.classroom_subject_id in keep:
                continue
            course = _course_or_404(session, paper.classroom_subject_id)
            if session.exec(select(Mark.id).where(Mark.exam_paper_id == paper.id)).first():
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"{_pretty(course.name)} already has marks, so it cannot be "
                        "taken off the date sheet."
                    ),
                )
            changes.append(f"{_pretty(course.name)} taken off the date sheet")
            session.delete(paper)

        for row, course in pairs:
            total = Decimal(str(row.total_marks))
            paper = existing.get(course.id)
            if paper is None:
                _check_picked_taker(session, row.taken_by_employee_id)
                paper = ExamPaper(
                    exam_id=exam.id,
                    classroom_subject_id=course.id,
                    exam_date=row.exam_date,
                    taken_by_employee_id=row.taken_by_employee_id,
                )
                _apply_line(paper, _line_for(session, row), total)
                paper.grade_mode = _grade_mode(row.grade_mode)
                session.add(paper)
                changes.append(f"{names[course.id]} added ({_day(row.exam_date)})")
                continue
            old_total = Decimal(str(paper.max_marks))
            if total != old_total and session.exec(
                select(func.count())
                .select_from(Mark)
                .where(Mark.exam_paper_id == paper.id, Mark.marks_obtained > total)
            ).one():
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"{names[course.id]} has marks above {_figure(total)}. Correct "
                        "them before lowering the total."
                    ),
                )
            line = _line_for(
                session, row, ladder=marking.ladder_from_json(paper.grading_scale) or None
            )
            old_line = (paper.pass_mode, paper.passing_marks, paper.passing_grade)
            if row.exam_date != paper.exam_date:
                changes.append(
                    f"{names[course.id]}: {_day(paper.exam_date)} -> {_day(row.exam_date)}"
                )
            if total != old_total:
                changes.append(
                    f"{names[course.id]} total marks {_figure(old_total)} -> {_figure(total)}"
                )
            if (line.mode, line.passing_marks, line.passing_grade) != old_line:
                changes.append(f"{names[course.id]} pass line")
            if row.taken_by_employee_id != paper.taken_by_employee_id:
                _check_picked_taker(session, row.taken_by_employee_id)
                changes.append(f"{names[course.id]}: who takes it")
                paper.taken_by_employee_id = row.taken_by_employee_id
            paper.exam_date = row.exam_date
            _apply_line(paper, line, total)
            if row.grade_mode is not None:
                new_mode = _grade_mode(row.grade_mode)
                if new_mode != (paper.grade_mode or "na"):
                    if paper.published_at is not None:
                        raise HTTPException(
                            status_code=409,
                            detail=(
                                f"{names[course.id]} marks are published; change its Grade "
                                "column on the marks sheet."
                            ),
                        )
                    paper.grade_mode = new_mode
            session.add(paper)

    if not changes and not note_changed:
        return exam_read(session, exam, user)
    session.add(exam)
    session.commit()
    session.refresh(exam)

    # Before publication the sheet is the school's own: nobody outside is told.
    if exam.datesheet_published_at is not None:
        body = f"The {exam.name} date sheet has changed"
        if changes:
            body += ": " + "; ".join(changes[:8])
            if len(changes) > 8:
                body += f"; and {len(changes) - 8} more"
        if note_changed and not changes:
            body += ": the note for families changed"
        elif note_changed:
            body += "; the note for families changed"
        _tell(
            session,
            exam.id,
            _families(session, {exam.classroom_id}),
            event=EVENT_CHANGED,
            title=f"Date sheet changed: {exam.name}",
            body=body + ".",
            key=f"{EVENT_CHANGED}:{exam.id}:{_revision(session, EVENT_CHANGED, exam.id)}",
        )
    return exam_read(session, exam, user)


# ----------------------------------------------------------------- publish


def publish_date_sheet(session: Session, exam_id: UUID, user) -> ExamRead:
    """Publish the date sheet (and the syllabus with it): families can see it from now on.

    The class teacher's call (or leadership's). Publishing twice is a `409`: a second bell
    would be noise. This is the **only** moment the families are first told.
    """
    exam = _school_exam_or_404(session, exam_id)
    _require_date_sheet(session, user, exam.classroom_id)
    if exam.status == "cancelled":
        raise HTTPException(status_code=409, detail="This exam was cancelled.")
    if exam.datesheet_published_at is not None:
        raise HTTPException(
            status_code=409, detail="This date sheet is already published."
        )
    papers = list(
        session.exec(
            select(ExamPaper)
            .where(ExamPaper.exam_id == exam.id)
            .order_by(ExamPaper.exam_date, ExamPaper.id)
        ).all()
    )
    if not papers:
        raise HTTPException(
            status_code=422, detail="Add at least one subject before publishing."
        )
    if any(paper.exam_date is None for paper in papers):
        raise HTTPException(
            status_code=422, detail="Every subject needs a date before publishing."
        )
    courses = {
        course.id: course
        for course in session.exec(
            select(ClassroomSubject).where(
                ClassroomSubject.id.in_({p.classroom_subject_id for p in papers})
            )
        ).all()
    }
    exam.datesheet_published_at = datetime.utcnow()
    exam.datesheet_published_by_user_id = getattr(user, "id", None)
    if exam.status == "draft":  # marks may already have moved it on; never drag it back
        exam.status = "scheduled"
    session.add(exam)
    session.commit()
    session.refresh(exam)

    listing = ", ".join(
        f"{_pretty(courses[p.classroom_subject_id].name)} {_day(p.exam_date)}"
        for p in papers[:10]
    )
    if len(papers) > 10:
        listing += f" and {len(papers) - 10} more"
    body = f"The {exam.name} date sheet is out: {listing}."
    if exam.family_note:
        body += f" Note: {exam.family_note}"
    _tell(
        session,
        exam.id,
        _families(session, {exam.classroom_id}),
        event=EVENT_PUBLISHED,
        title=f"Date sheet: {exam.name}",
        body=body,
        key=f"{EVENT_PUBLISHED}:{exam.id}",
    )
    return exam_read(session, exam, user)


def cancel_school_exam(session: Session, exam_id: UUID, user) -> ExamRead:
    """Call a school exam off. The record and any marks stay; it takes no more marks. If
    the date sheet was published, the families are told."""
    exam = _school_exam_or_404(session, exam_id)
    _require_date_sheet(session, user, exam.classroom_id)
    if exam.status == "cancelled":
        raise HTTPException(status_code=409, detail="This exam is already cancelled.")
    exam.status = "cancelled"
    session.add(exam)
    session.commit()
    session.refresh(exam)
    if exam.datesheet_published_at is not None:
        _tell(
            session,
            exam.id,
            _families(session, {exam.classroom_id}),
            event=EVENT_CANCELLED,
            title=f"Exam cancelled: {exam.name}",
            body=f"The {exam.name} has been cancelled.",
            key=f"{EVENT_CANCELLED}:{exam.id}",
        )
    return exam_read(session, exam, user)


def archive_school_exam(
    session: Session, exam_id: UUID, user, *, archive: bool = True
) -> ExamRead:
    """Hide a date sheet from the list (or bring it back). Nothing is deleted and nobody
    is told: marks, results and the trail stay exactly as they were."""
    exam = _school_exam_or_404(session, exam_id)
    _require_date_sheet(session, user, exam.classroom_id)
    if archive and exam.datesheet_published_at is not None and exam.status != "cancelled":
        raise HTTPException(
            status_code=409,
            detail="This date sheet is published. Cancel it first; then it can be archived.",
        )
    exam.archived_at = datetime.utcnow() if archive else None
    session.add(exam)
    session.commit()
    session.refresh(exam)
    return exam_read(session, exam, user)


def delete_school_exam(session: Session, exam_id: UUID, user) -> None:
    """Throw away a date sheet that was never published and has no marks.

    Nobody outside the school ever saw it, so nobody is told. A published sheet is not
    deleted (families have seen it).
    """
    exam = _school_exam_or_404(session, exam_id)
    _require_date_sheet(session, user, exam.classroom_id)
    if exam.datesheet_published_at is not None:
        raise HTTPException(
            status_code=409,
            detail="This date sheet is published and cannot be deleted.",
        )
    papers = list(session.exec(select(ExamPaper).where(ExamPaper.exam_id == exam.id)).all())
    if papers and session.exec(
        select(Mark.id).where(Mark.exam_paper_id.in_([p.id for p in papers]))
    ).first():
        raise HTTPException(
            status_code=409, detail="Marks are already entered, so it cannot be deleted."
        )
    for paper in papers:
        session.delete(paper)
    session.flush()
    session.delete(exam)
    session.commit()


# ---------------------------------------------------------------- syllabus


def _syllabus_target(
    session: Session, paper_id: UUID
) -> tuple[ExamPaper, Exam, ClassroomSubject]:
    paper = _paper_or_404(session, paper_id)
    exam = _exam_or_404(session, paper.exam_id)
    return paper, exam, _course_or_404(session, paper.classroom_subject_id)


def _syllabus_read(
    session: Session, paper: ExamPaper, exam: Exam, course: ClassroomSubject, can_edit: bool
) -> SyllabusRead:
    return SyllabusRead(
        paper_id=paper.id,
        exam_id=exam.id,
        subject=course.name,
        section=labels_by_section(session, [course.classroom_id]).get(
            course.classroom_id, ""
        ),
        exam_name=exam.name,
        syllabus_text=paper.syllabus_text,
        can_edit=can_edit,
    )


def get_syllabus(session: Session, paper_id: UUID, user) -> SyllabusRead:
    """A subject's syllabus.

    The writers (subject teacher, class teacher, leadership) always read it. Anyone else
    reads it only once the date sheet is published, and only if the exam is theirs to see
    (a teacher of that section, or a family with a child in it).
    """
    paper, exam, course = _syllabus_target(session, paper_id)
    writer = _may_write_syllabus(session, user, course, paper)
    if not writer:
        if (
            exam.exam_type != "class_test" and exam.datesheet_published_at is None
        ) or exam.id not in _visible_exam_ids(
            session, user, [exam]
        ):
            raise HTTPException(status_code=404, detail="Syllabus not found")
    return _syllabus_read(session, paper, exam, course, writer)


def set_syllabus(
    session: Session, paper_id: UUID, payload: SyllabusIn, user
) -> SyllabusRead:
    """Write (or clear) a subject's syllabus. Silent until published, then the families
    are told which subject's syllabus changed."""
    paper, exam, course = _syllabus_target(session, paper_id)
    if not _may_write_syllabus(session, user, course, paper):
        raise HTTPException(
            status_code=403,
            detail=(
                "Only this subject's teacher, the class teacher or the school's "
                "leadership may write the syllabus."
            ),
        )
    if exam.status == "cancelled":
        raise HTTPException(status_code=409, detail="This exam was cancelled.")
    text = (payload.syllabus_text or "").strip() or None
    if text is not None and len(text) > 5000:
        raise HTTPException(
            status_code=422, detail="The syllabus can be at most 5000 characters."
        )
    if "by_employee_id" in payload.model_fields_set:
        picked = payload.by_employee_id
        if picked is not None and picked not in {
            row[0] for row in get_active_teacher_options(session)
        }:
            raise HTTPException(
                status_code=422, detail="Pick a teacher who is teaching now."
            )
        assigned = people.assigned_teachers(session, {course.id}).get(course.id)
        paper.syllabus_by_employee_id = None if picked == assigned else picked
    changed = text != (paper.syllabus_text or None)
    paper.syllabus_text = text
    session.add(paper)
    session.commit()
    session.refresh(paper)
    if changed and (exam.exam_type == "class_test" or exam.datesheet_published_at is not None):
        subject = _pretty(course.name)
        _tell(
            session,
            exam.id,
            _families(session, {course.classroom_id}),
            event=EVENT_SYLLABUS,
            title=f"Syllabus updated: {subject}",
            body=f"The {subject} syllabus for the {exam.name} has been updated.",
            key=f"{EVENT_SYLLABUS}:{paper.id}:{_revision(session, EVENT_SYLLABUS, exam.id)}",
        )
    return _syllabus_read(session, paper, exam, course, True)
