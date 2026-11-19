"""Remove the appraisal season: its five tables and its five rights.

Revision ID: d2a7f4c9e1b8
Revises: c5f8a2d7e9b3
Create Date: 2026-11-17

Why
---
The school asked for appraisal to be **removed**, not hidden, and for a teacher's
performance to be measured from attendance, workload and course completion instead
(`people/teachers/performance/`). Once nothing reads the season, keeping the tables
means a schema that documents a feature nobody can reach, and the five permissions
would stay in the role catalog - granted to five roles - gating nothing.

What goes
---------
    appraisalgoal      -> appraisal        (foreign key first)
    appraisal          -> appraisalcycle
    trainingrecord     (independent)
    appraisalcycle
    teacherreview      the parent star ratings; the appraisal score was their only
                       reader, and performance no longer reads a rating at all

and the rights `appraisals.read`, `appraisals.self`, `appraisals.review`,
`appraisals.manage` and `training.manage` - their rows in `role_permission` first,
then the catalog rows in `permission`.

`_has_table` guards keep this re-runnable, for the reason Phases 6-9 record: a database
built by `create_missing()` is stamped at head and never runs this file, so a re-run
against a half-cleaned database must not fail on a table that is already gone.

Downgrade recreates the five tables, the permission catalog rows and the grants the
five roles held, so the reversal is exact.
"""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d2a7f4c9e1b8"
down_revision: str | Sequence[str] | None = "c5f8a2d7e9b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: Dropped in this order: the goals point at the appraisals, which point at the cycle.
REMOVED_TABLES = (
    "appraisalgoal",
    "appraisal",
    "trainingrecord",
    "appraisalcycle",
    "teacherreview",
)

#: codename -> (category, label) - what `auth/permissions.py` declared before this
#: revision. Needed by the downgrade, which must put the catalog back exactly.
REMOVED_PERMISSIONS: dict[str, tuple[str, str]] = {
    "appraisals.read": ("Appraisal", "Read Appraisals"),
    "appraisals.self": ("Appraisal", "Fill In Own Appraisal"),
    "appraisals.review": ("Appraisal", "Review Appraisals"),
    "appraisals.manage": ("Appraisal", "Manage Appraisal Seasons"),
    "training.manage": ("Appraisal", "Manage Training Records"),
}

#: The roles that held each right, as `auth/permissions.py` had it: the office ran the
#: season, an HOD reviewed inside their department, a teacher filled in their own.
PERMISSION_ROLES: dict[str, tuple[str, ...]] = {
    "appraisals.read": ("director", "principal", "vice_principal", "hod", "teacher"),
    "appraisals.self": ("director", "principal", "vice_principal", "hod", "teacher"),
    "appraisals.review": ("director", "principal", "vice_principal", "hod"),
    "appraisals.manage": ("director", "principal", "vice_principal"),
    "training.manage": ("director", "principal", "vice_principal", "hod"),
}


def _text() -> sa.types.TypeEngine:
    """The string type SQLModel's `str` maps to (`AutoString`)."""
    return sqlmodel.sql.sqltypes.AutoString()


