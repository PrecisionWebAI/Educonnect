# Course Feature — Phase Plan (EduConnect)

> **Status:** Phase 0 complete — 19 Nov 2026. Phase 1 se aage kuch shuru nahi hua.
> **Files:** yeh file = plan + progress log. `backend/phase2.md` = code se verify kiye
> gaye facts, corrections aur cross-phase reminders.
> **Language:** prose Hinglish; code, table/column names, API names, UI labels English.

---

## 0. Kaam kaise chalega

### 0.1 Phase discipline
- Har phase shuru karne se pehle: us phase ke subphases dobara padho, `phase2.md` ke
  reminders padho, aur current code us phase ke hisaab se deeply dekho.
- Purani phases mein bana hua code todna nahi hai.
- Har phase ke baad is file mein: checkbox `[x]`, aur Section 6 mein entry (kya kiya,
  files, tables/endpoints/components, tests, baaki, phase2.md mein kya add kiya).
- Ek phase khatam hone par summary do aur **ruko**. Agla phase sirf user ke
  "next phase" ke baad.

### 0.2 Loop aur terminal rules
- Sirf synchronous, khud khatam hone wali commands. Dev server / watch mode foreground
  mein nahi. Server chahiye to short-lived command ya timeout.
- Ek hi error par maximum 2 fix attempts; phir ruk kar error + analysis user ko batao.
- Lambe output ko filter karo (`Select-Object -First/-Last`, `Select-String`).
- Destructive command (drop/delete/force reset) user ko bataye bina nahi.

### 0.3 Testing rules
- Sirf us phase se juda test: us phase ka endpoint/table/component/migration.
- Poora suite nahi. Phase 10 mein hi Course feature ka end-to-end test.

### 0.4 Language
- `phase.md` / `phase2.md`: Hinglish. Baaki sab English.
- UI labels proper case. Dates school ke existing format mein.

### 0.5 Design aur codebase consistency
- Frontend: maujooda components/styles/spacing/tables/popups/tabs/badges/empty states
  reuse. Naya design system ya UI library nahi.
- Backend: existing router → service → repository pattern, auth dependency,
  `school_id` scoping, error format, pagination style (`X-Total-Count`), audit logging,
  alembic migrations.
- Existing `role` / `permission` / `rolepermission` / `user_role` reuse. Naya parallel
  permission system nahi.

### 0.6 Production aur scalability mindset
- Sab kuch per school aur per classroom section (`classroom_id`). Kuch hard-coded nahi.
- Har naye table mein `school_id` (DB mein NOT NULL), sahi FKs, indexes, unique
  constraints.
- N+1 nahi. Lists paginated. Counts (pending approvals, completion %) SQL aggregate se.
- Approve/Reject/Submit transaction mein + idempotent. Do reviewer ek hi week ek saath
  approve karein to race na bane (status/version check + row lock jahan DB de).
- Permission server par enforce; button chhupana kaafi nahi.
- School A ka data School B ko kabhi na dikhe.

---

## 1. Business Rules (agreed, final)

### 1.1 Subjects aur Classroom
- Fixed Course table hatega. **Verified:** wo table `syllabusprogress` thi aur migration
  `d3f1a8c5e2b7_course_chapters.py` (15 Nov 2026) mein already drop ho chuki hai. Ab
  subjects har classroom section ke rows honge (`classroomsubject`).
- Har section ke Course tab par **Add Subject** button. Table columns: Subject, Teacher,
  Lesson Plan, Total Chapters, Completed Chapters, lambi Progress Bar.
- Har row par **Edit**: teacher assign/change. Dropdown mein sirf us school ke **active**
  teachers.
- School ki ek master subject list (`subject`). Add Subject mein dropdown se pick; nahi
  mile to **Custom** se naya naam (e.g. English 1, English 2), wo list mein jud jata hai.
- Dropdown mein wo subjects na dikhein jo us section mein already add hain.
- Delete sirf tab jab koi approved plan ya completed chapter na ho. Warna **Archive**
  offer karo.

### 1.2 Weekly Lesson Plan
- Har subject row par **Lesson Plan** button; bada popup; month select.
- Tabs: Week 1–Week 4, aur Week 5 jab month mein ho. Har tab par date range (1 tareekh se
  month ke last date tak). Weekly off aur holidays hata kar sirf **real teaching days**.
- Teacher week-by-week plan bharta hai. **Draft state nahi.** Har week ka apna Submit
  button; dabate hi seedha principal ke paas.
- Official format (6 fields): Topics/Chapters to cover, Learning Objectives, Activities,
  Homework/Assignment, Teaching Resources, Assessment/Revision.
- Submit ke baad teacher ko har week ka status dikhe.

### 1.3 Approval Flow
- Principal aur uske upar ke saare roles approve/reject kar sakte hain.
- Row par count: "3 weeks submitted · 2 approved".
- Reviewer ko submitted weeks ki list; week par click karne par poora plan khule.
- Ek week, kai weeks, ya saare submitted weeks approve ho sakte hain.
- Reject par reason zaroori. Teacher ko reason dikhe, plan sudhar kar dobara submit kare.
- Statuses: Not Submitted, Submitted, Approved, Rejected (with reason). Draft nahi.
- Approved week locked. Badalne ke liye nayi submission + nayi approval, aur history save.

### 1.4 Teacher Change (mid-year)
- Purane teacher ke complete kiye chapters usi ke naam credit rahenge. Naya teacher wahin
  se aage badhega (A ne 3 kiye, B 4th se).
- Assignment history kabhi overwrite nahi hoti. Purani row band, nayi khulti hai.

### 1.5 Chapters aur Progress
- Teacher chapter tick karta hai. Date aur kis teacher ne complete kiya, record hota hai.
- Total/Completed/progress bar real chapters se; typed numbers se nahi.
- Section page ke upar **Course Completion** card us section ke saare subjects ka average
  dikhata hai. Subjects na ho to "No Subjects Yet".

### 1.5.1 Permissions (server par enforce)
- **Principal aur uske upar ke roles:** approve/reject, teacher assign/change, subject
  add/edit/delete/archive, chapter add/edit/delete, kisi bhi teacher ka course edit.
- **Teacher:** sirf apne subjects ke plans banana/submit karna aur apne subjects ke
  chapters tick karna. Apna hi course dekhna, kisi aur ka nahi.
- **Parent/Student view:** future phase (read-only, sirf approved weeks). Abhi scope mein
  nahi.

### 1.6 Teachers Area, naya "Course" tab
- Teachers tabs: List, Workload, Substitution, Attendance, Leave, Performance. List ke
  turant baad naya tab **Course**.
  - **Verified:** aaj ka UI "Attendance & Leave" ek hi tab mein rakhta hai; Course ko
    List ke baad daalenge (order: List, Course, Workload, Substitution, Attendance &
    Leave, Performance).
- Admin ke liye: pehle saare teachers ki list. Teacher kholne par uske saare subjects aur
  sections (current + past assignments), monthly lesson plan, har week ka plan aur status,
  aur chapter progress — jahan wo padha rahi hai ya padha chuki hai.
- Yahin se admin week approve/reject kar sakta hai — wahi Phase 7 ke endpoints aur data.
- Teacher list mein har teacher ke pending approvals ka count aur "behind" mark.
- Logged-in teacher ko sirf apna Course tab dikhega (wahi view, sirf apne data ke liye).
- Approve hone par teacher ko notification; Reject par bhi (reason ke saath).
- Principal ko pending-approval badge/notification. Jisne week submit nahi kiya use
  reminder.

### 1.7 Classroom List
- Classroom list ke section card par us section ka course completion % aur pending
  approvals ka count.

---

## 2. Current Database — Phase 0 mein code se verify kiya

> Neeche sirf verified sach hai. Jo prompt ke note se alag nikla, wo `phase2.md` mein
> detail se likha hai.

| Cheez | Verified state (code se) |
|---|---|
| Fixed Course table | `syllabusprogress` thi (classroom/subject counters). Migration `d3f1a8c5e2b7` ne drop kiya (rows zero hone par hi). Ab `chapter` + `chapterprogress` hi source hain. |
| School subject master | `subject(id, school_id, name, code)`; unique `(school_id,name)` aur `(school_id,code)`; `code` NOT NULL. `is_active` nahi hai. Seed me 13 subjects per school. |
| Assignment history | `subjectteacher(classroom_id, subject_id, teacher_id, academic_year_id, effective_from, effective_to)` — columns maujood hain, lekin **likhne ka rasta (service) purani row ko overwrite karta hai**; partial unique index bhi nahi hai. |
| Chapters | `chapter(school_id, class_id, subject_id, academic_year_id, sequence, name, planned_date)` class level; unique `(school_id,class_id,subject_id,academic_year_id,sequence)`. `chapterprogress(chapter_id, classroom_id, status, completed_on, completed_by_employee_id)` section level; unique `(chapter_id,classroom_id)`. Dono live. |
| Completion | `course/completion.py` — `by_section`, `for_section`, `for_subject`, `by_teacher`; `chapterprogress.status = "Completed"` count hota hai. Classroom card `syllabusPercent`, Teachers performance `course` component isi se. |
| Weekly off | `school_setting` key `attendance.weekly_off_days` (default `"6"`); `settings/calendar.py` `closures()`, `open_days()`, `count_open_days()`. Holidays `holiday(on_date..end_date, kind)`, extra open days `school_open_day`. |
| Teacher identity | Teacher = `employee`; `employee.user_id` → `app_user`. Teaching role `labels.TEACHING_ROLES`. Active filter: `employee.left_on IS NULL`, `deactivated_at IS NULL` (+ login `is_active`). |
| Teacher dropdown aaj | `/classroom/teachers` → `get_teacher_options` **saare staff** deta hai (koi teaching/active filter nahi). Isko Phase 4 mein theek karna hai. |
| Role hierarchy | `role(codename,label,description,is_system)` — koi level/rank column nahi. "Principal aur upar" permission se hoga. |
| Permission seeding | `permissions_repository.seed_permissions()` boot par `PermissionEnum` + `ROLE_PERMISSIONS_MAP` se rows/grants seed karta hai (idempotent). Naye codenames ke liye migration zaroori nahi. |
| Notifications | `notification(user_id, title, body, kind, event_type, entity_type, entity_id, dedupe_key, channel)`; single writer `main/notifications/events.py::notify()`; `PRINCIPALS` = `principal` + `vice_principal`. |
| Audit | `staffauditlog(employee_id, section, action, row_id, summary, changed_by_user_id)` append-only pattern. |
| Workload | `staffworkloadrule(weekly_periods, overload_percent, underload_percent)`, `timetableperiod`; matrix + capacity already exist. |
| Classroom list card | `ClassSectionCard` mein `syllabusPercent`, `subjectsTracked` already hai; pending approvals field nahi. |
| Section detail subjects | `repository.get_subject_rows()` **school ke saare subjects** deta hai (outer join se teacher), sirf section ke added subjects nahi. |
| Alembic head | `b7d2e4f1a9c3` (`open_day`). Naya migration isi ko `down_revision` karega. |
| Models registry | `app/core/schema.py::MODEL_MODULES` — naya `models.py` wahan list hona zaroori (`tests/test_structure.py` rule). |
| Raw SQL | `app/domains/**` mein text SQL allowed nahi (tenant filter bypass). Migrations mein allowed. |
| Existing tests | SQLite in-memory, `SQLModel.metadata.create_all`, scenario functions + pytest wrappers (`tests/test_classroom_course.py` pattern). |
| Frontend course UI | `SectionDetailPage` → `CoursePanel` (subject cards + chapter table). `ExamScheduleForm` bhi `getSectionCourse()` se options leta hai — response ke purane fields todna nahi. |
| Frontend tests | `node --test src/lib/course/view.test.ts` (Node 24, TS type-strip). Backend tests is machine par blocked (dekho `phase2.md`). |
| "LessonPlan.tsx" | Ye **lesson-detail card** hai (aaj ka lesson), weekly lesson plan nahi. Naya component naam `WeeklyLessonPlan*` rakhna hai. |

