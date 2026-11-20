"""Make the open year current and give its existing students an enrollment row.

Why this exists
---------------
A school that was running before `enrollment` was introduced has students in
`student` but no per-year row. The Admission screen filters by the current
academic year (the list joins `enrollment`), so those students disappear even
though the roll is full. The bootstrap used to backfill only when the current
year was first created, which missed every database whose year already existed.

This script is the deliberate, idempotent repair:

* pick the year that contains today (or `--year 2026-27`), not whichever future
  year was left flagged current;
* make exactly that year current;
* create the missing enrollment for every placed student, copying the status
  (`active` / `left`) and separation date from the student row;
* never delete, never move a student, and write nothing when the rows exist.

It is dry-run by default. `--apply` is the only path that writes.

    python scripts/repair_academic_year_enrollments.py
    python scripts/repair_academic_year_enrollments.py --school-code abc --apply
"""

import argparse
import os
import sys
from datetime import date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlmodel import Session, select

from app.core import schema
from app.core.db import engine
from app.domains.academic.classroom.students.models import (
    Enrollment,
    Student,
)
from app.domains.academic.classroom.students.placement import (
    backfill_current_enrollments,
)
from app.domains.admin.platform.models import School
from app.domains.admin.settings.academic_year_context import (
    academic_year_label,
    academic_year_start_year,
)
from app.domains.admin.settings.models import AcademicYear


def _target_label(value: str | None) -> str:
    """The explicit label, or the session containing today (April -> March)."""
    return value or academic_year_label(academic_year_start_year(date.today()))


def _missing(session: Session, year: AcademicYear) -> int:
    """Placed students with no enrollment row for `year`."""
    have = select(Enrollment.student_id).where(
        Enrollment.academic_year_id == year.id
    )
    return len(
        session.exec(
            select(Student.id).where(
                Student.classroom_id.is_not(None),
                Student.id.not_in(have),
            )
        ).all()
    )


def _years(session: Session) -> list[AcademicYear]:
    return list(
        session.exec(
            select(AcademicYear).order_by(AcademicYear.start_date.desc())
        ).all()
    )


def _make_current(session: Session, target: AcademicYear) -> None:
    """Clear the old flag first, then set the target (partial unique index)."""
    for other in session.exec(
        select(AcademicYear).where(AcademicYear.is_current == True)  # noqa: E712
    ).all():
        if other.id != target.id:
            other.is_current = False
            session.add(other)
    session.flush()
    target.is_current = True
    session.add(target)
    session.commit()
    session.refresh(target)


def _repair_school(session: Session, school: School, label: str, apply: bool) -> None:
    session.info["school_id"] = school.id
    years = _years(session)
    target = next((year for year in years if year.name == label), None)

    print(f"\n{school.name} ({school.code})")
    if not years:
        print("  no academic years - the current-year endpoint will create one")
        return
    for year in years:
        marker = "current" if year.is_current else "planned"
        print(f"  {year.name:<8} {year.start_date} -> {year.end_date}  {marker}")
    if target is None:
        print(
            f"  {label} does not exist; open it first or pass --year with one of "
            "the names above"
        )
        return

    missing = _missing(session, target)
    print(f"  target {target.name}: {missing} placed student(s) without enrollment")
    if not apply:
        return

    if not target.is_current:
        _make_current(session, target)
        print(f"  made {target.name} current")
    added = backfill_current_enrollments(session, target)
    session.commit()
    print(f"  backfilled {added} enrollment row(s)")
    print(f"  remaining missing: {_missing(session, target)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--school-code",
        help="only this school (the code in the login, e.g. abc); default: all",
    )
    parser.add_argument(
        "--year",
        help="academic year label, e.g. 2026-27; default: the year containing today",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="write the current flag and missing enrollments (default: report only)",
    )
    parser.add_argument(
        "--backup",
        metavar="PATH",
        help="save every model table to this JSON file before writing",
    )
    args = parser.parse_args()

    schema.load_models()
    schema.quiet()
    print(f"target database  {schema.target_label()}")
    print(f"academic year    {_target_label(args.year)}")
    print(f"mode             {'APPLY' if args.apply else 'dry-run'}")
    if args.apply and args.backup:
        tables = schema.backup_rows(args.backup)
        print(f"backup           {tables} table(s) -> {args.backup}")

    with Session(engine) as session:
        query = select(School).order_by(School.name)
        if args.school_code:
            query = query.where(School.code == args.school_code)
        schools = list(session.exec(query).all())
        if not schools:
            print("no school matched")
            return 1
        for school in schools:
            _repair_school(session, school, _target_label(args.year), args.apply)

    if not args.apply:
        print("\nDry run only. Re-run with --apply to write.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
