"""The staff leave workflow: apply, decide, and the balance behind both.

Every test here pins a number or a rule that is invisible in the browser when it is
wrong:

* **the balance is derived**, so a cancelled or rejected leave gives its days back
  with no update - and a *pending* one already blocks a second promise;
* **an untracked type has no limit and is not "0 days left"** - `None` and `0` are
  different sentences to a teacher;
* **the same decision twice is a no-op**: approving twice must not rewrite when the
  school decided, and must not write a second audit line;
* **nobody decides their own leave**, and a teacher cannot file or cancel for a
  colleague;
* **the year is the leave's own start year**, so a December request is measured
  against December's entitlement.

Runs on in-memory SQLite, like the rest of this module's suite.
"""

import importlib
from datetime import date
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.schema import MODEL_MODULES
from app.domains.admin.platform.models import School
from app.domains.admin.users.models import User
from app.domains.auth.models import Role
from app.domains.auth.roles import grant_role
from app.domains.people.staff.models import Employee
from app.domains.people.teachers.models import StaffAuditLog
from app.domains.services.leave import labels, repository, service, workflow
from app.domains.services.leave.models import LeaveRequest
from app.domains.services.leave.schemas import (
    LeaveApplyIn,
    LeaveBalanceWrite,
    LeavePoliciesWrite,
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
        ("vice_principal", "Vice Principal"),
        ("teacher", "Teacher"),
        ("hod", "Head of Department"),
        ("school_admin", "School Administrator"),
    ):
        session.add(Role(codename=codename, label=label))
    session.commit()


def _school(session: Session, name: str = "Test School", code: str = "TST-0001"):
    school = School(
        name=name,
        code=code,
        email=f"office@{code.lower()}.test",
    )
    session.add(school)
    session.commit()
    session.refresh(school)
    return school


