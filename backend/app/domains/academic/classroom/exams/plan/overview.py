"""The result overview: every test, the subject-wise percentage so far, and the overall one.

One **kind** at a time - Class Test results or School Exam results, never mixed - for the
academic year on screen. Everything is derived from the marks, never stored.

The numbers (D14 in `phase3.md`)
--------------------------------
* **A test** (one paper): `obtained / total * 100`, judged by **that paper's own** pass line
  and grading ladder (`marks_text`).
* **A subject so far**: `sum obtained / sum total` over that subject's tests - *weighted*,
  because tests have different totals - **not** the average of the percentages.
* **Overall**: `sum obtained / sum total` over every test so far.
* **An absent child** is left out of both sums (and shown as "Absent"); an unmarked child
  likewise. Zero is a score. Only **published** tests count anywhere.

Who sees what
-------------
* **Leadership**: any section. **A teacher**: a section where they hold a subject or are the
  class teacher - the *class view* with class average, highest, lowest, passed and failed per
  test. **A student or guardian**: only their own children, only published tests, and no
  class figures at all. Anybody else: `404`, never a `403` that confirms the section exists.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import or_
from sqlmodel import Session, select

from app.domains.academic.classroom.course.models import ClassroomSubject
from app.domains.academic.classroom.exams.models import Exam, ExamPaper, Mark
from app.domains.academic.classroom.labels import labels_by_section
from app.domains.academic.classroom.students.models import Student
from app.domains.admin.settings import year_scope
from app.domains.admin.settings.academic_year_context import current_academic_year_id

from . import marking, marks_text, people, setup
from .schemas import (
    OverviewEntryRead,
    OverviewStatsRead,
    OverviewStudentRead,
    OverviewSubjectRead,
    OverviewTestRead,
    OverviewTotalRead,
    ResultOverviewRead,
)
from .service import (
    _family_children,
    _held_course_ids,
    _is_leadership,
    _name_of,
    _room_or_404,
    _students_of,
)

KINDS = ("class_test", "school_exam")


# ----------------------------------------------------------------- the maths


@dataclass(frozen=True)
class Score:
    """One child's result on one test, reduced to what the sums need."""

    subject: str
    total: Decimal
    obtained: Decimal | None
    absent: bool
    passed: bool | None


def _percent(obtained: Decimal, total: Decimal) -> Decimal | None:
    return marking.percentage(obtained, total) if total > 0 else None


def fold(
    scores: list[Score], ladder: marking.Ladder
) -> tuple[list[OverviewSubjectRead], OverviewTotalRead]:
    """Subject-wise and overall totals from a child's scores (see the module docstring).

    Subjects are grouped by their (case-insensitive) name, so a child who moved section in
    the year keeps one Mathematics line; within a section the name is unique anyway.
    """
    subjects: dict[str, dict] = {}
    overall = {
        "obtained": Decimal(0),
        "total": Decimal(0),
        "counted": 0,
        "absent": 0,
        "passed": 0,
        "failed": 0,
    }
    for score in scores:
        line = subjects.setdefault(
            score.subject.strip().lower(),
            {
                "name": score.subject,
                "obtained": Decimal(0),
                "total": Decimal(0),
                "counted": 0,
                "absent": 0,
            },
        )
        if score.absent:
            line["absent"] += 1
            overall["absent"] += 1
            continue
        if score.obtained is None:
            continue  # not marked yet: nothing to add, nothing to count
        line["obtained"] += score.obtained
        line["total"] += score.total
        line["counted"] += 1
        overall["obtained"] += score.obtained
        overall["total"] += score.total
        overall["counted"] += 1
        if score.passed is True:
            overall["passed"] += 1
        elif score.passed is False:
            overall["failed"] += 1

    rows = []
    for key in sorted(subjects):
        line = subjects[key]
        percent = _percent(line["obtained"], line["total"])
        rows.append(
            OverviewSubjectRead(
                subject=line["name"],
                obtained=line["obtained"],
                total=line["total"],
                percentage=percent,
                grade=marking.grade_for(ladder, percent),
                tests_counted=line["counted"],
                tests_absent=line["absent"],
            )
        )
    percent = _percent(overall["obtained"], overall["total"])
    total = OverviewTotalRead(
        obtained=overall["obtained"],
        total=overall["total"],
        percentage=percent,
        grade=marking.grade_for(ladder, percent),
        tests_counted=overall["counted"],
        tests_absent=overall["absent"],
        tests_passed=overall["passed"],
        tests_failed=overall["failed"],
    )
    return rows, total


