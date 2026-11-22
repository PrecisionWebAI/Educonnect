# Classroom-Owned Subjects — Implementation Plan

> **Status:** Phases 1–4 code complete — 22 Nov 2026; M1 + M2 + M3 + M4 live DB par
> pending (backup + explicit approval). Phase 1 aur 2 ek hi shipment hain; Phase 5 agla.
> **Replaces:** purana Global Academic Year plan. Woh kaam complete ho chuka hai.
> **Source of truth:** `classroomsubject` — ek subject sirf ek classroom (school +
> class + section) ka hota hai, ek academic year ke liye.
> **Language:** Yeh file Hinglish mein hai. Code, table/column names, API names,
> UI labels English mein.
> **Naming:** Domain word **classroom subject** hai. Code mein `ClassroomSubject`,
> `classroom_subject_id`; API mein `/course/subjects/{id}`; UI mein `Subject`.
> Global `Subject` master ka koi naya naam nahi banega — usse Phase 5 mein drop karna hai.

---

## 0. Kaam kaise chalega

### 0.1 Phase discipline

- Har phase shuru karne se pehle: us phase ke subphases dobara padho, `phase2.md`
  ke reminders padho, aur current code us phase ke hisaab se deeply dekho.
- Purani phases mein bana hua code todna nahi hai.
- Har phase ke baad is file mein: checkbox `[x]`, aur Section 8 mein completion
  entry (kya kiya, files, tables/endpoints/components, tests, baaki, `phase2.md`
  mein kya add kiya).
- Ek phase khatam hone par summary do aur **ruko**. Agla phase sirf user ke
  “next phase” ke baad.
- **Phase 0 mein sirf plan/schema review hota hai; product code change nahi.**
- Har phase se pehle us phase ka deep plan dobara likho; bina deep plan code na
  likho.

### 0.2 Loop aur terminal rules

- Sirf synchronous, khud khatam hone wali commands. Dev server / watch mode
  foreground mein nahi. Server chahiye to short-lived command ya timeout.
- Ek hi error par maximum 2 fix attempts; phir ruk kar error + analysis user ko
  batao.
- Lambe output ko filter karo (`Select-Object -First/-Last`, `Select-String`).
- Destructive command (drop/delete/force reset) user ko bataye bina nahi.
- Migration se pehle database backup; migration ke baad row counts verify.
- Live/production DB par destructive step sirf explicit approval ke baad.

### 0.3 Testing rules

- Sirf us phase se juda test: us phase ka endpoint/table/component/migration.
- Poora suite nahi. Phase 5 mein hi poora subject redesign end-to-end test.
- Har schema change ke saath migration test: upgrade, downgrade (jahan possible
  ho), backfill, unique key, orphan check.
- Har phase ke baad kam se kam: backend `ruff`, us phase ke `pytest`, frontend
  `tsc --noEmit`, affected `node --test`, `eslint`/Prettier jahan project mein
  configured ho.
- Test data do schools ka ho, taaki tenant isolation pakda jaye.

### 0.4 Language aur naming

- `phase3.md` Hinglish; baaki code, comments, API, UI labels English.
- Ek hi domain word: **classroom subject**. `subject` sirf tab jab generic UI
  label ho; DB/API field `classroom_subject_id`.
- DB: `classroomsubject`, `classroom_subject_id`; API: `/course/subjects/{id}`;
  frontend: `CourseSubject`, `ClassroomSubjectRow`; tests: `test_classroom_subject*`.
- UI labels proper case. Subject names Title Case mein render honge.
- `Title Case` frontend helper se; DB mein stored case se UI nahi badlegi.

### 0.5 Design aur codebase consistency

- Frontend: maujooda components/styles/spacing/tables/popups/tabs/badges/empty
  states reuse. Naya design system ya UI library nahi.
- Backend: existing router → service → repository pattern, auth dependency,
  `school_id` scoping, error format, pagination style (`X-Total-Count`), audit
  logging, alembic migrations.
- Existing `role` / `permission` / `rolepermission` / `user_role` reuse. Naya
  parallel permission system nahi.
- Naya code purane naam ko copy nahi karega; migration ke saath rename aur tests
  update honge.
- `classroomsubject` ka create/rename/archive/restore **ek hi service** se hoga:
  `course/subjects.py`. Koi router, seed, exam, homework ya teacher module direct
  subject row create/update nahi karega.

### 0.6 Production aur scalability mindset

- Sab kuch per school, per classroom section, per academic year.
- Har naye table mein `school_id` (DB NOT NULL), sahi FKs, indexes, unique
  constraints.
- N+1 nahi. Lists paginated. Counts (completion %, pending approvals) SQL
  aggregate se.
- `section_course` jaisi screen fixed number of queries se bane; per-subject ya
  per-chapter query loop nahi.
- Approve/Submit/rename/archive transaction mein + idempotent. Do users ek hi
  subject rename ya duplicate add karein to unique index race ko rokega.
- Permission server par enforce; button chhupana kaafi nahi.
- School A ka data School B ko kabhi na dikhe.
- Subject name duplicate check case-insensitive + whitespace-normalised hoga.
- Archived row naya same-name add nahi rokegi; active partial unique index.
- Cross-class subject roll-up nahi banega. Reports classroom subject ke hisaab se
  scoped honge, naam ke hisaab se school-wide group nahi.

---

## 1. Product Rules (final, agreed)

1. **No fixed/global subject table.** Har classroom ki apni subject list hogi.
2. Same subject name different classrooms mein allowed — Nursery A aur Nursery B
   dono “Computer Science” rakh sakte hain.
3. Rename sirf usi classroom subject ka `name` badlega. Doosri classrooms
   untouched.
4. Ek classroom + academic year mein do **Active** subjects ka same name
   case-insensitive allowed nahi. Duplicate `409`.
5. Subject names UI mein Title Case.
6. Names per classroom free hain (“English 1” vs “English Literature”). Different
   classrooms ke subjects ke beech koi grouping/linking nahi. Sirf exam paper
   group exception hai, jo papers ko jodta hai — subjects ko nahi.
7. School-wide ya cross-class subject-by-name roll-up nahi.
8. Koi bhi teacher kisi bhi classroom subject ko padha sakta hai. Qualification
   hard restriction nahi; sirf optional ranking/suggestion.
9. Archived subject apne chapters, lesson plans, timetable, homework, exam papers
   aur history ke saath rehta hai; naya same-name subject add ho sakta hai.
10. Chapter bhi classroom subject ka hoga, class-level nahi. Same class ke do
    sections ke chapters independent honge; copy action optional convenience hai.
11. `exam` class/section event rahega; subject `exam_paper` par hoga. School exam
    ke liye har section ka apna paper row banega.
12. Shared question paper `exam_paper_group` se judega; group optional hoga.
13. Marks hamesha section ke apne `exam_paper` row se judenge.

---

## 2. Final Data Model

### 2.1 `classroomsubject` (single source of truth)

Columns:

| Column | Rule |
|---|---|
| `id` | UUID PK |
| `school_id` | NOT NULL, FK `school.id` |
| `classroom_id` | NOT NULL, FK `classroom.id` |
| `academic_year_id` | NOT NULL, FK `academic_year.id` |
| `name` | varchar(120), NOT NULL, trimmed + collapsed spaces |
| `code` | varchar(20), NULL (optional convenience only) |
| `status` | `Active` / `Archived`, NOT NULL |
| `created_by_user_id` | FK `app_user.id`, NULL |
| `archived_at` | timestamp, NULL |
| `archived_by_user_id` | FK `app_user.id`, NULL |
| `created_at` | timestamp, NOT NULL |
| `updated_at` | timestamp, NOT NULL |

Constraints/indexes:

```text
PARTIAL UNIQUE INDEX uq_classroomsubject_active_name
  ON classroomsubject (
    classroom_id,
    academic_year_id,
    lower(btrim(regexp_replace(name, '\s+', ' ', 'g')))
  )
  WHERE status = 'Active';

INDEX ix_classroomsubject_school_classroom_year
  ON classroomsubject (school_id, classroom_id, academic_year_id);

CHECK status IN ('Active', 'Archived');
```

- `subject_id` **nahi** hoga. Legacy `subject_id` sirf migration ke beech tak
  rahega, Phase 5 mein drop.
- Archived row same-name add nahi rokegi. Restore karte waqt agar active
  duplicate hai to `409`.
- Naam store normalized (trim + collapse) hoga. Case compare `lower()` se; UI
  `titleCase()` se render karega.

### 2.2 `subjectteacher` (history only)

```text
id, school_id, classroom_subject_id NOT NULL, teacher_id NOT NULL,
effective_from date NOT NULL, effective_to date NULL
```

- Legacy `classroom_id`, `subject_id`, unke indexes/constraints **drop**.
- `UNIQUE (classroom_subject_id, effective_from)`.
- Partial unique: ek open row per classroom subject:
  `WHERE effective_to IS NULL`.
- Teacher badalne par purani row ka `effective_to` set, nayi open row.
- Qualification match **hard filter nahi**; service sirf optional ranking hint
  de sakta hai.

### 2.3 `chapter` (classroom-subject-owned)

```text
id, school_id, classroom_subject_id NOT NULL,
sequence int NOT NULL, name, planned_date,
status, completed_on, completed_by_employee_id,
created_at, updated_at
```

- `UNIQUE (classroom_subject_id, sequence)`.
- `chapterprogress` **retire** hoga (recommended): progress ek hi chapter row par
  rahega, kyunki chapter already ek section ka hai. Isse duplicate
  `classroom_id` aur mismatch ka risk khatam.
- Agar aap minimal-churn alternative chahte hain to `chapterprogress` bach sakta
  hai, lekin tab `UNIQUE(chapter_id)` + `chapter.classroom_subject_id` ka match
  DB/service dono par enforce karna padega. **Recommendation: merge.**
- Existing class-level chapter ko migration mein section-wise copy kiya jayega;
  `exam_paper_chapter` ke purane links preserve honge.

### 2.4 `timetableperiod`, `homeworkassignment`, `attendancerecord`, `classlog`

| Table | Final change |
|---|---|
| `timetableperiod` | `subject_id` → `classroom_subject_id NOT NULL`; `classroom_id` retained for slot/class queries; service validates match. |
| `homeworkassignment` | `subject_id` → `classroom_subject_id NOT NULL`; `classroom_id` retained; service validates match. |
| `attendancerecord` | `subject_id` → `classroom_subject_id` nullable; day-level row still `NULL`; unique keys updated. |
| `classlog` | `subject_id` → `classroom_subject_id` nullable; day-level row still `NULL`. |

- `attendance` unique:
  `(school_id, student_id, date, classroom_subject_id)` plus partial day-level
  unique `(school_id, student_id, date) WHERE classroom_subject_id IS NULL`.
- `classroom_id` duplicate column ko drop nahi karenge jahan existing queries
  usi par filter karti hain; service `classroom_subject.classroom_id` se match
  enforce karega. Isse query simple rehti hai aur galat section ka link `422`.

### 2.5 Exams: `exam`, `exam_paper`, `exam_paper_group`

`exam` table **same rahega**: event/class/classroom/scope/status. Exam par subject
nahi hoga.

`exam_paper` final:

```text
id, school_id, exam_id NOT NULL, classroom_subject_id NOT NULL,
paper_group_id NULL, exam_date, start_time, end_time,
max_marks, passing_marks, room, note, published_at
```

- `UNIQUE (exam_id, classroom_subject_id)` — ek exam mein ek section-subject ka
  ek hi paper.
- `class_id` aur `subject_id` **drop**. Class `classroom_subject -> classroom ->
  class` se derive hoga.
- Date, time, room, max/passing marks per section paper par rahenge.

`exam_paper_group` (shared question paper):

```text
id, school_id, exam_id NOT NULL, display_title NULL,
locked_at NULL, locked_by_user_id NULL, created_by_user_id,
created_at, updated_at
```

- Same question paper wale section papers ek group mein honge.
- `display_title` optional: question paper/datesheet par group title; na ho to
  har row apna classroom subject name dikhaye.
- Group subjects ko link nahi karta; sirf paper rows ko.

