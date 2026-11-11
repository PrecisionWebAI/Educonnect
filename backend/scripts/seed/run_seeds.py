"""Run the seed scripts in order: 01_roles_seed.py, 02_permissions_seed.py, ...

Add a seed by dropping `NN_name_seed.py` here with a `main()`. Boot (`bootstrap()`),
`make seed` and the container entrypoint all call this, so there is one order.
"""

import importlib.util
import os
import re
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
NUMBERED = re.compile(r"^\d{2}_[\w]+_seed\.py$")


def seeds() -> list[str]:
    return sorted(name for name in os.listdir(HERE) if NUMBERED.match(name))


def run() -> int:
    """Run each seed; print what ran, what failed, and return 1 if anything did."""
    names = seeds()
    failed: list[str] = []
    started = time.perf_counter()
    for name in names:
        step_started = time.perf_counter()
        try:
            path = os.path.join(HERE, name)
            spec = importlib.util.spec_from_file_location(f"seed_{name[:-3]}", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            module.main()
            print(f"[seed] {name} ok in {time.perf_counter() - step_started:.1f}s")
        except Exception as exc:
            failed.append(name)
            print(f"[seed] {name} FAILED: {exc}")
            traceback.print_exc()
    took = time.perf_counter() - started
    print(
        f"[seed] seeds complete: {len(names) - len(failed)} ok, "
        f"{len(failed)} failed in {took:.1f}s"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(run())
