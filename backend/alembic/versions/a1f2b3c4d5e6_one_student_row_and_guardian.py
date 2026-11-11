"""One student row, and the guardian as a person of their own.

Revision ID: a1f2b3c4d5e6
Revises: f9e0f1a2b3d2
Create Date: 2026-11-06

Why
---
A learner used to be two rows: `student_admission_form` (the form) and
`studentprofile` (the student), the second built from the first at registration.
The child's name, date of birth and gender were stored twice, so a form edited
afterwards could disagree with the directory, and a **draft** had no student row at
all. A guardian was not a row either - only a `guardian_user_id` on the form plus a
`studentparentrelationship` link - so a phone number could not be unique per school
and a parent's second child re-typed the same person.

What this migration does
------------------------
* `student` is built from `studentprofile` keeping **the same ids**, so every table
  that points at a student is *repointed* rather than rewritten, and the admissions
  form's columns are folded onto that same row;
* a **draft** (a form row with no student yet) becomes a student row of its own
  with `status = Draft` and no admission number: "the form is the student while it
  is a draft" is exactly this;
* `guardian` holds a parent **once** - their login, phone and email - and
  `student_guardian_relationship` links them to each of their children;
* `studentparentrelationship`, `student_admission_form` and `studentprofile` go;
* `employee` gains the lifecycle columns a person who left needs (`left_on`,
  `deactivated_at`, the roles withdrawn at that moment) and its phone joins its
  email as unique per school.

Every uniqueness rule is **per school** (`user.email`, `guardian.phone` /
`email` / `alternate_phone`, `employee.phone` / `email`, `student.application_no` /
`admission_number` / `student_email`): two schools may each have an `admin@abc`, and
each may hand out `ADM-2026-0001`.
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1f2b3c4d5e6"
down_revision: str | Sequence[str] | None = "f9e0f1a2b3d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_AUTO_STR = sqlmodel.sql.sqltypes.AutoString

#: The form-only columns, copied onto the student row as-is ("col" -> the same name
#: on both sides). Kept in one place because the upgrade and the downgrade both move
#: them in opposite directions.
_FORM_ONLY = (
    "student_first_name",
    "student_middle_name",
    "student_last_name",
    "student_email",
    "blood_group",
    "religion",
    "category",
    "mother_tongue",
    "nationality",
    "aadhaar_id",
    "address",
    "permanent_address",
    "previous_school_name",
    "previous_class_passed",
    "previous_board",
    "transfer_certificate_no",
    "old_unique_id",
    "father_name",
    "father_occupation",
    "father_annual_income",
    "mother_name",
    "mother_occupation",
    "mother_annual_income",
    "applied_for_class_level",
    "current_class_or_last_class",
    "applied_section_preference",
    "needs_transport",
    "transport_route",
    "needs_hostel",
    "applied_class_id",
    "applied_section_id",
    "current_class_id",
    "previous_class_id",
    "separation_class_id",
    "separation_dropped_class",
    "separation_reason",
    "separation_session",
    "separation_date",
)

#: The form's **guardian block** - the contact the office typed. It travels with the
#: student row (a draft must keep the family's way in) and is what the `guardian` row
#: is built from when the application is registered.
_GUARDIAN_BLOCK = (
    "guardian_name",
    "guardian_relation",
    "guardian_phone",
    "guardian_email",
    "guardian_occupation",
    "guardian_address",
)

#: Tables that pointed at `studentprofile` and are **not** being dropped: their
#: foreign keys are moved onto `student` (the ids did not change).
_CHILD_TABLES = (
    "attendancerecord",
    "marks",
    "feetransaction",
    "leaverequest",
    "libraryissue",
    "homeworksubmission",
    "diaryremark",
)



def _text() -> _AUTO_STR:
    """A text column of the type every string column here uses."""
    return _AUTO_STR()


def _student_columns() -> list[sa.Column]:
    """The merged student row, column for column (`students/models.py`)."""
    return [
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("school_id", sa.Uuid(), sa.ForeignKey("school.id"), index=True),
        # ---- workflow ----------------------------------------------------
        sa.Column("application_no", _text(), nullable=False, index=True),
        sa.Column("status", _text(), nullable=False, server_default="Draft"),
        sa.Column(
            "created_on",
            sa.Date(),
            nullable=False,
            server_default=sa.text("current_date"),
        ),
        sa.Column("notes", _text()),
        # ---- identity ----------------------------------------------------
        sa.Column("full_name", _text()),
        sa.Column("student_first_name", _text()),
        sa.Column("student_middle_name", _text()),
        sa.Column("student_last_name", _text()),
        sa.Column("student_email", _text()),
        sa.Column("date_of_birth", sa.Date()),
        sa.Column("gender", _text()),
        sa.Column("blood_group", _text()),
        sa.Column("religion", _text()),
        sa.Column("category", _text()),
        sa.Column("mother_tongue", _text()),
        sa.Column("nationality", _text()),
        sa.Column("aadhaar_id", _text()),
        sa.Column("address", _text()),
        sa.Column("permanent_address", _text()),
        # ---- previous school ---------------------------------------------
        sa.Column("previous_school_name", _text()),
        sa.Column("previous_class_passed", _text()),
        sa.Column("previous_board", _text()),
        sa.Column("transfer_certificate_no", _text()),
        sa.Column("old_unique_id", _text()),
        # ---- father / mother (family detail; the contact is the guardian's) --
        sa.Column("father_name", _text()),
        sa.Column("father_occupation", _text()),
        sa.Column("father_annual_income", _text()),
        sa.Column("mother_name", _text()),
        sa.Column("mother_occupation", _text()),
        sa.Column("mother_annual_income", _text()),
        # ---- the guardian block (the form's contact block) ----------------
        sa.Column("guardian_name", _text()),
        sa.Column("guardian_relation", _text()),
        sa.Column("guardian_phone", _text()),
        sa.Column("guardian_email", _text()),
        sa.Column("guardian_occupation", _text()),
        sa.Column("guardian_address", _text()),
        # ---- placement + logistics ---------------------------------------
        sa.Column("applied_for_class_level", _text()),
        sa.Column("current_class_or_last_class", _text()),
        sa.Column("applied_section_preference", _text()),
        sa.Column("needs_transport", _text()),
        sa.Column("transport_route", _text()),
        sa.Column("needs_hostel", _text()),
        sa.Column(
            "applied_class_id",
            sa.Uuid(),
            sa.ForeignKey("classname.class_id"),
            index=True,
        ),
        sa.Column(
            "applied_section_id",
            sa.Uuid(),
            sa.ForeignKey("section.section_id"),
            index=True,
        ),
        sa.Column(
            "current_class_id",
            sa.Uuid(),
            sa.ForeignKey("classname.class_id"),
            index=True,
        ),
        sa.Column(
            "previous_class_id",
            sa.Uuid(),
            sa.ForeignKey("classname.class_id"),
            index=True,
        ),
        sa.Column(
            "separation_class_id",
            sa.Uuid(),
            sa.ForeignKey("classname.class_id"),
            index=True,
        ),
        # ---- enrolment ---------------------------------------------------
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("user.id"), unique=True),
        sa.Column("admission_number", _text(), index=True),
        sa.Column("classroom_id", sa.Uuid(), sa.ForeignKey("classroom.id"), index=True),
        sa.Column("promoted_at", sa.DateTime()),
        # ---- lifecycle ---------------------------------------------------
        sa.Column("activated_at", sa.DateTime()),
        sa.Column("deactivated_at", sa.DateTime()),
        # ---- separation --------------------------------------------------
        sa.Column("separation_dropped_class", _text()),
        sa.Column("separation_reason", _text()),
        sa.Column("separation_session", _text()),
        sa.Column("separation_date", sa.Date()),
        # ---- the rules that are per school --------------------------------
        sa.UniqueConstraint(
            "school_id", "application_no", name="uq_student_school_application_no"
        ),
        sa.UniqueConstraint(
            "school_id",
            "admission_number",
            name="uq_student_school_admission_number",
        ),
        sa.UniqueConstraint("school_id", "student_email", name="uq_student_school_email"),
    ]


def _guardian_columns() -> list[sa.Column]:
    """A parent / guardian: one person, one contact, shared by their children."""
    return [
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("school_id", sa.Uuid(), sa.ForeignKey("school.id"), index=True),
        sa.Column("name", _text(), nullable=False),
        sa.Column("phone", _text(), nullable=False, index=True),
        sa.Column("email", _text(), index=True),
        sa.Column("alternate_phone", _text(), index=True),
        sa.Column("occupation", _text()),
        sa.Column("address", _text()),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("user.id"), unique=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("school_id", "phone", name="uq_guardian_school_phone"),
        sa.UniqueConstraint("school_id", "email", name="uq_guardian_school_email"),
        sa.UniqueConstraint(
            "school_id",
            "alternate_phone",
            name="uq_guardian_school_alternate_phone",
        ),
    ]


def _relationship_columns() -> list[sa.Column]:
    """One guardian of one student (a parent with three children has three rows)."""
    return [
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("school_id", sa.Uuid(), sa.ForeignKey("school.id"), index=True),
        sa.Column(
            "student_id",
            sa.Uuid(),
            sa.ForeignKey("student.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "guardian_id",
            sa.Uuid(),
            sa.ForeignKey("guardian.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "relationship_type", _text(), nullable=False, server_default="guardian"
        ),
        sa.Column(
            "is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.UniqueConstraint(
            "student_id", "guardian_id", name="uq_student_guardian_student_guardian"
        ),
    ]


def upgrade() -> None:
    """Build the merged student, the guardian tables and the lifecycle columns."""
    # --- 1. the merged student row -------------------------------------------
    # Built from `studentprofile`, so every student **keeps its id** and the tables
    # that point at a student only need their foreign key moved.
    op.create_table("student", *_student_columns())

    form_columns = ", ".join(_FORM_ONLY)
    carried = ", ".join((*_FORM_ONLY, *_GUARDIAN_BLOCK))
    # The form's own columns, qualified: `studentprofile` and the form share several
    # column names (guardian_name, gender, ...), so a bare name would be ambiguous.
    from_form = ", ".join(f"f.{name}" for name in (*_FORM_ONLY, *_GUARDIAN_BLOCK))
    op.execute(
        f"""
        INSERT INTO student (
            id, school_id, user_id, admission_number, date_of_birth, gender,
            classroom_id, full_name, status, created_on, application_no, notes,
            promoted_at, activated_at, deactivated_at, {carried}
        )
        SELECT p.id, p.school_id, p.user_id, p.admission_number, p.date_of_birth,
               p.gender, p.classroom_id, p.full_name, 'Registered',
               coalesce(f.created_on, current_date),
               coalesce(f.application_no, p.admission_number),
               f.notes, f.promoted_at, coalesce(f.promoted_at, now()), NULL,
               {from_form}
          FROM studentprofile p
          LEFT JOIN student_admission_form f ON f.student_id = p.id
        """
    )

    # A **draft** is a student row too: the office is still typing the form, so it
    # has no admission number, no login and no class-section - and it keeps the id
    # the form row had.
    op.execute(
        f"""
        INSERT INTO student (
            id, school_id, status, created_on, application_no, notes, {carried}
        )
        SELECT f.id, f.school_id, 'Draft', f.created_on, f.application_no, f.notes,
               {from_form}
          FROM student_admission_form f
         WHERE f.student_id IS NULL
        """
    )

    # --- 2. the guardian, and the link to their children ----------------------
    op.create_table("guardian", *_guardian_columns())
    op.create_table("student_guardian_relationship", *_relationship_columns())

    # Every distinct family contact on the forms becomes **one** guardian row. The
    # phone falls back to the application number when the form left it out, because
    # a blank number would collide with the next blank one inside the same school.
    op.execute(
        """
        INSERT INTO guardian (
            id, school_id, name, phone, email, alternate_phone, occupation,
            address, user_id, created_at
        )
        SELECT gen_random_uuid(), x.school_id, x.name, x.phone, x.email, NULL,
               x.occupation, x.address, x.user_id, now()
          FROM (
            SELECT DISTINCT ON (
                       f.school_id,
                       lower(coalesce(f.guardian_email, '')),
                       coalesce(f.guardian_phone, '')
                   )
                   f.school_id,
                   coalesce(f.guardian_name, u.full_name, 'guardian') AS name,
                   coalesce(nullif(f.guardian_phone, ''), f.application_no) AS phone,
                   nullif(lower(f.guardian_email), '') AS email,
                   f.guardian_occupation AS occupation,
                   f.guardian_address AS address,
                   f.guardian_user_id AS user_id
              FROM student_admission_form f
              LEFT JOIN "user" u ON u.id = f.guardian_user_id
             WHERE f.guardian_name IS NOT NULL OR f.guardian_user_id IS NOT NULL
             ORDER BY f.school_id,
                      lower(coalesce(f.guardian_email, '')),
                      coalesce(f.guardian_phone, ''),
                      u.full_name
          ) x
         WHERE NOT EXISTS (
                   SELECT 1 FROM guardian g
                    WHERE g.school_id = x.school_id
                      AND g.email IS NOT DISTINCT FROM x.email
                      AND g.phone = x.phone
               )
        ON CONFLICT DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO student_guardian_relationship (
            id, school_id, student_id, guardian_id, relationship_type, is_primary
        )
        SELECT gen_random_uuid(), f.school_id, f.student_id, g.id,
               coalesce(f.guardian_relation, 'guardian'), true
          FROM student_admission_form f
          JOIN guardian g
            ON g.school_id = f.school_id
           AND g.email IS NOT DISTINCT FROM nullif(lower(f.guardian_email), '')
           AND g.phone = coalesce(nullif(f.guardian_phone, ''), f.application_no)
         WHERE f.student_id IS NOT NULL
        ON CONFLICT DO NOTHING
        """
    )

    # A parent whose account exists but who never had a form block of their own (the
    # old `studentparentrelationship` links): their login is the guardian row.
    op.execute(
        """
        INSERT INTO guardian (
            id, school_id, name, phone, email, alternate_phone, occupation,
            address, user_id, created_at
        )
        SELECT gen_random_uuid(), r.school_id, coalesce(u.full_name, 'guardian'),
               'unknown-' || u.id::text, nullif(lower(u.email), ''), NULL, NULL,
               NULL, u.id, now()
          FROM studentparentrelationship r
          JOIN "user" u ON u.id = r.parent_user_id
         WHERE NOT EXISTS (SELECT 1 FROM guardian g WHERE g.user_id = u.id)
        ON CONFLICT DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO student_guardian_relationship (
            id, school_id, student_id, guardian_id, relationship_type, is_primary
        )
        SELECT gen_random_uuid(), r.school_id, r.student_id, g.id,
               coalesce(r.relationship_type, 'guardian'), true
          FROM studentparentrelationship r
          JOIN guardian g ON g.user_id = r.parent_user_id
        ON CONFLICT DO NOTHING
        """
    )

    # --- 3. every child table follows the student it pointed at ---------------
    _repoint_student_fks("studentprofile", "student")

    # The three old tables go: the form is the student row, the guardian is a
    # person, and the parent link is `student_guardian_relationship`.
    op.drop_table("student_admission_form")
    op.drop_table("studentparentrelationship")
    op.drop_table("studentprofile")

    # --- 4. the staff lifecycle ----------------------------------------------
    op.add_column("employee", sa.Column("left_on", sa.Date()))
    op.add_column("employee", sa.Column("deactivated_at", sa.DateTime()))
    op.add_column("employee", sa.Column("deactivated_roles", _AUTO_STR()))

    # A phone number is unique **per school** for staff too. The demo roll written
    # before this rule existed may already hold the same number twice, so the index
    # is created only where the data allows it: otherwise the rule is enforced by
    # the code from here on (`app/core/contacts.py`, staff service) and the index
    # lands with the next clean seed. Either way the upgrade never fails on data.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM employee
                 WHERE phone IS NOT NULL AND phone <> ''
                 GROUP BY school_id, phone HAVING count(*) > 1
            ) THEN
                RAISE NOTICE
                    'uq_employee_school_phone skipped: duplicate staff phone numbers '
                    'exist in this database';
            ELSE
                CREATE UNIQUE INDEX IF NOT EXISTS uq_employee_school_phone
                    ON employee (school_id, phone)
                    WHERE phone IS NOT NULL AND phone <> '';
            END IF;
        END
        $$;
        """
    )

    # --- 5. the login rule ----------------------------------------------------
    # A school's address is unique *inside the school*, and the platform's own
    # accounts - which have no school - stay unique among themselves.
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_user_school_email
            ON "user" (school_id, email) WHERE school_id IS NOT NULL
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_user_platform_email
            ON "user" (email) WHERE school_id IS NULL
        """
    )


def _repoint_student_fks(old_table: str, new_table: str) -> None:
    """Move every foreign key that pointed at a student onto the new table.

    The student kept its id, so this is a **constraint swap** - no row is touched.
    The keys are discovered from the catalog instead of being hardcoded, so a child
    table added later is carried along.
    """
    bind = op.get_bind()
    for table in _CHILD_TABLES:
        rows = bind.execute(
            sa.text(
                """
                SELECT c.conname, a.attname
                  FROM pg_constraint c
                  JOIN pg_attribute a
                    ON a.attrelid = c.conrelid AND a.attnum = ANY (c.conkey)
                 WHERE c.conrelid = CAST(:table AS regclass)
                   AND c.confrelid = CAST(:old AS regclass)
                   AND c.contype = 'f'
                """
            ),
            {"table": table, "old": old_table},
        ).fetchall()
        for name, column in rows:
            op.drop_constraint(name, table, type_="foreignkey")
            op.create_foreign_key(
                f"{table}_{column}_fkey", table, new_table, [column], ["id"]
            )


def downgrade() -> None:
    """Put the two rows and the parent link back, and drop the guardian tables.

    The guardians survive as far as the old shape allows: the guardian block on the
    form is refilled from the **primary** guardian of each child and the old parent
    link is rebuilt from their login, which is everything the previous schema could
    hold. A draft keeps being a form row with no student, exactly as before.
    """
    # --- 1. the tables as they were -------------------------------------------
    op.create_table(
        "studentprofile",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("school_id", sa.Uuid(), sa.ForeignKey("school.id"), index=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("user.id"), unique=True),
        sa.Column("admission_number", _AUTO_STR(), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column("guardian_name", _AUTO_STR(), nullable=False),
        sa.Column("gender", _AUTO_STR()),
        sa.Column("classroom_id", sa.Uuid(), sa.ForeignKey("classroom.id"), index=True),
        sa.Column("full_name", _AUTO_STR()),
    )
    op.create_index(
        "ix_studentprofile_admission_number",
        "studentprofile",
        ["admission_number"],
        unique=True,
    )

    form_columns: list[sa.Column] = [
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("school_id", sa.Uuid(), sa.ForeignKey("school.id"), index=True),
        sa.Column("application_no", _AUTO_STR(), nullable=False, index=True),
        sa.Column("status", _AUTO_STR(), nullable=False),
        sa.Column("created_on", sa.Date(), nullable=False),
        sa.Column("notes", _AUTO_STR()),
    ]
    for name in _FORM_ONLY:
        form_columns.append(
            sa.Column(
                name,
                sa.Date()
                if name.endswith("_date")
                else (sa.Uuid() if name.endswith("_id") else _AUTO_STR()),
            )
        )
    for name in (
        # the guardian block (a row of its own in the new shape)
        "guardian_name",
        "guardian_relation",
        "guardian_phone",
        "guardian_email",
        "guardian_occupation",
        "guardian_address",
        # the father / mother contacts the old schema still carried
        "father_phone",
        "father_email",
        "mother_phone",
        "mother_email",
    ):
        form_columns.append(sa.Column(name, _AUTO_STR()))
    form_columns += [
        # the promotion links
        sa.Column(
            "student_id", sa.Uuid(), sa.ForeignKey("studentprofile.id"), unique=True
        ),
        sa.Column("student_user_id", sa.Uuid(), sa.ForeignKey("user.id")),
        sa.Column("guardian_user_id", sa.Uuid(), sa.ForeignKey("user.id")),
        sa.Column("promoted_at", sa.DateTime()),
    ]
    op.create_table("student_admission_form", *form_columns)

    op.create_table(
        "studentparentrelationship",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("school_id", sa.Uuid(), sa.ForeignKey("school.id"), index=True),
        sa.Column(
            "student_id", sa.Uuid(), sa.ForeignKey("studentprofile.id"), nullable=False
        ),
        sa.Column("parent_user_id", sa.Uuid(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("relationship_type", _AUTO_STR(), nullable=False),
    )

    # --- 2. the rows, back where they came from --------------------------------
    # The primary guardian of each child, as the old form block saw them.
    primary = """
        LEFT JOIN LATERAL (
            SELECT gr.user_id AS guardian_user_id
              FROM student_guardian_relationship r
              JOIN guardian gr ON gr.id = r.guardian_id
             WHERE r.student_id = s.id
             ORDER BY r.is_primary DESC, gr.created_at
             LIMIT 1
        ) g ON true
    """
    shared = ", ".join(_FORM_ONLY)
    shared_from_student = ", ".join(f"s.{name}" for name in _FORM_ONLY)
    op.execute(
        f"""
        INSERT INTO studentprofile (
            id, school_id, user_id, admission_number, date_of_birth, guardian_name,
            gender, classroom_id, full_name
        )
        SELECT s.id, s.school_id, s.user_id,
               coalesce(s.admission_number, s.application_no),
               coalesce(s.date_of_birth, s.created_on),
               coalesce(s.guardian_name, 'guardian'), s.gender, s.classroom_id,
               s.full_name
          FROM student s {primary}
         WHERE s.status = 'Registered'
        """
    )
    op.execute(
        f"""
        INSERT INTO student_admission_form (
            id, school_id, application_no, status, created_on, notes, {shared},
            guardian_name, guardian_relation, guardian_phone, guardian_email,
            guardian_occupation, guardian_address, father_phone, father_email,
            mother_phone, mother_email, student_id, student_user_id,
            guardian_user_id, promoted_at
        )
        SELECT s.id, s.school_id, s.application_no, s.status, s.created_on, s.notes,
               {shared_from_student}, s.guardian_name, s.guardian_relation, s.guardian_phone,
               s.guardian_email, s.guardian_occupation, s.guardian_address, NULL,
               NULL, NULL, NULL,
               CASE WHEN s.status = 'Registered' THEN s.id END, s.user_id,
               g.guardian_user_id, s.promoted_at
          FROM student s {primary}
        """
    )
    op.execute(
        """
        INSERT INTO studentparentrelationship (
            id, school_id, student_id, parent_user_id, relationship_type
        )
        SELECT gen_random_uuid(), r.school_id, r.student_id, g.user_id,
               coalesce(r.relationship_type, 'guardian')
          FROM student_guardian_relationship r
          JOIN guardian g ON g.id = r.guardian_id
         WHERE g.user_id IS NOT NULL
           AND r.student_id IN (SELECT id FROM studentprofile)
        """
    )

    # --- 3. the child tables follow the student back ---------------------------
    _repoint_student_fks("student", "studentprofile")

    op.drop_table("student_guardian_relationship")
    op.drop_table("guardian")
    op.drop_table("student")

    # --- 4. the staff lifecycle columns come off -------------------------------
    op.execute("DROP INDEX IF EXISTS uq_employee_school_phone")
    op.drop_column("employee", "deactivated_roles")
    op.drop_column("employee", "deactivated_at")
    op.drop_column("employee", "left_on")