### 2.6 `exam_paper_group_chapter` and `exam_paper_chapter`

Chapter IDs section-owned hain, isliye group ke chapters IDs se bind nahi honge:

```text
exam_paper_group_chapter:
  id, school_id, paper_group_id NOT NULL,
  sequence int NOT NULL, name varchar NOT NULL,
  UNIQUE (paper_group_id, sequence)
```

- Group chapter list ek baar set hoti hai; group ke saare paper rows wahi list
  dikhate hain.
- `exam_paper_chapter` sirf **detached/independent paper** ke liye:
  `(exam_paper_id, chapter_id)` with real FK to that section's `chapter`.
- Detach karte waqt group chapter names ko target section ke chapters se
  name/sequence match karke `exam_paper_chapter` rows banaye jayenge. Match na
  mile to detach `409` with the missing chapter names — silently guess nahi.

### 2.7 `marks`

Recommended final shape:

```text
id, school_id, exam_paper_id NOT NULL, student_id NOT NULL,
marks_obtained numeric(6,2) NULL, is_absent bool NOT NULL,
grade NULL, entered_by, created_at
UNIQUE (exam_paper_id, student_id)
```

- `subject_id` aur `exam_id` **drop**: dono paper se derive hote hain. Isse
  “mark ka subject paper se alag ho gaya” wala state impossible ho jata hai.
- Agar aap legacy `exam_id` query compatibility chahte hain to Phase 3 tak
  temporary column rakh sakte hain, lekin final model mein nahi.

### 2.8 `paperdraft`, `examsource`, `questionusagelog`

`paperdraft`:

```text
classroom_subject_id NOT NULL (replaces subject_id/class_id/section_id),
paper_group_id NULL, exam_paper_id NULL,
class_name, subject (free-text AI prompt snapshot), ...
```

- Group draft: `paper_group_id` set, group ke saare papers same question paper
  use karte hain.
- Independent paper draft: `exam_paper_id` set, group NULL.
- Dono NULL allowed jab draft exam se pehle bana ho.
- `paper_group_id` unique (ek group ka ek live draft), `exam_paper_id` unique.

`examsource`:

- `subject_id` → `classroom_subject_id` nullable.
- `subject` free-text snapshot remains (AI/RAG filter ke liye).
- `class_id` free-text/legacy mapping phase 5 mein drop; source library
  classroom subject se scoped hogi.

`questionusagelog`:

- `classroom_subject_id` nullable add.
- `subject` free-text remains for old rows; naya code classroom subject se
  filter karega.

### 2.9 People and hiring

`employee`:

- Add `subject_tags varchar(500) NULL` — simple informational text, e.g.
  `"English, Maths"`.
- `teachersubject` table **drop**.
- `pipeline_hiring_table.subject_id` **drop**; `subject_name` free text remains.
- `school_setting` key `hiring.subject_suggestions` — comma/JSON list, only
  convenience dropdown. Kisi subject table se link nahi.
- Subject teacher assignment kisi bhi active teacher ko allowed; `teachersubject`
  qualification gate nahi.

---

## 3. Phase 0 Impact Audit (every subject touch-point)

### 3.1 Backend — subject master, course and classroom

| Area | Files | What must change |
|---|---|---|
| Global subject master | `backend/app/domains/academic/classroom/academics/models.py`, `repository.py`, `router.py`, `schemas.py`, `service.py`, `seed.py`, `__init__.py` | `Subject`/`SubjectBase` remove; `SubjectTeacher`, `Chapter` relocate/repoint; `get_subjects`, `create_subject`, `update_subject`, `/academics/subjects` endpoints delete; boot seed ke 13 subjects delete. |
| Course model/service | `backend/app/domains/academic/classroom/course/models.py`, `service.py`, `schemas.py`, `router.py` | `ClassroomSubject.subject_id` → `name`; add rename; remove `available_subjects`; chapter CRUD per classroom subject; copy chapters; title/display name; all `Subject` joins removed. |
| Course supporting | `course/completion.py`, `course/scope.py`, `course/teacher_course.py`, `course/approvals.py`, `course/lesson_plans.py`, `course/reminders.py` | Completion counts by `classroom_subject_id`; permission scope by classroom subject; teacher course rows; review/reminder subject labels. |
| Classroom hub | `backend/app/domains/academic/classroom/repository.py`, `service.py`, `router.py`, `schemas.py` | `get_subject_rows` ab school-wide nahi, section ke active classroom subjects; timetable/homework/marks joins; legacy assignment route; `SubjectTeacherRow`/`SectionMarkSubjectRead` fields. |

### 3.2 Backend — timetable, homework, attendance

| Area | Files | What must change |
|---|---|---|
| Timetable | `backend/app/domains/academic/classroom/timetable/models.py`, `schemas.py`, `service.py`, `repository.py` | `subject_id` → `classroom_subject_id`; validate subject belongs to section/year; joins/read names; clash queries unchanged. |
| Homework | `backend/app/domains/academic/classroom/homework/models.py`, `schemas.py`, `service.py`, `repository.py`, `router.py` | `subject_id` → `classroom_subject_id`; teacher/assignment validation; list joins; class log subject. |
| Attendance | `backend/app/domains/academic/classroom/attendance/models.py`, `schemas.py`, `service.py`, `repository.py`, `router.py`, `register.py` | `subject_id` → nullable `classroom_subject_id`; new unique keys; register subject rows; history. |

### 3.3 Backend — exams and AI paper builder

| Area | Files | What must change |
|---|---|---|
| Exam models | `backend/app/domains/academic/classroom/exams/models.py` | `Exam` unchanged; `ExamPaper` → `classroom_subject_id` + `paper_group_id`; new `ExamPaperGroup`/`ExamPaperGroupChapter`; `Marks` drop subject/exam redundancy; `PaperDraft`/`ExamSource`/`QuestionUsageLog` repoint. |
| Exam plan | `backend/app/domains/academic/classroom/exams/plan/service.py`, `schemas.py`, `router.py` | Per-section paper creation; group create/detach/lock; subject names from classroom subject; marks/results through paper; school-exam expansion. |
| AI paper builder | `backend/app/domains/academic/classroom/exams/service.py`, `schemas.py`, `repository.py`, `router.py` | Draft/source contracts; `subject_id` → `classroom_subject_id`; group draft link; free-text snapshots. |
| RAG/LLM | `backend/app/domains/academic/classroom/exams/llm/prompts.py`, `llm/services.py`, `rag/ingest.py`, `rag/retriever.py`, `rag/store.py`, `rag/usage.py` | Prompt/filter metadata classroom subject id; no global subject name roll-up. Free-text `subject` old rows ke liye. |

### 3.4 Backend — people, auth, dashboard, hiring

| Area | Files | What must change |
|---|---|---|
| Teacher profiles | `backend/app/domains/people/teachers/models.py`, `service.py`, `schemas.py`, `profile/service.py`, `profile/router.py`, `profile/schemas.py` | `TeacherSubject` drop; `employee.subject_tags`; `/subjects` → `/subject-tags`; list/detail field; staff re-hire copy. |
| Staff/people | `backend/app/domains/people/staff/models.py`, `schemas.py`, `service.py`, `lifecycle.py` | `subject_ids` → `subject_tags`; hire form; profile read; lifecycle clone. |
| Substitution/workload/performance | `backend/app/domains/people/teachers/substitution/engine.py`, `repository.py`, `service.py`, `schemas.py`; `workload/repository.py`, `service.py`; `performance/service.py` | Candidate pool all active teachers; remove `teachersubject` hard gate; names/joins via classroom subject; per-classroom performance. |
| Auth scope | `backend/app/domains/auth/service.py` | `is_teacher_assigned_to_subject` → `classroom_subject_id`; `can_teach_subject` callers; scope joins `SubjectTeacher`. |
| Dashboard | `backend/app/domains/main/dashboard/service.py`, `router.py`, `schemas.py` | `subject_perf` ko classroom-scoped karo; school-wide by-name roll-up remove; timetable/homework names. |
| Hiring | `backend/app/domains/operations/staff_hiring/models.py`, `schemas.py` | `subject_id` drop; `subject_name` free text; suggestions from `school_setting`. |

### 3.5 API contracts that change

| Old | New |
|---|---|
| `GET /academics/subjects` | **delete** |
| `POST /academics/subjects` | **delete** |
| `PATCH /academics/subjects/{id}` | **delete** |
| `GET /classroom/sections/{id}/available-subjects` | **delete** (no fixed dropdown) |
| `POST /classroom/sections/{id}/subjects` body `{subject_id,name}` | body `{name, code?}` only |
| — | `PATCH /course/subjects/{id}` body `{name, code?}` (rename one classroom subject) |
| `PATCH /course/subjects/{id}/archive` | same path, response `classroom_subject_id/name/status` |
| `PATCH /course/subjects/{id}/restore` | same path; active duplicate → `409` |
| `DELETE /course/subjects/{id}` | same; dependency checks by new FKs |
| `GET /classroom/sections/{id}/course` | `CourseSubject.subject_id` remove; `name`, `status`, `canRename`, `canCopyChapters` add |
| `GET/POST /course/subjects/{id}/chapters` | same path; response `classroom_subject_id`; chapter list section-owned |
| `PATCH/DELETE /course/chapters/{id}` | same; ownership check via classroom subject |
| — | `POST /course/subjects/{id}/chapters/copy` body `{source_classroom_subject_id}` |
| `PUT /classroom/sections/{section_id}/subjects/{subject_id}/teacher` | `PUT /course/subjects/{classroom_subject_id}/teacher` only; legacy route delete |
| Timetable create/update | body `{classroom_subject_id}`; validate section/year |
| Homework create | body `{classroom_subject_id}`; validate section |
| Attendance/class log | body `{classroom_subject_id?}` where subject-specific |
| `POST /exams` school/class papers | per-section expansion; body selects class/sections + subject scope; response paper rows |
| `PATCH /exams/{id}` date sheet | keys by `classroom_subject_id` |
| — | `POST /exams/paper-groups/{group_id}/papers/{paper_id}/detach` |
| — | `PATCH /exams/paper-groups/{group_id}` group title/chapters/max marks (lock-aware) |
| Marks save/change | by `paper_id` (unchanged path); server writes `exam_paper_id` only |
| `PUT /teachers/profile/{id}/subjects` | `PUT /teachers/profile/{id}/subject-tags` body `{subject_tags}` |
| Staff hire form | `subject_ids` → `subject_tags`; old `subject_id` removed |
| Hiring interview | `subject_id` removed; `subject_name` free text |
| Dashboard `GET /dashboard/subject-perf` | classroom-scoped response; no by-name school roll-up |

### 3.6 Frontend components/services/types

