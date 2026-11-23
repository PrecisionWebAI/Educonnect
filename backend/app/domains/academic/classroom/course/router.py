"""The Course tab's two endpoints, mounted on the paths the plan names.

* `GET /classroom/sections/{id}/course` - the whole tab (plan + teachers + progress).
* `PATCH /course/chapters/{chapter_id}/progress` - tick one chapter for one section.

Two routers because the two paths live under different prefixes; both are this one
module's, so the rules (`service.py`) and the shapes (`schemas.py`) stay in one place.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission

from . import approvals, lesson_plans, service, teacher_course
from .schemas import (
    AddSectionSubjectIn,
    ApproveIn,
    ApproveManyIn,
    BulkReviewResult,
    ChapterCreate,
    ChapterRowRead,
    ChapterTickIn,
    ChapterUpdate,
    ClassroomSubjectUpdate,
    CourseSubjectRowRead,
    CourseSummaryRead,
    CourseTeacherAssignIn,
    CourseTeacherRead,
    CourseTeacherRow,
    LessonPlanSubmitIn,
    LessonPlanWeekRead,
    PlanRejectIn,
    ProgressSaveIn,
    RejectIn,
    ReviewCountRead,
    ReviewDecisionRead,
    ReviewRow,
    SectionCourseRead,
    TeacherAssignResult,
    TeacherCourseDetail,
)

#: Mounted at `/classroom` (the section's course).
classroom_router = APIRouter()

#: Mounted at `/course` (a chapter's progress).
router = APIRouter()


@classroom_router.get("/sections/{section_id}/course", response_model=SectionCourseRead)
def read_section_course(
    section_id: UUID,
    include_archived: bool = False,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("course.read")),
):
    """The Course tab for one class-section.

    Per subject: the section's row (active, or archived when asked), who teaches it now,
    everyone who has taught it (with what each of them finished), the chapter list with
    its status and dates, the percentage, the next chapter, and what the caller may do.

    A teacher receives only the subjects they hold now; the office receives every row.
    """
    return service.section_course(
        session=session,
        section_id=section_id,
        user=current_user,
        include_archived=include_archived,
    )


@classroom_router.post(
    "/sections/{section_id}/subjects",
    response_model=CourseSubjectRowRead,
    status_code=201,
)
def add_section_subject(
    section_id: UUID,
    payload: AddSectionSubjectIn,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("course.manage")),
):
    """Add a subject to this section, from the master list or as a custom name."""
    return service.add_subject(
        session=session, section_id=section_id, payload=payload, user=current_user
    )


@router.put(
    "/subjects/{classroom_subject_id}/teacher", response_model=TeacherAssignResult
)
def assign_subject_teacher(
    classroom_subject_id: UUID,
    payload: CourseTeacherAssignIn,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("course.assign_teacher")),
):
    """Assign/change the teacher of one section subject.

    The open assignment is closed the day before the effective date and a new row opens:
    the timeline is the history, and the old teacher keeps the chapters they finished.
    """
    return service.assign_teacher(
        session=session,
        classroom_subject_id=classroom_subject_id,
        payload=payload,
        user=current_user,
    )


@router.get(
    "/subjects/{classroom_subject_id}/teachers",
    response_model=list[CourseTeacherRead],
)
def read_subject_teacher_history(
    classroom_subject_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("course.read")),
):
    """Everyone who held this section subject, with the chapters each one finished."""
    return service.teacher_history(
        session=session, classroom_subject_id=classroom_subject_id
    )


@router.get(
    "/subjects/{classroom_subject_id}/chapters",
    response_model=list[ChapterRowRead],
)
def read_subject_chapters(
    classroom_subject_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("course.read")),
):
    """The class's chapter plan, with this section's progress and this month's evidence."""
    return service.list_chapters(
        session, classroom_subject_id=classroom_subject_id, user=current_user
    )


@router.post(
    "/subjects/{classroom_subject_id}/chapters",
    response_model=ChapterRowRead,
    status_code=201,
)
def create_subject_chapter(
    classroom_subject_id: UUID,
    payload: ChapterCreate,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("classes.read")),
):
    """Add a chapter to the class plan; every section of that class sees it."""
    return service.add_chapter(
        session,
        classroom_subject_id=classroom_subject_id,
        payload=payload,
        user=current_user,
    )


@router.patch("/chapters/{chapter_id}", response_model=ChapterRowRead)
def edit_chapter(
    chapter_id: UUID,
    payload: ChapterUpdate,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("classes.read")),
):
    """Rename, re-date or move one chapter (the list is renumbered on a move)."""
    return service.update_chapter(
        session, chapter_id=chapter_id, payload=payload, user=current_user
    )


