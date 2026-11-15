# Classroom module — master plan & phase tracker (2026-11-14)

**Branch:** `feat/subtitution` · **Start commit:** `a1d00ce` · **Alembic head at start:**
`e9d5c3f7a2b4`

This file is the **single tracker** for the Classroom module. It used to hold the
Teachers plan; the owner cleared it, so it now carries the Classroom work instead — the
Teachers history is in git (`19ade8b`, `9c5c1cc`, `a1d00ce`). The spec asked for
`classroom_phases.md`; the owner asked for `phase.md` + a pointer `phase2.md`, so the
plan lives here and `phase2.md` only points back.

Target tab order (spec §2): **Students · Attendance · Course · Exams · Homework ·
Timetable · AI Papers**.

Legend: `[x]` done · `[ ]` open · `[~]` done but with a caveat written next to it.

## Non-negotiables (spec §1, restated because every phase is judged by them)

1. One source of truth: written once, displayed everywhere else.
2. Multi-tenancy: `school_id NOT NULL` + index, every read filtered by school.
3. Permission on the server, same codename in the route and the UI; teacher = own
   classes/subjects only.
4. Reads from the DB, writes reach the DB; empty = "no data", never an invented 0.
5. No hard-delete of people or records; status fields + audit logs.
6. A constraint violation is a 4xx (409), never a 500.
7. Money **and marks** are `numeric`, never `float`.
8. Every rule gets a test, including one refusal (wrong role / wrong school / wrong
   section).
9. Notifications use the `notification` table, never block the request, never roll
   the main action back.

---

## Phase 0 — audit & plan (read-only) — **DONE**

### 0.a Environment

| Item | Result |
| --- | --- |
| `import app.main` on the host | **FAILS** — `ModuleNotFoundError: langchain_core` (`exams/llm/base.py:29`) |
| Host Python | 3.15 (pip env) — has fastapi/sqlmodel/pytest, no langchain/qdrant/pypdf |
| Project target | `.python-version` 3.14 + `uv.lock`; `uv` **not** on PATH (only `python -m uv` 0.13.7) |
| `.venv` created with `uv sync` | installs OK, but `.venv\Scripts\python.exe` is **blocked by Windows Application Control** (`os error 4551`) — same for a venv on `C:` |
| Base uv Python 3.14 | policy blocks the compiled extensions (`sqlalchemy _processors_cy`, `_cache_key_cy`) |
| Host `pip install langchain-core` on 3.15 | fails: no `pyyaml` wheel for cp315, source build needs Cython |
| **Working path** | **Docker** (Desktop 29.8.2, WSL2 backend). The repo already ships the right image: `backend/Dockerfile`'s **`checks`** stage → `docker build --target checks -t eduverse-checks .` (used for every gate below) |
| `import app.main` in the container | **OK** — proven by `tests/test_structure.py::test_every_router_is_mounted`, which builds the app (it is one of the 438 passes) |
| Full suite in the container | **438 passed, 9 failed, 7 skipped** in 101s (details in 0.d) |

**What the owner must do for host-side work (one of):**
1. Ask IT to allow-list the repo folder and `%LOCALAPPDATA%\uv\python\**` in the App
   Control policy (Python exe + `*.pyd`), then `python -m uv sync` works on the host; **or**
2. install CPython 3.14 from python.org and use it (its files are not blocked); **or**
3. keep using Docker — the repo's own path, and what Phase 0 used:

```
cd backend
docker build --target checks -t eduverse-checks .
docker run --rm -v "<repo>/backend:/src" -w /src -e PYTHONPATH=/src \
  eduverse-checks python -m pytest tests -q
docker run --rm -v "<repo>/backend:/src" -w /src \
  eduverse-checks python -m ruff check .
```

A separate `educonnect-py314` image was built while investigating; it is **not**
needed (its `python -c "import app.main"` hung, while the repo image works) and can be
removed with `docker rmi educonnect-py314`.

### 0.b Spec §2/§3 vs the real code and schema (evidence, not names)

Legend: **DONE** · **PARTIAL** · **MISSING**

| Spec item | State | Evidence |
| --- | --- | --- |
| Students: add/edit/activate/deactivate reach the DB | **MISSING** | `useStudents.ts:104-123` only `setQueryData`; `createStudent()` (students.service.ts:29) never called; no `PATCH/PUT /students` route (`students/router.py`) |
| Students: server-side pagination + search | **MISSING** | `useStudents.ts:48` asks `/students?limit=100`, filters/pages in the browser |
| Students: enrollment is the class truth | **PARTIAL** | `enrollment` table exists (`students/models.py:152-186`, UNIQUE school+student+year), **0 rows**, nothing writes it; truth today is `student.classroom_id`; `current_class_id` exists but **no code ever assigns it** |
| Attendance: saved register preloads | **MISSING** | `getSectionAttendance()` defined (`attendance.service.ts:33`), **unused** |
| Attendance: unique (student,date,subject) + classroom-aware dedupe | **MISSING** | live `attendancerecord` (3952 rows) has only pkey + `ix_*classroom_id` + `ix_*school_id`; dedupe query is student+date+subject (`attendance/repository.py:47-56`) |
| Attendance: real weekly trend / attention list | **MISSING** | `useAttendance.ts:135-159` hardcodes `{Mon:92…Sat:93}`; alerts read only today's marks |
| Attendance: totals, %, threshold flag (75%) | **MISSING** | no such endpoint; no settings store |
| Attendance: holidays + Sundays excluded | **MISSING** | `holiday` table exists (UNIQUE school+on_date, 0 rows); no attendance code reads it |
| Attendance: guardian notification on absent | **MISSING** | no notification call in the attendance domain |
| Attendance: `leave_request_id` + approved leave shown / cancelled reverted | **MISSING** | column absent (audit); `leaverequest` has `student_id` but the register never reads it |
| Attendance: consecutive-absence alert (teacher+principal) | **MISSING** | absent |
| Course: `chapter` / `chapter_progress` | **MISSING** | both tables absent |
| Course: `subjectteacher` history (effective_from/to, year) | **MISSING** | live: classroom_id, subject_id, teacher_id only; UNIQUE(classroom,subject) |
| Course: `syllabusprogress` as derived summary | **PARTIAL** | columns exist (teacher_id, academic_year_id, planned_completion, chapters_total/done), 0 rows, still an independent writer-to-be |
| Course: endpoints + tab | **MISSING** | none |
| Exams: `exam` extended (class/classroom/year/scope/type/status/note/published_at/created_by) | **MISSING** | live `exam`: name, term, start_date, end_date, status(text), created_at; 0 rows |
| Exams: `exam_paper` + `exam_paper_chapter` | **MISSING** | absent |
| Exams: `examsubject` → `exam_paper` | **PARTIAL** | `examsubject` exists (exam_id, subject_id, `max_marks double precision`, 0 rows, UNIQUE exam+subject) |
| Exams: marks numeric + absent + exam_paper_id + UNIQUE(exam_paper,student) | **PARTIAL** | `marks` exists 0 rows: `marks_obtained double precision`, no `is_absent`, no paper link, UNIQUE(exam,student,subject) |
| Exams: `marks_audit` | **MISSING** | absent |
| Exams: `grade_scale` | **MISSING** | absent |
| Exams: rank computed + `rank_display` setting | **MISSING** | no rank code, no settings store |
| Exams: visibility (student/parent own published; teacher own class/subject; principal school) | **PARTIAL** | `GET /classroom/marks` is `marks.read` + school-wide only; no published concept, no student/parent scope |
| Homework: `submitted_at`, `is_late`, `graded_at`, `marks_awarded` | **MISSING** | live `homeworksubmission`: content_url, status, `teacher_feedback` only |
| Homework: feedback UI / grade | **MISSING** | submissions list read-only (`SubmissionsReview.tsx`) |
| Homework: diary written from UI + period link | **PARTIAL** | `classlog` has `timetableperiod_id` + both unique keys (live), **no** `subject_id`; `POST /homework/diary` exists, no UI calls it |
| Timetable: `bell_schedule` | **MISSING** | absent; 6 periods hardcoded in `TimetablePanel.tsx:35-42` |
| Timetable: class-slot unique key | **MISSING** | live has `uq_timetableperiod_teacher_slot` only |
| Timetable: clash → 409 | **MISSING** | `timetable/service.py:11-15` no try/except → IntegrityError = 500 |
| Timetable: period counts in teacher workload | **DONE** | `people/teachers/service.py:253` sums `timetableperiod`; `test_phase3_teachers_split.py:226` |
| Notifications: event/entity/dedupe/channel columns | **MISSING** | live `notification`: user_id, title, body, kind, read, created_at (0 rows) |
| Notifications: one service + dedupe + non-blocking | **MISSING** | one ad-hoc insert at `substitution/service.py:334` |
| Notifications: scheduler for the exam reminder | **MISSING** | only `lifespan` bootstrap (`main.py:20`) — no scheduler anywhere |
| School settings (threshold, consecutive days, rank_display, reminder time) | **MISSING** | no settings table (`school` has no such columns) |
| Tab labels Students…AI Papers | **MISSING** | today: Students, Attendance, Academics, Homework, Timetable, Exams & AI Papers (`SectionDetailPage.tsx:46-53`) |

