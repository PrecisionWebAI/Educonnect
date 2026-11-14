"""The three leave tables: the request, the school's policy, one person's override.

A student leave and a staff leave are the same request -> approve/reject flow, so
they share `leaverequest`: `student_id` is set for a student and NULL for a staff
member. `leave_type` and `status` are plain text because the screen shows the words
that were chosen ("Medical", "Pending") rather than mapping enum names.

What is deliberately **not** a stored counter:

* `leavepolicy` says how many days a type grants in a year;
* `leavebalance` holds an **override** - the extra days one person was granted, or
  a figure that differs from the policy. It is not a running total;
* the days **used** are derived from the approved `leaverequest` rows.

A `remaining` column would have to be incremented on approval, decremented on
cancellation, re-checked on rejection and repaired by hand the first time a leave
was edited - four chances for the number and the requests to disagree, with no way
to tell which is right. Deriving costs one `SUM` and cannot drift.

Tenant-scoped (`TenantMixin`) like every other school-owned table.
"""

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, Index, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.ids import UUIDMixin
from app.core.tenancy import TenantMixin
from app.domains.auth.models import utcnow


class LeaveRequestBase(SQLModel):
    #: Set for a student leave, NULL for a staff leave.
    student_id: UUID | None = Field(default=None, foreign_key="student.id")
    #: Set for a staff leave, NULL for a student leave. The two are mutually
    #: exclusive and the request must name exactly one - `ck_leaverequest_one_subject`
    #: refuses a row that names both or neither, so "who is this leave about?" can
    #: never be answered two ways for the same row.
    employee_id: UUID | None = Field(
        default=None, foreign_key="employee.id", index=True
    )
    #: The person who filed it (the guardian/student for a student leave, the
    #: staff member for a staff leave).
    requester_user_id: UUID = Field(foreign_key="app_user.id")
    leave_type: str  # "Medical" / "Personal" / "Casual" / "Sick" / "Earned" / "OD"
    #: The school's own `leavetype` row this request belongs to. `leave_type` (the
    #: words) stays as the request was filed with; the id is what a balance and a
    #: filter group by, so renaming a type does not orphan history. NULL for rows
    #: filed before the master existed and for a type the school has since removed.
    leave_type_id: UUID | None = Field(default=None, foreign_key="leavetype.id")
    from_date: date
    to_date: date
    days: int
    #: A half-day request: `days` is still the calendar count of the range, and the
    #: register treats the requested day as half spent. Stored so an approver can see
    #: what was asked for instead of guessing from a 0.5 total that `days` cannot hold.
    half_day: bool = Field(default=False)
    reason: str | None = None
    status: str = Field(default="Pending")  # "Pending" / "Approved" / "Rejected"


class LeaveRequest(LeaveRequestBase, TenantMixin, UUIDMixin, table=True):
    """The request, plus the decision (Phase 6) and the two reads it must be fast for.

    Two indexes, because two questions are asked of this table on every screen:

    * **"who is on leave on this day?"** - the register, the directory's `On Leave`
      badge and the substitute engine all ask it for the whole school, and the
      answer is a range test (`from_date <= day <= to_date`) on the approved rows.
      Without `ix_leaverequest_school_status_window` PostgreSQL reads every leave
      the school ever filed.
    * **"how many days has this person taken?"** - one person's month sheet and the
      balance `SUM` ask it for one `requester_user_id`, which
      `ix_leaverequest_school_requester_status` answers without touching the rest.
    """

    __table_args__ = (
        Index(
            "ix_leaverequest_school_status_window",
            "school_id",
            "status",
            "from_date",
        ),
        Index(
            "ix_leaverequest_school_requester_status",
            "school_id",
            "requester_user_id",
            "status",
        ),
        #: The two tabs (0.10): a staff row has an `employee_id`, a student row has a
        #: `student_id`, and exactly one of them is set. Staff requests filed before
        #: this column existed are backfilled from `requester_user_id` by the Phase 2
        #: migration, so the rule holds for old rows too.
        CheckConstraint(
            "(student_id IS NULL) <> (employee_id IS NULL)",
            name="ck_leaverequest_one_subject",
        ),
    )

    created_at: datetime = Field(default_factory=utcnow)

    # --- the decision (Phase 6) -------------------------------------------
    #: Who approved, rejected or cancelled it. NULL while it is pending, and NULL
    #: for every row filed before this phase.
    decided_by_user_id: UUID | None = Field(default=None, foreign_key="app_user.id")
    #: When it happened - so the screen can print "Approved 2026/11/09 10:12"
    #: instead of only "Approved".
    decided_at: datetime | None = None
    #: The office's words with the decision ("half pay", "clashes with the exam").
    #: Prose, so it keeps its case.
    decision_note: str | None = None