| Area | Files |
|---|---|
| Course | `frontend/src/components/features/classroom/course/AddSubjectDialog.tsx`, `CoursePanel.tsx`, `CourseTable.tsx`, `SubjectMasterDialog.tsx` (**delete**), `ChapterEditorDialog.tsx`, `chapter-columns.tsx`, `CourseBar.tsx`, `CourseCompletionCard.tsx`, `TeacherAssignDialog.tsx`, `TeacherHistoryDialog.tsx`, `WeeklyLessonPlanDialog.tsx`, `LessonPlanReviewPanel.tsx` |
| Classroom | `frontend/src/components/features/classroom/SectionDetailPage.tsx`, `MyClasses.tsx`, `LessonPlan.tsx` |
| Timetable | `frontend/src/components/features/classroom/timetable/TimetablePanel.tsx`, `frontend/src/components/features/timetable/TimetablePage.tsx` |
| Homework | `frontend/src/components/features/classroom/homework/AssignHomework.tsx`, `WriteDailyLog.tsx`, `HomeworkPanel.tsx`, `ClassDiary.tsx`, `SubmissionsReview.tsx`, `HomeworkPage.tsx`, `useHomework.ts` |
| Exams plan | `frontend/src/components/features/classroom/exam-plan/ExamScheduleForm.tsx`, `ExamsPlanPanel.tsx`, `DateSheet.tsx`, `MarksGrid.tsx`, `ResultsView.tsx`, `useExamPlan.ts` |
| AI papers | `frontend/src/components/features/classroom/exams/ExamsPanel.tsx`, `frontend/src/components/features/exams/paper-builder/PaperBuilder.tsx`, `BasicsStep.tsx`, `SourceStep.tsx`, `GenerateStep.tsx`, `usePaperBuilder.ts`, `useSourceMaster.ts` |
| Teachers | `frontend/src/components/features/teachers/CourseTab.tsx`, `TeacherCourseDetail.tsx`, `StaffProfileSheet.tsx`, `StaffListTable.tsx`, `StaffWeekSheet.tsx`, `SubstitutionTab.tsx`, `WorkloadMatrixTable.tsx`, `MyStaffPanel.tsx`, `TeachersPage.tsx` |
| Staff hiring | `frontend/src/components/features/staff-hiring/StaffHiringPage.tsx`, `InterviewFormModal.tsx`, `StaffRegistrationForm.tsx`, `HiringCandidatesTable.tsx`, `useStaffHiring.ts` |
| Academics/attendance | `frontend/src/components/features/classroom/academics/AcademicsPage.tsx`, `GradebookTab.tsx`, `MarksEntryTab.tsx`, `useAcademics.ts`; `frontend/src/components/features/classroom/attendance/StudentHistoryDialog.tsx` |
| Dashboards | `frontend/src/components/features/dashboard/DashboardFeeds.tsx`, `TeacherDashboard.tsx`, `StudentDashboard.tsx`, `ParentDashboard.tsx`, `HodDashboard.tsx` |
| Services | `frontend/src/services/academics.service.ts`, `course.service.ts`, `attendance.service.ts`, `dashboard.service.ts`, `exam-builder.service.ts`, `exams-plan.service.ts`, `hiring.service.ts`, `homework.service.ts`, `operations.service.ts`, `staff.service.ts`, `teachers.service.ts`, `timetable.service.ts` |
| Types/helpers | `frontend/src/types/index.ts`, `frontend/src/types/exam-builder.ts`, `frontend/src/lib/course/view.ts`, `frontend/src/lib/course/lesson-plan.ts`, `frontend/src/lib/course/view.test.ts`, `frontend/src/lib/exams/view.ts`, `frontend/src/lib/exams/view.test.ts`, `frontend/src/lib/homework/view.ts`, `frontend/src/lib/homework/view.test.ts`, `frontend/src/lib/timetable/view.ts`, `frontend/src/lib/timetable/view.test.ts`, `frontend/src/lib/format.ts` |

### 3.7 Migrations and tests touched

- New migration parent: `e5a7b9c1d3f4` (current head). Purani migrations edit
  nahi hongi; unka historical meaning preserve rahega.
- `backend/alembic/versions/<new>_classroom_owned_subjects.py` — M1.
- `backend/alembic/versions/<new>_subject_curriculum_repoint.py` — M2.
- `backend/alembic/versions/<new>_subject_exam_papers.py` — M3.
- `backend/alembic/versions/<new>_subject_people_cleanup.py` — M4.
- `backend/alembic/versions/<new>_drop_global_subject.py` — M5.
- `backend/tests/test_phase3_migration.py` — head pin update.
- `backend/tests/test_course_migration.py` — old revision expectations remove/update.
- New: `backend/tests/test_classroom_subjects.py`,
  `backend/tests/test_classroom_chapters.py`,
  `backend/tests/test_subject_migration.py`,
  `backend/tests/test_exam_paper_groups.py`,
  `backend/tests/test_subject_tenant_scope.py`.

Existing test files that will need rewrite/update:

`test_course_subjects.py`, `test_course_chapters.py`, `test_course_lesson_plans.py`,
`test_course_approvals.py`, `test_course_teachers.py`, `test_course_teacher_tab.py`,
`test_course_end_to_end.py`, `test_course_permissions.py`, `test_course_schema.py`,
`test_classroom_course.py`, `test_classroom_timetable.py`,
`test_classroom_homework.py`, `test_classroom_attendance.py`,
`test_classroom_exams.py`, `test_phase1_schema.py`, `test_phase2_schema.py`,
`test_phase7_definition_of_done.py`, `test_phase10_end_to_end.py`,
`test_exams_source_index.py`, `test_staff_profile.py`, `test_staff_self_view.py`,
`test_staff_substitution.py`, `test_staff_workload.py`,
`test_assignments.py`, `test_people_contracts.py`, `test_phase3_teachers_split.py`,
`test_communications_authorization.py`, `test_academic_year_scope_contract.py`.

### 3.8 Explicitly excluded (not domain subject)

`chat.message.subject`, ticket `subject`, notification subject, email subject aur
unke frontend components (chat/tickets) **is redesign ka hissa nahi** — woh
generic message fields hain, academic subject nahi.

### 3.9 Risk register

| Risk | Mitigation |
|---|---|
| 58 files ek saath badalna | Phase-wise split; har phase ke baad focused tests. |
| Chapter IDs section-wise duplicate | Old canonical row preserve; copies for other sections; mapping temp table. |
| Exam papers class-level se section-level | Group table + one paper per section; marks mapped by student's section. |
| Shared paper chapters vs section chapter IDs | Group chapter snapshot; detached paper uses real FK. |
| Archived duplicate restore | Service active-duplicate check; DB partial unique. |
| `subject` table drop se old reports tootna | Dashboard/report queries Phase 4 mein classroom-scoped; final drop Phase 5. |
| Tenant leak | Har service query `school_id`; two-school tests. |
| N+1 in Course/Exam | One query per list; aggregates SQL; query count test. |
| Downgrade after drop | M1–M4 reversible; M5 explicitly irreversible. |

---

## 4. Migration Plan (proper Alembic, staged)

> Parent revision: `e5a7b9c1d3f4`.
> Har migration idempotent guards ke saath; `op.get_bind()` dialect-aware.
> Har step ke baad row counts + FK orphan check. Destructive steps Phase 5 only.
>
> **Hard rules (M1–M5):**
> 1. Har migration se pehle full database backup lo (timestamped dump +
>    restore check). Backup path aur size completion log mein likho.
> 2. **Koi migration naya `classroomsubject` row create nahi karega.** Sirf
>    already-existing classroom subject par map hoga.
> 3. Jo old row kisi existing `classroomsubject` par map na ho, woh orphan report
>    mein aayega aur migration **abort** karega. Silent drop ya auto-create nahi.
> 4. Har migration ke baad before/after count report; unexplained difference par
>    abort. Marks ka count exact match hoga; chapter/exam_paper ka expected
>    expansion count compare hoga; timetable/homework/attendance ka mapped count
>    exact match hoga.

### M1 — `classroom_owned_subjects`

0. **Backup:** full DB dump + restore check. No `classroomsubject` insert/update
   beyond the three identity columns below.
1. `classroomsubject` mein `name` (nullable), `code` (nullable), `updated_at`
   add.
2. `name = subject.name`, `code = subject.code` — existing `subject_id` join se.
3. Duplicate audit:
   ```sql
   SELECT classroom_id, academic_year_id,
          lower(btrim(regexp_replace(name, '\s+', ' ', 'g'))) AS key,
          array_agg(id) AS ids
   FROM classroomsubject
   WHERE status = 'Active'
   GROUP BY 1,2,3 HAVING count(*) > 1;
   ```
   Koi row mile to migration **abort** with the exact list. Automatic rename
   nahi.
4. `name` NOT NULL.
5. Partial unique active-name index create.
6. `(school_id, classroom_id, academic_year_id)` index create.
7. Legacy unique `(classroom_id, subject_id, academic_year_id)` retain (subject_id
   Phase 5 tak).
8. `classroomsubject.subject_id` nullable banao (naye rows bina master ke).

**Downgrade:** index + columns drop; old unique stays. Data loss only new names.
Working.

### M2 — `subject_curriculum_repoint`

0. **Backup:** full DB dump + restore check. Snapshot counts for `subjectteacher`,
   `chapter`, `chapterprogress`, `timetableperiod`, `homeworkassignment`,
   `attendancerecord`, `classlog`. No `classroomsubject` insert.
1. `subjectteacher`:
   - `classroom_subject_id` add; backfill only by an **existing**
     `(classroom_id, subject_id, academic_year_id)` `classroomsubject` row.
     `academic_year_id` NULL ho to current academic year ki existing row se
     match karo; multiple/no match → orphan report + abort.
   - Koi `classroomsubject` create nahi. Missing mapping → orphan report +
     migration abort.
   - New unique `(classroom_subject_id, effective_from)` + partial open-row
     index.
   - Legacy columns/indexes Phase 5 tak retain.
2. `chapter`:
   - `classroom_subject_id` add.
   - Har old class-level chapter ke liye target sections = **sirf woh sections
     jinke paas us subject ka already-existing `classroomsubject` row hai**.
   - **Koi naya `classroomsubject` create nahi.** Jinke paas row nahi hai woh
     `skipped_sections` report mein aayenge; unke liye chapter copy nahi hogi.
   - Agar target sections empty hain → old chapter orphan report mein aayega aur
     migration abort karega.
   - Canonical row preserve: old chapter id ko pehle eligible section ka chapter
     banao; baaki eligible sections ke liye copy insert.
   - `chapterprogress` merge: sirf eligible target chapter par `status`,
     `completed_on`, `completed_by_employee_id` copy. Jis progress ka classroom
     eligible nahi, woh orphan report + abort.
   - `chapterprogress` rows temp mapping ke baad Phase 5 mein drop.
   - New unique `(classroom_subject_id, sequence)`.
3. `timetableperiod`, `homeworkassignment`, `attendancerecord`, `classlog`:
   - `classroom_subject_id` add.
   - Backfill only by an **existing** `(classroom_id, subject_id,
     academic_year_id)` `classroomsubject` row; year NULL ho to current academic
     year ki existing row se match karo.
   - **Koi `classroomsubject` create nahi.** Multiple/no match ya missing mapping
     → orphan report + abort; silently NULL nahi.
   - FK + index add.
4. Attendance ke naye unique/partial indexes banao (old keys Phase 5 tak).
5. Orphan report: koi old row jiska classroom subject resolve na ho to migration
   abort. Report mein table, row id, classroom_id, subject_id, academic_year_id
   aur reason likho.
6. **Verification gate — M2:**
   - `chapter`: `before` = old class chapters; `after` = canonical chapters +
     copies in eligible sections. Expected count report; unexplained difference →
     abort.
   - `chapterprogress`: every old row mapped to an eligible target chapter;
     skipped/orphan rows report + abort.
   - `timetableperiod`, `homeworkassignment`, `attendancerecord`, `classlog`:
     mapped counts exact match; no row silently dropped or duplicated.
   - `classroomsubject` before/after count **exact match** — M2 zero rows create
     karta hai.
7. Report har table ka `before`, `expected_after`, `actual_after`, `delta`,
   `skipped_sections`, `orphans`. Difference ho to migration abort.

**Downgrade:** new columns/indexes drop; old columns retained. Chapter copies
reverse karna lossy hai (same class/subject/name mapping se best-effort), isliye
downgrade se pehle backup mandatory.

### M3 — `subject_exam_papers`

0. **Backup:** full DB dump + restore check. Snapshot counts for `chapter`,
   `exam_paper`, `exam_paper_chapter`, `marks`, `timetableperiod`,
   `homeworkassignment`, `attendancerecord`; save report path. No
   `classroomsubject` insert.
1. `exam_paper_group`, `exam_paper_group_chapter` create.
2. `exam_paper` mein `classroom_subject_id`, `paper_group_id` add.
3. Har old `exam_paper` (class + subject) ke liye:
   - Class ke sections load karo, lekin target sections = **sirf woh sections
     jinke paas us subject ka already-existing `classroomsubject` row hai**.
   - **Koi naya `classroomsubject` create nahi.** Missing subject wale sections
     `skipped_sections` report mein aayenge; unke liye paper row nahi banegi.
   - Agar target sections empty hain → old paper orphan report mein aayega aur
     migration abort karega.
   - Ek `exam_paper_group` banao (agar >1 target section) with
     `display_title` = old `subject.name`.
   - Old paper row ko canonical eligible section ka paper banao; baaki eligible
     sections ke liye naye paper rows insert.
   - Har group ke liye `exam_paper_group_chapter` rows old
     `exam_paper_chapter` + `chapter` names se banao.