### 0.c What the database really has (Supabase, Postgres 17.6, schema `public`, 81 tables)

Read-only audit via `_phase0_db_audit.py` (temp file, deleted after this phase).

| Table | Rows | Real keys that matter | Gap vs spec |
| --- | --- | --- | --- |
| `attendancerecord` | **3952** | pkey; `ix_…_classroom_id`; `ix_…_school_id`; `school_id` **NOT NULL** | no unique key at all |
| `attendanceauditlog` | 0 | pkey; `school_id` **nullable** | — |
| `marks` | 0 | UNIQUE (exam_id, student_id, subject_id); `marks_obtained double precision` | float, no absent, no paper link |
| `exam` | 0 | pkey; `ix_exam_school_id` | only name/term/dates/status |
| `examsubject` | 0 | UNIQUE (exam_id, subject_id); `max_marks double precision` | float |
| `subjectteacher` | 0 | UNIQUE (classroom_id, subject_id) | no history columns |
| `classlog` | 0 | UNIQUE (classroom_id, date, timetableperiod_id) **+** partial UNIQUE (classroom_id, date) WHERE period IS NULL | no `subject_id` |
| `timetableperiod` | 0 | UNIQUE (school_id, teacher_id, day_of_week, start_time) | no class-slot key |
| `syllabusprogress` | 0 | UNIQUE (classroom_id, subject_id) | summary only |
| `enrollment` | 0 | UNIQUE (school_id, student_id, academic_year_id) | never written |
| `student` | **917** | pkey + unique admission number per school | — |
| `holiday` | 0 | UNIQUE (school_id, on_date) | — |
| `academic_year` | 0 | UNIQUE (school_id, name) + partial unique "one current" | — |
| `notification` | 0 | pkey; `ix_notification_school_id` | no event/dedupe/channel |
| `homeworkassignment` / `homeworksubmission` | 0 / 0 | pkey + school index | no timing/grade columns |

**Duplicate scan — every new unique key is safe today** (0 duplicate groups in all 12
checks): attendance (school+student+date+subject **and** school+student+date), marks
(exam+student+subject), examsubject, subjectteacher, classlog (with and without
period), timetable (classroom slot + teacher slot), syllabusprogress, enrollment,
notification (user+title+kind).

So Phase 2/5/7 can add their unique keys without a data-cleaning migration; the
"clean duplicates first" step stays in the plan as a **guard**: the migration must run
the same group-by check and abort with a printed count if rows appear before it lands.

**Tables that do not exist yet:** `bell_schedule`, `chapter`, `chapter_progress`,
`exam_paper`, `exam_paper_chapter`, `marks_audit`, `grade_scale`, `school_setting`.

### 0.d Tests today

**Container run (`eduverse-checks`, Python 3.14, all runtime deps) — the numbers that
count:**

```
$ python -m pytest tests -q
438 passed, 9 failed, 7 skipped, 18 warnings in 101.40s
```

The 7 skips are the two legacy RBAC files, skipped **in this phase** (see below). The
9 failures are **pre-existing and outside the Classroom spec** — all in the AI-paper
builder, whose behaviour spec §2.6 says must not change:

| Test file | Failing | Cause (from `--tb=line`) |
| --- | --- | --- |
| `test_exams_generation.py` (2) | `test_paper_config_keeps_frontend_context_fields` | `assert 'science' == 'Science'` — the service normalises the subject to lower case, the test expects the original |
| | `test_generation_request_accepts_frontend_body` | `ValidationError` for `GenerationRequest` — the schema tightened after the test was written |
| `test_exams_question_unlock.py` (4) | all four | `SimpleNamespace` fixture has no `created_by` (`exams/service.py:1495`) — the service started needing the caller |
| `test_exams_source_index.py` (3) | all three | retrieval returns `[]` — no vectors in the test database (RAG state) |

They stay untouched here (spec 2.6). Question 4 in "Open questions" asks whether to fix
them in Phase 7/8 or leave them to the AI Papers task.

**Fixed in this phase (test-only):**

* `tests/test_authorization.py` and `tests/test_assignments.py` were written for the old
  single-role model (`RoleEnum.admin`, `can_manage_class(user, session, 1)`). Roles are
  data now (`role` + `user_role` + `rolepermission`), so both files are marked
  `pytest.mark.skip` with a reason that points at `tests/test_permission_matrix.py`,
  which asserts the same matrix against the real model (including the permissions a
  teacher must **not** hold). Nothing is lost; nothing is silently hidden.

**bcrypt pin:** no failure to fix. `pyproject.toml` pins `bcrypt<4.1.0`; the checks
image installs `bcrypt==4.0.1` and `tests/test_lifecycle.py` (6 tests) passes there. The
earlier host failure was a global 5.0.0 install, not the project.

**Host (Python 3.15)** — kept only as evidence of the gap: 6 files cannot be collected
(`langchain_core`), so anything reported from the host is incomplete.

**Lint baseline (important for later phases):** `ruff check .` is **not** green today —
`--statistics` reports **228 errors**: 99 `I001` (import order), 41 `F821`
(undefined-name), 39 `RUF100` (unused noqa), 18 `UP037`, 15 `F401`, 7 `RUF012`, 3
`C416`, 3 `RUF059`, 1 `E712`, 1 `RUF015`, 1 invalid-syntax. So the gate for Phases 1–10
is: **no new ruff errors on the files a phase touches** (and `ruff format --check` on
them), with the repo-wide cleanup in Phase 10.

* **No test file exists for students write, attendance, marks, homework, timetable or
  the exam tab** — Phase 1 onwards adds them (`tests/test_classroom_*`).

### 0.e Decisions taken in Phase 0 (recorded so later phases do not re-litigate)

1. **Tracker file:** `phase.md` (this file) + `phase2.md` pointer, per the owner's
   instruction; the spec's `classroom_phases.md` name is not used (one source of truth).
2. **Environment:** Docker image is the supported local/CI path; host venv is blocked by
   machine policy (details in 0.a).
3. **`school_id` nullability:** several tables still declare `school_id` nullable in the
   DB (models say NOT NULL). Each phase tightens **only the tables it touches**
   (backfill → `NOT NULL` → index), because a global sweep is a separate migration and
   the audit shows no NULLs in `attendancerecord`/`student`. Recorded per phase.
4. **`examsubject` / `syllabusprogress` are dropped** (owner decision, 15 Nov 2026; both
   hold 0 rows). Nothing new is written against them from now on, their models and every
   reference leave the codebase, and each table is dropped in the migration of the phase
   that lands its replacement - `syllabusprogress` in **Phase 5**, `examsubject` in
   **Phase 7**. Each of those migrations counts the rows first and **aborts printing the
   count** if it is not 0, and each downgrade recreates the empty table.
