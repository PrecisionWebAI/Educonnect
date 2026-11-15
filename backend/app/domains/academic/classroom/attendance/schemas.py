from datetime import date
from uuid import UUID

from pydantic import BaseModel

from app.core.text import CanonicalRequest

from .models import AttendanceRecordBase, AttendanceStatus


class AttendanceRecordCreate(CanonicalRequest, AttendanceRecordBase):
    pass


class AttendanceRecordRead(AttendanceRecordBase):
    id: UUID
    studentName: str | None = None
    className: str | None = None
    subjectName: str | None = None


class AttendanceRowWrite(BaseModel):
    """One child's mark inside a whole-register save.

    `status` is the stored wording (`present` / `absent` / `late` / `half_day` /
    `leave`), not the label a chip shows. A field the client did not send keeps what
    the row already says - `remarks` is therefore optional in the true sense.
    """

    student_id: UUID
    status: AttendanceStatus
    remarks: str | None = None


class AttendanceBulkCreate(CanonicalRequest):
    """A whole register in one call.

    Only the section is named - the class is `section.class_id`, so there is
    no second class id to keep in step with it. Saving the same register twice is an
    **update** (one row per child/day/subject), never a second row.
    """

    section_id: UUID
    subject_id: UUID | None = None
    date: date
    records: list[AttendanceRowWrite]


class RegisterRowRead(BaseModel):
    """One line of the register as the screen draws it.

    `marked` is the difference between "absent" and "nobody has said anything yet";
    `status` is `unmarked` for the second case. A child on approved leave shows
    `leave` **derived** from the request, with its id so the office can open it.
    """

    student_id: UUID
    record_id: UUID | None = None
    name: str
    admissionNo: str | None = None
    status: str
    marked: bool
    remarks: str | None = None
    leave_request_id: UUID | None = None


class RegisterCountsRead(BaseModel):
    present: int = 0
    absent: int = 0
    late: int = 0
    half_day: int = 0
    leave: int = 0
    unmarked: int = 0


class RegisterRead(BaseModel):
    """`GET /attendance/section/{id}?date=` - the roll plus the day's answer."""

    section_id: UUID
    date: date
    subject_id: UUID | None = None
    #: "Sunday" or the holiday's name when the school is closed that day; the
    #: register is still readable (it is history), it just cannot be saved.
    closed_reason: str | None = None
    counts: RegisterCountsRead
    #: Attendance percentage for that day (`None` when nothing is marked).
    percent: float | None = None
    rows: list[RegisterRowRead] = []


class StudentAttendanceSummaryRead(BaseModel):
    """One child over a range - the numbers the report card and the flag use."""

    student_id: UUID
    name: str
    admissionNo: str | None = None
    present: int = 0
    absent: int = 0
    late: int = 0
    half_day: int = 0
    leave: int = 0
    #: Days with a register row (leave days excluded - a leave is not a mark).
    marked: int = 0
    #: `None` when nothing was marked in the range: no data, not zero.
    percent: float | None = None
    threshold: int = 75
    below_threshold: bool = False


class SectionSummaryRead(BaseModel):
    section_id: UUID
    from_date: date
    to_date: date
    #: Days in the range the school was open (Sundays and holidays removed).
    working_days: int
    threshold: int
    rows: list[StudentAttendanceSummaryRead] = []


class TrendPointRead(BaseModel):
    """One day of the trend: `percent` is `None` when nothing was marked."""

    date: date
    present: int = 0
    marked: int = 0
    percent: float | None = None


class SectionTrendRead(BaseModel):
    section_id: UUID
    days: int
    #: Oldest first, so a chart can draw left to right.
    points: list[TrendPointRead] = []


class AttentionRowRead(BaseModel):
    """A child the office should ring: low percentage or a run of absences."""

    student_id: UUID
    name: str
    admissionNo: str | None = None
    percent: float | None = None
    consecutive_absences: int = 0
    reason: str


class ClosedDayRead(BaseModel):
    """A day the school does not run - what the date picker greys out.

    `reason` is the words the screen prints: `"Sunday"`, or the holiday's own name
    ("Diwali break"). The picker disables the day and the toolbar explains it, so the
    operator learns *why* Save is off instead of guessing.
    """

    date: date
    reason: str


class IrregularStudentRead(BaseModel):
    id: UUID
    name: str
    className: str
    absences: int
    pattern: str
    risk: str


class LeaveSyncRowRead(BaseModel):
    id: UUID
    student: str
    className: str
    from_date: str
    days: int
    autoMarked: str
    status: str
