"""RBAC: `role` + `user_role` (multi-role people) and a normalised grant table.

Revision ID: a2c5e8b1d4f7
Revises: (current head)

Why (see `info/db_mapping.txt`, LAYER 0):
  A person in a school holds **more than one role** - the principal teaches two
  periods a day, the physics teacher also runs the library, and a teacher is
  usually a parent too. The old shape could not express that at all: roles were
  a PostgreSQL enum plus a single `user.role` column.

  * `role` - the catalog. Roles become DATA: adding one is an INSERT, never a
    migration. That removes the exact drift the old enum suffered (14 labels in
    the database vs 13 in Python).
  * `user_role` - who holds which role, with `is_primary` naming the role whose
    dashboard opens at login. Composite key `(user_id, role_id)` plus the
    UNIQUE the doc asks for, so there is no surrogate id to maintain.
    Every existing `user.role` becomes one row here (`director` -> `owner`,
    `admin` -> `system_admin`, the stale `parent` -> `guardian`).
  * `rolepermission` - rebuilt to store `role_id` instead of the role *codename*
    as text. The old table repeated the codename in hundreds of rows, and the
    database would accept a grant for a role that no longer existed.

  Also: `user.created_at`, and the `roleenum` type is dropped.
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a2c5e8b1d4f7"
down_revision: str | Sequence[str] | None = "f1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_AUTO_STR = sqlmodel.sql.sqltypes.AutoString

#: The seeded role catalog.
#:
#: `system_admin` + `owner` are the two platform roles; the rest are the school's
#: own. `class_teacher` / `subject_teacher` / `accountant` / `librarian` /
#: `transport` are seeded because modules already exist for them - the doc lists
#: them as "extensible later (INSERT only)", and a seed IS an insert.
ROLE_CATALOG: list[dict] = [
    {
        "codename": "system_admin",
        "label": "System Admin",
        "description": "Platform administrator: unrestricted access, manages roles and grants.",
    },
    {
        "codename": "owner",
        "label": "Owner",
        "description": "Proprietor of the school; sees everything.",
    },
    {
        "codename": "principal",
        "label": "Principal",
        "description": "Heads academics; approves papers, fee cards and payroll.",
    },
    {
        "codename": "vice_principal",
        "label": "Vice Principal",
        "description": "Deputy to the principal: timetable, discipline, approvals.",
    },
    {
        "codename": "hod",
        "label": "Head of Department",
        "description": "Leads a department's teachers, syllabus and results.",
    },
    {
        "codename": "teacher",
        "label": "Teacher",
        "description": "Teaching staff: classroom, homework, marks, attendance.",
    },
    {
        "codename": "class_teacher",
        "label": "Class Teacher",
        "description": "Owns one section: attendance register, diary, report cards.",
    },
    {
        "codename": "subject_teacher",
        "label": "Subject Teacher",
        "description": "Teaches one subject across several classes.",
    },
    {
        "codename": "accountant",
        "label": "Accountant",
        "description": "Fees, receipts, payroll and collection reports.",
    },
    {
        "codename": "librarian",
        "label": "Librarian",
        "description": "Catalogue, issues and returns.",
    },
    {
        "codename": "transport",
        "label": "Transport Manager",
        "description": "Buses, routes and stop assignments.",
    },
    {
        "codename": "staff",
        "label": "Staff",
        "description": "Support staff: front office, lab, maintenance.",
    },
    {
        "codename": "student",
        "label": "Student",
        "description": "Learner login: own timetable, homework and fees.",
    },
    {
        "codename": "guardian",
        "label": "Parent / Guardian",
        "description": "Parent login: their children's records only.",
    },
]

#: Old single-role value -> catalog codename, for the backfill.
LEGACY_ROLE_MAP = {
    "director": "owner",
    "admin": "system_admin",
    "parent": "guardian",
}


def upgrade() -> None:
    """Upgrade schema."""
    # --- 1. the role catalog ----------------------------------------------
    op.create_table(
        "role",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("codename", _AUTO_STR(), nullable=False),
        sa.Column("label", _AUTO_STR(), nullable=False),
        sa.Column("description", _AUTO_STR(), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_role_codename"), "role", ["codename"], unique=True)

    catalog = sa.table(
        "role",
        sa.column("codename", sa.String),
        sa.column("label", sa.String),
        sa.column("description", sa.String),
        sa.column("is_system", sa.Boolean),
    )
    op.bulk_insert(catalog, [{**row, "is_system": True} for row in ROLE_CATALOG])

    # --- 2. who holds which role ------------------------------------------
    op.create_table(
        "user_role",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("assigned_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["role.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("user_id", "role_id"),
    )
    # `role_id` is not the leading key column, so "who holds role X?" needs its
    # own index; the PK index already covers "which roles does user X hold?".
    op.create_index(
        op.f("ix_user_role_role_id"), "user_role", ["role_id"], unique=False
    )

    # Every existing single role becomes one row. The remap happens inside the
    # query (not in an UPDATE on the enum column) because `owner` /
    # `system_admin` are not labels of the old `roleenum` type.
    #
    # The legacy column may already be gone - this change reached one database
    # before its code was reverted - so the backfill only runs when it is there.
    user_columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("user")}
    if "role" in user_columns:
        op.execute(
            "INSERT INTO user_role (user_id, role_id, is_primary, assigned_at) "
            "SELECT u.id, r.id, true, now() FROM \"user\" u "
            "JOIN role r ON r.codename = CASE u.role::text "
            "  WHEN 'director' THEN 'owner' "
            "  WHEN 'admin' THEN 'system_admin' "
            "  WHEN 'parent' THEN 'guardian' "
            "  ELSE u.role::text END"
        )

    # --- 3. rolepermission: codename text -> role_id -----------------------
    op.create_table(
        "rolepermission_new",
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("permission_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["permission_id"], ["permission.id"]),
        sa.ForeignKeyConstraint(["role_id"], ["role.id"]),
        sa.PrimaryKeyConstraint("role_id", "permission_id"),
    )
    op.create_index(
        op.f("ix_rolepermission_permission_id"),
        "rolepermission_new",
        ["permission_id"],
        unique=False,
    )
    op.execute(
        "INSERT INTO rolepermission_new (role_id, permission_id) "
        "SELECT r.id, rp.permission_id "
        "FROM rolepermission rp JOIN role r ON r.codename = rp.role"
    )
    op.drop_table("rolepermission")
    op.rename_table("rolepermission_new", "rolepermission")

    # --- 4. user: created_at in; role + the enum type out ------------------
    op.add_column("user", sa.Column("created_at", sa.DateTime(), nullable=True))
    op.execute("UPDATE \"user\" SET created_at = now() WHERE created_at IS NULL")
    op.alter_column("user", "created_at", nullable=False)
    op.drop_column("user", "role")
    op.execute("DROP TYPE IF EXISTS roleenum")


def downgrade() -> None:
    """Downgrade schema."""
    # --- rolepermission back to the codename text column -------------------
    op.create_table(
        "rolepermission_old",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("role", _AUTO_STR(), nullable=False),
        sa.Column("permission_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["permission_id"], ["permission.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_rolepermission_old_role"), "rolepermission_old", ["role"], unique=False
    )
    op.create_index(
        op.f("ix_rolepermission_old_permission_id"),
        "rolepermission_old",
        ["permission_id"],
        unique=False,
    )
    op.execute(
        "INSERT INTO rolepermission_old (role, permission_id) "
        "SELECT r.codename, rp.permission_id "
        "FROM rolepermission rp JOIN role r ON r.id = rp.role_id"
    )
    op.drop_index(op.f("ix_rolepermission_permission_id"), table_name="rolepermission")
    op.drop_table("rolepermission")
    op.rename_table("rolepermission_old", "rolepermission")

    # --- single-role column and the enum come back -------------------------
    roleenum = sa.Enum(
        "director",
        "principal",
        "hod",
        "teacher",
        "student",
        "parent",
        "accountant",
        "admin",
        "class_teacher",
        "subject_teacher",
        "guardian",
        "librarian",
        "transport",
        "staff",
        name="roleenum",
    )
    roleenum.create(op.get_bind(), checkfirst=True)
    op.add_column("user", sa.Column("role", roleenum, nullable=True))
    # One role per person again: the primary one, else the first by codename.
    # Every catalog codename is mapped explicitly, so a role added later cannot
    # make the cast fail (it falls back to `staff`).
    op.execute(
        "UPDATE \"user\" u SET role = sub.role_name::roleenum FROM ("
        "  SELECT DISTINCT ON (ur.user_id) ur.user_id, CASE r.codename "
        "    WHEN 'owner' THEN 'director' WHEN 'system_admin' THEN 'admin' "
        "    WHEN 'vice_principal' THEN 'principal' WHEN 'principal' THEN 'principal' "
        "    WHEN 'hod' THEN 'hod' WHEN 'teacher' THEN 'teacher' "
        "    WHEN 'class_teacher' THEN 'class_teacher' "
        "    WHEN 'subject_teacher' THEN 'subject_teacher' "
        "    WHEN 'accountant' THEN 'accountant' WHEN 'librarian' THEN 'librarian' "
        "    WHEN 'transport' THEN 'transport' WHEN 'staff' THEN 'staff' "
        "    WHEN 'student' THEN 'student' WHEN 'guardian' THEN 'guardian' "
        "    ELSE 'staff' END AS role_name "
        "  FROM user_role ur JOIN role r ON r.id = ur.role_id "
        "  ORDER BY ur.user_id, ur.is_primary DESC, r.codename"
        ") sub WHERE sub.user_id = u.id"
    )
    op.execute("UPDATE \"user\" SET role = 'staff' WHERE role IS NULL")
    op.alter_column("user", "role", nullable=False)
    op.drop_column("user", "created_at")

    op.drop_index(op.f("ix_user_role_role_id"), table_name="user_role")
    op.drop_table("user_role")
    op.drop_index(op.f("ix_role_codename"), table_name="role")
    op.drop_table("role")
