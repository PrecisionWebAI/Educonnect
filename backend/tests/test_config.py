"""Configuration stays a single reader, secret-free, and fully documented.

This used to be a standalone script. It is a test now, because it checks the code
and `scripts/` is for the database. Four rules, each one a mistake this repository
has already made once:

1. **One reader.** Settings are read in `app/core/config.py` and nowhere else.
   `os.getenv(...)` scattered through the code is how a value gets a hardcoded
   fallback nobody notices. Passing the environment through (`dict(os.environ)`,
   `os.environ.copy()`) is not reading a setting, so it stays allowed.
2. **No usable secret defaults.** A key or password field may only default to
   `""` (absent) or a documented throwaway.
3. **Documented inventory.** Every field of `Settings` appears in
   `backend/.env-example`, so the tracked reference stays the complete list.
4. **Frontend too.** Every `NEXT_PUBLIC_*` the frontend reads appears in
   `frontend/.env.example` - skipped when only `backend/` is mounted, as in the
   container.
"""

import ast
import re
from pathlib import Path

#: `backend/` - this file is `backend/tests/test_config.py`, whether the repo is
#: checked out as-is or `backend/` alone is mounted at `/app` (the container).
BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
CONFIG = BACKEND / "app" / "core" / "config.py"
ENV_EXAMPLE = BACKEND / ".env-example"
FRONTEND = ROOT / "frontend"

#: Secret-looking fields that may carry a documented throwaway default.
PLACEHOLDER_DEFAULTS = {
    "SECRET_KEY": {"dev-only-change-me"},
    "LLM_API_KEY": {"ollama"},
}

SECRET_NAME = re.compile(r"(_KEY|_PASSWORD|_SECRET|_TOKEN|_DB_URL)$")

#: Folders inside `frontend/` that are generated, not source.
GENERATED = {"node_modules", ".next", "dist", "build"}


def settings_fields() -> dict[str, object]:
    """`{field: default}` for every field of the `Settings` class."""
    tree = ast.parse(CONFIG.read_text(encoding="utf-8"))
    fields: dict[str, object] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or node.name != "Settings":
            continue
        for item in node.body:
            if not isinstance(item, ast.AnnAssign) or item.value is None:
                continue
            if not isinstance(item.target, ast.Name):
                continue
            value = item.value
            if isinstance(value, ast.Constant):
                fields[item.target.id] = value.value
            elif isinstance(value, ast.Call):  # Field(default=...)
                for keyword in value.keywords:
                    if keyword.arg == "default" and isinstance(
                        keyword.value, ast.Constant
                    ):
                        fields[item.target.id] = keyword.value.value
    return fields


def _is_os_environ(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "environ"
        and isinstance(node.value, ast.Name)
        and node.value.id == "os"
    )


def env_reads(tree: ast.Module) -> list[int]:
    """Lines that actually read the environment - prose mentioning it is fine.

    `dict(os.environ)` and `os.environ.copy()` pass the environment through to a
    child process; they are not reading a setting, and are not flagged.
    """
    lines: list[int] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and _is_os_environ(node.value):
            lines.append(node.lineno)
        elif isinstance(node, ast.Call):
            func = node.func
            if (
                isinstance(func, ast.Attribute)
                and func.attr == "getenv"
                and isinstance(func.value, ast.Name)
                and func.value.id == "os"
            ) or (
                isinstance(func, ast.Attribute)
                and func.attr == "get"
                and _is_os_environ(func.value)
            ):
                lines.append(node.lineno)
    return sorted(set(lines))


def test_settings_is_the_only_environment_reader():
    offenders: list[str] = []
    for path in sorted(BACKEND.rglob("*.py")):
        relative = path.relative_to(BACKEND)
        if ".venv" in relative.parts or path == CONFIG:
            continue
        if not {"app", "scripts"} & set(relative.parts):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:  # a broken file is another check's problem
            continue
        offenders += [f"{relative}:{line}" for line in env_reads(tree)]
    assert not offenders, (
        f"one reader: read the environment in config.py instead: {offenders}"
    )


def test_no_usable_secret_defaults():
    usable = [
        f"{name}={default!r}"
        for name, default in settings_fields().items()
        if SECRET_NAME.search(name)
        and default not in ("", None)
        and default not in PLACEHOLDER_DEFAULTS.get(name, set())
    ]
    assert not usable, f"no secrets: config.py has usable defaults: {usable}"


def test_every_setting_is_documented_in_env_example():
    assert ENV_EXAMPLE.is_file(), f"documented: missing {ENV_EXAMPLE}"
    text = ENV_EXAMPLE.read_text(encoding="utf-8")
    missing = [name for name in settings_fields() if name not in text]
    assert not missing, f"documented: backend/.env-example does not mention: {missing}"


def test_frontend_env_is_documented():
    source = FRONTEND / "src"
    if not source.is_dir():
        # Only `backend/` is mounted in the container, so this rule is checked
        # where the whole repo is (CI, or a normal checkout).
        return

    example = FRONTEND / ".env.example"
    documented = example.read_text(encoding="utf-8") if example.exists() else ""
    used: set[str] = set()
    for path in source.rglob("*.ts*"):
        if GENERATED & set(path.relative_to(FRONTEND).parts):
            continue
        used.update(
            re.findall(r"NEXT_PUBLIC_[A-Z0-9_]+", path.read_text(encoding="utf-8"))
        )

    missing = sorted(name for name in used if name not in documented)
    assert not missing, f"frontend : frontend/.env.example does not mention: {missing}"