4. `marks` — section **enrollment se** resolve karo, `student.classroom_id` se
   kabhi nahi:
   - Exam ka `academic_year_id` lo. NULL ho to us exam ke marks map nahi honge;
     orphan report + abort (current year guess nahi).
   - Har mark ke `student_id` ke liye:
     `Enrollment.student_id == mark.student_id AND
     Enrollment.academic_year_id == exam.academic_year_id`.
   - `enrollment.classroom_id` hi us waqt ka section hai. Us section ke naye
     paper se `exam_paper_id` match karo.
   - Enrollment missing, ya us section ke paas subject ka paper nahi → orphan
     report + abort. `student.classroom_id` fallback **nahi**.
   - `exam_id`/`subject_id` temporary retain; `exam_paper_id` NOT NULL banao.
5. `paperdraft`:
   - `classroom_subject_id` add + backfill only from an existing section/subject
     `classroomsubject`; no create.
   - `paper_group_id`/`exam_paper_id` add nullable.
   - Orphan draft report karo + abort; no silent discard.
6. `examsource`/`questionusagelog`:
   - `classroom_subject_id` add + backfill only where an existing
     section/subject/year match is unambiguous; no create.
   - Ambiguous/missing match → orphan report + abort.
   - Free-text `subject` retain.
7. New indexes/FKs.
8. **Verification gate — M3:**
   - `marks`: before count must equal after count **exactly**. Koi bhi
     difference → explicit row report + abort.
   - `chapter`: before count = source rows; after count = source rows mapped to
     eligible sections. `expected_after` report karo; actual != expected → abort.
   - `exam_paper`: before count = old class papers; after count = section papers
     created for eligible sections. `expected_after` report; actual != expected →
     abort.
   - `timetableperiod`, `homeworkassignment`, `attendancerecord`: mapped row
     count exact match; koi row drop/duplicate nahi.
   - Report har table ka `before`, `expected_after`, `actual_after`, `delta`,
     `skipped_sections`, `orphans`. Difference ho to migration abort, never
     “fix later”.
9. **Migration test:** ek student jo exam ke baad promote hua —
   exam year `2025-26` enrollment section A, current `student.classroom_id`
   section B. Migration ke baad mark section A ke paper par hona chahiye, B par
   nahi.

**Downgrade:** group tables drop, old paper rows canonical mapping se restore;
multiple sections ke different subject names original global `subject` identity
se reconstruct nahi ho sakte — lossy, documented. Marks enrollment mapping
reverse karna bhi lossy; backup se restore preferred.

### M4 — `subject_people_cleanup`

0. **Backup:** full DB dump + restore check. Snapshot `teachersubject` and
   `pipeline_hiring_table` counts; no `classroomsubject` insert.
1. `employee.subject_tags` add.
2. Backfill from `teachersubject` join `subject.name` → comma-separated text.
3. `pipeline_hiring_table`:
   - `subject_name` backfill from `subject.name` where NULL.
   - `subject_id` drop (after code no longer reads it).
4. `school_setting` seed `hiring.subject_suggestions` from distinct old subject
   names — only suggestion text.
5. `teachersubject` drop after profile/hiring code migrated.
6. Teacher profile/read schemas `subject_ids` → `subject_tags`; frontend forms
   updated.
7. **Verification gate — M4:** every `teachersubject` row represented in
   `employee.subject_tags`; hiring `subject_name` count preserved; no
   `classroomsubject` count change. Difference report + abort.

**Downgrade:** `teachersubject` recreate nahi ho sakta exactly; tags ko subject
rows mein split karke best-effort. Hiring `subject_id` NULL rahega. Documented
lossy.

### M5 — `drop_global_subject`

Only after Phase 1–4 code and tests pass.

0. **Backup:** full DB dump + restore check. Final before/after counts for
   `classroomsubject`, `chapter`, `exam_paper`, `marks`, `timetableperiod`,
   `homeworkassignment`, `attendancerecord`, `paperdraft`, `examsource`.
   No `classroomsubject` insert at any point.
1. Drop legacy columns:
   - `classroomsubject.subject_id`
   - `subjectteacher.classroom_id`, `subject_id` + old indexes/constraints
   - `chapter.class_id`, `subject_id` + old unique
   - `timetableperiod.subject_id`
   - `homeworkassignment.subject_id`
   - `attendancerecord.subject_id` + old unique
   - `classlog.subject_id`
   - `exam_paper.class_id`, `subject_id` + old unique
   - `marks.exam_id`, `subject_id` + old unique
   - `paperdraft.class_id`, `subject_id`, `section_id`
   - `examsource.subject_id`, `class_id`
2. Drop `chapterprogress` after verifying every chapter row has its status.
3. Drop old course master unique `(classroom_id, subject_id, academic_year_id)`.
4. Drop `subject` table (and its indexes/FKs) **last**.
5. Remove `academic.classroom.academics.seed` subject seeding and all imports
   of `Subject`.
6. Run `alembic check`/schema drift check only for this feature; existing
   unrelated drift report karo, ignore mat karo.
7. **Verification gate — M5:** final counts compare against M3/M4 verified
   snapshots; `marks` exact, `chapter`/`exam_paper` expected expansion, mapped
   operational rows exact. `classroomsubject` count unchanged. Difference report
   + abort/restore.

**Downgrade:** not reasonable after `subject` drop. Migration should raise a
clear `RuntimeError` explaining backup/restore required. M1–M4 downgrades remain
available before M5.

---

## 5. Exam-Paper Approach (for review, before code)

### 5.1 Exam level (unchanged)

- `exam` = one event for a class/section: “Half Yearly, Class 5”.
- `scope` class/school jaisa existing; exam par koi subject column nahi.
- School exam = class ke saare sections; class test = ek classroom section.
- Exam dates/status/publish unchanged.

### 5.2 Paper level (one row per classroom subject)

`exam_paper`:

- `classroom_subject_id` — section + subject + year.
- `exam_date`, `start_time`, `end_time`, `room`, `max_marks`,
  `passing_marks`, `note` — per section.
- `UNIQUE(exam_id, classroom_subject_id)`.
- `paper_group_id` nullable — same question paper group.

### 5.3 Creating a school exam in one action

Request shape:

```json
{
  "scope": "school",
  "class_id": "...",
  "name": "Half Yearly",
  "subjects": [
    {"name": "English", "date": "2026-12-01", "max_marks": 100}
  ]
}
```

Algorithm:

1. Class ke saare `classroom` sections load karo.
2. Har section ke **already-existing active** `classroomsubject` load karo.
   **Koi subject create nahi.**
3. Admin ke selected subject names ko case-insensitive match karo.
4. Har matched section-subject ke liye `exam_paper` row banao.
5. Matching sections ke rows ek `exam_paper_group` mein daalo; group title =
   selected name.
6. Jis section mein selected name nahi mila, usse `skipped` list mein return
   karo — us section ke liye subject pehle Course tab se add karna hoga, migration
   ya exam create usse auto-create nahi karega.
7. Class test mein sirf ek classroom section; wahi process, group optional.

> **Decision D1:** different section names (“English 1” vs “English Literature”)
> ko ek group mein jodne ke liye admin group banate waqt per-section subject
> choose kar sakta hai. Form default matching-name se group banayega; mismatch
> rows skipped dikhengi. Koi subject name linking DB mein store nahi hogi.

### 5.4 Shared question paper

- `exam_paper_group` = one shared paper.
- `paperdraft.paper_group_id` = group’s question paper.
- Group edit (title, chapters, max marks, question paper) applies to all rows.
- `display_title` optional; datesheet/question paper par group title, warna
  section ka classroom subject name.

### 5.5 Different paper for one section

- `POST /exams/paper-groups/{group_id}/papers/{paper_id}/detach`.
- Detach:
  1. Group chapters → target section ke chapter IDs se name/sequence match.
  2. Missing match → `409` with names; koi silent create nahi.
  3. Paper’s `paper_group_id = NULL`.
  4. Group draft clone → `paperdraft.exam_paper_id` (new independent draft).
  5. `exam_paper_chapter` target section ke real chapters se fill.
- Detached row ke baad hi us section ka question paper/chapters alag edit hoga.

### 5.6 Marks

- Marks `exam_paper_id` se link; student apne section ke paper par.
- `UNIQUE(exam_paper_id, student_id)`.
- Subject/exam marks se derive; duplicate source of truth nahi.
- `marks_audit` unchanged; publication per paper.

### 5.7 Lock after marks or publish

- Group locked when:
  - kisi bhi group paper par marks exist, **or**
  - koi group paper published.
- Locked group par `display_title`, chapters, question paper, `max_marks` edit
  `409`.
- Detach allowed; detached row independent ho jati hai.
- Detached row par bhi existing marks ke baad `max_marks` change require:
  marks clear karo ya audited correction flow. Isse “score ka meaning” silently
  nahi badalta.
- Lock check service mein transaction ke andar; `locked_at` convenience field
  + actual `marks`/`published_at` re-check.

### 5.8 `paperdraft` exact change

| Old | New |
|---|---|
| `subject_id` FK `subject.id` | `classroom_subject_id` FK `classroomsubject.id` |
| `class_id` | drop (derive from classroom subject) |
| `section_id` | drop (derive from classroom subject) |
| `subject` free text | retain as AI snapshot |
| — | `paper_group_id` nullable unique |
| — | `exam_paper_id` nullable unique |

- Shared paper: `paper_group_id` set.
- Single paper: `exam_paper_id` set.
- Pre-exam draft: dono null.
- Detach clone: new draft with `exam_paper_id`, group null.
- Read contract `PaperDraftRead`: `classroomSubjectId`, `paperGroupId`,
  `examPaperId`, `subject` snapshot; no `classId`/`sectionId`/`subjectId`.

### 5.9 `exam_paper_chapter` exact change

| Case | Storage |
|---|---|
| Group shared paper | `exam_paper_group_chapter` names/sequences; `exam_paper_chapter` empty |
| Detached/independent paper | `exam_paper_chapter(exam_paper_id, chapter_id)` real FK |
| Group chapter edit | group table only; all rows read group list |
| Detach | group names matched to target chapter IDs; mismatch `409` |

- `exam_paper_chapter` old `chapter_id` FK remains valid after chapter migration
  because canonical section chapter IDs preserve hain; baaki sections ke copies
  group se cover honge.
- Chapter delete block check: `exam_paper_chapter` + group name reference. Group
  chapter snapshot name delete ko block nahi karega, lekin source chapter delete
  se pehle warn/409 if linked.

---

## 6. Phase Plan (5 implementation phases)

### Phase 0 — Impact audit + architecture approval (this phase)

**Goal:** code se verify kiya hua impact list, final schema, migration approach aur
exam-paper design. Product code zero.

**Tasks:**

- [x] Backend subject touch-point inventory (58 app files + migrations/tests).
- [x] Frontend subject touch-point inventory.
- [x] Final `classroomsubject` schema + constraints.
- [x] Migration M1–M5 outline with downgrade limits.
- [x] Exam paper group approach + lock rule.
- [x] Chapter ownership change + copy action.
- [x] Subject rename isolation + 409 rules.
- [x] Teacher qualification/hiring simplification.
- [x] Risk register + test list.
- [x] `phase3.md` replace with this plan.

**Acceptance:**

- Impact list mein har model, service, schema, endpoint, frontend component,
  migration/test named hai.
- Migration order DB-safe hai: old columns final phase tak retain.
- `subject` table final phase mein drop hota hai, hidden master nahi bachta.
- Chapter/Exam group edge cases documented.

**Stop:** user “next phase” bole tabhi Phase 1.

---

### Phase 1 — Classroom subject foundation + Course tab (1.1–1.8)

> **Important - Next-phase gate:** Jab user is phase ke liye “next” bole, pehle
> is phase ka deep plan banao (current code, files, schema, tests, risks), phir
> implement karo. Bina deep plan code na likho.
>
> **Shipment gate:** Phase 1 aur Phase 2 ek hi shipment hain. Phase 1 ke baad
> naye subjects ka `subject_id` nahi hota, jabki timetable/homework/attendance/
> classlog Phase 2 tak `subject_id` use karte hain. Isliye **Phase 1 alone demo
> ya deployment nahi hogi**; Phase 2 turant baad mein complete hoga.

