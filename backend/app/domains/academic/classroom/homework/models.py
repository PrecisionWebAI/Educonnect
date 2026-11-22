import enum
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Index, UniqueConstraint, text
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
    #: Section-owned subject (Phase 2). Legacy `subject_id` stays nullable until M5.
    classroom_subject_id: UUID = Field(foreign_key="classroomsubject.id", index=True)
    subject_id: UUID | None = Field(default=None, foreign_key="subject.id")
    teacher_id: UUID = Field(foreign_key="employee.id")
    due_date: date


class HomeworkAssignment(HomeworkAssignmentBase, TenantMixin, UUIDMixin, table=True):
    pass


class HomeworkSubmissionBase(SQLModel):
    homework_id: UUID = Field(foreign_key="homeworkassignment.id")
    student_id: UUID = Field(foreign_key="student.id")
    content_url: str | None = None
    status: SubmissionStatus = Field(default=SubmissionStatus.pending)
    teacher_feedback: str | None = None
    #: When the child actually handed it in - set by `POST /homework/submit`, never by
    #: hand, so "Submitted" on the board is a fact rather than a status word.
    submitted_at: datetime | None = None
    #: True when `submitted_at` fell after the assignment's due date. Kept as a column
    #: (not derived on read) because the due date can be moved later - and a child who
    #: was late should stay late.
    is_late: bool = Field(default=False)
    #: When the teacher graded it, and what they gave. `numeric(6,2)` like every other
    #: mark in the school, so 12.5 out of 25 stays exact.
    graded_at: datetime | None = None
    marks_awarded: Decimal | None = Field(default=None, max_digits=6, decimal_places=2)


class HomeworkSubmission(HomeworkSubmissionBase, TenantMixin, UUIDMixin, table=True):
    """One row per child per assignment - the key says so.

    The service has always upserted on `(homework_id, student_id)`; without the
    constraint two requests could still race and put the same child on the board twice.
    """

    __table_args__ = (
        UniqueConstraint(
            "homework_id",
            "student_id",
            name="uq_homeworksubmission_homework_student",
        ),
    )


class ClassLogBase(SQLModel):
    """One line of a class-section's day: what was covered, and anything noted.

    A line is **either** the register-style entry for the whole day
    (`timetableperiod_id` NULL, one per class-section per day) **or** the record of
    one period (`timetableperiod_id` set, one per period). The two keys in
    `ClassLog.__table_args__` enforce exactly that, which is what makes the workload
    tab's "completed this week" a period count rather than a day count.

    Anything about a single student belongs in `DiaryRemark`, so a class-wide note
    is not repeated on every student's row.
    """

    classroom_id: UUID = Field(foreign_key="classroom.id", index=True)
    #: Who wrote it - the class teacher, normally.
    teacher_id: UUID = Field(foreign_key="employee.id")
    #: The timetable slot this log entry was written against (Phase 2). NULL for the
    #: register-style entry a class teacher keeps once a day, and set when the log is
    #: written per period - which is what lets the workload tab report "periods
    #: completed this week" instead of guessing from the day.
    timetableperiod_id: UUID | None = Field(
        default=None, foreign_key="timetableperiod.id", index=True
    )
    #: Which subject this line was about. NULL is allowed - a day-level entry ("revision
    #: + doubt clearing") may cover several - but a per-period log should name it, which
    #: is what lets the diary be read by subject (Phase 9).
    classroom_subject_id: UUID | None = Field(
        default=None, foreign_key="classroomsubject.id", index=True
    )
    subject_id: UUID | None = Field(default=None, foreign_key="subject.id", index=True)
    date: date
    note: str


class ClassLog(ClassLogBase, TenantMixin, UUIDMixin, table=True):
    """Two keys, because a log line has two shapes.

    * `uq_classlog_classroom_date_period` - one line per class-section **per period**;
    * `uq_classlog_classroom_day_only` - a **partial** unique index, so the
      day-level entry (no period) is still one per class-section per day. Without it
      PostgreSQL would treat two NULL `timetableperiod_id` values as different and
      let the day's line be written twice.
    """

    __tablename__ = "classlog"
    __table_args__ = (
        UniqueConstraint(
            "classroom_id",
            "date",
            "timetableperiod_id",
            name="uq_classlog_classroom_date_period",
        ),
        Index(
            "uq_classlog_classroom_day_only",
            "classroom_id",
            "date",
            unique=True,
            postgresql_where=text("timetableperiod_id IS NULL"),
            #: SQLite ignores `postgresql_where`; without this the index would be an
            #: unconditional unique on (classroom, date) and a second period in the
            #: same room on the same day would be refused by the tests.
            sqlite_where=text("timetableperiod_id IS NULL"),
        ),
    )


class DiaryRemarkBase(SQLModel):
    """A note about one student on one day's log.

    This is where the per-student part of the old `classdiary` went: the log holds
    the class's day, and a remark names the student it is about.
    """

    class_log_id: UUID = Field(foreign_key="classlog.id", index=True)
    student_id: UUID = Field(foreign_key="student.id")
    remark: str


class DiaryRemark(DiaryRemarkBase, TenantMixin, UUIDMixin, table=True):
    pass
