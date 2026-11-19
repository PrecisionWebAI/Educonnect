# Phase 2 Notes — Course Feature (verified facts + reminders)

> Ye file **cross-phase** notes ke liye hai. `phase.md` = plan + progress log; yahan wo
> baatein hain jo ek phase se doosre phase ko affect karti hain, aur jo prompt ke notes se
> alag code mein mili.
>
> Rule: har phase ke baad, jo baat aage/peeche ke phase ko affect kare, wo yahan add karo.

---

## A. Prompt ke notes vs code — corrections (Phase 0 audit)

1. **"Fixed Course table" = `syllabusprogress`** (classroom_id, subject_id, chapters_total,
   chapters_done, teacher_id, academic_year_id, planned_completion). Ye table **already
   drop ho chuki hai** migration `d3f1a8c5e2b7_course_chapters.py` (15 Nov 2026) mein —
   aur migration rows zero hone par hi drop karti thi. Matlab Phase 1.5 ka "purane course
   data ka migration" **trivial** hai: migrate karne ke liye koi counter data maujood nahi.
   Frontend mein bhi koi fixed/hard-coded course table nahi mili; `LessonPlan.tsx` ek
   lesson-detail card hai (aaj ka lesson), weekly plan nahi.

2. **`subject` structure wahi hai jo note kehta hai** (`id, school_id, name, code`), lekin:
   - `code` **NOT NULL** aur unique per school hai — custom subject ke liye code generate
     karna padega.
   - `is_active` nahi hai (add karna hai).
   - `(school_id, name)` unique **exact** match par hai. Writes `CanonicalRequest` se
     lowercase hote hain, par DB-level `lower(name)` unique index nahi hai.
   - Boot seed (`academics/seed.py`) har active school ko 13 subjects deta hai (mathematics,
     english, hindi, physics, chemistry, biology, computer science, social science,
     history, geography, physical education, art, music).

3. **`subjectteacher` mein history columns maujood hain, par write path galat hai.**
   `academic/classroom/service.py::assign_subject_teacher` open row ka `teacher_id`
   **overwrite** karta hai (aur `None` par row delete). Columns (`effective_from`
   NOT NULL default today, `effective_to`) aur unique
   `(classroom_id, subject_id, effective_from)` hain, lekin "ek open row" ka DB rule nahi.
   Course tab ke tests rows seedha insert karte hain, isliye bug pakda nahi gaya.
   → Phase 1 (index) + Phase 4 (service) mein fix; legacy endpoint ko bhi history-aware
   karna hai.

4. **Chapters bilkul note jaise hain** — `chapter` class-level, `chapterprogress`
   section-level, `completed_on` + `completed_by_employee_id` ke saath. Lekin **chapter
   CRUD endpoints nahi hain**: aaj sirf Course tab read + tick hai. Chapter add/edit/
   reorder/delete Phase 5 mein naya kaam hai (model change nahi).

5. **Weekly off kahan hai:** `school_setting` row `attendance.weekly_off_days`
   (default `"6"`; `"5,6"`, `"5#1"` bhi support). `admin/settings/calendar.py` already
   `closures()`, `open_days(session, start, end)`, `count_open_days()` deta hai — holidays
   (`on_date..end_date`), dated `week_off`, aur `school_open_day` sab respect karta hai.
   **Naya helper likhne ki zarurat nahi**; `course/teaching_days.py` ko isi ka thin wrapper
   banana hai.

6. **Teacher pehchanna:** teacher = `employee` row; `employee.user_id` → `app_user`.
   Teaching role `people/teachers/labels.py::TEACHING_ROLES` se. Active = `left_on IS NULL`
   + `deactivated_at IS NULL` (login `is_active` alag). `teachers/repository.py::
   teachers_statement(kind="teacher", status="Active")` mein sahi filter already hai.

7. **`/classroom/teachers` dropdown aaj galat list deta hai:** `repository.
   get_teacher_options` **saare staff** (accountant, driver, leaver bhi) deta hai, koi
   teaching/active filter nahi. Phase 4 mein `get_active_teacher_options` chahiye.