---

## 3. Design Decisions (D1–D10) — recommendation

### D1. `subject` reuse ya naya `school_subject`?
**Recommendation: reuse `subject`** + `is_active` + unique index `(school_id, lower(name))`.
- Pros: `subject.id` ko `paperdraft`, `examsource`, `homeworkassignment`,
  `timetableperiod`, `marks`, `exam_paper`, `chapter`, `teachersubject` already refer
  karte hain; ek hi master rahega, rename sab jagah follow karega. `department` bhi isi
  pattern (`is_active`) par hai.
- Cons: `code` NOT NULL — custom subject ke liye code generate karna padega (initials +
  counter, per school unique). Case-insensitive unique index banane se pehle duplicate
  check karna padega.
- Aapka default: Reuse + `is_active` + case-insensitive unique — **isse sehmat**, with
  duplicate pre-check.

### D2. Assignment history: `subjectteacher` reuse ya naya table?
**Recommendation: naya `classroomsubject` + `subjectteacher` ko uski history table banao.**
- `classroomsubject` = "is section mein ye subject hai" (teacher abhi assign nahi bhi ho
  sakta). `subjectteacher` = kaun kab padhaya (open row = aaj ka teacher).
- Pros: "subject add kiya, teacher baad mein" represent ho sakta hai; history per subject
  natural; lesson plan `classroomsubject` par tikega isliye teacher change par plan orphan
  nahi hota. Cons: ek naya table + backfill.
- `subjectteacher.classroom_subject_id` nullable add karenge; purane `classroom_id` /
  `subject_id` columns rahenge (existing modules/tests na tootein).
- Aapka default: New `classroom_subject` + `subjectteacher` as history — **sehmat**.

### D3. Chapters: `chapter` + `chapterprogress` reuse?
**Recommendation: reuse.** Class-level chapter (9-A aur 9-B same book/order), section-level
progress. `exam_paper_chapter` / `paperdraft` ko chhuna nahi.
- Pros: aaj ka Course tab, Classroom card, Teachers performance sab isi par chal rahe hain;
  dobara banana duplication + do numbers honge.
- Cons: ek section dusre se alag chapter order nahi rakh sakta. Agar kabhi zarurat pade to
  `classroomsubjectchapter` override baad mein (aaj scope mein nahi).
- Aapka default: Reuse — **sehmat**.

### D4. Lesson plan fields: columns ya JSON?
**Recommendation: alag text columns** (6 fields) + `format_version` int.
- Pros: query/report simple, validation seedha, koi JSON parsing nahi; prose ka case
  preserve karne ke liye request model `CanonicalRequest` se inherit **nahi** karega.
- Cons: naya field = migration. (JSONB flexible hota, par validate/report mushkil.)
- Aapka default: text columns + format version — **sehmat**.

### D5. Week boundaries
**Recommendation:** Week 1 = 1–7, 2 = 8–14, 3 = 15–21, 4 = 22–28, Week 5 = 29–month end
(sirf jab month mein 29+ din ho). `start_date`/`end_date` **store** karo; teaching days
live compute honge (`calendar.open_days`) taaki holiday edit turant dikhe.
- Pros: week numbers stable, range history mein bhi wahi rahegi. Cons: agar school apna
  week pattern badle to purane stored ranges wahi rehte hain (jo sahi hai).
- Aapka default: same — **sehmat**.

### D6. Approved week edit
**Recommendation:** versioned current row + immutable history snapshot; approved version
tab tak "effective" jab tak naya version approve na ho.
- `lessonplan` = latest version ka working row (`status` = latest version ka status,
  `version`, `approved_version`, `rejection_reason`).
- `lessonplanhistory` = har submitted version ka snapshot (content immutable; review
  verdict fields stamp hote hain).
- Approved week seedha editable nahi; "Request change" → naya version Submitted. Reject
  hone par purana approved version hi effective rehta hai; UI "Approved v2 · v3 Rejected:
  reason" dikhata hai.
- Pros: ek current row (reads simple), poora history, galti se approved plan gayab nahi.
- Cons: "effective vs latest" do concepts — response mein dono blocks dene padte hain.
- Aapka default: nayi version + purana approved snapshot history mein — **sehmat**, isi
  shape mein.

### D7. Course Completion average
**Recommendation:** per subject % = completed/total; total=0 wale subjects average se
bahar; koi subject nahi → "No Subjects Yet"; subjects hain par koi plan nahi →
"No Data Yet" (`None`, 0% nahi).
- Implementation: naya `completion.subject_average(session)` (subject-wise average).
  Purana `by_section()` aggregate (chapter-weighted) Teachers performance ke liye rahega.
- Note: Classroom card ka `syllabusPercent` aaj chapter-weighted hai; Phase 4 mein use
  subject-average par shift karenge taaki card aur Course tab ka top card same dikhe.
- Aapka default: same — **sehmat**.

### D8. "Behind" ki definition
**Recommendation:** sirf `chapter.planned_date < today` aur `status != Completed` wale
chapters. Jis subject ki koi planned date nahi, wo kabhi "behind" nahi. Teacher list ka
"behind" mark = us teacher ke current subjects mein aisa koi chapter ho.
- Aaj `course/service.py::_chapter_row` yahi karta hai (`behind`, `planned`) — reuse.
- Aapka default: same — **sehmat**.

### D9. Permission codenames
**Recommendation (6):**

| Codename | Kya deta hai | Kisko |
|---|---|---|
| `course.read` | Course tab / apna course dekhna | principal+, HOD, teacher |
| `course.plan` | apne subject ka weekly plan submit/edit, apne subject ke chapter tick | teacher, HOD, principal+ |
| `course.assign_teacher` | section mein teacher assign/change | principal+ |
| `course.manage` | subject add/archive/delete, chapter add/edit/delete, kisi bhi teacher ka course edit | principal+ |
| `course.approve` | week approve/reject, review list | principal+ (principal, vice_principal, school_admin, system_admin) |
| `course.view_all` | saare teachers ka course / teacher list | principal+ |

- `principal+` = principal + vice_principal + school_admin + system_admin (school_admin /
  system_admin ko `ALL_PERMISSIONS` se automatically mil jayenge).
- HOD: `course.read` + `course.plan` (apni teaching); `course.view_all` **nahi** — kyunki
  service department-scope nahi karta, aur poora school dikhana HOD ke liye zyada hoga.
  (Agar HOD ko department-wide view chahiye to batao — Phase 2 mein scope add hoga.)
- Teacher: `course.read` + `course.plan` only.
- Seeding: `PermissionEnum` + `ROLE_PERMISSIONS_MAP` update; boot seed khud grant kar dega.
- Aapka default: 4 codenames — **main 2 extra (`course.read`, `course.plan`) recommend
  karta hoon** taaki teacher ka read/submit alag ho aur `course.manage` sirf admin ke paas
  rahe.

### D10. Teacher change ke baad pending weeks
**Recommendation:** lesson plan `classroomsubject` par tika hai, teacher par nahi. Isliye:
- Not Submitted / Rejected weeks naya (current) teacher edit + submit kar sakta hai;
  rejection reason usi row par rehta hai.
- Submitted week jaise hai waise review hoti hai (purane teacher ke naam `submitted_by`).
- Approved week locked.
- Naya teacher purane teacher ke complete chapters ka credit nahi leta
  (`chapterprogress.completed_by_employee_id`).
- Aapka default: same — **sehmat**.

---

## 4. Phase Plan

### Phase 0: Study aur Plan (Agent sabse pehle ye karega) [x]
- [x] 0.1 Backend structure padha (models, routers, services, auth/permission deps,
      alembic, tests pattern). Summary Section 2 + `phase2.md`.
- [x] 0.2 Frontend padha (Classroom list, Section tabs, Teachers tabs, shared components,
      styles, API client, role/permission handling). Summary Section 2.
- [x] 0.3 Section 2 ke notes code se verify kiye (fixed Course table = dropped
      `syllabusprogress`; weekly off `school_setting`; teacher = employee + role;
      role hierarchy = codename only). Corrections `phase2.md`.
- [x] 0.4 D1–D10 par recommendation likhi (Section 3).
- [x] 0.5 Phase 1–10 ka code-aware plan likha (Section 5). **User approval pending.**

### Phase 1: Data Model aur Migration [x]
- [x] 1.1 `subject` extend: `is_active`; case-insensitive unique `(school_id, lower(name))`;
      duplicates pehle report.
- [x] 1.2 `classroomsubject` table (school, classroom, subject, year, status, timestamps);
      unique `(classroom_id, subject_id, academic_year_id)`.
- [x] 1.3 `subjectteacher` history: `classroom_subject_id`; ek open row per subject
      (partial unique); change = purani close + nayi open; overwrite nahi.
- [x] 1.4 `lessonplan` + `lessonplanhistory` tables; unique per subject/year/month/week;
      status check constraint; version fields.
- [x] 1.5 Migration `e2b8c4f7a1d9_course_lesson_plans.py` likhi (backfill + indexes +
      downgrade). **DB par apply nahi ki** — user approval ke baad (Phase 10 dry-run).

### Phase 2: Permissions aur Backend Guards [x]
- [x] 2.1 Naye permission codenames seed (D9), principal+ roles ko (seed/migration se,
      code mein hard-coded role names nahi).
- [x] 2.2 Reusable server dependencies/helpers: `can_manage_course`, `can_approve_course`,
      `is_own_course_teacher` (employee id se), sab school scoped.
- [x] 2.3 Helper `teaching_days(session, start, end)`: holidays + weekly off +
      `school_open_day` respect kare; unit test.
- [x] 2.4 Permission matrix test: admin allow, teacher own allow, teacher other deny,
      doosre school ka user deny.

### Phase 3: Subject Master aur Add Subject [x]
- [x] 3.1 Admin school subject list: dekhna, rename, deactivate. Proper case, duplicate
      (case-insensitive) block.
- [x] 3.2 API: section mein subject add; dropdown = school subjects minus already added;
      Custom option school list mein add kare.
- [x] 3.3 Section Course tab par Add Subject button + form (existing UI style). Add hote
      hi row dikhe; teacher optional.
- [x] 3.4 Delete/Archive rule: approved plan ya completed chapter ho to delete block,
      Archive offer. Controls sirf admin-level (server bhi check kare).

### Phase 4: Section Course Table aur Teacher Assignment [x]
- [x] 4.1 Table API (fixed number of queries, N+1 nahi): Subject, Teacher, Lesson Plan
      summary (current month), Total, Completed, %. `LessonPlanSummaryRead` +
      `lesson_plan` per row; `completionPercent` / `completionSubjects` / `subjectsCount`
      envelope.
- [x] 4.2 Table UI + lambi progress bar; loading/empty states; subject na ho to admin
      message.
- [x] 4.3 Edit panel: teacher assign/change; sirf active teachers; effective date;
      overload warning (workload data), block nahi.
- [x] 4.4 Teacher change par history row; purane teacher ke chapters usi ke naam; teacher
      cell par history link/tooltip.
- [x] 4.5 Course Completion card (D7) + "No Subjects Yet"; section header ka
      `syllabusPercent` bhi ab subject-average hai. Legacy route ka guard
      `course.assign_teacher`.

### Phase 5: Chapters aur Progress [x]
- [x] 5.1 Chapter add/edit/reorder/delete (admin) per subject; order maintain.
      `POST/GET /course/subjects/{cs}/chapters`, `PATCH/DELETE /course/chapters/{id}`;
      explicit sequence duplicate `409`; move = position + two-phase renumber.
- [x] 5.2 Teacher chapter tick/untick (sirf apne subject par); date + completed-by record.
      Existing tick hardened: `course.manage` bhi office maana jata hai; teacher row se
      `canEdit=false`, `canTick=true` sirf current holder.
