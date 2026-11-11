"""Every gate a restructure phase must pass, in one command.

    python scripts/verify.py                                 # after each phase

Three gates, in the order that fails fastest:

    compile     - every module still parses
    api surface - no URL was added, removed or moved (scripts/api_surface.json)
    structure   - one feature per folder, models registered, nothing cross-tenant

`python -m pytest tests -q` is deliberately not here: it is the slow gate, and it
is run by hand when a phase touches behaviour (it should never need to).
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
SURFACE = os.path.join(HERE, "api_surface.json")
PY = sys.executable


def run(name: str, args: list[str]) -> bool:
    print(f"[verify] {name} ...")
    result = subprocess.run(args, cwd=BACKEND, capture_output=True, text=True)
    output = (result.stdout + result.stderr).strip()
    if output:
        print("\n".join(f"    {line}" for line in output.splitlines()))
    passed = result.returncode == 0
    print(f"[verify] {name}: {'ok' if passed else 'FAILED'}")
    return passed


def main() -> int:
    gates = [
        ("compile", [PY, "-m", "compileall", "-q", "app", "scripts"]),
        ("api surface", [PY, os.path.join(HERE, "api_snapshot.py"), "--check", SURFACE]),
        ("structure", [PY, os.path.join(HERE, "check_structure.py")]),
    ]
    if not os.path.isfile(SURFACE):
        print(f"[verify] no baseline - run: python scripts/api_snapshot.py --out {SURFACE}")
        return 1

    failed = [name for name, args in gates if not run(name, args)]
    if failed:
        print(f"[verify] failed: {', '.join(failed)}")
        return 1
    print("[verify] all gates passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
