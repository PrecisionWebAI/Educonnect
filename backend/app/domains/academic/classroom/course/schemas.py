from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, model_validator

from app.core.text import CanonicalRequest


class ChapterRowRead(BaseModel):
    """One chapter as the Course tab draws it: the plan plus this section's answer."""

    chapter_id: UUID
    sequence: int
    name: str
    planned_date: date | None = None
    #: Pending / In progress / Completed - the words the tab shows.
    status: str
    completed_on: date | None = None
    completed_by: str | None = None
    completed_by_employee_id: UUID | None = None
    #: The saved row, when there is one (a plan with no progress has none yet).
    #: True when the chapter was finished on or before its planned date.
    ahead: bool | None = None
    #: True when the planned date has passed and it is not finished.
    behind: bool = False
    #: May this caller tick it? (the subject teacher, or the office)
    can_tick: bool = False
    #: May this caller rename, move or delete it? (the office only)
    can_edit: bool = False
    #: Saved by the teacher, waiting for the principal: `Completed` or `Skipped`.
    proposed_status: str | None = None


class ChapterCreate(BaseModel):
    """Add one chapter to a class + subject + session.

    A chapter belongs to the **class**, so adding it once shows it in every section of
    that class; each section then has its own progress. The name keeps its capitalisation
    (it is a book title, not a canonical key).
    """

    name: str
    #: 1-based position; omitted means "append to the end".
    sequence: int | None = None
    planned_date: date | None = None

    @model_validator(mode="after")
    def _clean(self):
        self.name = " ".join((self.name or "").split())
        if not self.name:
            raise ValueError("Type the chapter's name.")
        if self.sequence is not None and self.sequence < 1:
            raise ValueError("sequence must be 1 or more.")
        return self


class ChapterUpdate(BaseModel):
    """Rename, re-date or move one chapter.

    `sequence` means **move to this position**, not "store this number": the whole list is
    renumbered in one transaction, so two chapters can never claim position 2. Sending
    `planned_date: null` clears the date; omitting it leaves it untouched.
    """

    name: str | None = None
    sequence: int | None = None
    planned_date: date | None = None

    @model_validator(mode="after")
    def _clean(self):
        if self.name is not None:
            self.name = " ".join(self.name.split())
            if not self.name:
                raise ValueError("Type the chapter's name.")
        if self.sequence is not None and self.sequence < 1:
            raise ValueError("sequence must be 1 or more.")
        return self


class CourseTeacherRead(BaseModel):
    """Who taught this subject, and how much of the plan they finished.

    The share is what makes a teacher change legible: "2 of 10" for the person who left,
    "0 of 10" for the one who took over, instead of moving the old work to the new name.
    """

    employee_id: UUID
    name: str
    effective_from: date | None = None
    effective_to: date | None = None
    #: True for the person holding the subject today.
    current: bool = False
    #: Chapters of this subject **this** person completed in this section.
    completed: int = 0


class LessonPlanSummaryRead(BaseModel):
    """The current month's weekly plans for one section subject.

    `submitted` counts every week that has a row (its latest version); `approved` and
    `pending` split those by the latest verdict, `rejected` names the ones waiting for a
    corrected resubmission. The row prints "3 submitted · 2 approved".
    """

    year: int
    month: int
    submitted: int = 0
    approved: int = 0
    pending: int = 0
    rejected: int = 0


class LessonPlanContentRead(BaseModel):
    """The six official fields, exactly as the teacher wrote them."""

    topics: str = ""
    learning_objectives: str = ""
    activities: str = ""
    homework: str = ""
    resources: str = ""
    assessment: str = ""


class LessonPlanSubmitIn(BaseModel):
    """One week's submission - no draft, and no rewriting an old version.

    `topics` and `learning_objectives` are required; the other four fields may be blank.
    `expected_version` is the version the form opened with (`0` before the first submit):
    a stale form gets `409` instead of silently overwriting somebody else's submit.
    """

    topics: str = ""
    learning_objectives: str = ""
    activities: str = ""
    homework: str = ""
    resources: str = ""
    assessment: str = ""
    expected_version: int = 0
    #: Required only on an approved week; anything else is a normal submit/resubmit.
    intent: Literal["change"] | None = None


