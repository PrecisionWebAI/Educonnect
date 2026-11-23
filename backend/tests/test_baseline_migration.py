"""The migration history is one baseline built from the models, then small steps.

Everything before the baseline was squashed (the development database holds demo data
only), so `alembic upgrade head` on an empty database is the one way a schema is made.
"""

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

VERSIONS = Path("alembic/versions")


def test_the_history_is_the_baseline_plus_a_straight_line_of_small_steps():
    names = sorted(p.name for p in VERSIONS.glob("*.py"))
    assert names[0] == "0001_baseline.py"
    script = ScriptDirectory.from_config(Config("alembic.ini"))
    heads = script.get_heads()
    assert len(heads) == 1
    assert script.get_revision("0001").down_revision is None
    chain = [rev.revision for rev in script.walk_revisions()]
    assert len(chain) == len(names)  # no stray, unreachable revision file


def test_the_baseline_creates_every_model_table():
    from sqlmodel import SQLModel

    from app.core.schema import load_models

    load_models()
    text = (VERSIONS / "0001_baseline.py").read_text(encoding="utf-8")
    created = set(__import__("re").findall(r"op\.create_table\('([^']+)'", text))
    assert created == set(SQLModel.metadata.tables)
