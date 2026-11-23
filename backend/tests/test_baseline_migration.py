"""The migration history is one baseline built from the models.

Everything before it was squashed (the development database holds demo data only), so
`alembic upgrade head` on an empty database is the one way a schema is made.
"""

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

VERSIONS = Path("alembic/versions")


def test_there_is_exactly_one_revision_and_it_is_the_baseline():
    files = [p for p in VERSIONS.glob("*.py")]
    assert [p.name for p in files] == ["0001_baseline.py"]
    script = ScriptDirectory.from_config(Config("alembic.ini"))
    assert script.get_heads() == ["0001"]
    assert script.get_revision("0001").down_revision is None


def test_the_baseline_creates_every_model_table():
    from sqlmodel import SQLModel

    from app.core.schema import load_models

    load_models()
    text = (VERSIONS / "0001_baseline.py").read_text(encoding="utf-8")
    created = set(__import__("re").findall(r"op\.create_table\('([^']+)'", text))
    assert created == set(SQLModel.metadata.tables)
