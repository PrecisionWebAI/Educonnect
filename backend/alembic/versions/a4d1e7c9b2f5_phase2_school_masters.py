"""Phase 2 (1/3): the school-wide masters - `academic_year`, `holiday`,
`department`, `enrollment`, and the `employee.department_id` link.

Why these three first
---------------------
The rest of Phase 2 points at them: `leavebalance.academic_year_id`,
`syllabusprogress.academic_year_id`, `holiday.academic_year_id` and
`enrollment.academic_year_id` all need the row to exist before a foreign key can be
added. `department` is first for the same reason - `employee.department_id` is the
link the picker and the HOD scope read.

`employee.department` (the text) is **not dropped**: it is what the profile prints
and what every existing filter compares against. This revision only adds the master
row and the id, and backfills the id from the distinct text values the school
already uses - so a filter can start listing real departments without a school
having to re-type anything.

`enrollment` is a **stub**: the table and the minimum columns a promotion/history
screen will need. Nothing reads it yet, and no existing row is touched.

All four tables are tenant-scoped (`school_id` nullable, filled by `before_flush`)
like every other school-owned table, and every unique key includes `school_id` so
two schools may each have "2026-27", "Science" or a holiday on the same date.

Revision ID: a4d1e7c9b2f5
Revises: f2c7a4e9b6d1
Create Date: 2026-11-14
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a4d1e7c9b2f5"
down_revision: str | Sequence[str] | None = "f2c7a4e9b6d1"
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
    names = _tables()

    # --- academic_year ------------------------------------------------------
    if "academic_year" not in names:
        op.create_table(
            "academic_year",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("school_id", sa.Uuid(), nullable=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("start_date", sa.Date(), nullable=False),
            sa.Column("end_date", sa.Date(), nullable=False),
            sa.Column("is_current", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["school_id"], ["school.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "school_id", "name", name="uq_academicyear_school_name"
            ),
            sa.CheckConstraint("end_date >= start_date", name="ck_academicyear_dates"),
        )
        op.create_index("ix_academic_year_school_id", "academic_year", ["school_id"])
        op.create_index("ix_academic_year_name", "academic_year", ["name"])

    # --- department ---------------------------------------------------------
    if "department" not in names:
        op.create_table(
            "department",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("school_id", sa.Uuid(), nullable=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("code", sa.String(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.ForeignKeyConstraint(["school_id"], ["school.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("school_id", "name", name="uq_department_school_name"),
        )
        op.create_index("ix_department_school_id", "department", ["school_id"])
        op.create_index("ix_department_name", "department", ["name"])

    # --- holiday ------------------------------------------------------------
    if "holiday" not in names:
        op.create_table(
            "holiday",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("school_id", sa.Uuid(), nullable=True),
            sa.Column("on_date", sa.Date(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("kind", sa.String(), nullable=False),
            sa.Column("academic_year_id", sa.Uuid(), nullable=True),
            sa.ForeignKeyConstraint(["school_id"], ["school.id"]),
            sa.ForeignKeyConstraint(["academic_year_id"], ["academic_year.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("school_id", "on_date", name="uq_holiday_school_date"),
        )
        op.create_index("ix_holiday_school_id", "holiday", ["school_id"])
        op.create_index("ix_holiday_on_date", "holiday", ["on_date"])
        op.create_index("ix_holiday_academic_year_id", "holiday", ["academic_year_id"])


    # --- employee.department_id (the text column stays) ---------------------
    if "department_id" not in _columns("employee"):
        op.add_column("employee", sa.Column("department_id", sa.Uuid(), nullable=True))
        op.create_foreign_key(
            "fk_employee_department_id",
            "employee",
            "department",
            ["department_id"],
            ["id"],
        )
        op.create_index("ix_employee_department_id", "employee", ["department_id"])

    # Backfill: one `department` row per (school, distinct text), then the link.
    # `DISTINCT ON (... lower(btrim(department)))` is what dedupes: a plain
    # `SELECT DISTINCT` cannot, because `gen_random_uuid()` is volatile and makes
    # every row unique. The `NOT EXISTS` keeps this re-runnable.
    op.execute(
        """
        INSERT INTO department (id, school_id, name, is_active)
        SELECT gen_random_uuid(), x.school_id, x.name, true
        FROM (
            SELECT DISTINCT ON (e.school_id, lower(btrim(e.department)))
                   e.school_id, btrim(e.department) AS name
            FROM employee e
            WHERE e.school_id IS NOT NULL
              AND e.department IS NOT NULL
              AND btrim(e.department) <> ''
            ORDER BY e.school_id, lower(btrim(e.department)), btrim(e.department)
        ) AS x
        WHERE NOT EXISTS (
            SELECT 1 FROM department d
            WHERE d.school_id = x.school_id AND lower(d.name) = lower(x.name)
        )
        """
    )
    op.execute(
        """
        UPDATE employee e
        SET department_id = d.id
        FROM department d
        WHERE e.department_id IS NULL
          AND d.school_id = e.school_id
          AND lower(d.name) = lower(btrim(e.department))
        """
    )

    # --- enrollment (stub) --------------------------------------------------
    if "enrollment" not in names:
        op.create_table(
            "enrollment",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("school_id", sa.Uuid(), nullable=True),
            sa.Column("student_id", sa.Uuid(), nullable=False),
            sa.Column("classroom_id", sa.Uuid(), nullable=False),
            sa.Column("academic_year_id", sa.Uuid(), nullable=False),
            sa.Column("roll_no", sa.String(), nullable=True),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("joined_on", sa.Date(), nullable=True),
            sa.Column("left_on", sa.Date(), nullable=True),
            sa.ForeignKeyConstraint(["school_id"], ["school.id"]),
            sa.ForeignKeyConstraint(["student_id"], ["student.id"]),
            sa.ForeignKeyConstraint(["classroom_id"], ["classroom.id"]),
            sa.ForeignKeyConstraint(["academic_year_id"], ["academic_year.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "school_id",
                "student_id",
                "academic_year_id",
                name="uq_enrollment_school_student_year",
            ),
        )
        op.create_index("ix_enrollment_school_id", "enrollment", ["school_id"])
        op.create_index("ix_enrollment_student_id", "enrollment", ["student_id"])
        op.create_index("ix_enrollment_classroom_id", "enrollment", ["classroom_id"])
        op.create_index(
            "ix_enrollment_academic_year_id", "enrollment", ["academic_year_id"]
        )


def downgrade() -> None:
    names = _tables()

    if "enrollment" in names:
        op.drop_table("enrollment")

    if "department_id" in _columns("employee"):
        op.drop_index("ix_employee_department_id", table_name="employee")
        op.drop_constraint("fk_employee_department_id", "employee", type_="foreignkey")
        op.drop_column("employee", "department_id")

    if "holiday" in names:
        op.drop_table("holiday")

    if "department" in names:
        op.drop_table("department")

    if "academic_year" in names:
        op.drop_table("academic_year")
