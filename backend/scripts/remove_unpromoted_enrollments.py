"""Remove enrollments that were copied into a year without a promotion.

An old backfill copied every student's class into whichever year was selected, so a
next year (for example 2027-28) showed last year's whole roll although nobody was
promoted. Such a row is `NEW_ADMISSION`, has no `previous_enrollment_id`, and sits in a
year that is not the one today falls in.

    python scripts/remove_unpromoted_enrollments.py --school abc --year 2027-28          # dry run
    python scripts/remove_unpromoted_enrollments.py --school abc --year 2027-28 --yes    # delete

It refuses to touch the year today falls in, and refuses when any of those rows already
has attendance or is the source of a later year. After deleting, every student of the
school is pointed at the class they have in the **selected** year (or "not placed").
"""

import argparse
import os
import sys
from datetime import date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import sqlalchemy as sa  # noqa: E402

from app.core.db import engine  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--school", required=True, help="school code (abc)")
    parser.add_argument("--year", required=True, help='academic year name ("2027-28")')
    parser.add_argument("--yes", action="store_true", help="actually delete")
    args = parser.parse_args()

    with engine.begin() as conn:

        def one(sql: str, **params):
            return conn.execute(sa.text(sql), params).scalar()

        school = one("select id from school where code = :c", c=args.school)
        year = conn.execute(
            sa.text(
                "select id, start_date, end_date from academic_year "
                "where school_id = :s and name = :n"
            ),
            {"s": school, "n": args.year},
        ).first()
        if school is None or year is None:
            print("school or year not found")
            return 1
        if year.start_date <= date.today() <= year.end_date:
            print(f"{args.year} is the year today falls in - refusing to touch it")
            return 1

        where = (
            "from enrollment where academic_year_id = :y and school_id = :s "
            "and promotion_status = 'NEW_ADMISSION' and previous_enrollment_id is null"
        )
        params = {"y": year.id, "s": school}
        total = one("select count(*) " + where, **params)
        with_attendance = one(
            "select count(*) from attendancerecord where enrollment_id in "
            f"(select id {where})",
            **params,
        )
        chained = one(
            "select count(*) from enrollment where previous_enrollment_id in "
            f"(select id {where})",
            **params,
        )
        print(
            f"{total} unpromoted enrollments in {args.year}: "
            f"{with_attendance} with attendance, {chained} used by a later year"
        )
        if with_attendance or chained:
            print("refusing: some of these rows are in use")
            return 1
        if not args.yes:
            print("dry run - add --yes to delete")
            return 0

        conn.execute(sa.text("delete " + where), params)
        selected = one(
            "select id from academic_year where school_id = :s and is_current", s=school
        )
        conn.execute(
            sa.text(
                "update student st set classroom_id = (select en.classroom_id "
                "from enrollment en where en.student_id = st.id "
                "and en.academic_year_id = :cur and en.status = 'active') "
                "where st.school_id = :s"
            ),
            {"cur": selected, "s": school},
        )
        print(f"deleted {total} enrollments; students re-pointed at the selected year")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
