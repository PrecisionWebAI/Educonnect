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
    #: The section subject for a per-subject register; NULL is the day register.
    classroom_subject_id: UUID | None = None
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
    #: False for a child who has left the school: still on the sheet (their history is
    #: real), but the screen greys the chips out instead of inviting a mark.
    active: bool = True


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
    classroom_subject_id: UUID | None = None
    #: "Sunday" or the holiday's name when the school is closed that day; the
    #: register is still readable (it is history), it just cannot be saved.
    closed_reason: str | None = None
    #: `weekly_off` / `week_off` / `holiday` - the colour the calendar paints the day.
    closed_kind: str | None = None
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
    #: Present + late - what the table prints as "Present", because a late child was
    #: in school and the register's own percentage counts them the same way.
    present_total: int = 0
    absent: int = 0
    late: int = 0
    half_day: int = 0
    leave: int = 0
    #: Days with a register row (leave days excluded - a leave is not a mark).
    marked: int = 0
    #: Present + late **in the month the register's calendar shows** - what the row
    #: prints as `Monthly attendance 12/30`.
    month_present_total: int = 0
    #: Absent days in that month.
    month_absent: int = 0
    #: Open days of that month up to the month's cutoff - the `/12` in `Monthly
    #: attendance 5/12`. A **completed** month divides by all of its open days; the month
    #: we are living in divides by the open days up to the day on screen. A day nobody
    #: marked inside that span is still a day the school was open, so it counts against
    #: the child - only the days after the cutoff are left alone.
    month_open_days: int = 0
    #: Days of that month with a saved register (up to the cutoff) - not the denominator,
    #: but the number the row's tooltip prints as "9 of 12 registers taken".
    month_saved: int = 0
    #: Open days this child's percentage divides by (the class window, or their own
    #: first mark when they joined later).
    open_days: int = 0
    #: `None` when nothing was marked in the range: no data, not zero.
    percent: float | None = None
    threshold: int = 75
    below_threshold: bool = False


class SectionSummaryRead(BaseModel):
    section_id: UUID
    from_date: date
    #: The last day the annual percentage may judge: the cutoff (today when this section
    #: has a register today, yesterday otherwise), or the `to` the caller named.
    to_date: date
    #: Days in the range the school was open (Sundays and holidays removed).
    working_days: int
    threshold: int
    #: The month the rows' `Monthly attendance` describes, and where its cutoff fell.
    #: `month_to_date` before `month_from_date` means "nothing has happened in it yet".
    month_from_date: date | None = None
    month_to_date: date | None = None
    rows: list[StudentAttendanceSummaryRead] = []


class TrendPointRead(BaseModel):
    """One bar of the trend: a day, a week of the month, or a month.

    `percent` is `None` when nothing was marked in the span - a chart must not accuse a
    class on a day nobody opened the register. `label` is the x-axis word ("Mon", "3rd wk
    Nov", "Nov") and `end_date` where a multi-day span stops, so a tooltip can name the
    whole span from the same payload the axis is drawn from.
    """

    date: date
    #: The x-axis word, decided by the server: the axis does not guess the span's name.
    label: str = ""
    present: int = 0
    marked: int = 0
    percent: float | None = None
    #: The last day of the span; `None` for a single day (it is `date`).
    end_date: date | None = None


