"""`GET /teachers/performance` - the anonymous reviews, summarised.

Moved here in Phase 10: `teacherreview` is the *review* half of an appraisal, so the
read that summarises it belongs beside the season rather than in the directory's
service. Two things deliberately did not move:

* **the URL.** The screen has called `/teachers/performance` since Phase 1; a rename
  would break the client for no product reason, so the route spells the full path and
  is mounted with no prefix (`api.py`);
* **the right.** It stays `teachers.read`: reading ratings is reading the directory.
  `appraisals.review` is the right to *give* one, and it was never what this needed.
"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.core.db import get_session
from app.domains.admin.users.models import User
from app.domains.auth.dependencies import RequirePermission
from app.domains.people.teachers import repository as teachers_repository
from app.domains.people.teachers.models import TeacherReview
from app.domains.people.teachers.schemas import StaffPerformance

router = APIRouter()


def trend(ratings: list[int]) -> str:
    """Which way the ratings moved: the recent half against the older half.

    A teacher with one rating has no movement to report, and "flat" is the honest
    answer for that - not a made-up direction.
    """
    if len(ratings) < 2:
        return "flat"
    midpoint = len(ratings) // 2
    older = sum(ratings[:midpoint]) / midpoint
    recent = sum(ratings[midpoint:]) / (len(ratings) - midpoint)
    if recent > older:
        return "up"
    if recent < older:
        return "down"
    return "flat"


def performance(session: Session) -> list[StaffPerformance]:
    """Per-teacher summary computed from the anonymous `teacherreview` rows.

    Only teachers with at least one rating appear: an empty list is the honest
    answer before any review exists, and a fabricated 0 would read as a bad score
    rather than "not rated yet".
    """
    reviews = session.exec(
        select(TeacherReview.teacher_id, TeacherReview.rating).order_by(
            TeacherReview.teacher_id,  # type: ignore[arg-type]
            TeacherReview.created_at,  # type: ignore[arg-type]
        )
    ).all()
    if not reviews:
        return []

    ratings: dict[UUID, list[int]] = {}
    for teacher_id, rating in reviews:
        ratings.setdefault(teacher_id, []).append(rating)

    teachers = {
        teacher.id: teacher
        for teacher in teachers_repository.teaching_employees(session)
    }
    names = {
        user.id: user.full_name
        for user in session.exec(
            select(User).where(
                User.id.in_([teacher.user_id for teacher in teachers.values()])
            )
        ).all()
    }

    rows: list[StaffPerformance] = []
    for teacher_id, values in ratings.items():
        teacher = teachers.get(teacher_id)
        if teacher is None:
            # A review of somebody no longer on the roll: keep the review row, but do
            # not put them on a screen the roll defines.
            continue
        rating = round(sum(values) / len(values), 1)
        rows.append(
            StaffPerformance(
                id=teacher_id,
                staff=names.get(teacher.user_id, ""),
                rating=rating,
                reviews=len(values),
                trend=trend(values),
                score=round(rating / 5 * 100),
            )
        )
    return sorted(rows, key=lambda row: row.staff)


@router.get("/teachers/performance", response_model=list[StaffPerformance])
def read_staff_performance(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("teachers.read")),
):
    """Ratings from the anonymous reviews - viewing is a read, not a workload right."""
    return performance(session)
