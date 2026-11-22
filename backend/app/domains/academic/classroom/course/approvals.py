"""The principal's side of a weekly plan: queue, approve, reject, approve many.

Approval is a **state transition on one version**, not a text edit:

* the reviewer sends the `expected_version` they saw; a stale review is a `409`;
* approving stamps the current `lessonplanhistory` snapshot's `approved_at`/`approved_by`
  and points `lessonplan.approved_version` at that version;
* rejecting stores the mandatory reason on the plan and on the snapshot;
* repeating the same decision with the same version is idempotent (`200`).

The teacher is told once per version (`dedupe_key`), and a notification failure can never
undo the decision - `notify` writes in its own savepoint.
"""

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func
from sqlmodel import Session, select

from app.domains.academic.classroom.academics.models import (
    ClassName,
    Classroom,
    Section,
)
from app.domains.academic.classroom.course.models import (
    PLAN_APPROVED,
    PLAN_REJECTED,
    PLAN_SUBMITTED,
    ClassroomSubject,
    LessonPlan,
    LessonPlanHistory,
)
from app.domains.auth.models import utcnow
from app.domains.main.notifications import events
from app.domains.main.notifications.events import notify
from app.domains.people.staff.models import Employee
from app.domains.people.teachers.profile.repository import employee_names

from . import scope
from .schemas import (
    ApproveManyIn,
    BulkReviewItem,
    BulkReviewResult,
    RejectIn,
    ReviewDecisionRead,
    ReviewRow,
)


def _require_approve(session: Session, user) -> None:
    if not scope.can_approve_course(session, user):
        raise HTTPException(
            status_code=403,
            detail="Only the principal's office can review lesson plans.",
        )


def _plan_or_404(session: Session, plan_id: UUID) -> LessonPlan:
    plan = session.exec(select(LessonPlan).where(LessonPlan.id == plan_id)).first()
    if plan is None:
        raise HTTPException(status_code=404, detail="Lesson plan not found")
    return plan


def _current_history(session: Session, plan: LessonPlan) -> LessonPlanHistory:
    history = session.exec(
        select(LessonPlanHistory).where(
            LessonPlanHistory.lesson_plan_id == plan.id,
            LessonPlanHistory.version == plan.version,
        )
    ).first()
    if history is None:
        raise HTTPException(
            status_code=409,
            detail="This plan's history is missing; submit it again from the Course tab.",
        )
    return history


def _context(
    session: Session, plan: LessonPlan
) -> tuple[ClassroomSubject | None, str, str]:
    """(section row, "Class 9-A", "Mathematics") for a message or a queue row."""
    course = session.exec(
        select(ClassroomSubject).where(ClassroomSubject.id == plan.classroom_subject_id)
    ).first()
    room = session.get(Classroom, course.classroom_id) if course is not None else None
    classroom = session.get(ClassName, room.class_id) if room is not None else None
    section = session.get(Section, room.section_id) if room is not None else None

    label = (
        f"{classroom.classname}-{section.section_name}"
        if classroom is not None and section is not None
        else ""
    )
    return course, label, course.name if course is not None else "Subject"


def _review_row(
    session: Session,
    plan: LessonPlan,
    names: dict[UUID, str],
) -> ReviewRow:
    course, label, subject = _context(session, plan)
    return ReviewRow(
        plan_id=plan.id,
        classroom_subject_id=plan.classroom_subject_id,
        section_id=course.classroom_id if course is not None else plan.id,
        label=label,
        subject=subject,
        week_no=plan.week_no,
        year=plan.year,
        month=plan.month,
        start_date=plan.start_date,
        end_date=plan.end_date,
        status=plan.status,
        version=plan.version,
        expected_version=plan.version,
        submitted_at=plan.submitted_at,
        submitted_by=(
            names.get(plan.submitted_by_employee_id)
            if plan.submitted_by_employee_id is not None
            else None
        ),
        topics=plan.topics,
        learning_objectives=plan.learning_objectives,
        activities=plan.activities,
        homework=plan.homework,
        resources=plan.resources,
        assessment=plan.assessment,
        rejection_reason=plan.rejection_reason,
    )


