"""The appraisal season: the window, the person's words, the reviewer's, the lock.

Every test here is a sentence a school has argued about:

* **opening a season creates a row for everybody on the roll** - the queue is the staff
  list, not whoever remembered the form;
* a season that is `Draft` (or `Closed`) cannot be filled in: `409`, not a silent write;
* **only the person may fill in their own appraisal**, and only until the reviewer has
  rated it - an office role is not a licence to write somebody's self-assessment;
* an HOD reviews their department and nobody else's, and **never themselves**;
* only a **reviewed** appraisal can be finalized, and a finalized one is `409` to
  every write - including the reviewer's;
* a goal nobody judged is `None`, not `False`.

Runs on in-memory SQLite, like the rest of this module's suite.
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
from app.domains.admin.users.models import User
from app.domains.auth.models import Role
from app.domains.auth.roles import grant_role
from app.domains.people.staff.models import Employee
from app.domains.people.teachers import labels
from app.domains.people.teachers.appraisal import service
from app.domains.people.teachers.appraisal.models import (
    Appraisal,
    AppraisalCycle,
    AppraisalGoal,
    TrainingRecord,
)
from app.domains.people.teachers.appraisal.schemas import (
    CycleIn,
    GoalIn,
    ReviewIn,
    SelfAssessmentIn,
    TrainingIn,
)


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


def _roles(session: Session) -> None:
    for codename, label in (
        ("principal", "Principal"),
        ("hod", "Head of Department"),
        ("teacher", "Teacher"),
    ):
        session.add(Role(codename=codename, label=label))
    session.commit()


def _person(
    session: Session, school_id, code: str, *, name, roles, department="Science"
):
    user = User(
        email=f"{code.lower()}@test",
        full_name=name,
        hashed_password="x",
        school_id=school_id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    for codename in roles:
        grant_role(session, user, codename)
    employee = Employee(
        user_id=user.id,
        employee_code=code,
        department=department,
        joining_date=date(2023, 6, 1),
        email=f"{code.lower()}@test",
    )
    session.add(employee)
    session.commit()
    session.refresh(employee)
    return user, employee


def _school(session: Session, name="Test School", code="APP-0001"):
    school = School(
        name=name,
        code=code,
        email=f"office@{code.lower()}.test",
        phone="9999999999",
        address="1 Test Road",
    )
    session.add(school)
    session.commit()
    session.refresh(school)
    return school


@pytest.fixture()
def seeded():
    """One school: a principal, a Science HOD, one Science teacher, one Maths teacher."""
    session = session_for(engine())
    _roles(session)
    school = _school(session)
    session.info["school_id"] = school.id

    principal, principal_row = _person(
        session, school.id, "EMP-0001", name="Principal One", roles=("principal",)
    )
    hod_user, hod = _person(
        session, school.id, "EMP-0002", name="Hod One", roles=("hod",)
    )
    one_user, one = _person(
        session, school.id, "EMP-0003", name="Teacher One", roles=("teacher",)
    )
    two_user, two = _person(
        session,
        school.id,
        "EMP-0004",
        name="Teacher Two",
        roles=("teacher",),
        department="Maths",
    )

    return SimpleNamespace(
        session=session,
        school=school,
        principal=principal,
        principal_row=principal_row,
        hod_user=hod_user,
        hod=hod,
        one_user=one_user,
        one=one,
        two_user=two_user,
        two=two,
    )


def _cycle(seeded, *, status: str = labels.CYCLE_OPEN):
    """A season, and the rows that opening it creates."""
    created = service.create_cycle(
        seeded.session,
        CycleIn(
            name="2026-27 Annual",
            start_date=date(2026, 4, 1),
            end_date=date(2027, 3, 31),
        ),
        seeded.principal,
    )
    if status == labels.CYCLE_OPEN:
        return service.set_cycle_status(
            seeded.session, created.id, labels.CYCLE_OPEN, seeded.principal
        )
    return created


def _row(seeded, cycle_id, employee_id):
    return seeded.session.exec(
        select(Appraisal).where(
            Appraisal.cycle_id == cycle_id, Appraisal.employee_id == employee_id
        )
    ).one()


# --- the season -------------------------------------------------------------


def test_a_new_season_is_a_draft_and_asks_nobody_for_anything(seeded):
    """`Draft` means planned: no appraisals, so no forms."""
    created = _cycle(seeded, status=labels.CYCLE_DRAFT)

    assert created.status == labels.CYCLE_DRAFT
    assert created.appraisals == 0
    assert seeded.session.exec(select(Appraisal)).all() == []


def test_opening_a_season_creates_a_row_for_everybody_on_the_roll(seeded):
    """The queue is the staff list, not whoever remembered the form."""
    created = _cycle(seeded)

    rows = seeded.session.exec(select(Appraisal)).all()
    assert len(rows) == 4  # principal, HOD, and the two teachers
    assert {row.status for row in rows} == {labels.APPRAISAL_DRAFT}
    assert created.appraisals == len(rows)


def test_two_seasons_cannot_share_a_name(seeded):
    _cycle(seeded, status=labels.CYCLE_DRAFT)
    with pytest.raises(HTTPException) as problem:
        service.create_cycle(
            seeded.session,
            CycleIn(
                name="2026-27 Annual",
                start_date=date(2027, 4, 1),
                end_date=date(2028, 3, 31),
            ),
            seeded.principal,
        )
    assert problem.value.status_code == 409


def test_a_window_that_ends_before_it_starts_is_refused(seeded):
    with pytest.raises(HTTPException) as problem:
        service.create_cycle(
            seeded.session,
            CycleIn(
                name="Backwards",
                start_date=date(2027, 3, 31),
                end_date=date(2026, 4, 1),
            ),
            seeded.principal,
        )
    assert problem.value.status_code == 422


def test_a_draft_season_cannot_be_filled_in(seeded):
    """No form is offered before the office opens the season."""
    created = _cycle(seeded, status=labels.CYCLE_DRAFT)
    service.set_cycle_status(
        seeded.session, created.id, labels.CYCLE_OPEN, seeded.principal
    )
    cycle = seeded.session.get(AppraisalCycle, created.id)
    cycle.status = labels.CYCLE_DRAFT
    seeded.session.add(cycle)
    seeded.session.commit()

    row = _row(seeded, created.id, seeded.one.id)
    with pytest.raises(HTTPException) as problem:
        service.save_self(
            seeded.session,
            row.id,
            SelfAssessmentIn(self_rating=4),
            seeded.one_user,
        )
    assert problem.value.status_code == 409


def test_only_the_office_opens_a_season(seeded):
    with pytest.raises(HTTPException) as problem:
        service.create_cycle(
            seeded.session,
            CycleIn(
                name="Mine",
                start_date=date(2026, 4, 1),
                end_date=date(2027, 3, 31),
            ),
            seeded.one_user,
        )
    assert problem.value.status_code == 403


# --- the person's own words -------------------------------------------------


def test_the_person_fills_in_their_own_appraisal(seeded):
    created = _cycle(seeded)
    row = _row(seeded, created.id, seeded.one.id)

    saved = service.save_self(
        seeded.session,
        row.id,
        SelfAssessmentIn(
            self_rating=4,
            self_note="steady year",
            goals=[
                GoalIn(title="Class 9 average above 75"),
                GoalIn(title="Two parent meetings a term", weight=2),
            ],
        ),
        seeded.one_user,
    )

    assert saved.self_rating == 4
    assert saved.status == labels.APPRAISAL_DRAFT
    assert saved.goals_total == 2
    assert saved.goals_judged == 0  # nobody has judged them yet
    assert [goal.achieved for goal in saved.goals] == [None, None]


def test_saving_again_replaces_the_goals(seeded):
    """A goal removed from the form is a goal the person no longer claims."""
    created = _cycle(seeded)
    row = _row(seeded, created.id, seeded.one.id)

    service.save_self(
        seeded.session,
        row.id,
        SelfAssessmentIn(self_rating=3, goals=[GoalIn(title="Old goal")]),
        seeded.one_user,
    )
    saved = service.save_self(
        seeded.session,
        row.id,
        SelfAssessmentIn(self_rating=4, goals=[GoalIn(title="New goal")]),
        seeded.one_user,
    )

    assert [goal.title for goal in saved.goals] == ["New goal"]
    assert len(seeded.session.exec(select(AppraisalGoal)).all()) == 1


def test_nobody_writes_somebody_elses_self_assessment(seeded):
    """`appraisals.self` is not a licence to fill in a colleague's form."""
    created = _cycle(seeded)
    row = _row(seeded, created.id, seeded.two.id)

    with pytest.raises(HTTPException) as problem:
        service.save_self(
            seeded.session, row.id, SelfAssessmentIn(self_rating=5), seeded.one_user
        )
    assert problem.value.status_code == 403


