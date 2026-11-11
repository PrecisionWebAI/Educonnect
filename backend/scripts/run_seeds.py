"""Run the seed scripts in order: 01_roles.py, 02_seed.py, 03_permissions.py, ...

Add a seed by dropping `NN_name.py` here with a `main()`. Boot (`bootstrap()`),
`make seed` and the container entrypoint all call this, so there is one order.
"""

import importlib.util
import os
import re
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
NUMBERED = re.compile(r"^\d{2}_\w+\.py$")


def seeds() -> list[str]:
    return sorted(name for name in os.listdir(HERE) if NUMBERED.match(name))


def run() -> int:
    """Run each seed; print what failed and return 1 if anything did."""
    failed = 0
    for name in seeds():
        print(f"[seed] {name}")
        try:
            path = os.path.join(HERE, name)
            spec = importlib.util.spec_from_file_location(f"seed_{name[:-3]}", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            module.main()
        except Exception as exc:
            failed += 1
            print(f"[seed] {name} FAILED: {exc}")
            traceback.print_exc()
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(run())