8. **Role hierarchy nahi hai:** `role` mein sirf `codename`, `label`, `description`,
   `is_system`. "Principal aur upar" ka matlab permission hona chahiye (D9), role naam
   hard-code nahi.

9. **Permission seeding migration ke bina hoti hai:** `permissions_repository.
   seed_permissions()` har boot par `PermissionEnum` + `ROLE_PERMISSIONS_MAP` se
   `permission`/`rolepermission` rows idempotently daalta hai. Naye codenames sirf in do
   jagah add karo. `scripts/seed/02_permissions_seed.py` bhi wahi function call karta hai.

10. **Notifications ka ek hi writer hai:** `main/notifications/events.py::notify()`.
    `PRINCIPALS = ("principal","vice_principal")` — spec "principal aur uske upar" ke liye
    **permission-based resolver** chahiye (`course.approve` holders). `dedupe_key` +
    partial unique index duplicate rokta hai; notification failure caller ko fail nahi
    karta (savepoint + swallow).

11. **Scheduler ka existing pattern:** `core/scheduler.py` `register_job(name, callable)`
    deta hai, aur **ek job already registered hai** — `exam-reminder`, jo
    `academic/classroom/exams/plan/__init__.py` mein import par register hota hai (us
    package ko `api.py` import karta hai). Course reminder bhi isi pattern se:
    `course/reminders.py` mein job banao aur `course/__init__.py` (ya `router.py`) se
    import karo, taaki `api.py` mount hote hi register ho jaye. `main.py` chhedne ki
    zarurat nahi.

12. **Alembic head = `b7d2e4f1a9c3`** (`open_day`), aur chain mein
    `d3f1a8c5e2b7_course_chapters` already shaamil hai. `backend/scripts/check_schema.py`
    sirf **tables/columns** compare karta hai (nullability/index nahi), isliye migration
    mein `school_id NOT NULL` karne se drift check nahi tootega.

13. **`TenantMixin.school_id` model mein nullable hai** (session `before_flush` stamp
    karta hai). Naye tables ke migration mein `nullable=False` rakhna hai (spec), model
    `Optional` hi rahega — yahi existing pattern hai (`b7e4c1a9f2d3_school_id_not_null`).

14. **`section_detail` ke subjects:** `repository.get_subject_rows(session, section_id)`
    **school ke saare subjects** return karta hai (left join se us section ka teacher) —
    sirf section ke added subjects nahi. Isliye Exams/Timetable dropdowns aaj hi "all
    subjects" dikhate hain. Course tab ka source `classroomsubject` hoga; is function ko
    chhedne ki zarurat nahi (warna doosre tabs badal jayenge).

---

## B. Cross-phase reminders (inhe har phase se pehle padho)