def _user(session: Session, name: str, school_id, roles: tuple[str, ...]) -> User:
    user = User(
        email=f"{name.lower().replace(' ', '.')}@test",
        full_name=name,
        hashed_password="x",
        school_id=school_id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    for codename in roles:
        grant_role(session, user, codename)
    return user


def _person(
    session: Session,
    school_id,
    code: str,
    *,
    name: str | None = None,
    roles: tuple[str, ...] = ("teacher",),
    **extra,
) -> tuple[User, Employee]:
    user = _user(session, name or f"Staff {code}", school_id, roles)
    employee = Employee(
        user_id=user.id,
        employee_code=code,
        department=extra.pop("department", "Science"),
        joining_date=extra.pop("joining_date", date(2023, 6, 1)),
        email=f"{code.lower()}@test",
        **extra,
    )
    session.add(employee)
    session.commit()
    session.refresh(employee)
    return user, employee


def _apply(
    *,
    employee_id=None,
    student_id=None,
    leave_type: str = "Casual",
    from_date: date = date(2026, 11, 20),
    to_date: date | None = None,
    reason: str = "Family function",
) -> LeaveApplyIn:
    return LeaveApplyIn(
        employee_id=employee_id,
        student_id=student_id,
        leave_type=leave_type,
        from_date=from_date,
        to_date=to_date or from_date,
        reason=reason,
    )


@pytest.fixture()
def world():
    """A school with a principal, an HOD, a teacher and a second teacher."""
    created = engine()
    session = session_for(created)
    _roles(session)
    school = _school(session)
    session.info["school_id"] = school.id
    principal_user, principal = _person(
        session,
        school.id,
        "EMP-0001",
        name="Principal Rao",
        roles=("principal",),
    )
    hod_user, hod = _person(
        session,
        school.id,
        "EMP-0002",
        name="Hod Iyer",
        roles=("hod",),
        department="Science",
    )
    teacher_user, teacher = _person(
        session, school.id, "EMP-0003", name="Teacher Sharma", department="Science"
    )
    other_user, other = _person(
        session, school.id, "EMP-0004", name="Teacher Bose", department="Arts"
    )
    return {
        "session": session,
        "school": school,
        "principal": principal_user,
        "principal_employee": principal,
        "hod": hod_user,
        "hod_employee": hod,
        "teacher": teacher_user,
        "teacher_employee": teacher,
        "other": other_user,
        "other_employee": other,
    }


def _audit(session: Session, employee_id) -> list[StaffAuditLog]:
    return list(
        session.exec(
            select(StaffAuditLog).where(StaffAuditLog.employee_id == employee_id)
        ).all()
    )


# --- vocabulary -------------------------------------------------------------


def test_days_are_inclusive_of_both_ends():
    """A Friday-to-Monday leave is four days in a school office, not three."""
    assert labels.days_between(date(2026, 11, 20), date(2026, 11, 23)) == 4
    assert labels.days_between(date(2026, 11, 20), date(2026, 11, 20)) == 1


def test_a_backwards_range_counts_nothing():
    """The schema refuses it; this function reports rather than judges."""
    assert labels.days_between(date(2026, 11, 23), date(2026, 11, 20)) == 0


def test_an_untracked_type_has_no_limit_and_is_not_zero():
    """`None` is "this school tracks no balance", `0` is "none left"."""
    assert labels.balance_left(entitled=None, used=4, pending=0) is None
    assert labels.over_limit(entitled=None, used=99, pending=0, days=30) is False
    assert labels.balance_left(entitled=12, used=4, pending=2) == 6
    assert labels.over_limit(entitled=12, used=4, pending=2, days=7) is True


def test_a_negative_balance_is_reported_not_clamped():
    """An override lowered after the fact has to show up as a correction to make."""
    assert labels.balance_left(entitled=5, used=8, pending=0) == -3


def test_type_keys_compare_the_same_word_case_insensitively():
    assert labels.type_key("  Casual ") == labels.type_key("CASUAL") == "casual"


# --- the policy -------------------------------------------------------------


def test_defaults_answer_before_any_policy_is_written(world):
    """A school that never opened the screen still has a working apply form."""
    rows = service.policies_read(world["session"])
    granted = {row.leave_type: row.annual_days for row in rows}
    assert granted == labels.DEFAULT_POLICIES
    # No row was saved, so nothing claims to have been set by a person.
    assert all(row.updated_by is None for row in rows)


def test_saving_a_policy_upserts_and_leaves_other_types_alone(world):
    session, principal = world["session"], world["principal"]
    first = workflow.save_policies(
        session,
        LeavePoliciesWrite(
            policies=[
                {"leave_type": "Casual", "annual_days": 10},
                {"leave_type": "Sick", "annual_days": 6},
            ]
        ),
        principal,
    )
    assert {row.leave_type: row.annual_days for row in first} == {
        "Casual": 10,
        "Sick": 6,
    }

    # A second save mentioning one type must not delete the other.
    second = workflow.save_policies(
        session,
        LeavePoliciesWrite(policies=[{"leave_type": "Casual", "annual_days": 14}]),
        principal,
    )
    assert {row.leave_type: row.annual_days for row in second} == {
        "Casual": 14,
        "Sick": 6,
    }
    assert all(row.updated_by == "Principal Rao" for row in second)
    # Stored rows replace the defaults wholesale.
    assert repository.effective_policies(session) == {
        "casual": ("Casual", 14),
        "sick": ("Sick", 6),
    }


def test_only_the_office_may_write_the_policy(world):
    session = world["session"]
    with pytest.raises(HTTPException) as refusal:
        workflow.save_policies(
            session,
            LeavePoliciesWrite(policies=[{"leave_type": "Casual", "annual_days": 99}]),
            world["teacher"],
        )
    assert refusal.value.status_code == 403
    # An HOD decides leave but does not sign entitlements.
    with pytest.raises(HTTPException) as hod_refusal:
        workflow.save_policies(
            session,
            LeavePoliciesWrite(policies=[{"leave_type": "Casual", "annual_days": 99}]),
            world["hod"],
        )
    assert hod_refusal.value.status_code == 403


def test_one_row_per_leave_type_in_a_save():
    with pytest.raises(ValidationError) as invalid:
        LeavePoliciesWrite(
            policies=[
                {"leave_type": "Casual", "annual_days": 10},
                {"leave_type": "casual", "annual_days": 12},
            ]
        )
    assert "appears twice" in str(invalid.value)


def test_a_type_in_use_cannot_be_deleted(world):
    """`annual_days = 0` retires a type; deleting it would orphan the requests."""
    session = world["session"]
    workflow.save_policies(
        session,
        LeavePoliciesWrite(
            policies=[
                {"leave_type": "Casual", "annual_days": 12},
                {"leave_type": "Bereavement", "annual_days": 3},
            ]
        ),
        world["principal"],
    )
    workflow.apply_leave(
        session, _apply(employee_id=world["teacher_employee"].id), world["principal"]
    )

    with pytest.raises(HTTPException) as in_use:
        workflow.delete_policy(session, "Casual", world["principal"])
    assert in_use.value.status_code == 409

    # An unused type goes, and is gone from the list afterwards.
    workflow.delete_policy(session, "bereavement", world["principal"])
    assert [row.leave_type for row in service.policies_read(session)] == ["Casual"]


# --- applying ---------------------------------------------------------------


def test_a_teacher_files_their_own_leave(world):
    session, teacher = world["session"], world["teacher"]
    read = workflow.apply_leave(
        session,
        _apply(from_date=date(2026, 11, 20), to_date=date(2026, 11, 22)),
        teacher,
    )

    assert read.status == labels.PENDING
    assert read.scope == "staff"
    assert read.days == 3
    assert read.person == "Teacher Sharma"
    assert read.person_code == "EMP-0003"
    # The requester is the staff member, not whoever may have filed it: the
    # register derives `On Leave` from this column.
    row = session.get(LeaveRequest, read.id)
    assert row.requester_user_id == world["teacher_employee"].user_id
    # 12 entitled, 3 pending, so 9 are still free to ask for.
    assert read.balance_remaining == 9


def test_the_office_files_on_somebodys_behalf(world):
    session = world["session"]
    read = workflow.apply_leave(
        session,
        _apply(employee_id=world["teacher_employee"].id),
        world["principal"],
    )
    assert read.person == "Teacher Sharma"
    # The trail is on the teacher's file, not the principal's.
    assert _audit(session, world["teacher_employee"].id)
    assert not _audit(session, world["principal_employee"].id)


def test_a_teacher_cannot_file_for_a_colleague(world):
    """A teacher-only account cannot even see the colleague: the domain answers 404."""
    session = world["session"]
    with pytest.raises(HTTPException) as refusal:
        workflow.apply_leave(
            session, _apply(employee_id=world["other_employee"].id), world["teacher"]
        )
    assert refusal.value.status_code == 404

    # A role that *can* see the roster but does not decide leave is a plain 403.
    desk = _user(session, "Front Desk", world["school"].id, ("staff",))
    with pytest.raises(HTTPException) as office_refusal:
        workflow.apply_leave(
            session, _apply(employee_id=world["other_employee"].id), desk
        )
    assert office_refusal.value.status_code == 403
    assert "somebody else" in office_refusal.value.detail


def test_an_unknown_leave_type_names_the_ones_the_school_grants(world):
    session = world["session"]
    with pytest.raises(HTTPException) as refusal:
        workflow.apply_leave(session, _apply(leave_type="Sabbatical"), world["teacher"])
    assert refusal.value.status_code == 422
    assert "Casual" in refusal.value.detail


def test_the_type_is_stored_in_the_schools_own_spelling(world):
    """`casual` and `Casual` cannot become two balances for one teacher."""
    session = world["session"]
    read = workflow.apply_leave(session, _apply(leave_type="casual"), world["teacher"])
    assert read.leave_type == "Casual"


def test_a_reversed_range_is_refused_at_the_edge():
    with pytest.raises(ValidationError) as invalid:
        _apply(from_date=date(2026, 11, 22), to_date=date(2026, 11, 20))
    assert "ends before it starts" in str(invalid.value)


def test_one_leave_belongs_to_one_person():
    with pytest.raises(ValidationError) as invalid:
        _apply(employee_id=uuid4(), student_id=uuid4())
    assert "either an employee or a student" in str(invalid.value)


def test_a_clashing_leave_is_refused(world):
    session, teacher = world["session"], world["teacher"]
    workflow.apply_leave(
        session,
        _apply(from_date=date(2026, 11, 20), to_date=date(2026, 11, 22)),
        teacher,
    )

    with pytest.raises(HTTPException) as refusal:
        workflow.apply_leave(
            session,
            _apply(from_date=date(2026, 11, 21), to_date=date(2026, 11, 24)),
            teacher,
        )
    assert refusal.value.status_code == 409
    assert "already has a pending" in refusal.value.detail


def test_a_cancelled_leave_does_not_block_a_new_one(world):
    session, teacher = world["session"], world["teacher"]
    first = workflow.apply_leave(
        session,
        _apply(from_date=date(2026, 11, 20), to_date=date(2026, 11, 22)),
        teacher,
    )
    workflow.decide(session, first.id, action="cancel", user=teacher)

    again = workflow.apply_leave(
        session,
        _apply(from_date=date(2026, 11, 21), to_date=date(2026, 11, 23)),
        teacher,
    )
    assert again.status == labels.PENDING
    assert again.days == 3


def test_a_request_beyond_the_entitlement_is_refused_with_the_numbers(world):
    session, teacher = world["session"], world["teacher"]
    # Casual grants 12 days; ask for 13.
    with pytest.raises(HTTPException) as refusal:
        workflow.apply_leave(
            session,
            _apply(from_date=date(2026, 11, 2), to_date=date(2026, 11, 14)),
            teacher,
        )
    assert refusal.value.status_code == 409
    assert "12 entitled" in refusal.value.detail
    assert "0 used" in refusal.value.detail
    # The refusal wrote nothing.
    assert session.exec(select(LeaveRequest)).all() == []


def test_pending_days_already_spoken_for_are_counted(world):
    """11 days pending leave 1; a second request for 2 must be refused."""
    session, teacher = world["session"], world["teacher"]
    workflow.apply_leave(
        session,
        _apply(from_date=date(2026, 11, 2), to_date=date(2026, 11, 12)),
        teacher,
    )
    with pytest.raises(HTTPException) as refusal:
        workflow.apply_leave(
            session,
            _apply(from_date=date(2026, 12, 1), to_date=date(2026, 12, 2)),
            teacher,
        )
    assert refusal.value.status_code == 409
    assert "11 pending" in refusal.value.detail


def test_a_leaver_cannot_be_given_new_leave(world):
    session = world["session"]
    world["other_employee"].left_on = date(2026, 10, 31)
    session.add(world["other_employee"])
    session.commit()

    with pytest.raises(HTTPException) as refusal:
        workflow.apply_leave(
            session, _apply(employee_id=world["other_employee"].id), world["principal"]
        )
    assert refusal.value.status_code == 409
    assert "off the staff roll" in refusal.value.detail


def test_a_login_without_a_staff_record_cannot_file_for_itself(world):
    session = world["session"]
    outsider = _user(session, "Front Desk", world["school"].id, ("staff",))
    with pytest.raises(HTTPException) as refusal:
        workflow.apply_leave(session, _apply(), outsider)
    assert refusal.value.status_code == 409
    assert "not attached to a staff record" in refusal.value.detail


# --- balances ---------------------------------------------------------------


def test_the_balance_counts_approved_pending_and_what_is_left(world):
    session, teacher = world["session"], world["teacher"]
    approved = workflow.apply_leave(
        session,
        _apply(from_date=date(2026, 11, 2), to_date=date(2026, 11, 4)),
        teacher,
    )
    workflow.decide(session, approved.id, action="approve", user=world["principal"])
    workflow.apply_leave(
        session,
        _apply(from_date=date(2026, 12, 1), to_date=date(2026, 12, 2)),
        teacher,
    )

    register = service.balance_register(
        session,
        year=2026,
        employee_id=world["teacher_employee"].id,
        user=world["principal"],
    )
    casual = next(row for row in register.rows if row.leave_type == "Casual")
    assert (casual.entitled, casual.used, casual.pending) == (12, 3, 2)
    assert casual.remaining == 7
    assert casual.source == "policy"
    assert casual.staff_name == "Teacher Sharma"
    # Every type the school grants gets a row, tracked or not.
    assert register.types == sorted(labels.DEFAULT_POLICIES)


def test_an_override_beats_the_policy_and_is_the_offices_to_give(world):
    session = world["session"]
    with pytest.raises(HTTPException) as refusal:
        workflow.save_balance(
            session,
            world["teacher_employee"].id,
            LeaveBalanceWrite(leave_type="Casual", year=2026, entitled_days=20),
            world["hod"],
        )
    assert refusal.value.status_code == 403

    row = workflow.save_balance(
        session,
        world["teacher_employee"].id,
        LeaveBalanceWrite(
            leave_type="Casual", year=2026, entitled_days=20, note="joined mid-year"
        ),
        world["principal"],
    )
    assert (row.entitled, row.remaining, row.source) == (20, 20, "override")

    register = service.balance_register(
        session,
        year=2026,
        employee_id=world["teacher_employee"].id,
        user=world["principal"],
    )
    casual = next(row for row in register.rows if row.leave_type == "Casual")
    assert (casual.entitled, casual.source) == (20, "override")


def test_an_override_must_name_a_type_the_school_grants(world):
    session = world["session"]
    with pytest.raises(HTTPException) as refusal:
        workflow.save_balance(
            session,
            world["teacher_employee"].id,
            LeaveBalanceWrite(leave_type="Sabbatical", year=2026, entitled_days=5),
            world["principal"],
        )
    assert refusal.value.status_code == 422


def test_a_cancelled_leave_gives_its_days_back(world):
    """No counter to decrement: the days are summed from the rows themselves."""
    session, teacher = world["session"], world["teacher"]
    read = workflow.apply_leave(
        session,
        _apply(from_date=date(2026, 11, 2), to_date=date(2026, 11, 4)),
        teacher,
    )
    workflow.decide(session, read.id, action="approve", user=world["principal"])
    assert service.days_for(
        session, employee=world["teacher_employee"], leave_type="Casual", year=2026
    ) == (3, 0)

    workflow.decide(session, read.id, action="cancel", user=world["principal"])
    assert service.days_for(
        session, employee=world["teacher_employee"], leave_type="Casual", year=2026
    ) == (0, 0)


def test_a_leave_is_counted_in_the_year_it_starts(world):
    """A December request belongs to December's entitlement, not next year's."""
    session, teacher = world["session"], world["teacher"]
    workflow.apply_leave(
        session,
        _apply(from_date=date(2025, 12, 29), to_date=date(2026, 1, 2)),
        teacher,
    )
    assert service.days_for(
        session, employee=world["teacher_employee"], leave_type="Casual", year=2025
    ) == (0, 5)
    assert service.days_for(
        session, employee=world["teacher_employee"], leave_type="Casual", year=2026
    ) == (0, 0)


def test_a_teacher_only_account_reads_its_own_balance(world):
    session = world["session"]
    register = service.balance_register(session, year=2026, user=world["teacher"])
    people = {row.employee_code for row in register.rows}
    assert people == {"EMP-0003"}


def test_an_untracked_type_reports_no_entitlement_rather_than_zero(world):
    session = world["session"]
    assert (
        service.entitlement_for(
            session,
            employee=world["teacher_employee"],
            leave_type="Sabbatical",
            year=2026,
        )
        is None
    )
    assert service.days_for(
        session, employee=world["teacher_employee"], leave_type="Sabbatical", year=2026
    ) == (0, 0)


# --- deciding ---------------------------------------------------------------


def _filed(world, **kwargs):
    """A pending leave on the teacher's file, filed by the principal."""
    return workflow.apply_leave(
        world["session"],
        _apply(employee_id=world["teacher_employee"].id, **kwargs),
        world["principal"],
    )


def test_approving_sets_the_decision_the_decider_and_writes_one_audit_line(world):
    session = world["session"]
    read = _filed(world)

    approved = workflow.decide(
        session, read.id, action="approve", note="approved", user=world["principal"]
    )
    assert approved.status == labels.APPROVED
    assert approved.decided_by == "Principal Rao"
    assert approved.decided_at
    assert approved.decision_note == "approved"

    trail = _audit(session, world["teacher_employee"].id)
    assert [row.section for row in trail] == ["leave", "leave"]
    assert trail[-1].summary.endswith("Approved: approved")
    assert trail[-1].action == "updated"


def test_approving_twice_is_the_same_answer_and_writes_nothing_more(world):
    session = world["session"]
    read = _filed(world)
    first = workflow.decide(session, read.id, action="approve", user=world["principal"])
    lines = len(_audit(session, world["teacher_employee"].id))

    second = workflow.decide(
        session, read.id, action="approve", user=world["principal"]
    )
    assert second.status == labels.APPROVED
    # The record of *when* the school decided must not move on a double click.
    assert second.decided_at == first.decided_at
    assert len(_audit(session, world["teacher_employee"].id)) == lines


def test_nobody_approves_their_own_leave(world):
    session, teacher = world["session"], world["teacher"]
    read = workflow.apply_leave(session, _apply(), teacher)
    with pytest.raises(HTTPException) as refusal:
        workflow.decide(session, read.id, action="approve", user=teacher)
    assert refusal.value.status_code == 403
    assert "your own leave" in refusal.value.detail


def test_rejecting_keeps_the_offices_reason(world):
    session = world["session"]
    read = _filed(world)
    rejected = workflow.decide(
        session,
        read.id,
        action="reject",
        note="clashes with the annual exam",
        user=world["principal"],
    )
    assert rejected.status == labels.REJECTED
    assert rejected.decision_note == "clashes with the annual exam"
    assert rejected.balance_remaining == 12  # nothing was spent


def test_a_rejected_leave_cannot_be_approved(world):
    session = world["session"]
    read = _filed(world)
    workflow.decide(session, read.id, action="reject", user=world["principal"])
    with pytest.raises(HTTPException) as refusal:
        workflow.decide(session, read.id, action="approve", user=world["principal"])
    assert refusal.value.status_code == 409
    assert "already rejected" in refusal.value.detail


def test_an_approved_leave_is_cancelled_not_rejected(world):
    session = world["session"]
    read = _filed(world)
    workflow.decide(session, read.id, action="approve", user=world["principal"])
    with pytest.raises(HTTPException) as refusal:
        workflow.decide(session, read.id, action="reject", user=world["principal"])
    assert refusal.value.status_code == 409
    assert "cancel it instead" in refusal.value.detail


def test_cancelling_a_rejected_leave_is_refused(world):
    session = world["session"]
    read = _filed(world)
    workflow.decide(session, read.id, action="reject", user=world["principal"])
    with pytest.raises(HTTPException) as refusal:
        workflow.decide(session, read.id, action="cancel", user=world["principal"])
    assert refusal.value.status_code == 409
    assert "nothing to cancel" in refusal.value.detail


def test_the_person_who_filed_it_may_withdraw_their_own_leave(world):
    session, teacher = world["session"], world["teacher"]
    read = workflow.apply_leave(session, _apply(), teacher)
    withdrawn = workflow.decide(session, read.id, action="cancel", user=teacher)
    assert withdrawn.status == labels.CANCELLED

    # And saying so twice is the same answer, not an error.
    again = workflow.decide(session, read.id, action="cancel", user=teacher)
    assert again.status == labels.CANCELLED


def test_a_colleague_cannot_cancel_somebody_elses_leave(world):
    session = world["session"]
    read = _filed(world)
    # A teacher who cannot see the colleague gets the domain's own 404.
    with pytest.raises(HTTPException) as refusal:
        workflow.decide(session, read.id, action="cancel", user=world["other"])
    assert refusal.value.status_code == 404

    # A role that sees the roster but may not decide is refused as such.
    desk = _user(session, "Front Desk", world["school"].id, ("staff",))
    with pytest.raises(HTTPException) as office_refusal:
        workflow.decide(session, read.id, action="cancel", user=desk)
    assert office_refusal.value.status_code == 403
    assert "or the office" in office_refusal.value.detail


def test_an_approval_that_would_overrun_a_lowered_entitlement_is_refused(world):
    """The balance is re-checked on approval: days promised to others count too."""
    session, teacher = world["session"], world["teacher"]
    # 6 + 6 = 12 = the policy's grant, so both are accepted while pending.
    first = workflow.apply_leave(
        session,
        _apply(from_date=date(2026, 11, 2), to_date=date(2026, 11, 7)),
        teacher,
    )
    workflow.apply_leave(
        session,
        _apply(from_date=date(2026, 12, 7), to_date=date(2026, 12, 12)),
        teacher,
    )
    # The office then corrects the grant down to 10 days: the two together no
    # longer fit, and approving one of them would promise days nobody has.
    workflow.save_balance(
        session,
        world["teacher_employee"].id,
        LeaveBalanceWrite(leave_type="Casual", year=2026, entitled_days=10),
        world["principal"],
    )

    with pytest.raises(HTTPException) as refusal:
        workflow.decide(session, first.id, action="approve", user=world["principal"])
    assert refusal.value.status_code == 409
    assert "no longer fits" in refusal.value.detail
    # The request is untouched: still pending, still nothing spent.
    session.refresh(session.get(LeaveRequest, first.id))
    assert session.get(LeaveRequest, first.id).status == labels.PENDING


def test_an_unknown_request_is_a_404(world):
    session = world["session"]
    with pytest.raises(HTTPException) as refusal:
        workflow.decide(session, uuid4(), action="approve", user=world["principal"])
    assert refusal.value.status_code == 404
    with pytest.raises(HTTPException) as read_refusal:
        workflow.read_request(session, uuid4(), world["principal"])
    assert read_refusal.value.status_code == 404


# --- the student screen -----------------------------------------------------


def test_a_student_leave_files_and_decides_without_a_balance(world):
    from app.domains.academic.classroom.students.models import Student

    session = world["session"]
    student_user = _user(session, "Aarav Mehta", world["school"].id, ("student",))
    student = Student(
        user_id=student_user.id,
        admission_number="ADM-0001",
        school_id=world["school"].id,
    )
    session.add(student)
    session.commit()
    session.refresh(student)

    read = workflow.apply_leave(
        session,
        _apply(student_id=student.id, leave_type="od", from_date=date(2026, 11, 20)),
        # Filed by the class teacher, decided by the principal: nobody approves
        # the request they filed themselves.
        world["teacher"],
    )
    assert read.scope == "student"
    assert read.leave_type == "OD"
    assert read.person == "Aarav Mehta"
    # A student has no employment entitlement, so there is no number to print.
    assert read.balance_remaining is None

    approved = workflow.decide(
        session, read.id, action="approve", user=world["principal"]
    )
    assert approved.status == labels.APPROVED


def test_a_student_leave_type_outside_the_screens_list_is_refused(world):
    from app.domains.academic.classroom.students.models import Student

    session = world["session"]
    student_user = _user(session, "Aarav Mehta", world["school"].id, ("student",))
    student = Student(
        user_id=student_user.id,
        admission_number="ADM-0001",
        school_id=world["school"].id,
    )
    session.add(student)
    session.commit()
    session.refresh(student)

    with pytest.raises(HTTPException) as refusal:
        workflow.apply_leave(
            session,
            _apply(student_id=student.id, leave_type="Casual"),
            world["principal"],
        )
    assert refusal.value.status_code == 422
    assert "Medical" in refusal.value.detail
