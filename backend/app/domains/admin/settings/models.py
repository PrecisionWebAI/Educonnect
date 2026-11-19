"""The Settings screen's own rows: the security log and the gateway statuses.

Both are read-only lists the school keeps for itself; the users table and the
school's own details are read from the real `app_user` / `school` tables instead
(see `service.py`), so there is nothing to duplicate here.

Phase 2 adds the three **school-wide masters** the teachers screens ask about:
`academic_year` (which session a plan/balance belongs to), `holiday` (the calendar
a leave is counted against) and `department` (the row behind the free-text
`employee.department`, so a filter can list the departments a school actually has).
"""

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.ids import UUIDMixin
from app.core.tenancy import TenantMixin
from app.domains.auth.models import utcnow


class SecurityLogBase(SQLModel):
    event: str
    #: Who the event is about - the login/email the screen prints. It used to be called
    #: `user`, a reserved word that had to be quoted at every use (Rule 6).
    actor_email: str
    #: When it happened, as the words the screen shows ("Today, 09:12"). It used to be
    #: called `when` - a keyword, and not a type either.
    occurred_at: str


class SecurityLog(SecurityLogBase, TenantMixin, UUIDMixin, table=True):
    pass


class GatewayStatusBase(SQLModel):
    name: str
    type: str
    status: str
    quota: str


class GatewayStatus(GatewayStatusBase, TenantMixin, UUIDMixin, table=True):
    pass


class AcademicYearBase(SQLModel):
    """One school session: "2026-27", from April to March.

    Stored rather than derived from the calendar because an Indian school year
    straddles two calendar years, and a plan/balance that says "this year" has to
    mean the school's year, not January's.

    `is_current` is a flag and not "the row with the latest start date": a school
    opens next year's dates in advance, and the screens must keep showing the year
    that is actually running. `UNIQUE(school_id, name)` stops the same session being
    opened twice; a partial unique index (`uq_academicyear_one_current`) makes sure
    at most one row per school can be current.
    """

    #: "2026-27" - the words the school prints.
    name: str = Field(index=True)
    start_date: date
    end_date: date
    #: True for the session the screens treat as "now". At most one per school.
    is_current: bool = Field(default=False)


class AcademicYear(AcademicYearBase, TenantMixin, UUIDMixin, table=True):
    __tablename__ = "academic_year"

    __table_args__ = (
        UniqueConstraint("school_id", "name", name="uq_academicyear_school_name"),
        CheckConstraint("end_date >= start_date", name="ck_academicyear_dates"),
    )

    created_at: datetime = Field(default_factory=utcnow)


class HolidayBase(SQLModel):
    """A day the school is closed - the calendar a leave is counted against.

    Until this table existed `labels.days_between` counted every calendar day and
    said so on screen. Now a leave's **working days** exclude the rows here, which
    is the difference between "four days" and "four days, two of them a weekend
    and one Diwali".

    `UNIQUE(school_id, on_date)` - one holiday per day per school. Two rows for the
    same date would make the day-count depend on which row a query happened to
    read. The column is called `on_date`, like `staffduty.on_date`, because a field
    named `date` with the type `date` is a pydantic clash.
    """

    on_date: date = Field(index=True)
    name: str
    #: `public` / `festival` / `vacation` / `local` - the screen groups by this.
    kind: str = Field(default="public")
    #: The session this holiday belongs to, when the school has the master rows.
    academic_year_id: UUID | None = Field(
        default=None, foreign_key="academic_year.id", index=True
    )
    #: The last day of a holiday **range** (`on_date` .. `end_date`). Empty for a
    #: single day, so one row can say "winter break, 24 Dec - 2 Jan" instead of nine
    #: rows that each have to be edited when the school extends the break.
    end_date: date | None = Field(default=None)
    #: Who added it. The calendar prints a name next to each holiday, and "who
    #: declared this" is the question a disputed holiday actually raises.
    created_by_id: UUID | None = Field(
        default=None, foreign_key="app_user.id", index=True
    )


class Holiday(HolidayBase, TenantMixin, UUIDMixin, table=True):
    __tablename__ = "holiday"

    __table_args__ = (
        UniqueConstraint("school_id", "on_date", name="uq_holiday_school_date"),
    )


class OpenDayBase(SQLModel):
    """**One date** the school reopened although a rule closes it.

    A weekly off (every Sunday, "the 2nd Saturday") and a holiday row close a day for the
    whole school. Sometimes the school opens on one of those days anyway - an exam, a
    make-up class - and the calendar has to say so without unsaving the rule: toggling
    "Sunday off" off and on again would reopen every Sunday of the year.

    So the override is a row of its own, one date at a time, and it **wins over every other
    answer** (`admin/settings/calendar.closures`). `UNIQUE (school_id, on_date)` keeps the
    question single-answer, exactly like `holiday`.
    """

    on_date: date = Field(index=True)
    #: Who opened it - the question "who said school is open on a Sunday" gets an answer.
    created_by_id: UUID | None = Field(
        default=None, foreign_key="app_user.id", index=True
    )


class OpenDay(OpenDayBase, TenantMixin, UUIDMixin, table=True):
    __tablename__ = "school_open_day"

    __table_args__ = (
        UniqueConstraint("school_id", "on_date", name="uq_open_day_school_date"),
    )


class SchoolSettingBase(SQLModel):
    """One policy number/word a school sets for itself.

    Why a table instead of constants: "below 75% is a concern", "three absences in a
    row is a pattern", "remind the class at 18:00" are the **school's** decisions, not
    facts about the code. A constant would make a second school's 80% a code change.

    `key` is dotted and stable (`attendance.absence_threshold`); `value` is text
    because the same table holds a number, a time and a word - `values.get_int`
    reads the numeric ones and falls back to the default when a row holds nonsense.
    """

    key: str = Field(index=True)
    value: str


class SchoolSetting(SchoolSettingBase, TenantMixin, UUIDMixin, table=True):
    """`UNIQUE(school_id, key)` - one answer per question per school."""

    __tablename__ = "school_setting"

    __table_args__ = (
        UniqueConstraint("school_id", "key", name="uq_school_setting_school_key"),
    )

    updated_at: datetime = Field(default_factory=utcnow)


class DepartmentBase(SQLModel):
    """A department a school actually runs ("Science", "Administration").

    `employee.department` stays as the words that were typed - it is printed on the
    profile and every existing filter reads it. This master is the list behind the
    picker and the HOD's scope, and `employee.department_id` is the link. The text
    column is **not** dropped: a rename in the master must not rewrite history, and
    a value nobody has mapped yet must still be visible.
    """

    name: str = Field(index=True)
    #: Short code the office uses ("SCI", "ADMIN"). Optional.
    code: str | None = None
    #: Retired departments stay (employees point at them); they leave the picker.
    is_active: bool = Field(default=True)


class Department(DepartmentBase, TenantMixin, UUIDMixin, table=True):
    __tablename__ = "department"

    __table_args__ = (
        UniqueConstraint("school_id", "name", name="uq_department_school_name"),
    )
