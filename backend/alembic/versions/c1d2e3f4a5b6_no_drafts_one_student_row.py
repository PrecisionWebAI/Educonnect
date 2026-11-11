"""No drafts: one student row, and it is always a real student.

Revision ID: c1d2e3f4a5b6
Revises: b3c4d4e5f6a7
Create Date: 2026-11-06

Why
---
`student` used to carry two lives at once. A row could be a **draft** - half a form
the office was still typing, with no login, no class-section and no admission number
- or a registered student, and one column told the two apart: `status`. That flag
dragged three other things along with it:

* an **application number** (`application_no`) minted for the draft, which the
  registered row then kept as a second number beside `admission_number`;
* a **guardian block** (`guardian_name` ... `guardian_address`) copied onto every
  child, although a parent is a person of their own (`guardian`) linked through
  `student_guardian_relationship` - so one parent was one row *and* two columns on
  each child;
* rows that were not students at all, which every screen that read the table had to
  remember to filter out. One that forgot (`students/repository.get_students`) listed
  half-filled forms in the student directory.

None of it is needed. A row in `student` is a student the school has admitted, so
there is nothing to filter, nothing to promote and nothing to duplicate.

What this migration does
-----------------------
1. **Promotes the drafts that are complete enough to be students** - a first name, the
   class applied for, a guardian name, and a guardian email and phone the family can
   actually be reached on. They keep the number they already carry (`application_no`
   becomes their `admission_number`, unless that number is taken), get the guardian
   row and link they never had, and are stamped as activated.
2. **Deletes the drafts that cannot be students**, after removing the rows that
   reference them - the same order `students/service.delete_student` uses. A form that
   was never complete was never a student; leaving it behind would keep the directory
   listing half-made children. The rows are in `backup_before_no_drafts.sql`.
3. Backfills `admission_number` for any student still without one, so the number is
   never missing on any row.
4. Drops `application_no`, `status`, `promoted_at` and the six guardian columns,
   together with their unique constraint and index.

`admission_number` stays, and it becomes the **single** number a learner has: the
server mints it the moment a student is created (`admissions/service.py`).
"""

from collections.abc import Sequence
from datetime import date

import sqlalchemy as sa
from sqlmodel.sql.sqltypes import AutoString as _AUTO_STR
from sqlalchemy.engine import Connection

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c1d2e3f4a5b6"
down_revision: str | None = "b3c4d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: The columns the draft dragged in, and the ones it duplicated the guardian into.
_DROPPED_COLUMNS = (
    "application_no",
    "status",
    "promoted_at",
    "guardian_name",
    "guardian_relation",
    "guardian_phone",
    "guardian_email",
    "guardian_occupation",
    "guardian_address",
)

#: Everything that carries a foreign key to `student` - it has to go before the row
#: does (the same list `students/service.py::delete_student` walks).
_CHILD_TABLES = (
    "attendancerecord",
    "marks",
    "feetransaction",
    "leaverequest",
    "libraryissue",
    "homeworksubmission",
    "diaryremark",
    "student_guardian_relationship",
)

#: A draft worth keeping as a student: the school knows who the child is *and* can
#: reach the family. The same set `REQUIRED_TO_ADMIT` enforces in
#: `admissions/service.py`, written as SQL because a migration talks to the database.
#: A guardian name may come from either parent's block, which is how the form allowed
#: it before the guardian block existed.
_COMPLETE_DRAFT = """
    status = 'Draft'
    AND coalesce(trim(student_first_name), '') <> ''
    AND coalesce(trim(applied_for_class_level), '') <> ''
    AND coalesce(trim(guardian_email), '') <> ''
    AND coalesce(
        nullif(trim(guardian_name), ''),
        nullif(trim(father_name), ''),
        nullif(trim(mother_name), '')
    ) IS NOT NULL
    AND length(regexp_replace(coalesce(guardian_phone, ''), '[^0-9]', '', 'g')) = 10
"""


def _digits(value: str | None) -> str:
    """The digits of a phone number, however it was typed (`canonical_phone`)."""
    return "".join(character for character in (value or "") if character.isdigit())


#: The prefix the product mints when a school has no number to hand
#: (`admissions/repository.py::next_admission_number`).
_NUMBER_PREFIX = f"ADM-{date.today().year}-"