5. **Marks are `numeric`:** the two float columns (`marks.marks_obtained`,
   `examsubject.max_marks`) are converted in Phase 7 with `numeric(6,2)`; the API
   keeps serving `float` for JSON, the DB stops being float.
6. **`student.current_class_id`** is never written by any code; Phase 1 makes
   `classroom_id` the one writer and treats enrollment as the yearly history (no second
   source of truth).

---

## Phase 0 — Result (2026-11-14)

**Summary.** Environment diagnosed and a working gate path established through the
repo's own `eduverse-checks` image (host Python is blocked by machine policy — exact Ask
in 0.a). Every spec §2/§3 item was checked against the live database and the code; the
result is the matrix in 0.b, the schema/duplicate facts in 0.c and the test baseline in
0.d. No application code and **no schema** was changed in this phase.

**Files touched**

* `backend/phase.md` (this file) and `backend/phase2.md` (pointer) — new.
* `tests/test_authorization.py`, `tests/test_assignments.py` — module-level `skip` with
  the reason (legacy RBAC; superseded by `test_permission_matrix.py`).
* Temporary, now deleted: `backend/_phase0_db_audit.py` (read-only audit script).

**Tables touched:** none. **Migrations:** none.

**Tests:** 438 passed / 9 failed (pre-existing AI-paper) / 7 skipped (the retired RBAC
files) in the container; app import proven by `test_structure`. `ruff check .` baseline
= 228 errors (recorded above; later phases must not add to it).

**Open questions:** see the four at the end of this file (none blocking Phase 1).

**Next phase (1 — Students tab, real writes):** `PATCH /students/{id}`, one
`place_student` writer for `classroom_id` + current-year `enrollment`, real
create/edit/deactivate wiring in `useStudents`, server-side search/pagination, and
`tests/test_classroom_students.py` (create → edit → deactivate → reactivate + two
refusals). **Awaiting the owner's "next phase".**

---

# Plan — phases 1 to 10


Rules for every phase: migrations are additive, have a working downgrade, and are
proven `up → down → up` on a copy; every write path ends with a test (happy + refusal);
the phase ends with a dated result block in this file and a short report.

---

## Phase 1 — Students tab, real writes

**a. Backend**
- [x] `PATCH /students/{id}` (`students.update`): name fields and the class-section
      move. 404 for another school, 403 for a role without the codename.
      *Note:* `status` is **not** in the body on purpose — leaving and returning are the
      lifecycle routes, which stamp the dates the directory reads.
- [x] One service function `placement.place_student(session, student, classroom_id)`
      writes `student.classroom_id` **and** upserts the current-year `enrollment` row —
      the single writer for "which class is this child in".
      *Note:* `enrollment.academic_year_id` is NOT NULL and no school had an
      `academic_year` row, so `current_academic_year()` opens the session (June→April)
      on first placement — idempotent, one row per school, documented in the module.
- [x] `POST /students` keeps working but goes through `place_student`.
- [x] Deactivate / reactivate write `enrollment.status` (`left` / `active`) and its
      `left_on` — through `placement.set_enrollment_status`, so the roll and the
      session's history cannot drift.
- [x] `GET /students` gains `q` (name / admission number / guardian), `class_id`,
      `classroom_id`, `status`, and `limit`/`offset` with `X-Total-Count`; `limit=None`
      still means "all of it" (no silent 100). The office's search, filters and paging
      all run in SQL now.
- [x] *Added while implementing (rule 3):* a **parent or a student** used to receive the
      whole roll from the API (the browser filtered it — not a boundary). The list and
      the single read are now narrowed in SQL by `visible_student_ids` (own child /
      own row), following the rule `may_read_student_dues` already applied to fees.

**b. Frontend**
- [x] `students.service.updateStudent()`; `useStudents` → real `createStudent`,
      `updateStudent`, `deactivate/reactivate`; every `setQueryData` write is gone and
      the hook invalidates `["students"]` after each success. Errors are shown from the
      API (409/403) instead of a success toast.
- [x] `StudentsPanel` edits through `PATCH`, and the status button is
      "Mark as left" / "Bring back" (the lifecycle routes), not a cache flip.
- [x] *Added while implementing:* creating a child also links the guardian the form
      collects (`POST /students/{id}/guardians`), so the directory does not silently drop
      the parent's name. The school-wide tiles now read **server** counts
      (Total / Active / Inactive) instead of counting the loaded page.

