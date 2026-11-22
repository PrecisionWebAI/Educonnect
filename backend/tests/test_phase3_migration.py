"""The Phase 3 migration chain has one head and our revision is on it.

The live database is stamped by `app.core.schema`, but a second head still means
`alembic upgrade head` is ambiguous. This test reads the revision files themselves
without touching a database, so it is safe in an environment where the legacy
chain cannot be replayed from an empty PostgreSQL schema.
"""

import re
from pathlib import Path

VERSIONS = Path(__file__).resolve().parents[1] / "alembic" / "versions"
HEAD_REVISION = "f3e4a5b6c7d8"


def _revisions() -> tuple[dict[str, list[str]], set[str]]:
    revision_pattern = re.compile(
        r'^revision:\s*str\s*=\s*["\']([^"\']+)["\']', re.MULTILINE
    )
    revisions: dict[str, list[str]] = {}
    for path in VERSIONS.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        found = revision_pattern.search(text)
        if found is None:
            continue
        down_part = text.split("down_revision", 1)[-1].split(
            "branch_labels", 1
        )[0]
        parents = re.findall(r'["\']([^"\']+)["\']', down_part)
        revisions[found.group(1)] = parents
    return revisions, set(revisions)


def test_phase_three_migration_chain_has_a_single_head() -> None:
    revisions, known = _revisions()
    parents = {parent for values in revisions.values() for parent in values}
    heads = sorted(revision for revision in known if revision not in parents)
    assert len(heads) == 1, f"alembic has multiple heads: {heads}"
    assert heads[0] == HEAD_REVISION, (
        f"expected the Phase 3 head {HEAD_REVISION}, found {heads[0]}"
    )


def test_our_revision_is_linked_to_known_parents() -> None:
    revisions, known = _revisions()
    parents = revisions[HEAD_REVISION]
    assert parents
    assert set(parents) <= known, f"parent revisions {parents} include a missing one"
