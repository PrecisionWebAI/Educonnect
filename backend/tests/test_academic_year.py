"""The academic year: read it, open a new one, make one current.

The navbar's selector is the only caller, and the rules it depends on are:

* an academic year is **1 April -> 31 March**, derived from its name - a school cannot open
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
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.schema import MODEL_MODULES
from app.domains.admin.platform.models import School
from app.domains.admin.settings import academic_years as module
from app.domains.admin.settings.academic_year_context import (
    ACADEMIC_YEAR_START_MONTH,
    academic_year_for_date,
    ensure_current_academic_year,
)
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
    return module.open_academic_year(
        module.AcademicYearIn(**payload), world.session, None
    )


def test_an_academic_year_runs_from_april_to_march(world):
    """The window is derived from the name, not typed in."""
    opened = open_year(world, name="2026-27")

    assert opened.name == "2026-27"
    assert opened.start_date == date(2026, 4, 1)
    assert opened.end_date == date(2027, 3, 31)


def test_only_the_year_after_the_current_one_can_be_opened(world):
    """2026-27 current => 2027-28 may be planned; 2028-29 waits its turn."""
    open_year(world, start_year=2026)
    open_year(world, start_year=2027)

    with pytest.raises(HTTPException) as skipped:
        open_year(world, start_year=2028)
    assert skipped.value.status_code == 422
    assert "2027-28" in skipped.value.detail


def test_the_first_academic_year_becomes_current_and_the_next_one_waits(world):
    """A school planning next year must keep showing the year that is running."""
    first = open_year(world, start_year=2026)
    second = open_year(world, start_year=2027)

    assert first.is_current is True
    assert second.is_current is False

    rows = module.read_academic_years(world.session, None)
    assert [row.name for row in rows] == ["2027-28", "2026-27"], "newest first"


def test_switching_leaves_exactly_one_current(world):
    first = open_year(world, start_year=2026)
    second = open_year(world, start_year=2027)
    assert first.is_current is True

    switched = module.make_academic_year_current(second.id, world.session, None)
    assert switched.is_current is True

    rows = {row.name: row for row in module.read_academic_years(world.session, None)}
    assert rows["2027-28"].is_current is True
    assert rows["2026-27"].is_current is False, "the old flag is cleared with it"


def test_switching_to_the_year_already_current_is_idempotent(world):
    first = open_year(world, start_year=2026)

    again = module.make_academic_year_current(first.id, world.session, None)

    assert again.is_current is True
    assert len(module.read_academic_years(world.session, None)) == 1


def test_the_same_academic_year_cannot_be_opened_twice(world):
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


def test_an_unknown_academic_year_is_a_404(world):
    from uuid import uuid4

    with pytest.raises(HTTPException) as refused:
        module.make_academic_year_current(uuid4(), world.session, None)
    assert refused.value.status_code == 404


def test_no_name_opens_the_academic_year_we_are_in(world):
    """The navbar's "new session" button sends nothing and gets this year."""
    opened = open_year(world, start_year=None)

    today = date.today()
    start_year = today.year if today.month >= ACADEMIC_YEAR_START_MONTH else today.year - 1
    assert opened.start_date == date(start_year, 4, 1)
    assert opened.end_date == date(start_year + 1, 3, 31)
    assert world.session.exec(select(AcademicYear)).one().is_current


def test_a_date_resolves_to_the_academic_year_that_contains_it(world):
    """31 March belongs to the old year; 1 April belongs to the new one."""
    opened = open_year(world, start_year=2026)

    assert academic_year_for_date(world.session, date(2026, 4, 1)).id == opened.id
    assert academic_year_for_date(world.session, date(2027, 3, 31)).id == opened.id
    assert academic_year_for_date(world.session, date(2027, 4, 1)) is None


def test_ensure_uses_an_existing_date_covered_row_instead_of_creating_one(world):
    """A calendar row that already covers today becomes current; no duplicate."""
    row = AcademicYear(
        name="2026-27",
        start_date=date(2026, 4, 1),
        end_date=date(2027, 3, 31),
        is_current=False,
        school_id=world.school.id,
    )
    world.session.add(row)
    world.session.commit()
    world.session.refresh(row)

    ensured = ensure_current_academic_year(world.session, date(2026, 11, 20))

    assert ensured.id == row.id
    assert ensured.is_current is True
    assert len(world.session.exec(select(AcademicYear)).all()) == 1


