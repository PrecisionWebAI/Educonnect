"""Add employeesalary, link salarypayment to employee, drop employee.salary_monthly.

Revision ID: f6b7c8d9e0f1
Revises: f5a6b7c8d9e0
Create Date: 2026-11-02

Why:
  Salary is its own concern, so it stops living on the person:

  * `employeesalary` - what an employee is paid now (the figure the hire form
    collects). One row per employee (`employee_id` is unique). `employee` keeps
    the bank / KYC detail, which is about paying the person, not the amount.
  * `salarypayment` - the monthly register now points at the employee
    (`employee_id` + `school_id`) instead of repeating `staff_code`,
    `staff_name`, `designation` and `department` as text. The register screen
    still shows all four; they are read through `employee_id`, so a rename or a
    promotion can no longer leave the register describing someone who is gone.

  The register is empty at this point, so the column swap is structural.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f6b7c8d9e0f1"
down_revision: str | Sequence[str] | None = "f5a6b7c8d9e0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: The register's old denormalised columns - replaced by the `employee_id` link.
_PAYMENT_TEXT_COLUMNS = ("staff_code", "staff_name", "designation", "department")


def upgrade() -> None:
    """Create employeesalary, move the salary off `employee`, relink the register."""
    inspector = sa.inspect(op.get_bind())

    # --- 1. employeesalary --------------------------------------------------
    if "employeesalary" not in inspector.get_table_names():
        op.create_table(
            "employeesalary",
            sa.Column("employee_id", sa.Integer(), nullable=False),
            sa.Column(
                "salary_monthly", sa.Float(), nullable=False, server_default="0"
            ),
            sa.Column("effective_from", sa.Date(), nullable=False),
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("school_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["employee_id"], ["employee.id"]),
            sa.ForeignKeyConstraint(["school_id"], ["school.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_employeesalary_employee_id",
            "employeesalary",
            ["employee_id"],
            unique=True,
        )
        op.create_index("ix_employeesalary_school_id", "employeesalary", ["school_id"])

    employee_columns = {c["name"] for c in inspector.get_columns("employee")}
    if "salary_monthly" in employee_columns:
        op.execute(
            """
            INSERT INTO employeesalary
                (employee_id, salary_monthly, effective_from, school_id, created_at)
            SELECT e.id, e.salary_monthly,
                   COALESCE(e.joining_date, CURRENT_DATE), e.school_id, now()
            FROM employee e
            WHERE e.salary_monthly IS NOT NULL
            """
        )
        op.drop_column("employee", "salary_monthly")

    # --- 2. salarypayment.employee_id ---------------------------------------
    payment_columns = {c["name"] for c in inspector.get_columns("salarypayment")}
    if "employee_id" in payment_columns:
        return

    op.add_column(
        "salarypayment", sa.Column("employee_id", sa.Integer(), nullable=True)
    )
    if "staff_code" in payment_columns:
        op.execute(
            """
            UPDATE salarypayment p
            SET employee_id = e.id
            FROM employee e
            WHERE e.employee_code = p.staff_code
            """
        )
    # A row that cannot be matched to an employee has nothing to point at.
    op.execute("DELETE FROM salarypayment WHERE employee_id IS NULL")
    op.alter_column("salarypayment", "employee_id", nullable=False)
    op.create_foreign_key(
        "salarypayment_employee_id_fkey",
        "salarypayment",
        "employee",
        ["employee_id"],
        ["id"],
    )
    op.create_index("ix_salarypayment_employee_id", "salarypayment", ["employee_id"])
    for column in _PAYMENT_TEXT_COLUMNS:
        if column in payment_columns:
            op.drop_column("salarypayment", column)


def downgrade() -> None:
    """Restore the register's text columns and `employee.salary_monthly`."""
    inspector = sa.inspect(op.get_bind())

    payment_columns = {c["name"] for c in inspector.get_columns("salarypayment")}
    if "employee_id" in payment_columns:
        for column in _PAYMENT_TEXT_COLUMNS:
            if column not in payment_columns:
                op.add_column(
                    "salarypayment",
                    sa.Column(column, sa.String(), nullable=False, server_default=""),
                )
        op.execute(
            """
            UPDATE salarypayment p
            SET staff_code = e.employee_code,
                staff_name = COALESCE(u.full_name, ''),
                designation = '',
                department = COALESCE(e.department, '')
            FROM employee e
            LEFT JOIN "user" u ON u.id = e.user_id
            WHERE e.id = p.employee_id
            """
        )
        op.drop_index("ix_salarypayment_employee_id", table_name="salarypayment")
        op.drop_constraint(
            "salarypayment_employee_id_fkey", "salarypayment", type_="foreignkey"
        )
        op.drop_column("salarypayment", "employee_id")

    employee_columns = {c["name"] for c in inspector.get_columns("employee")}
    if "salary_monthly" not in employee_columns:
        op.add_column("employee", sa.Column("salary_monthly", sa.Float(), nullable=True))
        op.execute(
            """
            UPDATE employee e
            SET salary_monthly = s.salary_monthly
            FROM employeesalary s
            WHERE s.employee_id = e.id
            """
        )

    if "employeesalary" in inspector.get_table_names():
        op.drop_index("ix_employeesalary_school_id", table_name="employeesalary")
        op.drop_index("ix_employeesalary_employee_id", table_name="employeesalary")
        op.drop_table("employeesalary")