def test_submitting_needs_a_rating(seeded):
    created = _cycle(seeded)
    row = _row(seeded, created.id, seeded.one.id)

    with pytest.raises(HTTPException) as problem:
        service.submit(seeded.session, row.id, seeded.one_user)
    assert problem.value.status_code == 409
    assert "rating" in problem.value.detail


def test_submitting_twice_is_the_same_answer(seeded):
    created = _cycle(seeded)
    row = _row(seeded, created.id, seeded.one.id)
    service.save_self(
        seeded.session, row.id, SelfAssessmentIn(self_rating=4), seeded.one_user
    )

    first = service.submit(seeded.session, row.id, seeded.one_user)
    second = service.submit(seeded.session, row.id, seeded.one_user)

    assert first.status == labels.APPRAISAL_SUBMITTED
    assert second.status == labels.APPRAISAL_SUBMITTED
    assert seeded.session.get(Appraisal, row.id).submitted_at is not None


# --- the reviewer -----------------------------------------------------------


def _submitted(seeded):
    created = _cycle(seeded)
    row = _row(seeded, created.id, seeded.one.id)
    service.save_self(
        seeded.session,
        row.id,
        SelfAssessmentIn(
            self_rating=4, goals=[GoalIn(title="Class 9 average above 75")]
        ),
        seeded.one_user,
    )
    return service.submit(seeded.session, row.id, seeded.one_user)


