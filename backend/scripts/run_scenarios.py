"""Run the scenario tests inside the API image - no pytest needed.

Why
---
The API image carries no dev dependencies (`test_staff_contacts.py` says so in its own
words), but the scenarios that matter need none: each is a plain function that builds
its own throw-away SQLite database, and every test module that is written that way
exposes `SCENARIOS` (a tuple of `(label, scenario)`) plus a `memory_session()` that
hands out a fresh database. `test_lifecycle.py` and `test_staff_contacts.py` run their
own list under `__main__`; this walks **all** of them the same way, which is what
`_phase4_verify.py` used to do for one phase at a time.

    python scripts/run_scenarios.py              # every module with SCENARIOS
    python scripts/run_scenarios.py lifecycle    # only modules whose name matches

Modules whose scenarios need pytest fixtures of their own (the `test_*` functions that
take `db_session` or `monkeypatch`) are skipped: they are not part of this walk and
their scenarios are not written to stand alone.
"""

from __future__ import annotations

import importlib
import inspect
import os
import sys
import traceback

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

#: Where the test modules live.
_TESTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tests")


def _modules(pattern: str | None) -> list[str]:
    """The importable test modules, oldest name first, optionally name-filtered."""
    names: list[str] = []
    for entry in sorted(os.listdir(_TESTS)):
        if entry.startswith("test_") and entry.endswith(".py"):
            name = entry[:-3]
            if pattern and pattern not in name:
                continue
            names.append(name)
    return names


def _takes_session(scenario) -> bool:
    """True when this scenario expects the freshly built database as its argument.

    The modules disagree on purpose: `test_contacts.py` hands each scenario a session
    that its runner opened, while `test_lifecycle.py` lets its scenarios open their
    own. Both are plain functions, so the signature is the honest way to tell.
    """
    return bool(inspect.signature(scenario).parameters)


def main(argv: list[str]) -> int:
    pattern = argv[0] if argv else None
    ran = 0
    failures = 0
    for name in _modules(pattern):
        try:
            module = importlib.import_module(f"tests.{name}")
        except ImportError as error:
            # A module that needs pytest (or another dev package) is not one of the
            # scenario modules this walk covers - it is skipped, not failed.
            print(f"\n{name}\n  SKIP  ({error})")
            continue
        scenarios = getattr(module, "SCENARIOS", None)
        if not scenarios:
            continue
        #: A module that defines its scenarios declares how to build their database.
        session_factory = getattr(module, "memory_session", None)
        print(f"\n{name}")
        for label, scenario in scenarios:
            ran += 1
            try:
                if session_factory is not None and _takes_session(scenario):
                    with session_factory() as session:
                        scenario(session)
                else:
                    scenario()
                print(f"  PASS  {label}")
            except Exception:  # noqa: BLE001 - a runner reports, it does not raise
                failures += 1
                print(f"  FAIL  {label}")
                traceback.print_exc()
    print(f"\n{ran - failures}/{ran} scenarios passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
