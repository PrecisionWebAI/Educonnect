"""The Course feature's own tables: which subjects a section runs, and its weekly plan.

Three tables, each with one job:

* ``classroomsubject`` - "Class 9-A runs Mathematics in 2026-27". It is what the Course
  tab's rows are, and it exists before a teacher does: adding a subject and assigning a
  teacher are two separate decisions.
* ``lessonplan`` - the **latest** version of one week's plan (subject + month + week),
  with its status and review fields. "Not Submitted" is the absence of a row.
* ``lessonplanhistory`` - one immutable snapshot per submitted version. The content is
  never rewritten; reviewing stamps the verdict (`approved_at` / `rejected_at`). An
  approved week stays effective until a new version is approved, which is why the
  current row carries `approved_version`.

Naming follows the rest of the schema (`chapterprogress`, `staffworkloadrule`): SQLModel's
default lower-case table name, no underscores.
"""

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, Index, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.ids import UUIDMixin
from app.core.tenancy import TenantMixin
from app.domains.auth.models import utcnow

#: The two words a section's subject row can carry. Archived rows stay (homework, exams
#: and papers point at the subject) but leave the Add Subject dropdown.
COURSE_ACTIVE = "Active"
COURSE_ARCHIVED = "Archived"
COURSE_STATUSES: tuple[str, ...] = (COURSE_ACTIVE, COURSE_ARCHIVED)

#: The words a week's plan carries. There is no Draft: a row is written by a Submit.
PLAN_SUBMITTED = "Submitted"
PLAN_APPROVED = "Approved"
PLAN_REJECTED = "Rejected"
PLAN_STATUSES: tuple[str, ...] = (PLAN_SUBMITTED, PLAN_APPROVED, PLAN_REJECTED)

#: The plan's official format. Bumping this is how a future field is introduced without
#: reinterpreting older rows.
PLAN_FORMAT_VERSION = 1


class ClassroomSubjectBase(SQLModel):
    """One subject, in one class-section, for one school session."""

    classroom_id: UUID = Field(foreign_key="classroom.id", index=True)
    subject_id: UUID = Field(foreign_key="subject.id", index=True)
    #: The session this row belongs to (`academic_year.id`). A subject is added once per
    #: session, so next year's sections start clean while this year's history stays.
    academic_year_id: UUID = Field(foreign_key="academic_year.id", index=True)
    #: Active / Archived - the words themselves (like every other status here).
    status: str = Field(default=COURSE_ACTIVE)
    created_by_user_id: UUID | None = Field(
        default=None, foreign_key="app_user.id", index=True
    )
    #: Set when the school archives it; NULL while it is running.
    archived_at: datetime | None = None
    archived_by_user_id: UUID | None = Field(
        default=None, foreign_key="app_user.id", index=True
    )


class ClassroomSubject(ClassroomSubjectBase, TenantMixin, UUIDMixin, table=True):
    """`UNIQUE(classroom_id, subject_id, academic_year_id)` - one per section/subject/session."""

    __table_args__ = (
        UniqueConstraint(
            "classroom_id",
            "subject_id",
            "academic_year_id",
            name="uq_classroomsubject_section_subject_year",
        ),
        Index(
            "ix_classroomsubject_school_classroom_status",
            "school_id",
            "classroom_id",
            "status",
        ),
        CheckConstraint(
            "status IN ('Active', 'Archived')",
            name="ck_classroomsubject_status",
        ),
    )

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class LessonPlanBase(SQLModel):
    """One week of a subject's plan, in the official six-field format.

    The prose fields are plain `str` (PostgreSQL `varchar` with no limit), because a
    paragraph has no canonical form: the request model deliberately does **not** inherit
    `CanonicalRequest`, so "Learning Objectives" keeps the teacher's capitalisation.
    """

    classroom_subject_id: UUID = Field(foreign_key="classroomsubject.id", index=True)
    #: Denormalised so "the school's pending plans this session" is one indexed read.
    academic_year_id: UUID = Field(foreign_key="academic_year.id", index=True)
    #: The calendar month and the week inside it (1-4, plus 5 when the month has 29+ days).
    year: int
    month: int
    week_no: int
    #: The week's own range, stored rather than recomputed: a later calendar edit must not
    #: silently move a plan that was already submitted.
    start_date: date
    end_date: date
    topics: str = ""
    learning_objectives: str = ""
    activities: str = ""
    homework: str = ""
    resources: str = ""
    assessment: str = ""
    #: Which shape the six fields above are in (see `PLAN_FORMAT_VERSION`).
    format_version: int = Field(default=PLAN_FORMAT_VERSION)
    #: Submitted / Approved / Rejected - the **latest** version's status.
    status: str = Field(default=PLAN_SUBMITTED)
    #: The latest version, and the last version that was approved (NULL before the first
    #: approval). A rejected newer version leaves `approved_version` where it was, so the
    #: class keeps the plan the principal already signed.
    version: int = Field(default=1)
    approved_version: int | None = None
    submitted_by_employee_id: UUID | None = Field(
        default=None, foreign_key="employee.id", index=True
    )
    submitted_at: datetime | None = None
    reviewed_by_user_id: UUID | None = Field(default=None, foreign_key="app_user.id")
    reviewed_at: datetime | None = None
    #: The reviewer's words on a rejection; cleared by the next submit.
    rejection_reason: str | None = None


