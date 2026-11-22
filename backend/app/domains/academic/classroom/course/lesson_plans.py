"""The weekly lesson plan: one official six-field form per week, submitted for review.

A week has **no draft**. The teacher writes the six fields and submits; that writes the
working row and one immutable `lessonplanhistory` snapshot in the same transaction. A
later submit is a new version, never a rewrite of the old one.

The month is cut into Week 1-4, plus Week 5 only when the month has a 29th (D5). The
week's range is stored on the plan, so a later calendar edit cannot silently move an
already-submitted week; the teaching days are read from the school calendar for display.

Approval is Phase 7. A week that is already approved is read-only here: a change needs
`intent="change"`, which submits a new version while `approved_version` still points at
the version the principal signed.
"""

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.domains.academic.classroom.academics.repository import room_label
from app.domains.academic.classroom.course.models import (
    PLAN_APPROVED,
    PLAN_FORMAT_VERSION,
    PLAN_SUBMITTED,
    ClassroomSubject,
    LessonPlan,
    LessonPlanHistory,
)
from app.domains.admin.settings.models import AcademicYear
from app.domains.auth.models import utcnow
from app.domains.main.notifications import events
from app.domains.main.notifications.events import notify
from app.domains.people.teachers.profile.repository import employee_names

from . import scope, teaching_days
from .schemas import (
    LessonPlanContentRead,
    LessonPlanSubmitIn,
    LessonPlanWeekRead,
)
from .service import _course_row_or_404, _employee_of

_MAX_FIELD = 2000
_CONTENT_FIELDS = (
    "topics",
    "learning_objectives",
    "activities",
    "homework",
    "resources",
    "assessment",
)


def _require_month_in_year(
    session: Session, row: ClassroomSubject, year: int, month: int
) -> None:
    """A plan belongs to the subject's own academic year - April to March, say.

    The month is checked against that year's dates, not against the calendar year, so
    January-March of the *next* calendar year is valid for a 2026-27 subject and
    April 2027 is not. There is no fallback to "this month": an out-of-year request is
    a `422` that names the year.
    """
    academic_year = session.get(AcademicYear, row.academic_year_id)
    if academic_year is None:
        raise HTTPException(
            status_code=409, detail="This subject's academic year no longer exists."
        )
    wanted = year * 12 + month
    first = academic_year.start_date.year * 12 + academic_year.start_date.month
    last = academic_year.end_date.year * 12 + academic_year.end_date.month
    if not first <= wanted <= last:
        raise HTTPException(
            status_code=422,
            detail=(
                f"That month is outside the academic year {academic_year.name}."
            ),
        )


def _visible(session: Session, user, classroom_subject_id: UUID) -> None:
    """A caller may read only a subject they hold now, or the office may read any."""
    row = _course_row_or_404(session, classroom_subject_id)
    visible = scope.visible_course_subject_ids(session, user, row.classroom_id)
    if visible is not None and row.id not in visible:
        raise HTTPException(
            status_code=403,
            detail="You can read only the lesson plans of the subject you teach.",
        )


def _may_edit(session: Session, user, classroom_subject_id: UUID) -> bool:
    if not scope.can_plan_course(session, user):
        return False
    return scope.may_edit_plan(session, user, classroom_subject_id)


def _approved_content(
    history: LessonPlanHistory | None,
) -> LessonPlanContentRead | None:
    if history is None:
        return None
    return LessonPlanContentRead(
        topics=history.topics,
        learning_objectives=history.learning_objectives,
        activities=history.activities,
        homework=history.homework,
        resources=history.resources,
        assessment=history.assessment,
    )