class LessonPlanWeekRead(BaseModel):
    """One week tab: the calendar slot, the latest plan, and the approved snapshot."""

    #: The submitted row; `None` until the week is submitted (approval needs an id).
    plan_id: UUID | None = None
    week_no: int
    start_date: date
    end_date: date
    #: The real open days in the range (Sunday/holiday removed).
    teaching_days: list[date] = []
    #: `None` means "not submitted" - the week has no row yet.
    status: str | None = None
    version: int = 0
    approved_version: int | None = None
    #: Send this back on submit; `0` for a week with no row.
    expected_version: int = 0
    topics: str = ""
    learning_objectives: str = ""
    activities: str = ""
    homework: str = ""
    resources: str = ""
    assessment: str = ""
    #: The last approved version's content, even when a newer version is pending.
    approved: LessonPlanContentRead | None = None
    rejection_reason: str | None = None
    submitted_at: datetime | None = None
    submitted_by: str | None = None
    can_edit: bool = False
    #: Approved week: a change needs the explicit "Request change" intent.
    can_request_change: bool = False


class ReviewRow(BaseModel):
    """One submitted week in the approver's queue, with the full six fields."""

    plan_id: UUID
    classroom_subject_id: UUID
    section_id: UUID
    #: "Class 9-A" - what the reviewer's list prints.
    label: str
    subject: str
    week_no: int
    year: int
    month: int
    start_date: date
    end_date: date
    status: str
    version: int
    expected_version: int
    submitted_at: datetime | None = None
    submitted_by: str | None = None
    topics: str = ""
    learning_objectives: str = ""
    activities: str = ""
    homework: str = ""
    resources: str = ""
    assessment: str = ""
    rejection_reason: str | None = None


class ReviewCountRead(BaseModel):
    count: int = 0


class ApproveIn(CanonicalRequest):
    """The version the reviewer saw; a stale review is a `409`."""

    expected_version: int


class RejectIn(BaseModel):
    """`reason` is mandatory - the teacher has to know what to correct.

    Plain `BaseModel`, not `CanonicalRequest`: the reviewer's sentence is prose and keeps
    its capitalisation (the same rule as the plan's six fields).
    """

    reason: str
    expected_version: int

    @model_validator(mode="after")
    def _reason(self):
        self.reason = " ".join((self.reason or "").split())
        if not self.reason:
            raise ValueError("A rejection reason is required.")
        if len(self.reason) > 1000:
            raise ValueError("The rejection reason must be at most 1000 characters.")
        return self


class ApproveManyItem(BaseModel):
    plan_id: UUID
    expected_version: int


class ApproveManyIn(CanonicalRequest):
    items: list[ApproveManyItem]


class ReviewDecisionRead(BaseModel):
    plan_id: UUID
    status: str
    version: int
    approved_version: int | None = None
    rejection_reason: str | None = None
    reviewed_at: datetime | None = None


class BulkReviewItem(BaseModel):
    plan_id: UUID
    #: approved / skipped
    status: str
    detail: str | None = None


class BulkReviewResult(BaseModel):
    approved: list[UUID] = []
    skipped: list[BulkReviewItem] = []


class CourseSummaryRead(BaseModel):
    """The small count the Classroom/Course badge asks for."""

    subject_count: int = 0
    pending_approvals: int = 0
    completion_percent: float | None = None


class CourseTeacherRow(BaseModel):
    """One teacher in the Teachers > Course list, with the aggregate the table needs."""

    employee_id: UUID
    name: str
    employee_code: str | None = None
    department: str | None = None
    subjects_count: int = 0
    sections_count: int = 0
    pending_approvals: int = 0
    behind_subjects: int = 0
    completion_percent: float | None = None


class TeacherWeekRow(BaseModel):
    week_no: int
    start_date: date
    end_date: date
    plan_id: UUID | None = None
    status: str | None = None
    version: int = 0
    approved_version: int | None = None
    rejection_reason: str | None = None


class TeacherChapterRow(BaseModel):
    chapter_id: UUID
    sequence: int
    name: str
    planned_date: date | None = None
    status: str = "Pending"
    completed_on: date | None = None
    completed_by: str | None = None


class TeacherAssignmentRow(BaseModel):
    """One subject/class-section a teacher holds (or held)."""

    classroom_subject_id: UUID
    section_id: UUID
    label: str
    subject: str
    current: bool = True
    effective_from: date | None = None
    effective_to: date | None = None
    done: int = 0
    total: int = 0
    percent: float | None = None
    weeks: list[TeacherWeekRow] = []
    chapters: list[TeacherChapterRow] = []


class TeacherCourseDetail(BaseModel):
    employee_id: UUID
    name: str
    employee_code: str | None = None
    department: str | None = None
    #: Current open assignments, then the past ones.
    assignments: list[TeacherAssignmentRow] = []


