"""Request/response shapes for promotion batches and class-teacher history."""

from datetime import date, datetime
from uuid import UUID

from sqlmodel import Field, SQLModel


class PromotionBatchCreate(SQLModel):
    from_academic_year_id: UUID
    to_academic_year_id: UUID
    note: str | None = None


class PromotionDecisionWrite(SQLModel):
    student_id: UUID
    decision: str = Field(default="promote")
    to_classroom_id: UUID | None = None
    roll_no: str | None = None
    reason: str | None = None


class PromotionDecisionRead(SQLModel):
    id: UUID
    batch_id: UUID
    student_id: UUID
    from_enrollment_id: UUID
    decision: str
    to_classroom_id: UUID | None = None
    to_enrollment_id: UUID | None = None
    roll_no: str | None = None
    reason: str | None = None
    decided_at: datetime | None = None
    applied_at: datetime | None = None


class PromotionBatchRead(SQLModel):
    id: UUID
    from_academic_year_id: UUID
    to_academic_year_id: UUID
    status: str
    note: str | None = None
    applied_at: datetime | None = None
    created_at: datetime
    decisions: list[PromotionDecisionRead] = Field(default_factory=list)


class PromotionApplyResult(SQLModel):
    batch_id: UUID
    status: str
    applied: int
    skipped: int
    errors: list[str] = Field(default_factory=list)


class ClassTeacherAssignmentRead(SQLModel):
    id: UUID
    classroom_id: UUID
    academic_year_id: UUID
    teacher_id: UUID
    effective_from: date
    effective_to: date | None = None
    note: str | None = None


class ClassTeacherAssignmentWrite(SQLModel):
    classroom_id: UUID
    academic_year_id: UUID
    teacher_id: UUID
    effective_from: date | None = None
    note: str | None = None
