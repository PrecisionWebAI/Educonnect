"""Shared question papers: one `exam_paper_group` over several sections' papers.

A group links **papers**, never subjects: 9-A's "English" and 9-B's "English Literature"
may sit one paper without either subject changing its name. The group owns what is
shared - a title and a chapter list **by name** (chapter ids belong to one section each).
Everything per section (date, room, marks, the subject itself) stays on the paper.

The lock is **read live**: a group is locked as soon as any of its papers has a mark or a
publication date. `locked_at` is only a convenience stamp; trusting it alone would let a
mark entered a second ago slip past the check.
"""

from datetime import datetime
from uuid import UUID

from sqlmodel import Session, select

from app.domains.academic.classroom.exams.models import (
    ExamPaper,
    ExamPaperGroup,
    ExamPaperGroupChapter,
    Mark,
)

from .schemas import PaperGroupRead


def clean_names(names: list[str]) -> list[str]:
    """Trim, drop blanks and exact repeats (case-insensitive), keep the order."""
    seen: set[str] = set()
    cleaned: list[str] = []
    for name in names:
        value = " ".join((name or "").split())
        if value and value.lower() not in seen:
            seen.add(value.lower())
            cleaned.append(value)
    return cleaned


def set_chapters(session: Session, group: ExamPaperGroup, names: list[str]) -> None:
    """Replace the group's chapter list with `names` (numbered 1..n)."""
    for row in session.exec(
        select(ExamPaperGroupChapter).where(
            ExamPaperGroupChapter.paper_group_id == group.id
        )
    ).all():
        session.delete(row)
    session.flush()
    for number, name in enumerate(clean_names(names), start=1):
        session.add(
            ExamPaperGroupChapter(
                paper_group_id=group.id,
                sequence=number,
                name=name,
                school_id=group.school_id,
            )
        )
    session.flush()


def create_group(
    session: Session,
    *,
    exam_id: UUID,
    title: str | None,
    chapter_names: list[str],
    user,
    school_id: UUID | None,
) -> ExamPaperGroup:
    group = ExamPaperGroup(
        exam_id=exam_id,
        display_title=title,
        created_by_user_id=getattr(user, "id", None),
        school_id=school_id,
    )
    session.add(group)
    session.flush()
    set_chapters(session, group, chapter_names)
    return group


def chapter_names(session: Session, group_ids: list[UUID]) -> dict[UUID, list[str]]:
    """`{group_id: [chapter names in order]}` - one query for any number of groups."""
    names: dict[UUID, list[str]] = {}
    if not group_ids:
        return names
    for row in session.exec(
        select(ExamPaperGroupChapter)
        .where(ExamPaperGroupChapter.paper_group_id.in_(group_ids))
        .order_by(ExamPaperGroupChapter.paper_group_id, ExamPaperGroupChapter.sequence)
    ).all():
        names.setdefault(row.paper_group_id, []).append(row.name)
    return names


def locked_group_ids(session: Session, group_ids: list[UUID]) -> set[UUID]:
    """Groups where any paper is published or has a mark - two queries, any number."""
    if not group_ids:
        return set()
    locked = set(
        session.exec(
            select(ExamPaper.paper_group_id).where(
                ExamPaper.paper_group_id.in_(group_ids),
                ExamPaper.published_at.is_not(None),
            )
        ).all()
    )
    with_marks = session.exec(
        select(ExamPaper.paper_group_id)
        .join(Mark, Mark.exam_paper_id == ExamPaper.id)
        .where(ExamPaper.paper_group_id.in_(group_ids))
        .distinct()
    ).all()
    locked.update(with_marks)
    return {group_id for group_id in locked if group_id is not None}


def is_locked(session: Session, group_id: UUID) -> bool:
    return group_id in locked_group_ids(session, [group_id])


def stamp_lock(session: Session, group: ExamPaperGroup, user) -> None:
    """Record the moment a group first became locked (informational)."""
    if group.locked_at is None:
        group.locked_at = datetime.utcnow()
        group.locked_by_user_id = getattr(user, "id", None)
        session.add(group)


def read_groups(
    session: Session, exam_id: UUID, papers: list[ExamPaper]
) -> list[PaperGroupRead]:
    """The exam's groups, each with its chapter names and the papers that sit it."""
    return read_groups_many(session, [exam_id], papers).get(exam_id, [])


def read_groups_many(
    session: Session, exam_ids: list[UUID], papers: list[ExamPaper]
) -> dict[UUID, list[PaperGroupRead]]:
    """The groups of **many** exams in a fixed number of queries: `{exam: [group, ...]}`."""
    if not exam_ids:
        return {}
    groups = list(
        session.exec(
            select(ExamPaperGroup)
            .where(ExamPaperGroup.exam_id.in_(exam_ids))
            .order_by(ExamPaperGroup.created_at, ExamPaperGroup.id)
        ).all()
    )
    ids = [group.id for group in groups]
    names = chapter_names(session, ids)
    locked = locked_group_ids(session, ids)
    members: dict[UUID, list[UUID]] = {}
    for paper in papers:
        if paper.paper_group_id is not None:
            members.setdefault(paper.paper_group_id, []).append(paper.id)
    out: dict[UUID, list[PaperGroupRead]] = {}
    for group in groups:
        if not members.get(group.id):
            continue
        out.setdefault(group.exam_id, []).append(
            PaperGroupRead(
                id=group.id,
                exam_id=group.exam_id,
                display_title=group.display_title,
                chapters=names.get(group.id, []),
                paper_ids=members.get(group.id, []),
                locked=group.id in locked,
            )
        )
    return out
