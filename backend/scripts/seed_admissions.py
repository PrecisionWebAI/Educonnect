"""Seed the demo school's students the way the product does it: by admitting them.

Why this file exists:
  Students used to be written straight into `studentprofile` by a seed script,
  which meant the student directory and the admission register could disagree.
  Registering an application now creates the student (login, profile, guardian
  link - see `admissions/service.py`), so the demo is built from the forms
  themselves: fill a form, register it, and the student appears everywhere.

What it creates:
  * a full admission form for every student (Nursery ... Class 12, sections A/B)
  * a few drafts, so the Draft tab is not empty
  * the awkward cases on purpose: a form naming a class the school does not have
    (student created without a class), a form with no date of birth, a form with
    no gender, a student with no attendance, and a **second child of the same
    parent** (proving one parent login is reused, not duplicated)
  * attendance for the last ten weekdays for every placed student
  * `info/demo_logins.md` - the generated logins with their first-time passwords,
    so the demo can actually be logged into

Idempotent: it does nothing when the school already has students.

    docker exec eduverse-backend python scripts/seed_admissions.py
"""

import os
import sys
from datetime import date, timedelta
from pathlib import Path

from sqlmodel import Session, select

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.db import engine
from app.domains.academics.models import Classroom
from app.domains.admissions import service as admissions_service
from app.domains.admissions.models import (
    STATUS_DRAFT,
    STATUS_REGISTERED,
    AdmissionApplication,
)
from app.domains.attendance.models import AttendanceRecord, AttendanceStatus
from app.domains.students.models import StudentProfile

#: Students admitted into section A of every class (and a couple into B).
PER_CLASS = 3
ATTENDANCE_DAYS = 10
SCHOOL_DOMAIN = "educonnect.com"
#: Where the generated logins are written. Inside the container the backend root
#: is `/app`, so the file lands next to the scripts; `DEMO_LOGINS_PATH` overrides
#: it (e.g. to copy it straight into the repository's `info/` folder).
LOGINS_FILE = Path(
    os.getenv(
        "DEMO_LOGINS_PATH",
        str(Path(__file__).resolve().parents[1] / "demo_logins.md"),
    )
)

FIRST_NAMES = (
    ("Aarav", "Male"),
    ("Ananya", "Female"),
    ("Vihaan", "Male"),
    ("Ishita", "Female"),
    ("Kabir", "Male"),
    ("Diya", "Female"),
    ("Rohan", "Male"),
    ("Saanvi", "Female"),
    ("Ishaan", "Male"),
    ("Aadhya", "Female"),
    ("Aditya", "Male"),
    ("Meera", "Female"),
    ("Arjun", "Male"),
    ("Riya", "Female"),
    ("Dev", "Male"),
    ("Nisha", "Female"),
    ("Yash", "Male"),
    ("Tara", "Female"),
    ("Neel", "Male"),
    ("Ira", "Female"),
    ("Rudra", "Male"),
    ("Mahi", "Female"),
    ("Om", "Male"),
    ("Kiara", "Female"),
)
SURNAMES = (
    "Mehta",
    "Rao",
    "Singh",
    "Das",
    "Gupta",
    "Nair",
    "Sharma",
    "Verma",
    "Patel",
    "Joshi",
    "Kulkarni",
    "Reddy",
    "Iyer",
    "Menon",
    "Bose",
    "Sheikh",
)
PARENT_FIRST = (
    "Rakesh",
    "Sunita",
    "Vijay",
    "Anita",
    "Manoj",
    "Priya",
    "Deepak",
    "Shalini",
    "Ravi",
    "Neha",
    "Ashok",
    "Kiran",
    "Sandeep",
    "Meenakshi",
    "Faisal",
    "Rekha",
)
OCCUPATIONS = (
    "Business",
    "Government Service",
    "Private Service",
    "Professional",
    "Self Employed",
    "Farmer",
)
BLOOD_GROUPS = ("A+", "B+", "O+", "AB+", "A-", "O-")
CATEGORIES = ("General", "OBC", "SC", "ST", "EWS")


def _weekdays(count: int) -> list[date]:
    days: list[date] = []
    cursor = date.today()
    while len(days) < count:
        if cursor.weekday() < 5:
            days.append(cursor)
        cursor -= timedelta(days=1)
    return days


def _status_for(seed: int) -> AttendanceStatus:
    bucket = seed % 100
    if bucket < 6:
        return AttendanceStatus.absent
    if bucket < 10:
        return AttendanceStatus.late
    if bucket < 12:
        return AttendanceStatus.half_day
    if bucket < 14:
        return AttendanceStatus.leave
    return AttendanceStatus.present