@router.delete("/chapters/{chapter_id}", status_code=204)
def remove_chapter(
    chapter_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("classes.read")),
):
    """Delete an unstarted, unused chapter; completed history and exam papers block it."""
    service.delete_chapter(session, chapter_id=chapter_id, user=current_user)


@router.get(
    "/subjects/{classroom_subject_id}/lesson-plans",
    response_model=list[LessonPlanWeekRead],
)
def read_month_lesson_plan(
    classroom_subject_id: UUID,
    year: int,
    month: int,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("course.read")),
):
    """Week 1-5 of a month: ranges, teaching days, status and the six fields."""
    return lesson_plans.month_plan(
        session,
        classroom_subject_id=classroom_subject_id,
        year=year,
        month=month,
        user=current_user,
    )


@router.put(
    "/subjects/{classroom_subject_id}/lesson-plans/{year}/{month}/{week_no}",
    response_model=LessonPlanWeekRead,
)
def submit_lesson_plan_week(
    classroom_subject_id: UUID,
    year: int,
    month: int,
    week_no: int,
    payload: LessonPlanSubmitIn,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("course.read")),
):
    """Submit (or resubmit/request a change of) one week.

    The service checks that the caller holds the subject **now**, that the week is real,
    that `expectedVersion` still matches, and that an approved week is only changed with
    `intent="change"`. The route's `course.read` is the door; the service is the rule.
    """
    return lesson_plans.submit_week(
        session,
        classroom_subject_id=classroom_subject_id,
        year=year,
        month=month,
        week_no=week_no,
        payload=payload,
        user=current_user,
    )


@router.get("/summary", response_model=CourseSummaryRead)
def read_course_summary(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("course.read")),
):
    """Subjects, submitted weeks and D7 completion for the caller's scope."""
    return teacher_course.summary(session, current_user)


@router.get("/sections/{section_id}/summary", response_model=CourseSummaryRead)
def read_section_course_summary(
    section_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("course.read")),
):
    """The same three numbers for one class-section (the Classroom card)."""
    return teacher_course.section_summary(session, section_id, current_user)


@router.get("/teachers", response_model=list[CourseTeacherRow])
def read_course_teachers(
    q: str | None = None,
    skip: int = 0,
    limit: int = 50,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("course.read")),
):
    """The teaching roll with subjects, pending approvals, behind subjects and completion.

    `course.view_all` sees every teacher; a teacher sees only their own row.
    """
    return teacher_course.teacher_list(
        session, current_user, q=q, skip=skip, limit=limit
    )


@router.get("/teachers/{employee_id}", response_model=TeacherCourseDetail)
def read_teacher_course(
    employee_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("course.read")),
):
    """One teacher's subjects/sections, this month's weeks and chapter progress."""
    return teacher_course.teacher_detail(session, employee_id, current_user)


@router.get("/my", response_model=TeacherCourseDetail)
def read_my_course(
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("course.read")),
):
    """The signed-in teacher's own course - no id from the browser."""
    return teacher_course.my_course(session, current_user)


@router.get("/reviews", response_model=list[ReviewRow])
def read_review_queue(
    response: Response,
    section_id: UUID | None = None,
    skip: int = 0,
    limit: int = 50,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("course.approve")),
):
    """Submitted weeks waiting for the principal, oldest submission first.

    `X-Total-Count` carries the full count so the list can show a badge without a second
    convention. The rows include the six fields - clicking a week does not need another
    read.
    """
    rows = approvals.review_queue(
        session,
        current_user,
        section_id=section_id,
        skip=skip,
        limit=limit,
    )
    response.headers["X-Total-Count"] = str(
        approvals.count_review_queue(session, current_user, section_id=section_id)
    )
    return rows


@router.get("/reviews/count", response_model=ReviewCountRead)
def read_review_count(
    section_id: UUID | None = None,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("course.approve")),
):
    """The badge number - submitted weeks only."""
    return ReviewCountRead(
        count=approvals.count_review_queue(session, current_user, section_id=section_id)
    )


@router.post("/lesson-plans/approve-many", response_model=BulkReviewResult)
def approve_many_lesson_plans(
    payload: ApproveManyIn,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("course.approve")),
):
    """Approve the reviewed rows; stale rows come back in `skipped`, not as a 500."""
    return approvals.approve_many(session, payload, current_user)


@router.post("/lesson-plans/{plan_id}/approve", response_model=ReviewDecisionRead)
def approve_lesson_plan(
    plan_id: UUID,
    payload: ApproveIn,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("course.approve")),
):
    """Approve one week; repeating the same decision is an idempotent `200`."""
    return approvals.approve(
        session,
        plan_id=plan_id,
        expected_version=payload.expected_version,
        user=current_user,
    )