| # | Reminder | Kise affect karta hai |
|---|---|---|
| R1 | `MODEL_MODULES` (`app/core/schema.py`) mein naya `models.py` add karna zaroori hai, warna tests/create_all us table ko nahi banayenge aur `test_structure` fail hoga. | Phase 1 |
| R2 | Har naya `router.py` `api.py` mein mount hona chahiye (`tests/test_structure.py` rule 3). `course/router.py` pehle se mounted hai, isliye naye routes wahin add karo. | 3–9 |
| R3 | `app/domains/**` mein text SQL nahi (`test_no_domain_runs_its_own_sql`); raw SQL sirf `alembic/versions/*` mein. `lower(name)` unique index migration mein `op.execute` se. | 1 |
| R4 | `SectionCourseRead` ke purane fields (`subjectId`, `subject`, `teachers[]`, `done`, `total`, `percent`, `chapters[]`, `canTick`) **kabhi na hatao** — `ExamScheduleForm` unhe padhta hai. Naye fields add karo. | 3–5 |
| R5 | `subjectteacher` par legacy open rows (jinka `classroom_subject_id` NULL) ho sakte hain. Assign karte waqt dono ko close karo, warna do "current" teachers dikhenge. | 4 |
| R6 | Completion ke do formulas hain: `by_section()` chapter-weighted (performance ke liye) aur naya `subject_average()` (D7 card/tab ke liye). Card + Course tab subject-average use karein; performance ko na badlo. | 4, 8, 9 |
| R7 | `course.manage` sirf admin-level; teacher ke paas `course.read` + `course.plan`. Har naye route par `RequirePermission` + service-level holder check dono. | 2–9 |
| R8 | Reject reason **server par mandatory** (`422`), sirf UI validation nahi. Approve/reject `expected_version` ke saath; already-approved same version → idempotent 200. | 7 |
| R9 | Lesson plans `classroomsubject` par tike hain, teacher par nahi — isliye teacher change par plans orphan nahi hote (D10). Chapter credit `chapterprogress.completed_by_employee_id` se. | 4, 6, 8 |
| R10 | Notification recipients **permission** se (`course.approve`), role naam se nahi. Writer sirf `events.notify()`; `dedupe_key` version ke saath. | 9 |
| R11 | Frontend mein `LessonPlan.tsx` already hai (lesson-detail). Weekly plan components ka naam `WeeklyLessonPlan*` / `LessonPlanReview*` rakho; `Tabs` component props `{ tabs, active, onChange }` hain. | 6, 7 |
| R12 | `TeachersPage` teacher-only account par `MyStaffPanel` dikhata hai; Course tab wahan bhi chahiye. Tab order: List → Course → Workload → Substitution → Attendance & Leave → Performance. | 8 |
| R13 | `get_teacher_options` ka legacy result `(employee_id, name, email)` tuple hai; naya active-teacher function banao aur purane ko alias/delegate karo, warna other screens toot jayengi. | 4 |
| R14 | Migration prefix `b7d2e4f1a9c3` se `down_revision`; purani revisions ke `down_revision` mat chhedo. Downgrade likhna hai (Phase 1) aur data-loss wali baat phase.md mein. | 1 |
| R15 | `subject.name` canonical lowercase store hota hai, frontend `titleCase` se dikhata hai. Custom subject "English 1" → DB `english 1`. Isliye duplicate check `func.lower` par. | 3 |
| R16 | Date format: API/DB `YYYY-MM-DD`, frontend jo school ka existing format hai wahi. Naya date library nahi (date-fns already hai). | 3–9 |
| R17 | Phase 1 ke baad `classroomsubject` hi Course tab ka source hai. `repository.get_subject_rows()` (section detail) ko **na chhedo** — Exams/Timetable/Homework dropdowns usi par hain. | 3–5 |
| R18 | `subjectteacher` par do partial unique indexes hain: `uq_subjectteacher_open_cs` (jab `classroom_subject_id` set ho) aur `uq_subjectteacher_open_legacy` (jab NULL ho). Phase 4 ka assign hamesha nayi row par `classroom_subject_id` set kare, aur purani legacy open row close kare. | 4 |
| R19 | Migration `e2b8c4f7a1d9_course_lesson_plans.py` = naya head, lekin **DB par abhi run nahi hui**. Chalane se pehle backup + user approval; backfill counts print karti hai aur duplicate names/open rows par abort karti hai. | 1, 10 |
| R20 | `lessonplanhistory` mein `status` column **nahi** hai: verdict `approved_at`/`rejected_at` se pata chalta hai; "abhi effective" version `lessonplan.approved_version` se. Services `updated_at` khud set karein (default sirf insert par chalta hai). | 6, 7 |
| R21 | Local Python blocked hai, par Docker image `eduverse-checks:latest` se backend tests/lint chalte hain (neeche Section C). PowerShell redirect UTF-16 likhta hai — `read` karte waqt dhyan rakho. | 1–10 |
| R22 | Legacy route `PUT /classroom/sections/{id}/subjects/{subject_id}/teacher` aaj `classes.assign_teacher` par hai — HOD ke paas wo right hai. Phase 4 mein ise `course.assign_teacher` par shift karo; warna HOD Course rights ke bahar teacher change kar sakta hai. | 4 |
| R23 | Course scope mein school check hamesha `select(...)` se karo, `session.get` se nahi: identity map purane school ki row wapas de sakta hai (tenant filter bypass). `course/scope.py` isliye aise likha hai. | 3–9 |
| R24 | `GET /classroom/sections/{id}/course` ka guard ab `course.read` hai (pehle `classes.read`), aur source `classroomsubject` (+ legacy `subjectteacher`). `ExamScheduleForm` isi read ko use karta hai — teacher/principal ke paas `course.read` hai, accountant ke paas nahi. | 4–10 |
| R25 | Subject delete ke rules: koi `lessonplan` row (status koi bhi) ya completed chapter → `409` + "archive instead"; empty row hi hard-delete hoti hai (unstarted progress + assignment history saath). Master subject retire karne se section rows delete nahi hote. | 4, 6, 10 |
| R26 | `subjectteacher` history rows `(classroom_id, subject_id, effective_from)` par unique hain. Same-day teacher correction **usi row ka teacher badle**, nayi row insert na kare; warna unique violation. `course.service._assign_row` yeh handle karta hai. | 4–6 |
| R27 | `chapter` class-level hai: add/edit/delete se **har section** ka total badalta hai; progress section-level. `sequence` update = move-to-position (two-phase renumber), explicit create duplicate `409`. Delete blocked by any completed `chapterprogress` **and** `exam_paper_chapter`; `canEdit` sirf `course.manage`. | 5–8 |
| R28 | Plan submit always (a) `expected_version` check kare, (b) working row + `lessonplanhistory` same transaction mein likhe, (c) approved week par bina `intent="change"` ke `409` de, (d) `approved_version` ko chhode. Concurrent submit `IntegrityError` → `409`, 500 nahi. History row immutable; review Phase 7 verdict stamp karega. | 6–8 |
| R29 | Decision `expected_version` par hai: approve/reject current history row ko verdict stamp karte hain; same version dobara approve → idempotent `200`; stale → `409`. `approved_version` sirf approval badalta hai, reject use chhodta hai. Bulk approve valid rows commit kare aur stale rows `skipped` return kare, poora batch fail na ho. | 7–9 |
| R30 | Teachers > Course: `teacher_list` `course.view_all` ke bina sirf caller ka row; `teacher_detail` doosre teacher par `404` (403 nahi, existence leak nahi); `my_course` token se employee nikalta hai, browser id se nahi. `behind_subjects` D8 ka approximation hai. | 8–10 |
| R31 | Course notifications: approvers `course.approve` role grants se resolve karo (`course_approver_user_ids`), naam list se nahi. Submit/approve/reject dedupe key version ke saath rakho. Reminder job current month ke finished weeks ko dekhe, current teacher ko, aur dedupe key `course:reminder:{cs}:{year}-{month}-w{week}` ho. | 9–10 |
| R32 | `e2b8c4f7a1d9` migration live DB ko `inspect()` karti hai, isliye offline `alembic --sql` SQL generate nahi kar sakti. Actual upgrade/downgrade sirf backup + approval ke baad school Postgres par; `tests/test_course_migration.py` single head + downgrade contract pin karta hai. | 10 |