- [x] 5.3 Teacher change ke baad continue-from behaviour verify (A ne 3, B 4th se).
      Test: A chapter 1, handover, B chapter 2; A chapter 3 par `403`; shares 1/1.
- [x] 5.4 Total/Completed/progress sirf real chapters se; table aur card sync.
      Delete blocked by any completed progress (409) + `exam_paper_chapter` (409);
      add/delete/tick se `section_course` aur Classroom card dono badalte hain.

### Phase 6: Weekly Lesson Plan, Teacher Side [x]
- [x] 6.1 Week ranges generate (D5) + real teaching days (Phase 2 helper); start/end store.
      `lesson_plans.month_plan` month → Week 1-5; `start_date`/`end_date` plan row par
      store, teaching days calendar se.
- [x] 6.2 Lesson Plan popup: month select, Week tabs (5 jab ho), range + teaching days.
      `WeeklyLessonPlanDialog` + `Tabs`; current month default.
- [x] 6.3 Official format form (6 fields), validation, har week ka Submit (draft nahi);
      submit par status Submitted + history snapshot.
      `topics` + `learning_objectives` required, 2000-char cap; `expectedVersion`;
      working row + `lessonplanhistory` ek transaction.
- [x] 6.4 Har week ka status teacher ko; Rejected par reason; sudhaar kar resubmit.
      Status badge + version + submitted-by; rejection reason visible; resubmit version +1.
- [x] 6.5 Approved week locked (read-only); edit flow D6 ke hisaab se.
      `canRequestChange` → change mode → `intent="change"`; approved snapshot visible,
      `approved_version` intact.

### Phase 7: Approval Flow [x]
- [x] 7.1 Reviewer list: submitted weeks (poora plan list mein nahi); click par full plan.
      `GET /course/reviews` + `/count`; `ReviewRow` mein six fields; `X-Total-Count`.
- [x] 7.2 Approve: ek/kai/saare; transaction + idempotent + race-safe.
      `POST /lesson-plans/{id}/approve` (same version dobara → 200), `approve-many`
      valid rows commit + stale `skipped`, expected_version mismatch → 409.
- [x] 7.3 Reject: reason mandatory; status Rejected; teacher ko reason.
      `RejectIn` (prose preserved, blank/1000+ → 422); history rejected_* stamp;
      notification `course.week_rejected` with reason.
- [x] 7.4 Row par "3 weeks submitted · 2 approved"; teacher change ke baad pending
      behaviour (D10).
      Row summary already Phase 4; pending week naye current teacher ke liye editable,
      approved locked (test).
- [x] 7.5 Approved week change flow: nayi version, nayi approval, history preserved.
      Phase 6 `intent="change"` + Phase 7 approve nayi version; `approved_version` tab
      tak purana rehta hai jab tak naya approve na ho.

### Phase 8: Teachers > Course Tab [x]
- [x] 8.1 Teachers area mein List ke turant baad Course tab (existing tab component).
      `CourseTab.tsx`; `StaffTab` mein "Course"; teacher-only branch ka My Course
      `MyStaffPanel` ke andar.
- [x] 8.2 Admin view: teachers list + pending approvals count + "behind" mark (D8);
      paginated, search, single aggregate query.
      `teacher_list`: subjects/sections, pending approvals, behind subjects, D7
      completion; fixed queries, no per-teacher N+1.
- [x] 8.3 Teacher detail: subjects/sections (current + past), monthly plan, week statuses,
      chapter progress (existing UI style).
      `GET /course/teachers/{id}`; `TeacherCourseDetail` cards + weeks + chapters;
      `WeeklyLessonPlanDialog` reuse.
- [x] 8.4 Yahin se approve/reject — Phase 7 ke hi endpoints.
      Plan popup approver controls (same `approve`/`reject` routes).
- [x] 8.5 Teacher login par sirf apna course; doosre teacher ka data server par block.
      `teacher_list` self row, `teacher_detail` other → `404`, `/course/my` token-based.

### Phase 9: Notifications, Reminders, Badges, Overview [x]
- [x] 9.1 Submit par approvers ko notification; approve/reject par teacher ko (reject mein
      reason). Existing `notification`, `dedupe_key`.
      `course_approver_user_ids` (`course.approve` grants) + submit hook; approve/reject
      already notify the submitter (Phase 7).
- [x] 9.2 Reminder job unsubmitted weeks ke liye (`core/scheduler.register_job`).
      `course/reminders.py`, job `course.reminders`; finished weeks without
      Submitted/Approved, current teacher, dedupe per section-week.
- [x] 9.3 Pending-approval badge (Teachers Course tab + Classroom).
      Teachers Course stats/tile + per-row badge; Classroom card `pendingApprovals`.
- [x] 9.4 Classroom list card par completion % + pending approvals.
      `SectionCard.pendingApprovals` + existing D7 `syllabusPercent`; mini-row prints both.
- [ ] 9.5 (Optional, user se poochho) Principal overview screen.
      **Skipped pending confirmation** — no dedicated overview screen built.

### Phase 10: Final Integration, Hardening aur Testing [x]
- [x] 10.1 E2E: subject add → teacher assign → chapters → plan submit → approve/reject →
      teacher change → notifications.
      `tests/test_course_end_to_end.py` — master + custom subject, 2 chapters, 2 weeks,
      approve/reject/resubmit/approve, handover, tick, notifications.
- [x] 10.2 Classroom Course tab aur Teachers Course tab ke numbers/status match.
      E2E: `section_course.percent == teacher_detail.percent == summary` (100%);
      week statuses Approved; teacher list pending 0.
- [x] 10.3 Permission + multi-school isolation final check (server side).
      Course tests + permission matrix green; E2E binds a second school and asserts
      section/teacher reads are `404`.
- [~] 10.4 Performance: indexes, query count, badi list speed; migration up/down dry-run.
      Indexes reviewed (model/migration); route tests green. Migration single head +
      downgrade contract test added. **Actual `upgrade → downgrade → upgrade` blocked**:
      no local Postgres backup/approval, and offline `--sql` fails because the migration
      inspects the live schema (by design). Needs a maintenance window.
- [ ] 10.5 Cleanup: unused code, purane fixed course references, `phase.md`/`phase2.md`
      final; Parent/Student view "future phase" note.

---

## 5. Phase-wise Detailed Plan

> Paths `backend/` ke andar ke hain jab tak `frontend/` na likha ho. Har phase ke end par
> sirf us phase ke relevant tests chalane hain.

### Phase 1 — Data Model aur Migration

**Files**
- `backend/app/domains/academic/classroom/academics/models.py`
  - `SubjectBase`/`Subject`: `is_active: bool = Field(default=True)` (+ `updated_at`).
  - `SubjectTeacherBase`/`SubjectTeacher`: `classroom_subject_id: UUID | None`
    (`foreign_key="classroomsubject.id"`, index); table args mein partial unique index
    `uq_subjectteacher_open_subject` on `classroom_subject_id WHERE effective_to IS NULL`
    (`postgresql_where` + `sqlite_where`, pattern `notification` model se).
- `backend/app/domains/academic/classroom/course/models.py` (**new**)
  - `ClassroomSubject` → table `classroomsubject`
    - `classroom_id` FK `classroom.id`, `subject_id` FK `subject.id`,
      `academic_year_id` FK `academic_year.id` (indexes)
    - `status: str = "Active"` (`Active` / `Archived`), `archived_at`,
      `archived_by_user_id`, `created_by_user_id`, `created_at`, `updated_at`
    - unique `(classroom_id, subject_id, academic_year_id)`; index
      `(school_id, classroom_id, status)`
  - `LessonPlan` → table `lessonplan`
    - `classroom_subject_id` FK, `academic_year_id` FK, `year: int`, `month: int`,
      `week_no: int` (1–5), `start_date`, `end_date`
    - 6 prose fields: `topics`, `learning_objectives`, `activities`, `homework`,
      `resources`, `assessment` (`sa.Text`); `format_version: int = 1`
    - `status` (`Submitted` / `Approved` / `Rejected`; Not Submitted = row ka na hona),
      `version: int = 1`, `approved_version: int | None`
    - `submitted_by_employee_id`, `submitted_at`, `reviewed_by_user_id`, `reviewed_at`,
      `rejection_reason`, `created_at`, `updated_at`
    - unique `(classroom_subject_id, academic_year_id, year, month, week_no)`;
      index `(school_id, status)`, `(classroom_subject_id, year, month)`,
      `(school_id, submitted_by_employee_id)`
    - `CheckConstraint` status ke liye + `week_no BETWEEN 1 AND 5` + `month BETWEEN 1 AND 12`
  - `LessonPlanHistory` → table `lessonplanhistory`
    - `lesson_plan_id` FK, `version`, sabhi 6 content fields, `start_date`, `end_date`,
      `submitted_by_employee_id`, `submitted_at`, `approved_at`, `approved_by_user_id`,
      `rejected_at`, `rejected_by_user_id`, `rejection_reason`, `created_at`
    - unique `(lesson_plan_id, version)`; append-only (koi update/delete endpoint nahi)
- `backend/app/core/schema.py` — `MODEL_MODULES` mein `"academic.classroom.course"` add.
- `backend/alembic/versions/e2b8c4f7a1d9_course_lesson_plans.py` (**new**,
  `down_revision = "b7d2e4f1a9c3"`)

**Migration steps (upgrade)**
1. `subject.is_active` add (server_default `true`, NOT NULL), phir default hatao.
2. Case-insensitive duplicates check:
   `SELECT school_id, lower(name), count(*) FROM subject GROUP BY 1,2 HAVING count(*)>1`.
   Koi row mile to migration **abort** + list print (data change nahi).
3. `CREATE UNIQUE INDEX uq_subject_school_name_lower ON subject (school_id, lower(name))`.
4. `classroomsubject` create + indexes/unique.
5. Backfill `classroomsubject`: distinct `(classroom_id, subject_id, academic_year_id)`
   from `subjectteacher`; jahan year NULL ho wahan school ka `academic_year.is_current`
   row; current year na ho to school ka earliest year; dono na ho to row skip + count print.
   `status = 'Active'`.
6. `subjectteacher.classroom_subject_id` add + FK + index; backfill matching
   `(classroom_id, subject_id)` + year (ya NULL year).
7. Open-row duplicates check: `subjectteacher` mein per `classroom_subject_id` (ya legacy
   `(classroom_id,subject_id)`) ek se zyada `effective_to IS NULL` ho to abort + list.
8. Partial unique indexes:
   `uq_subjectteacher_open_cs ON subjectteacher (classroom_subject_id) WHERE effective_to IS NULL`
   aur legacy `uq_subjectteacher_open_legacy ON subjectteacher (classroom_id, subject_id)
   WHERE effective_to IS NULL AND classroom_subject_id IS NULL`.
9. `lessonplan`, `lessonplanhistory` create + indexes/unique/checks.

**Downgrade** (data loss note ke saath): tables drop → open-row indexes drop → column drop
→ `classroomsubject` drop → `subject` index + column drop. Lesson plan data downgrade par
jaata hai, isliye production par chalane se pehle backup.

**Implemented (19 Nov 2026):** model file + `MODEL_MODULES` + migration likhi. Migration
ke helpers: `_subject_flags`, `_create_classroom_subject`, `_backfill_classroom_subject`
(`subjectteacher` + `chapter` se, `ON CONFLICT DO NOTHING`), `_link_subject_teacher`
(backfill + duplicate abort + partial indexes), `_create_lesson_plan`,
`_create_lesson_plan_history`, aur poora `downgrade`. **DB par apply nahi ki.**

**Tests:** `backend/tests/test_course_schema.py` (new) — 7 scenarios: `is_active` retire,
one section-subject per session, one **open** teacher row (close → new allowed), one plan
per week, one history snapshot per version, closed status vocabulary (Draft refused),
named keys declared. Results: 7/7 pass; `test_classroom_course.py` 5/5;
`test_phase1_schema.py` + `test_phase2_schema.py` 21/21; ruff check + format clean.
(SQLite partial indexes ka behaviour Postgres se alag ho sakta hai — Phase 10 dry-run.)