def _student_form(
    *,
    serial: int,
    classroom_name: str,
    section: str,
    birth_year: int,
    contact: str | None = None,
    with_dob: bool = True,
    with_gender: bool = True,
) -> dict:
    """One admission form, filled the way the office would fill it."""
    first_name, gender = FIRST_NAMES[serial % len(FIRST_NAMES)]
    surname = SURNAMES[(serial * 5 + 3) % len(SURNAMES)]
    parent_first = PARENT_FIRST[(serial * 7 + 1) % len(PARENT_FIRST)]
    parent_name = f"{parent_first} {surname}"
    parent_email = (
        contact or f"{parent_first.lower()}.{surname.lower()}{serial}@example.com"
    )
    return {
        "status": STATUS_REGISTERED,
        "created_on": date.today() - timedelta(days=serial % 40),
        "student_first_name": first_name,
        "student_last_name": surname,
        "date_of_birth": (
            date(birth_year, (serial % 12) + 1, (serial % 27) + 1) if with_dob else None
        ),
        "gender": gender if with_gender else None,
        "blood_group": BLOOD_GROUPS[serial % len(BLOOD_GROUPS)],
        "category": CATEGORIES[serial % len(CATEGORIES)],
        "nationality": "Indian",
        "address": f"{serial} Rose Villa, Kothrud, Pune 411038",
        "father_name": parent_name,
        "father_occupation": OCCUPATIONS[serial % len(OCCUPATIONS)],
        "father_phone": f"+91 98200 {10000 + serial:05d}",
        "father_email": parent_email,
        "mother_name": f"{PARENT_FIRST[(serial * 11 + 4) % len(PARENT_FIRST)]} {surname}",
        "mother_phone": f"+91 98200 {20000 + serial:05d}",
        "applied_for_class_level": classroom_name,
        "applied_section_preference": section or None,
        "needs_transport": "Yes" if serial % 3 == 0 else "No",
        "transport_route": "Route 4 - Kothrud" if serial % 3 == 0 else None,
    }


def _draft_forms() -> list[dict]:
    """Half-filled forms, so the Draft tab is not empty."""
    return [
        {
            "status": STATUS_DRAFT,
            "created_on": date.today(),
            "student_first_name": "Tara",
            "student_last_name": "Menon",
            "applied_for_class_level": "Nursery",
            "notes": "Started at the front desk; parents will return with papers.",
        },
        {
            "status": STATUS_DRAFT,
            "created_on": date.today(),
            "student_first_name": "Aryan",
            "student_last_name": "Bose",
            "gender": "Male",
            "notes": "Phone enquiry - form sent home.",
        },
        {
            "status": STATUS_DRAFT,
            "created_on": date.today(),
            "student_first_name": "Zoya",
            "student_last_name": "Khan",
            "applied_for_class_level": "Class 1",
            "applied_section_preference": "A",
        },
    ]


def _next_sequence(session: Session) -> int:
    """The next form number, continuing whatever the table already holds."""
    numbers: list[int] = []
    for row in session.exec(select(AdmissionApplication)).all():
        tail = (row.application_no or "").rsplit("-", 1)[-1]
        if tail.isdigit():
            numbers.append(int(tail))
    return (max(numbers) if numbers else 0) + 1


#: Every form this script creates carries this note, so a later run can tell
#: "the demo batch is already here" from "the school has other applications".
DEMO_NOTE = "Created by scripts/seed_admissions.py (demo batch)."


def _demo_batch_exists(session: Session) -> bool:
    return (
        session.exec(
            select(AdmissionApplication).where(AdmissionApplication.notes == DEMO_NOTE)
        ).first()
        is not None
    )


def promote_registered_applications(session: Session | None = None) -> int:
    """Register every application that is Registered but has no student yet.

    Run after any step that can create applications, so "Registered" always means
    "the student is in the directory" - whatever wrote the form.
    """
    own_session = session is None
    session = session or Session(engine)
    try:
        promoted = 0
        for application in session.exec(
            select(AdmissionApplication).where(
                AdmissionApplication.status == STATUS_REGISTERED,
                AdmissionApplication.student_id.is_(None),  # type: ignore[union-attr]
            )
        ).all():
            result = admissions_service.register_application(session, application.id)
            promoted += 1
            if result.placement_note:
                print(
                    f"[seed_admissions] note on {application.application_no}: "
                    f"{result.placement_note}"
                )
        return promoted
    finally:
        if own_session:
            session.close()


def _write_login_list(rows: list[tuple[str, str, object]]) -> None:
    """Write the generated logins (with first-time passwords) for the demo."""
    lines = [
        "# Demo logins (generated)",
        "",
        "Created by `backend/scripts/seed_admissions.py` while the admission forms",
        "were registered. Each first-time password is shown **once** - the database",
        "stores only its hash - so this file is the only place to read it.",
        "",
        "| Form | Student | Who | Login email | First-time password |",
        "|---|---|---|---|---|",
    ]
    for form_no, student, cred in rows:
        password = cred.password or "_(existing login - password unchanged)_"
        lines.append(
            f"| {form_no} | {student} | {cred.role} | `{cred.email}` | `{password}` |"
        )
    LOGINS_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        f"[seed_admissions] login list written to {LOGINS_FILE.name} ({len(rows)} rows)"
    )
    # Also to the log, so the office (or whoever runs the demo) can see the
    # logins without opening a file - each password exists only at this moment.
    for form_no, student, cred in rows:
        if cred.password:
            print(
                f"[seed_admissions]   {cred.role:<8} {cred.email}  "
                f"password={cred.password}  ({student}, {form_no})"
            )


