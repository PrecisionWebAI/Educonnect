"""The role catalog - the rows the `role` table must always hold.

Role codenames are the machine keys the whole app speaks (`ROLE_PERMISSIONS_MAP`,
`RequirePermission`, the frontend route guards). Historically they existed **only**
as data written by migration `a2c5e8b1d4f7_rbac_roles`, so a database whose `role`
table was emptied - truncate, a restore, a fresh dump - came back with no roles at
all: `set_user_roles()` silently applied nothing and every user ended up with zero
permissions, with only a `[permissions] skipped unknown roles: [...]` line to
explain it.

Keeping the catalog here lets `seed_roles()` repair that on startup. The migration
keeps its own frozen copy (migrations must not import application code), and the
two are kept in sync by hand - add a role in both places.
"""

from typing import TypedDict


class RoleEntry(TypedDict):
    """One catalog row."""

    codename: str
    label: str
    description: str


#: `system_admin` + `owner` are the two platform roles; the rest are the school's
#: own. `class_teacher` / `subject_teacher` / `accountant` / `librarian` /
#: `transport` are listed because modules already exist for them - the doc calls
#: them "extensible later (INSERT only)", and a seed IS an insert.
ROLE_CATALOG: tuple[RoleEntry, ...] = (
    {
        "codename": "system_admin",
        "label": "System Admin",
        "description": (
            "Platform administrator: unrestricted access, manages roles and grants."
        ),
    },
    {
        "codename": "owner",
        "label": "Owner",
        "description": "Proprietor of the school; sees everything.",
    },
    {
        "codename": "principal",
        "label": "Principal",
        "description": "Heads academics; approves papers, fee cards and payroll.",
    },
    {
        "codename": "vice_principal",
        "label": "Vice Principal",
        "description": "Deputy to the principal: timetable, discipline, approvals.",
    },
    {
        "codename": "hod",
        "label": "Head of Department",
        "description": "Leads a department's teachers, syllabus and results.",
    },
    {
        "codename": "teacher",
        "label": "Teacher",
        "description": "Teaching staff: classroom, homework, marks, attendance.",
    },
    {
        "codename": "class_teacher",
        "label": "Class Teacher",
        "description": "Owns one section: attendance register, diary, report cards.",
    },
    {
        "codename": "subject_teacher",
        "label": "Subject Teacher",
        "description": "Teaches one subject across several classes.",
    },
    {
        "codename": "accountant",
        "label": "Accountant",
        "description": "Fees, receipts, payroll and collection reports.",
    },
    {
        "codename": "librarian",
        "label": "Librarian",
        "description": "Catalogue, issues and returns.",
    },
    {
        "codename": "transport",
        "label": "Transport Manager",
        "description": "Buses, routes and stop assignments.",
    },
    {
        "codename": "staff",
        "label": "Staff",
        "description": "Support staff: front office, lab, maintenance.",
    },
    {
        "codename": "student",
        "label": "Student",
        "description": "Learner login: own timetable, homework and fees.",
    },
    {
        "codename": "guardian",
        "label": "Parent / Guardian",
        "description": "Parent login: their children's records only.",
    },
)
