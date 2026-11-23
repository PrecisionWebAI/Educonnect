"""Promotion-safe tables: class teacher per year and the promotion audit."""

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, Index, UniqueConstraint, text
from sqlmodel import Field, SQLModel

from app.core.ids import UUIDMixin
from app.core.tenancy import TenantMixin
from app.domains.auth.models import utcnow


class ClassTeacherAssignmentBase(SQLModel):
    classroom_id: UUID = Field(foreign_key="classroom.id", index=True)
    academic_year_id: UUID = Field(foreign_key="academic_year.id", index=True)
    teacher_id: UUID = Field(foreign_key="employee.id", index=True)
    effective_from: date = Field(default_factory=date.today)
    effective_to: date | None = None
    assigned_by_user_id: UUID | None = Field(default=None, foreign_key="app_user.id")
    note: str | None = None


class ClassTeacherAssignment(
    ClassTeacherAssignmentBase, TenantMixin, UUIDMixin, table=True
):
    __tablename__ = "classteacherassignment"

    __table_args__ = (
        Index(
            "uq_classteacherassignment_open",
            "school_id",
            "classroom_id",
            "academic_year_id",
            unique=True,
            postgresql_where=text("effective_to IS NULL"),
            sqlite_where=text("effective_to IS NULL"),
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="ck_classteacherassignment_dates",
        ),
    )
    created_at: datetime = Field(default_factory=utcnow)


class PromotionBatchBase(SQLModel):
    from_academic_year_id: UUID = Field(foreign_key="academic_year.id", index=True)
    to_academic_year_id: UUID = Field(foreign_key="academic_year.id", index=True)
    status: str = Field(default="draft", index=True)
    note: str | None = None
    created_by_user_id: UUID | None = Field(default=None, foreign_key="app_user.id")
    applied_by_user_id: UUID | None = Field(default=None, foreign_key="app_user.id")
    applied_at: datetime | None = None


class PromotionBatch(PromotionBatchBase, TenantMixin, UUIDMixin, table=True):
    __tablename__ = "promotionbatch"

    __table_args__ = (
        UniqueConstraint(
            "school_id",
            "from_academic_year_id",
            "to_academic_year_id",
            name="uq_promotionbatch_school_from_to",
        ),
        CheckConstraint(
            "from_academic_year_id <> to_academic_year_id",
            name="ck_promotionbatch_different_years",
        ),
        CheckConstraint(
            "status IN ('draft','applied','cancelled')",
            name="ck_promotionbatch_status",
        ),
    )
    created_at: datetime = Field(default_factory=utcnow)


class PromotionDecisionBase(SQLModel):
    batch_id: UUID = Field(foreign_key="promotionbatch.id", index=True)
    student_id: UUID = Field(foreign_key="student.id", index=True)
    from_enrollment_id: UUID = Field(foreign_key="enrollment.id", index=True)
    decision: str = Field(default="promote")
    to_classroom_id: UUID | None = Field(
        default=None, foreign_key="classroom.id", index=True
    )
    to_enrollment_id: UUID | None = Field(
        default=None, foreign_key="enrollment.id", index=True
    )
    roll_no: str | None = None
    reason: str | None = None
    decided_by_user_id: UUID | None = Field(default=None, foreign_key="app_user.id")
    decided_at: datetime | None = None
    applied_at: datetime | None = None


class PromotionDecision(PromotionDecisionBase, TenantMixin, UUIDMixin, table=True):
    __tablename__ = "promotiondecision"

    __table_args__ = (
        UniqueConstraint(
            "batch_id", "student_id", name="uq_promotiondecision_batch_student"
        ),
        UniqueConstraint("to_enrollment_id", name="uq_promotiondecision_to_enrollment"),
        Index("ix_promotiondecision_batch_decision", "batch_id", "decision"),
        CheckConstraint(
            "decision IN ('promote','repeat','transfer','leave','graduate')",
            name="ck_promotiondecision_decision",
        ),
        CheckConstraint(
            "decision NOT IN ('promote','repeat') OR to_classroom_id IS NOT NULL",
            name="ck_promotiondecision_target_required",
        ),
        CheckConstraint(
            "decision IN ('promote','repeat') OR to_classroom_id IS NULL",
            name="ck_promotiondecision_target_forbidden",
        ),
    )
