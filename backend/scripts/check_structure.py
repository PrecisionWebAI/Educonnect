"""Is the tree still one feature per folder - and nothing else?

    python scripts/check_structure.py

Five mechanical rules, no opinions:

1. package  - every folder under `app/domains` with Python files has `__init__.py`
2. registry - every `models.py` is listed in `app.core.schema.MODEL_MODULES`
3. mounted  - every `router.py` serves at least one route in the built app
4. tenancy  - `SKIP_SCHOOL` only where a cross-school read is documented
5. groups   - every top-level group is listed in `app/domains/README.md`

Exit code 1 when a rule is broken: a restructure phase is done only when this and
`api_snapshot.py --check` both pass.
"""

import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from app.core.schema import MODEL_MODULES  # noqa: E402

APP = os.path.join(ROOT, "app")
DOMAINS = os.path.join(APP, "domains")
README = os.path.join(DOMAINS, "README.md")

#: The one machine-readable line in `domains/README.md`; the table below it is
#: for humans, this line is what the gate compares with the folders on disk.
GROUPS_LINE = re.compile(r"<!--\s*groups:(.*?)-->", re.S)

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


def documented_groups() -> list[str]:
    """The `<!-- groups: ... -->` line in `domains/README.md`, split into names."""
    if not os.path.isfile(README):
        return []
    match = GROUPS_LINE.search(open(README, encoding="utf-8").read())
    return match.group(1).split() if match else []


def group_dirs() -> list[str]:
    """Top-level folders under `app/domains` - the groups themselves."""
    return sorted(
        name
        for name in os.listdir(DOMAINS)
        if name != "__pycache__" and os.path.isdir(os.path.join(DOMAINS, name))
    )


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

    on_disk = group_dirs()
    documented = documented_groups()
    if not documented:
        problems.append("groups  : README.md has no `<!-- groups: ... -->` line")
    for name in sorted(set(on_disk) - set(documented)):
        problems.append(f"groups  : {name}/ is not listed in domains/README.md")
    for name in sorted(set(documented) - set(on_disk)):
        problems.append(f"groups  : README.md lists {name}/ but that folder is gone")

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
    print(
        f"[structure] ok: {len(on_disk)} groups, {folders} packages, "
        f"{len(MODEL_MODULES)} model modules registered"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
