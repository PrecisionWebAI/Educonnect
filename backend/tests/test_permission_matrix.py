"""The permission matrix: every codename is real, held, and not held by the wrong role.

Phase 9's first job was the matrix, and a matrix is only worth having if it is
checked rather than reviewed. These tests fail for the mistakes that actually happen:

* a codename added to `PermissionEnum` and to no role - a right nobody can hold;
* a string typed into a role list that is not a codename - a right nobody can see;
* a duplicate inside a role list - a merge that went wrong, hiding a missing entry;
* a right handed to a role that must not have it (an HOD finalising an appraisal, a
  teacher reading the whole register).

No database and no fixtures: this is a contract test over the matrix itself.
"""

from app.domains.auth.permissions import (
    ADMIN_PERMISSIONS,
    ALL_PERMISSIONS,
    DIRECTOR_PERMISSIONS,
    HOD_PERMISSIONS,
    PRINCIPAL_PERMISSIONS,
    ROLE_PERMISSIONS_MAP,
    SCHOOL_ADMIN_PERMISSIONS,
    SYSTEM_ADMIN_PERMISSIONS,
    TEACHER_PERMISSIONS,
    VICE_PRINCIPAL_PERMISSIONS,
    PermissionEnum,
)

CATALOGUE = {permission.value for permission in PermissionEnum}


def test_the_catalogue_and_the_flat_list_agree():
    """`ALL_PERMISSIONS` is the enum, not a second hand-written list."""
    assert set(ALL_PERMISSIONS) == CATALOGUE
    assert len(ALL_PERMISSIONS) == len(CATALOGUE)


def test_every_role_list_only_names_real_codenames():
    """A typo in a role list is a permission nobody can ever hold."""
    for role, held in ROLE_PERMISSIONS_MAP.items():
        unknown = set(held) - CATALOGUE
        assert unknown == set(), f"{role} names unknown permissions: {sorted(unknown)}"


def test_no_role_list_repeats_itself():
    """A duplicate hides the entry that was meant to be there."""
    for role, held in ROLE_PERMISSIONS_MAP.items():
        assert len(held) == len(set(held)), f"{role} repeats a permission"


def test_every_codename_is_held_by_somebody():
    """A right no role holds is dead weight the matrix claims to grant."""
    granted = {
        permission for held in ROLE_PERMISSIONS_MAP.values() for permission in held
    }
    assert CATALOGUE - granted == set()


def test_the_platform_admin_holds_everything():
    assert set(SYSTEM_ADMIN_PERMISSIONS) == CATALOGUE


def test_the_school_admin_holds_everything_but_impersonation():
    """One school, everything inside it; impersonation stays with the platform."""
    assert set(SCHOOL_ADMIN_PERMISSIONS) == CATALOGUE - {"users.impersonate"}


def test_the_director_and_the_principal_sign_the_seasons():
    """Both run the school, so both hold the appraisal lock and the leave policy."""
    for role, held in (
        ("director", DIRECTOR_PERMISSIONS),
        ("principal", PRINCIPAL_PERMISSIONS),
    ):
        assert {
            "appraisals.manage",
            "appraisals.review",
            "substitutions.approve",
            "leave.manage_policy",
        } <= set(held), role


def test_the_deputy_runs_the_day_but_signs_no_contract():
    """A vice-principal: reviews and covers, never the entitlements or the KYC."""
    held = set(VICE_PRINCIPAL_PERMISSIONS)
    assert {"appraisals.manage", "substitutions.approve", "leave.approve"} <= held
    assert not held & {
        "leave.manage_policy",
        "teachers.view_kyc",
        "teachers.audit_read",
        "hiring.hire",
    }
    assert "users.impersonate" not in held


def test_a_head_of_department_decides_inside_their_department_only():
    """Cover and review: yes. Signing cover off, finalising a season, writing the
    policy: no - those are the office's."""
    held = set(HOD_PERMISSIONS)
    assert {"substitutions.assign", "appraisals.review", "training.manage"} <= held
    assert not held & {
        "substitutions.approve",
        "appraisals.manage",
        "leave.manage_policy",
        "teachers.view_kyc",
    }


def test_a_teacher_gets_their_own_work_and_not_the_office_s():
    held = set(TEACHER_PERMISSIONS)
    assert {
        "teachers.read",
        "leave.create",
        "appraisals.self",
        "substitutions.read",
    } <= held
    assert not held & {
        "staff_attendance.read",
        "staff_attendance.mark",
        "teachers.view_workload",
        "leave.approve",
        "substitutions.assign",
        "appraisals.review",
        "appraisals.manage",
        "teachers.audit_read",
    }


def test_administration_holds_the_people_screen():
    held = set(ADMIN_PERMISSIONS)
    assert {"teachers.read", "staff_attendance.read", "appraisals.manage"} <= held