class LessonPlan(LessonPlanBase, TenantMixin, UUIDMixin, table=True):
    """`UNIQUE(classroom_subject_id, academic_year_id, year, month, week_no)`."""

    __table_args__ = (
        UniqueConstraint(
            "classroom_subject_id",
            "academic_year_id",
            "year",
            "month",
            "week_no",
            name="uq_lessonplan_subject_year_month_week",
        ),
        Index("ix_lessonplan_school_status", "school_id", "status"),
        Index(
            "ix_lessonplan_subject_year_month",
            "classroom_subject_id",
            "year",
            "month",
        ),
        Index(
            "ix_lessonplan_school_submitter",
            "school_id",
            "submitted_by_employee_id",
        ),
        CheckConstraint(
            "status IN ('Submitted', 'Approved', 'Rejected')",
            name="ck_lessonplan_status",
        ),
        CheckConstraint("month >= 1 AND month <= 12", name="ck_lessonplan_month"),
        CheckConstraint("week_no >= 1 AND week_no <= 5", name="ck_lessonplan_week"),
        CheckConstraint("end_date >= start_date", name="ck_lessonplan_dates"),
        CheckConstraint("version >= 1", name="ck_lessonplan_version"),
    )

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class LessonPlanHistoryBase(SQLModel):
    """One submitted version's content, kept exactly as it was submitted.

    The six fields and the dates are immutable. Review adds `approved_*` or `rejected_*`
    once; the row itself is never edited by a teacher and never rewritten by a later
    submission (that is a new version, a new row).
    """

    lesson_plan_id: UUID = Field(foreign_key="lessonplan.id", index=True)
    version: int
    start_date: date
    end_date: date
    topics: str = ""
    learning_objectives: str = ""
    activities: str = ""
    homework: str = ""
    resources: str = ""
    assessment: str = ""
    format_version: int = Field(default=PLAN_FORMAT_VERSION)
    submitted_by_employee_id: UUID | None = Field(
        default=None, foreign_key="employee.id", index=True
    )
    submitted_at: datetime | None = None
    approved_at: datetime | None = None
    approved_by_user_id: UUID | None = Field(default=None, foreign_key="app_user.id")
    rejected_at: datetime | None = None
    rejected_by_user_id: UUID | None = Field(default=None, foreign_key="app_user.id")
    rejection_reason: str | None = None


class LessonPlanHistory(LessonPlanHistoryBase, TenantMixin, UUIDMixin, table=True):
    """`UNIQUE(lesson_plan_id, version)` - one snapshot per version, never two."""

    __table_args__ = (
        UniqueConstraint(
            "lesson_plan_id",
            "version",
            name="uq_lessonplanhistory_plan_version",
        ),
        Index(
            "ix_lessonplanhistory_school_plan",
            "school_id",
            "lesson_plan_id",
        ),
    )

    created_at: datetime = Field(default_factory=utcnow)