def test_a_reviewer_rates_a_submitted_appraisal(seeded):
    """The Science HOD reviews the Science teacher."""
    reviewed = service.review(
        seeded.session,
        _submitted(seeded).id,
        ReviewIn(reviewer_rating=4, reviewer_note="agree, with the caveat"),
        seeded.hod_user,
    )

    assert reviewed.status == labels.APPRAISAL_REVIEWED
    assert reviewed.reviewer_rating == 4
    assert reviewed.reviewer_name == "Hod One"
    assert reviewed.reviewed_at is not None


def test_a_draft_cannot_be_reviewed(seeded):
    """There is nothing to answer yet."""
    created = _cycle(seeded)
    row = _row(seeded, created.id, seeded.one.id)

    with pytest.raises(HTTPException) as problem:
        service.review(
            seeded.session, row.id, ReviewIn(reviewer_rating=3), seeded.hod_user
        )
    assert problem.value.status_code == 409
    assert "not been submitted" in problem.value.detail


def test_an_hod_reviews_their_department_only(seeded):
    """Teacher Two is Maths: not the Science head's to rate (`403`)."""
    created = _cycle(seeded)
    row = _row(seeded, created.id, seeded.two.id)
    service.save_self(
        seeded.session, row.id, SelfAssessmentIn(self_rating=4), seeded.two_user
    )
    service.submit(seeded.session, row.id, seeded.two_user)

    with pytest.raises(HTTPException) as problem:
        service.review(
            seeded.session, row.id, ReviewIn(reviewer_rating=4), seeded.hod_user
        )
    assert problem.value.status_code == 403


def test_nobody_reviews_themselves(seeded):
    """The HOD's own appraisal is the principal's to review."""
    created = _cycle(seeded)
    row = _row(seeded, created.id, seeded.hod.id)
    service.save_self(
        seeded.session, row.id, SelfAssessmentIn(self_rating=5), seeded.hod_user
    )
    service.submit(seeded.session, row.id, seeded.hod_user)

    with pytest.raises(HTTPException) as problem:
        service.review(
            seeded.session, row.id, ReviewIn(reviewer_rating=5), seeded.hod_user
        )
    assert problem.value.status_code == 403

    reviewed = service.review(
        seeded.session, row.id, ReviewIn(reviewer_rating=4), seeded.principal
    )
    assert reviewed.status == labels.APPRAISAL_REVIEWED


