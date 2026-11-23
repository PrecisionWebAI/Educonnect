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


class PromoteIn(SQLModel):
    """Students to promote; `target_class_id` omitted means "the next class"."""

    student_ids: list[UUID]
    target_class_id: UUID | None = None
    #: A section letter ("A" - "J") in the target class; omitted keeps the child's own
    #: section letter (or the class's first section when that letter does not exist).
    target_section: str | None = None


class DemoteIn(SQLModel):
    """Students to move one class down, into this section letter ("A" - "J")."""

    student_ids: list[UUID]
    target_section: str


class UndoIn(SQLModel):
    student_ids: list[UUID]
    #: True once the caller has seen the counts that `undo/preview` returned.
    confirm: bool = False


class StudentIdsIn(SQLModel):
    student_ids: list[UUID]


class DepromoteIn(SQLModel):
    student_ids: list[UUID]
    #: True once the caller has seen `DepromotePreviewRead` and agreed to the deletion.
    confirm: bool = False


class PromotionSkippedRead(SQLModel):
    student_id: UUID
    name: str
    reason: str


class PromotionResultRead(SQLModel):
    done: int
    skipped: list[PromotionSkippedRead] = []


class DepromoteStudentRead(SQLModel):
    student_id: UUID
    name: str
    attendance: int = 0
    fees: int = 0
    marks: int = 0


class DepromotePreviewRead(SQLModel):
    """What de-promoting deletes: counts per student and in total."""

    students: list[DepromoteStudentRead] = []
    attendance: int = 0
    fees: int = 0
    marks: int = 0
    skipped: list[PromotionSkippedRead] = []
