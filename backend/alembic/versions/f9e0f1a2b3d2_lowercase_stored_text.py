"""Canonical text - bring every stored value into lower-case.

Why:
  Every request body now runs through `app.core.text.CanonicalRequest`, which
  stores text in its canonical form: lower-case. New rows are therefore written
  as "prashant saxena", "class 9", "a", "cbse" - and presentation ("Prashant
  Saxena") is the frontend's job (`lib/format.ts` → `titleCase`).

  Rows written before that rule kept whatever case the operator typed: the
  admission form held "Tanya " / "SAXENA" / "General" / "CBSE" while the class
  catalog held "Class 10", so the *same* value could be spelled two ways and a
  lookup that compared them could miss. This migration normalises the rows that
  are already stored, including the class/section/subject catalog, so the whole
  database speaks one case from here on.

What it does **not** touch (the same policy as `app/core/text.py`):
  * secrets - `user.hashed_password` and friends;
  * prose - notes, reasons, descriptions, messages: a paragraph has no canonical
    form and lower-casing it would corrupt meaning rather than tidy it;
  * identifiers - `application_no`, `employee_code`, `ifsc`, `pan_no`,
    `admission_number`, `transfer_certificate_no`;
  * the fixed vocabularies the workflow compares - `status` ("Draft",
    "Registered"), `priority`, `session`, `needs_transport` ("Yes"), `qtype`,
    `term`, `grade`, `month`, `day`, `qualification`;
  * links and file paths, where case is significant.

Downgrade is deliberately a no-op: the original capitalisation is not recorded
anywhere, so it cannot be restored (a case-only change destroys information in
one direction). Rolling back leaves the data canonical, which every read path
accepts.

Revision ID: f9e0f1a2b3d2
Revises: f9e0f1a2b3d1
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f9e0f1a2b3d2"
down_revision: Union[str, Sequence[str], None] = "f9e0f1a2b3d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


#: The admission form is the biggest surface: almost every column is text the
#: family or the office typed, so all of it is canonical - except the workflow
#: fields (`status`), the prose (`notes`), the identifiers (`application_no`,
#: `transfer_certificate_no`, `old_unique_id`, `aadhaar_id`) and the Yes/No and
#: session vocabularies, which keep the exact wording the screen shows.
ADMISSION_TEXT_COLUMNS: tuple[str, ...] = (
    "student_first_name",
    "student_middle_name",
    "student_last_name",
    "student_email",
    "gender",
    "blood_group",
    "religion",
    "category",
    "mother_tongue",
    "nationality",
    "address",
    "permanent_address",
    "previous_school_name",
    "previous_class_passed",
    "previous_board",
    "father_name",
    "father_occupation",
    "father_phone",
    "father_email",
    "father_annual_income",
    "mother_name",
    "mother_occupation",
    "mother_phone",
    "mother_email",
    "mother_annual_income",
    "guardian_name",
    "guardian_relation",
    "guardian_phone",
    "guardian_email",
    "guardian_occupation",
    "guardian_address",
    "applied_for_class_level",
    "current_class_or_last_class",
    "applied_section_preference",
    "transport_route",
    "separation_dropped_class",
)

#: (table, columns) - a column this database does not have is skipped, so the
#: migration is safe on any deployment that sits between revisions.
LOWERCASE_COLUMNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("user", ("email", "full_name")),
    ("school", ("name", "email", "phone", "address")),
    ("classname", ("classname", "stage")),
    ("section", ("section_name",)),
    ("subject", ("name",)),
    ("classroom", ("name",)),
    ("studentprofile", ("full_name", "guardian_name", "gender")),
    ("studentparentrelationship", ("relationship_type",)),
    ("teacherprofile", ("department",)),
    ("employee", ("department", "designation")),
    (
        "staffprofile",
        (
            "department",
            "address",
            "email",
            "phone",
            "emergency_contact",
            "bank_name",
            "bank_account_no",
        ),
    ),
    ("student_admission_form", ADMISSION_TEXT_COLUMNS),
    (
        "hiringcandidate",
        ("department", "applied_for", "subject_name", "phone", "email"),
    ),
    ("feestructure", ("name",)),
    ("paperdraft", ("class_name", "subject", "board", "language")),
    ("exam", ("class_name", "subject")),
    ("homeworkassignment", ("subject",)),
    ("classlog", ("subject",)),
    ("librarybook", ("author", "category")),
    ("transportroute", ("name", "driver")),
    ("bus", ("name",)),
    ("meeting", ("with_whom", "room")),
    ("timetableperiod", ("room",)),
    ("ticket", ("category",)),
)


def _existing_columns(connection: sa.Connection, table: str) -> set[str]:
    """The columns of `table` that this database actually has."""
    rows = connection.execute(
        sa.text(
            "SELECT column_name FROM information_schema.columns"
            " WHERE table_name = :table"
        ),
        {"table": table},
    )
    return {row[0] for row in rows}


def upgrade() -> None:
    """Lower-case every stored value that has a canonical form."""
    connection = op.get_bind()
    changed = 0
    for table, columns in LOWERCASE_COLUMNS:
        present = _existing_columns(connection, table)
        if not present:
            continue
        for column in columns:
            if column not in present:
                continue
            result = connection.execute(
                sa.text(
                    f'UPDATE "{table}"'
                    f' SET "{column}" = lower(btrim("{column}"))'
                    f' WHERE "{column}" IS NOT NULL'
                    f' AND "{column}" <> lower(btrim("{column}"))'
                )
            )
            changed += result.rowcount or 0
    print(f"[lowercase] {changed} value(s) brought into canonical form")


def downgrade() -> None:
    """Nothing to undo: the previous capitalisation was never recorded."""


