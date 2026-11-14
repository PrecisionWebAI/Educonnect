"""Phase 2 (2/3): `leavetype`, the staff side of `leaverequest`, and the check
that makes "staff leave or student leave" a schema fact.

What and why
------------
* `leavetype` - the school's own list of leave types. The screens already use two
  vocabularies (staff policy: Casual/Sick/Earned; student form: Medical/OD/Event/
  Travel), so one master row per spelling with `applies_to` is what lets the Staff
  and Student tabs (0.10) offer the right list and stay one table underneath.
  Every school is seeded with both vocabularies plus any type its own rows mention.
* `leaverequest.employee_id` - the staff half of the request. `student_id` alone
  could not say *which* staff member, so the register and the balance had to go
  through `requester_user_id` and hope it was the employee's own login.
* `ck_leaverequest_one_subject` - `(student_id IS NULL) <> (employee_id IS NULL)`:
  a request names exactly one person. Both-null (the old staff shape) and both-set
  are refused. Existing staff rows are backfilled from `requester_user_id` first;
  a row whose requester has no employee record keeps the constraint **off** rather
  than failing the migration - the guard reports how many would violate it.
* `leave_type_id` on `leaverequest` / `leavepolicy` / `leavebalance` - the link to
  the master. The text columns stay (they are what the request was filed with, and
  what every existing reader compares), so nothing breaks and nothing is lost.
* `leavebalance.academic_year_id` - the session a balance belongs to, for schools
  whose year does not start in January.

`used_days` is deliberately **not** added: the balance stays derived from approved
requests (see `services/leave/models.py`). A stored counter would need increment,
decrement, re-check and repair, and the four places it can drift are four places the
register and the balance can then disagree.

Revision ID: b5e2f8d0c3a6
Revises: a4d1e7c9b2f5
Create Date: 2026-11-14
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b5e2f8d0c3a6"
down_revision: str | Sequence[str] | None = "a4d1e7c9b2f5"
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

    # --- leavetype ----------------------------------------------------------
    if "leavetype" not in names:
        op.create_table(
            "leavetype",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("school_id", sa.Uuid(), nullable=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("applies_to", sa.String(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("sort_order", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["school_id"], ["school.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("school_id", "name", name="uq_leavetype_school_name"),
        )
        op.create_index("ix_leavetype_school_id", "leavetype", ["school_id"])
        op.create_index("ix_leavetype_name", "leavetype", ["name"])

    # Seed every school with the two vocabularies the screens already use.
    op.execute(
        """
        INSERT INTO leavetype (id, school_id, name, applies_to, is_active,
                               sort_order, created_at)
        SELECT gen_random_uuid(), s.id, t.name, t.applies_to, true, t.sort_order,
               now()
        FROM school s
        CROSS JOIN (VALUES
            ('Casual',   'staff',   0),
            ('Sick',     'staff',   1),
            ('Earned',   'staff',   2),
            ('Medical',  'student', 0),
            ('Personal', 'student', 1),
            ('OD',       'student', 2),
            ('Event',    'student', 3),
            ('Travel',   'student', 4)
        ) AS t(name, applies_to, sort_order)
        WHERE NOT EXISTS (
            SELECT 1 FROM leavetype lt
            WHERE lt.school_id = s.id AND lower(lt.name) = lower(t.name)
        )
        """
    )
    # ... plus every type a school's own rows already mention (renamed or added).
    # `DISTINCT ON` dedupes first: `gen_random_uuid()` is volatile, so a plain
    # `SELECT DISTINCT` would hand one row per employee and hit the unique key.
    op.execute(
        """
        INSERT INTO leavetype (id, school_id, name, applies_to, is_active,
                               sort_order, created_at)
        SELECT gen_random_uuid(), x.school_id, x.name, 'both', true, 9, now()
        FROM (
            SELECT DISTINCT ON (y.school_id, lower(y.name))
                   y.school_id, y.name
            FROM (
                SELECT school_id, leave_type AS name FROM leavepolicy
                UNION ALL
                SELECT school_id, leave_type FROM leavebalance
                UNION ALL
                SELECT school_id, leave_type FROM leaverequest
            ) AS y
            WHERE y.school_id IS NOT NULL
              AND y.name IS NOT NULL
              AND btrim(y.name) <> ''
            ORDER BY y.school_id, lower(y.name), y.name
        ) AS x
        WHERE NOT EXISTS (
            SELECT 1 FROM leavetype lt
            WHERE lt.school_id = x.school_id AND lower(lt.name) = lower(x.name)
        )
        """
    )


    # --- leaverequest: the staff half + the master link + half day ----------
    columns = _columns("leaverequest")
    if "employee_id" not in columns:
        op.add_column(
            "leaverequest", sa.Column("employee_id", sa.Uuid(), nullable=True)
        )
        op.create_foreign_key(
            "fk_leaverequest_employee_id",
            "leaverequest",
            "employee",
            ["employee_id"],
            ["id"],
        )
        op.create_index("ix_leaverequest_employee_id", "leaverequest", ["employee_id"])
    if "leave_type_id" not in columns:
        op.add_column(
            "leaverequest", sa.Column("leave_type_id", sa.Uuid(), nullable=True)
        )
        op.create_foreign_key(
            "fk_leaverequest_leave_type_id",
            "leaverequest",
            "leavetype",
            ["leave_type_id"],
            ["id"],
        )
    if "half_day" not in columns:
        op.add_column(
            "leaverequest",
            sa.Column(
                "half_day", sa.Boolean(), nullable=False, server_default=sa.false()
            ),
        )

    # Existing staff rows: the requester's employee record is the person.
    op.execute(
        """
        UPDATE leaverequest r
        SET employee_id = e.id
        FROM employee e
        WHERE r.employee_id IS NULL
          AND r.student_id IS NULL
          AND e.user_id = r.requester_user_id
          AND e.school_id = r.school_id
        """
    )
    op.execute(
        """
        UPDATE leaverequest r
        SET leave_type_id = lt.id
        FROM leavetype lt
        WHERE r.leave_type_id IS NULL
          AND lt.school_id = r.school_id
          AND lower(lt.name) = lower(r.leave_type)
        """
    )

    # The rule itself. Added only when every row already satisfies it - a staff
    # request whose requester has no employee record keeps the constraint off
    # instead of blocking the deployment, and the count is printed.
    violating = (
        op.get_bind()
        .exec_driver_sql(
            "SELECT count(*) FROM leaverequest"
            " WHERE (student_id IS NULL) = (employee_id IS NULL)"
        )
        .scalar_one()
    )
    if violating == 0:
        op.create_check_constraint(
            "ck_leaverequest_one_subject",
            "leaverequest",
            "(student_id IS NULL) <> (employee_id IS NULL)",
        )
    else:  # pragma: no cover - only on a database with unmapped staff leaves
        print(
            f"[phase2] {violating} leaverequest row(s) name no subject; "
            "ck_leaverequest_one_subject was not created"
        )

    # --- the two existing leave tables get the master link ------------------
    if "leave_type_id" not in _columns("leavepolicy"):
        op.add_column(
            "leavepolicy", sa.Column("leave_type_id", sa.Uuid(), nullable=True)
        )
        op.create_foreign_key(
            "fk_leavepolicy_leave_type_id",
            "leavepolicy",
            "leavetype",
            ["leave_type_id"],
            ["id"],
        )
    op.execute(
        """
        UPDATE leavepolicy p
        SET leave_type_id = lt.id
        FROM leavetype lt
        WHERE p.leave_type_id IS NULL
          AND lt.school_id = p.school_id
          AND lower(lt.name) = lower(p.leave_type)
        """
    )

    if "leave_type_id" not in _columns("leavebalance"):
        op.add_column(
            "leavebalance", sa.Column("leave_type_id", sa.Uuid(), nullable=True)
        )
        op.create_foreign_key(
            "fk_leavebalance_leave_type_id",
            "leavebalance",
            "leavetype",
            ["leave_type_id"],
            ["id"],
        )
    if "academic_year_id" not in _columns("leavebalance"):
        op.add_column(
            "leavebalance", sa.Column("academic_year_id", sa.Uuid(), nullable=True)
        )
        op.create_foreign_key(
            "fk_leavebalance_academic_year_id",
            "leavebalance",
            "academic_year",
            ["academic_year_id"],
            ["id"],
        )
        op.create_index(
            "ix_leavebalance_academic_year_id", "leavebalance", ["academic_year_id"]
        )
    op.execute(
        """
        UPDATE leavebalance b
        SET leave_type_id = lt.id
        FROM leavetype lt
        WHERE b.leave_type_id IS NULL
          AND lt.school_id = b.school_id
          AND lower(lt.name) = lower(b.leave_type)
        """
    )
    op.execute(
        """
        UPDATE leavebalance b
        SET academic_year_id = a.id
        FROM academic_year a
        WHERE b.academic_year_id IS NULL
          AND a.school_id = b.school_id
          AND b.year BETWEEN extract(year FROM a.start_date)
                         AND extract(year FROM a.end_date)
        """
    )


def downgrade() -> None:
    columns = _columns("leavebalance")
    if "academic_year_id" in columns:
        op.drop_index("ix_leavebalance_academic_year_id", table_name="leavebalance")
        op.drop_constraint(
            "fk_leavebalance_academic_year_id", "leavebalance", type_="foreignkey"
        )
        op.drop_column("leavebalance", "academic_year_id")
    if "leave_type_id" in columns:
        op.drop_constraint(
            "fk_leavebalance_leave_type_id", "leavebalance", type_="foreignkey"
        )
        op.drop_column("leavebalance", "leave_type_id")

    if "leave_type_id" in _columns("leavepolicy"):
        op.drop_constraint(
            "fk_leavepolicy_leave_type_id", "leavepolicy", type_="foreignkey"
        )
        op.drop_column("leavepolicy", "leave_type_id")

    columns = _columns("leaverequest")
    if "employee_id" in columns:
        op.drop_constraint("ck_leaverequest_one_subject", "leaverequest", type_="check")
        op.drop_index("ix_leaverequest_employee_id", table_name="leaverequest")
        op.drop_constraint(
            "fk_leaverequest_employee_id", "leaverequest", type_="foreignkey"
        )
        op.drop_column("leaverequest", "employee_id")
    if "leave_type_id" in columns:
        op.drop_constraint(
            "fk_leaverequest_leave_type_id", "leaverequest", type_="foreignkey"
        )
        op.drop_column("leaverequest", "leave_type_id")
    if "half_day" in columns:
        op.drop_column("leaverequest", "half_day")

    if "leavetype" in _tables():
        op.drop_table("leavetype")

