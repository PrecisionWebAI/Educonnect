import enum
from datetime import date
from uuid import UUID

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.ids import UUIDMixin
from app.core.tenancy import TenantMixin


class SubmissionStatus(enum.StrEnum):
    pending = "pending"
    submitted = "submitted"
    graded = "graded"


class HomeworkAssignmentBase(SQLModel):
    title: str
    description: str
    #: Homework is set for one class-section - the school's `classroom` row
    #: ("Class 10-A"). The class comes from `classroom.class_id`.
    classroom_id: UUID = Field(foreign_key="classroom.id", index=True)
    subject_id: UUID = Field(foreign_key="subject.id")
    teacher_id: UUID = Field(foreign_key="employee.id")
    due_date: date


class HomeworkAssignment(HomeworkAssignmentBase, TenantMixin, UUIDMixin, table=True):
    pass


class HomeworkSubmissionBase(SQLModel):
    homework_id: UUID = Field(foreign_key="homeworkassignment.id")
    student_id: UUID = Field(foreign_key="studentprofile.id")
    content_url: str | None = None
    status: SubmissionStatus = Field(default=SubmissionStatus.pending)
    teacher_feedback: str | None = None


class HomeworkSubmission(HomeworkSubmissionBase, TenantMixin, UUIDMixin, table=True):
    pass


class ClassLogBase(SQLModel):
    """The day's log for one class-section: what was covered, and anything noted.

    One row per class-section per day (`UNIQUE(classroom_id, date)`) - the
    register-style line a class teacher actually keeps for the whole class.
    Anything about a single student belongs in `DiaryRemark`, so a class-wide note
    is not repeated on every student's row.
    """

    classroom_id: UUID = Field(foreign_key="classroom.id", index=True)
    #: Who wrote it - the class teacher, normally.
    teacher_id: UUID = Field(foreign_key="employee.id")
    date: date
    note: str


class ClassLog(ClassLogBase, TenantMixin, UUIDMixin, table=True):
    """`UNIQUE(classroom_id, date)` - one log entry per class-section per day."""

    __tablename__ = "classlog"
    __table_args__ = (
        UniqueConstraint("classroom_id", "date", name="uq_classlog_classroom_date"),
    )


class DiaryRemarkBase(SQLModel):
    """A note about one student on one day's log.

    This is where the per-student part of the old `classdiary` went: the log holds
    the class's day, and a remark names the student it is about.
    """

    class_log_id: UUID = Field(foreign_key="classlog.id", index=True)
    student_id: UUID = Field(foreign_key="studentprofile.id")
    remark: str


class DiaryRemark(DiaryRemarkBase, TenantMixin, UUIDMixin, table=True):
    pass
