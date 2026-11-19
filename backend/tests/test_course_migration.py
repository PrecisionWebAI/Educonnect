"""The Course migration's contract - a single head and a real downgrade.

The SQL dry-run needs a live PostgreSQL (the migration inspects the existing schema to
make the backfill re-runnable), so this test pins what can be checked without a database:
the revision chain and the presence of both directions.
"""

import importlib.util
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

REVISION = "e2b8c4f7a1d9"
PARENT = "b7d2e4f1a9c3"


def test_the_course_revision_is_the_single_head_with_a_parent_and_a_downgrade():
    script = ScriptDirectory.from_config(Config("alembic.ini"))
    assert script.get_heads() == [REVISION]

    revision = script.get_revision(REVISION)
    assert revision.down_revision == PARENT

    path = Path("alembic/versions/e2b8c4f7a1d9_course_lesson_plans.py")
    spec = importlib.util.spec_from_file_location("course_migration", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.revision == REVISION
    assert module.down_revision == PARENT
    assert callable(module.upgrade)
    assert callable(module.downgrade)
