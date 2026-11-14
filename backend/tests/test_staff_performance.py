"""`GET /teachers/performance` - owned by `appraisal/`, still at its own URL.

Phase 10 moved the read that summarises `teacherreview` beside the season, because
`teacherreview` is the review half of an appraisal. Two things had to stay put, and
both are asserted here: the **URL** (the screen has called it since Phase 1) and the
**behaviour** (an average of what was actually left, "flat" with one rating, and
nothing invented for a teacher nobody has rated).
"""

import importlib
from datetime import date
from types import SimpleNamespace

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.core.schema import MODEL_MODULES
from app.domains.admin.platform.models import School
from app.domains.admin.users.models import User
from app.domains.auth.models import Role
from app.domains.auth.roles import grant_role
from app.domains.people.staff.models import Employee
from app.domains.people.teachers.appraisal import performance as module
from app.domains.people.teachers.models import TeacherReview


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


def session_for(created, school_id=None):
    session = Session(created, expire_on_commit=False)
    if school_id is not None:
        session.info["school_id"] = school_id
    return session


def _teacher(session: Session, school_id, code: str, name: str):
    role = session.exec(
        __import__("sqlmodel").select(Role).where(Role.codename == "teacher")
    ).first()
    user = User(
        email=f"{code.lower()}@test",
        full_name=name,
        hashed_password="x",
        school_id=school_id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    if role is not None:
        grant_role(session, user, "teacher")
    employee = Employee(
        user_id=user.id,
        employee_code=code,
        department="Science",
        joining_date=date(2023, 6, 1),
        email=f"{code.lower()}@test",
    )
    session.add(employee)
    session.commit()
    session.refresh(employee)
    return user, employee


@pytest.fixture()
def seeded():
    session = session_for(engine())
    session.add(Role(codename="teacher", label="Teacher"))
    session.commit()
    school = School(
        name="Test School",
        code="PERF-0001",
        email="office@perf-0001.test",
        phone="9999999999",
        address="1 Test Road",
    )
    session.add(school)
    session.commit()
    session.refresh(school)
    session.info["school_id"] = school.id

    _, one = _teacher(session, school.id, "EMP-0001", "Teacher One")
    _, two = _teacher(session, school.id, "EMP-0002", "Teacher Two")
    return SimpleNamespace(session=session, school=school, one=one, two=two)


def test_the_url_did_not_move():
    """The screen has called `/teachers/performance` since Phase 1."""
    paths = [route.path for route in module.router.routes]
    assert "/teachers/performance" in paths


def test_a_rating_is_the_average_of_what_was_left(seeded):
    seeded.session.add_all(
        [
            TeacherReview(teacher_id=seeded.one.id, rating=4, reviewer_role="Parent"),
            TeacherReview(teacher_id=seeded.one.id, rating=5, reviewer_role="HOD"),
        ]
    )
    seeded.session.commit()

    rows = {row.staff: row for row in module.performance(seeded.session)}
    one = rows["Teacher One"]
    assert one.rating == 4.5
    assert one.reviews == 2
    # The reviews component is the rating out of five, as a percentage.
    reviews = next(item for item in one.components if item.key == "reviews")
    assert reviews.value == 90


def test_one_rating_has_no_trend_to_report(seeded):
    seeded.session.add(
        TeacherReview(teacher_id=seeded.one.id, rating=3, reviewer_role="Parent")
    )
    seeded.session.commit()

    rows = module.performance(seeded.session)
    assert rows[0].trend == "flat"


def test_a_rising_pair_reads_up(seeded):
    """The recent half against the older half - not a made-up direction."""
    seeded.session.add_all(
        [
            TeacherReview(teacher_id=seeded.one.id, rating=2, reviewer_role="Parent"),
            TeacherReview(teacher_id=seeded.one.id, rating=5, reviewer_role="Parent"),
        ]
    )
    seeded.session.commit()

    assert module.performance(seeded.session)[0].trend == "up"


def test_a_teacher_nobody_rated_shows_no_data_not_zero(seeded):
    """Phase 5: everyone on the roll gets a row - an unrated one says "no data".

    Before Phase 5 the list held only rated teachers; the new contract is "the roll,
    with the facts that exist". A 0 would read as a bad score, so the component is
    `None` and the screen prints "no data".
    """
    seeded.session.add(
        TeacherReview(teacher_id=seeded.one.id, rating=4, reviewer_role="Parent")
    )
    seeded.session.commit()

    rows = {row.staff: row for row in module.performance(seeded.session)}
    assert set(rows) == {"Teacher One", "Teacher Two"}
    two = rows["Teacher Two"]
    assert two.reviews == 0
    reviews = next(item for item in two.components if item.key == "reviews")
    assert reviews.value is None
    assert reviews.display == "no data"
