"""Which permission actually guards each route - checked on the built app.

The screens used to answer with fixtures and check the caller's role *inside* the
handler; they now read real rows and are guarded by `RequirePermission`, so the
thing worth testing is the wiring: every route is behind the permission its nav
entry asks for.

Two checks: nothing answers without a guard (which is how `/settings/security-logs`,
`/settings/gateways` and `/chat/files` were found serving anonymous callers), and a
route that moved between groups still asks for the same permission.
"""

import pytest

from app.core.api_surface import walk
from app.domains.auth.dependencies import (
    RequirePermission,
    get_current_active_user,
    get_current_user,
)
from app.main import app

#: The only routes that answer before anybody has signed in, and why.
PUBLIC = {
    "/": "the service banner",
    "/health": "the container health check",
    "/auth/login": "the way in",
    "/auth/token": "the OAuth2 password form of the way in",
    "/auth/logout": "logging out only tells the client to drop its token - there is no server session",
}

#: Callables that only require a signed-in person, not a permission.
SIGNED_IN = (get_current_active_user, get_current_user)


def guards_of(route) -> set[str]:
    """The auth requirements a route declares directly."""
    found: set[str] = set()
    for dependency in route.dependant.dependencies:
        call = dependency.call
        if isinstance(call, RequirePermission):
            found.add(call.permission)
        elif call in SIGNED_IN:
            found.add("signed-in")
    return found


def http_routes() -> dict[str, set[str]]:
    """`{"GET /path": guards}` for every product route the app serves.

    FastAPI's own docs endpoints (`/openapi.json`, `/docs`, `/redoc`) are plain
    Starlette routes with no dependency tree, so they are skipped - they belong to
    the framework, not to the product.
    """
    found: dict[str, set[str]] = {}
    for path, route in walk(app.routes):
        methods = getattr(route, "methods", None)
        if not methods or getattr(route, "dependant", None) is None:
            continue
        for method in methods:
            found[f"{method} {path}"] = guards_of(route)
    return found


def test_no_route_answers_without_a_guard():
    """Every HTTP route is behind a sign-in and a permission, except the four public ones."""
    unguarded = sorted(
        route_key
        for route_key, guards in http_routes().items()
        if not guards and route_key.split(" ", 1)[1] not in PUBLIC
    )
    assert unguarded == []


#: The permission each moved route keeps. A restructure must not widen access.
EXPECTED = {
    "GET /library/books": {"library.read"},
    "GET /library/issues": {"library.read"},
    "GET /transport/routes": {"transport.read"},
    "GET /transport/buses": {"transport.read"},
    "GET /meetings": {"ptm.read"},
    "GET /tickets": {"messages.read"},
    "GET /leave/applications": {"leave.read"},
    "GET /leave/staff-requests": {"leave.read"},
    "GET /notifications": {"messages.read"},
    "POST /notifications/mark-read": {"messages.read"},
    "GET /chat/files": {"messages.read"},
    "GET /copilot/automations": {"ai_copilot.use"},
    "GET /copilot/suggestions": {"ai_copilot.use"},
    "GET /copilot/commands": {"ai_copilot.use"},
    "GET /reports/cards": {"reports.read"},
    "GET /reports/data-quality": {"analytics.read"},
    "GET /reports/education": {"reports.read"},
    "GET /settings/users": {"settings.read"},
    "GET /settings/school-info": {"settings.read"},
    "GET /settings/security-logs": {"settings.read"},
    "GET /settings/gateways": {"settings.read"},
    "GET /classroom/classes": {"classes.read"},
    "GET /classroom/lesson-detail": {"classes.read"},
}


@pytest.mark.parametrize("route_key", sorted(EXPECTED))
def test_moved_route_keeps_its_permission(route_key):
    assert http_routes()[route_key] == EXPECTED[route_key]
