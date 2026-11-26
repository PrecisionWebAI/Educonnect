"""The shapes the Teachers & Staff screen reads.

Two rules these schemas follow, because both were broken before:

* a value that may not exist is **optional**, not a stand-in. The old
  `qualification: str` blew up the whole list with a 500 on a single employee
  whose qualification was NULL, and `workload: int = 18` printed an invented
  load for anybody the timetable query missed;
* a field name says what the value is (`status` is the employment state, not the
  login state) and the three statuses are the ones `labels` defines, so the API
  cannot grow a fourth word the badges do not know.
"""

from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.text import CanonicalRequest

from .profile.schemas import (
    CertificationRead,
    DocumentRead,
    ExperienceRead,
    HistoryRead,
    KycRead,
    QualificationRead,
)


class TeacherCreate(CanonicalRequest):
    user_id: UUID
    department: str
    qualification: str | None = None
    joining_date: date


class TeacherRead(BaseModel):
    """One row of the staff directory."""

    id: UUID
    user_id: UUID
    department: str
    #: NULL for the staff who were hired without one - not a reason to fail.
    qualification: str | None = None
    joining_date: date
    #: `employee.employee_code` (`EMP-0043`) - always present on a real employee.
    staffCode: str
    name: str
    #: What this teacher can teach, as the plain text they were hired with ("English,
    #: Maths"). Empty when none is listed - which is a different fact from "their
    #: department" and from the section subjects they take now.
    subjectTags: str = ""
    phone: str
    email: str
    #: `Inactive` (off the roll) / `On Leave` (approved leave today) / `Active`.
    status: Literal["Active", "Inactive", "On Leave"] = "Active"
    #: The class-sections they are attached to (class teacher or subject teacher).
    classes: list[str] = Field(default_factory=list)
    #: Timetable periods a week, from `timetableperiod`.
    workload: int = 0


class PerformanceComponent(BaseModel):
    """One ingredient of the overall score - and **null when there is no data**.

    Three ingredients, each a fact the school already records: the **staff
    register**, the **timetable** and the **chapter plan**. `value` is `None`, not
    `0`, when the school has nothing to judge that component by (no day marked, no
    period on the timetable, no plan written). The screen prints "no data" and the
    score is computed over the components that do exist, with the weights
    renormalised - so an unmarked month cannot quietly punish a teacher.
    """

    key: Literal["attendance", "workload", "course"]
    label: str
    #: 0-100, or None for "no data".
    value: float | None = None
    #: The share this component carries when it has data.
    weight: float = 0.0
    #: What the screen prints under the bar ("96% of marked days", "no data").
    display: str = "no data"


class StaffPerformance(BaseModel):
    """One row of the performance tab: the session, the components and the score.

    `score` is `None` when nothing is known yet - a fabricated 0 would read as a
    failing teacher rather than an empty record. `session` and its two dates travel
    with the row because a percentage without a window is not a fact: the same 80%
    over a month and over a year are different claims.
    """

    id: UUID
    staff: str
    #: Which tab the row belongs to (0.9): staff have no timetable or plan, so those
    #: two components are **absent** rather than 0%.
    kind: Literal["teacher", "staff"] = "teacher"
    #: The session these numbers describe ("2026-27"), from `academic_year`.
    session: str = ""
    session_start: date | None = None
    session_end: date | None = None
    score: int | None = None
    components: list[PerformanceComponent] = Field(default_factory=list)


class StaffSummary(BaseModel):
    """The four tiles above the directory - counted by the database.

    The screen used to derive them from the rows it had loaded, so a capped or
    filtered page silently changed the totals.
    """

    total: int
    active: int
    on_leave_today: int
    inactive: int
    #: Which side of the split these tiles count (0.9).
    kind: Literal["teacher", "staff"] = "teacher"
    #: False for staff: the periods tile is not shown at all, because a staff
    #: member's job has no periods - 0 would read as "unassigned load".
    shows_periods: bool = True
    #: Timetable periods a week across the whole teaching staff (0 for staff).
    periods_per_week: int
    #: Teachers on the roll with no period in the timetable yet (0 for staff).
    without_timetable: int


class StaffProfile(BaseModel):
    """One person, as the profile drawer shows them - identity, post, four lists.

    Snapshot fields (`subjects`, `classes`, `workload`) come from the same reads the
    directory row uses, so a profile opened from the table cannot disagree with the
    row behind it. `capacity` is the timetable's own week, which is what makes
    `utilisation` a comparison of two real numbers.
    """

    id: UUID
    user_id: UUID
    staff_code: str
    name: str
    department: str
    #: NULL until somebody sets it - the profile shows "—", not the department.
    designation: str | None = None
    employment_type: str | None = None
    qualification: str | None = None
    experience_years: int = 0
    joining_date: date
    probation_end: date | None = None
    #: Who they report to, by name (the id is what is stored).
    reports_to: str | None = None
    reports_to_employee_id: UUID | None = None
    phone: str = ""
    email: str = ""
    address: str | None = None
    emergency_contact: str | None = None
    #: `Inactive` / `On Leave` / `Active`, from `labels.employee_status`.
    status: Literal["Active", "Inactive", "On Leave"] = "Active"
    #: What this teacher can teach, as plain text. Informational only.
    subjectTags: str = ""
    classes: list[str] = Field(default_factory=list)
    workload: int = 0
    capacity: int = 0
    utilisation: int = 0
    qualifications: list[QualificationRead] = Field(default_factory=list)
    experiences: list[ExperienceRead] = Field(default_factory=list)
    certifications: list[CertificationRead] = Field(default_factory=list)
    history: list[HistoryRead] = Field(default_factory=list)
    #: The dossier: rows only, never a path or a storage key. `doc_type_label` is
    #: the screen's word for the type, so the drawer carries no second vocabulary.
    documents: list[DocumentRead] = Field(default_factory=list)
    #: Aadhaar / PAN / bank, **masked** unless the caller asked with `reveal` and
    #: holds `teachers.view_kyc`. Always present, so the screen never has to decide
    #: whether a blank means "no record" or "not allowed".
    kyc: KycRead = Field(default_factory=KycRead)
