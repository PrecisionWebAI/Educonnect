"""The shapes the Homework board and the diary read and write.

One naming rule, and it is worth stating: the **API says `section_id`**, the database
column is `classroom_id`. A class-section is what homework is set for and what a
timetable period belongs to, so that is the word a screen and a URL use - and the
repository is the only place that knows both names.
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.text import CanonicalRequest

from .models import SubmissionStatus

#: A score is `numeric(6,2)` - the same shape as every mark in the school.
_EXACT = {"max_digits": 6, "decimal_places": 2}


class HomeworkAssignmentCreate(CanonicalRequest):
    """One assignment for one class-section."""

    title: str
    description: str
    section_id: UUID
    subject_id: UUID
    teacher_id: UUID
    due_date: date


class HomeworkAssignmentRead(BaseModel):
    id: UUID
    title: str
    description: str
    section_id: UUID
    subject_id: UUID
    teacher_id: UUID
    due_date: date
    subject: str | None = None
    className: str | None = None
    due: str | None = None
    assignedBy: str | None = None
    #: How many children have handed it in, out of the section's roll. Counted from
    #: `homeworksubmission` in one grouped query, so the board can say "3/4 in" without
    #: reading every submission row.
    submitted: int = 0
    total: int = 0


class SubmissionSubmitIn(BaseModel):
    """What a student or a guardian sends: the assignment, the child, an optional link."""

    homework_id: UUID
    student_id: UUID
    content_url: str | None = None


class SubmissionFeedbackIn(BaseModel):
    """What a teacher sends back: a score, a remark, or both."""

    marks_awarded: Decimal | None = Field(default=None, **_EXACT)
    teacher_feedback: str | None = None


class HomeworkSubmissionRead(BaseModel):
    """One submission row, as the submit call answers it."""

    id: UUID
    homework_id: UUID
    student_id: UUID
    status: SubmissionStatus
    content_url: str | None = None
    submitted_at: datetime | None = None
    is_late: bool = False


class SubmissionItemRead(BaseModel):
    """One row of the review board - a child, an assignment and where it has got to."""

    #: `None` for a child who has not handed anything in yet: there is no submission
    #: row to point at, and nothing to grade - which is exactly what the board shows.
    id: UUID | None = None
    homeworkId: UUID
    homeworkTitle: str
    studentId: UUID
    student: str
    sectionId: UUID | None = None
    subject: str | None = None
    #: `Pending` | `Submitted` | `Graded`. "Late" is a **fact of its own** (`isLate`),
    #: not a fourth status: a late submission is still submitted, and a graded one was
    #: graded whether or not it arrived on time.
    status: str
    #: `YYYY-MM-DD HH:MM` (or "" when it has not arrived) - what the column prints.
    submittedAt: str = ""
    isLate: bool = False
    marksAwarded: Decimal | None = None
    feedback: str | None = None
    gradedAt: str | None = None


class ClassLogCreate(CanonicalRequest):
    """Write one line of a class-section's day.

    `timetableperiod_id` names the period the line is about (or is NULL for the
    register-style day entry), and `subject_id` says what was taught - the field Phase 9
    added, so a diary can be read by subject.
    """

    section_id: UUID
    teacher_id: UUID
    timetableperiod_id: UUID | None = None
    subject_id: UUID | None = None
    date: date
    note: str


class ClassLogRead(BaseModel):
    id: UUID
    section_id: UUID
    teacher_id: UUID
    timetableperiod_id: UUID | None = None
    subject_id: UUID | None = None
    date: date
    note: str


class DiaryEntryRead(BaseModel):
    """One line of the diary, with the names a reader needs."""

    id: UUID
    className: str
    #: `YYYY-MM-DD` - the day it was written about.
    date: str
    #: "Mon", "Tue" … - the day's own word.
    day: str
    subject: str
    #: "P3" / "Break" / "" when the line covers the whole day.
    period: str
    topic: str

    graded_at: datetime | None = None
    marks_awarded: Decimal | None = None
    teacher_feedback: str | None = None
