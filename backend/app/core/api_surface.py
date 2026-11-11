"""The route table of a built app, flattened - for the restructure gates.

FastAPI keeps `include_router()` as a lazy node in `app.routes` (it is only
expanded when a request arrives), so "every method + path" has to be walked out
of the includes by hand. One walker, so the API snapshot and the structure check
can never disagree about what the app serves.
"""

from collections.abc import Iterator
from typing import Any

from fastapi import FastAPI


def walk(routes: list[Any], prefix: str = "") -> Iterator[tuple[str, Any]]:
    """Every (path, route) under `routes`, expanding lazy `include_router()` nodes."""
    for route in routes:
        original = getattr(route, "original_router", None)
        if original is not None:
            context = getattr(route, "include_context", None)
            yield from walk(
                original.routes, prefix + (getattr(context, "prefix", "") or "")
            )
            continue
        children = getattr(route, "routes", None)
        if children is not None and getattr(route, "endpoint", None) is None:
            yield from walk(children, prefix + (getattr(route, "path", "") or ""))
            continue
        yield prefix + (getattr(route, "path", "") or ""), route


def entries(app: FastAPI) -> list[str]:
    """Every `METHOD /path` (and `WS /path`) the app answers, sorted."""
    found: set[str] = set()
    for path, route in walk(app.routes):
        methods = getattr(route, "methods", None)
        if methods:
            found.update(f"{method} {path}" for method in methods)
        else:
            found.add(f"WS {path}")
    return sorted(found)


def endpoint_modules(app: FastAPI) -> set[str]:
    """The module of every endpoint - proof that a `router.py` is mounted."""
    modules: set[str] = set()
    for _, route in walk(app.routes):
        endpoint = getattr(route, "endpoint", None)
        module = getattr(endpoint, "__module__", "")
        if module.startswith("app.domains."):
            modules.add(module.rsplit(".", 1)[0])
    return modules