**c. Tests** (`tests/test_classroom_students.py` — 8 tests)
- [x] create → edit → deactivate → reactivate, each read back from the database
      (fields, `deactivated_at`, `left_on`, the read's `status`).
- [x] refusal: a teacher (holds `students.read` only) is `403` at the route guard; another
      school's id is `404` for read, edit **and** deactivate; a parent reading a
      classmate is `404`.
- [x] enrollment: one row per student per session (the session row is opened once, not
      per student) and a section move **updates** that row.
- [x] search/scope/count: name, admission number and guardian name; `classroom_id`,
      `class_id`, `status`; a page (`skip`/`limit`) and the matching count.
- [x] family scope: a guardian sees only their linked child, a student only their own
      row, the office the whole school.

### Phase 1 - Result

**What landed.** The Students tab now writes to the database and reads the directory
from it. Create, edit, leave and return all go through one placement writer, the list
is searched, filtered and paged in SQL, and a family's read is narrowed on the server.
No cache flip is left anywhere in the flow.

*Backend*
- `students/placement.py` (new) - `place_student`, `set_enrollment_status`,
  `current_academic_year`: the **only** writer of `student.classroom_id` + the
  current-session `enrollment` row; opens the session (June-April) on first use.
- `students/repository.py` - `get_students`/`count_students` with `q` (name, admission
  number, guardian name), `classroom_id`, `class_id`, `status`, `skip`/`limit`, plus
  `visible_student` / `visible_student_ids`.
- `students/service.py` - `get_student(user=...)`, `create_student`,
  `update_student`, `get_students`, `count_students`; guardian rows written on create.
- `students/schemas.py` - `StudentUpdate` (name fields + `classroom_id`; status is the
  lifecycle's, not the form's).
- `students/router.py` - `PATCH /students/{id}` (`students.update`), list filters +
  `X-Total-Count`, `GET /students/{id}` scoped.
- `students/lifecycle.py` - deactivate/reactivate also stamp the enrollment row.

*Frontend*
- `lib/api/client.ts` - `getWithTotal` (reads `X-Total-Count` alongside the body).
- `services/students.service.ts` - `getStudentsPage`, `updateStudent`,
  `deactivateStudent`, `reactivateStudent`.
- `classroom/students/useStudents.ts` - real mutations; invalidates `["students"]`;
  API errors surface instead of a success toast.
- `classroom/students/StudentsPanel.tsx` - create (with guardian), edit via `PATCH`,
  "Mark as left" / "Bring back"; tiles read server counts (Total / Active / Inactive).
- `classroom/students/StudentsPage.tsx`, `StudentTable.tsx` - server paging + search
  box wired to the query; `types/index.ts` - `StudentPageQuery`, `StudentLifecycleResult`.

**Gates**
- `tests/test_classroom_students.py` (new, 8 tests): create -> edit -> leave -> return
  read back from the DB; section move updates the same enrollment row; search by name /
  admission number / guardian; `classroom_id`, `class_id`, `status` filters; page +
  count; teacher `403`; another school `404` (read, edit, deactivate); parent/student
  scope.
- Full suite in `eduverse-checks`: **446 passed, 9 failed, 7 skipped** - the 9 are the
  pre-existing AI-Papers failures (Phase 0 baseline: 438 passed, same 9), so Phase 1
  adds 8 passing tests and no new failures.
- `ruff check .`: **209** errors (Phase 0 baseline 228 - the students package is now
  clean); `ruff format --check` clean on every touched file.
- `npx tsc --noEmit`: clean. `npx eslint` on the changed files: clean (the single
  remaining error is `GuardianCard.tsx`'s `set-state-in-effect`, a file this phase did
  not touch - noted for Phase 10).

**Deviations / decisions**
- No migration: `enrollment` and `deactivated_at` already existed; Phase 1 needed none.
- `status` is not editable through `PATCH`: leaving and returning stamp `left_on`,
  which the directory reads; letting the form set it silently would fork the truth.
- `limit` keeps its old default of "all rows" when omitted, so existing callers are
  unchanged; the tab now always sends `skip`/`limit` and reads the count.
- The academic-year row is auto-opened from the calendar because
  `enrollment.academic_year_id` is NOT NULL and no school had one - documented in
  `placement.py`; the owner may prefer to seed it instead.
- Guardian scope follows `student_guardian_relationship` (siblings share it), the same
  rule `finance/fees` already used for one balance.

## Phase 2 — Attendance schema + backend

**a. Schema (migration, `b7c1d4e9a3f2`)**
- [x] Guard: group-by duplicate scan on **both** keys; abort printing the count if any
      group > 1 (0 today - it printed "0 duplicate groups" and carried on).
- [x] `attendancerecord.leave_request_id` (nullable FK `leaverequest.id`) + index.
- [x] UNIQUE `(school_id, student_id, date, subject_id)` — plus a partial unique
      `(school_id, student_id, date) WHERE subject_id IS NULL` so a day-level row is
      also single.
- [x] `school_setting` (key/value per school: `attendance.absence_threshold=75`,
      `attendance.consecutive_days=3`, `exam.reminder_time`, `exam.rank_display`,
      `exam.grade_scale`) — new table, unique `(school_id, key)`; read through
      `admin/settings/values.py` (`get_int` falls back on a non-number, never raises).
- [x] `school_id` NOT NULL on `attendancerecord` (already) and on
      `attendanceauditlog` (backfilled from the parent row, then tightened).

**b. Backend behaviour**
- [x] Save = upsert keyed by (school, student, date, subject) — one writer,
      `attendance/register.py::save_register`; `409` on the lost race; an audit row on
      every status/remarks change, naming the user.
- [x] `GET /attendance/section/{id}?date=` returns the saved register (the endpoint the
      UI forgot to call): the **whole roll**, `unmarked` included, plus
      `closed_reason`, the counts and the day's percentage.
- [x] `GET /attendance/section/{id}/summary?from=&to=` → per student present/absent/
      leave days + %, `below_threshold` flag from settings.
- [x] `GET /attendance/section/{id}/trend?days=7` → real per-day present % (holidays and
      Sundays skipped, `holiday` table read; an unmarked day is `null`, not 0).
- [x] `GET /attendance/section/{id}/attention` → below threshold or ≥ N consecutive
      absences (both limits from `school_setting`).
- [x] Save refuses a holiday/Sunday date with `409` naming the holiday.
- [x] Leave wiring: on read, an approved `leaverequest` day shows as `leave` (derived,
      never stored twice); the register rows link `leave_request_id`, which a cancel
      keeps as the trace.

**c. Tests** (`tests/test_classroom_attendance.py` — 8 tests)
- [x] re-save updates (no duplicate row, audit written); the **keys** refuse a second
      row, day-level and per-subject (a real `IntegrityError`, not just the service).
- [x] totals/percentage correct; threshold flag (and it follows the setting);
      Sunday/holiday refused.
- [x] approved leave shows as leave; cancelled leave reverts to the teacher's mark.
- [x] refusal: a teacher cannot mark another section (403, route **and** guard).

### Phase 2 - Result

**What landed.** The register is one row per child per day (per subject), it can be
saved repeatedly without doubling, a closed day is refused by name, and the four reads
the Attendance screen needs (register, summary, trend, attention) now exist and are
answered from `attendancerecord` + `holiday` + `leaverequest` + `school_setting` —
nothing is computed from fixtures or typed twice.

*Schema (migration `b7c1d4e9a3f2`, proven `up → down → up` on Postgres 17)*
- `attendancerecord.leave_request_id` (nullable FK `leaverequest.id`) + index.
- `UNIQUE(school_id, student_id, date, subject_id)` and the partial unique
  `(school_id, student_id, date) WHERE subject_id IS NULL` (a day-level mark is single).
- `school_setting` (new) — `UNIQUE(school_id, key)`, read through
  `admin/settings/values.py`; `attendance.absence_threshold=75`,
  `attendance.consecutive_days=3` are the defaults.
- `attendanceauditlog.school_id` backfilled from the parent row, then `NOT NULL`.
- Guard first: the migration group-by-scans **both** keys and raises (printing the
  count) when any group > 1 — proven on a scratch table holding one duplicate pair:
  `RuntimeError: … 1 student/day/subject group(s) and 1 day-level group(s) hold more
  than one row. Nothing was changed`, `GUARD_EXIT=1`, version still `e9d5c3f7a2b4`.

*Backend*
- `attendance/register.py` (new) — `save_register` (upsert + audit + closed-day refusal
  + leave link), `register`, `section_summary`, `section_trend`, `section_attention`,
  `closed_reason`. One writer for a mark, one calculator for every number.
- `attendance/repository.py` — range/detail reads: `active_students`, `records_on`,
  `records_between`, `find_record`, `approved_leave_on`, `approved_leaves_between`,
  `holiday_on`, `holidays_between`, `audit_rows` (the old second writer
  `create_or_update_attendance` is gone).
- `attendance/schemas.py` — `AttendanceRowWrite` (the body is typed now),
  `RegisterRead`/`RegisterRowRead`/`RegisterCountsRead`, `SectionSummaryRead`,
  `StudentAttendanceSummaryRead`, `SectionTrendRead`, `AttentionRowRead`.
- `attendance/router.py` — `GET /attendance/section/{id}?date=`,
  `…/summary?from=&to=`, `…/trend?days=`, `…/attention`; `POST /attendance/bulk` now
  saves through `save_register`.
- `admin/settings/models.py` + `values.py` — `SchoolSetting`, `get_value`/`get_int`/
  `set_value` (a stored non-number falls back instead of raising).

**Rules the numbers follow**
- `unmarked` is a state: the register lists the whole roll and never invents a status.
- Attendance % = credit / marked, credit `present=1, late=1, half_day=0.5,
  absent=0`; **approved leave is excluded** from the denominator (a leave is not
  something a child makes up) and `None` means "no data", never `0%`.
- Sunday and holidays are skipped by the trend and the consecutive-absence run, and a
  day with no rows stops the run.
- Leave is derived on read; the stored mark is never overwritten, and the row keeps
  `leave_request_id` as the trace after a cancel.

**Gates**
- `tests/test_classroom_attendance.py` (new, 8 tests): re-save updates + audits; the
  keys refuse a duplicate (`IntegrityError`, day-level **and** per-subject); Sunday and
  a named holiday are `409` and nothing is written; summary counts/percentage and the
  threshold (including when the school changes the setting); the trend skips Sunday +
  holiday and returns `null` for an unmarked day; leave derived → revert; attention
  flags a 3-day run; a teacher cannot mark another section.
- Full suite in `eduverse-checks`: **454 passed, 9 failed, 7 skipped** — the 9 are the
  pre-existing AI-Papers failures (Phase 1: 446 passed), so Phase 2 adds 8 passing tests
  and no new failures.
- `ruff check` on every touched path: clean; `ruff format --check`: clean. Repo total
  210 (Phase 1: 209) — the one addition is a pre-existing `F821` in
  `app/domains/main/dashboard/service.py` (untouched by this phase, `git diff` empty for
  it) that the earlier count had not picked up.
- Migration: `up → down → up` on Postgres 17 with the state printed at each step
  (before: no column/keys/table; after up: all present, audit `NOT NULL`, 0 NULLs;
  after down: back to the pre-migration shape with the data untouched; after up again:
  identical to the first up).

**Known limitation (recorded, not fixed here)**
- `alembic upgrade head` on a **completely empty** database fails at
  `f9e0f1a2b3c4_school_scoped_class_catalog` (`column c.name does not exist` on
  `classroom_legacy`). The deployed database was built incrementally, so the chain has
  never been run from zero; that hole is older than this module. Phase 2's proof
  therefore starts from the pre-migration shape stamped at `e9d5c3f7a2b4`. Repairing
  the historical chain belongs in Phase 10 (final verification).

## Phase 3 — Notifications foundation

**a. Schema (migration, `c8e2f5a1d7b3`)**
- [x] `notification` gains `event_type` (+ index), `entity_type`, `entity_id`,
      `dedupe_key` (nullable), `channel` (default `in_app` — existing rows backfilled
      by the server default).
- [x] UNIQUE `(user_id, dedupe_key)` (**partial**: only where `dedupe_key IS NOT NULL`) —
      one message per event per person; rows that name no key may legitimately repeat.
- [x] Index `(school_id, user_id, created_at)` for the bell.
- [x] Guard: the duplicate scan runs **after** the columns exist and before the index —
      the first attempt scanned a column that did not exist yet and the proof caught it.

**b. One service** (`main/notifications/events.py`)
- [x] `notify(session, event=…, recipients=…, title=…, body=…, dedupe_key=…)` plus
      `audience(session, roles={guardians|student|class_teacher|principals}, …)`:
      recipients resolved through `student_guardian_relationship` (guardians), the
      student's own `user_id`, `classroom.class_teacher_id` → `employee.user_id`, and
      the `principal` / `vice_principal` role rows.
- [x] Never raises into the caller: rows are written inside a savepoint, every failure
      is logged and reported as `0` (rule 9); `commit=False` keeps a caller's
      transaction intact.
- [x] Existing ad-hoc insert in `substitution/service.py` moved onto it
      (`substitution:{assignment}:assigned|withdrawn`), and no other module builds a
      `Notification` any more — a test asserts that.

**c. Scheduler**
- [x] `app/core/scheduler.py`: one daemon thread, 60-second tick, `register_job` (by
      name, idempotent), `run_once()` for tests, start/stop in `lifespan`. Documented
      here and in the README ("Background jobs"). No new dependency; the exam reminder
      (Phase 7) is its first job.

**d. First events**
- [x] `attendance.absent` → guardians, dedupe `attendance:{student}:{date}:absent`,
      emitted **after** the register commit.
- [x] `attendance.consecutive` → class teacher + principals, dedupe
      `consecutive:{student}:{date}`, when the run reaches
      `attendance.consecutive_days` (settings).

**e. Tests** (`tests/test_classroom_notifications.py` — 6 tests)
- [x] guardian gets exactly one message; re-save sends none; an unrelated parent gets
      nothing; a failing notification does not fail the attendance save.
- [x] a run of absences reaches the class teacher and the head, once for that day.
- [x] only one module constructs a `Notification`; the scheduler runs a job and
      survives one that raises.

### Phase 3 - Result

**What landed.** One writer for every message, a reason stored on each row, and a
database-level "once per event per person". Attendance now tells the family about an
absence and the office about a run of them; substitution keeps telling the person who
has to walk into the room, through the same service. The scheduler exists and is empty,
which is the honest state until Phase 7 registers the exam reminder.

*Schema (migration `c8e2f5a1d7b3`, proven `up → down → up` on Postgres 17)*
- `notification.event_type` (+ index), `entity_type`, `entity_id`, `dedupe_key`,
  `channel` (default `in_app`).
- partial unique `(user_id, dedupe_key) WHERE dedupe_key IS NOT NULL`;
  `(school_id, user_id, created_at)`.
- Proof: before = 8 columns, no new indexes, 1 old row → up = +5 columns, 3 indexes,
  the old row showing `channel=in_app` → down = exactly the before shape, row kept →
  up again = identical to the first up.

*Backend*
- `main/notifications/events.py` (new) — `notify`, `audience`,
  `guardian_user_ids` / `student_user_id` / `class_teacher_user_id` /
  `principal_user_ids`, `kind_for`; event + audience constants.
- `main/notifications/models.py` — the new columns and the two indexes.
- `attendance/notify.py` (new) — `announce(...)`: guardians about an absence, class
  teacher + principals about a run; called by `register.save_register` **after** the
  commit.
- `core/scheduler.py` (new) + `main.py` lifespan start/stop.
- `people/teachers/substitution/service.py` — `_notify` now calls `events.notify`
  (`commit=False`, dedupe per assignment + action).

**Decisions worth knowing**
- A recipient list is **always** derived from the data; no caller passes names.
- `dedupe_key` is per event *and per day* (`…:2026-11-16:absent`), so tomorrow's absence
  is a new message while a re-save today is not.
- `notify` commits by default (attendance has already committed its own work) but
  accepts `commit=False` where the message must live inside the caller's transaction.
- `kind` ("Attendance" / "Substitution") is derived from the event, so the bell's tabs
  do not need a second list to keep in step.

**Gates**
- `tests/test_classroom_notifications.py` (new, 6 tests) — 38 passed together with the
  attendance and substitution suites.
- Full suite: **460 passed, 9 failed, 7 skipped** — the same 9 pre-existing AI-Papers
  failures (Phase 2: 454 passed), so Phase 3 adds 6 tests and no regressions.
- `ruff check` / `ruff format --check` on every touched path: clean.


## Phase 4 — Attendance UI + leave wiring

**a. Register**
- [x] Opening a date calls `GET /attendance/section/{id}?date=` and pre-fills the
      grid (`services/attendance.service.ts::getSectionRegister` is the real path now).
      A saved day comes back as the chips already pressed, and only the rows the user
      **changes** are sent on Save - the old flow sent every row with `?? "Present"`,
      which marked the untouched children present.
- [x] Save disabled on holidays/Sundays with the reason shown
      (`closed_reason` → "School closed — Diwali break"); the date picker greys those
      days out (`GET /attendance/closed-days`, `DatePicker.isClosedDay`).

**b. Widgets**
- [x] Summary strip and trend chart read the new endpoints (no hardcoded numbers):
      the strip is `register.counts`, the chart is `/trend` (`null` days are skipped, not
      drawn as 0%); attention list = `/attention` (below threshold / consecutive
      absences), each row deep-links to `/dashboard/students?student=<id>` and the
      directory opens that child's profile.
- [x] Per-student totals panel (week / 14 days / month) with present/absent/leave/%
      and the threshold chip, from `/summary` - the school's own `threshold` and
      `below_threshold` decide the colour, and "no data" prints `—`, not `0%`.

**c. Leave wiring in the UI**
- [x] Register shows `leave` rows with the request id and an "approved in Leave &
      Applications" hint; no way to create leave here (the row has no chips, and
      "mark all present" never invents a leave).

