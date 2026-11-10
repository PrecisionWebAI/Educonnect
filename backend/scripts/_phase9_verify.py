"""One-off HTTP check of the admission write path (Phase 9, no drafts).

Logs in, POSTs a complete form (which is now the admission itself), checks the
admission number and the logins it made, then POSTs an incomplete one and checks it
is refused - and finally deletes the student it created, so the school is left
exactly as it was found.

    python scripts/_admit_check.py
"""

import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings

BASE = "http://localhost:8000"
EMAIL = "admin@abc"
# The credential lives in `backend/.env` (SEED_SCHOOL_ADMIN_PASSWORD); the repo
# does not carry it.
PASSWORD = settings.SEED_SCHOOL_ADMIN_PASSWORD


def _post(path: str, payload: dict, token: str | None = None, method: str = "POST"):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        f"{BASE}{path}", data=json.dumps(payload).encode(), headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode()
        return response.status, (json.loads(body) if body else None)
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode()


def _get(path: str, token: str):
    request = urllib.request.Request(
        f"{BASE}{path}", headers={"Authorization": f"Bearer {token}"}, method="GET"
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read().decode() or "null")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode()


def _wipe_previous(token: str) -> None:
    """Delete the students this check made on an earlier run (and their logins)."""
    status, rows = _get("/admissions/applications?limit=500", token)
    if status != 200 or not isinstance(rows, list):
        return
    for row in rows:
        if row.get("student_first_name") == "phase9":
            _post(f"/students/{row['id']}", {}, token, "DELETE")


def main() -> int:
    status, login = _post("/auth/login", {"username": EMAIL, "password": PASSWORD})
    if status != 200 or not isinstance(login, dict) or not login.get("access_token"):
        print(f"FAIL login: {status} {login}")
        return 1
    token = login["access_token"]
    print("OK   login")

    form = {
        "student_first_name": "phase9",
        "student_last_name": "check",
        "student_email": "phase9.student@abc.demo",
        "date_of_birth": "2015-06-01",
        "gender": "Female",
        "applied_for_class_level": "class 1",
        "applied_section_preference": "A",
        "guardian_name": "phase nine parent",
        "guardian_relation": "mother",
        "guardian_phone": "9111111111",
        "guardian_email": "phase9.check@abc.demo",
        # A field the server does not store: the form used to send the father's
        # phone this way and lose it silently. It must now be refused, loudly.
        "father_phone": "9222222222",
    }

    # Housekeeping: remove anything this check left behind on an earlier run, so it
    # can be run again without piling students up.
    _wipe_previous(token)

    status, body = _post("/admissions/applications", form, token)
    if status != 422:
        print(f"FAIL an unknown field should be refused, got {status}: {body}")
        return 1
    print("OK   a field the server does not store is refused (422)")

    form.pop("father_phone")
    status, body = _post("/admissions/applications", form, token)
    if status != 201 or not isinstance(body, dict):
        print(f"FAIL admit: {status} {body}")
        return 1
    number = body.get("admission_number")
    roles = {item["role"] for item in (body.get("credentials") or [])}
    if not number or roles != {"student", "guardian"}:
        print(f"FAIL admit answered without a number / both logins: {number} {roles}")
        return 1
    if body.get("guardian_name") != "phase nine parent":
        print(f"FAIL the guardian block did not read back: {body.get('guardian_name')!r}")
        return 1
    student_id = body.get("student_id") or body.get("id")
    print(f"OK   admitted {body['student_first_name']} as {number} with {sorted(roles)} logins")
    print(f"OK   guardian read back from the person: {body['guardian_name']}")

    incomplete = dict(form)
    incomplete["guardian_email"] = ""
    incomplete["student_first_name"] = ""
    status, body = _post("/admissions/applications", incomplete, token)
    if status != 422 or "Fill in" not in str(body):
        print(f"FAIL an incomplete form should be refused with a reason, got {status}: {body}")
        return 1
    print("OK   an incomplete form is refused before anything is written (422)")

    # Clean up: the student this check made, by its own id, so the school is left
    # exactly as it was found.
    if student_id:
        status, body = _post(f"/students/{student_id}", {}, token, "DELETE")
        if status != 200:
            print(f"WARN the check's student {student_id} was not deleted: {status} {body}")
        else:
            print("OK   the check's student was deleted again")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