def _week_read(
    week: teaching_days.WeekRange,
    plan: LessonPlan | None,
    histories: dict[tuple[UUID, int], LessonPlanHistory],
    *,
    may_edit: bool,
    submitted_by: str | None,
) -> LessonPlanWeekRead:
    """One week: the calendar slot plus the latest plan (or the honest empty)."""
    approved = None
    if plan is not None and plan.approved_version is not None:
        approved = _approved_content(histories.get((plan.id, plan.approved_version)))

    locked = plan is not None and plan.status == PLAN_APPROVED

    return LessonPlanWeekRead(
        plan_id=plan.id if plan is not None else None,
        week_no=week.week_no,
        start_date=week.start_date,
        end_date=week.end_date,
        teaching_days=list(week.teaching_days),
        status=plan.status if plan is not None else None,
        version=plan.version if plan is not None else 0,
        approved_version=plan.approved_version if plan is not None else None,
        expected_version=plan.version if plan is not None else 0,
        topics=plan.topics if plan is not None else "",
        learning_objectives=plan.learning_objectives if plan is not None else "",
        activities=plan.activities if plan is not None else "",
        homework=plan.homework if plan is not None else "",
        resources=plan.resources if plan is not None else "",
        assessment=plan.assessment if plan is not None else "",
        approved=approved,
        rejection_reason=plan.rejection_reason if plan is not None else None,
        submitted_at=plan.submitted_at if plan is not None else None,
        submitted_by=submitted_by,
        can_edit=bool(may_edit and not locked),
        can_request_change=bool(may_edit and locked),
    )


def month_plan(
    session: Session,
    classroom_subject_id: UUID,
    year: int,
    month: int,
    user=None,
) -> list[LessonPlanWeekRead]:
    """The month's Week 1-5 tabs, with the latest plan and the approved snapshot."""
    _visible(session, user, classroom_subject_id)
    row = _course_row_or_404(session, classroom_subject_id)
    _require_month_in_year(session, row, year, month)

    try:
        weeks = teaching_days.week_ranges(session, year, month)
    except ValueError as cause:
        raise HTTPException(status_code=422, detail=str(cause)) from cause

    plans = {
        plan.week_no: plan
        for plan in session.exec(
            select(LessonPlan).where(
                LessonPlan.classroom_subject_id == row.id,
                LessonPlan.academic_year_id == row.academic_year_id,
                LessonPlan.year == year,
                LessonPlan.month == month,
            )
        ).all()
    }

    histories: dict[tuple[UUID, int], LessonPlanHistory] = {}
    if plans:
        for history in session.exec(
            select(LessonPlanHistory).where(
                LessonPlanHistory.lesson_plan_id.in_(
                    [plan.id for plan in plans.values()]
                )
            )
        ).all():
            histories[(history.lesson_plan_id, history.version)] = history

    names = employee_names(
        session,
        [
            plan.submitted_by_employee_id
            for plan in plans.values()
            if plan.submitted_by_employee_id is not None
        ],
    )
    may_edit = _may_edit(session, user, classroom_subject_id)

    result: list[LessonPlanWeekRead] = []
    for week in weeks:
        plan = plans.get(week.week_no)
        submitted_by = (
            names.get(plan.submitted_by_employee_id)
            if plan is not None and plan.submitted_by_employee_id is not None
            else None
        )
        result.append(
            _week_read(
                week,
                plan,
                histories,
                may_edit=may_edit,
                submitted_by=submitted_by,
            )
        )
    return result


def _clean_content(payload: LessonPlanSubmitIn) -> dict[str, str]:
    """Preserve the prose, trim only the edges, and enforce the one required pair."""
    content: dict[str, str] = {}
    for field in _CONTENT_FIELDS:
        value = (getattr(payload, field) or "").strip()
        if len(value) > _MAX_FIELD:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"{field.replace('_', ' ').title()} must be at most "
                    f"{_MAX_FIELD} characters."
                ),
            )
        content[field] = value

    if not content["topics"]:
        raise HTTPException(status_code=422, detail="Topics is required.")
    if not content["learning_objectives"]:
        raise HTTPException(status_code=422, detail="Learning objectives is required.")
    return content


def _notify_submitted(
    session: Session,
    plan: LessonPlan,
    week: teaching_days.WeekRange,
    course_row: ClassroomSubject,
) -> None:
    """Tell the approvers once per submitted version; never undo the submit."""
    recipients = events.course_approver_user_ids(session)
    if not recipients:
        return
    subject_name = course_row.name
    notify(
        session,
        event=events.EVENT_COURSE_WEEK_SUBMITTED,
        recipients=recipients,
        title="Lesson plan submitted",
        body=(
            f"{subject_name} · {room_label(session, course_row.classroom_id)} · "
            f"Week {week.week_no} ({week.start_date} to {week.end_date})"
        ),
        entity_type="lesson_plan",
        entity_id=plan.id,
        dedupe_key=f"course:plan:{plan.id}:v{plan.version}:submitted",
    )