def _taken_numbers(connection: Connection) -> dict[object, set[str]]:
    """{school_id: the admission numbers that school has already handed out}."""
    taken: dict[object, set[str]] = {}
    for school_id, number in connection.execute(
        sa.text(
            "SELECT school_id, admission_number FROM student "
            "WHERE admission_number IS NOT NULL"
        )
    ).fetchall():
        taken.setdefault(school_id, set()).add(number)
    return taken


def _mint(taken: dict[object, set[str]], school_id: object) -> str:
    """The next free `ADM-<year>-<nnnn>` for that school, and remember it."""
    used = {
        int(number.rsplit("-", 1)[-1])
        for number in taken.get(school_id, set())
        if number.startswith(_NUMBER_PREFIX)
        and number.rsplit("-", 1)[-1].isdigit()
    }
    number = f"{_NUMBER_PREFIX}{max(used, default=0) + 1:04d}"
    taken.setdefault(school_id, set()).add(number)
    return number


def _available_number(
    taken: dict[object, set[str]], school_id: object, wanted: str | None
) -> str:
    """`wanted` - the form number the draft already carries - or a fresh one.

    A school's own numbers (the demo schools hand out `DPS-2026-1206`) are kept as
    they are: the draft's number becomes the student's number, exactly as it did for
    every row that was registered before this revision.
    """
    if wanted and wanted not in taken.get(school_id, set()):
        taken.setdefault(school_id, set()).add(wanted)
        return wanted
    return _mint(taken, school_id)


def _promote(connection: Connection) -> int:
    """Keep the complete drafts as real students: number, guardian, link, activated.

    The guardian is found by their **email or phone** first, so a row that was being
    typed for a family already on file joins that family instead of creating a second
    parent - the same "one contact, one person" rule the product enforces at runtime.
    """
    rows = connection.execute(
        sa.text(
            "SELECT id, school_id, application_no, guardian_name, father_name, "
            "mother_name, guardian_relation, guardian_phone, guardian_email, "
            "guardian_occupation, guardian_address "
            f"FROM student WHERE {_COMPLETE_DRAFT}"
        )
    ).mappings().all()
    taken = _taken_numbers(connection)
    for row in rows:
        name = (
            (row["guardian_name"] or "").strip()
            or (row["father_name"] or "").strip()
            or (row["mother_name"] or "").strip()
        )
        email = (row["guardian_email"] or "").strip().lower() or None
        phone = _digits(row["guardian_phone"])
        guardian_id = connection.execute(
            sa.text(
                "SELECT id FROM guardian WHERE school_id = :school_id "
                "AND (lower(email) = :email OR phone = :phone) LIMIT 1"
            ),
            {"school_id": row["school_id"], "email": email, "phone": phone},
        ).scalar()
        if guardian_id is None:
            guardian_id = connection.execute(
                sa.text(
                    "INSERT INTO guardian (id, school_id, name, phone, email, "
                    "occupation, address) VALUES "
                    "(gen_random_uuid(), :school_id, :name, :phone, :email, "
                    ":occupation, :address) RETURNING id"
                ),
                {
                    "school_id": row["school_id"],
                    "name": name,
                    "phone": phone,
                    "email": email,
                    "occupation": (row["guardian_occupation"] or "").strip() or None,
                    "address": (row["guardian_address"] or "").strip() or None,
                },
            ).scalar_one()
        connection.execute(
            sa.text(
                "INSERT INTO student_guardian_relationship "
                "(id, school_id, student_id, guardian_id, relationship_type, "
                "is_primary) VALUES "
                "(gen_random_uuid(), :school_id, :student_id, :guardian_id, "
                ":relation, true) ON CONFLICT (student_id, guardian_id) DO NOTHING"
            ),
            {
                "school_id": row["school_id"],
                "student_id": row["id"],
                "guardian_id": guardian_id,
                "relation": (row["guardian_relation"] or "").strip().lower()
                or "guardian",
            },
        )
        connection.execute(
            sa.text(
                "UPDATE student SET admission_number = :number, "
                "activated_at = coalesce(activated_at, now()), "
                "status = 'Registered' WHERE id = :id"
            ),
            {
                "number": _available_number(
                    taken, row["school_id"], row["application_no"]
                ),
                "id": row["id"],
            },
        )
    return len(rows)