---

## C. Environment / commands (is machine par verify kiya)

- **Backend tests: Docker se chalte hain.** Local `uv` PATH mein nahi hai aur
  `backend/.venv/Scripts/python.exe` par Application Control policy block hai, lekin
  `eduverse-checks:latest` (Python 3.14 + deps + ruff) maujood hai:
  - tests:
    `docker run --rm -v "<repo>\backend:/app" --workdir /app --entrypoint python eduverse-checks:latest -m pytest tests/test_x.py -q`
  - lint / format:
    `docker run --rm -v "<repo>\backend:/app" --workdir /app --entrypoint ruff eduverse-checks:latest check <paths>`
    (aur `format --check` / `format`).
  - PowerShell output redirect UTF-16 likhta hai; `Get-Content -Encoding Unicode` ya
    `read_files` se padho.
  - User ke machine par seedha `cd backend; uv run python -m pytest tests -q` bhi chalega.
- **Frontend unit tests chalte hain:** `cd frontend; node --test src/lib/course/view.test.ts`
  → 7/7 pass (Node v24.22.0, TS type-strip by default). Naye pure-function tests isi
  command se.
- **Lint/format (jab chale):** backend `uv run ruff check .` + `ruff format .`; frontend
  `npm/yarn lint` + `prettier`. Node available hai.