def test_a_goal_is_judged_by_the_reviewer(seeded):
    """`achieved` stays `None` until somebody with the right says otherwise."""
    reviewed = service.review(
        seeded.session,
        _submitted(seeded).id,
        ReviewIn(reviewer_rating=4),
        seeded.hod_user,
    )
    goal = reviewed.goals[0]
    assert goal.achieved is None

    judged = service.decide_goal(seeded.session, goal.id, True, seeded.hod_user)
    assert judged.goals[0].achieved is True
    assert judged.goals_achieved == 1
    assert judged.goals_judged == 1


# --- the lock ---------------------------------------------------------------


def test_only_a_reviewed_appraisal_can_be_finalized(seeded):
    submitted = _submitted(seeded)
    with pytest.raises(HTTPException) as problem:
        service.finalize(seeded.session, submitted.id, seeded.principal)
    assert problem.value.status_code == 409
    assert "reviewed" in problem.value.detail


def test_finalizing_locks_every_write(seeded):
    """The number has been told to somebody: nothing changes after it."""
    reviewed = service.review(
        seeded.session,
        _submitted(seeded).id,
        ReviewIn(reviewer_rating=4),
        seeded.hod_user,
    )
    finalized = service.finalize(seeded.session, reviewed.id, seeded.principal)
    assert finalized.status == labels.APPRAISAL_FINALIZED
    assert finalized.finalized_at is not None

    # Finalizing twice is the same answer.
    again = service.finalize(seeded.session, reviewed.id, seeded.principal)
    assert again.finalized_at == finalized.finalized_at

    for write in (
        lambda: service.review(
            seeded.session, reviewed.id, ReviewIn(reviewer_rating=1), seeded.hod_user
        ),
        lambda: service.save_self(
            seeded.session,
            reviewed.id,
            SelfAssessmentIn(self_rating=1),
            seeded.one_user,
        ),
        lambda: service.decide_goal(
            seeded.session, finalized.goals[0].id, False, seeded.hod_user
        ),
    ):
        with pytest.raises(HTTPException) as problem:
            write()
        assert problem.value.status_code == 409


def test_only_the_office_finalizes(seeded):
    reviewed = service.review(
        seeded.session,
        _submitted(seeded).id,
        ReviewIn(reviewer_rating=4),
        seeded.hod_user,
    )
    with pytest.raises(HTTPException) as problem:
        service.finalize(seeded.session, reviewed.id, seeded.hod_user)
    assert problem.value.status_code == 403


# --- the queue and training -------------------------------------------------


def test_a_teacher_reads_their_own_appraisal_and_no_other(seeded):
    created = _cycle(seeded)
    queue = service.queue(seeded.session, created.id, seeded.one_user)

    assert [row.employee_id for row in queue.rows] == [seeded.one.id]
    assert queue.mine is not None
    assert queue.mine.employee_id == seeded.one.id
    assert queue.total == 1


def test_the_office_reads_the_whole_season(seeded):
    created = _cycle(seeded)
    queue = service.queue(seeded.session, created.id, seeded.principal)

    assert queue.total == 4
    assert queue.cycle.appraisals == 4


def test_training_is_recorded_and_read_back(seeded):
    recorded = service.add_training(
        seeded.session,
        seeded.one.id,
        TrainingIn(
            title="Classroom assessment",
            provider="SCERT",
            on_date=date(2026, 6, 10),
            hours=6,
        ),
        seeded.principal,
    )
    assert recorded.hours == 6

    rows = service.training(seeded.session, seeded.one.id, seeded.one_user)
    assert [row.title for row in rows] == ["Classroom assessment"]
    assert len(seeded.session.exec(select(TrainingRecord)).all()) == 1


def test_a_teacher_cannot_record_training(seeded):
    with pytest.raises(HTTPException) as problem:
        service.add_training(
            seeded.session,
            seeded.one.id,
            TrainingIn(title="Self-declared", on_date=date(2026, 6, 10)),
            seeded.one_user,
        )
    assert problem.value.status_code == 403
