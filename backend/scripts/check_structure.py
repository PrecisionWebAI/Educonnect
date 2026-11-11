"""Is the tree still one feature per folder - and nothing else?

    python scripts/check_structure.py

Four mechanical rules, no opinions:

1. package  - every folder under `app/domains` with Python files has `__init__.py`
2. registry - every `models.py` is listed in `app.core.schema.MODEL_MODULES`
3. mounted  - every `router.py` serves at least one route in the built app
4. tenancy  - `SKIP_SCHOOL` only where a cross-school read is documented

Exit code 1 when a rule is broken: a restructure phase is done only when this and
`api_snapshot.py --check` both pass.
"""

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from app.core.schema import MODEL_MODULES  # noqa: E402

APP = os.path.join(ROOT, "app")
DOMAINS = os.path.join(APP, "domains")

#: Cross-school reads that are deliberate. Keyed by a path fragment (relative to
#: `app/domains`) so a feature keeps its permission after it moves.
ALLOWED_SKIP_SCHOOL = {
    "auth/": "impersonation looks a user up by id, before a school is known",
    "admin/platform/": "the cross-school console - the only place that may see all schools",
    "staff/service.py": "employee codes are unique per school; minting must see them all",
}


def python_dirs() -> list[tuple[str, list[str]]]:
    """(folder, python files) for every folder under `app/domains`, recursively."""
    found = []
    for dirpath, dirnames, filenames in os.walk(DOMAINS):
        dirnames[:] = sorted(d for d in dirnames if d != "__pycache__")
        py = sorted(f for f in filenames if f.endswith(".py"))
        if py:
            found.append((dirpath, py))
    return found


def dotted(dirpath: str) -> str:
    """`.../app/domains/operations/admission` -> `operations.admission`."""
    return os.path.relpath(dirpath, DOMAINS).replace(os.sep, ".")


def mounted_modules() -> set[str]:
    """Every module that actually serves a route, from the app itself.

    Importing the app runs the whole include chain, so a `router.py` that no
    group router mounts simply never appears here - which is the check.
    """
    from app.core.api_surface import endpoint_modules
    from app.main import app  # noqa: PLC0415 - building the app is the check

    return endpoint_modules(app)


def main() -> int:
    problems: list[str] = []
    mounted = mounted_modules()

    for dirpath, filenames in python_dirs():
        key = dotted(dirpath)
        if "__init__.py" not in filenames:
            problems.append(f"package : {key or '.'} has no __init__.py")
        if "models.py" in filenames and key not in MODEL_MODULES:
            problems.append(f"registry: {key}.models is not in MODEL_MODULES")
        if "router.py" in filenames and f"app.domains.{key}" not in mounted:
            problems.append(f"mounted : {key}.router is not included anywhere")

    for dirpath, filenames in python_dirs():
        for name in filenames:
            path = os.path.join(dirpath, name)
            text = open(path, encoding="utf-8").read()
            if "SKIP_SCHOOL" not in text:
                continue
            rel = os.path.relpath(path, DOMAINS).replace(os.sep, "/")
            if not any(fragment in rel for fragment in ALLOWED_SKIP_SCHOOL):
                problems.append(f"tenancy : {rel} reads across schools (SKIP_SCHOOL)")

    for line in problems:
        print(f"[structure] {line}")
    if problems:
        print(f"[structure] {len(problems)} problem(s)")
        return 1

    folders = len(python_dirs())
    print(f"[structure] ok: {folders} packages, {len(MODEL_MODULES)} model modules registered")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
