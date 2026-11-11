# Domains - one folder per group, one folder per screen

`app/domains/` is cut the same way the sidebar is, with one deliberate
difference: **a folder is a boundary, not a menu.**

- A **group** (top level) owns one set of tables, one set of permissions and the
  tests that cover them - it is what a reviewer signs off on.
- The **sidebar** groups pages for the user. It lives in
  `frontend/src/lib/constants/nav.ts` (`NAV_GROUPS`) and is free to put two
  groups behind one heading.

So the sidebar renders 6 headings while this folder has 9 groups: four map 1:1
to a heading (`Main`, `Academic`, `Services`, `Operations`), two headings cover
two groups each (`People & Finance` -> `people` + `finance`,
`Insights & Admin` -> `insights` + `admin`), and `auth` has no heading at all -
it is the door, not a room.

The rule, in one line:

> **Folder = table + permission owner. Nav title = what the user sees.**

<!-- groups: auth main academic people finance operations services insights admin -->

## Sidebar -> code

| Sidebar group | Screen (`/dashboard/...`) | Backend package | Mounted by | Permissions |
| --- | --- | --- | --- | --- |
| Main | `/dashboard` | `main/dashboard` | `main/api.py` | `dashboard.read` (+ `analytics`/`attendance`/`homework`/`leave`/`ptm`/`timetable` `.read`) |
| Main | `/dashboard/chat` | `main/chat` | `main/api.py` | `messages.read`, `messages.send` |
| - (header bell) | - | `main/notifications` | `main/api.py` | `messages.read` |
| - (overlay) | - | `main/copilot` | `main/api.py` | `ai_copilot.use` |
| Academic | `/dashboard/classroom` | `academic/classroom` + `academics` `students` `attendance` `homework` `timetable` `exams` | `academic/api.py` -> `classroom/api.py` | `classes.read`, `attendance.*`, `exams.*`, `marks.*` |
| People & Finance | `/dashboard/teachers` | `people/teachers`, `people/staff` | `people/api.py` | `teachers.read`, `hiring.read` |
| People & Finance | `/dashboard/payroll` | `finance/fees` (payroll views) + `operations/salary` | `finance/api.py`, `operations/api.py` | `payroll.read`, `payroll.manage`, `payroll.view_payslip` |
| People & Finance | `/dashboard/finance` | `finance/fees` | `finance/api.py` | `fees.read`, `fees.create` |
| Services | `/dashboard/library` | `services/library` | `services/api.py` | `library.read` |
| Services | `/dashboard/transport` | `services/transport` | `services/api.py` | `transport.read` |
| Services | `/dashboard/meetings` | `services/meetings` | `services/api.py` | `ptm.read` |
| Services | `/dashboard/tickets` | `services/tickets` | `services/api.py` | `messages.read` |
| Services | `/dashboard/leave` | `services/leave` | `services/api.py` | `leave.read` |
| Operations | `/dashboard/operations/admission` | `operations/admission` | `operations/api.py` | `admissions.read`, `admissions.manage` |
| Operations | `/dashboard/operations/staff-hiring` | `operations/staff_hiring` | `operations/api.py` | `hiring.read`, `hiring.manage` |
| Operations | `/dashboard/operations/fees-structure` | `operations/fees_structure` | `operations/api.py` | `fees.read`, `fees.manage_structure` |
| Operations | `/dashboard/operations/salary` | `operations/salary` | `operations/api.py` | `payroll.read`, `payroll.manage` |
| Insights & Admin | `/dashboard/reports` | `insights/reports` | `insights/api.py` | `reports.read`, `analytics.read` |
| Insights & Admin | `/dashboard/settings` | `admin/settings`, `admin/users`, `admin/platform` | `admin/api.py` | `settings.read`, `users.manage`, `roles.manage` |
| - (`/login`) | - | `auth` (+ `auth/schemas`) | `main.py`, prefix `/auth` | `permissions.manage`, `users.impersonate` |

## Why one heading can be two folders

### People & Finance -> `people/` + `finance/`

- **No shared table.** `people/` is built on `employee`, `teachersubject` and
  the roster; `finance/` on `feeinvoice`, `feetransaction`, `feehead`. Not one
  model is common, so merging would create
  `people_finance/teachers` and `people_finance/fees` - a compound name over
  the same two folders.
- **Three different permissions** sit under the one heading: `teachers.read`,
  `payroll.read`/`payroll.view_payslip`, `fees.read`. A folder that spans three
  permission domains cannot be granted or reviewed as a unit.
- **The heading is already split in practice:** the Payroll screen reads both
  `finance/fees` and `operations/salary`. UI grouping cannot map 1:1 to table
  ownership - and does not need to.
- Money changes (`fees`) and employment changes (`people`) should never land in
  the same diff.

### Insights & Admin -> `insights/` + `admin/`

- `insights/` is **read-only** (`reports.read`, `analytics.read`): it aggregates
  and writes nothing.
- `admin/` is where identity and the tenant itself live: `admin/settings` reads
  the school's own details, `admin/users` grants sign-in and roles
  (`users.manage`, `roles.manage`), and `admin/platform/` holds the `School` row
  and is the only package allowed to look across schools -
  `tests/test_structure.py` allow-lists it for `SKIP_SCHOOL` by name.
- Merging them would put read-only reporting in the same package as role
  grants and the cross-school console, which is the opposite of a boundary.

## Adding a screen

1. `app/domains/<group>/<feature>/` with `__init__.py` (nav path in the
   docstring: `"""Feature - Group > Screen: what it is."""`), `models.py`,
   `schemas.py`, `service.py`, `router.py`.
2. `models.py` -> add the dotted module to `app.core.schema.MODEL_MODULES`.
3. Mount the router in `<group>/api.py` - never in `__init__.py`, so importing a
   model module cannot build routes (that is what caused the old import cycles).
4. New permission -> `app/domains/auth/roles.py` and
   `frontend/src/lib/auth/rbac.ts`.
5. Sidebar entry -> `frontend/src/lib/constants/nav.ts`, then add the row to the
   table above.
6. `uv run python -m pytest tests -q` - the gates. The tree rules (folder =
   table + permission owner, models registered, every `router.py` mounted) live
   in `tests/test_structure.py`, the configuration rules in `tests/test_config.py`.
   There is no frozen URL baseline any more; a new screen adds routes on purpose.

## Keeping the table honest

`tests/test_structure.py` compares the `<!-- groups: ... -->` line above with the
folders on disk: a new group that is not documented, or a documented group whose
folder is gone, fails `make test`. The table itself is reviewed by hand - if a
screen moves, its row moves with it.