def stats_of(
    total: Decimal, results: list[marks_text.Figures]
) -> OverviewStatsRead:
    """The class view of one test: average, highest, lowest, passed, failed.

    Absent children are counted as absent and stay out of every figure; a child with no
    mark yet is not counted at all.
    """
    scored = [r for r in results if r.obtained is not None]
    absent = sum(1 for r in results if r.absent)
    if not scored:
        return OverviewStatsRead(absent=absent)
    values = [r.obtained for r in scored]
    average = sum(values, Decimal(0)) / len(values)
    return OverviewStatsRead(
        marked=len(scored),
        absent=absent,
        average_marks=marking.round2(average),
        average_percentage=_percent(average, total),
        highest=max(values),
        lowest=min(values),
        passed=sum(1 for r in scored if r.passed is True),
        failed=sum(1 for r in scored if r.passed is False),
    )


# --------------------------------------------------------------- the queries


def _papers(
    session: Session, kind: str, classroom_ids: set[UUID]
) -> list[tuple[ExamPaper, Exam, ClassroomSubject]]:
    """Every paper of this kind, for these sections, in the year on screen."""
    year_id = current_academic_year_id(session)
    statement = (
        select(ExamPaper, Exam, ClassroomSubject)
        .join(Exam, Exam.id == ExamPaper.exam_id)
        .join(ClassroomSubject, ClassroomSubject.id == ExamPaper.classroom_subject_id)
        .where(
            ClassroomSubject.classroom_id.in_(classroom_ids),
            Exam.status != "cancelled",
        )
    )
    if year_id is not None:
        statement = statement.where(
            or_(Exam.academic_year_id == year_id, Exam.academic_year_id.is_(None))
        )
    if kind == "class_test":
        statement = statement.where(Exam.exam_type == "class_test")
    else:
        statement = statement.where(
            or_(Exam.exam_type != "class_test", Exam.exam_type.is_(None))
        )
    rows = list(session.exec(statement).all())
    rows.sort(
        key=lambda row: (
            row[0].exam_date or date.max,
            row[1].name,
            row[2].name,
            str(row[0].id),
        )
    )
    return rows


def _marks(session: Session, paper_ids: list[UUID]) -> dict[tuple[UUID, UUID], Mark]:
    if not paper_ids:
        return {}
    return {
        (mark.exam_paper_id, mark.student_id): mark
        for mark in session.exec(
            select(Mark).where(Mark.exam_paper_id.in_(paper_ids))
        ).all()
    }