**Risks:** `subject` par already Title Case rows ho sakti hain (migration `f9e0f1a2b3d2`
ne lowercase kiya tha, par naye rows kisi purane script se aa sakte hain) — duplicate
abort isliye. Backfill ka year resolution Phase 3 ke "Add Subject" se pehle tay hona
chahiye. Agar `subjectteacher` mein ek hi subject ke do open rows mile to migration
**abort** karegi (data change nahi) — pehle unhe close karna hoga.

### Phase 2 — Permissions aur Backend Guards

**Files**
- `backend/app/domains/auth/permissions.py`
  - `PermissionEnum`: `course.read`, `course.plan`, `course.assign_teacher`,
    `course.manage`, `course.approve`, `course.view_all`.
  - `TEACHER_PERMISSIONS`: `course.read`, `course.plan`.
  - `HOD_PERMISSIONS`: `course.read`, `course.plan`.
  - `PRINCIPAL_PERMISSIONS`: chhe ke chhe.
  - `VICE_PRINCIPAL_PERMISSIONS`: principal list inherit karti hai, isliye automatically.
  - `SCHOOL_ADMIN_PERMISSIONS` / `SYSTEM_ADMIN_PERMISSIONS` already `ALL_PERMISSIONS` se.
- `backend/app/domains/academic/classroom/course/scope.py` (**new**)
  - `is_own_course_teacher(session, user, classroom_subject_id) -> bool` — current open
    `subjectteacher.teacher_id` == caller ka `employee.id`
  - `may_read_section_course(session, user, classroom_id) -> bool` — `course.view_all` /
    `course.manage` / `course.approve`; warna teacher ke liye sirf apne
    `classroom_subject` rows
  - `may_edit_plan(session, user, cs) -> bool` — `course.plan` + current holder (ya
    `course.manage`)
  - `may_manage_section`, `may_assign_teacher`, `may_approve`
  - `visible_teacher_ids(...)` (Phase 8 ka base)
- `backend/app/domains/academic/classroom/course/teaching_days.py` (**new**)
  - `teaching_days(session, start, end) -> list[date]` → `settings.calendar.open_days`
  - `teaching_day_count(...)`
  - `week_ranges(session, year, month) -> list[WeekRange]` (D5 ka ek hi implementation)
- `backend/tests/test_course_permissions.py` (**new**) — SQLite; roles/permissions seed
  karke: admin allow, teacher own allow, teacher other `403`, other-school `404`,
  teacher-only section read filter.

**Implemented (19 Nov 2026):**
- `permissions.py`: chhe codenames; principal + vice-principal (inherits) + school/system
  admin ko chhe ke chhe; teacher aur HOD ko sirf `course.read` + `course.plan`.
- `course/scope.py`: `can_read_course`, `can_plan_course`, `can_manage_course`,
  `can_assign_teacher`, `can_approve_course`, `can_view_all_courses`, `employee_of`,
  `may_read_section_course`, `is_own_course_teacher`, `may_edit_plan`,
  `may_read_teacher_course`, `visible_course_subject_ids`.
  - Legacy assignment rows (`classroom_subject_id` NULL) bhi "own" maane jaate hain.
  - School check `select(...)` se hota hai, `session.get` se nahi — identity map tenant
    filter bypass na kare.
- `course/teaching_days.py`: `get_teaching_days`, `teaching_day_count`, `week_ranges`
  (Week 1–5, `start_date`/`end_date`, `teaching_days`, `label`), `WeekRange`.
- Seeding khud boot par hoti hai (`seed_permissions`); koi migration nahi. Static matrix
  test bhi pass (`ALL_PERMISSIONS` == enum, duplicate nahi, har codename kisi role ke
  paas).

**Tests (19 Nov 2026):**
- `tests/test_course_permissions.py` — 6 scenarios (office rights, own subject, teacher
  change, other school, visible filter, read-own-only) — **6/6 pass**.
- `tests/test_course_teaching_days.py` — 6 scenarios (week cut/fifth week, Sunday +
  holiday, dated week off, open-day override, weekly-off setting, bad input) — **6/6
  pass**.
- `tests/test_permission_matrix.py` (+ naya course-rights test) — **12/12 pass**.
- `ruff check` + `ruff format --check` — clean (6 files).

**Seeding**
- Koi migration nahi: `seed_permissions()` boot par naye codenames + grants daal deta hai.
  (Agar frozen DB migration chahiye to ek chhoti data migration `permission` +
  `rolepermission` insert karegi — default: nahi.)
- Role names code mein hard-code nahi; kaun "principal+" hai wo permission se decide hota
  hai (`ROLE_PERMISSIONS_MAP` data hai).

**Notes**
- `RequirePermission("course.read")` route par; **section-level** filtering service karega
  (aaj `classes.read` `section_id` ko scope nahi karta — `phase2.md`).
- Naya guard system nahi; `RequirePermission` + `scope.py`.

**Risks:** `course.view_all` na hone par teacher ko sirf apne subjects dikhane hain —
filter `SectionCourseRead.subjects` par service mein, router mein nahi.

### Phase 3 — Subject Master aur Add Subject

**Backend files**
- `backend/app/domains/academic/classroom/academics/schemas.py`
  - `SubjectRead`: `id`, `name`, `code`, `isActive`; `SubjectCreate(name, code?)`,
    `SubjectUpdate(name?, isActive?)` (`CanonicalRequest` — name lowercase store hoga).
- `backend/app/domains/academic/classroom/academics/repository.py`
  - `get_subjects(session, include_inactive=False)`
  - `find_subject_by_name(session, name)` → `func.lower(name)` compare
  - `next_subject_code(session)` → initials + number (e.g. `ENG1`), per school unique
- `backend/app/domains/academic/classroom/academics/service.py`
  - `create_subject`, `update_subject` (rename duplicate → `409`); deactivate se dropdown
    se hat jata hai, rows/FKs intact.
- `backend/app/domains/academic/classroom/academics/router.py`
  - `POST /academics/subjects` (`course.manage`)
  - `PATCH /academics/subjects/{subject_id}` (`course.manage`)
  - `GET /academics/subjects?include_inactive=false` (existing route extend)
- `backend/app/domains/academic/classroom/course/service.py`
  - `add_subject(session, section_id, user, subject_id=None, name=None)`:
    current academic year (na ho to `409` "Set the current session first");
    archived row mila to restore; duplicate active → `409`;
    custom name → `academics.create_subject` + `classroomsubject`.
  - `archive_subject`, `restore_subject`, `delete_subject`:
    approved lesson plan ya `chapterprogress` completed → `409` + `canArchive: true`;
    hard delete sirf jab koi `lessonplan` row hi na ho.
  - `section_course()` ka source = `classroomsubject` (legacy `subjectteacher` rows bhi
    include, jinka `classroom_subject_id` null ho).
- `backend/app/domains/academic/classroom/course/router.py`
  - `POST /classroom/sections/{section_id}/subjects` (`course.manage`)
  - `PATCH /course/subjects/{classroom_subject_id}/archive` / `.../restore`
  - `DELETE /course/subjects/{classroom_subject_id}`
- `backend/app/domains/academic/classroom/course/schemas.py` — request/response models.
- `backend/tests/test_course_subjects.py` (**new**).

**Frontend files**
- `frontend/src/services/academics.service.ts` — `getSubjects(includeInactive?)`,
  `createSubject`, `updateSubject`.
- `frontend/src/services/course.service.ts` — `addSectionSubject`,
  `archiveCourseSubject`, `restoreCourseSubject`, `deleteCourseSubject`.
- `frontend/src/types/index.ts` — `SubjectRow.isActive`; naye course row fields.
- `frontend/src/components/features/classroom/course/AddSubjectDialog.tsx` (**new**) —
  `Dialog` + `Select` (master subjects minus already-added) + "Custom subject" `Input`.
- `frontend/src/components/features/classroom/course/CourseTable.tsx` (**new**, basic) —
  `Table` columns: Subject | Teacher | Lesson Plan | Total | Completed | Progress.
- `frontend/src/components/features/classroom/course/CoursePanel.tsx` — Add Subject
  button (sirf `course.manage`), toolbar, table, empty state "No subjects added yet".
- `frontend/src/lib/course/view.ts` — `subjectOptions()`, `canDeleteSubject()`,
  `archiveOffer()` + `view.test.ts` tests.

**Rules:** dropdown server se (already-added hide server-side query mein); Custom naam
`subject` master mein judta hai; delete/archive controls sirf permission par (server bhi
check kare).

**Risks:** `get_subject_rows()` (section detail) aaj **saare** school subjects deta hai —
Course tab ka source badalne se Exams/Timetable dropdowns na tootein; unhe chhedna nahi.
`add_subject` current year ke bina fail kare, chupke year create na kare.

**Implemented (19 Nov 2026):**
- `academics`: `GET /academics/subjects?include_inactive=`, `POST /academics/subjects`,
  `PATCH /academics/subjects/{id}` (`course.manage`). Name lower-case + case-insensitive
  duplicate `409`, code minted (`E1`, `ENG2`) when omitted.
- `course`: `GET .../available-subjects`, `POST .../subjects`,
  `PATCH /course/subjects/{id}/archive|restore`, `DELETE /course/subjects/{id}`
  (`course.manage`, service bhi check karta hai).
- `section_course` ka source ab `classroomsubject` (+ legacy `subjectteacher` rows); GET
  guard `course.read`, `include_archived` query; per-row flags `canManage`,
  `canAssignTeacher`, `canArchive`, `canRestore`, `canDelete`.
- Delete rule: koi `lessonplan` row ya completed chapter → `409` + "archive instead";
  empty row apne unstarted progress + assignment history ke saath delete hota hai.
- Frontend: `CourseTable` (Subject/Teacher/Lesson Plan/Total/Completed/lambi bar/actions),
  `AddSubjectDialog` (master minus added + Custom), `SubjectMasterDialog` (rename/retire),
  `CoursePanel` rewrite (toolbar, show archived, chapters popup, delete confirm).
- Tests: `tests/test_course_subjects.py` 7/7; `tests/test_classroom_course.py` 5/5
  (legacy course behaviour intact); `node --test src/lib/course/view.test.ts` 8/8;
  `tsc --noEmit` clean; backend ruff clean.

**Note:** "Lesson Plan" column abhi "No plan" dikhata hai — weekly plan button/summary
Phase 6 mein aayega. Teacher assign/edit Phase 4. `CourseBar.tsx` ab panel se use nahi
hota (Phase 6 mein review/cleanup).

### Phase 4 — Section Course Table aur Teacher Assignment

**Backend files**
- `backend/app/domains/academic/classroom/course/repository.py` (**new**) — table read ek
  saath (N+1 nahi):
  - `subject_rows(session, classroom_id, year_id)` → `classroomsubject` + `subject`
    (active/archived) + current `subjectteacher` + `User.full_name` (ek query)
  - `chapter_totals(session, class_id, year_id)` → `{(subject_id): count}` (aggregate)
  - `completed_totals(session, classroom_id, year_id)` → `{(subject_id): count}`
    (`chapterprogress.status == "Completed"`)
  - `lesson_plan_counts(session, classroom_subject_ids, year, month)` →
    `{(cs_id): (submitted, approved, rejected, latest_status, latest_version)}`
    (GROUP BY, ek query)
  - `pending_approvals(session, classroom_id=None)` → count (Phase 9 ka badge bhi isi se)
  - `teacher_periods(session, employee_id)` → timetable periods (workload warning)
