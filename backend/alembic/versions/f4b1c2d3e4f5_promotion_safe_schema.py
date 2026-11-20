"""Promotion-safe history: enrollment chain, class teacher per year, batches.

Revision ID: f4b1c2d3e4f5
Revises: e2b8c4f7a1d9
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f4b1c2d3e4f5"
down_revision: str | Sequence[str] | None = "e2b8c4f7a1d9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _columns(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table)}


def upgrade() -> None:
    tables = _tables()
    if "enrollment" in tables:
        columns = _columns("enrollment")
        if "previous_enrollment_id" not in columns:
            op.add_column(
                "enrollment",
                sa.Column("previous_enrollment_id", sa.Uuid(), nullable=True),
            )
            op.create_foreign_key(
                "fk_enrollment_previous_enrollment",
                "enrollment",
                "enrollment",
                ["previous_enrollment_id"],
                ["id"],
            )
            op.create_index(
                "ix_enrollment_previous_enrollment_id",
                "enrollment",
                ["previous_enrollment_id"],
            )
        if "created_at" not in columns:
            op.add_column(
                "enrollment",
                sa.Column(
                    "created_at",
                    sa.DateTime(timezone=True),
                    server_default=sa.text("CURRENT_TIMESTAMP"),
                    nullable=False,
                ),
            )
        if "updated_at" not in columns:
            op.add_column(
                "enrollment",
                sa.Column(
                    "updated_at",
                    sa.DateTime(timezone=True),
                    server_default=sa.text("CURRENT_TIMESTAMP"),
                    nullable=False,
                ),
            )

    if "student" in tables and "separation_academic_year_id" not in _columns("student"):
        op.add_column(
            "student",
            sa.Column("separation_academic_year_id", sa.Uuid(), nullable=True),
        )
        op.create_foreign_key(
            "fk_student_separation_academic_year",
            "student",
            "academic_year",
            ["separation_academic_year_id"],
            ["id"],
        )
        op.create_index(
            "ix_student_separation_academic_year_id",
            "student",
            ["separation_academic_year_id"],
        )

    if "classteacherassignment" not in tables:
        op.create_table(
            "classteacherassignment",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("school_id", sa.Uuid(), sa.ForeignKey("school.id"), nullable=False),
            sa.Column("classroom_id", sa.Uuid(), nullable=False),
            sa.Column("academic_year_id", sa.Uuid(), nullable=False),
            sa.Column("teacher_id", sa.Uuid(), nullable=False),
            sa.Column("effective_from", sa.Date(), nullable=False),
            sa.Column("effective_to", sa.Date(), nullable=True),
            sa.Column("assigned_by_user_id", sa.Uuid(), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["classroom_id"], ["classroom.id"]),
            sa.ForeignKeyConstraint(["academic_year_id"], ["academic_year.id"]),
            sa.ForeignKeyConstraint(["teacher_id"], ["employee.id"]),
            sa.ForeignKeyConstraint(["assigned_by_user_id"], ["app_user.id"]),
            sa.ForeignKeyConstraint(["school_id"], ["school.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.CheckConstraint(
                "effective_to IS NULL OR effective_to >= effective_from",
                name="ck_classteacherassignment_dates",
            ),
        )
        op.create_index(
            "uq_classteacherassignment_open",
            "classteacherassignment",
            ["school_id", "classroom_id", "academic_year_id"],
            unique=True,
            postgresql_where=sa.text("effective_to IS NULL"),
            sqlite_where=sa.text("effective_to IS NULL"),
        )
        op.create_index(
            "ix_classteacherassignment_classroom_id",
            "classteacherassignment",
            ["classroom_id"],
        )
        op.create_index(
            "ix_classteacherassignment_academic_year_id",
            "classteacherassignment",
            ["academic_year_id"],
        )
        op.create_index(
            "ix_classteacherassignment_teacher_id",
            "classteacherassignment",
            ["teacher_id"],
        )

    if "promotionbatch" not in tables:
        op.create_table(
            "promotionbatch",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("school_id", sa.Uuid(), sa.ForeignKey("school.id"), nullable=False),
            sa.Column("from_academic_year_id", sa.Uuid(), nullable=False),
            sa.Column("to_academic_year_id", sa.Uuid(), nullable=False),
            sa.Column("status", sa.String(), server_default="draft", nullable=False),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
            sa.Column("applied_by_user_id", sa.Uuid(), nullable=True),
            sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["school_id"], ["school.id"]),
            sa.ForeignKeyConstraint(
                ["from_academic_year_id"], ["academic_year.id"]
            ),
            sa.ForeignKeyConstraint(["to_academic_year_id"], ["academic_year.id"]),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["app_user.id"]),
            sa.ForeignKeyConstraint(["applied_by_user_id"], ["app_user.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "school_id",
                "from_academic_year_id",
                "to_academic_year_id",
                name="uq_promotionbatch_school_from_to",
            ),
            sa.CheckConstraint(
                "from_academic_year_id <> to_academic_year_id",
                name="ck_promotionbatch_different_years",
            ),
            sa.CheckConstraint(
                "status IN ('draft','applied','cancelled')",
                name="ck_promotionbatch_status",
            ),
        )
        op.create_index(
            "ix_promotionbatch_from_academic_year_id",
            "promotionbatch",
            ["from_academic_year_id"],
        )
        op.create_index(
            "ix_promotionbatch_to_academic_year_id",
            "promotionbatch",
            ["to_academic_year_id"],
        )
        op.create_index("ix_promotionbatch_status", "promotionbatch", ["status"])

    if "promotiondecision" not in tables:
        op.create_table(
            "promotiondecision",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("school_id", sa.Uuid(), sa.ForeignKey("school.id"), nullable=False),
            sa.Column("batch_id", sa.Uuid(), nullable=False),
            sa.Column("student_id", sa.Uuid(), nullable=False),
            sa.Column("from_enrollment_id", sa.Uuid(), nullable=False),
            sa.Column("decision", sa.String(), nullable=False),
            sa.Column("to_classroom_id", sa.Uuid(), nullable=True),
            sa.Column("to_enrollment_id", sa.Uuid(), nullable=True),
            sa.Column("roll_no", sa.String(), nullable=True),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("decided_by_user_id", sa.Uuid(), nullable=True),
            sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["school_id"], ["school.id"]),
            sa.ForeignKeyConstraint(["batch_id"], ["promotionbatch.id"]),
            sa.ForeignKeyConstraint(["student_id"], ["student.id"]),
            sa.ForeignKeyConstraint(["from_enrollment_id"], ["enrollment.id"]),
            sa.ForeignKeyConstraint(["to_classroom_id"], ["classroom.id"]),
            sa.ForeignKeyConstraint(["to_enrollment_id"], ["enrollment.id"]),
            sa.ForeignKeyConstraint(["decided_by_user_id"], ["app_user.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "batch_id", "student_id", name="uq_promotiondecision_batch_student"
            ),
            sa.UniqueConstraint(
                "to_enrollment_id", name="uq_promotiondecision_to_enrollment"
            ),
            sa.CheckConstraint(
                "decision IN ('promote','repeat','transfer','leave','graduate')",
                name="ck_promotiondecision_decision",
            ),
            sa.CheckConstraint(
                "decision NOT IN ('promote','repeat') OR to_classroom_id IS NOT NULL",
                name="ck_promotiondecision_target_required",
            ),
            sa.CheckConstraint(
                "decision IN ('promote','repeat') OR to_classroom_id IS NULL",
                name="ck_promotiondecision_target_forbidden",
            ),
        )
        op.create_index(
            "ix_promotiondecision_batch_id", "promotiondecision", ["batch_id"]
        )
        op.create_index(
            "ix_promotiondecision_student_id", "promotiondecision", ["student_id"]
        )
        op.create_index(
            "ix_promotiondecision_from_enrollment_id",
            "promotiondecision",
            ["from_enrollment_id"],
        )
        op.create_index(
            "ix_promotiondecision_to_classroom_id",
            "promotiondecision",
            ["to_classroom_id"],
        )
        op.create_index(
            "ix_promotiondecision_batch_decision",
            "promotiondecision",
            ["batch_id", "decision"],
        )


def downgrade() -> None:
    tables = _tables()
    if "promotiondecision" in tables:
        op.drop_table("promotiondecision")
    if "promotionbatch" in tables:
        op.drop_table("promotionbatch")
    if "classteacherassignment" in tables:
        op.drop_table("classteacherassignment")
    student_columns = _columns("student")
    if "separation_academic_year_id" in student_columns:
        op.drop_index(
            "ix_student_separation_academic_year_id", table_name="student"
        )
        op.drop_constraint(
            "fk_student_separation_academic_year", "student", type_="foreignkey"
        )
        op.drop_column("student", "separation_academic_year_id")
    columns = _columns("enrollment")
    if "previous_enrollment_id" in columns:
        op.drop_index("ix_enrollment_previous_enrollment_id", table_name="enrollment")
        op.drop_constraint(
            "fk_enrollment_previous_enrollment", "enrollment", type_="foreignkey"
        )
        op.drop_column("enrollment", "previous_enrollment_id")
    if "updated_at" in columns:
        op.drop_column("enrollment", "updated_at")
    if "created_at" in columns:
        op.drop_column("enrollment", "created_at")