def _build(
    session: Session,
    *,
    kind: str,
    view: str,
    papers: list[tuple[ExamPaper, Exam, ClassroomSubject]],
    students: list[tuple[Student, UUID | None]],
    labels: dict[UUID, str],
    with_stats: bool,
    classroom_id: UUID | None = None,
) -> ResultOverviewRead:
    """Assemble the overview from the papers and the children (no access decisions here)."""
    published = [row for row in papers if row[0].published_at is not None]
    unpublished = len(papers) - len(published)
    marks = _marks(session, [paper.id for paper, _, _ in published])
    school_ladder = setup.school_ladder(session)
    ladders = {paper.id: marks_text.ladder_of(session, paper) for paper, _, _ in published}
    mode = setup.school_display_mode(session)

    by_room: dict[UUID, list[tuple[ExamPaper, Exam, ClassroomSubject]]] = defaultdict(list)
    for row in papers:
        by_room[row[2].classroom_id].append(row)

    # --- the columns (one per test), with the class view when staff asked
    tests: list[OverviewTestRead] = []
    for paper, exam, course in papers:
        stats = None
        is_out = paper.published_at is not None
        if with_stats and is_out:
            figures = [
                marks_text.figures(paper, marks.get((paper.id, student.id)), ladders[paper.id])
                for student, room in students
                if room == course.classroom_id and (paper.id, student.id) in marks
            ]
            stats = stats_of(Decimal(str(paper.max_marks)), figures)
        if not is_out and view == "family":
            continue  # a family never hears of a test that is not out
        tests.append(
            OverviewTestRead(
                paper_id=paper.id,
                exam_id=exam.id,
                exam_name=exam.name,
                exam_type=exam.exam_type,
                subject=course.name,
                section=labels.get(course.classroom_id, ""),
                exam_date=paper.exam_date,
                total_marks=paper.max_marks,
                pass_mode=paper.pass_mode,
                pass_percent=paper.pass_percent,
                passing_marks=paper.passing_marks,
                passing_grade=paper.passing_grade,
                published=is_out,
                stats=stats,
            )
        )

    # --- one block per child
    rows: list[OverviewStudentRead] = []
    for student, room in sorted(
        students, key=lambda item: (item[0].admission_number or "", _name_of(item[0]))
    ):
        entries: list[OverviewEntryRead] = []
        scores: list[Score] = []
        for paper, _, course in by_room.get(room, []) if room else []:
            if paper.published_at is None:
                continue
            mark = marks.get((paper.id, student.id))
            found = marks_text.figures(paper, mark, ladders[paper.id])
            entries.append(
                OverviewEntryRead(
                    paper_id=paper.id,
                    obtained=found.obtained,
                    absent=found.absent,
                    percentage=found.percentage,
                    grade=found.grade,
                    passed=found.passed,
                )
            )
            scores.append(
                Score(
                    subject=course.name,
                    total=Decimal(str(paper.max_marks)),
                    obtained=found.obtained,
                    absent=found.absent,
                    passed=found.passed,
                )
            )
        subjects, overall = fold(scores, school_ladder)
        rows.append(
            OverviewStudentRead(
                student_id=student.id,
                name=_name_of(student),
                admission_number=student.admission_number,
                classroom_id=room,
                section=labels.get(room, "") if room else "",
                entries=entries,
                subjects=subjects,
                overall=overall,
            )
        )

    return ResultOverviewRead(
        kind=kind,
        academic_year_id=current_academic_year_id(session),
        view=view,
        classroom_id=classroom_id,
        section=labels.get(classroom_id, "") if classroom_id else "",
        tests=tests,
        students=rows,
        unpublished=unpublished if view == "section" else 0,
        display_mode=mode,
    )


# ------------------------------------------------------------------- access


def _may_see_section(session: Session, user, classroom_id: UUID) -> bool:
    """Leadership, or a teacher who holds a subject in it or is its class teacher."""
    if _is_leadership(session, user):
        return True
    if classroom_id in people.class_teacher_room_ids(session, user):
        return True
    held = _held_course_ids(session, user)
    if not held:
        return False
    return (
        session.exec(
            select(ClassroomSubject.id).where(
                ClassroomSubject.id.in_(held),
                ClassroomSubject.classroom_id == classroom_id,
            )
        ).first()
        is not None
    )


def _children_with_rooms(
    session: Session, child_ids: set[UUID]
) -> list[tuple[Student, UUID | None]]:
    """Each child with the section they sit in this year."""
    if not child_ids:
        return []
    roll = year_scope.placed(session)
    placed = {
        student_id: room
        for student_id, room in session.exec(
            select(roll.c.student_id, roll.c.classroom_id).where(
                roll.c.student_id.in_(child_ids)
            )
        ).all()
    }
    children = session.exec(select(Student).where(Student.id.in_(child_ids))).all()
    return [(child, placed.get(child.id)) for child in children]


def result_overview(
    session: Session, user, kind: str, classroom_id: UUID | None
) -> ResultOverviewRead:
    """The overview for this caller (see the module docstring for who sees what)."""
    if kind not in KINDS:
        raise HTTPException(
            status_code=422, detail=f"Kind must be one of: {', '.join(KINDS)}."
        )

    if classroom_id is not None:
        room = _room_or_404(session, classroom_id)
        if not _may_see_section(session, user, room.id):
            # Not their section: a family asking for it sees nothing of it either.
            raise HTTPException(status_code=404, detail="Class-section not found")
        roster = _students_of(session, classroom_id=room.id)
        labels = labels_by_section(session, [room.id])
        return _build(
            session,
            kind=kind,
            view="section",
            papers=_papers(session, kind, {room.id}),
            students=[(student, room.id) for student in roster],
            labels=labels,
            with_stats=True,
            classroom_id=room.id,
        )

    children = _children_with_rooms(session, _family_children(session, user))
    if not children:
        raise HTTPException(
            status_code=422,
            detail="Choose a class-section to see its results.",
        )
    rooms = {room for _, room in children if room is not None}
    return _build(
        session,
        kind=kind,
        view="family",
        papers=_papers(session, kind, rooms) if rooms else [],
        students=children,
        labels=labels_by_section(session, list(rooms)) if rooms else {},
        with_stats=False,
    )
