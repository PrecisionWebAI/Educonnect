"""Read-only smoke test for the three Operations areas and the Classroom.

It logs in and GETs every route those screens need, so a broken wire - a 500, a
403 from a missing grant, a route that was never registered - shows up as one
line here instead of a screen that quietly renders nothing.

    python scripts/smoke_areas.py
    python scripts/smoke_areas.py --base-url https://api.example.com \
        --email admin@abc --password adminabc123

**It only reads.** No row is created, changed or deleted, so it is safe to run
against a live school at any time.
"""

import argparse
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import date

#: (area, path) - the calls the screens make when they open. `{section}` / `{class}`
#: are filled in from the Classroom overview (so the drill-down and the register of
#: a real class-section are covered), `{today}` from the current date.
ROUTES: tuple[tuple[str, str], ...] = (
    ("admission", "/admissions/applications"),
    ("admission", "/admissions"),
    ("admission", "/academics/classes"),
    ("admission", "/academics/subjects"),
    ("hiring", "/hiring/candidates"),
    ("hiring", "/hiring/summary"),
    ("hiring", "/staff/profiles"),
    ("classroom", "/classroom/overview"),
    ("classroom", "/classroom/teachers"),
    ("classroom", "/classroom/classes"),
    ("classroom", "/academics/class-info"),
    ("classroom", "/classroom/sections/{section}"),
    ("classroom", "/classroom/lesson-detail"),
    # The Students and Attendance views that now live inside a class-section.
    ("students", "/students?skip=0&limit=5"),
    ("attendance", "/attendance?skip=0&limit=5"),
    ("attendance", "/attendance/class/{class}/section/{section}?target_date={today}"),
    ("attendance", "/attendance/irregular"),
    ("attendance", "/attendance/leave-sync"),
    # ...and the Academics and Homework views that live there too.
    ("academics", "/classroom/sections/{section}/marks"),
    # The class-section's own week (what the Timetable tab reads).
    ("timetable", "/timetable/class/{class}?section_id={section}"),
    ("timetable", "/timetable"),

    ("homework", "/homework/section/{section}"),
    ("homework", "/homework/diary/section/{section}"),
    ("homework", "/homework/submissions"),
)

#: Routes that answer 404 for a legitimate reason (nobody teaches this person),
#: so the smoke test does not cry wolf about them.
EMPTY_IS_FINE = ("/classroom/lesson-detail",)


def _call(
    base: str, path: str, token: str | None = None, form: dict[str, str] | None = None
) -> tuple[int, object]:
    """One request. Raises `HTTPError` for a non-2xx answer."""
    headers: dict[str, str] = {}
    data: bytes | None = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if form is not None:
        data = urllib.parse.urlencode(form).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"

    request = urllib.request.Request(
        f"{base}{path}", data=data, headers=headers, method="POST" if form else "GET"
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read().decode()
    return response.status, (json.loads(body) if body else None)


def _first_ids(overview: object) -> tuple[str, str]:
    """(classroom id, section id) of the first class-section the grid shows."""
    if not isinstance(overview, list):
        return "", ""
    for group in overview:
        if not isinstance(group, dict):
            continue
        classroom_id = str(group.get("classroomId") or "")
        for card in group.get("sections", []):
            section_id = str(card.get("sectionId") or "")
            if classroom_id and section_id:
                return classroom_id, section_id
    return "", ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--email", default="admin@abc")
    parser.add_argument("--password", default="adminabc123")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    try:
        _, login = _call(
            base, "/auth/login", form={"username": args.email, "password": args.password}
        )
    except urllib.error.HTTPError as error:
        print(f"FAIL login as {args.email}: HTTP {error.code} {error.read().decode()[:200]}")
        return 1
    token = (login or {}).get("access_token") if isinstance(login, dict) else None
    if not token:
        print(f"FAIL login as {args.email}: no access_token in the response")
        return 1
    print(f"OK   login as {args.email}")

    failures = 0
    section = ""
    classroom = ""
    today = date.today().isoformat()
    for area, path in ROUTES:
        if ("{section}" in path and not section) or ("{class}" in path and not classroom):
            print(f"SKIP {area:<9} {path}  (the Classroom grid is empty - nothing to open)")
            continue
        target = (
            path.replace("{section}", section)
            .replace("{class}", classroom)
            .replace("{today}", today)
        )
        try:
            status, payload = _call(base, target, token=token)
        except urllib.error.HTTPError as error:
            detail = error.read().decode()[:160]
            if error.code == 404 and path in EMPTY_IS_FINE:
                print(f"OK   {area:<9} 404 {target}  (nothing scheduled)")
                continue
            print(f"FAIL {area:<9} HTTP {error.code} {target}  {detail}")
            failures += 1
            continue
        size = len(payload) if isinstance(payload, list) else "object"
        print(f"OK   {area:<9} {status} {target}  ({size})")
        if target == "/classroom/overview":
            classroom, section = _first_ids(payload)

    print(
        f"\n{len(ROUTES) - failures - 1} route(s) answered, {failures} failure(s)"
        if failures
        else f"\nAll {len(ROUTES)} routes answered."
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