#### 1.1 Model + migration

- [ ] `ClassroomSubject`: `subject_id` hatao, `name`/`code`/`updated_at` add.
- [ ] Partial unique active-name index + `(school_id, classroom_id,
      academic_year_id)` index.
- [ ] M1 migration + duplicate abort report.
- [ ] `ClassroomSubject` model se `Subject` import/relationship remove.
- [ ] `classroomsubject` naye rows bina global subject ke.

#### 1.2 One subject service

- [ ] New `backend/app/domains/academic/classroom/course/subjects.py`.
- [ ] `normalise_name` — trim, collapse internal spaces.
- [ ] `create_subject`, `rename_subject`, `archive_subject`, `restore_subject`,
      `get_subject`, `list_section_subjects`.
- [ ] Duplicate check within `(school_id, classroom_id, academic_year_id)` and
      `status='Active'`, case-insensitive.
- [ ] `409` details: same classroom + same name.
- [ ] Tenant guard: school mismatch `404`.
- [ ] All writes commit in transaction; rename/archive idempotent.

#### 1.3 API + schemas

- [ ] `AddSectionSubjectIn` sirf `name`/`code`.
- [ ] `CourseSubjectRowRead`: `classroom_subject_id`, `name`, `code`, `status`.
- [ ] `PATCH /course/subjects/{id}` rename.
- [ ] `GET /classroom/sections/{id}/course` response `subject_id` remove.
- [ ] `/academics/subjects` GET/POST/PATCH delete.
- [ ] `/available-subjects` delete.
- [ ] Legacy subject master service/repository/router/seed delete.
- [ ] `SubjectTeacherRow`/`SectionDetail` name/ID source update.

#### 1.4 Course service read path

- [ ] `section_course` rows `ClassroomSubject.name` se; `Subject` query remove.
- [ ] `_course_rows`, `_row_read`, `_teachers_by_subject` `classroom_subject_id`
      par.
- [ ] `_teachers_by_subject` current academic year + classroom subject filter.
- [ ] 2027-28 teacher rows current 2026-27 course view mein na aayein.
- [ ] Completion/lesson plan summaries `classroom_subject_id` se.
- [ ] N+1 guard: fixed query count test.

#### 1.5 Frontend Course tab

- [ ] `AddSubjectDialog`: dropdown/`useApiQuery(available)` remove; plain
      `Input` + Add.
- [ ] Add duplicate `409` clear inline error.
- [ ] `CourseTable`: subject name Title Case; row ke baad `Edit`.
- [ ] New `RenameSubjectDialog` (same folder) — name only, 409 inline.
- [ ] Rename success par sirf `course` queries invalidate; doosri class ka data
      untouched.
- [ ] `SubjectMasterDialog.tsx` delete + toolbar import/button remove.
- [ ] `CoursePanel` se `masterOpen` state/button remove.
- [ ] `CourseSubject` type `subjectId` remove; `name`/`canRename` add.
- [ ] `CourseSubjectRow` type update.
- [ ] `titleCase` render (list + dialog + toast).
- [ ] `academics.service.ts` se subject master functions remove.
- [ ] `course.service.ts` se `getAvailableSubjects` remove; add
      `renameCourseSubject`.

#### 1.6 Tests

- [ ] Same classroom same name → `409`; different case → `409`.
- [ ] Same name two classrooms → allowed.
- [ ] Rename one classroom → other unchanged.
- [ ] Archived same name re-add → allowed.
- [ ] Restore when active duplicate exists → `409`.
- [ ] Tenant isolation: School A cannot see/rename School B subject.
- [ ] Course `section_course` no `Subject` query; old year teacher rows hidden.
- [ ] Frontend `titleCase`, duplicate error, rename dialog unit tests.
- [ ] M1 migration upgrade/backfill/duplicate abort test.

#### 1.7 Acceptance

- Course tab par sirf us section ke subjects.
- Add Subject plain name se kaam kare; global list ka koi UI nahi.
- Edit se sirf usi class ka subject rename ho; doosri class same.
- Same class duplicate 409; different class same name allowed.
- Subject Master screen khatam.
- Zero subject master seed/API references left in Course.
- Phase 1 alone demo/deploy nahi — Phase 2 ke bina timetable/homework/
  attendance/classlog compatibility complete nahi.

#### 1.8 Out of scope

- Chapters (Phase 2), timetable/homework (Phase 2), exams (Phase 3), teachers
  (Phase 4), `subject` table drop (Phase 5).

---

### Phase 2 — Chapters, timetable, homework, attendance, lesson plans (2.1–2.9)

> **Shipment gate:** Phase 2 Phase 1 ke turant baad complete hoga. Dono phases
> ke bina demo/deployment nahi. Phase 2 se pehle Phase 1 ka M1 + Course tab
> fully verified hona chahiye.

#### 2.0 Deep plan (resume — 22 Nov 2026)

Phase 2 beech mein ruka tha. Code audit ke baad state:

- **Ho chuka (uncommitted):** `Chapter.classroom_subject_id` + progress fields
  model mein; course service chapters/tick/completion naye path par; timetable/
  homework/attendance/classlog models mein `classroom_subject_id`; services
  naam `ClassroomSubject` se padhte hain; M2 draft (`f2d3e4a5b6c7`);
  `CopyChaptersDialog` + Chapters button hamesha enabled.
- **Galat / adhura:**
  1. M2: naye columns par FK nahi; `chapter.classroom_subject_id` NOT NULL nahi;
     `chapterprogress` orphan abort nahi; before/after count gate nahi;
     `subjectteacher` NULL-link check + `(classroom_subject_id, effective_from)`
     unique nahi; timetable/homework `classroom_subject_id` NOT NULL nahi;
     downgrade sirf raise karta hai.
  2. Copy chapters plan se alag: school-wide naam match + `replace`. Plan:
     same school + same class + same year, append after max, same-name skip,
     response `{copied, skipped}`.
  3. Lesson plans/approvals/reminders/teacher course/scope/attendance history/
     classroom cards abhi bhi global `Subject` se naam padhte hain → naye
     (name-only) subjects par "Subject" ya card gayab.
  4. `teacher_course.course_summary` totals ko purane `(class_id, subject_id)`
     key se padhta hai → completion % hamesha None.
  5. `get_subject_rows` outer join ka open-row filter WHERE mein → jis subject ki
     sirf closed history hai woh section se gayab.
  6. API field abhi bhi `subject_id` naam se classroom subject id le jata hai.
     Plan 3.5: body/response `classroom_subject_id`.
  7. Lesson plan: out-of-year month server reject nahi; UI year free dropdown,
     month Jan–Dec.
  8. Tests: ~12 purani test files purane `AddSectionSubjectIn(subject_id=...)`,
     bina naam `ClassroomSubject`, bina `classroom_subject_id` `Chapter` se
     fixtures banati hain → 67 fail. Head pin `f1c2d3e4a5b6` par.
- **Order:** M2 + models → services/schemas rename → lesson-plan year rule →
  test fixtures + naye tests (`test_classroom_chapters.py`, M2 migration) →
  frontend types/services/panels → `ruff`, phase pytest, `tsc`, `node --test`,
  eslint/Prettier → is file mein checkboxes + completion log.
- **Out of scope (Phase 3/4):** exam paper/marks/AI paper builder, auth
  `is_teacher_assigned_to_subject`, substitution/workload/dashboard,
  `ExamSource` repoint. Exam plan ka chapter check abhi legacy `subject_id` par
  rahega; Phase 3 usse badlega.

#### 2.1 Chapter model + migration

- [x] `Chapter` se `class_id`/`subject_id` hatao; `classroom_subject_id NOT NULL`.
- [x] `sequence`, `name`, `planned_date`.
- [x] Progress fields merge: `status`, `completed_on`,
      `completed_by_employee_id`.
- [x] `UNIQUE(classroom_subject_id, sequence)`.
- [x] M2 migration: old class chapter → copies only in sections with an existing
      `classroomsubject`; old canonical ID preserve; progress copy.
- [x] M2 **no new classroomsubject**; unmapped chapter/progress rows → orphan
      report + abort.
- [x] `chapterprogress` table Phase 5 drop; code abhi se naya path use kare.

#### 2.2 Chapter service + API