def _queue_statement(section_id: UUID | None, status: str):
    statement = select(LessonPlan).where(LessonPlan.status == status)
    if section_id is not None:
        statement = statement.where(
            LessonPlan.classroom_subject_id.in_(
                select(ClassroomSubject.id).where(
                    ClassroomSubject.classroom_id == section_id
                )
            )
        )
    return statement


def review_queue(
    session: Session,
    user,
    *,
    section_id: UUID | None = None,
    status: str = PLAN_SUBMITTED,
    skip: int = 0,
    limit: int = 50,
) -> list[ReviewRow]:
    """Submitted weeks, oldest submission first - the reviewer's working list."""
    _require_approve(session, user)
    plans = list(
        session.exec(
            _queue_statement(section_id, status)
            .order_by(LessonPlan.submitted_at)
            .offset(max(0, skip))
            .limit(max(1, min(limit, 200)))
        ).all()
    )
    names = employee_names(
        session,
        [
            plan.submitted_by_employee_id
            for plan in plans
            if plan.submitted_by_employee_id is not None
        ],
    )
    return [_review_row(session, plan, names) for plan in plans]


def count_review_queue(
    session: Session,
    user,
    *,
    section_id: UUID | None = None,
    status: str = PLAN_SUBMITTED,
) -> int:
    """How many rows the queue has - the `X-Total-Count` badge."""
    _require_approve(session, user)
    queue = _queue_statement(section_id, status).subquery()
    return int(session.exec(select(func.count()).select_from(queue)).one())


def week_counts(
    session: Session, classroom_subject_ids: list[UUID], year: int, month: int
) -> dict[UUID, dict[str, int]]:
    """{section subject: {Submitted, Approved, Rejected}} in one grouped read."""
    if not classroom_subject_ids:
        return {}
    rows = session.exec(
        select(
            LessonPlan.classroom_subject_id,
            LessonPlan.status,
            func.count(LessonPlan.id),
        )
        .where(
            LessonPlan.classroom_subject_id.in_(classroom_subject_ids),
            LessonPlan.year == year,
            LessonPlan.month == month,
        )
        .group_by(LessonPlan.classroom_subject_id, LessonPlan.status)
    ).all()
    result: dict[UUID, dict[str, int]] = {}
    for course_id, status, count in rows:
        result.setdefault(course_id, {})[status] = int(count)
    return result


def _apply_approve(
    session: Session, plan: LessonPlan, expected_version: int, user
) -> bool:
    if (
        plan.status == PLAN_APPROVED
        and plan.version == expected_version
        and plan.approved_version == plan.version
    ):
        return False
    if plan.version != expected_version:
        raise HTTPException(
            status_code=409,
            detail="This plan changed since you opened it. Re-open the queue.",
        )
    if plan.status != PLAN_SUBMITTED:
        raise HTTPException(
            status_code=409,
            detail="Only a submitted week can be approved.",
        )

    history = _current_history(session, plan)
    now = utcnow()
    plan.status = PLAN_APPROVED
    plan.approved_version = plan.version
    plan.reviewed_by_user_id = getattr(user, "id", None)
    plan.reviewed_at = now
    plan.rejection_reason = None
    plan.updated_at = now
    history.approved_at = now
    history.approved_by_user_id = getattr(user, "id", None)
    history.rejected_at = None
    history.rejected_by_user_id = None
    history.rejection_reason = None
    session.add(plan)
    session.add(history)
    return True


def _decision(plan: LessonPlan) -> ReviewDecisionRead:
    return ReviewDecisionRead(
        plan_id=plan.id,
        status=plan.status,
        version=plan.version,
        approved_version=plan.approved_version,
        rejection_reason=plan.rejection_reason,
        reviewed_at=plan.reviewed_at,
    )


def _teacher_user_id(session: Session, plan: LessonPlan) -> UUID | None:
    """The person who submitted the week - the teacher the decision is about."""
    if plan.submitted_by_employee_id is None:
        return None
    employee = session.exec(
        select(Employee).where(Employee.id == plan.submitted_by_employee_id)
    ).first()
    return employee.user_id if employee is not None else None