**d. Tests**
- [x] approve leave → register shows leave; cancel → reverts: the backend covers it
      (Phase 2). Here the **API contract** the UI reads is pinned:
      `check_the_payload_is_what_the_screen_reads` asserts every field of the register,
      summary, trend and attention payloads, and
      `check_closed_days_lists_sundays_and_holidays` covers the calendar.
- [x] view-logic tests (`frontend/src/lib/attendance/view.test.ts`, 5 tests, run by
      Node's built-in runner): preload (a leave/half-day/unmarked row is **not**
      re-sent), holiday state, threshold chip, trend bars. *No component-test stack
      exists in this repository* (no vitest/jest, no `test` script), so the rules are
      tested as pure functions instead of adding a whole toolchain the owner never
      approved - recorded as a deviation below.

### Phase 4 - Result

**What landed.** The Attendance screen draws what the server holds. Opening a date
pre-fills the register, a closed day cannot be picked or saved and says why, the three
widgets are the section's real numbers, a leave row is shown as a leave with its
request, and Save writes only the rows the user touched.

*Backend (no migration)*
- `register.closed_days(...)` + `GET /attendance/closed-days?from=&to=` (+ guard: a
  range wider than a year is `422`), so the calendar and the toolbar explain a closed
  day with the same string.
- Two new tests: the calendar, and the **payload contract** the UI is built on.