- `backend/app/domains/academic/classroom/course/service.py`
  - `section_course()` — rows + per-subject chapter list; `percent` D7 ke hisaab se;
    `lesson_plan` summary; `can_*` flags; teacher ke liye sirf apne rows (scope).
  - `assign_teacher(session, cs_id, teacher_id, effective_from, user)`:
    - active teacher check (`left_on`/`deactivated_at` null + teaching role)
    - same teacher & open row → no-op (idempotent)
    - open row close: `effective_to = effective_from - 1 day` (agar same-day row hai to
      usi din replace); nayi row open (`effective_from`, `effective_to=None`,
      `classroom_subject_id`, `academic_year_id`)
    - `staffauditlog` row (section `course`, action `assigned`/`changed`, summary)
    - workload warning (non-blocking) response mein
  - `teacher_history(session, cs_id)`
  - `completion.subject_average()` (Phase 1/4) + `SectionCourseRead.completion_percent`
- `backend/app/domains/academic/classroom/course/router.py`
  - `PUT /course/subjects/{classroom_subject_id}/teacher` (`course.assign_teacher`)
  - `GET /course/subjects/{classroom_subject_id}/teachers` (`course.read`)
- `backend/app/domains/academic/classroom/course/schemas.py` — `TeacherAssignIn`,
  `TeacherAssignResult(warning?)`, `CourseTeacherRead` (existing), table row fields.
- `backend/app/domains/academic/classroom/repository.py` — `get_active_teacher_options`
  (teaching role + active filters; existing `get_teacher_options` ko replace/alias).
- `backend/app/domains/academic/classroom/service.py` — `assign_subject_teacher`
  (legacy endpoint) ko history-aware banao: `classroomsubject` ensure + close/open;
  overwrite band.
- `backend/tests/test_course_teachers.py` (**new**).

**Frontend files**
- `frontend/src/components/features/classroom/course/TeacherAssignDialog.tsx` (**new**) —
  active teachers `Select`, effective date (`date-picker`), warning `Badge`/text,
  Save → invalidate `["course","section",sectionId]` + `["classroom"]`.
- `frontend/src/components/features/classroom/course/CourseTable.tsx` — columns + lambi
  progress bar (`CourseBar` reuse), Edit button, archive/delete menu, lesson-plan cell
  ("3 submitted · 2 approved" / "No plan").
- `frontend/src/components/features/classroom/course/CoursePanel.tsx` — table + dialogs;
  `usePermission("course.manage")` / `course.assign_teacher` / `course.read`.
- `frontend/src/components/features/classroom/course/CourseCompletionCard.tsx` (**new**) —
  D7 average, "No Subjects Yet" / "No Data Yet".
- `frontend/src/components/features/classroom/SectionDetailPage.tsx` — card top par
  render (Course tab ke andar ya page ke top; spec: section page ke upar).
- `frontend/src/services/course.service.ts` — `assignCourseTeacher`,
  `getCourseTeacherHistory`.
- `frontend/src/lib/course/view.ts` — `progressWidth`, `lessonPlanSummary`,
  `historyLabel` + tests.

**Rules:** sirf active teachers; history kabhi overwrite nahi; purane teacher ke chapters
ka credit usi ke naam (`completed_by_employee_id`); overload warning block nahi.

**Tests (relevant):** teacher change → two rows, first closed; same teacher no-op;
inactive teacher `422/409`; history endpoint order; percent = subject average; card value
= course tab value.

**Risks:** `subjectteacher` par legacy open rows hain (backfill ke baad bhi) — assign
karte waqt `classroom_subject_id` null wali open row bhi close karo, warna do teachers
"current" dikhenge.

### Phase 5 — Chapters aur Progress

**Backend files**
- `backend/app/domains/academic/classroom/course/service.py`
  - `add_chapter(session, cs, name, sequence?, planned_date?, user)` — `chapter` class +
    subject + current year par create; `sequence` na do to `max+1`; duplicate sequence →
    `409`; **saare sections** ke liye same chapter (D3).
  - `update_chapter(...)` — name/planned_date/sequence; reorder ek transaction mein
    (temporary negative sequence ya ordered rewrite) + unique constraint safe.
  - `delete_chapter(...)` — koi `chapterprogress` completed ho to `409`; warna progress
    rows + chapter delete (transaction).
  - `tick_chapter(...)` — `course.plan` + current holder (ya `course.manage`/legacy
    `classes.update`); Completed par `completed_on = today`,
    `completed_by_employee_id = employee.id`; untick par dono clear.
  - `chapter_row(...)` — `ahead` / `behind` D8 ke hisaab se.
- `backend/app/domains/academic/classroom/course/router.py`
  - `GET /course/subjects/{cs_id}/chapters` (`course.read`)
  - `POST /course/subjects/{cs_id}/chapters` (`course.manage`)
  - `PATCH /course/chapters/{chapter_id}` (`course.manage`)
  - `DELETE /course/chapters/{chapter_id}` (`course.manage`)
  - existing `PATCH /course/chapters/{chapter_id}/progress` (`course.read` + service guard)
- `backend/app/domains/academic/classroom/course/schemas.py` — `ChapterCreate`,
  `ChapterUpdate`, `ChapterRowRead` (existing extend: `can_edit`, `can_tick`).
- `backend/tests/test_course_chapters.py` (**new**).

**Frontend files**
- `frontend/src/components/features/classroom/course/ChapterEditorDialog.tsx` (**new**) —
  add/edit dialog (`Dialog`, `Input`, `date-picker`), reorder buttons (up/down).
- `frontend/src/components/features/classroom/course/chapter-columns.tsx` — Edit/Delete
  column sirf `canEdit` par; tick existing.
- `frontend/src/components/features/classroom/course/CoursePanel.tsx` — "Chapters" panel
  mein Add Chapter (admin), table, progress refresh.
- `frontend/src/services/course.service.ts` — `getChapters`, `createChapter`,
  `updateChapter`, `deleteChapter`.
- `frontend/src/lib/course/view.ts` — `reorderSequence`, `chapterTotals` + tests.

**Rules:** total/completed/progress sirf `chapter`/`chapterprogress` se; typed numbers
kahin store nahi. Chapter add karne se section table + completion card turant badlein
(query invalidate).

**Tests:** add chapter shows in 9-A and 9-B (class-level); duplicate sequence `409`;
reorder keeps order; tick by wrong teacher `403`; tick by current teacher records date +
employee; teacher change ke baad B 4th chapter tick kare to A ke 3 chapters A ke naam;
delete blocked when any section completed.

**Risks:** `exam_paper_chapter` / `paperdraft` chapters ko reference karte hain — chapter
delete se pehle un par FK hona check karo (aaj FK hai to delete `409` aayega; use
friendly message mein badlo).

### Phase 6 — Weekly Lesson Plan, Teacher Side

**Backend files**
- `backend/app/domains/academic/classroom/course/lesson_plans.py` (**new** service) —
  - `month_plan(session, cs, year, month, user)` → weeks 1..N (D5), ranges, teaching days
    (`teaching_days.py`), harness/status, latest + approved snapshot, rejection reason,
    permitted actions
  - `submit_week(session, cs, year, month, week_no, payload, user, expected_version)`:
    transaction; current holder only; `expected_version` mismatch → `409`; version+1;
    status `Submitted`; snapshot `lessonplanhistory` (same transaction); submitter
    employee id; notify approvers (Phase 9 hook, abhi placeholder)
  - validation: 6 fields mein kam se kam `topics` + `learning_objectives` required;
    max length limits; week range ke bahar submit nahi
  - `approved week` par direct submit nahi: naya version tabhi jab caller "change request"
    kare (payload `intent: "change"`), warna `409`
- `backend/app/domains/academic/classroom/course/repository.py` — plan row/snapshot
  queries (month ek query, history ek query).
- `backend/app/domains/academic/classroom/course/router.py`
  - `GET /course/subjects/{cs_id}/lesson-plans?year=&month=` (`course.read`)
  - `PUT /course/subjects/{cs_id}/lesson-plans/{year}/{month}/{week_no}`
    (`course.plan`; service holder check)
- `backend/app/domains/academic/classroom/course/schemas.py` — `LessonPlanWeekRead`,
  `LessonPlanContent(in)`, `LessonPlanSubmitIn(expected_version, intent?)`.
- `backend/tests/test_course_lesson_plans.py` (**new**).

**Frontend files**
- `frontend/src/components/features/classroom/course/WeeklyLessonPlanDialog.tsx`
  (**new**) — bada `Dialog`, month `Select`, `Tabs` Week 1..5, har tab par range + teaching
  days, 6 `Textarea`s, status `Badge`, Submit (per week), rejected reason, approved
  read-only.
- `frontend/src/components/features/classroom/course/useCourseLessonPlan.ts` (**new**) —
  `useApiQuery` + `useMutation` (submit), invalidate `["course", ...]`.
- `frontend/src/components/features/classroom/course/CourseTable.tsx` — Lesson Plan button
  + summary cell.
- `frontend/src/services/course.service.ts` — `getLessonPlanMonth`, `submitLessonPlanWeek`.
- `frontend/src/lib/course/lesson-plan.ts` (+ `lesson-plan.test.ts`) — week ranges, status
  words, required-field validation, "teaching days" label. (Pure functions, `node --test`.)
- `frontend/src/types/index.ts` — lesson plan types.

**Rules:** draft nahi; har week ka apna submit; submit ke baad status turant; approved
week locked (read-only) with "Request change" (Phase 7 ke baad effective).

**Tests:** week ranges (Feb 28, leap Feb, 31-day, Week 5), teaching days exclude Sunday
and holiday, submit sets Submitted + creates history v1, second submit without change `409`
concurrency (SQLite: expected_version), rejected reason visible, approved edit needs intent.

**Risks:** prose fields `CanonicalRequest` se inherit nahi karenge (warna lowercase ho
jayega); `submitted_at` UTC; month/year int validation.

### Phase 7 — Approval Flow

**Backend files**
- `backend/app/domains/academic/classroom/course/approvals.py` (**new**)
  - `review_queue(session, user, *, section_id=None, status="Submitted", skip, limit)` —
    sirf submitted weeks; `count_review_queue` (`X-Total-Count`).
  - `approve(session, plan_id, user, expected_version)` — transaction:
    `select(...).with_for_update()` (Postgres; SQLite par skip); status Submitted check;
    already Approved + same version → idempotent `200`; version mismatch → `409`;
    `status = Approved`, `approved_version = version`, reviewer fields, history verdict
    stamp; notify teacher.
  - `reject(session, plan_id, reason, user, expected_version)` — reason blank → `422`;
    status `Rejected`, reviewer fields, history verdict; teacher notify (reason body).
  - `approve_many(session, plan_ids, user, expected_versions)` — per-plan result;
    ek transaction + `skipped` list; same code path (second logic nahi).
  - `week_counts(session, cs_ids, year, month)` → submitted/approved/rejected counts
    (GROUP BY; Phase 4 table aur Phase 8 list same function).
- `backend/app/domains/academic/classroom/course/router.py`
  - `GET /course/reviews` (`course.approve`)
  - `GET /course/reviews/count` (`course.approve`) — badge
  - `POST /course/lesson-plans/{plan_id}/approve` (`course.approve`)
  - `POST /course/lesson-plans/{plan_id}/reject` (`course.approve`)
  - `POST /course/lesson-plans/approve-many` (`course.approve`)
- `backend/app/domains/academic/classroom/course/schemas.py` — `ReviewRow`,
  `RejectIn(reason, expected_version)`, `ApproveManyIn`, `BulkResult`.
- `backend/tests/test_course_approvals.py` (**new**).

**Frontend files**
- `frontend/src/components/features/classroom/course/LessonPlanReviewPanel.tsx` (**new**) —
  submitted weeks list (week click → full plan), select checkboxes, "Approve selected",
  reject with reason `Textarea` (`Dialog`).
- `frontend/src/components/features/classroom/course/WeeklyLessonPlanDialog.tsx` —
  approver ke liye Approve/Reject controls; teacher ke liye sirf status + reason.