def _has_table(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def _grants_table() -> str | None:
    """The role↔permission join table's real name.

    `RolePermission` maps to `rolepermission` (SQLModel's default), while the older
    hand-written SQL in this file said `role_permission`. Deleting the grants is what
    makes the catalog delete legal, so the name is resolved rather than assumed.
    """
    for name in ("rolepermission", "role_permission"):
        if _has_table(name):
            return name
    return None


def _drop_tables() -> None:
    for name in REMOVED_TABLES:
        if _has_table(name):
            op.drop_table(name)


def _drop_permissions() -> None:
    """Delete the grants, then the catalog rows - the join table first."""
    bind = op.get_bind()
    grants = _grants_table()
    if grants is not None and _has_table("permission"):
        bind.execute(
            sa.text(
                f"DELETE FROM {grants} WHERE permission_id IN "
                "(SELECT id FROM permission WHERE codename IN :codes)"
            ).bindparams(sa.bindparam("codes", expanding=True)),
            {"codes": list(REMOVED_PERMISSIONS)},
        )
    if _has_table("permission"):
        bind.execute(
            sa.text("DELETE FROM permission WHERE codename IN :codes").bindparams(
                sa.bindparam("codes", expanding=True)
            ),
            {"codes": list(REMOVED_PERMISSIONS)},
        )


def _restore_permissions() -> None:
    """Put the catalog rows back and grant them to the roles that held them."""
    bind = op.get_bind()
    grants = _grants_table()
    if not (_has_table("permission") and grants):
        return
    if not _has_table("role"):
        return

    for codename, roles in PERMISSION_ROLES.items():
        category, label = REMOVED_PERMISSIONS[codename]
        permission_id = bind.execute(
            sa.text("SELECT id FROM permission WHERE codename = :codename"),
            {"codename": codename},
        ).scalar_one_or_none()
        if permission_id is None:
            permission_id = uuid4()
            bind.execute(
                sa.text(
                    "INSERT INTO permission (id, codename, category, label) "
                    "VALUES (:id, :codename, :category, :label)"
                ),
                {
                    "id": permission_id,
                    "codename": codename,
                    "category": category,
                    "label": label,
                },
            )
        for role in roles:
            role_id = bind.execute(
                sa.text("SELECT id FROM role WHERE codename = :codename"),
                {"codename": role},
            ).scalar_one_or_none()
            if role_id is None:
                continue
            held = bind.execute(
                sa.text(
                    f"SELECT id FROM {grants} "
                    "WHERE role_id = :role_id AND permission_id = :permission_id"
                ),
                {"role_id": role_id, "permission_id": permission_id},
            ).scalar_one_or_none()
            if held is not None:
                continue
            bind.execute(
                sa.text(
                    f"INSERT INTO {grants} (id, role_id, permission_id) "
                    "VALUES (:id, :role_id, :permission_id)"
                ),
                {"id": uuid4(), "role_id": role_id, "permission_id": permission_id},
            )


def upgrade() -> None:
    _drop_tables()
    _drop_permissions()


# --- downgrade: put the season back, exactly as `e8b2f5c9a1d4` created it -----


def _create_cycles() -> None:
    if _has_table("appraisalcycle"):
        return
    op.create_table(
        "appraisalcycle",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("school_id", sa.Uuid(), sa.ForeignKey("school.id"), index=True),
        sa.Column("name", _text(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("status", _text(), nullable=False),
        sa.Column("note", _text(), nullable=True),
        sa.Column(
            "created_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("app_user.id"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("school_id", "name", name="uq_appraisalcycle_school_name"),
    )


def _create_appraisals() -> None:
    if _has_table("appraisal"):
        return
    op.create_table(
        "appraisal",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("school_id", sa.Uuid(), sa.ForeignKey("school.id"), index=True),
        sa.Column(
            "cycle_id",
            sa.Uuid(),
            sa.ForeignKey("appraisalcycle.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "employee_id",
            sa.Uuid(),
            sa.ForeignKey("employee.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("status", _text(), nullable=False),
        sa.Column("self_rating", sa.Integer(), nullable=True),
        sa.Column("self_note", _text(), nullable=True),
        sa.Column("reviewer_rating", sa.Integer(), nullable=True),
        sa.Column("reviewer_note", _text(), nullable=True),
        sa.Column(
            "reviewer_employee_id",
            sa.Uuid(),
            sa.ForeignKey("employee.id"),
            nullable=True,
        ),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("finalized_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint(
            "school_id",
            "cycle_id",
            "employee_id",
            name="uq_appraisal_cycle_employee",
        ),
    )
    op.create_index("ix_appraisal_cycle_status", "appraisal", ["cycle_id", "status"])


def _create_goals() -> None:
    if _has_table("appraisalgoal"):
        return
    op.create_table(
        "appraisalgoal",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("school_id", sa.Uuid(), sa.ForeignKey("school.id"), index=True),
        sa.Column(
            "appraisal_id",
            sa.Uuid(),
            sa.ForeignKey("appraisal.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("title", _text(), nullable=False),
        sa.Column("target", _text(), nullable=True),
        sa.Column("achieved", sa.Boolean(), nullable=True),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def _create_training() -> None:
    if _has_table("trainingrecord"):
        return
    op.create_table(
        "trainingrecord",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("school_id", sa.Uuid(), sa.ForeignKey("school.id"), index=True),
        sa.Column(
            "employee_id",
            sa.Uuid(),
            sa.ForeignKey("employee.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("title", _text(), nullable=False),
        sa.Column("provider", _text(), nullable=True),
        sa.Column("on_date", sa.Date(), nullable=False),
        sa.Column("hours", sa.Integer(), nullable=False),
        sa.Column("note", _text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column(
            "created_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("app_user.id"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_trainingrecord_employee_date",
        "trainingrecord",
        ["employee_id", "on_date"],
    )


def _create_reviews() -> None:
    """The anonymous star ratings, in the shape the model had at this revision."""
    if _has_table("teacherreview"):
        return
    op.create_table(
        "teacherreview",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("school_id", sa.Uuid(), sa.ForeignKey("school.id"), index=True),
        sa.Column(
            "teacher_id", sa.Uuid(), sa.ForeignKey("employee.id"), nullable=False
        ),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("reviewer_role", _text(), nullable=False),
        sa.Column("comment", _text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    _create_cycles()
    _create_appraisals()
    _create_goals()
    _create_training()
    _create_reviews()
    _restore_permissions()


