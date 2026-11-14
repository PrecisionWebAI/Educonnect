"""The cover board's shapes: the absences, the affected periods, the candidates.

Three rules, each about a claim a screen would otherwise make without evidence:

* **the reason travels with the candidate.** Every candidate carries the words that
  justify offering them ("Teaches Physics; Science department; 18 periods a week"),
  and every *rejected* colleague carries the words that say why not ("On approved
  Sick leave"). A list of names with no reason asks the office to trust a score it
  cannot see;
* **the slot is named in words as well as ids.** `slot` ("09:00-09:45") and
  `class_label` ("Class 10-A") come from the server, because a time and a
  class-section are rendered in four places already and drift when re-typed;
* **an assignment reads as a sentence.** The board returns the substitute's name and
  the status word next to the period, not just a boolean, so the table can print
  "Covered by Rao (Assigned)" instead of a tick.
"""

from datetime import date, datetime, time
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.core.text import CanonicalRequest


class SubstitutionCandidateRead(BaseModel):
    """A colleague the engine offers, with the reason it offers them."""

    employee_id: UUID
    name: str
    employee_code: str | None = None
    department: str | None = None
    #: Always true for an **eligible** candidate: teaching the subject is a hard
    #: filter, not a bonus. It is on the payload so the UI can say so in words.
    teaches_subject: bool = True
    same_department: bool = False
    #: Timetable periods a week - the load the engine weighs.
    weekly_periods: int = 0
    #: Also teaches this class-section, so the children know them.
    knows_the_class: bool = False
    #: A ranking, never a mark out of 100: see `engine.score`.
    score: int = 0
    reason: str


class BlockedCandidateRead(BaseModel):
    """Somebody who teaches the subject but cannot take this slot, and why."""

    employee_id: UUID
    name: str
    reason: str


class SubstitutionAssignmentRead(BaseModel):
    """One cover: the slot, who is away, who stood in, and how far it is signed."""

    id: UUID
    period_id: UUID
    on_date: date
    absent_employee_id: UUID
    absent_name: str
    substitute_employee_id: UUID
    substitute_name: str
    status: str
    status_label: str
    note: str | None = None
    assigned_at: datetime | None = None
    decided_at: datetime | None = None


class SubstitutionAbsenceRead(BaseModel):
    """One reason a timetable needs covering today."""

    employee_id: UUID
    name: str
    employee_code: str | None = None
    department: str | None = None
    reason: str
    #: The leave type when the absence came from an approved leave, else None.
    leave_type: str | None = None
    note: str | None = None
    #: How many periods of theirs that day still have nobody in front of the class.
    open_periods: int = 0
    total_periods: int = 0


class SubstitutionPeriodRead(BaseModel):
    """One period of an absent teacher's day, covered or not."""

    period_id: UUID
    slot: str
    start_time: time
    end_time: time
    subject_id: UUID
    subject: str
    class_label: str
    room: str | None = None
    absent_employee_id: UUID
    absent_name: str
    #: None while the slot is open.
    assignment: SubstitutionAssignmentRead | None = None


class SubstitutionBoardRead(BaseModel):
    """The day's cover sheet: who is away, their periods, and what is still open."""

    on_date: date
    weekday: str
    absences: list[SubstitutionAbsenceRead] = []
    periods: list[SubstitutionPeriodRead] = []
    total: int = 0
    covered: int = 0
    open: int = 0
    #: True when the weekday has no timetable periods at all - Sunday, or a school
    #: that has not built its timetable yet. The screen says which, not "0 open".
    timetable_empty: bool = False


class SubstitutionCandidatesRead(BaseModel):
    """The engine's answer for one period: who can, who cannot, and why."""

    period_id: UUID
    on_date: date
    slot: str
    subject: str
    class_label: str
    candidates: list[SubstitutionCandidateRead] = []
    blocked: list[BlockedCandidateRead] = []
    #: Set when the slot already has a cover - offering candidates would invite a
    #: second assignment the unique key is going to refuse anyway.
    assignment: SubstitutionAssignmentRead | None = None


class SubstitutionAssignIn(CanonicalRequest):
    """Arrange cover for one period.

    `on_date` is sent rather than derived from the period: the same period row is
    every Monday, and the cover is for one particular Monday.
    """

    period_id: UUID
    on_date: date
    absent_employee_id: UUID
    substitute_employee_id: UUID
    note: str | None = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def _nobody_covers_for_themselves(self) -> SubstitutionAssignIn:
        if self.substitute_employee_id == self.absent_employee_id:
            raise ValueError(
                "A person cannot substitute for themselves; choose a colleague."
            )
        return self


class SubstitutionDecisionIn(CanonicalRequest):
    """The principal's note with an approval (or a withdrawal's reason)."""

    note: str | None = Field(default=None, max_length=300)
