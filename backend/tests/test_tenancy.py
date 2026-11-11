"""One school's rows never show up in another school's session.

The isolation is not a rule each repository remembers to apply: it is two Session
listeners in `app/core/db.py` (`do_orm_execute` adds `WHERE school_id = ...` to every
SELECT, `before_flush` stamps new rows and refuses cross-school writes). That is worth
pinning on its own, because a change there is a silent data leak rather than an error
somebody notices.

Scenarios:

    1. a list and a `count(*)` return only the bound school's rows;
    2. a single-row read by id from the **other** school finds nothing (404, not 403:
       the API must not confirm that somebody else's id exists);
    3. writing a row that belongs to another school is refused (`TenantError`);
    4. a new row is stamped with the session's school, so nothing lands unscoped;
    5. the platform (`school_id = None`) still sees every school - the seeds and the
       platform console depend on it;
    6. `SKIP_SCHOOL` is that escape hatch, per query and explicit;
    7. a school-level account with **no** school is refused at the door, instead of
       being handed a session whose filter is switched off;
    8. "switch school" - a platform token carrying a `sch` claim is pinned to that
       school, a school-level account ignores the claim, and an unknown or
       suspended school is refused instead of becoming "no filter".

Runs under pytest, and on its own without dev dependencies.
"""

import importlib
from datetime import date
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.schema import MODEL_MODULES
from app.core.security import create_access_token
from app.core.tenancy import SKIP_SCHOOL, TenantError, tenant_of
from app.domains.academic.classroom.students.models import Student
from app.domains.admin.platform.models import School
from app.domains.admin.users.models import User
from app.domains.auth.dependencies import _bind_school
from app.domains.auth.models import Role
from app.domains.auth.roles import attach_roles, grant_role


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


def student(name: str, number: str, **extra) -> Student:
    return Student(
        student_first_name=name,
        full_name=name,
        admission_number=number,
        date_of_birth=date(2014, 3, 3),
        **extra,
    )


def two_schools(created) -> dict:
    """School A with two students, school B with one - each written bound to itself."""
    with Session(created) as session:
        first = School(name="First school", code="aaa", email="a@test")
        second = School(name="Second school", code="bbb", email="b@test")
        session.add(first)
        session.add(second)
        session.commit()
        session.refresh(first)
        session.refresh(second)

        session.info["school_id"] = first.id
        ours = [
            student("Ours One", "ADM-2026-0001"),
            student("Ours Two", "ADM-2026-0002"),
        ]
        session.add_all(ours)
        session.commit()

        session.info["school_id"] = second.id
        theirs = [student("Theirs One", "ADM-2026-0001")]
        session.add_all(theirs)
        session.commit()

        return {
            "first": first.id,
            "second": second.id,
            "ours": [row.id for row in ours],
            "theirs": [row.id for row in theirs],
        }


def test_a_list_shows_only_the_bound_school():
    created = engine()
    ids = two_schools(created)

    with Session(created) as session:
        session.info["school_id"] = ids["first"]
        rows = session.exec(select(Student)).all()
        assert sorted(row.full_name for row in rows) == ["Ours One", "Ours Two"]

    with Session(created) as session:
        session.info["school_id"] = ids["second"]
        rows = session.exec(select(Student)).all()
        assert [row.full_name for row in rows] == ["Theirs One"]


def test_a_count_is_scoped_too():
    """`SELECT count(*)` is the shape the Admission tiles use - it must be filtered."""
    created = engine()
    ids = two_schools(created)

    with Session(created) as session:
        session.info["school_id"] = ids["first"]
        assert session.exec(select(func.count(Student.id))).one() == 2

    with Session(created) as session:
        session.info["school_id"] = ids["second"]
        assert session.exec(select(func.count(Student.id))).one() == 1


def test_a_single_read_from_another_school_finds_nothing():
    created = engine()
    ids = two_schools(created)

    with Session(created) as session:
        session.info["school_id"] = ids["first"]
        assert session.get(Student, ids["theirs"][0]) is None
        assert session.get(Student, ids["ours"][0]) is not None


def test_a_write_into_another_school_is_refused():
    created = engine()
    ids = two_schools(created)

    with Session(created) as session:
        session.info["school_id"] = ids["first"]
        session.add(student("Smuggled", "ADM-2026-0009", school_id=ids["second"]))
        with pytest.raises(TenantError):
            session.commit()


def test_a_new_row_is_stamped_with_the_sessions_school():
    created = engine()
    ids = two_schools(created)

    with Session(created) as session:
        session.info["school_id"] = ids["first"]
        row = student("Stamped", "ADM-2026-0010")
        session.add(row)
        session.commit()
        session.refresh(row)
        assert row.school_id == ids["first"]


def test_the_platform_sees_every_school():
    """No school on the session means no narrowing - the seeds and the console rely on it."""
    created = engine()
    two_schools(created)

    with Session(created) as session:
        assert tenant_of(session) is None
        assert session.exec(select(func.count(Student.id))).one() == 3


def test_skip_school_is_an_explicit_escape_hatch():
    created = engine()
    ids = two_schools(created)

    with Session(created) as session:
        session.info["school_id"] = ids["first"]
        everything = session.exec(
            select(Student), execution_options={SKIP_SCHOOL: True}
        ).all()
        assert len(everything) == 3