class SubjectCourseRead(BaseModel):
    """One subject's course in one class-section."""

    #: The row the Course tab acts on (teacher, plan, archive). `None` only for a
    #: legacy `subjectteacher` row written before Phase 1's backfill.
    classroom_subject_id: UUID | None = None
    #: The section's own display name.
    name: str
    code: str | None = None
    #: Active / Archived - the section's row, not a school-wide master list.
    status: str = "Active"
    #: The teacher holding it today (`None` when nobody is assigned).
    current_teacher: str | None = None
    current_teacher_id: UUID | None = None
    #: Everyone who has held it, oldest first.
    teachers: list[CourseTeacherRead] = []
    done: int = 0
    total: int = 0
    #: `None` when there is no plan - "no plan" is not "0%".
    percent: float | None = None
    #: The first chapter that is not completed (what the class is on now).
    next_chapter: str | None = None
    #: Chapters whose planned date has passed and that are not completed.
    behind: int = 0
    #: True when at least one chapter carries a planned date.
    planned: bool = False
    chapters: list[ChapterRowRead] = []
    #: This month's weekly-plan counts, or None when no week has been submitted.
    lesson_plan: LessonPlanSummaryRead | None = None
    #: What this caller may do **to this row**, decided on the server.
    can_manage: bool = False
    can_assign_teacher: bool = False
    can_archive: bool = False
    can_restore: bool = False
    can_delete: bool = False
    #: Draft / Submitted / Approved - the chapter list's own lifecycle.
    chapter_plan_status: str = "Draft"
    chapter_plan_reject_reason: str | None = None
    #: Chapters skipped (approved). They are not counted as done.
    skipped: int = 0
    #: Chapters whose saved change waits for the principal's approval.
    pending_approval: int = 0
    #: May this caller add / rename / delete chapters right now?
    can_edit_plan: bool = False
    #: May this caller submit the list for approval?
    can_submit_plan: bool = False
    #: May this caller save progress (Completed / Skipped) on an approved list?
    can_save_progress: bool = False
    #: May this caller approve or send back a plan or a progress change?
    can_approve: bool = False


class SectionCourseRead(BaseModel):
    """`GET /classroom/sections/{id}/course` - the whole Course tab in one read."""

    section_id: UUID
    label: str
    #: The session the plan belongs to ("2026-27"), when one is open.
    academic_year: str | None = None
    #: D7: the average of each subject's own percentage; None when no subject has a plan.
    completion_percent: float | None = None
    #: How many subjects that average is made of (subjects with at least one chapter).
    completion_subjects: int = 0
    #: Active subjects in this section - "No Subjects Yet" is this being zero.
    subjects_count: int = 0
    subjects: list[SubjectCourseRead] = []


class ChapterTickIn(CanonicalRequest):
    """Tick a chapter for one class-section.

    The section is part of the body because a chapter belongs to the **class** and the
    progress belongs to the **section**: the same chapter can be done in 9-A and not in
    9-B, and only the caller knows which register they are looking at.
    """

    classroom_id: UUID
    #: Pending / In progress / Completed (the tab's own words).
    status: str


class ProgressItemIn(CanonicalRequest):
    chapter_id: UUID
    #: Pending (take my change back) / Completed / Skipped.
    status: str


class ProgressSaveIn(CanonicalRequest):
    """Save several chapters at once; the server fills the gaps with `Skipped`."""

    items: list[ProgressItemIn]


class PlanRejectIn(BaseModel):
    reason: str

    @model_validator(mode="after")
    def _clean(self):
        self.reason = " ".join((self.reason or "").split())
        if not self.reason:
            raise ValueError("Tell the teacher what to change.")
        return self


class AddSectionSubjectIn(CanonicalRequest):
    """Add one subject to this class-section.

    There is no school-wide picker: the name typed here belongs to this section
    only. `code` is optional and never used as an identity.
    """

    name: str
    code: str | None = None

    @model_validator(mode="after")
    def _clean(self):
        self.name = " ".join((self.name or "").split())
        if not self.name:
            raise ValueError("Type a subject name.")
        return self


class ClassroomSubjectUpdate(CanonicalRequest):
    """Rename one classroom subject without touching any other section."""

    name: str
    code: str | None = None

    @model_validator(mode="after")
    def _clean(self):
        self.name = " ".join((self.name or "").split())
        if not self.name:
            raise ValueError("Type a subject name.")
        return self


class CourseSubjectRowRead(BaseModel):
    """The row Add Subject / rename / archive / restore returns."""

    classroom_subject_id: UUID
    name: str
    code: str | None = None
    status: str


class CourseTeacherAssignIn(CanonicalRequest):
    """Assign or change the teacher of one section subject.

    `effective_from` defaults to today. A change closes the open assignment the day
    before and opens a new row - the timeline is history, never an overwrite.
    """

    teacher_id: UUID
    effective_from: date | None = None


class TeacherAssignResult(BaseModel):
    """What the assign/change answers with - including the workload warning, if any."""

    classroom_subject_id: UUID
    teacher_id: UUID
    teacher: str
    effective_from: date
    #: A sentence about the teacher's current load; the assignment still happened.
    warning: str | None = None