@router.post("/lesson-plans/{plan_id}/reject", response_model=ReviewDecisionRead)
def reject_lesson_plan(
    plan_id: UUID,
    payload: RejectIn,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("course.approve")),
):
    """Reject one week with a mandatory reason; the teacher is notified once."""
    return approvals.reject(
        session, plan_id=plan_id, payload=payload, user=current_user
    )


@router.patch("/chapters/{chapter_id}/progress", response_model=ChapterRowRead)
def tick_chapter_progress(
    chapter_id: UUID,
    payload: ChapterTickIn,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("course.approve")),
):
    """Move a chapter's status directly - **approvers only**.

    Teachers do not tick: they save progress (`PUT /subjects/{id}/progress`) and the
    principal's office approves it. This route is the office's direct correction.
    """
    return service.tick_chapter(
        session=session, chapter_id=chapter_id, payload=payload, user=current_user
    )


@router.patch("/subjects/{classroom_subject_id}", response_model=CourseSubjectRowRead)
def rename_section_subject(
    classroom_subject_id: UUID,
    payload: ClassroomSubjectUpdate,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("course.manage")),
):
    """Rename one classroom subject; another section's subject is untouched."""
    return service.rename_subject(
        session,
        classroom_subject_id=classroom_subject_id,
        payload=payload,
        user=current_user,
    )


@router.patch(
    "/subjects/{classroom_subject_id}/archive", response_model=CourseSubjectRowRead
)
def archive_section_subject(
    classroom_subject_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("course.manage")),
):
    """Retire a subject from a section: the row, its chapters and plans stay."""
    return service.archive_subject(
        session=session,
        classroom_subject_id=classroom_subject_id,
        user=current_user,
    )


@router.patch(
    "/subjects/{classroom_subject_id}/restore", response_model=CourseSubjectRowRead
)
def restore_section_subject(
    classroom_subject_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("course.manage")),
):
    """Bring an archived subject back to the section (the master must be active)."""
    return service.restore_subject(
        session=session,
        classroom_subject_id=classroom_subject_id,
        user=current_user,
    )


@router.delete("/subjects/{classroom_subject_id}", status_code=204)
def delete_section_subject(
    classroom_subject_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("course.manage")),
):
    """Delete an empty section subject; one with plans or completed chapters is refused
    (`409`, with the archive instruction) so the school's history is never destroyed."""
    service.delete_subject(
        session=session,
        classroom_subject_id=classroom_subject_id,
        user=current_user,
    )


@router.post(
    "/subjects/{classroom_subject_id}/chapter-plan/submit",
    response_model=CourseSubjectRowRead,
)
def submit_plan(
    classroom_subject_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("classes.read")),
):
    """The teacher sends the chapter list to the principal's office."""
    return service.submit_chapter_plan(session, classroom_subject_id, current_user)


@router.post(
    "/subjects/{classroom_subject_id}/chapter-plan/approve",
    response_model=CourseSubjectRowRead,
)
def approve_plan(
    classroom_subject_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("course.approve")),
):
    return service.approve_chapter_plan(session, classroom_subject_id, current_user)


@router.post(
    "/subjects/{classroom_subject_id}/chapter-plan/reject",
    response_model=CourseSubjectRowRead,
)
def reject_plan(
    classroom_subject_id: UUID,
    payload: PlanRejectIn,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("course.approve")),
):
    return service.reject_chapter_plan(
        session, classroom_subject_id, payload, current_user
    )


@router.put(
    "/subjects/{classroom_subject_id}/progress",
    response_model=list[ChapterRowRead],
)
def save_subject_progress(
    classroom_subject_id: UUID,
    payload: ProgressSaveIn,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("classes.read")),
):
    """Save Completed / Skipped for one or many chapters; the principal approves."""
    return service.save_progress(session, classroom_subject_id, payload, current_user)


@router.post(
    "/subjects/{classroom_subject_id}/progress/approve",
    response_model=list[ChapterRowRead],
)
def approve_subject_progress(
    classroom_subject_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("course.approve")),
):
    return service.approve_progress(session, classroom_subject_id, current_user)


@router.post(
    "/subjects/{classroom_subject_id}/progress/reject",
    response_model=list[ChapterRowRead],
)
def reject_subject_progress(
    classroom_subject_id: UUID,
    session: Session = Depends(get_session),
    current_user=Depends(RequirePermission("course.approve")),
):
    return service.reject_progress(session, classroom_subject_id, current_user)