- [x] `list_chapters` sirf target classroom subject ke rows.
- [x] `add_chapter`: first chapter bhi create ho; sequence boundary.
- [x] `update_chapter` rename/date/move.
- [x] `delete_chapter`: completed chapter and exam-paper link checks (the group
      chapter reference check arrives with Phase 3's group tables).
- [x] `tick_chapter`: classroom subject ownership; completed by/on.
- [x] `ChapterRowRead` `classroom_subject_id` field.
- [x] N+1 guard: chapters + names + completion fixed queries.
- [x] `course.manage` chapters edit; `course.plan` own subject tick; server
      authority.

#### 2.3 Course Chapters UI fix

- [x] `CourseTable` “Chapters” button **zero chapters par bhi enabled** jab
      `classroomSubjectId` aur access ho.
- [x] Empty popup mein “No chapters yet” + “Add chapter” visible to manager.
- [x] `CoursePanel` chapter popup state empty list par bhi khule.
- [x] `ChapterEditorDialog` add-first flow.
- [x] Edit/Delete chapter manager ke liye; teacher read-only.
- [x] After add/edit/delete/tick: course query invalidate.
- [x] No hidden “total===0” disabled bug.

#### 2.4 Copy chapters from another section

- [x] `POST /course/subjects/{target}/chapters/copy` body
      `{source_classroom_subject_id}`.
- [x] Same school, same class, same academic year; target ≠ source.
- [x] Copy `name`, `planned_date`, order; status Pending, completion clear.
- [x] Target empty: sequence preserve; target non-empty: append after max.
- [x] Existing same name rows skip (returned `skipped`), no silent duplicate.
- [x] Response `{copied, skipped}`.
- [x] UI: “Copy chapters” action in chapter popup; source selector same
      class/year; confirmation; result toast with skipped names.
- [x] After copy, source/target independent — edit one does not affect other.

#### 2.5 Timetable repoint

- [x] `TimetablePeriod.subject_id` → `classroom_subject_id`.
- [x] Service validates subject belongs to that `classroom_id` + current year.
- [x] `get_timetable_rows` join classroom subject name.
- [x] Period create/update/clear/list/read schemas.
- [x] Clash constraints unchanged.
- [x] Frontend `TimetablePanel` options section subjects; body field rename.

#### 2.6 Homework + class log repoint

- [x] `HomeworkAssignment.subject_id` → `classroom_subject_id`.
- [x] Service validates section match; teacher assignment any active teacher.
- [x] `HomeworkRow`/`DiaryRow` names via classroom subject.
- [x] `ClassLog.subject_id` → nullable `classroom_subject_id`.
- [x] `AssignHomework`, `WriteDailyLog`, `HomeworkPanel`, `ClassDiary` fields
      update.
- [x] Homework lists and submission review names.

#### 2.7 Attendance repoint

- [x] `AttendanceRecord.subject_id` → nullable `classroom_subject_id`.
- [x] New unique keys + partial day-level index.
- [x] Register/service/repository queries.
- [x] `StudentHistoryDialog` subject labels.
- [x] Two-subject same day and day-level rows both safe.

#### 2.8 Lesson plan scope + lifecycle

- [x] `LessonPlan` FK stays `classroom_subject_id`; no change.
- [x] Year current open academic year se; UI read-only.
- [x] Month dropdown April–March order only.
- [x] Calendar year derived from academic-year start (Apr–Dec start year,
      Jan–Mar next year).
- [x] Server rejects out-of-year month; no silent fallback.
- [x] v1 Submitted editable/resubmittable until approved.
- [x] Approved locks; change request creates v2/v3.
- [x] Pending/rejected version editable; Resubmit button after submit.
- [x] `WeeklyLessonPlanDialog` year control read-only; current year from
      `useAcademicYear`.
- [x] `lesson-plan.ts` month helpers + tests.

#### 2.9 Tests / acceptance

- [x] Chapter add/edit/delete/move/copy, zero-chapter Add flow.
- [x] Copy across sections independent; duplicate skip.
- [x] Timetable/homework/attendance resolve classroom subject name.
- [x] Same class two sections rename/subject isolated.
- [x] Lesson plan year/month/lifecycle tests.
- [x] M2 migration row counts; chapter copies; progress preserved; no orphans.
- [x] M2 test: zero `classroomsubject` rows created; skipped sections reported;
      orphan row aborts migration.
- [ ] Phase 1 + Phase 2 combined smoke before any demo/deploy — **pending: needs the
      M1+M2 backup/apply on the live DB and a browser pass.**
- [x] `ruff` clean on every file this phase touched (the repo still has older,
      unrelated ruff findings), phase tests, `tsc`, `node --test` clean.

---

### Phase 3 — Exams: section papers + shared groups (3.1–3.9)

#### 3.0 Deep plan (22 Nov 2026)

Audit (code padh kar): `ExamPaper` abhi `(exam, class_id, subject_id)` global `Subject`
par; `exams/plan/service.py` (1379 lines) har jagah `subject_id`/`class_id` se kaam
karta hai (guards, marks, results, reminder); `classroom/{service,repository}.py` ka
purana marks save/read bhi `ExamPaper.subject_id` se; AI builder (`PaperDraft`,
`ExamSource`, `QuestionUsageLog`) ke `subject_id/class_id` nullable legacy hain
(frontend IDs bhejta hi nahi, free-text snapshot use hota hai).

**Contract (decide kiya):**
- `ExamPaper`: `classroom_subject_id NOT NULL`, `paper_group_id NULL`,
  `UNIQUE(exam_id, classroom_subject_id)`. Legacy `class_id`/`subject_id` nullable
  rehte hain (M5 drop). Section aur class `classroomsubject -> classroom` se derive.
- Paper row input `PaperScheduleIn`: ya to `classroom_subject_id` (ek section ka
  subject, `chapter_ids` real FK ke saath) ya `subject_name` + `class_id`
  (class ke har section mein existing active subject name se expand;
  `chapters` = naam list). Expand par >1 section => `exam_paper_group`
  (`display_title` = naam, chapters group names); 1 section => group nahi, naam se
  chapter FK match (miss => 409). Koi subject create nahi; jis section mein naam
  nahi mila woh response `skipped` mein.
- Marks: `exam_paper_id NOT NULL`; `subject_id` nullable aur ab likha nahi jata;
  `exam_id` paper se likha jata hai jab tak M5 drop na kare.
  Students = paper ke section ke students (class-wide nahi).
- Group lock: kisi bhi group paper par marks ya `published_at` => group edit 409
  (live check, `locked_at` sirf convenience). Detach allowed. Marks wale paper par
  `max_marks` change 409 (D4).
- Guards: office, ya paper ke `classroom_subject` ka **abhi ka** teacher
  (`SubjectTeacher.classroom_subject_id`, open row).
- Results/reminder/publish/notify: naam `classroomsubject.name` (group title
  fallback ke saath); cohort = us paper ke section ke students.
- Old Academics marks save/read (`classroom/service.save_section_marks`,
  `repository.get_section_marks`): subject id => classroom subject id, paper
  `(exam, classroom_subject)` se.
- AI builder: `PaperDraft.classroom_subject_id/paper_group_id/exam_paper_id`
  nullable add, `ExamSource`/`QuestionUsageLog.classroom_subject_id` nullable add;
  free-text `subject` snapshot rehta hai; read/create schemas mein naye fields.
  Deviation (documented): source library class-level hai, isliye source/usage rows
  ka ambiguous section match **abort nahi**, NULL rehta hai; draft jisme
  `subject_id`+`section_id` dono ho aur match na mile woh abort.
- M3 `f3...` migration: SQLite-testable data steps (M2 jaisa): groups tables, paper
  expansion sirf existing classroomsubject wale sections mein, marks enrollment se
  (exam year NULL => abort), before/expected/actual/delta gate, promoted-student test.

**Order:** models + M3 + M3 test => plan service/schemas/router (groups, detach,
lock) => classroom marks path + reminders => AI builder fields => frontend types/
services/ExamScheduleForm/DateSheet/MarksGrid/ResultsView + group/detach UI => tests
(`test_exam_paper_groups.py`, M3, tenant, rewrite `test_classroom_exams.py`,
phase10) => ruff, pytest, tsc, node --test, prettier => checkboxes + completion log.

**Out of scope (Phase 4/5):** teacher tags, substitution/workload/dashboard,
`subject` table drop, `Mark.exam_id`/legacy columns drop.

#### 3.1 Exam models + migration

- [x] `Exam` unchanged.
- [x] `ExamPaper`: `classroom_subject_id NOT NULL`, `paper_group_id NULL`;
      drop `class_id`/`subject_id`.
- [x] `ExamPaperGroup` + `ExamPaperGroupChapter`.
- [x] `Marks`: `exam_paper_id NOT NULL`, `subject_id` nullable and never written;
      `exam_id` is still written from the paper and dropped in M5 (older reads filter
      on it). Unique `(exam_paper_id, student_id)` already existed.
- [x] `PaperDraft`/`ExamSource`/`QuestionUsageLog` repoint (additive: nullable
      `classroom_subject_id`; the legacy columns stay until M5).
- [x] M3 migration: class paper → section papers + group only for sections with
      an existing `classroomsubject`; no create. (Data steps tested on SQLite; **not yet
      run on a real PostgreSQL / the live DB** — backup + approval pending.)
- [x] M3 marks mapped via `enrollment` for the exam’s academic year, never
      `student.classroom_id`.
- [x] M3 before/after counts: marks exact; chapter/exam_paper expected expansion;
      timetable/homework/attendance exact. Difference report + abort.
- [x] Group chapters snapshot from old paper chapters.

#### 3.2 Exam plan service

- [x] `create_exam` class test: selected classroom subjects → paper rows.
- [x] `create_exam` school exam: class sections × **already-existing** matching
      classroom subjects; one action; skipped list. Koi subject create nahi.
- [x] Group create for multi-section same paper.
- [x] `update_exam` date sheet keyed by `classroom_subject_id`.
- [x] Delete/replace paper only when no marks/publish.
- [x] `_paper_read` name from classroom subject; group title fallback.
- [x] `read_exam` groups/papers included.
- [x] Permission: office or the paper's current subject teacher (open `subjectteacher`
      row of that classroom subject).

#### 3.3 Marks + results

- [x] Save marks by paper; only students in that section.
- [x] `_mark_of` by `(paper_id, student_id)`.
- [x] Results: subject from `exam_paper.classroom_subject`; no school-wide name
      grouping.
- [x] Publish per paper; lock group.
- [x] Change mark audit unchanged.
- [x] Reminder uses group/paper title.

#### 3.4 Group edit + detach

- [x] `PATCH /exams/paper-groups/{group_id}` title/chapters/max marks.
- [x] Lock if any paper marks/published; `409`.
- [x] `POST .../detach`; clone group chapter snapshot to target section
      `exam_paper_chapter`; missing match `409`.
- [x] Detach group draft clone to `paperdraft.exam_paper_id`.
- [x] After detach group remains for other rows.
- [x] Locked group detach allowed; row still subject to marks/max rule.

#### 3.5 AI paper builder + sources

- [x] `PaperDraftCreate`/Read `classroom_subject_id`; no `subject_id`.
- [x] `PaperDraft` group/single links.
- [x] `ExamSource` optional classroom subject; free-text subject retained.
- [x] `QuestionUsageLog` classroom subject optional.
- [x] RAG filters classroom subject id/free text; no global roll-up.
- [x] `BasicsStep`/`SourceStep`/`GenerateStep` payloads.

#### 3.6 Frontend exam plan

- [x] `ExamScheduleForm`: section subjects from classroom, not
      `getSubjects`; school exam uses class sections + matching subject names.
- [x] DateSheet/MarksGrid/ResultsView group title fallback.
- [x] Group detach action + lock message.
- [x] Subject name per section Title Case.
- [x] `ExamPaperPlan` type `classroomSubjectId`, `paperGroupId`,
      `displayTitle`.
- [x] `useExamPlan` query keys/invalidations by classroom subject.

#### 3.7 AI papers frontend

- [x] `BasicsStep` subject choice from classroom.
- [x] `SourceStep`/`GenerateStep` subject snapshots.
- [x] `usePaperBuilder`/`useSourceMaster` types and body fields.
- [x] `PaperBuilder` shared draft/group context.

#### 3.8 Tests

- [x] Class test one paper per selected section subject.
- [x] School exam creates rows for every section; skipped names reported.
- [x] Shared group chapters apply all rows.
- [x] Detach creates independent paper; others unchanged.
- [x] Marks link to section paper; results per section.
- [x] Lock after first mark/publish; locked edit 409; detach allowed.
- [x] Max marks change with marks refused.
- [x] M3 migration: paper counts, marks mapping, group chapters, no orphans.
- [x] M3 test: student promoted after the exam — mark maps to old enrollment
      section paper, not current `student.classroom_id`.
- [x] M3 marks before/after exact count; other table counts expected/exact.
- [x] No `classroomsubject` row created by M3.
- [x] Frontend exam group/detach/render tests (helpers: `view.test.ts`; the group
      dialog and detach button are typechecked and linted, **not browser-tested**).

#### 3.9 Acceptance

- Koi class-level subject exam paper mein nahi.
- School exam ek action mein saare section papers banaye.
- Same question paper group optional; different section paper detach ho sake.
- Marks/results section-specific; shared paper par name difference allowed.
- Marks/publish ke baad group edit blocked.

---

### Phase 4 — People, hiring, substitution, dashboard (4.1–4.8)

#### 4.0 Deep plan (22 Nov 2026)

Audit: `teachersubject` ko `staff/{service,lifecycle,schemas}`, `teachers/{service,
profile/*}` aur substitution repository padhte/likhte hain; hiring ka `subject_id` model +
schema mein hai (service/repository mein nahi); dashboard 4 jagah global `Subject` se
naam leta hai; `auth/service` mein legacy `subject_id` scope path bacha hai
(`is_teacher_assigned_to_subject`, `can_teach_subject`) jiska koi caller nahi.

**Contract:**
- `employee.subject_tags varchar(500) NULL` — comma-separated, normalised (trim, collapse,
  case-insensitive dedupe) by ek helper `teachers/subject_tags.py`; max 500 (`422`).
- `teachersubject` model + table drop. Hire/Staff schemas: `subject_ids`/`subject_id`
  => `subject_tags: str | None`. `StaffProfileRead.subject_tags`.
- `PUT /teachers/profile/{id}/subject-tags` body `{subject_tags}` => response
  `{subject_tags}`; purana `/subjects` route delete. Teacher list/detail field
  `subject` => `subjectTags` (list row `subject` string = tags). Workload matrix subject
  column = **section subjects jo woh abhi padhata hai** (classroom subject names,
  per assignment) — koi by-name school roll-up nahi.
- Rehire/lifecycle: tags copy (ab ek column, row copy automatic); delete employee mein
  `TeacherSubject` cleanup hata.
- Substitution: pool = active employees jinke paas teaching role hai (D5), `teachersubject`
  gate nahi; hard refusal nahi; ranking: tags mein subject ka naam => boost (+TAG_MATCH),
  reason "Lists <subject> in their subjects". Non-matching teacher assign ho sakta hai.
- Auth: legacy `subject_id` scope path + `is_teacher_assigned_to_subject` +
  `can_teach_subject` delete (callers sab `classroom_subject_id` par).
- Hiring: `HiringCandidate.subject_id` drop (`subject_name` free text rehta hai);
  `school_setting hiring.subject_suggestions` (JSON list) read/write endpoints; read ka
  default = is school ke current-year classroom subject names (sirf convenience).
- Dashboard: timetable/homework names `ClassroomSubject` se; `subject_perf` pehle se
  `[]` (koi by-name roll-up nahi) — test se pin.
