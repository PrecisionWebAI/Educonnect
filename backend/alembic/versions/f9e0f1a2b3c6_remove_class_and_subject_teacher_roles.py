"""Remove the `class_teacher` and `subject_teacher` roles.

Revision ID: f9e0f1a2b3c6
Revises: f9e0f1a2b3c5
Create Date: 2026-11-02

Why:
  Neither was ever a job - they were *assignments*. "Is this person a class
  teacher?" is answered by `section.class_teacher_id`, and "do they take this
  subject?" by `subjectteacher`; both name the class-section involved, which a role
  cannot. So every scope check went and read the assignment tables anyway, and the
  two roles only stood in for them - while forcing a person to hold two role rows
  to do one job.

  `teacher` stays, and the two roles are removed: their grants first, then the
  assignments, then the roles themselves. Roles are DATA, so the app-level catalog
  stops seeding them and this migration cleans up a database that already has them.

  The `class.*` permission codenames the class-teacher role carried stay in the
  catalog: nothing grants them now, and they are what the classroom hub will gate
  on later.

Downgrade recreates both roles and restores their grants.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f9e0f1a2b3c6"
down_revision: str | Sequence[str] | None = "f9e0f1a2b3c5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: The two roles this revision drops.
REMOVED_ROLES: tuple[str, ...] = ("class_teacher", "subject_teacher")

#: The grants the class-teacher role had on top of `teacher` - restored on
#: downgrade so the reversal is exact.
CLASS_TEACHER_EXTRAS: tuple[str, ...] = (
    "class.students.read",
    "class.attendance.read",
    "class.attendance.mark",
    "class.attendance.update",
    "class.homework.monitor",
    "class.diary.manage",
    "class.leave.read",
    "class.ptm.read",
    "class.communication.send",
    "class.analytics.read",
    "class.announcements.create",
)

#: (codename, label, description) for the downgrade.
ROLE_ROWS: tuple[tuple[str, str, str], ...] = (
    (
        "class_teacher",
        "Class Teacher",
        "Owns one section: attendance register, diary, report cards.",
    ),
    (
        "subject_teacher",
        "Subject Teacher",
        "Teaches one subject across several classes.",
    ),
)


def _role_id(bind, codename: str):
    """The role's id, or None when it is not in the catalog."""
    return bind.execute(
        sa.text("SELECT id FROM role WHERE codename = :c"), {"c": codename}
    ).scalar()


def upgrade() -> None:
    """Delete the two roles: their grants, then their assignments, then the roles."""
    bind = op.get_bind()
    for codename in REMOVED_ROLES:
        role_id = _role_id(bind, codename)
        if role_id is None:
            continue
        bind.execute(
            sa.text("DELETE FROM rolepermission WHERE role_id = :r"), {"r": role_id}
        )
        bind.execute(sa.text("DELETE FROM user_role WHERE role_id = :r"), {"r": role_id})
        bind.execute(sa.text("DELETE FROM role WHERE id = :r"), {"r": role_id})


def downgrade() -> None:
    """Recreate both roles and give them back their grants."""
    bind = op.get_bind()
    for codename, label, description in ROLE_ROWS:
        if _role_id(bind, codename) is not None:
            continue
        bind.execute(
            sa.text(
                "INSERT INTO role (id, codename, label, description, is_system) "
                "VALUES (gen_random_uuid(), :c, :l, :d, true)"
            ),
            {"c": codename, "l": label, "d": description},
        )
        role_id = _role_id(bind, codename)

        # Both roles started from the teacher grant set.
        bind.execute(
            sa.text(
                "INSERT INTO rolepermission (id, role_id, permission_id) "
                "SELECT gen_random_uuid(), :r, p.id FROM permission p "
                "JOIN rolepermission tp ON tp.permission_id = p.id "
                "JOIN role t ON t.id = tp.role_id AND t.codename = 'teacher'"
            ),
            {"r": role_id},
        )
        if codename == "class_teacher":
            bind.execute(
                sa.text(
                    "INSERT INTO rolepermission (id, role_id, permission_id) "
                    "SELECT gen_random_uuid(), :r, p.id FROM permission p "
                    "WHERE p.codename = ANY(:codenames)"
                ),
                {"r": role_id, "codenames": list(CLASS_TEACHER_EXTRAS)},
            )
