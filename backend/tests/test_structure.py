"""The tree is still one feature per folder - and nothing else.

This gate used to live in `scripts/`, next to the database tooling. It is a test
now: `scripts/` is for the database (sync, schema, seeds), and everything that
checks the code lives in `tests/`, where `make test` and CI already run it.

Seven rules, the same ones `app/domains/README.md` documents:

1. package  - every folder under `app/domains` with Python files has `__init__.py`
2. registry - every `models.py` is listed in `app.core.schema.MODEL_MODULES`
3. mounted  - every `router.py` serves at least one route in the built app
4. tenancy  - `SKIP_SCHOOL` only where a cross-school read is documented
5. groups   - every top-level group is listed in `app/domains/README.md`
6. tenant   - every mapped table is school-owned, or named in `GLOBAL_TABLES`
7. no SQL   - no module under `app/domains` hands a statement over as text
"""

import importlib
import re
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
DOMAINS = BACKEND / "app" / "domains"
README = DOMAINS / "README.md"

#: The one machine-readable line in `domains/README.md`; the table below it is for
#: humans, this line is what the rule compares with the folders on disk.
GROUPS_LINE = re.compile(r"<!--\s*groups:(.*?)-->", re.S)

#: Cross-school reads that are deliberate. Keyed by a path fragment (relative to
#: `app/domains`) so a feature keeps its permission after it moves.
ALLOWED_SKIP_SCHOOL = {
    "auth/": "impersonation looks a user up by id, before a school is known",
    "admin/platform/": "the cross-school console, the only place that may see all schools",
    "staff/service.py": "employee codes are unique per school; minting must see them all",
}

#: Tables that are genuinely **not** school-owned, each with the reason it is not.
#: Everything else must inherit `TenantMixin`: a table without `school_id` is
#: invisible to the tenant filter (`app/core/db.py`), so one query over it would
#: show every school's rows. Adding a table is therefore a decision, not a default.
GLOBAL_TABLES = {
    "school": "the tenants themselves - one row per school",
    "classname": "the class catalog (nursery .. 12) the schools pick from",
    "section": "the section catalog (A .. J) the schools pick from",
    "role": "the RBAC catalog, shared by every school",
    "permission": "the RBAC catalog, shared by every school",
    "rolepermission": "which permission a catalog role carries",
    "user_role": "which person holds which catalog role (scoping is on `user`)",
    "impersonationlog": "the platform console's audit of who viewed whom",
}


def python_dirs() -> list[tuple[Path, list[str]]]:
    """(folder, python files) for every folder under `app/domains`, recursively."""
    found: list[tuple[Path, list[str]]] = []
    for folder in sorted(DOMAINS.rglob("*")):
        if not folder.is_dir() or "__pycache__" in folder.parts:
            continue
        files = sorted(path.name for path in folder.iterdir() if path.suffix == ".py")
        if files:
            found.append((folder, files))
    return found


def dotted(folder: Path) -> str:
    """`.../app/domains/operations/admission` -> `operations.admission`."""
    return folder.relative_to(DOMAINS).as_posix().replace("/", ".")


def documented_groups() -> list[str]:
    """The `<!-- groups: ... -->` line in `domains/README.md`, split into names."""
    if not README.is_file():
        return []
    match = GROUPS_LINE.search(README.read_text(encoding="utf-8"))
    return match.group(1).split() if match else []


def group_dirs() -> list[str]:
    """Top-level folders under `app/domains` - the groups themselves."""
    return sorted(
        path.name
        for path in DOMAINS.iterdir()
        if path.is_dir() and path.name != "__pycache__"
    )


def test_every_package_has_init():
    missing = [
        dotted(folder) or "."
        for folder, files in python_dirs()
        if "__init__.py" not in files
    ]
    assert not missing, f"package : these folders have no __init__.py: {missing}"


def test_every_models_module_is_registered():
    from app.core.schema import MODEL_MODULES

    unregistered = [
        f"{dotted(folder)}.models"
        for folder, files in python_dirs()
        if "models.py" in files and dotted(folder) not in MODEL_MODULES
    ]
    assert not unregistered, (
        f"registry: these modules are missing from MODEL_MODULES: {unregistered}"
    )


