"""Phase 8: the two follow-ups - `user`-named objects and a per-period class log.

Every test here pins a promise the two migrations make:

* **no model object is still named after the old `user` table** - a database built by
  `create_all` and one built by the migrations must agree on names, or a later
  `ALTER`/restore behaves differently on the two paths;
* **a log line has two shapes** - one per period, or the register-style day line,
  one per class-section per day (the partial unique index is what stops the day line
  being written twice, because PostgreSQL treats NULLs as distinct);
* **"completed this week" counts periods** once a school logs per period, and days
  when it still logs the old way - never both for the same teacher.

Runs on in-memory SQLite, which enforces partial unique indexes too.
"""

import importlib
from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.schema import MODEL_MODULES
from app.domains.academic.classroom.homework.models import ClassLog
from app.domains.people.teachers.workload import repository as workload_repository


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


def _session(created) -> Session:
    return Session(created, expire_on_commit=False)


def _log(day: date, *, classroom_id=None, period_id=None, teacher_id=None) -> ClassLog:
    return ClassLog(
        classroom_id=classroom_id or uuid4(),
        teacher_id=teacher_id or uuid4(),
        date=day,
        note="Chapter 4",
        timetableperiod_id=period_id,
    )


# --- names follow the table --------------------------------------------------


def test_no_model_object_is_still_named_after_the_user_table():
    """`user_pkey`, `ix_user_*`, `uq_user_*` are drift from before the rename."""
    names: set[str] = set()
    for table in SQLModel.metadata.tables.values():
        names.update(index.name for index in table.indexes if index.name)
        names.update(
            constraint.name for constraint in table.constraints if constraint.name
        )

    stale = {
        name
        for name in names
        if (name.startswith(("ix_user_", "uq_user_")) or name == "user_pkey")
        # `user_role` is its own table: its objects are allowed to start with `user_`.
        and "user_role" not in name
    }
    assert stale == set()


# --- classlog: one line per period, one day line per day --------------------


def test_two_periods_in_the_same_room_on_one_day_are_two_lines():
    created = engine()
    with _session(created) as session:
        room = uuid4()
        day = date(2026, 11, 10)
        session.add_all(
            [
                _log(day, classroom_id=room, period_id=uuid4()),
                _log(day, classroom_id=room, period_id=uuid4()),
            ]
        )
        session.commit()
        assert len(session.exec(select(ClassLog)).all()) == 2


def test_the_same_period_cannot_be_logged_twice():
    created = engine()
    with _session(created) as session:
        room = uuid4()
        day = date(2026, 11, 10)
        period = uuid4()
        session.add_all(
            [
                _log(day, classroom_id=room, period_id=period),
                _log(day, classroom_id=room, period_id=period),
            ]
        )
        with pytest.raises(IntegrityError):
            session.commit()


def test_the_day_line_is_still_one_per_class_section():
    """NULL periods are distinct to PostgreSQL - the partial index is the rule."""
    created = engine()
    with _session(created) as session:
        room = uuid4()
        day = date(2026, 11, 10)
        session.add_all([_log(day, classroom_id=room), _log(day, classroom_id=room)])
        # The first pair in the "two periods" test used distinct random period ids;
        # these two are both day-level rows for the same room and day.
        with pytest.raises(IntegrityError):
            session.commit()


# --- completed this week counts periods -------------------------------------


def test_completed_counts_periods_when_the_school_logs_per_period():
    created = engine()
    with _session(created) as session:
        teacher = uuid4()
        room = uuid4()
        day = date(2026, 11, 10)
        session.add_all(
            [
                _log(day, classroom_id=room, period_id=uuid4(), teacher_id=teacher),
                _log(day, classroom_id=room, period_id=uuid4(), teacher_id=teacher),
            ]
        )
        session.commit()

        counts = workload_repository.completed_counts(
            session, [teacher], date(2026, 11, 9), date(2026, 11, 15)
        )
        assert counts[teacher] == 2


def test_completed_counts_days_when_the_school_logs_a_day_line():
    created = engine()
    with _session(created) as session:
        teacher = uuid4()
        session.add(_log(date(2026, 11, 10), teacher_id=teacher))
        session.commit()

        counts = workload_repository.completed_counts(
            session, [teacher], date(2026, 11, 9), date(2026, 11, 15)
        )
        assert counts[teacher] == 1