- `frontend/src/components/features/classroom/course/CourseTable.tsx` — row count
  "3 submitted · 2 approved".
- `frontend/src/components/features/teachers/CourseTab.tsx` (Phase 8) — wahi review
  endpoint use karega.
- `frontend/src/services/course.service.ts` — `getReviewQueue`, `approveLessonPlan`,
  `rejectLessonPlan`, `approveManyLessonPlans`.
- `frontend/src/lib/course/lesson-plan.ts` — `canReject(reason)`, `countsLabel` + tests.

**Rules:** reject reason mandatory (server + UI); approve/reject idempotent; do reviewers
race → ek jeete, doosre ko `409` (ya already-approved 200 same state); approved week par
naya version D6 flow.

**Tests:** approve once → Approved + history verdict; approve again → 200 same; two
approvals with same expected_version → one `409`; reject blank reason `422`; bulk approve
returns per-plan results; teacher change (D10) ke baad pending weeks naye teacher ke liye
editable, approved locked.

**Risks:** SQLite `FOR UPDATE` nahi deta — race test expected_version par based hoga;
Postgres row lock Phase 10 dry-run mein.

### Phase 8 — Teachers > Course Tab

**Backend files**
- `backend/app/domains/academic/classroom/course/teacher_course.py` (**new**)
  - `teacher_list(session, user, q, skip, limit)` — single aggregate query: per teacher
    `(subjects_count, sections_count, pending_approvals, behind_subjects,
    completion_percent)`; `course.view_all` warna self only.
  - `teacher_detail(session, employee_id, user)` — current + past `classroom_subject`
    assignments (class/section/subject, effective range), month plan weeks + statuses,
    chapter progress (done/total, per chapter who/when), pending counts. Agar caller
    `view_all` nahi rakhta aur teacher doosra hai → `404`.
  - `my_course(session, user)` — caller ka employee row → same detail shape.
- `backend/app/domains/academic/classroom/course/router.py`
  - `GET /course/teachers` (`course.view_all`; teacher ke liye `course.read` par self)
  - `GET /course/teachers/{employee_id}` (`course.view_all` ya self)
  - `GET /course/my` (`course.read`)
- `backend/app/domains/academic/classroom/course/schemas.py` — `CourseTeacherRow`,
  `TeacherCourseDetail`, `TeacherSubjectRow`, `TeacherWeekRow`.
- `backend/tests/test_course_teacher_tab.py` (**new**).

**Frontend files**
- `frontend/src/components/features/teachers/CourseTab.tsx` (**new**) — teachers list
  (Table: Name | Subjects | Pending approvals | Behind | Completion), search + `Pagination`.
- `frontend/src/components/features/teachers/TeacherCourseDetail.tsx` (**new**) — teacher
  header, subjects/sections cards, month plan (`WeeklyLessonPlanDialog` read-only),
  chapter progress table, approve/reject (Phase 7 calls).
- `frontend/src/components/features/teachers/useTeacherCourse.ts` (**new**) — queries +
  mutations + invalidation.
- `frontend/src/components/features/teachers/TeachersPage.tsx` — tabs order:
  `["List"]`, phir `if (kind==="teacher" && canReadCourse) push("Course")`, phir Workload…
- `frontend/src/components/features/teachers/useStaff.ts` — `StaffTab` union mein
  `"Course"`.
- `frontend/src/components/features/teachers/MyStaffPanel.tsx` — "My Course" section
  (`/course/my`), same detail component; own plan submit.
- `frontend/src/services/course.service.ts` — `getCourseTeachers`, `getTeacherCourse`,
  `getMyCourse`.
- `frontend/src/types/index.ts` — teacher course types.

**Rules:** Classroom side aur Teachers side same endpoints/data (`section_course`,
`lesson-plans`, `approve/reject`) — do copies nahi. Teacher-only login par sirf apna
`/course/my`; doosre teacher ka id `404`/`403` (existence leak nahi).

**Tests:** teacher list counts match `pending_approvals`; behind flag D8; detail past
assignment dikhata hai (teacher change ke baad); teacher B calls teacher A detail → 403;
school B → 404; `my` returns self.

**Risks:** `TeachersPage` aaj teacher-only par `MyStaffPanel` dikhata hai — Course tab
wahan bhi accessible hona chahiye; `StaffTab` type add karte waqt `useStaff` ke queries
`Course` tab par na chalein (enabled flags).

### Phase 9 — Notifications, Reminders, Badges, Overview

**Backend files**
- `backend/app/domains/main/notifications/events.py`
  - Event constants: `course.week_submitted`, `course.week_approved`,
    `course.week_rejected`, `course.reminder`.
  - `_KIND_BY_EVENT` mein `"Course"` mapping.
  - `COURSE_APPROVERS = "course_approvers"` recipient set + resolver: us school ke wo
    `user_id` jinke roles `course.approve` hold karte hain (`rolepermission` join; ek
    query, per-notification query nahi).
  - `notify(... dedupe_key=...)` hi writer rahega — naya notification table/writer nahi.
- `backend/app/domains/academic/classroom/course/approvals.py` / `lesson_plans.py`
  - submit par approvers ko (entity `lesson_plan`, dedupe
    `course:plan:{id}:v{version}:submitted`)
  - approve/reject par teacher ke `user_id` ko (dedupe `...:approved` / `...:rejected`,
    reject body mein reason).
- `backend/app/domains/academic/classroom/course/reminders.py` (**new**)
  - `remind_unsubmitted(session)` — current month ki un weeks ke liye jinka `end_date <
    today` aur koi Submitted/Approved row nahi; current teacher ko ek notification
    (dedupe `course:reminder:{cs_id}:{year}-{month}-w{week}`); inactive/archived skip.
  - `register_job("course.reminders", remind_unsubmitted)` module import par; ise
    `course/__init__.py` (ya `router.py`) se import karo — existing `exam-reminder`
    (`exams/plan/__init__.py`) ka wahi pattern, `main.py` chhedne ki zarurat nahi.
- `backend/app/domains/academic/classroom/course/router.py`
  - `GET /course/summary` (`course.read`) — pending approvals + subject count +
    completion (badge ke liye; scoped).
  - `GET /course/sections/{section_id}/summary` (`course.read`) — Classroom card/header.
- `backend/app/domains/academic/classroom/repository.py` + `service.py` +
  `schemas.py` — `ClassSectionCard.pendingApprovals` (aur completion subject-average).
- `backend/tests/test_course_notifications.py` (**new**).

**Frontend files**
- `frontend/src/components/features/classroom/course/CoursePanel.tsx` — pending badge.
- `frontend/src/components/features/teachers/TeachersPage.tsx` — Course tab par badge
  (`/course/summary`).
- `frontend/src/components/features/classroom/ClassroomCards.tsx` — section row par
  `Course {pct}% · {n} pending` (null-safe, "No course plan" fallback).
- `frontend/src/components/features/classroom/SectionDetailPage.tsx` — header card.
- `frontend/src/services/course.service.ts` — `getCourseSummary`.
- `frontend/src/components/features/notifications/*` — koi change nahi; naye events bell
  mein apne aap aa jayenge (`kind = "Course"` badge tone add karna pad sakta hai).

**Rules:** reminder duplicate na bane (dedupe_key + unique index); notification fail ho to
submit/approve fail na ho (`notify` already swallow karta hai); scheduled job existing
`core/scheduler.py` (APScheduler nahi).

**Tests:** submit → approver ke paas 1 notification (dobara submit → naya version, naya
dedupe); approve/reject → teacher ke paas 1; reminder job dobara chalne par duplicate
nahi; school B ke approver ko School A ka notification nahi.

**Risks:** approver resolver role names par nahi, permission par based ho; `course/__init__.py`
se `reminders` import na ho to reminder job kabhi register nahi hoga.

### Phase 10 — Final Integration, Hardening aur Testing

**Files**
- `backend/tests/test_course_end_to_end.py` (**new**) — ek scenario: subject add (custom +
  master) → teacher assign → chapters add → tick → month plan submit (2 weeks) → approve
  one / reject one → resubmit rejected → approve → teacher change → new teacher continues
  → Classroom vs Teachers numbers match → notifications + isolation.
- `backend/tests/test_course_schema.py` extend — migration head/columns/drift.
- `frontend/src/lib/course/*.test.ts` — pure helpers ke saare cases.
- `backend/app/core/api_surface.py` — naye routes listing (agar route count test ho to
  update).
- Cleanup: `get_teacher_options` legacy alias, unused `syllabusprogress` mentions,
  docstrings, `phase.md` / `phase2.md` final.

**Checks**
- Query count: SQLAlchemy event se gino — section course table ≤ 6 queries, teacher list
  1 aggregate, month plan 2.
- Indexes: `EXPLAIN` (Postgres) — `classroomsubject(school_id, classroom_id, status)`,
  `lessonplan(school_id, status)`, `lessonplan(classroom_subject_id, year, month)`,
  `subjectteacher` open index.
- Migration: `alembic upgrade head` → `downgrade -1` → `upgrade head` (local DB only;
  pehle backup/approval).
- Permission matrix test (`test_permission_matrix.py` + new course test) green.
- Multi-school: har naye endpoint par doosre school ka id → 404.

**Exit notes:** Parent/Student read-only approved-weeks view future phase ke roop mein
`phase.md` Section 6 + `phase2.md` mein note; HOD department-scope bhi future decision.

---

## 6. Completion Log

### Phase 0: complete (19 Nov 2026)
- **Kya kiya:** Backend + frontend ka poora Course/Classroom/Teachers structure padha;
  prompt ke Section 2 ke notes code se verify kiye; D1–D10 par recommendation likhi;
  Phase 1–10 ka code-aware plan (files, tables, endpoints, components, tests, risks)
  likha.
- **Files badli/bani:** `backend/phase.md` (yeh plan), `backend/phase2.md` (verified
  facts + cross-phase reminders). Koi application code change nahi.
- **Kya test kiya (sirf relevant):** `node --test src/lib/course/view.test.ts` — 7/7 pass
  (frontend test runner confirm). Backend tests is machine par nahi chale: `uv` installed
  nahi aur `.venv\Scripts\python.exe` Application Control policy se blocked hai.
- **Baaki / known issues:**
  - `subjectteacher` ka write path (`assign_subject_teacher`) aaj history overwrite karta
    hai — Phase 1/4 mein fix.
  - `get_teacher_options` saare staff deta hai (active teachers filter nahi) — Phase 4.
  - Teacher ko doosre section ka Course data aaj dikh sakta hai (`classes.read` +
    `section_id` scope nahi) — Phase 2.
  - Completion % ka formula: card aaj chapter-weighted; D7 subject-average — Phase 4.
- **phase2.md mein kya add kiya:** verified schema facts (A1–A14), 16 cross-phase
  reminders (R1–R16), environment/test commands, aur "inhe todna nahi" list.

### Phase 1: complete (19 Nov 2026)
- **Kya kiya:**
  - `subject.is_active` (default true) — retired subject picker se hatta hai, rows/FKs
    rehte hain.
  - `classroomsubject` table: section + subject + session, `Active`/`Archived`, timestamps,
    unique per (section, subject, session).
  - `subjectteacher.classroom_subject_id` + do partial unique indexes (per
    `classroomsubject` aur legacy per section+subject) — ek hi open assignment.
  - `lessonplan` (latest version, status, `approved_version`, review fields) +
    `lessonplanhistory` (immutable submission snapshots; verdict `approved_at` /
    `rejected_at`).
  - Migration `e2b8c4f7a1d9_course_lesson_plans.py`: subject flag + lower(name) unique
    index (duplicates par abort), tables, backfill from `subjectteacher` + `chapter`,
    link + duplicate abort + partial indexes, full downgrade.