def test_a_school_level_account_without_a_school_is_refused():
    """The fail-closed half: `school_id = None` must mean "platform", never "everybody"."""
    created = engine()
    two_schools(created)

    with Session(created) as session:
        session.add(Role(codename="teacher", label="Teacher"))
        session.commit()

        orphan = User(email="orphan@test", full_name="Orphan", hashed_password="x")
        session.add(orphan)
        session.commit()
        session.refresh(orphan)
        grant_role(session, orphan, "teacher")
        attach_roles(session, orphan)

        assert orphan.school_id is None
        with pytest.raises(HTTPException) as refused:
            _bind_school(session, orphan)
        assert refused.value.status_code == 403
        assert tenant_of(session) is None


def test_a_platform_account_may_stay_school_less():
    created = engine()
    two_schools(created)

    with Session(created) as session:
        session.add(Role(codename="system_admin", label="System admin"))
        session.commit()
        platform = User(email="root@test", full_name="Root", hashed_password="x")
        session.add(platform)
        session.commit()
        session.refresh(platform)
        grant_role(session, platform, "system_admin")
        attach_roles(session, platform)

        _bind_school(session, platform)
        assert tenant_of(session) is None


# ── "Switch school": a platform token pinned to one school ──────────────────
#
# The administrator stays themselves (`sub`), only the tenant binding moves. The
# claim is validated, ignored for school-level accounts, and absent means the
# platform-wide view - so a bug here is either a leak or a locked-out console.


def account_with_role(session, codename: str, email: str, school_id=None) -> User:
    """An active account holding `codename`, with its roles already attached."""
    session.add(Role(codename=codename, label=codename.replace("_", " ").title()))
    session.commit()
    user = User(
        email=email,
        full_name=codename.title(),
        hashed_password="x",
        school_id=school_id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    grant_role(session, user, codename)
    attach_roles(session, user)
    return user


def scoped_token(user: User, school_id) -> str:
    return create_access_token(subject=user.id, extra_claims={"sch": school_id})


def test_a_platform_account_can_scope_itself_to_one_school():
    """Switch school: same account, same roles, only the rows change."""
    created = engine()
    ids = two_schools(created)

    with Session(created) as session:
        platform = account_with_role(session, "system_admin", "root@test")

        _bind_school(session, platform, scoped_token(platform, ids["second"]))

        assert tenant_of(session) == ids["second"]
        rows = session.exec(select(Student)).all()
        assert [row.full_name for row in rows] == ["Theirs One"]


def test_clearing_the_scope_returns_the_platform_view():
    """`school_id: null` is the same token a fresh login has: every school again."""
    created = engine()
    ids = two_schools(created)

    with Session(created) as session:
        platform = account_with_role(session, "system_admin", "root@test")

        _bind_school(session, platform, scoped_token(platform, ids["first"]))
        assert session.exec(select(func.count(Student.id))).one() == 2

        _bind_school(session, platform, create_access_token(subject=platform.id))
        assert tenant_of(session) is None
        assert session.exec(select(func.count(Student.id))).one() == 3


def test_a_school_account_ignores_the_scope_claim():
    """The claim must never move somebody else's account out of its school."""
    created = engine()
    ids = two_schools(created)

    with Session(created) as session:
        teacher = account_with_role(
            session, "teacher", "t@test", school_id=ids["first"]
        )

        _bind_school(session, teacher, scoped_token(teacher, ids["second"]))

        assert tenant_of(session) == ids["first"]
        rows = session.exec(select(Student)).all()
        assert sorted(row.full_name for row in rows) == ["Ours One", "Ours Two"]


def test_an_unknown_scope_school_is_refused():
    """Fail closed: a school that is gone must not become "no filter"."""
    created = engine()
    two_schools(created)

    with Session(created) as session:
        platform = account_with_role(session, "system_admin", "root@test")

        with pytest.raises(HTTPException) as refused:
            _bind_school(session, platform, scoped_token(platform, uuid4()))

        assert refused.value.status_code == 403
        assert tenant_of(session) is None


def test_a_suspended_scope_school_is_refused():
    created = engine()
    ids = two_schools(created)

    with Session(created) as session:
        platform = account_with_role(session, "system_admin", "root@test")
        suspended = session.get(School, ids["second"])
        suspended.is_active = False
        session.add(suspended)
        session.commit()

        with pytest.raises(HTTPException) as refused:
            _bind_school(session, platform, scoped_token(platform, ids["second"]))

        assert refused.value.status_code == 403
        assert tenant_of(session) is None

    created = engine()
    ids = two_schools(created)

    with Session(created) as session:
        session.add(Role(codename="teacher", label="Teacher"))
        session.commit()
        teacher = User(
            email="teacher@test",
            full_name="Teacher",
            hashed_password="x",
            school_id=ids["first"],
        )
        session.add(teacher)
        session.commit()
        session.refresh(teacher)
        grant_role(session, teacher, "teacher")
        attach_roles(session, teacher)

        _bind_school(session, teacher)
        assert tenant_of(session) == ids["first"]