- **Alembic:** head `b7d2e4f1a9c3`; migration ke baad `uv run alembic upgrade head`
  (local DB, backup ke baad).
- **DB:** PostgreSQL (local/Supabase) `.env` se; SQLite sirf tests ke liye (`StaticPool`).

---

## D. Inhe todna nahi (existing behaviour)

- `exam_paper_chapter`, `paperdraft`, `examsource`, `homeworkassignment`,
  `timetableperiod`, `marks`, `exam_paper` — `subject` / `chapter` ke existing FKs aur
  columns.
- `course/completion.py` ke public functions (`by_section`, `for_section`, `for_subject`,
  `by_teacher`) — Classroom card + Teachers performance inhe use karte hain.
- `PATCH /course/chapters/{chapter_id}/progress` ka contract (`classroom_id`, `status`) —
  frontend `tickChapter` isi ko call karta hai.
- `GET /classroom/sections/{id}/course` ke purane response fields (R4).
- `notification` table ka single-writer rule aur dedupe partial index.
- `RequirePermission` + `ScopeValidator` ka existing behaviour (naya system nahi).
- Tenant listeners: har query `select(Model)`/`session.get` se; `SKIP_SCHOOL` sirf allowed
  paths par.
- `TeachersPage` ke existing tabs/queries; sirf naya tab add karna hai.

---

## E. Open questions (user se confirm)

1. **D9:** `course.read` + `course.plan` add karna theek hai? HOD ko `course.view_all`
   (department scope ke bina) chahiye ya nahi?
2. **D5:** Week 5 sirf 29+ din wale month mein — theek hai? (Feb mein Week 5 kabhi nahi.)
3. **D7:** Classroom card ka `syllabusPercent` subject-average par shift karna theek hai?
   (Aaj chapter-weighted hai; number badlega.)
4. **Phase 9.5:** Principal overview screen chahiye ya optional skip?
5. **Lesson plan required fields:** sirf `topics` + `learning_objectives` mandatory
   rakhun, ya chhah field bhi mandatory? (Default: do mandatory, baaki optional.)

---

## F. Phase entries (future)

Har phase ke baad yahan ek chhoti line: date, phase, aur kya cross-phase note bana.

- **Phase 0 (19 Nov 2026):** file bani; corrections A1–A14 aur reminders R1–R16 add kiye.
- **Phase 1 (19 Nov 2026):** schema + migration ready.
  - `subject.is_active` (default true) + migration-only functional unique index
    `uq_subject_school_name_lower`.
  - Tables: `classroomsubject`, `lessonplan`, `lessonplanhistory`; naya model module
    `academic.classroom.course` `MODEL_MODULES` mein registered.
  - `subjectteacher.classroom_subject_id` + `uq_subjectteacher_open_cs` /
    `uq_subjectteacher_open_legacy`.
  - Migration `e2b8c4f7a1d9` = head; **abhi kisi DB par apply nahi hui**.
  - Tests: `tests/test_course_schema.py` 7/7, `tests/test_classroom_course.py` 5/5,
    `tests/test_phase1_schema.py` + `test_phase2_schema.py` 21/21; ruff check + format
    clean (reminders R17–R21 add kiye).