- **Files badli/bani:**
  - `app/domains/academic/classroom/academics/models.py` (subject/subjectteacher)
  - `app/domains/academic/classroom/course/models.py` (**new**)
  - `app/core/schema.py` (`MODEL_MODULES` mein `academic.classroom.course`)
  - `alembic/versions/e2b8c4f7a1d9_course_lesson_plans.py` (**new**, head)
  - `tests/test_course_schema.py` (**new**)
- **Kya test kiya (sirf relevant):**
  - `tests/test_course_schema.py` — 7/7 pass (Docker `eduverse-checks:latest`, Python
    3.14). Unique/check constraints, one open teacher row, plan/history keys, status
    vocabulary.
  - `tests/test_classroom_course.py` — 5/5 pass (purana Course behaviour intact).
  - `tests/test_phase1_schema.py` + `tests/test_phase2_schema.py` — 21/21 pass.
  - `ruff check` + `ruff format --check` — clean (5 files).
  - Migration head check: `e2b8c4f7a1d9` single head, chain
    `... → b7d2e4f1a9c3 → e2b8c4f7a1d9`.
- **Baaki / known issues:**
  - **Migration DB par apply nahi ki** — user approval ke baad (backup ke saath). Backfill
    duplicate names/open rows par abort karegi aur counts print karegi.
  - PostgreSQL-specific dry-run (`upgrade → downgrade -1 → upgrade`) Phase 10 mein.
  - `test_structure.py` poora file is environment mein pytest ke saath atak gaya (app
    import chain); registry rule alag se verify kiya — `MODEL_MODULES` mein 31 modules,
    naya module included, saare models import OK.
  - `lessonplan`/`classroomsubject` ka `updated_at` services ko khud refresh karna hoga
    (Phase 6/4).
- **phase2.md mein kya add kiya:** R17–R21 (Course source, open-row indexes, migration
  pending + abort rules, history verdict shape, Docker test/lint commands) aur Phase 1
  entry.

### Phase 2: complete (19 Nov 2026)
- **Kya kiya:**
  - 6 naye permission codenames (`course.read`, `course.plan`,
    `course.assign_teacher`, `course.manage`, `course.approve`, `course.view_all`).
  - Principal + vice-principal + school/system admin: saare chhe; teacher aur HOD: sirf
    read + plan.
  - Reusable server guards `course/scope.py` mein (school scoped; legacy assignment rows
    bhi handle).
  - `course/teaching_days.py`: open days + Week 1–5 ranges (D5 ka ek implementation).
- **Files badli/bani:**
  - `app/domains/auth/permissions.py`
  - `app/domains/academic/classroom/course/scope.py` (**new**)
  - `app/domains/academic/classroom/course/teaching_days.py` (**new**)
  - `tests/test_course_permissions.py` (**new**)
  - `tests/test_course_teaching_days.py` (**new**)
  - `tests/test_permission_matrix.py` (course-rights contract test)
- **Kya test kiya (sirf relevant):**
  - `tests/test_course_permissions.py` — 6/6 pass.
  - `tests/test_course_teaching_days.py` — 6/6 pass.
  - `tests/test_permission_matrix.py` — 12/12 pass.
  - `ruff check` + `ruff format --check` — clean.
- **Baaki / known issues:**
  - HOD ke paas purana `classes.assign_teacher` hai; legacy subject-teacher endpoint
    (`PUT /classroom/sections/{id}/subjects/{subject_id}/teacher`) abhi usi par chalta
    hai. Phase 4 mein us route ko `course.assign_teacher` par shift karna hai, warna HOD
    teacher change kar sakta hai (course rights se bahar).
  - Teacher ke liye subject-row filtering Phase 3/4 mein service mein lagegi
    (`visible_course_subject_ids` ready hai).
  - Migration `e2b8c4f7a1d9` abhi bhi DB par apply nahi ki (approval pending).
- **phase2.md mein kya add kiya:** R22 (legacy teacher endpoint ka guard),
  R23 (`session.get` identity-map pitfall) aur Phase 2 entry.

### Phase 3: complete (19 Nov 2026)
- **Kya kiya:**
  - School subject master: list (active / include inactive), create (name + optional code,
    code auto), rename, retire (`course.manage`).
  - Section Add Subject: master dropdown (server-side minus already added), Custom name
    (master list mein join), teacher optional.
  - `section_course` ka source `classroomsubject`; legacy teacher rows bhi included;
    teacher ko sirf apne subjects; `include_archived` switch.
  - Archive/Restore; delete sirf empty row par (lesson plan ya completed chapter → `409`
    + "archive instead").
  - Frontend Course table (Subject/Teacher/Lesson Plan/Total/Completed/lambi bar +
    actions), Add Subject dialog, Manage Subjects dialog, chapters popup, delete confirm.
- **Files badli/bani:**
  - `app/domains/academic/classroom/academics/{schemas,repository,service,router}.py`
  - `app/domains/academic/classroom/course/{schemas,service,router}.py`
  - `tests/test_course_subjects.py` (**new**)
  - Frontend: `course/CourseTable.tsx`, `course/AddSubjectDialog.tsx`,
    `course/SubjectMasterDialog.tsx` (**new**), `course/CoursePanel.tsx` (rewrite),
    `services/{course,academics}.service.ts`, `types/index.ts`, `lib/course/view.ts`
    (+ test).
- **Kya test kiya (sirf relevant):**
  - `tests/test_course_subjects.py` — **7/7 pass** (custom master once, rename/retire,
    teacher denied manage, dropdown hides added, archive/restore/delete rules, teacher
    sees own only, other school 404).
  - `tests/test_classroom_course.py` — **5/5 pass** (legacy Course tab still works).
  - `node --test src/lib/course/view.test.ts` — **8/8 pass**.
  - `node tsc --noEmit` (frontend) — clean; backend `ruff` — clean.
  - Routes verify: `/sections/{id}/available-subjects`, `/sections/{id}/subjects`,
    `/subjects/{id}/archive|restore`, `/subjects/{id}` (DELETE) registered.
- **Baaki / known issues:**
  - "Lesson Plan" column abhi "No plan"; weekly plan + button Phase 6.
  - Teacher assign/edit + `course.assign_teacher` route Phase 4 (legacy route abhi
    `classes.update`/`classes.assign_teacher` par).
  - Section detail ke Exams/Timetable dropdowns abhi `get_subject_rows()` (saare school
    subjects) use karte hain — Phase 3 mein unhe chheda nahi.
  - `CourseBar.tsx` ab CoursePanel se use nahi hota; Phase 6 mein review/cleanup.
  - Migration `e2b8c4f7a1d9` abhi bhi DB par apply nahi ki.
- **phase2.md mein kya add kiya:** R24 (`course.read` guard + `section_course` source),
  R25 (delete/archive + master UI) aur Phase 3 entry.

### Phase 4: complete (19 Nov 2026)
- **Kya kiya:**
  - Table envelope: `LessonPlanSummaryRead` (current month: submitted / approved /
    pending / rejected) per row; `completionPercent` (D7 subject average),
    `completionSubjects`, `subjectsCount`. Sab fixed number of queries (per-row N+1
    nahi).
  - `assign_teacher`: active teacher + teaching role check; same teacher = no-op;
    effective date default today; old open row closes at `effective_from - 1 day`;
    new open row; same-day correction replaces that day; audit row. Legacy route ab
    `course.assign_teacher` guard ke saath isi history ko likhta hai.
  - Workload warning (`staffworkloadrule` + `timetableperiod`), non-blocking.
  - `GET /course/subjects/{id}/teachers` timeline (oldest first, per-teacher completed).
  - `get_active_teacher_options`: teaching role + `left_on`/`deactivated_at` null +
    active login; old `get_teacher_options` delegate.
  - D7 completion: `completion.subject_average_by_section`; Classroom card
    `get_syllabus_percent` ab subject-average. Class-level chapter plan har section par
    lagta hai (9-B bina row ke 0%, "no data" nahi) — legacy card behaviour preserved.
  - Frontend: `TeacherAssignDialog`, `TeacherHistoryDialog`, `CourseCompletionCard`;
    CourseTable Lesson Plan cell + Assign/Edit + history link; `lessonPlanLabel`,
    `historyLabel`, `completionDetail` + tests.
- **Files badli/bani:** course `{schemas,service,router,completion}.py`;
  `classroom/{repository,router,service}.py`; new `tests/test_course_teachers.py`;
  frontend new dialogs/card + `CourseTable.tsx`, `CoursePanel.tsx`,
  `services/course.service.ts`, `types/index.ts`, `lib/course/view.ts` (+ test).
- **Kya test kiya:** `tests/test_course_teachers.py` 8/8; regression
  `test_course_subjects` + `test_classroom_course` + `test_course_permissions`
  = 26/26 pass. `node --test src/lib/course/view.test.ts` 11/11. `tsc --noEmit` clean.
  `ruff check` + `ruff format --check` changed files clean.
- **Baaki / known issues:**
  - `GET /classroom/teachers` ab active teaching staff deta hai (pehle saare staff);
    baaki screens (homework/timetable/exams) isi list ko use karte hain — behaviour
    improvement hai, par Phase 5 mein ek baar UI se verify karna.
  - Table ka Lesson Plan summary **current calendar month** ka hai; month switch Phase 6
    ke popup mein.
  - New assign API clear (`teacher_id = null`) nahi leta; clear sirf legacy route par
    (history close hoti hai).
  - `CourseCompletionCard` Course tab ke top par hai; SectionDetailPage ka header Stat
    bhi D7 number dikhata hai.
  - Migration `e2b8c4f7a1d9` abhi bhi DB par apply nahi ki.
- **phase2.md mein kya add kiya:** Phase 4 entry + D7/teacher-history notes.

### Phase 5: complete (19 Nov 2026)
- **Kya kiya:**
  - Chapter CRUD class-level: add (append ya explicit sequence, duplicate `409`),
    rename/re-date, move-to-position (poori list two-phase negative → positive renumber,
    unique constraint safe), delete.
  - Delete rules: koi section ne completed → `409` ("undo the tick"); koi
    `exam_paper_chapter` → `409`; warna section progress rows + chapter delete.
  - `GET /course/subjects/{cs}/chapters`: class ka plan + is section ka progress;
    teacher sirf apne current subject ke liye, warna `403`.
  - `ChapterRowRead.canEdit` (office only) ke saath `canTick` (current holder/office);
    tick ab `course.manage` ko bhi office maanta hai (legacy `classes.update` bana hua).
  - Frontend: chapter table mein Add Chapter, Edit, Delete (confirm), ↑/↓ reorder;
    `ChapterEditorDialog` (name + planned date); service `getChapters`/`createChapter`/
    `updateChapter`/`deleteChapter`; `reorderSequence` + `chapterTotals` pure helpers.
  - Har add/edit/move/delete/tick par `course` + `classroom` queries invalidate, so table
    total/completed/bar aur D7 card turant sync rehte hain.
- **Files badli/bani:** `course/{schemas,service,router}.py`; new
  `tests/test_course_chapters.py`; frontend new `ChapterEditorDialog.tsx`,
  `chapter-columns.tsx`, `CoursePanel.tsx`, `services/course.service.ts`,
  `types/index.ts`, `lib/course/view.ts` (+ test).
- **Kya test kiya:** chapters 7/7; regression (teachers, subjects, classroom course,
  Phase 10 chapter flow) = 30/30 pass. Frontend view 13/13; `tsc --noEmit` clean;
  `ruff check` + `ruff format --check` clean.
- **Baaki / known issues:**
  - `POST` with an explicit sequence greater than the list length leaves a gap (order is
    still correct; the next move renumbers). UI append karta hai, gap sirf API caller se.
  - Chapter ka `canEdit` sirf `course.manage` par hai; teacher apne subject ke chapters
    sirf tick kar sakta hai (plan ke mutabik admin edit).
  - Chapter delete progress rows bhi delete karta hai (In progress included); completed
    par block hai.
  - Migration `e2b8c4f7a1d9` abhi bhi DB par apply nahi ki.