*Frontend*
- `services/attendance.service.ts` - `getSectionRegister`, `getSectionSummary`,
  `getSectionTrend`, `getSectionAttention`, `getClosedDays` (all through `toCamel`).
- `lib/attendance/view.ts` (new, pure) + `view.test.ts` - preload, closed-day lookup,
  threshold tone, trend bars, weekday labels.
- `useAttendance.ts` (rewritten) - register + calendar + the three widget reads; the
  room is resolved from the class catalogue when the page does not pin it, so the
  school-wide page writes to a real class-section instead of only the cache; the draft
  is keyed by (room, day) so changing either re-reads the server (no reset effect).
- `MarkAttendanceTab.tsx` - rows from the register, leave rows without chips + hint,
  disabled on a closed day.
- `AttendanceWidgets.tsx` - `SummaryStrip` (server counts), `WeeklyTrendCard` (points),
  `TotalsPanel` + `PercentChip` (threshold chip, `—` for no data).
- `AttentionList.tsx` - real flags with a deep link; `StudentsPage.tsx` honours
  `?student=<id>` by opening that child's profile (`getStudent`, fetched by id).
- `AttendancePanel.tsx`, `AttendancePage.tsx` - wired end to end; `date-picker.tsx`
  gains `isClosedDay` (struck-through + unselectable).

**Deviations / decisions**
- **No component test**: the repo has no frontend test runner. Rather than add vitest +
  jsdom + testing-library (dependencies the owner never approved), the rules the plan
  wanted tested live in `lib/attendance/view.ts` and are covered by
  `node --test` (Node 24 strips the types; zero new dependencies). `tsconfig` gained
  `allowImportingTsExtensions` for that import only.
- `leave` is **never** pre-loaded into the editable chips: re-sending it would store a
  derived status and break the "cancel a leave → the mark comes back" rule.
- Attendance % shown in the toolbar is the server's `percent` (`null` when nothing is
  marked) - the browser never divides anything itself.
- The school-wide page now needs a class-section to mark: the pickers come from the
  class catalogue and the first section is selected automatically.

**Gates**
- Backend: `tests/test_classroom_attendance.py` **10 passed**; full suite **462 passed,
  9 failed, 7 skipped** (the same 9 pre-existing AI-Papers failures; Phase 3 was 460).
- `ruff check` + `ruff format --check` on the touched backend paths: clean; repo total
  **210**, the same as Phase 3 (no new lint error; the one remaining pre-existing
  `F821` is in `dashboard/service.py`, untouched).
- Frontend: `npx tsc --noEmit` clean; `npx eslint` clean on every changed path;
  `node --test src/lib/attendance/view.test.ts` **5 passed**; `prettier --write` applied.


## Phase 5 — Course schema + backend

**a. Schema (migration `d3f1a8c5e2b7`)**
- [x] `chapter (school_id, class_id, subject_id, academic_year_id, sequence, name,
      planned_date)` — unique `(school_id, class_id, subject_id, academic_year_id,
      sequence)`.
- [x] `chapter_progress (school_id, chapter_id, classroom_id, status, completed_on,
      completed_by_employee_id)` — unique `(chapter_id, classroom_id)`.
- [x] `subjectteacher` gains `academic_year_id`, `effective_from` (NOT NULL, default
      today) and `effective_to`; the old unique `(classroom_id, subject_id)` became
      `(classroom_id, subject_id, effective_from)` — history kept, not overwritten.
- [x] **`syllabusprogress` is dropped in this migration** (owner decision). Order:
      count the rows → `raise` printing the count if not 0 → remove the model and every
      reference → `op.drop_table` (it printed `[syllabusprogress] 0 row(s)` and dropped).
      The downgrade **recreates the empty table** with its original columns, indexes and
      unique key.
- [x] **Course completion has one source:** `course/completion.py` counts
      `chapter_progress` for every caller (Course tab, Classroom card, Teachers score);
      nothing stores a "chapters done" counter.

**b. Backend**
- [x] `GET /classroom/sections/{id}/course` → per subject: current teacher, previous
      teachers (with dates), chapter list (number, name, planned date, status,
      completed on/by), per-teacher share of completed chapters, next chapter,
      ahead/behind count.