def _delete_incomplete_drafts(connection: Connection) -> int:
    """Remove the drafts that cannot be students, and everything pointing at them.

    The order is the one `students/service.delete_student` uses: the rows carrying a
    foreign key to the student go first (attendance, marks, fees, homework, diary,
    leaves, library issues, guardian links), then the student row itself.
    """
    ids = [
        row[0]
        for row in connection.execute(
            sa.text("SELECT id FROM student WHERE status = 'Draft'")
        ).fetchall()
    ]
    if not ids:
        return 0
    for table in _CHILD_TABLES:
        connection.execute(
            sa.text(f"DELETE FROM {table} WHERE student_id IN :ids").bindparams(
                sa.bindparam("ids", expanding=True)
            ),
            {"ids": ids},
        )
    connection.execute(
        sa.text("DELETE FROM student WHERE id IN :ids").bindparams(
            sa.bindparam("ids", expanding=True)
        ),
        {"ids": ids},
    )
    return len(ids)


def _backfill_numbers(connection: Connection) -> int:
    """Give every student a number: a row in this table is never numberless now."""
    rows = connection.execute(
        sa.text("SELECT id, school_id FROM student WHERE admission_number IS NULL")
    ).fetchall()
    taken = _taken_numbers(connection)
    for student_id, school_id in rows:
        connection.execute(
            sa.text("UPDATE student SET admission_number = :number WHERE id = :id"),
            {"number": _mint(taken, school_id), "id": student_id},
        )
    return len(rows)


def upgrade() -> None:
    """Drop the draft, its columns, and the guardian block copied onto every child."""
    connection = op.get_bind()
    promoted = _promote(connection)
    removed = _delete_incomplete_drafts(connection)
    numbered = _backfill_numbers(connection)
    print(
        f"no drafts: {promoted} promoted to students, {removed} incomplete removed, "
        f"{numbered} missing numbers minted"
    )

    # The draft's own columns, and the guardian block it kept duplicated.
    op.drop_constraint("uq_student_school_application_no", "student", type_="unique")
    op.drop_index("ix_student_application_no", table_name="student")
    for column in _DROPPED_COLUMNS:
        op.drop_column("student", column)

    # A row in `student` is a student, and every student has a number - so the
    # column stops accepting an empty one. The model still types it as optional so a
    # request can say "mint one for me"; the service always writes a value.
    op.alter_column("student", "admission_number", nullable=False)


def downgrade() -> None:
    """Put the columns back - the drafts this revision removed do **not** come back.

    They were never students, and their rows are in the backup taken before the
    upgrade. Every row that is here *is* a student, so it returns as `Registered`,
    carrying the `admission_number` it was minted from as its application number.
    """
    op.alter_column("student", "admission_number", nullable=True)
    op.add_column("student", sa.Column("guardian_address", _AUTO_STR(), nullable=True))
    op.add_column(
        "student", sa.Column("guardian_occupation", _AUTO_STR(), nullable=True)
    )
    op.add_column("student", sa.Column("guardian_email", _AUTO_STR(), nullable=True))
    op.add_column("student", sa.Column("guardian_phone", _AUTO_STR(), nullable=True))
    op.add_column(
        "student", sa.Column("guardian_relation", _AUTO_STR(), nullable=True)
    )
    op.add_column("student", sa.Column("guardian_name", _AUTO_STR(), nullable=True))
    op.add_column("student", sa.Column("promoted_at", sa.DateTime(), nullable=True))
    op.add_column(
        "student",
        sa.Column("status", _AUTO_STR(), nullable=False, server_default="Registered"),
    )
    op.add_column(
        "student",
        sa.Column("application_no", _AUTO_STR(), nullable=False, server_default=""),
    )
    op.execute(
        "UPDATE student SET application_no = coalesce(admission_number, ''), "
        "promoted_at = coalesce(activated_at, now())"
    )
    op.create_index("ix_student_application_no", "student", ["application_no"])
    op.create_unique_constraint(
        "uq_student_school_application_no", "student", ["school_id", "application_no"]
    )
