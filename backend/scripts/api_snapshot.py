"""Freeze the API surface, so moving a module can never move a URL.

    python scripts/api_snapshot.py --out api_surface.json    # before a restructure
    python scripts/api_snapshot.py --check api_surface.json  # after every phase

Only `METHOD path` pairs are compared - no tags, no ordering - because those are
what the frontend and the tests actually depend on. A phase is finished when this
says "surface unchanged".
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def surface() -> list[str]:
    """Every method+path the app answers, sorted (see `app/core/api_surface.py`)."""
    from app.core.api_surface import entries
    from app.main import app  # noqa: PLC0415 - importing the app is the work

    return entries(app)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, help="save the current surface here")
    parser.add_argument("--check", type=Path, help="compare against a saved surface")
    args = parser.parse_args()

    current = surface()
    if args.out:
        args.out.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
        print(f"[api] surface saved: {len(current)} routes -> {args.out}")

    if args.check:
        expected = json.loads(args.check.read_text(encoding="utf-8"))
        removed = sorted(set(expected) - set(current))
        added = sorted(set(current) - set(expected))
        for line in removed:
            print(f"[api] MISSING {line}")
        for line in added:
            print(f"[api] EXTRA   {line}")
        if removed or added:
            print(f"[api] surface changed: {len(removed)} missing, {len(added)} extra")
            return 1
        print(f"[api] surface unchanged: {len(current)} routes")

    if not (args.out or args.check):
        print("\n".join(current))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