- **phase2.md mein kya add kiya:** Phase 5 entry + R27 (class-level chapter + delete
  blocks + `canEdit`).

### Phase 6: complete (19 Nov 2026)
- **Kya kiya:**
  - `course/lesson_plans.py`: `month_plan` (Week 1-5 + real teaching days + latest row +
    approved snapshot + rejection reason + `canEdit`/`canRequestChange`) aur
    `submit_week` (working row + immutable history snapshot, ek transaction).
  - Submit rules: current holder ya office; `topics` + `learning_objectives` required,
    2000-char cap; `expectedVersion` stale → `409`; approved week `intent="change"` ke
    bina `409`; rejected resubmit reason clear; version +1; `approved_version` preserve;
    concurrent insert/update `IntegrityError` → `409` (500 nahi).
  - API: `GET /course/subjects/{cs}/lesson-plans?year=&month=`,
    `PUT /course/subjects/{cs}/lesson-plans/{year}/{month}/{week_no}`.
  - Frontend: `WeeklyLessonPlanDialog` (month/year select, Week tabs, range + teaching
    days, 6 `Textarea`, status/version/submitted-by, rejection reason, approved snapshot,
    Request change), `lib/course/lesson-plan.ts` (+ tests), service functions, CourseTable
    Lesson Plan cell ab popup kholta hai.
- **Files badli/bani:** `course/{schemas,router}.py`, naya `course/lesson_plans.py`;
  new `tests/test_course_lesson_plans.py`; frontend new `WeeklyLessonPlanDialog.tsx`,
  `lib/course/lesson-plan.ts` (+ test), `CourseTable.tsx`, `CoursePanel.tsx`,
  `services/course.service.ts`, `types/index.ts`.
- **Kya test kiya:** lesson plans 9/9; course regression (chapters/teachers/subjects/
  classroom) = 36/36 pass. Frontend view + lesson-plan 17/17; `tsc --noEmit` clean;
  `ruff check` + `ruff format --check` clean.
- **Baaki / known issues:**
  - Submit route `course.read` par hai; service `course.plan` + current holder check karta
    hai (reviewer read kar sakta hai, write nahi).
  - Approved snapshot sirf read ke liye; Phase 7 review verdict/history stamping baaki.
  - Notification hook comment `submit_week` ke andar hai (Phase 9).
  - Past/future month submit allowed agar week valid ho; koi date-window block nahi.
  - Migration `e2b8c4f7a1d9` abhi bhi DB par apply nahi ki.
- **phase2.md mein kya add kiya:** Phase 6 entry + R28 (submit/snapshot/version rules).

### Phase 7: complete (19 Nov 2026)
- **Kya kiya:**
  - `course/approvals.py`: reviewer queue (submitted only, oldest first, full six fields,
    section filter, `X-Total-Count`), count, week counts; approve/reject/approve-many.
  - approve: expected-version guard, history `approved_at/by` stamp,
    `approved_version=version`, reviewer fields; same version repeat → idempotent 200.
  - reject: reason mandatory (prose preserved, ≤1000), history `rejected_at/by/reason`,
    plan status Rejected; idempotent same version.
  - approve-many: one transaction, valid rows saved, stale/unknown rows returned in
    `skipped` (no 500).
  - Notifications: `course.week_approved` / `course.week_rejected` ("Course" kind),
    teacher (submitter) ko ek per version; reject body mein reason; dedupe key.
  - API: `GET /course/reviews`, `/course/reviews/count`,
    `POST /course/lesson-plans/{id}/approve|reject`, `/approve-many`.
  - Frontend: `LessonPlanReviewPanel` (queue, select/bulk approve, full-plan dialog,
    reject reason), Course tab toolbar "Review plans"; `WeeklyLessonPlanDialog` mein
    approver ke liye Approve/Reject; service functions; `canReject` + `countsLabel`.
- **Files badli/bani:** naya `course/approvals.py`, `course/{schemas,router}.py`;
  notifications `events.py`; new `tests/test_course_approvals.py`; frontend new
  `LessonPlanReviewPanel.tsx`, `WeeklyLessonPlanDialog.tsx`, `CoursePanel.tsx`,
  `services/course.service.ts`, `types/index.ts`, `lib/course/lesson-plan.ts` (+ test).
- **Kya test kiya:** approvals 6/6; regression (lesson plans, chapters, teachers,
  classroom, notifications) = 41/41 pass. Frontend 18/18; `tsc --noEmit` clean;
  `ruff check` + `ruff format --check` clean.
- **Baaki / known issues:**
  - Race safety `expected_version` + unique semantics par hai; Postgres `FOR UPDATE`
    Phase 10 dry-run mein add/verify karna hai.
  - Approver ko submission notification Phase 9 mein; abhi sirf approve/reject teacher
    ko jaata hai.
  - Reviewer current submitted week ko office rights se edit kar sakta hai (service
    allow karta hai); UI reviewer ko read-only dikhata hai.
  - Migration `e2b8c4f7a1d9` abhi bhi DB par apply nahi ki.
- **phase2.md mein kya add kiya:** Phase 7 entry + R29 (decision/version/history rules).

### Phase 8: complete (19 Nov 2026)
- **Kya kiya:**
  - `teacher_course.py`: `teacher_list` (subjects/sections, pending approvals, D8 behind
    subjects, D7 completion; batch queries), `teacher_detail` (current + past
    assignments, this month's week statuses, chapter rows, done/total), `my_course`
    (token → employee).
  - API: `GET /course/teachers`, `/course/teachers/{employee_id}`, `/course/my`
    (`course.read`; service `course.view_all`/self guard). Another teacher's detail `404`.
  - Frontend: Teachers area "Course" tab (`CourseTab`) with search + pagination +
    pending/behind/completion columns; `TeacherCourseDetail` cards/week badges/chapter
    table + plan popup; teacher-only My Staff panel gets "My course" from `/course/my`.
  - Plan popup reuse means an approver can approve/reject from the teacher detail with
    Phase 7's endpoints, not a second UI.
- **Files badli/bani:** new `course/teacher_course.py`, `course/{schemas,router}.py`;
  new `tests/test_course_teacher_tab.py`; frontend new `teachers/CourseTab.tsx`,
  `teachers/TeacherCourseDetail.tsx`, `TeachersPage.tsx`, `useStaff.ts`,
  `MyStaffPanel.tsx`, `services/course.service.ts`, `types/index.ts`.
- **Kya test kiya:** teacher tab 4/4; regression (teacher tab, approvals, lesson plans,
  teachers, chapters) = 34/34 pass. Frontend view + lesson-plan 18/18; `tsc --noEmit`
  clean; `ruff check` + `ruff format --check` clean.
- **Baaki / known issues:**
  - List endpoint pagination server-side (`skip`/`limit`); UI currently loads up to 200
    and pages client-side (search is server-side).
  - `behind_subjects` D8 approximation: a planned-past chapter with no/completed-elsewhere
    progress marks each section without a Completed row; no “behind” badge on Classroom
    list yet (Phase 9).
  - Teacher-only account sees "My course" inside My Staff, not a separate tab (same data
    and component).
  - Migration `e2b8c4f7a1d9` abhi bhi DB par apply nahi ki.
- **phase2.md mein kya add kiya:** Phase 8 entry + R30 (teacher self/view-all + detail 404).

### Phase 9: complete (19 Nov 2026) — 9.5 optional skipped
- **Kya kiya:**
  - Notifications: `COURSE_APPROVERS` + `course_approver_user_ids` (rolepermission
    `course.approve`); submit par approvers ko `course.week_submitted`, dedupe per
    plan version. Approve/reject notification Phase 7 se already teacher ko.
  - `course/reminders.py`: `course.reminders` scheduler job; current month ki finished
    weeks jinka plan Submitted/Approved nahi; current teacher ko dedupe per section-week.
    `course/__init__.py` par `register_job` (exam-reminder pattern).
  - Badges: `/course/summary` + `/course/sections/{id}/summary`; Teachers Course tab ke
    stat tiles + per-row pending badge; Classroom card `pendingApprovals`.
  - Classroom mini-row ab D7 completion % aur pending approvals dono dikhata hai.
- **Files badli/bani:** `main/notifications/events.py`; `course/reminders.py` (new);
  `course/{lesson_plans,teacher_course,router,schemas}.py`;
  `classroom/{schemas,repository,service}.py`; `tests/test_course_teacher_tab.py`
  (3 naye tests); frontend `classroom/ClassroomCards.tsx`, `teachers/CourseTab.tsx`,
  `services/course.service.ts`, `types/index.ts`.
- **Kya test kiya:** teacher tab + Phase 9 = 7/7; regression (teacher tab, approvals,
  lesson plans, notifications, classroom course, Phase 10 E2E) = **39/39** pass.
  Frontend view + lesson-plan 18/18; `tsc --noEmit` clean; `ruff check` +
  `ruff format --check` clean.
- **Baaki / known issues:**
  - 9.5 principal overview screen **nahi banaya** (optional; user confirmation pending).
  - No "behind" badge on Classroom list yet — teacher list shows it; Classroom card only
    completion + pending currently.
  - Reminder job current month only; past-month backfill nahi.
  - Migration `e2b8c4f7a1d9` abhi bhi DB par apply nahi ki.
- **phase2.md mein kya add kiya:** Phase 9 entry + R31 (notification/reminder scopes).

### Phase 10: complete (19 Nov 2026) — migration dry-run blocked
- **Kya kiya:**
  - Naya `tests/test_course_end_to_end.py`: master + custom subject → teacher assign →
    chapters + tick → 2 week submits → approve one / reject one → resubmit + approve →
    teacher change → new teacher ticks → Classroom vs Teachers vs summary numbers match →
    notifications counted → second school `404`.
  - Naya `tests/test_course_migration.py`: single head `e2b8c4f7a1d9`, parent
    `b7d2e4f1a9c3`, callable `upgrade`/`downgrade` (module loaded by path because
    `alembic/versions` is not a Python package).
  - Menu/pages cleanup: no feature code changed in this phase beyond tests; the legacy
    `get_teacher_options` alias stays because Homework/Timetable/Exams use it.
- **Kya test kiya:** full Course suite + permission matrix + classroom regression =
  **82/82** pass (one migration test path fixed after the first run); frontend 18/18;
  `tsc --noEmit` clean; `ruff` clean.
- **Migration state (verified live, 20 Nov 2026):**
  - `alembic current` / bootstrap = `e2b8c4f7a1d9 (head)`; `alembic upgrade head` was a
    no-op (already applied).
  - Tables `classroomsubject`, `lessonplan`, `lessonplanhistory` present; both
    `subject.is_active` and `subjectteacher.classroom_subject_id` present; all new unique
    indexes present (`uq_subjectteacher_open_cs/_legacy`, lesson-plan keys).
  - Pre-deployment backup: `backend/backups/course_db_backup_20261120.dump`
    (916,778 bytes, SHA-256 `DF7D6607...D59CE8`), ignored by git via `*.dump`.
  - Backend image rebuilt and restarted; healthy, 290 routes, Course routes present in
    live OpenAPI.
  - Offline `alembic --sql` remains unavailable because the migration inspects the live
    schema; `alembic check` reports broad pre-existing repo drift (school_id nullability,
    old exam/leave indexes), not a Course-specific mismatch.
- **Exit notes (future):**
  - Parent/Student read-only approved-weeks view — future phase (phase.md Section 6).
  - HOD department-scoped `course.view_all` — future product decision (D9 open).
  - Query-count target from the original plan (section table ≤ 6) not met; current
    implementation is bounded but >6 queries. Optimization backlog.
  - 9.5 principal overview still optional/skipped.
- **phase2.md mein kya add kiya:** Phase 10 entry + R32 (migration run needs live DB;
  E2E is the number contract).

> **Course feature complete (code + tests + live schema).** DB already head par hai,
> backup liya gaya, backend rebuild/restart ho chuka hai, aur Course routes live hain.


