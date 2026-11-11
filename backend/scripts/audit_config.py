"""Guard the configuration rules, so they stay true after today.

    python scripts/audit_config.py        # exit 1 if a rule is broken

Four rules, each one a mistake this repository has already made once:

1. **One reader.** Settings are read in `app/core/config.py` and nowhere else.
   `os.getenv(...)` scattered through the code is how a value gets a hardcoded
   fallback nobody notices. Passing the environment through (`dict(os.environ)`,
   `os.environ.copy()`) is allowed - that is not reading a setting.

2. **No usable secret defaults.** A key or password field may only default to
   `""` (absent) or a documented throwaway. `SECRET_KEY` defaults to the
   placeholder that the validator refuses outside `local`.

3. **Documented inventory.** Every field of `Settings` appears in
   `backend/.env-example`, so the tracked reference stays the complete list.

4. **Frontend too.** Every `NEXT_PUBLIC_*` the frontend reads appears in
   `frontend/.env.example`.
"""

import ast
import pathlib
import re

#: `backend/` - this file is `backend/scripts/audit_config.py`, whether the repo is
#: checked out as-is or `backend/` alone is mounted at `/app` (the container).
BACKEND = pathlib.Path(__file__).resolve().parents[1]
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


def _env_reads(tree: ast.Module) -> list[int]:
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


def check_single_reader() -> list[str]:
    problems: list[str] = []
    for path in sorted(BACKEND.rglob("*.py")):
        if ".venv" in path.parts or path == CONFIG:
            continue
        if not {"app", "scripts"} & set(path.parts):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:  # a broken file is another check's problem
            continue
        name = path.relative_to(BACKEND)
        problems += [
            f"{name}:{line} reads the environment - read it in config.py instead"
            for line in _env_reads(tree)
        ]
    return problems


def check_secret_defaults(fields: dict[str, object]) -> list[str]:
    problems: list[str] = []
    for name, default in fields.items():
        if not SECRET_NAME.search(name):
            continue
        allowed = PLACEHOLDER_DEFAULTS.get(name, set())
        if default in ("", None) or default in allowed:
            continue
        problems.append(f"config.py: {name} has a usable default ({default!r})")
    return problems


def check_documented(fields: dict[str, object]) -> list[str]:
    text = ENV_EXAMPLE.read_text(encoding="utf-8")
    return [
        f"backend/.env-example does not mention {name}"
        for name in fields
        if name not in text
    ]


def check_frontend() -> list[str]:
    source = FRONTEND / "src"
    if not source.is_dir():
        # Only `backend/` is mounted in the container, so the frontend rule is
        # checked where the whole repo is (CI, or a normal checkout).
        return []
    example = FRONTEND / ".env.example"
    documented = example.read_text(encoding="utf-8") if example.exists() else ""
    used: set[str] = set()
    for path in source.rglob("*.ts*"):
        used.update(re.findall(r"NEXT_PUBLIC_[A-Z0-9_]+", path.read_text(encoding="utf-8")))
    return [
        f"frontend/.env.example does not mention {name}"
        for name in sorted(used)
        if name not in documented
    ]


def main() -> int:
    fields = settings_fields()
    problems = (
        check_single_reader()
        + check_secret_defaults(fields)
        + check_documented(fields)
        + check_frontend()
    )

    print(f"settings         {len(fields)} fields in app/core/config.py")
    print(f"documented       {len(fields)} checked against backend/.env-example")

    if problems:
        print(f"\n{len(problems)} problem(s):")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print("\nOK: one reader, no secret defaults, everything documented.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