class SectionTrendRead(BaseModel):
    section_id: UUID
    #: The scale the points are on - `day`, `week` or `month`.
    range: str = "day"
    #: The day window a `day` chart covers (kept for the callers that still ask in days).
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

    `reason` is the words the screen prints: `"Sunday"`, `"1st Saturday"`, or the
    holiday's own name ("Diwali break"). `kind` is what the calendar colours by
    (`weekly_off` / `week_off` / `holiday`), so the screen never has to compare text to
    decide a colour. The picker marks the day and the toolbar explains it, so the
    operator learns *why* Save is off instead of guessing.
    """

    date: date
    reason: str
    #: `weekly_off` / `week_off` / `holiday`.
    kind: str | None = None


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


# ---------------------------------------------------------------------------
# The school's calendar (Phase 3.5): holidays are school-wide, never per section
# ---------------------------------------------------------------------------


class HolidayRead(BaseModel):
    """One row of the calendar list."""

    id: UUID
    name: str
    #: `public` / `school` / `vacation` / `other` (older rows may say festival/local).
    kind: str
    #: The words the list prints beside the type.
    kind_label: str
    start_date: date
    #: Equal to `start_date` for a single day.
    end_date: date
    #: Calendar days the row covers, both ends included.
    days: int
    created_by_id: UUID | None = None
    created_by: str | None = None


class HolidayWrite(BaseModel):
    """Add or edit a holiday: one day, or a range that may cross a month."""

    name: str
    kind: str = "public"
    start_date: date
    #: Empty means the single day `start_date`.
    end_date: date | None = None


class HolidayImpact(BaseModel):
    """What a saved holiday means for registers that already exist."""

    holiday: HolidayRead
    #: Days in the window that already have a saved register. A warning, never a
    #: delete: the attendance rows stay and the day leaves every count.
    saved_register_days: int = 0


class OpenDayRead(BaseModel):
    """One date the school reopened although a weekly off or a holiday closes it."""

    on_date: date
    created_by_id: UUID | None = None
    #: The name the calendar prints beside the row.
    created_by: str | None = None


class OpenDayWrite(BaseModel):
    """The single date to reopen - the calendar's "just this day" override."""

    on_date: date


class HolidayCalendarRead(BaseModel):
    """Everything the calendar draws for one window."""

    from_date: date
    to_date: date
    #: The holiday rows only - an extra weekly off is a closure, not a holiday.
    holidays: list[HolidayRead] = []
    #: `date.weekday()` values (0 = Monday) the school is closed every week.
    weekly_off_days: list[int] = []
    #: The "1st/2nd/3rd/4th Saturday" rules, as the `"5#1"` tokens they are stored as.
    nth_off_days: list[str] = []
    #: Every day in the window the calendar must shade as a **weekly off**, straight from
    #: `closure()`: a whole weekday, a Saturday rule and a dated extra off all arrive here
    #: already worked out. The screen draws the list; it never repeats the date maths, so a
    #: "2nd and 4th Saturday" rule cannot look right in one calendar and wrong in another.
    weekly_off_dates: list[date] = []
    #: Days in the window the school dated as an extra weekly off (`kind = week_off`).
    #: They close the day like a Sunday, so they never appear in `holidays`.
    week_off_dates: list[date] = []
    #: The extra weekly off rows themselves (id + name + dates), so one added by mistake
    #: can be opened and deleted from the weekly-off card.
    week_offs: list[HolidayRead] = []
    #: Single dates the school reopened although a rule (or a holiday) closes them - the
    #: calendar's "just this one day" override. The grid draws them open, and the same row
    #: lets the day be closed again.
    open_days: list[OpenDayRead] = []
    #: Every closed day of the window, with the words to print ("Sunday", "Diwali break").
    #: The same answer the register's date control reads, so clicking a shaded day can say
    #: *why* it is shut without the screen repeating the rule.
    closed_days: list[ClosedDayRead] = []
    #: Days in the window with a saved register - the daily register's calendar dots.
    marked_dates: list[date] = []
    #: The page's three cards (total / public / vacation days). It rides on **this** read so
    #: a card can never disagree with the list under it and no screen has to make a second
    #: request that could go stale: one window, one answer.
    summary: HolidaySummaryRead | None = None


class HolidaySummaryRead(BaseModel):
    """The three figures on the Calendar page's cards.

    The window is the school's **current session** ("2026-27", 1 Apr - 31 Mar), because "how
    many holidays this year" means the school year, never January's. A school that has not
    opened a session falls back to the calendar year, and `session_label` says which one it is.
    """

    from_date: date
    to_date: date
    #: "2026-27" when the window is a session; empty when it is a plain calendar year.
    session_label: str = ""
    #: Holiday rows in the window - a weekly off is a closure, not a holiday.
    total: int = 0
    public: int = 0
    school: int = 0
    vacation: int = 0
    other: int = 0
    #: Days the vacations cover (a 10-day break is 10, not 1).
    vacation_days: int = 0