def test_opening_next_year_does_not_steal_current_from_a_date_covered_row(world):
    """No current row but today is covered: the existing row becomes current."""
    covered = AcademicYear(
        name="2026-27",
        start_date=date(2026, 4, 1),
        end_date=date(2027, 3, 31),
        is_current=False,
        school_id=world.school.id,
    )
    world.session.add(covered)
    world.session.commit()

    next_year = open_year(world, start_year=2027)

    world.session.refresh(covered)
    assert next_year.is_current is False
    assert covered.is_current is True


def test_the_current_read_never_leaks_another_school(world):
    """A school with no current year sees null even when another school has one."""
    other = School(
        name="Other School",
        code="SY-0002",
        email="office@sy-0002.test",
        phone="9999999998",
        address="2 Test Road",
    )
    world.session.add(other)
    world.session.commit()
    world.session.refresh(other)
    # The request session is bound to the first school; lift the write guard only
    # long enough to create the other school's calendar row.
    first_school = world.session.info["school_id"]
    world.session.info["school_id"] = None
    try:
        world.session.add(
            AcademicYear(
                name="2026-27",
                start_date=date(2026, 4, 1),
                end_date=date(2027, 3, 31),
                is_current=True,
                school_id=other.id,
            )
        )
        world.session.commit()
    finally:
        world.session.info["school_id"] = first_school

    assert module.current_academic_year(world.session) is None


def test_two_current_rows_are_refused_by_the_database(world):
    """The partial unique index is the last guard against split-brain screens."""
    open_year(world, start_year=2026)
    world.session.add(
        AcademicYear(
            name="2027-28",
            start_date=date(2027, 4, 1),
            end_date=date(2028, 3, 31),
            is_current=True,
            school_id=world.school.id,
        )
    )
    with pytest.raises(IntegrityError):
        world.session.commit()
    world.session.rollback()


def test_current_read_is_none_until_a_year_is_opened(world):
    """The current read is auth-only and never creates a row."""
    assert module.current_academic_year(world.session) is None
    assert world.session.exec(select(AcademicYear)).all() == []

    opened = open_year(world, start_year=2026)
    assert module.current_academic_year(world.session).id == opened.id
    assert len(world.session.exec(select(AcademicYear)).all()) == 1


def test_the_current_route_is_auth_only_and_ensures_the_default_year(world):
    """Every signed-in school role gets a running year, even on the first read."""
    route = next(
        route for route in module.router.routes if route.path == "/academic-years/current"
    )
    permissions = [
        getattr(dependency.call, "permission", None)
        for dependency in route.dependant.dependencies
    ]
    assert all(permission is None for permission in permissions)

    payload = module.read_current_academic_year(world.session, None)
    assert payload.academic_year is not None
    assert payload.academic_year.is_current is True
    assert len(world.session.exec(select(AcademicYear)).all()) == 1

    again = module.read_current_academic_year(world.session, None)
    assert again.academic_year is not None
    assert again.academic_year.id == payload.academic_year.id
    assert len(world.session.exec(select(AcademicYear)).all()) == 1


def test_principal_and_vice_cannot_change_the_year_but_a_school_admin_can():
    """The product rule is a role gate, not only a permission grant."""
    principal = SimpleNamespace(_role_names={"principal"})
    vice = SimpleNamespace(_role_names={"vice_principal"})
    admin = SimpleNamespace(_role_names={"school_admin"})

    for user in (principal, vice):
        with pytest.raises(HTTPException) as refused:
            module._can_change(user)
        assert refused.value.status_code == 403

    assert module._can_change(admin) is admin


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

    assert ("GET", "/academic-years", "settings.read") in found
    assert ("POST", "/academic-years", "academic_year.manage") in found
    assert (
        "PATCH",
        "/academic-years/{year_id}/current",
        "academic_year.manage",
    ) in found