- **Phase 2 (19 Nov 2026):** permissions + guards.
  - `course.read`, `course.plan`, `course.assign_teacher`, `course.manage`,
    `course.approve`, `course.view_all`; teacher/HOD read+plan, principal+ all six.
  - `course/scope.py` (own-subject, teacher-change, visible rows, other-school `404`
    behaviour) aur `course/teaching_days.py` (open days + Week 1–5, D5).
  - Tests: permissions 6/6, teaching days 6/6, matrix 12/12; ruff clean.
  - Reminders R22 (legacy teacher route abhi `classes.assign_teacher` par) aur R23
    (`session.get` identity-map) add kiye.
- **Phase 3 (19 Nov 2026):** subject master + Add Subject.
  - Master APIs (create/rename/retire), section add (master/custom), archive/restore/
    delete rules; `section_course` source `classroomsubject` + legacy rows; `course.read`
    guard; per-row `can*` flags.
  - Frontend Course table + Add Subject + Manage Subjects + chapters popup; Lesson Plan
    cell still "No plan" until Phase 6.
  - Tests: backend subjects 7/7, legacy course 5/5, frontend view 8/8; tsc + ruff clean.
  - Reminders R24 (guard/source change) aur R25 (delete vs archive) add kiye.
- **Phase 4 (19 Nov 2026):** table + teacher assignment.
  - Teacher change = history: open row closed at `effective_from - 1 day`, new open row,
    same teacher no-op, same-day correction replaces that day; legacy route shares the
    same service and now guards on `course.assign_teacher` (R22 closed).
  - `get_active_teacher_options` = teaching role + not left/deactivated + active login;
    `get_teacher_options` delegates. `/classroom/teachers` ab active teachers deta hai.
  - D7: `completion.subject_average_by_section` (per subject %, then average); Classroom
    `syllabusPercent` bhi isi se. Class-level chapter plan har section par lagta hai, so
    9-B with no section row still reads 0% rather than "no data" (legacy test preserved).
  - Table Lesson Plan summary = **current month** counts; month switch Phase 6 popup.
  - Tests: teachers 8/8 + regression 26/26; frontend view 11/11; tsc + ruff clean.
  - New reminder R26: assignment history rows are keyed by
    `(classroom_id, subject_id, effective_from)`; same-day edits must update the row, not
    insert a second one.
- **Phase 5 (19 Nov 2026):** chapters + progress.
  - Class-level chapter CRUD (`POST/GET /course/subjects/{cs}/chapters`,
    `PATCH/DELETE /course/chapters/{id}`); add appends unless an explicit free sequence is
    given (occupied → `409`); a `sequence` PATCH means **move to position**, renumbered
    with a negative-then-positive flush.
  - Delete blocked by a completed `chapterprogress` in **any** section and by
    `exam_paper_chapter`; otherwise progress rows + chapter go.
  - `ChapterRowRead.canEdit` = office (`course.manage`); `canTick` unchanged (current
    holder or office). `_may_tick` now accepts `course.manage` as well as legacy
    `classes.update`.
  - Frontend chapter table: Add chapter, Edit, Delete confirm, ↑/↓ reorder;
    `reorderSequence` + `chapterTotals` pure helpers; every write invalidates `course`
    and `classroom`, so the row bar and the D7 card stay equal.
  - Tests: chapters 7/7; regression 30/30; frontend view 13/13; tsc + ruff clean.
  - New reminder R27: chapter changes are class-wide; delete has two blockers; teacher
    edit is deliberately not allowed.