class ClosureImpactSectionRead(BaseModel):
    """One class-section that already holds a register on a day being closed."""

    section_id: UUID
    class_name: str
    section_name: str
    #: Children with at least one mark that day.
    students: int = 0
    #: Rows a confirmed delete would remove (one per child per subject).
    records: int = 0


class ClosureImpactDayRead(BaseModel):
    """One day being closed, and the class-sections whose register would go."""

    date: date
    #: Why the day is (or would be) closed, in the calendar's own words.
    reason: str = ""
    #: `weekly_off` / `week_off` / `holiday`.
    kind: str = ""
    total_records: int = 0
    sections: list[ClosureImpactSectionRead] = []


class ClosureImpactRead(BaseModel):
    """The warning before a closure: **what already exists** on the days about to close.

    `total_records == 0` means there is nothing to lose and the closure can be saved at once.
    """

    from_date: date
    to_date: date
    total_records: int = 0
    days: list[ClosureImpactDayRead] = []


class ClosureDeleteWrite(BaseModel):
    """The confirmed delete: which days, and (optionally) which sections only.

    `dates` is the safe form: exactly the days the warning listed. `from_date`/`to_date` say
    "the whole range" and are what a holiday's own range sends.
    """

    from_date: date | None = None
    to_date: date | None = None
    #: The exact days to clear - takes precedence over the range when it is not empty.
    dates: list[date] = []
    #: Empty = every class-section the impact listed.
    section_ids: list[UUID] = []


class ClosureDeleteRead(BaseModel):
    """What a confirmed delete removed - named back, so the toast can say it."""

    deleted_records: int = 0
    deleted_audit_rows: int = 0
    days: list[date] = []


class WeeklyOffRead(BaseModel):
    days: list[int] = []
    #: `"5#1"` = the 1st Saturday of every month, `"5#3"` the third.
    nth: list[str] = []


class WeeklyOffWrite(BaseModel):
    #: An empty list is a real answer: a school that runs seven days a week.
    days: list[int] = []
    #: The Saturday rules. `None` keeps what the school already had.
    nth: list[str] | None = None


class SectionCalendarDayRead(BaseModel):
    """One day of the register's month calendar: closed, saved, or both."""

    date: date
    #: `weekly_off` / `week_off` / `holiday`; `None` on a day a register may be taken.
    closed_kind: str | None = None
    #: The words the toolbar prints for that closed day ("Sunday", "Diwali break").
    closed_reason: str | None = None
    #: A register was saved on this day for this class-section - the calendar's dot.
    saved: bool = False


class SectionCalendarRead(BaseModel):
    """The month the daily register's date control draws."""

    section_id: UUID
    from_date: date
    to_date: date
    days: list[SectionCalendarDayRead] = []


class LateStudentRowRead(BaseModel):
    """One child on the late list: how many late days, and what share of the month."""

    student_id: UUID
    name: str
    late: int
    percent: float


class LateStudentsRead(BaseModel):
    """The last complete month's late list, with everything the card needs to explain it."""

    from_date: date
    to_date: date
    #: "November 2026" - the words the card prints.
    month_label: str
    #: Open days in that month (weekly offs and holidays removed).
    open_days: int = 0
    #: Days of that month with any register row - 0 means "no data", not "nobody late".
    marked_days: int = 0
    #: `attendance.late_share_percent` - the bar a child has to clear.
    threshold: int = 5
    rows: list[LateStudentRowRead] = []


# `HolidayCalendarRead.summary` names `HolidaySummaryRead`, which is declared further down this
# module. Pydantic resolves the string annotation here, once every class exists.
HolidayCalendarRead.model_rebuild()