- **M4 `f4...`:** `employee.subject_tags` add; `teachersubject` + `subject.name` se tags
  backfill; `pipeline_hiring_table.subject_name` backfill jahan NULL; `subject_id` drop;
  `school_setting` seed `hiring.subject_suggestions` (distinct old subject names);
  verification: har `teachersubject` row tags mein, hiring count same,
  `classroomsubject` count same; phir `teachersubject` drop. Downgrade: lossy refuse.
- Frontend: staff/hiring forms tags input + datalist, profile drawer tags text, `useStaffHiring`
  suggestions query, `getSubjects`/`replaceSubjects` hatao, teachers list `subjectTags`.

**Order:** tags helper + models + M4 (+test) => staff/profile/teachers services & schemas
=> substitution + auth + dashboard + hiring => tests rewrite => frontend => checks/log.

**Out of scope (Phase 5):** `subject` table, legacy columns, `chapterprogress` drop,
M5, final regression.

#### 4.1 Teacher subject tags

- [x] `employee.subject_tags varchar(500) NULL` add.
- [x] `teachersubject` model/table/imports remove.
- [x] `TeacherSubject` ke saare queries replace.
- [x] Teacher list/detail `subject` → `subjectTags`.
- [x] Profile drawer Subjects tab simple text; no multi-select IDs.
- [x] M4 migration backfill tags from old teacher subjects (SQLite-tested; **not run on a
      real PostgreSQL / the live DB**).
- [x] Rehire/lifecycle copy tags.

#### 4.2 Teacher profile API

- [x] `SubjectsUpdate` → `SubjectTagsUpdate {subject_tags}`.
- [x] `PUT /teachers/profile/{id}/subject-tags`.
- [x] Old `/subjects` route delete.
- [x] `ProfileRead.subjects` names `subjectTags`.
- [x] Staff profile forms/UI update (hire form + drawer text; the drawer's Subjects line is
      read-only - the PUT endpoint exists, an inline editor was not built).
- [x] `replaceSubjects` frontend remove.

#### 4.3 Teacher assignment / permissions

- [x] `SubjectTeacher` classroom_subject only; legacy classroom/subject drop
      (M5).
- [x] `assign_teacher` any active teacher with teaching role.
- [x] No subject qualification match/block.
- [x] `_has_teaching_role` remains role check only.
- [x] Auth scope `is_teacher_assigned_to_subject` → classroom subject id.
- [x] Callers pass `classroom_subject_id`; old subject id path remove.
- [x] Any teacher can be assigned even if tags don't match.

#### 4.4 Substitution

- [x] Candidate pool all active teachers, not just `teachersubject` holders.
- [x] Remove hard “does not teach subject” refusal.
- [x] Optional ranking: tag text contains subject name → +10 boost only.
- [x] Subject/class labels via classroom subject.
- [x] Frontend `SubstitutionTab` candidate labels/reasons update.
- [x] Tests: non-matching teacher assignable; matching teacher only ranked
      higher.

#### 4.5 Workload / performance

- [x] Workload repository joins timetable classroom subject.
- [x] Workload matrix subject column per classroom, no by-name school roll-up.
- [x] Performance chapter plan by `classroom_subject_id`.
- [x] Teacher course tab/detail names.
- [x] No `Subject` table import.

#### 4.6 Hiring

- [x] `pipeline_hiring_table.subject_id` drop; `subject_name` free text.
- [x] `school_setting.hiring.subject_suggestions` read/write.
- [x] Hiring interview form: input + suggestion datalist, no FK.
- [x] StaffRegistrationForm tags input.
- [x] `useStaffHiring` suggestions query.
- [x] No `getSubjects` call in hiring.

#### 4.7 Dashboard / reports

- [x] `GET /dashboard/subject-perf` classroom-scoped; no school-wide by-name
      grouping.
- [x] Dashboard timetable/homework/leave subject names.
- [x] Auth/permissions scope tests.
- [x] Tenant isolation two schools.
- [x] No cross-class roll-up introduced anywhere.

#### 4.8 Tests / acceptance

- [x] Non-matching teacher can be assigned and can tick/mark.
- [x] Substitution candidate list includes non-matching active teacher.
- [x] Teacher profile tags round-trip, no subject IDs.
- [x] Hiring suggestion list independent of subject table.
- [x] Dashboard subject performance scoped, not name-rolled.
- [x] M4 migration tags/backfill.
- [x] `ruff`, phase tests, `tsc`, `node --test` clean.

---

### Phase 5 — Final cleanup + global subject drop + end-to-end (5.1–5.9)

#### 5.1 Drop legacy schema

- [ ] M5 migration as Section 4.
- [ ] `subject` table drop last.
- [ ] `classroomsubject.subject_id` drop.
- [ ] All legacy `subject_id`/`class_id`/`section_id` drop.
- [ ] `chapterprogress` drop after verification.
- [ ] `teachersubject` already dropped; verify.
- [ ] Old indexes/constraints drop.
- [ ] Migration downgrade explicitly irreversible message.

#### 5.2 Remove old code

- [ ] `Subject` imports/usages zero across `backend/app`.
- [ ] `academics` subject master service/repository/router/schemas/seed gone.
- [ ] `SubjectMasterDialog`/`getSubjects`/`createSubject`/`updateSubject` gone.
- [ ] `available-subjects` route/service gone.
- [ ] Old `PUT /classroom/sections/{id}/subjects/{subject_id}/teacher` gone.
- [ ] `operations.service.setSubjectTeacher` dead code gone.
- [ ] No `TeacherSubject` references.
- [ ] No `subject_id` in domain request/response schemas.

#### 5.3 Contract + docs

- [ ] `phase2.md` cross-phase reminders update.
- [ ] API docs/openapi refresh.
- [ ] Migration README/rollout note.
- [ ] `phase3.md` completion log.
- [ ] `PHASES.md` pointer if path changes.

#### 5.4 Full regression

- [ ] Subject create/rename/archive/restore.
- [ ] Two classrooms same name; rename isolation; duplicate 409.
- [ ] Archived re-add; restore duplicate 409.
- [ ] Course chapters zero-add/edit/delete/move/copy.
- [ ] Timetable/homework/attendance/class log.
- [ ] Lesson plan year/month/lifecycle.
- [ ] Exam class test/school exam/group/detach/lock/marks/results.
- [ ] AI paper builder/source library.
- [ ] Teacher profile/tags/assignment/substitution/workload/performance.
- [ ] Hiring forms.
- [ ] Dashboard/reports.
- [ ] Two-school tenant isolation.

#### 5.5 Performance

- [ ] `section_course` query count constant.
- [ ] Exam list/results query count constant.
- [ ] Dashboard no N+1.
- [ ] Index review: classroom subject, exam paper, marks, timetable, homework,
      attendance.
- [ ] Pagination on large lists.

#### 5.6 Security

- [ ] Every service query `school_id`.
- [ ] Cross-school IDs `404`.
- [ ] Permission server-side tests.
- [ ] No subject master API left open.
- [ ] Archived subject not writable except restore.

#### 5.7 Frontend validation

- [ ] `tsc --noEmit` clean.
- [ ] `eslint` clean.
- [ ] Prettier check.
- [ ] `node --test` all course/exam/homework/timetable helpers.
- [ ] Browser smoke: Course add/edit, chapters add/edit/copy, lesson plan,
      timetable, homework, exams, teacher assignment, hiring.

#### 5.8 Migration validation

- [ ] Fresh DB upgrade head.
- [ ] Live/dev DB upgrade from `e5a7b9c1d3f4`.
- [ ] M1–M5 backups present, restorable, timestamped.
- [ ] Row counts: classroomsubject, chapter, exam_paper, marks, timetable,
      homework, attendance, paperdraft, examsource.
- [ ] Marks before/after exact; chapter/exam_paper expected expansion;
      timetable/homework/attendance exact.
- [ ] `classroomsubject` count unchanged by every migration.
- [ ] No orphan FKs.
- [ ] No duplicate active names.
- [ ] `subject` table absent.
- [ ] Single head; `alembic current`/`heads` match.

#### 5.9 Final summary

- [ ] Kya add hua, kya rename hua, kya drop hua.
- [ ] Kaunse decisions liye.
- [ ] Kaunse tests pass.
- [ ] Kaunse known limitations/user decisions bache.

---

## 7. Decisions requiring approval before Phase 1

### D1 — School exam subject-name mismatch
Same class ke sections ke subject names different ho sakte hain. Phase 3 form
matching-name se group banayega; mismatch rows `skipped` aayengi aur admin
per-section subject choose karke group bana sakta hai. Koi DB-level name linking
nahi.

### D2 — `chapterprogress` merge
Recommendation: progress fields `chapter` par merge, table drop. Isse section
duplicate aur mismatch khatam. Agar aap 1:1 table rakhna chahte hain to batao;
plan tab minimal-churn variant use karega.

### D3 — `marks` redundancy
Recommendation: `marks` sirf `exam_paper_id` rakhe; `exam_id`/`subject_id` drop.
Subject/exam paper se derive. Isse marks ka subject paper se alag hona impossible.

### D4 — Detached paper max marks
Detach ke baad bhi existing marks ke saath `max_marks` change blocked rahega
jab tak marks clear/audited correction na ho. Question paper/chapters detached
row par editable honge. Agar aap detach ke baad max marks allow karna chahte
hain, marks ka meaning badalne ka risk accept karna padega.

### D5 — Teacher role vs qualification
“Any teacher” ka matlab: active teaching-role employee, not any staff
(accountant/driver). Qualification/tag match sirf suggestion/ranking. Agar aap
non-teaching staff ko bhi assign karna chahte hain to `_has_teaching_role` bhi
hatega — default plan mein nahi.

### D6 — `code` field
`classroomsubject.code` optional rakhenge, unique nahi. UI mein default hidden.
Agar school codes chahta hai to per-classroom unique index baad mein add ho
sakta hai.

### D7 — Archived subject restore
Active same-name row hone par restore `409`; user pehle active row rename/archive
karega. Silent merge nahi.

---

## 8. Completion Log

> Har phase ke baad yahan entry. Format fixed rakho.

### Phase 0 — 21 Nov 2026

- **Kya kiya:** poori subject dependency audit; final schema; migration M1–M5;
  exam paper group design; chapter ownership/copy; subject rename rules;
  teacher/hiring simplification; risk register; is file ko replace kiya.
- **Files:** sirf `backend/phase3.md` (plan). Product code zero.
- **Backend impact:** 58 app files + migrations/tests listed in Section 3.
- **Frontend impact:** Section 3.6 list.
- **Tests:** koi test run nahi (Phase 0 planning only).
- **Baaki:** Phase 1 approval; D1–D7 decisions.
- **phase2.md:** Phase 1 shuru hone par subject redesign reminders add honge.

### Phase 0 review — 21 Nov 2026

- **Review changes accepted:** migrations never create `classroomsubject`;
  unmapped rows go to orphan report and abort. Marks map through enrollment for
  the exam year, not `student.classroom_id`, with a promoted-student migration
  test. Phase 1 and Phase 2 ship together; no demo/deploy between them. Every
  migration M1–M5 needs backup + before/after count report; marks exact, chapter/
  exam_paper expected expansion, timetable/homework/attendance exact.
- **Files:** `backend/phase3.md` only. Product code/migration unchanged.
- **Tests:** planning only; no test run.
- **Next:** wait for user “next phase” before Phase 1 deep plan.

### Phase 1 — code complete (21 Nov 2026; live M1 pending)

- **Done:** `ClassroomSubject` now owns `name`/`code`; legacy `subject_id` is nullable and not written for new subjects. `subjects.py` is the write service. Course Add is a plain name input; CourseTable has Edit; `SubjectMasterDialog` and global subject APIs/seed removed. M1 migration + active-name index + nullable legacy FK added.
- **Tests:** `test_course_subjects.py` 5/5; `test_classroom_subject_migration.py` 4/4; migration head tests 7/7; frontend `view.test.ts` 14/14; `tsc` clean; `ruff` clean; Prettier check clean.
- **Not done / intentional:** M1 not applied to live DB yet. `Subject` model/service/repository still exists **only** for Phase 2/3 legacy modules; it has no API/UI/seed/Course use. Phase 1 is not deployable without Phase 2, as recorded in the shipment gate.
- **Files:** `course/{models,service,router,schemas,subjects}.py`, `academics/{models,router,seed}.py`, `course/{AddSubjectDialog,CoursePanel,CourseTable,RenameSubjectDialog,ChapterEditorDialog,TeacherAssignDialog,TeacherHistoryDialog,WeeklyLessonPlanDialog}.tsx`, `TeacherCourseDetail.tsx`, `course.service.ts`, `types/index.ts`, `lib/course/view.test.ts`, M1 migration, tests.
- **Next:** Phase 2 deep plan, then implement; no demo/deploy between.