def submit_week(
    session: Session,
    classroom_subject_id: UUID,
    year: int,
    month: int,
    week_no: int,
    payload: LessonPlanSubmitIn,
    user=None,
) -> LessonPlanWeekRead:
    """Submit one week: the only write path, and it always writes a snapshot."""
    if not _may_edit(session, user, classroom_subject_id):
        raise HTTPException(
            status_code=403,
            detail=(
                "Only the subject's current teacher, or the office, "
                "can submit this week."
            ),
        )

    row = _course_row_or_404(session, classroom_subject_id)
    _require_month_in_year(session, row, year, month)
    try:
        weeks = teaching_days.week_ranges(session, year, month)
    except ValueError as cause:
        raise HTTPException(status_code=422, detail=str(cause)) from cause

    week = next((item for item in weeks if item.week_no == week_no), None)
    if week is None:
        raise HTTPException(
            status_code=422,
            detail="That week does not exist in this month.",
        )

    content = _clean_content(payload)
    plan = session.exec(
        select(LessonPlan).where(
            LessonPlan.classroom_subject_id == row.id,
            LessonPlan.academic_year_id == row.academic_year_id,
            LessonPlan.year == year,
            LessonPlan.month == month,
            LessonPlan.week_no == week_no,
        )
    ).first()

    expected = plan.version if plan is not None else 0
    if payload.expected_version != expected:
        raise HTTPException(
            status_code=409,
            detail="This week changed in another tab. Re-open it and submit again.",
        )

    if plan is not None and plan.status == PLAN_APPROVED and payload.intent != "change":
        raise HTTPException(
            status_code=409,
            detail=(
                "This week is approved. Request a change before submitting "
                "a new version."
            ),
        )

    version = (plan.version if plan is not None else 0) + 1
    submitted_at = utcnow()
    employee_id = _employee_of(session, user)

    if plan is None:
        plan = LessonPlan(
            classroom_subject_id=row.id,
            academic_year_id=row.academic_year_id,
            year=year,
            month=month,
            week_no=week_no,
            start_date=week.start_date,
            end_date=week.end_date,
            version=1,
            status=PLAN_SUBMITTED,
        )
    else:
        plan.start_date = week.start_date
        plan.end_date = week.end_date

    for field, value in content.items():
        setattr(plan, field, value)
    plan.version = version
    plan.status = PLAN_SUBMITTED
    plan.format_version = PLAN_FORMAT_VERSION
    plan.submitted_by_employee_id = employee_id
    plan.submitted_at = submitted_at
    # A new version is unreviewed; the approved version (if any) deliberately stays.
    plan.reviewed_by_user_id = None
    plan.reviewed_at = None
    plan.rejection_reason = None
    plan.updated_at = submitted_at
    session.add(plan)
    session.flush()

    session.add(
        LessonPlanHistory(
            lesson_plan_id=plan.id,
            version=version,
            start_date=week.start_date,
            end_date=week.end_date,
            format_version=PLAN_FORMAT_VERSION,
            submitted_by_employee_id=employee_id,
            submitted_at=submitted_at,
            **content,
        )
    )
    try:
        session.commit()
    except IntegrityError as cause:
        # Two tabs submitted the same week at once: the unique key caught it. That is a
        # conflict for the loser, not a server error.
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail="This week was submitted in another tab. Re-open it and try again.",
        ) from cause
    session.refresh(plan)
    _notify_submitted(session, plan, week, row)

    histories = {
        (history.lesson_plan_id, history.version): history
        for history in session.exec(
            select(LessonPlanHistory).where(LessonPlanHistory.lesson_plan_id == plan.id)
        ).all()
    }
    name = (
        employee_names(session, [employee_id]).get(employee_id)
        if employee_id is not None
        else None
    )
    # Phase 9 hook: notify the approvers here, in this transaction.
    return _week_read(
        week,
        plan,
        histories,
        may_edit=True,
        submitted_by=name,
    )