def _notify_decision(session: Session, plan: LessonPlan, *, approved: bool) -> None:
    user_id = _teacher_user_id(session, plan)
    if user_id is None:
        return
    _course, label, subject = _context(session, plan)
    event = (
        events.EVENT_COURSE_WEEK_APPROVED
        if approved
        else events.EVENT_COURSE_WEEK_REJECTED
    )
    title = "Lesson plan approved" if approved else "Lesson plan rejected"
    body = f"{subject} · {label} · Week {plan.week_no} ({plan.month}/{plan.year})"
    if not approved and plan.rejection_reason:
        body = f"{body}: {plan.rejection_reason}"
    notify(
        session,
        event=event,
        recipients=[user_id],
        title=title,
        body=body,
        entity_type="lesson_plan",
        entity_id=plan.id,
        dedupe_key=(
            f"course:plan:{plan.id}:v{plan.version}:"
            f"{'approved' if approved else 'rejected'}"
        ),
    )


def approve(
    session: Session,
    plan_id: UUID,
    expected_version: int,
    user,
) -> ReviewDecisionRead:
    """Approve the version the reviewer saw; repeating it is a safe `200`."""
    _require_approve(session, user)
    plan = _plan_or_404(session, plan_id)
    changed = _apply_approve(session, plan, expected_version, user)
    if changed:
        session.commit()
        session.refresh(plan)
        _notify_decision(session, plan, approved=True)
    return _decision(plan)


def reject(
    session: Session, plan_id: UUID, payload: RejectIn, user
) -> ReviewDecisionRead:
    """Reject a submitted week; the reason is mandatory and goes to the teacher."""
    _require_approve(session, user)
    plan = _plan_or_404(session, plan_id)

    if plan.status == PLAN_REJECTED and plan.version == payload.expected_version:
        return _decision(plan)
    if plan.version != payload.expected_version:
        raise HTTPException(
            status_code=409,
            detail="This plan changed since you opened it. Re-open the queue.",
        )
    if plan.status != PLAN_SUBMITTED:
        raise HTTPException(
            status_code=409,
            detail="Only a submitted week can be rejected.",
        )

    history = _current_history(session, plan)
    now = utcnow()
    plan.status = PLAN_REJECTED
    plan.rejection_reason = payload.reason
    plan.reviewed_by_user_id = getattr(user, "id", None)
    plan.reviewed_at = now
    plan.updated_at = now
    history.rejected_at = now
    history.rejected_by_user_id = getattr(user, "id", None)
    history.rejection_reason = payload.reason
    history.approved_at = None
    history.approved_by_user_id = None
    session.add(plan)
    session.add(history)
    session.commit()
    session.refresh(plan)
    _notify_decision(session, plan, approved=False)
    return _decision(plan)


def approve_many(session: Session, payload: ApproveManyIn, user) -> BulkReviewResult:
    """Approve the rows that are still at the reviewed version; skip the rest.

    One transaction: the principal ticking ten rows either saves the eight that are
    still valid or reports why the other two were skipped - a stale row does not stop
    the batch.
    """
    _require_approve(session, user)
    approved: list[UUID] = []
    skipped: list[BulkReviewItem] = []
    changed_plans: list[LessonPlan] = []

    for item in payload.items:
        plan = session.exec(
            select(LessonPlan).where(LessonPlan.id == item.plan_id)
        ).first()
        if plan is None:
            skipped.append(
                BulkReviewItem(
                    plan_id=item.plan_id,
                    status="skipped",
                    detail="Lesson plan not found.",
                )
            )
            continue
        try:
            changed = _apply_approve(session, plan, item.expected_version, user)
        except HTTPException as refused:
            skipped.append(
                BulkReviewItem(
                    plan_id=item.plan_id,
                    status="skipped",
                    detail=str(refused.detail),
                )
            )
            continue
        approved.append(plan.id)
        if changed:
            changed_plans.append(plan)

    if changed_plans:
        session.commit()
        for plan in changed_plans:
            session.refresh(plan)
            _notify_decision(session, plan, approved=True)

    return BulkReviewResult(approved=approved, skipped=skipped)
