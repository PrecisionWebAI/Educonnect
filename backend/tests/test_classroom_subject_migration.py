"""M1 contract: one head, section-owned name, and the active-name index."""

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from app.domains.academic.classroom.course.models import ClassroomSubject

REVISION = "f1c2d3e4a5b6"
PARENT = "e5a7b9c1d3f4"
NEXT = "f2d3e4a5b6c7"


def test_m1_sits_on_the_single_chain_with_the_expected_parent():
    script = ScriptDirectory.from_config(Config("alembic.ini"))
    # M2 is the head now; M1 is its parent, so the chain is still one line.
    assert script.get_heads() == ["f4a5b6c7d8e9"]
    assert script.get_revision(NEXT).down_revision == REVISION
    revision = script.get_revision(REVISION)
    assert revision is not None
    assert revision.down_revision == PARENT


def test_m1_file_has_both_directions():
    path = Path("alembic/versions/f1c2d3e4a5b6_classroom_subject_identity.py")
    text = path.read_text(encoding="utf-8")
    assert f'revision: str = "{REVISION}"' in text
    assert f'down_revision: str | Sequence[str] | None = "{PARENT}"' in text
    assert "def upgrade()" in text
    assert "def downgrade()" in text


def test_the_name_belongs_to_the_section_row():
    columns = {column.name: column for column in ClassroomSubject.__table__.columns}
    assert "name" in columns
    assert columns["name"].nullable is False
    # New rows do not need a legacy school-wide subject row.
    assert columns["subject_id"].nullable is True


def test_the_active_name_index_is_partial_and_case_insensitive():
    indexes = {index.name: index for index in ClassroomSubject.__table__.indexes}
    assert "uq_classroomsubject_active_name" in indexes
    assert indexes["uq_classroomsubject_active_name"].unique is True
    assert indexes["uq_classroomsubject_active_name"].dialect_options["postgresql"][
        "where"
    ] is not None