def seed_admissions() -> None:
    """Create the demo admission forms (once) and register what needs it."""
    with Session(engine) as session:
        classrooms = list(
            session.exec(select(Classroom).order_by(Classroom.level)).all()  # type: ignore[arg-type]
        )
        if not classrooms:
            print("[seed_admissions] No classes yet - run the academics seed first.")
            return

        # The demo batch is written once. After that the script only registers
        # what is still outstanding, so a reset + restart cannot pile up
        # duplicate forms (or duplicate students) in the school.
        if _demo_batch_exists(session):
            print("[seed_admissions] Demo admission batch already exists.")
        elif session.exec(select(StudentProfile)).first():
            print(
                "[seed_admissions] Students already exist - the roll is built from "
                "the admission forms now, so no demo batch is created."
            )
        else:
            _create_demo_batch(session, classrooms)

        # register, then give the new students their attendance
        logins = _register_outstanding(session)

        # 5. attendance for the placed students (one is left with none on purpose)
        days = _weekdays(ATTENDANCE_DAYS)
        students = list(session.exec(select(StudentProfile)).all())
        created = 0
        for index, student in enumerate(students):
            if not (student.classroom_id and student.section_id):
                continue
            if index == 0 and len(students) > 1:
                continue
            for day_index, day in enumerate(days):
                session.add(
                    AttendanceRecord(
                        student_id=student.id,
                        classroom_id=student.classroom_id,
                        section_id=student.section_id,
                        date=day,
                        status=_status_for(index * 37 + day_index * 17),
                    )
                )
                created += 1
        session.commit()
        print(
            f"[seed_admissions] {created} attendance record(s) for "
            f"{len(students)} student(s)"
        )

        _write_login_list(logins)


def _create_demo_batch(session: Session, classrooms: list[Classroom]) -> None:
    """Write the demo admission forms: the roll, a shared family, and the edges."""
    forms: list[dict] = []
    serial = 0

    # 1. the everyday roll: a few students in every class
    for classroom in classrooms:
        for slot in range(PER_CLASS):
            serial += 1
            forms.append(
                _student_form(
                    serial=serial,
                    classroom_name=classroom.name,
                    section="A" if slot < PER_CLASS - 1 else "B",
                    birth_year=2026 - classroom.level - 4,
                )
            )

    # 2. one family, two children: the parent's login must be reused
    shared_contact = "homer.simpson@example.com"
    serial += 1
    forms.append(
        _student_form(
            serial=serial,
            classroom_name="Class 6",
            section="A",
            birth_year=2014,
            contact=shared_contact,
        )
    )
    serial += 1
    forms.append(
        _student_form(
            serial=serial,
            classroom_name="Class 3",
            section="A",
            birth_year=2017,
            contact=shared_contact,
        )
    )

    # 3. the awkward cases, one form each
    serial += 1
    forms.append(
        _student_form(
            serial=serial, classroom_name="Class 99", section="", birth_year=2015
        )
    )
    serial += 1
    forms.append(
        _student_form(
            serial=serial,
            classroom_name="Class 8",
            section="A",
            birth_year=2012,
            with_dob=False,
        )
    )
    serial += 1
    forms.append(
        _student_form(
            serial=serial,
            classroom_name="Class 9",
            section="A",
            birth_year=2011,
            with_gender=False,
        )
    )

    drafts = _draft_forms()
    sequence = _next_sequence(session)
    for row in forms + drafts:
        # The draft rows carry their own note; every form additionally carries the
        # demo marker, so a later run can tell this batch apart from real forms.
        own_note = (row.get("notes") or "").strip()
        payload = {key: value for key, value in row.items() if key != "notes"}
        session.add(
            AdmissionApplication(
                **payload,
                application_no=f"ADM-{date.today().year}-{sequence:04d}",
                notes=f"{own_note} {DEMO_NOTE}".strip(),
            )
        )
        sequence += 1
    session.commit()
    print(
        f"[seed_admissions] {len(forms)} admission form(s) and "
        f"{len(drafts)} draft(s) created"
    )


def _register_outstanding(session: Session) -> list[tuple[str, str, object]]:
    """Register everything still waiting, returning the logins it created."""
    logins: list[tuple[str, str, object]] = []
    registered = 0
    for application in session.exec(
        select(AdmissionApplication).where(
            AdmissionApplication.status == STATUS_REGISTERED,
            AdmissionApplication.student_id.is_(None),  # type: ignore[union-attr]
        )
    ).all():
        result = admissions_service.register_application(session, application.id)
        registered += 1
        student = f"{application.student_first_name} {application.student_last_name}"
        for credential in result.credentials or []:
            logins.append((application.application_no, student, credential))
        if result.placement_note:
            print(
                f"[seed_admissions] note on {application.application_no}: "
                f"{result.placement_note}"
            )
    print(f"[seed_admissions] {registered} application(s) registered")
    return logins


if __name__ == "__main__":
    seed_admissions()