def test_every_router_is_mounted():
    from app.core.api_surface import endpoint_modules
    from app.main import app  # importing the app runs the whole include chain

    mounted = endpoint_modules(app)
    unmounted = [
        f"{dotted(folder)}.router"
        for folder, files in python_dirs()
        if "router.py" in files and f"app.domains.{dotted(folder)}" not in mounted
    ]
    assert not unmounted, f"mounted : these routers are included nowhere: {unmounted}"


def test_skip_school_only_where_documented():
    offenders = []
    for folder, files in python_dirs():
        for name in files:
            path = folder / name
            if "SKIP_SCHOOL" not in path.read_text(encoding="utf-8"):
                continue
            relative = path.relative_to(DOMAINS).as_posix()
            if not any(fragment in relative for fragment in ALLOWED_SKIP_SCHOOL):
                offenders.append(relative)
    assert not offenders, (
        f"tenancy : these read across schools (SKIP_SCHOOL): {offenders}"
    )


#: `session.exec("select ...")` / `session.execute("insert ...")` - a statement the
#: tenant filter cannot see, because the listeners rewrite ORM statements, not text.
STRING_SQL = re.compile(r"\b(?:session\.)?exec(?:ute)?\(\s*[fr]?[\"']")


def mapped_tables() -> dict[str, type]:
    """`{table name: model class}` for every table the app maps.

    The models are imported first: a class is only mapped once its module has run,
    which is exactly what `MODEL_MODULES` is the list of.
    """
    from sqlmodel import SQLModel

    from app.core.schema import MODEL_MODULES

    for domain in MODEL_MODULES:
        importlib.import_module(f"app.domains.{domain}.models")

    def walk(cls):
        for subclass in cls.__subclasses__():
            yield subclass
            yield from walk(subclass)

    return {
        model.__table__.name: model
        for model in walk(SQLModel)
        if "__table__" in model.__dict__
    }


def test_every_table_is_school_owned_or_global_on_purpose():
    """A table is either `TenantMixin` (filtered) or named in `GLOBAL_TABLES` (and then not).

    Both halves matter: a school-owned table that forgot the mixin is a leak, and a
    table listed as global but actually scoped means the list has stopped describing
    the code - which is how an allow-list rots into a lie.
    """
    from app.core.tenancy import TenantMixin

    tables = mapped_tables()

    unscoped = sorted(
        name
        for name, model in tables.items()
        if name not in GLOBAL_TABLES and not issubclass(model, TenantMixin)
    )
    assert not unscoped, (
        f"tenant  : these tables carry no school_id - inherit TenantMixin, or add "
        f"them to GLOBAL_TABLES with a reason: {unscoped}"
    )

    stale = sorted(set(GLOBAL_TABLES) - set(tables))
    assert not stale, f"tenant  : GLOBAL_TABLES lists tables that are gone: {stale}"

    contradictory = sorted(
        name
        for name, model in tables.items()
        if name in GLOBAL_TABLES and issubclass(model, TenantMixin)
    )
    assert not contradictory, (
        f"tenant  : these tables are school-owned, so they do not belong in "
        f"GLOBAL_TABLES: {contradictory}"
    )


def test_no_domain_runs_its_own_sql():
    """A statement handed over as text is invisible to the tenant filter."""
    offenders = [
        f"{path.relative_to(DOMAINS).as_posix()}:{number}"
        for folder, files in python_dirs()
        for name in files
        for path in [folder / name]
        for number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        )
        if STRING_SQL.search(line)
    ]
    assert not offenders, (
        f"no SQL   : use select(Model)/session.get so the school filter applies: "
        f"{offenders}"
    )


def test_groups_match_the_domains_readme():
    if not README.is_file():
        # `*.md` stays out of the Docker image (see `.dockerignore`), so this rule
        # can only mean something in a source checkout - a missing doc in the
        # image is not drift, but a doc that is there and wrong is.
        return

    documented = set(documented_groups())
    on_disk = set(group_dirs())
    assert documented, "groups  : domains/README.md has no `<!-- groups: ... -->` line"
    assert not on_disk - documented, (
        f"groups  : these folders are not listed in domains/README.md: "
        f"{sorted(on_disk - documented)}"
    )
    assert not documented - on_disk, (
        f"groups  : domains/README.md lists folders that are gone: "
        f"{sorted(documented - on_disk)}"
    )