- [x] `PATCH /course/chapters/{chapter_id}/progress` (`classes.read` + "this teacher
      holds this class+subject now" or the office's `classes.update`) → status stepper;
      sets `completed_on` and `completed_by_employee_id` on Completed, clears both when
      the chapter leaves Completed.
- [x] Teacher change = new `subjectteacher` row with `effective_from`; nothing is
      overwritten, so the bar keeps the old shares.
- [x] The Teachers performance component reads `completion.by_teacher` - the same
      calculation, one number.

**c. Tests** (`tests/test_classroom_course.py` — 5 tests)
- [x] teacher change keeps history; share per teacher correct (2/10 and 0/10, then 2/10
      and 1/10 after the new teacher ticks one); the section stays one number (3/10).
- [x] refusal: another teacher (`403`, and the teacher who handed the subject over too);
      another school's section and chapter are `404`; unticking clears the credit.

### Phase 5 - Result

**What landed.** The Course tab has a real backend: a chapter plan per (class, subject,
session), one progress row per chapter per class-section, a teacher timeline instead of a
pointer, and **one** completion number shared by the Course tab, the Classroom card and
the Teachers performance score. `syllabusprogress` is gone, exactly as the owner
decided - dropped in this migration with a row-count guard and an empty recreation on
downgrade.

*Schema (migration `d3f1a8c5e2b7`, proven `up → down → up` on Postgres 17)*
- `chapter` (plan) + `chapterprogress` (this section's answer), both with their unique
  keys and indexes.
- `subjectteacher` + `academic_year_id`, `effective_from`, `effective_to`; key swapped to
  `(classroom_id, subject_id, effective_from)`.
- `syllabusprogress` dropped **after** printing `0 row(s)`; both the up and the down
  print what they did.
- Proof: before = old shape (1 teacher row, old key, mirror present) → up = plan tables
  in, mirror **gone**, teacher row kept with `effective_from=2026-11-15` → down = mirror
  **recreated empty**, plan tables gone, old key back → up again = identical.
- Guard: with one row in `syllabusprogress` the migration stops:
  `RuntimeError: [syllabusprogress] refusing to drop it: 1 row(s) are still in the
  table. Nothing was changed`, exit 1, version unchanged, nothing dropped.

*Backend*
- `course/completion.py` (new) — `by_section`, `for_section`, `for_subject`,
  `for_teacher` (`by_teacher`), `planned_subjects`, `current_year` (a read, never
  creating the session).
- `course/service.py` (new) — `section_course`, `tick_chapter`, `_may_tick`, the
  teacher timeline and the per-teacher share.
- `course/schemas.py`, `course/router.py` (new) — mounted at `/classroom` and `/course`.
- `academics/models.py` — `Chapter`, `ChapterProgress`, `CHAPTER_*` words; `SubjectTeacher`
  history; `SyllabusProgress` deleted.
- `academic/classroom/repository.py` — the card's `get_syllabus_percent` /
  `get_syllabus_per_section` now read `completion` (no counters).
- `people/teachers/appraisal/performance.py` — the course component reads
  `completion.by_teacher`.
- `tests/test_phase2_schema.py` — the old `SyllabusProgress` assertion replaced by
  `chapter` / `chapterprogress` (and it asserts no counter columns exist).

**Decisions worth knowing**
- `chapter` hangs off the **class** (Class 9 reads one book), `chapterprogress` off the
  **section** — so 9-A and 9-B can be at different chapters with one plan.
- `completed_by_employee_id` is the person who ticked it, so a teacher change does not
  move finished work to the new name; clearing a tick clears both date and name.
- The office right for a tick is `classes.update` (existing codename); a teacher passes
  through owning the subject **now**. No new permission was invented.
- `effective_from` is NOT NULL with a `CURRENT_DATE` default, which is what let the
  migration keep the one existing assignment.

**Gates**
- `tests/test_classroom_course.py` (new, 5 tests): **5 passed** (with
  `test_phase2_schema.py`: 15 passed).
- Full suite: **467 passed, 9 failed, 7 skipped** — the same 9 pre-existing AI-Papers
  failures (Phase 4: 462 passed; +5 = the new course tests, with the Phase-2 schema test
  rewritten rather than dropped). `test_structure` caught the new package missing its
  `__init__.py`; fixed before the final run.
- `ruff check` / `ruff format --check`: clean on the course package, the migration, the
  tests and the files this phase edited; repo total **201** (Phase 4: 210 — the fix pass
  also tidied pre-existing import order in the files it touched, and caught a stray
  `return result` my edit had left behind).
- Combined run of `test_classroom_course` + `test_phase2_schema` + `test_structure` +
  `test_staff_workload`: **51 passed**.


## Phase 6 — Course tab UI

- [x] New tab **Course** in `SectionDetailPage` (position 3, after Attendance) →
      Students · Attendance · **Course** · Academics · Homework · Timetable ·
      Exams & AI Papers.
- [x] Subject row: subject, current teacher, previous teachers **one per line with their
      dates and their own count** (`ansari · 2026-06-01 → 2026-09-30 · 2/10`), the
      segmented bar — one colour per teacher who finished something, a grey "not done"
      remainder, and a legend with `2/10 chapters`; every slice carries its share and
      count on hover.
- [x] Expand → chapter table: number, name, planned date, status chip (red when behind
      plan), completed on, completed by, and a **Mark done / Undo** button that is
      disabled unless the server's `canTick` allows it, with the reason in the tooltip.
- [x] Ahead/behind badge per subject (`3 behind plan` / `+2 on plan` / `On plan`), and
      **"No plan"** when the school set no planned dates — never a green "on time" for an
      unplanned subject. Empty states: "no subject assigned", "no chapters planned yet",
      "No plan".
- [x] Tests: the bar shares, the teacher-change case and the permission gate are covered
      by `lib/course/view.test.ts` (**7 tests**) on the same zero-dependency runner the
      Attendance tab uses; the write itself is refused server-side and proven in
      `tests/test_classroom_course.py` (Phase 5).

### Phase 6 - Result

**What landed.** The class-section page has its Course tab: one read draws every
subject's plan, its teacher history, the segmented bar and the chapter table, and the
people who own a subject can tick chapters straight from the row.

*Frontend*
- `services/course.service.ts` (new) — `getSectionCourse`, `tickChapter` (`toCamel`).
- `lib/course/view.ts` (new, pure) — `barSegments`, `scheduleBadge`, `tickGate`,
  `nextStatus`, `tickLabel`, `teacherTrail`, `chaptersLabel`; + `view.test.ts` (7 tests).
- `components/features/classroom/course/CoursePanel.tsx` (new) — the tab; invalidates
  `["course", …]` and `["classroom"]` after a tick, because the card prints the same
  percentage.
- `course/CourseBar.tsx` (new) — the bar + legend; `course/chapter-columns.tsx` (new) —
  the chapter table's columns and the gated button.
- `SectionDetailPage.tsx` — the tab (position 3); `types/index.ts` — `SectionCourse`,
  `CourseSubject`, `CourseChapter`, `CourseTeacher`, `ChapterStatus`.

**Decisions worth knowing**
- The bar has **no slice for a teacher with 0 finished chapters**: a colour that stands
  for nothing is a lie. They still appear, with their dates and `0/10`, in the row's
  teacher lines — which is where "has not started" belongs.
- The badge reads `No plan` when no chapter has a planned date, and `+N on plan` only
  when nothing is late (a subject never claims both ahead and behind).
- The button's `disabled` state comes from the server's `canTick`, so the screen cannot
  offer a tick the API will refuse; the tooltip carries the sentence, and the API
  refuses again (`403`) if called anyway.

**Gates**
- `node --test src/lib/course/view.test.ts` — **7 passed**.
- `npx tsc --noEmit` clean; `npx eslint` clean on every changed path; `prettier --write`
  applied.
- Backend untouched in this phase (Phase 5 shipped it), so the server suite result stands
  at Phase 5: 467 passed / 9 pre-existing failures / 7 skipped.


## Phase 7 — Exams schema + backend

**a. Schema (migration)**
- [ ] `exam` gains: `class_id`, `classroom_id` (nullable = school exam),
      `academic_year_id`, `scope` (`class`/`school`), `exam_type` label, `status`
      enum (`draft/scheduled/done/marks_entry/published`), `created_by_user_id`,
      `note`, `published_at`. Existing `status` text migrated to the enum.
- [ ] `exam_paper` (date-sheet row): `exam_id`, `subject_id`, `class_id`,
      `exam_date`, `start_time`, `end_time`, `max_marks numeric(6,2)`,
      `passing_marks numeric(6,2)`, `room`, `note`; unique
      `(exam_id, class_id, subject_id)`.
- [ ] `exam_paper_chapter (exam_paper_id, chapter_id)`; unique pair.
- [ ] `marks`: `marks_obtained` → `numeric(6,2)`, `is_absent` bool, `exam_paper_id`
      FK, unique `(exam_paper_id, student_id)`; old rows mapped from
      `(exam_id, student_id, subject_id)` with row counts printed.
- [ ] `marks_audit (marks_id, old_value, new_value, changed_by_user_id, changed_at)`.
- [ ] `grade_scale (school_id, min_percent, grade)` + unique `(school_id, min_percent)`.
- [ ] **`examsubject` is dropped in this migration** (owner decision: 0 rows). It is the
      old "what a subject is out of" row; `exam_paper.max_marks` states it once per
      paper. Order: move anything the new tables lack (0 rows today) → count and
      **abort printing the count** if it is not 0 → remove the `ExamSubject` model and
      every reference (grep `examsubject`, `ExamSubject`, `exam_subject`) →
      `op.drop_table`. The downgrade **recreates the empty table** with its original
      shape, proven `up → down → up`.

**b. Endpoints**
- [ ] `POST /exams` (class exam: teacher own class+subject; school exam: principal
      only) with date sheet + syllabus from `chapter` ids.
- [ ] `PATCH /exams/{id}` (date, syllabus, note) — notifies schedulers.
- [ ] `POST /exams/papers/{id}/marks` draft save; `POST …/publish`;
      `PATCH …/marks/{student}` after publish → `marks_audit` row.
- [ ] `GET /exams/{id}/results` → per student: marks, absent, grade, rank (section /
      class / overall for school exams); competition ranking `1,2,2,4`, absentees
      excluded; averages/highest/lowest for teacher, class averages + unpublished
      list for principal.
- [ ] Visibility: student/parent only own published marks + own rank + totals;
      teacher own class/subject; principal/HOD school; other school = 404.
- [ ] `rank_display` setting (`rank` default, `band`, `off`); `grade_scale` read.
- [ ] Notifications: scheduled/changed (class test), date sheet published/changed,
      marks published, marks changed; the one-day-before reminder via the Phase 3
      scheduler (only `status=scheduled`).

**c. Tests** (`tests/test_classroom_exams.py`)
- [ ] visibility matrix (student, parent, teacher, principal, other school).
- [ ] unpublished hidden; ties ranked `1,2,2,4`; absent not ranked; audit on change.
- [ ] notifications exactly once per event; reminder fires once.

## Phase 8 — Exams tab UI

- [ ] Rename **Academics** → **Exams**, two sub-tabs: **Class Exams** / **School
      Exams**.
- [ ] Schedule form: name, type label, class + sections, subject, date, start/end
      time, total + passing marks, syllabus picker (chapters from Course), note, room.
- [ ] Date-sheet builder for school exams (rows per class/subject/date).
- [ ] Marks grid: per student, absent as its own state, **Save draft** → **Publish**;
      after publish an edit shows "logged" and saves with an audit row.
- [ ] Result views by role (student/parent own row; teacher class table with
      average/highest/lowest; principal school view with unpublished exams).
- [ ] Tests: form validation (passing ≤ total, date required), role-based views.

## Phase 9 — Homework + Timetable

**a. Homework schema (migration)**
- [ ] `homeworksubmission` gains `submitted_at`, `is_late`, `graded_at`,
      `marks_awarded numeric(6,2)`; unique `(homework_id, student_id)` (0 rows today).
- [ ] `classlog` gains `subject_id` (nullable); the existing period keys stay.

**b. Homework backend + UI**
- [ ] `POST /homework/submissions/{id}/feedback` (`homework.grade` or reuse
      `homework.create`): feedback + marks + `graded_at`; returns the row.
- [ ] `POST /homework/submit` stamps `submitted_at` and sets `is_late` from the due
      date (student/parent path).
- [ ] Diary: `POST /homework/diary` accepts `timetableperiod_id` + `subject_id`; the
      UI gets a small "Write today's log" form (subject, period, note).
- [ ] Notifications: assigned (section students + guardians) and feedback given
      (student + guardians), dedupe per homework/student.
- [ ] UI: submissions table gets grade/feedback inputs and the submitted time + late
      badge.

**c. Timetable**
- [ ] `bell_schedule (school_id, period_no, start_time, end_time, is_break)` — unique
      `(school_id, period_no)`; seeded per school on first read (a 6-period default).
- [ ] `timetableperiod` unique `(school_id, classroom_id, day_of_week, start_time)`
      **in addition to** the teacher slot.
- [ ] `create/update` catch `IntegrityError` → `409` "teacher already booked at …" /
      "class already has … at …".
- [ ] Frontend grid reads the bell schedule from the API (no hardcoded 6 periods);
      break rows rendered as breaks.
- [ ] Workload: confirm `periods_per_week` (Teachers) changes on assign/move/delete
      (already derived) and the UI invalidates the teachers query.

**d. Tests** (`tests/test_classroom_homework.py`, `tests/test_classroom_timetable.py`)
- [ ] feedback visible to that student/guardian only; late flag correct.
- [ ] clash returns 409 with the teacher/class name (never 500).
- [ ] assigning a period changes `periods_per_week` by 1; deleting it takes it back.

## Phase 10 — Rename, cleanup, final verification

- [ ] Rename the tab **Exams & AI Papers** → **AI Papers** (label only, nothing else).
- [ ] `pct()` / `inr()` → one shared module; remove dead code found on the way.
- [ ] Verify the two mirrors are **gone**: `grep -ri examsubject` and
      `grep -ri syllabusprogress` find nothing outside `alembic/versions/` (the
      migrations that created and dropped them) and this file. They were dropped in
      Phase 5 / Phase 7 - there is no "deprecated" table to clean up here.
- [ ] End-to-end tests: attendance + notification + leave; course chapter update across
      a teacher change; class test schedule → published marks → ranks → notifications;
      school exam with date sheet; homework feedback; timetable assignment reflected in
      Teachers.
- [ ] Full suite, `ruff check`, `ruff format --check`, `tsc --noEmit`, and every
      migration `up → down → up` on a copy — output pasted into this file.
- [ ] Final report: what is done, what was skipped and why.

---

## Migration log (filled as phases land)

| Phase | Revision | What it changes | Down works? | Proven up→down→up |
| --- | --- | --- | --- | --- |
| Phase 1 | — | no migration: `enrollment` + `student.deactivated_at` already existed | — | — |
| Phase 2 | `b7c1d4e9a3f2` | register keys (composite + partial day-level), `leave_request_id`, `school_setting`, audit `school_id NOT NULL` | yes — drops the keys/column/table and re-opens `school_id`; register + audit rows kept | yes (Postgres 17: before → up → down → up, state printed at each step; duplicate guard proven separately) |
| Phase 3 | `c8e2f5a1d7b3` | `notification` event columns + partial `(user_id, dedupe_key)` + bell index | yes — drops the indexes and the 5 columns; every message stays readable | yes (Postgres 17: before → up → down → up, one pre-existing row carried through with `channel=in_app`) |
| Phase 4 | — | no migration: the screen reads endpoints Phase 2/3 already shipped (one new read: `GET /attendance/closed-days`) | — | — |
| Phase 5 | `d3f1a8c5e2b7` | `chapter` + `chapterprogress`, `subjectteacher` history columns + key, **`syllabusprogress` dropped** | yes — recreates `syllabusprogress` empty, restores the old teacher key, drops the plan tables | yes (Postgres 17: before → up → down → up; the drop guard proven separately with 1 row → refused, exit 1) |

### Tables to be dropped (owner decision, 15 Nov 2026)

`examsubject` and `syllabusprogress` hold **0 rows**. They are removed - not mirrored:
each is dropped inside the migration of the phase that lands its replacement, and every
reference leaves the code with it.

| Table | Dropped in | Replaced by | Guard before `drop_table` | Downgrade |
| --- | --- | --- | --- | --- |
| `syllabusprogress` | Phase 5 | `chapter` + `chapter_progress` | `SELECT count(*)` → **abort and print** if ≠ 0 | recreates the empty table (columns, indexes, `UNIQUE(classroom_id, subject_id)`) |
| `examsubject` | Phase 7 | `exam_paper.max_marks` (per paper) + `marks` | `SELECT count(*)` → **abort and print** if ≠ 0 | recreates the empty table (`UNIQUE(exam_id, subject_id)`, `max_marks`) |

Rules that come with this decision:
* **No new code** may read or write either table from now on. New data goes only to
  `chapter` / `chapter_progress` (course) and `exam` / `exam_paper` /
  `exam_paper_chapter` / `marks` (exams).
* **Course completion is computed from `chapter_progress` only** - one function, used by
  the Course tab *and* the Teachers performance score. No second copy of "chapters done".
* The row-count guard is a refusal, not a log line: a non-empty table means something
  still writes the old path, and the migration must stop rather than destroy data.

Reference removal surface (grep on 15 Nov 2026 - the whole of it):

| File | What is there today |
| --- | --- |
| `backend/app/domains/academic/classroom/academics/models.py` | `SyllabusProgress` model |
| `backend/app/domains/academic/classroom/academics/repository.py` | reads/writes of `SyllabusProgress` |
| `backend/app/domains/academic/classroom/exams/models.py` | `ExamSubject` model |
| `backend/app/domains/academic/classroom/repository.py` | `ExamSubject` / syllabus reads |
| `backend/app/domains/people/teachers/appraisal/performance.py` | syllabus completion → must read `chapter_progress` |
| `backend/tests/test_phase2_schema.py` | asserts the `SyllabusProgress` columns exist → replaced by the `chapter_progress` assertions |
| `frontend/src/services/academics.service.ts` | one comment that names `examsubject` → reworded to `exam_paper` |

## Open questions for the owner (blocking only where marked)

1. **Not blocking** — host Python: allow-list the repo + uv python folders, or should
   every phase keep using the `eduverse-checks` container? (Phase 0 used the container.)
2. **Resolved (15 Nov 2026) - drop, do not mirror** - `examsubject` and
   `syllabusprogress` hold 0 rows, so they are dropped (Phase 5 / Phase 7). The
   reference list below is the whole removal surface, taken with grep today.
3. **Not blocking** — scheduler: a 60-second thread inside the API, or APScheduler as a
   dependency? (Default planned: the thread — no new dependency.)
4. **Not blocking** — the 9 pre-existing AI-Papers test failures (see Phase 0 result):
   fix them inside Phase 7/8, or leave them for the separate AI Papers task?