class LeaveType(TenantMixin, UUIDMixin, table=True):
    """The school's own list of leave types - what the two tabs offer and what a
    balance is grouped by.

    A master row rather than a constant because the screens already disagree on the
    words: a staff policy has `Casual` / `Sick` / `Earned`, the student form has
    `Medical` / `OD` / `Event`. `applies_to` says which tab may pick the type, so a
    school can add "Bereavement" for staff without it appearing on a child's form.

    `UNIQUE(school_id, name)` keeps one row per spelling inside a school; two
    schools may each have their own `Casual`.
    """

    __table_args__ = (
        UniqueConstraint("school_id", "name", name="uq_leavetype_school_name"),
    )

    #: The words the screen prints ("Casual", "Medical"). Stored, not translated.
    name: str = Field(index=True)
    #: `staff` / `student` / `both` - which leave screen may offer this type.
    applies_to: str = Field(default="both")
    #: Retired types stay (requests point at them); they just leave the picker.
    is_active: bool = Field(default=True)
    #: Sort position in the picker; ties fall back to the name.
    sort_order: int = Field(default=0)
    created_at: datetime = Field(default_factory=utcnow)


class LeavePolicy(TenantMixin, UUIDMixin, table=True):
    """How many days of one leave type a school grants in a year.

    `UNIQUE(school_id, leave_type)` is enforced by PostgreSQL (both columns NOT
    NULL), so a second policy for the same type cannot be created by two
    administrators saving the same screen at the same moment.

    `annual_days = 0` is a real, useful value: it says "this type exists but grants
    nothing", which is how a school retires a type without deleting the requests
    that mention it.
    """

    __table_args__ = (
        UniqueConstraint("school_id", "leave_type", name="uq_leavepolicy_school_type"),
    )

    leave_type: str
    annual_days: int
    #: Who last set it. The row is school-level, not a person's record, so this is
    #: the only trail it carries (`staffauditlog.employee_id` is NOT NULL).
    updated_by_user_id: UUID | None = Field(default=None, foreign_key="app_user.id")
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class LeaveBalance(TenantMixin, UUIDMixin, table=True):
    """One person's **override** for one leave type in one year.

    Not a counter: days used are summed from the approved requests every time a
    balance is read (see the module docstring).

    `UNIQUE(school_id, employee_id, leave_type, year)` - all four NOT NULL, so one
    person cannot end up with two overrides that disagree about the same year.
    """

    __table_args__ = (
        UniqueConstraint(
            "school_id",
            "employee_id",
            "leave_type",
            "year",
            name="uq_leavebalance_employee_type_year",
        ),
    )

    employee_id: UUID = Field(foreign_key="employee.id", index=True)
    leave_type: str
    #: The `academic_year` row this balance belongs to. `year` (the calendar number)
    #: stays for the current one-year-per-January rule; the id is what ties a balance
    #: to a school year that does not start in January. NULL on rows written before
    #: the academic-year table existed.
    academic_year_id: UUID | None = Field(
        default=None, foreign_key="academic_year.id", index=True
    )
    #: The balance year (`labels.leave_year(from_date)`).
    year: int
    #: The entitlement this person has **instead of** the policy's number.
    entitled_days: int
    #: Why it differs ("joined mid-year", "carried forward 4 days").
    note: str | None = None
    updated_by_user_id: UUID | None = Field(default=None, foreign_key="app_user.id")
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