- **Phase 6 (19 Nov 2026):** weekly lesson plan (teacher side).
  - `month_plan` = Week 1-5 (D5) + real teaching days + latest row + approved snapshot;
    `submit_week` = working row + immutable snapshot in one transaction, `expected_version`
    guard, approved lock + `intent="change"`, rejected resubmit clears reason.
  - APIs: `GET/PUT /course/subjects/{cs}/lesson-plans...`; route `course.read`, service
    `course.plan` + current-holder check.
  - Frontend `WeeklyLessonPlanDialog` (month/year, Week tabs, 6 fields, status/version,
    rejection reason, approved snapshot, Request change); CourseTable cell opens it.
  - Tests: lesson plans 9/9; course regression 36/36; frontend 17/17; tsc + ruff clean.
  - New reminder R28: submit always checks version, writes history in the same transaction,
    and never rewrites the approved version without the change intent.
- **Phase 7 (19 Nov 2026):** approval flow.
  - Queue (`GET /course/reviews`, count, section filter) shows only Submitted weeks with
    the full six fields; approve/reject/approve-many guarded by `course.approve`.
  - Approve stamps history (`approved_at/by`) and `approved_version`; re-approving the
    same version is idempotent 200. Reject needs a prose reason, stamps history, sets
    Rejected. Bulk approve commits valid rows and returns stale ones as `skipped`.
  - Teacher notifications: `course.week_approved` / `course.week_rejected`, dedupe per
    version; reject body carries the reason.
  - Frontend: `LessonPlanReviewPanel` (queue, view plan, approve/reject, bulk approve) +
    approver controls inside `WeeklyLessonPlanDialog`; Course tab "Review plans".
  - Tests: approvals 6/6; regression 41/41; frontend 18/18; tsc + ruff clean.
  - New reminder R29: decisions are versioned and history-stamped; bulk is partial-success,
    not all-or-nothing.
- **Phase 8 (19 Nov 2026):** Teachers > Course.
  - Backend `teacher_course.py`: list aggregates (subjects/sections/pending/behind/
    completion), detail (current + past assignments, month weeks, chapters), `my_course`.
  - API `GET /course/teachers`, `/course/teachers/{id}`, `/course/my`; self/view_all guard,
    other teacher `404`.
  - Frontend Teachers tab + detail; My Staff gets "My course"; plan popup reused for
    approve/reject.
  - Tests: teacher tab 4/4; regression 34/34; frontend 18/18; tsc + ruff clean.
  - New reminder R30: teacher list/detail are scoped server-side; never accept an employee
    id as proof of access.
- **Phase 9 (19 Nov 2026):** notifications, reminders, badges, cards.
  - Submit notifies `course.approve` holders per version; approve/reject notify submitter
    (Phase 7); all use `notification.dedupe_key`.
  - Scheduler job `course.reminders` nudges finished weeks with no Submitted/Approved plan
    to the current teacher (current month, dedupe per section-week).
  - `/course/summary`, `/course/sections/{id}/summary`; Classroom card gets
    `pendingApprovals`; Teachers Course tab stat tiles + row badges.
  - Tests: 7/7 teacher-tab+Phase9; regression 39/39; frontend 18/18; tsc + ruff clean.
  - New reminder R31: approvers are role-grant resolved; notification and reminder keys
    are version/week scoped.
  - Optional 9.5 principal overview skipped pending user confirmation.
- **Phase 10 (19 Nov 2026):** final integration + hardening.
  - E2E test follows master/custom subject → assignment → chapters/tick → 2 submits →
    approve/reject/resubmit/approve → handover → Classroom/Teachers/summary equality →
    notifications → second school `404`.
  - Migration contract test pins single head, parent and downgrade. Live DB verified at
    `e2b8c4f7a1d9 (head)`: tables, columns and indexes present; `alembic upgrade head` is
    a no-op. Pre-migration dump saved under `backend/backups/` (git-ignored). Backend
    image rebuilt and healthy. Offline `--sql` still cannot inspect, and `alembic check`
    reports pre-existing repo drift outside Course.
  - Full Course + permission matrix + classroom regression = 82/82; frontend 18/18;
    tsc + ruff clean.
  - Exit notes: Parent/Student approved-weeks view future; HOD department scope future;
    section_course query-count optimization backlog; 9.5 overview optional.
  - New reminder R32: migration needs the live DB; single-head contract is in tests.


