"""The Admission tiles are counted by the database, for the caller's school.

The four numbers used to be computed in the browser from the rows the list endpoint
returned, so a school whose roll was bigger than that endpoint's cap saw the cap on
every tile (500 students, 500 active, 0 inactive) - the numbers were never wrong about
the list, they were just not a count of the school.

`GET /admissions/stats` is that count. Two things are worth pinning:

    1. each tile is the school's own number - another school's rows never leak in
       (the tenant filter in `app/core/db.py` does the scoping);
    2. the tiles do not inherit the list's size: 520 students are 520 students, and
       the list endpoint hands back all of them (no default cap).

Runs under pytest, and on its own without dev dependencies.
"""

import importlib
from datetime import date

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.core.schema import MODEL_MODULES
from app.domains.academic.classroom.students.models import Student
from app.domains.admin.platform.models import School
from app.domains.operations.admission import repository, service
from app.domains.operations.admission.schemas import AdmissionStats


def engine():
    """A fresh in-memory database with every model's table."""
    for domain in MODEL_MODULES:
        importlib.import_module(f"app.domains.{domain}.models")
    created = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(created)
    return created


def student(number: str, **extra) -> Student:
    return Student(
        student_first_name=f"Learner {number}",
        full_name=f"Learner {number}",
        admission_number=number,
        date_of_birth=date(2014, 3, 3),
        **extra,
    )


def two_schools(created) -> dict:
    """School A: 3 students, 2 of them separated (1 mid-session). School B: 2, none."""
    with Session(created) as session:
        first = School(name="First school", code="aaa", email="a@test")
        second = School(name="Second school", code="bbb", email="b@test")
        session.add(first)
        session.add(second)
        session.commit()
        session.refresh(first)
        session.refresh(second)

        session.info["school_id"] = first.id
        session.add_all(
            [
                student("ADM-2026-0001"),
                student(
                    "ADM-2026-0002",
                    separation_reason="Transfer Certificate Issued",
                    separation_session="Incomplete Session",
                    separation_date=date(2026, 6, 30),
                ),
                student(
                    "ADM-2026-0003",
                    separation_reason="Completed schooling",
                    separation_session="Completed Session",
                    separation_date=date(2026, 3, 31),
                ),
            ]
        )
        session.commit()

        session.info["school_id"] = second.id
        session.add_all([student("ADM-2026-0001"), student("ADM-2026-0002")])
        session.commit()

        return {"first": first.id, "second": second.id}


def test_each_tile_is_the_schools_own_number():
    created = engine()
    ids = two_schools(created)

    with Session(created) as session:
        session.info["school_id"] = ids["first"]
        assert service.stats(session) == AdmissionStats(
            students=3, active=1, inactive=2, mid_dropped=1
        )

    with Session(created) as session:
        session.info["school_id"] = ids["second"]
        assert service.stats(session) == AdmissionStats(
            students=2, active=2, inactive=0, mid_dropped=0
        )


def test_active_and_inactive_always_add_up_to_the_roll():
    created = engine()
    ids = two_schools(created)

    with Session(created) as session:
        session.info["school_id"] = ids["first"]
        counts = repository.stats(session)
        assert counts["active"] + counts["inactive"] == counts["students"]
        assert counts["mid_dropped"] <= counts["inactive"]


def test_the_tiles_do_not_inherit_the_lists_size():
    """520 students are 520 on the tiles, and the list endpoint returns all 520."""
    created = engine()
    ids = two_schools(created)

    with Session(created) as session:
        session.info["school_id"] = ids["first"]
        session.add_all([student(f"ADM-2026-{n:04d}") for n in range(2000, 2517)])
        session.commit()

        counts = repository.stats(session)
        assert counts["students"] == 520

        rows = repository.get_applications(session)
        assert len(rows) == 520


def test_the_list_is_ordered_by_admission_number_within_a_day():
    """A `date` puts a whole day's admissions in arbitrary order; the number breaks it."""
    created = engine()
    ids = two_schools(created)

    with Session(created) as session:
        session.info["school_id"] = ids["first"]
        numbers = [row.admission_number for row in repository.get_applications(session)]
        assert numbers == ["ADM-2026-0003", "ADM-2026-0002", "ADM-2026-0001"]


def test_a_page_is_asked_for_explicitly():
    """`limit=None` means the roll; a caller that wants a page passes `skip`/`limit`."""
    created = engine()
    ids = two_schools(created)

    with Session(created) as session:
        session.info["school_id"] = ids["first"]
        assert len(repository.get_applications(session, limit=2)) == 2
        assert len(repository.get_applications(session, skip=1)) == 2
