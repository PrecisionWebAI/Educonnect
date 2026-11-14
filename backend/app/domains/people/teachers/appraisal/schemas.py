"""The appraisal shapes: the window, one person's appraisal, its goals, training.

Three choices worth knowing:

* **the rating is 1..5 and nothing else.** A free-text "grade" is a number the school
  cannot average, and a percentage with no rubric is one it cannot defend. The words
  live in `self_note` / `reviewer_note`, where they belong;
* **`achieved` is `bool | None`.** A goal nobody has judged is *unjudged*, not
  failed - the same `null`-is-not-zero rule the leave balance follows;
* **a goal travels inside the self-assessment.** The person writes their goals and
  their rating in one call, so a half-saved appraisal cannot exist.
"""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.text import CanonicalRequest

CycleStatus = Literal["Draft", "Open", "Closed"]


class CycleIn(CanonicalRequest):
    name: str = Field(min_length=3, max_length=80)
    start_date: date
    end_date: date
    note: str | None = Field(default=None, max_length=300)


class CycleStatusIn(CanonicalRequest):
    status: CycleStatus


class CycleRead(BaseModel):
    id: UUID
    name: str
    start_date: date
    end_date: date
    status: str
    note: str | None = None
    #: How many people the cycle covers, and how far the season has got.
    appraisals: int = 0
    submitted: int = 0
    finalized: int = 0


class GoalIn(CanonicalRequest):
    title: str = Field(min_length=3, max_length=160)
    target: str | None = Field(default=None, max_length=200)
    weight: int = Field(default=1, ge=1, le=10)


class GoalRead(BaseModel):
    id: UUID
    title: str
    target: str | None = None
    achieved: bool | None = None
    weight: int = 1


class GoalVerdictIn(CanonicalRequest):
    achieved: bool


class SelfAssessmentIn(CanonicalRequest):
    """What the person says about their own year - rating, note and goals, together."""

    self_rating: int = Field(ge=1, le=5)
    self_note: str | None = Field(default=None, max_length=2000)
    #: The goals they are being appraised against. Sending a list **replaces** it:
    #: a goal removed from the form is a goal they no longer claim.
    goals: list[GoalIn] = Field(default_factory=list, max_length=20)


class ReviewIn(CanonicalRequest):
    reviewer_rating: int = Field(ge=1, le=5)
    reviewer_note: str | None = Field(default=None, max_length=2000)


class AppraisalRead(BaseModel):
    id: UUID
    cycle_id: UUID
    cycle_name: str
    employee_id: UUID
    employee_code: str
    name: str
    department: str | None = None
    status: str
    status_label: str
    self_rating: int | None = None
    self_note: str | None = None
    reviewer_rating: int | None = None
    reviewer_note: str | None = None
    reviewer_name: str | None = None
    submitted_at: datetime | None = None
    reviewed_at: datetime | None = None
    finalized_at: datetime | None = None
    goals: list[GoalRead] = []
    #: What the goals add up to, so a screen does not have to count them itself:
    #: `judged` of `total` goals decided, and how many were achieved.
    goals_total: int = 0
    goals_judged: int = 0
    goals_achieved: int = 0


class QueueRead(BaseModel):
    cycle: CycleRead
    rows: list[AppraisalRead] = []
    total: int = 0
    #: The caller's own appraisal in this cycle, when they have one - the queue and
    #: "my appraisal" are two questions about the same season.
    mine: AppraisalRead | None = None


class TrainingIn(CanonicalRequest):
    title: str = Field(min_length=3, max_length=160)
    provider: str | None = Field(default=None, max_length=120)
    on_date: date
    hours: int = Field(default=0, ge=0, le=200)
    note: str | None = Field(default=None, max_length=300)


class TrainingRead(BaseModel):
    id: UUID
    employee_id: UUID
    title: str
    provider: str | None = None
    on_date: date
    hours: int = 0
    note: str | None = None