### Phase 2 — code complete (22 Nov 2026; M2 not yet applied to the live DB)

- **Kya kiya:** Phase 2 beech mein ruka tha (service + models adhure, M2 draft mein
  FK/NOT NULL/gate nahi, 67 tests fail). Ab:
  - **M2 `f2d3e4a5b6c7`** dobara likha: har `subjectteacher`/`chapter`/
    `chapterprogress`/timetable/homework/attendance/classlog row sirf *existing*
    `classroomsubject` par map; koi row create nahi; unmapped row → orphan report +
    abort; before/expected/actual/delta count gate; FK, NOT NULL, `uq_chapter_
    classroom_subject_sequence`, `uq_subjectteacher_cs_from`, attendance keys; lossy
    downgrade documented. Data steps functions hain, isliye SQLite par bhi chalte hain.
  - **Chapters section-owned:** progress `chapter` par merge; `chapterprogress` ab
    sirf legacy (Phase 5 drop). Copy chapters = same school/class/year, append, same
    name skip, `{copied, skipped, chapters}`; `GET .../chapter-sources`.
  - **Timetable, homework, class log, attendance** `classroom_subject_id` par; ek hi
    check `subjects.require_section_subject` (404 other school, 422 other section,
    409 archived). API field `classroom_subject_id` (request + response).
  - **Course read** ab fixed queries: teacher ka per-subject tick query hata
    (`_tickable_subjects`), legacy `Subject` joins hataye (lesson plans, approvals,
    reminders, teacher course, scope, classroom cards, subject rows, substitution).
    Legacy `PUT /classroom/sections/{id}/subjects/{subject_id}/teacher` + dead helpers
    delete.
  - **Lesson plan:** server out-of-year month `422`; UI year read-only (academic year
    context), months April→March (`academicYearMonths`).
  - Teacher completion % ka purana `(class_id, subject_id)` key bug fix.
- **Tests:** `test_subject_migration.py` 7/7 (M2 on SQLite: counts, no create,
  orphan aborts), `test_subject_tenant_scope.py` 3/3 (two schools, fixed query
  count for office + teacher), chapter copy tests, in-year lesson plan test;
  ~25 purani test files naye shape par. Backend suite: 625 pass, 12 fail; ye 12
  purane aur Phase 2 se alag (exams `created_by` SimpleNamespace x9,
  `test_operations_authorization` academic-years route, phase1 teacher-slot NULL
  year key, homework "Tomorrow" date-dependent). `tsc` clean; `node --test` 44/44;
  Prettier clean on touched files.
- **Not done / intentional:** M1+M2 live DB par apply nahi hue (backup + approval
  chahiye) aur browser smoke baaki — isliye Phase 1+2 combined smoke unchecked.
  Exams abhi bhi legacy `Subject`/`subject_id` use karte hain (Phase 3);
  `ExamScheduleForm` ka school-exam dropdown `/academics/subjects` par tha jo Phase 1
  mein delete ho chuka — Phase 3.6 mein theek hoga. Auth `is_teacher_assigned_to_
  subject` legacy path abhi bhi hai (Phase 4.3); naya `is_teacher_assigned_to_
  classroom_subject` add hua. Substitution qualification gate legacy subject id wale
  subjects par rehta hai; name-only subject par sab active teachers (Phase 4.4 gate
  hatayega).
- **Files:** `alembic/versions/f2d3e4a5b6c7_*`, `course/{service,subjects,router,
  schemas,scope,lesson_plans,approvals,reminders,teacher_course,completion}.py`,
  `attendance/*`, `homework/*`, `timetable/*`, `classroom/{service,repository,
  router,schemas}.py`, `auth/service.py`, `people/teachers/{performance,workload,
  substitution}`, frontend course/timetable/homework services, types, `CopyChaptersDialog`,
  `WeeklyLessonPlanDialog`, `lib/course/lesson-plan.ts`, tests.
- **Next:** Phase 3 (exams) — user ke "next phase" ke baad, deep plan pehle.

### Phase 3 — code complete (22 Nov 2026; M3 not yet applied to the live DB)

- **Kya kiya:**
  - **Models:** `ExamPaper` ab `classroom_subject_id NOT NULL` + `paper_group_id`,
    `UNIQUE(exam_id, classroom_subject_id)`; naye `ExamPaperGroup` /
    `ExamPaperGroupChapter`; `Mark.exam_paper_id NOT NULL`, `subject_id` ab likha nahi
    jata; `PaperDraft`/`ExamSource`/`QuestionUsageLog` par nullable
    `classroom_subject_id` (+ draft par `paper_group_id`/`exam_paper_id`).
  - **M3 `f3e4a5b6c7d8`:** class paper -> section papers (sirf existing
    `classroomsubject` wale sections), shared group (title + chapters by name), marks
    **enrollment** se (exam year), before/expected/actual/delta gate (marks exact,
    `exam_paper` +copies, `exam_paper_chapter` -moved links, `classroomsubject` same),
    koi row create nahi, unmapped => abort. Downgrade deliberately refuse (backup
    restore) - lossy hai.
  - **Plan service:** date-sheet row `classroom_subject_id` ya `subject_name`(+class) —
    naam wali row har section mein expand (>1 => group), `skipped` list mein jin
    sections mein subject nahi; update/delete marks/publish ke saath 409; marks sheet
    section ke students ki; results per-section paper columns; reminder/publish/notify
    names section subject se; teacher guard = open `subjectteacher` row.
  - **Groups:** `PATCH /exams/paper-groups/{id}` (title, chapters, max marks; live lock
    409), `POST .../papers/{paper_id}/detach` (chapters naam se match, missing => 409
    naam ke saath, draft clone). Lock allowed-detach, locked-edit 409.
  - **Old Academics marks** (`classroom/{service,repository}`): section subject se,
    `SectionMarkEntryIn.classroom_subject_id`; `get_mark` (dead) delete.
  - **AI builder:** link fields + `_check_draft_links` (tenant, group xor paper, ek live
    draft per group/paper); usage ledger `classroom_subject_id`.
  - **Frontend:** types/service/view helpers, `ExamScheduleForm` (class exam =
    section subject picker; school exam = class + subject *naam* + chapter names; saved
    exam = labelled section papers; skipped toast), `DateSheet` (Shared badge, section,
    Own paper, shared-paper card), naya `PaperGroupDialog`, marks header, results columns
    per section paper, Academics marks, builder `classroomSubjectId`.
- **Tests:** `test_exam_migration.py` 10 (M3 on SQLite: expansion, group, marks via
  enrollment incl. promoted student, counts, aborts, no create), `test_exam_paper_groups.py`
  11 (expansion/skipped/by-name chapters/section marks/lock/detach/draft clone/max under
  marks/teacher/tenant/fixed queries), `test_classroom_exams.py` 15 + phase10 6 converted;
  frontend `view.test.ts` 15. Backend suite: 646 pass; baaki 12 fail purane aur Phase 3
  se alag (exams `created_by` SimpleNamespace x9, operations-auth route, phase1 NULL-year
  key, homework date). `tsc` clean; `node --test` 46/46; Prettier clean on touched files.
- **Deviations (decided, documented):** (1) source library / usage log class-level hai,
  isliye unka ambiguous section match **abort nahi**, NULL rehta hai (plan abort kehta tha);
  draft jisme subject+section dono hon aur match na ho woh abort. (2) `Mark.exam_id`
  M5 tak rehta hai. (3) M3 downgrade refuse karta hai.
- **Not done / intentional:** M3 abhi live DB par apply nahi (backup + approval, aur real
  PostgreSQL par dry-run). Browser smoke baaki. `exam_paper.class_id/subject_id`,
  `marks.exam_id/subject_id`, `paperdraft.class_id/subject_id/section_id`,
  `examsource.class_id/subject_id` M5 mein drop. Teacher/auth legacy
  `is_teacher_assigned_to_subject` abhi bhi (Phase 4.3). `getSubjects` hiring mein abhi
  bhi (Phase 4.6).
- **Phase 2 se pending fix:** `ExamScheduleForm` ka school-exam `/academics/subjects`
  dropdown ab hata diya (subject naam se).
- **Next:** Phase 4 (people, hiring, substitution, dashboard) — "next phase" ke baad.

### Phase 4 — code complete (22 Nov 2026; M4 not yet applied to the live DB)

- **Kya kiya:**
  - **Tags:** `employee.subject_tags varchar(500)` + helper `teachers/subject_tags.py`
    (normalise/split/mentions; >500 => 422, kabhi cut nahi). `teachersubject` model
    delete; staff create/update/list/read, rehire/delete, profile PUT
    `/teachers/profile/{id}/subject-tags` (purana `/subjects` route delete), Teachers
    directory `subjectTags`, profile `subjectTags`; workload matrix subject column ab
    **abhi ke open section-subject names** (koi school-wide naam roll-up nahi).
  - **Assignment:** `is_teacher_assigned_to_subject`/`can_teach_subject` + legacy
    `subject_id` scope path delete (callers pehle se `classroom_subject_id` par the).
  - **Substitution:** pool = active staff with a teaching role; "does not teach" refusal
    hata; tags mein subject ka naam => +10 (`LISTS_THE_SUBJECT`), reason "Lists X in their
    subjects" / "Free to cover"; non-matching teacher assign ho jata hai.
  - **Hiring:** `pipeline_hiring_table.subject_id` hata (model + schema), `subject_name`
    free text; `GET/PUT /hiring/subject-suggestions` (`school_setting hiring.subject_
    suggestions`, JSON list; default = is school ke current-year section-subject names).
  - **Dashboard:** timetable/homework names `ClassroomSubject` se; `subject_perf` empty
    (by-name roll-up nahi) — test se pinned.
  - **M4 `f4a5b6c7d8e9`:** tags backfill (alphabetical), hiring `subject_name` backfill
    (typed snapshot kabhi overwrite nahi), per-school suggestions seed, gate (har
    `teachersubject` row tags mein; `classroomsubject`/hiring/employee counts same; 500+
    => abort **drop se pehle**), phir `subject_id` + `teachersubject` drop. Downgrade refuse.
  - **Frontend:** hire form + interview form (free text + datalist suggestions),
    `useStaffHiring` suggestions query, drawer/list/MyStaffPanel `subjectTags`,
    `replaceSubjectTags`, dead `getSubjects/createSubject/updateSubject` + `SubjectRow`
    delete; demo seeder `subject_tags`.
- **Tests:** `test_people_subject_migration.py` 6, `test_people_subject_tags.py` 12 (tag text,
  hire/list round trip, non-matching teacher holds+ticks, suggestions default/saved/
  cross-school/not-a-link, candidate free text, fixed query count), substitution 24 (rewritten
  gate tests + exact +10 boost), profile/contracts converted. Backend: 664 pass, 12 fail (wahi
  purane Phase 3 se alag). `tsc` clean; `node --test` 46/46; Prettier clean.
- **Notes:** request base class text ko lowercase store karti hai, isliye tags aur candidate
  `subject_name` API se lowercase store hote hain (UI title-case karti hai; `mentions` case-
  insensitive hai). Drawer ka Subjects line read-only hai (inline editor nahi banaya).
- **Not done / intentional:** M4 live DB par apply nahi (backup + approval, real PostgreSQL
  dry-run). `Subject` table + legacy columns Phase 5 (M5). Browser smoke baaki.
- **Next:** Phase 5 (final cleanup + drop global subject + end-to-end) — "next phase" ke baad.

### Phase 5 — pending


