"""The session year: read it, open a new one, make one current.

The navbar's selector is the only caller, and the rules it depends on are:

* a session is **1 April -> 31 March**, derived from its name - a school cannot open
  a June-to-April window and quietly measure a different year than the score uses;
* **exactly one row is current**: the first year a school opens becomes current (so
  the screens have something to read), a later one waits until somebody switches;
* switching clears the old flag in the same transaction.

Dates are asserted, not just flags: a "current" row with the wrong window would make
every percentage on the performance screen describe the wrong year.
"""

import importlib
from datetime import date
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.schema import MODEL_MODULES
from app.domains.admin.platform.models import School
from app.domains.admin.settings import academic_years as module
from app.domains.admin.settings.models import AcademicYear


def engine():
    for domain in MODEL_MODULES:
        importlib.import_module(f"app.domains.{domain}.models")
    created = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(created)
    return created


@pytest.fixture()
def world():
    session = Session(engine(), expire_on_commit=False)
    school = School(
        name="Test School",
        code="SY-0001",
        email="office@sy-0001.test",
        phone="9999999999",
        address="1 Test Road",
    )
    session.add(school)
    session.commit()
    session.refresh(school)
    session.info["school_id"] = school.id
    return SimpleNamespace(session=session, school=school)


def open_year(world, **payload):
    return module.open_session_year(
        module.SessionYearIn(**payload), world.session, None
    )


def test_a_session_runs_from_april_to_march(world):
    """The window is derived from the name, not typed in."""
    opened = open_year(world, name="2026-27")

    assert opened.name == "2026-27"
    assert opened.start_date == date(2026, 4, 1)
    assert opened.end_date == date(2027, 3, 31)


def test_the_first_session_becomes_current_and_the_next_one_waits(world):
    """A school planning next year must keep showing the year that is running."""
    first = open_year(world, start_year=2026)
    second = open_year(world, start_year=2027)

    assert first.is_current is True
    assert second.is_current is False

    rows = module.read_session_years(world.session, None)
    assert [row.name for row in rows] == ["2027-28", "2026-27"], "newest first"


def test_switching_leaves_exactly_one_current(world):
    first = open_year(world, start_year=2026)
    second = open_year(world, start_year=2027)
    assert first.is_current is True

    switched = module.make_session_current(second.id, world.session, None)
    assert switched.is_current is True

    rows = {row.name: row for row in module.read_session_years(world.session, None)}
    assert rows["2027-28"].is_current is True
    assert rows["2026-27"].is_current is False, "the old flag is cleared with it"


def test_switching_to_the_year_already_current_is_idempotent(world):
    first = open_year(world, start_year=2026)

    again = module.make_session_current(first.id, world.session, None)

    assert again.is_current is True
    assert len(module.read_session_years(world.session, None)) == 1


def test_the_same_session_cannot_be_opened_twice(world):
    open_year(world, start_year=2026)

    with pytest.raises(HTTPException) as refused:
        open_year(world, start_year=2026)
    assert refused.value.status_code == 409


def test_a_label_that_is_not_two_years_in_a_row_is_a_422(world):
    with pytest.raises(HTTPException) as refused:
        open_year(world, name="FY26")
    assert refused.value.status_code == 422

    with pytest.raises(HTTPException) as skipped:
        open_year(world, name="2026-29")
    assert skipped.value.status_code == 422


def test_the_name_and_the_starting_year_must_agree(world):
    with pytest.raises(HTTPException) as refused:
        open_year(world, name="2026-27", start_year=2027)
    assert refused.value.status_code == 422


def test_an_unknown_session_is_a_404(world):
    from uuid import uuid4

    with pytest.raises(HTTPException) as refused:
        module.make_session_current(uuid4(), world.session, None)
    assert refused.value.status_code == 404


def test_no_name_opens_the_session_we_are_in(world):
    """The navbar's "new session" button sends nothing and gets this year."""
    opened = open_year(world, start_year=None)

    today = date.today()
    start_year = today.year if today.month >= module.SESSION_START_MONTH else today.year - 1
    assert opened.start_date == date(start_year, 4, 1)
    assert opened.end_date == date(start_year + 1, 3, 31)
    assert world.session.exec(select(AcademicYear)).one().is_current


def test_the_routes_are_guarded_by_the_rights_the_screen_needs():
    """Reading is `settings.read`; switching the year is `academic_year.manage`."""
    found = set()
    for route in module.router.routes:
        for dependency in route.dependant.dependencies:
            permission = getattr(dependency.call, "permission", None)
            if permission is None:
                continue
            for method in route.methods:
                found.add((method, route.path, permission))

    assert ("GET", "/session-years", "settings.read") in found
    assert ("POST", "/session-years", "academic_year.manage") in found
    assert (
        "PATCH",
        "/session-years/{year_id}/current",
        "academic_year.manage",
    ) in found
