# Global Academic Year — Implementation Plan

> **Status:** Phase 10 contract/migration hardening complete (20 Nov 2026); live migration, backup and browser smoke pending.
> **Source of truth:** `academic_year` table. Koi naya/duplicate year master nahi banega.
> **Language:** Yeh file Hinglish mein hai. Code, table/column/route names English mein.
> **Naming:** domain word sirf **academic year** hai. Code, API, UI aur plan mein
> koi synonym nahi chalega. SQLAlchemy ka DB handle framework ka technical object hai;
> domain field/route/component ka naam hamesha `academic_year` / `AcademicYear` hoga.

---

## 0. Kaam kaise chalega

### 0.1 Phase discipline

- Har phase shuru karne se pehle: us phase ke subphases dobara padho, `phase2.md` ke
  reminders padho, aur current code us phase ke hisaab se deeply dekho.
- Purani phases mein bana hua code todna nahi hai.
- Har phase ke baad `phase3.md` mein: checkbox `[x]`, completion log entry (kya kiya,
  files, tables/endpoints/components, tests, baaki, `phase2.md` mein kya add kiya).
- Ek phase khatam hone par summary do aur **ruko**. Agla phase sirf user ke
  “next phase” ke baad.
- Phase 0 mein sirf plan/schema review hota hai; product code change nahi.

### 0.2 Loop aur terminal rules

- Sirf synchronous, khud khatam hone wali commands. Dev server / watch mode foreground
  mein nahi. Server chahiye to short-lived command ya timeout.
- Ek hi error par maximum 2 fix attempts; phir ruk kar error + analysis user ko batao.
- Lambe output ko filter karo (`Select-Object -First/-Last`, `Select-String`).
- Destructive command (drop/delete/force reset) user ko bataye bina nahi.

### 0.3 Testing rules

- Sirf us phase se juda test: us phase ka endpoint/table/component/migration.
- Poora suite nahi. Phase 10 mein academic-year feature ka end-to-end test.
- Har schema change ke saath migration test: upgrade, downgrade, backfill, unique key.

### 0.4 Language aur naming

- `phase3.md` Hinglish; baaki code, comments, API, UI labels English.
- Ek hi domain word: **academic year**. Koi synonym use nahi hoga. UI par
  `Academic year 2026-27` ya `Academic year not set`.
- DB: `academic_year`, `academic_year_id`; API: `/settings/academic-years`;
  frontend: `AcademicYearSelect`, `AcademicYearProvider`, `academic-year.service.ts`;
  tests: `test_academic_year*`.
- Database handle ka technical variable existing framework convention follow karega;
  domain field/route/component mein “academic year” hi aayega.
- UI labels proper case. Dates school ke existing format mein.

### 0.5 Design aur codebase consistency

- Frontend: maujooda components/styles/spacing/tables/popups/tabs/badges/empty states
  reuse. Naya design system ya UI library nahi.
- Backend: existing router → service → repository pattern, auth dependency,
  `school_id` scoping, error format, pagination style (`X-Total-Count`), audit logging,
  alembic migrations.
- Existing `role` / `permission` / `rolepermission` / `user_role` reuse. Naya parallel
  permission system nahi.
- Naya code purane naam ko copy nahi karega; migration ke saath rename aur tests
  update honge (Phase 1/2).

### 0.6 Production aur scalability mindset

- Sab kuch per school aur per academic year. Koi hard-coded year (jaise `2026-27`) nahi.
- Har naye year-owned table mein `school_id` (DB NOT NULL), `academic_year_id`,
  sahi FKs, indexes, unique constraints.
- N+1 nahi. Lists paginated. Counts SQL aggregate se. Promotion bulk insert/chunk mein,
  per-student query loop nahi.
- Approve/Submit/Promote transaction mein + idempotent. Do users ek hi batch apply
  karein to race na bane (status/version check + row lock jahan DB de).
- Permission server par enforce; button chhupana kaafi nahi.
- School A ka data School B ko kabhi na dikhe.
- **History kabhi delete nahi:** academic year switch, promotion ya correction purane
  enrollment/marks/fees/attendance ko rewrite nahi karega.

---

## 1. Ek line mein goal

School ka **ek hi academic year** ho — `2026-27` jaisa — jo navbar par sabko dikhe,
office se open/switch ho, aur admission, course, attendance, exams, fees, timetable,
hiring, salary aur reports sab usi ek master se juden.

**Do rules kabhi nahi todne:**

1. “academic year” aur “academic year” **ek hi cheez** hai. Do master nahi banenge.
2. Har table mein `academic_year_id` nahi ghusega. Jahan zaroori hai wahan column;
   jahan date se academic year nikal aata hai wahan **derive** hoga.

“Global” ka matlab: logged-in school ke poore app ke liye ek current academic year.
Database multi-tenant hai, isliye har school ka apna `academic_year` hoga — ek
school ka academic year doosre school ko kabhi na dikhe.

---

## 2. Non-technical explanation (user-facing)

School ka academic year ek **diary ka saal** jaisa hai. Har subject, chapter, admission,
exam, fee aur attendance us diary ke kisi ek saal mein likha jata hai.

Aaj problem yeh hai:

- Almari (table) maujood hai,
- lekin school ne abhi koi saal **open/current** nahi kiya,
- isliye system ko pata nahi subject kis saal ki diary mein likhna hai,
- aur woh safety ke liye “Open the current academic year” bol kar rok deta hai.

Yeh error bug nahi, **safety lock** hai — taaki data galat saal mein na chala jaye.

Navbar par year isliye nahi dikh raha kyunki purana control zero-academic year par
khud ko hide kar deta hai. Usse “Academic year not set” dikhna chahiye tha.

---

## 3. Aaj ki sachchai — code audit (Phase 0)

### 3.1 Jo already sahi hai

- `academic_year` table maujood hai:
  - `name` (`2026-27`), `start_date` (1 April), `end_date` (31 March),
  - `is_current`, `school_id` (tenant).
- Rules:
  - `UNIQUE(school_id, name)` — same academic year do baar open nahi.
  - partial unique index `uq_academicyear_one_current` — ek school mein ek hi current.
- Routes (Phase 1 mein canonical academic-year paths):
  - `GET /settings/academic-years` (`settings.read`)
  - `POST /settings/academic-years` (`academic_year.manage`)
  - `PATCH /settings/academic-years/{id}/current` (`academic_year.manage`)
- Frontend year control top bar mein already imported hai (Phase 2 mein
  `AcademicYearSelect` rename):
  - AppLayout mein school name ke neeche, left aligned.
  - Native `Select` + current default + confirmation + “Open next year”.

### 3.2 Jo gap hai

- Aaj ke database mein school ke liye **koi `academic_year` row nahi** hai.
- `AcademicYearSelect` `years.length === 0` par `return null` karta hai — control gayab.
- `GET /settings/academic-years` `settings.read` maangta hai; har logged-in user ke paas
  woh right nahi ho sakta, isliye “sabko dikhe” guarantee nahi.
- Course `completion.current_academic_year()` sirf read karta hai; academic year na ho to
  `409` deta hai — sahi safety, lekin user ke paas open karne ka CTA nahi.
- Student placement pehli baar academic year **auto-create** karta hai; baaki screens
  (Course) explicit academic year maangte hain. Behaviour inconsistent hai.
- Kuch modules year-linked hain, kuch date-based, kuch bilkul linked nahi.

### 3.3 Tables jo already academic year se jude hain

| Table | Column | Notes |
|---|---|---|
| `enrollment` | `academic_year_id` | Student ka academic year placement; `place_student` likhta hai, lekin admission form par target academic year chunne ka option nahi. |
| `subjectteacher` | `academic_year_id` | Assignment academic year; legacy rows mein NULL ho sakta hai. |
| `chapter` | `academic_year_id` | Class + subject ka syllabus academic year. |
| `classroomsubject` | `academic_year_id` | Section ka subject academic year. |
| `lessonplan` | `academic_year_id` | Weekly plan academic year. |
| `lessonplanhistory` | via `lessonplan` | Child table; apna year column nahi chahiye. |
| `chapterprogress` | via `chapter` | Child table; apna year column nahi chahiye. |
| `exam` | `academic_year_id` (optional) | Backfill + new records current. |
| `holiday` | `academic_year_id` (optional) | Academic-year-specific holidays. |
| `leavebalance` | `academic_year_id` (optional) | Staff leave balance per year; legacy rows NULL ho sakte hain. |

### 3.4 Tables jinme column add karna hai

| Table | Column | Kyun |
|---|---|---|
| `timetableperiod` | `academic_year_id` | Timetable har academic year badal sakta hai; year ke bina purana timetable naye saal se clash karega. Unique keys bhi academic-year-aware honge. |
| `feestructure` | `academic_year_id` | Fee head/amount saal-vaar badalta hai; purane saal ka fee card naye saal par nahi dikhna chahiye. `feetransaction` structure se year inherit karega. |

### 3.4A Naye tables / columns — promotion-safe

| Table | Add | Kyun |
|---|---|---|
| `enrollment` | `previous_enrollment_id`, status vocabulary, roll unique, timestamps | Promotion chain aur idempotent apply (Section 4A.3). |
| `student` | `separation_academic_year_id` (optional FK) | Student leave/transfer ka year clear; legacy separation text column replace. |
| `classteacherassignment` | Naya table | Class teacher har academic year ka; purana year history (Section 4A.4). |
| `promotionbatch` | Naya table | Bulk promotion ka draft/apply audit (Section 4A.5). |
| `promotiondecision` | Naya table | Per student promote/repeat/transfer/leave/graduate decision (Section 4A.5). |

### 3.5 Tables jinme column **nahi** add karna

| Table / area | Kyun nahi |
|---|---|
| `student` | Student school mein kai saal rehta hai; uska placement year `enrollment` se aata hai. `separation_academic_year_id` sirf leave event ka year hai, placement stamp nahi. |
| `employee` | Employment multi-year hoti hai; joining date se academic year derive hota hai. |
| `classroom` | “Class 10-A” master row multi-year rehti hai; student ka year-wise placement `enrollment`, class teacher ka year-wise record `classteacherassignment`. |
| student `attendancerecord` | `date` se academic year pata hai. Duplicate year column drift karega. |
| `staffattendancerecord` | `date` se academic year. |
| `salarypayment` | `month` / `paid_on` se academic year. |
| `feetransaction` | `feestructure` se academic year; receipt par duplicate nahi. |
| `notification` | Entity (plan/exam) se academic year; bell ko filter chahiye to entity join. |
| `staffauditlog`, `marks_audit` | Timestamp se history; year column duplicate. |
| admission form/student | Admission `student` row likhta hai; academic year ka asli ghar `enrollment` hai. |
| meetings, tickets, library, transport | Inka apna event date/period hai; academic year unka primary lens nahi. |
| child tables (`marks`, `exam_paper_chapter`, `chapterprogress`, `lessonplanhistory`) | Parent se year aata hai; duplicate nahi. |

### 3.6 Date se academic year derive karne wale modules

- Student attendance — `date`
- Staff attendance — `date`
- Salary — `month` / `paid_on`
- Hiring / joining — `employee.joining_date`
- Admission date — `student.admission_date` (agar field hai)
- Fee receipts — parent fee structure
- Payroll/report ranges — date range

Yahan **column nahi**, ek shared helper se academic year nikalega:
`academic_year_for_date(academic year, day)` → `AcademicYear` (1 Apr–31 Mar).

---

## 4. Design decisions (D1–D15)

| # | Decision | Reason |
|---|---|---|
| D1 | “academic year” = `academic_year`; naya table nahi. | Ek hi sach; duplicate master avoid. |
| D2 | Ek school mein ek `is_current`; DB partial unique index hi final guard. | Do current row = screens ka split brain. |
| D3 | First academic year open hone par current; baad ka academic year open karne par current **nahi** badlega. | Agle saal ki planning pehle ho sakti hai; running year nahi badalna chahiye. |
| D4 | Navbar academic year **sab logged-in users** ko dikhe; open/switch sirf principal se senior roles (`system_admin`/`school_admin`; future `director`/`admin` agar seeded) karein. Principal/vice read-only. | Year context hai; change karna school ke sabse senior office ka decision hai. |
| D5 | Current academic year read auth-only endpoint se; school ke liye pehli read par **default current year ensure** hoga. Poori list `settings.read` par rahe. | Har role ko year dikhe; school ko zero-year dead end nahi milna chahiye. |
| D6 | Server hi naye record par current academic year default kare; browser se aaya year blindly trust na kare. | API/curl se galat year na bhar sake. |
| D7 | Sirf year-owned tables mein column; date-owned modules mein derive. | Har table mein column duplicate + drift paida karta hai. |
| D8 | academic year window fixed 1 April–31 March; naam se dates derive. | “June to April” jaisa custom window reports ko todta hai. |
| D9 | School ka current academic year **default** hai: first current-read par aaj ka year ensure/create hoga. Curriculum writes tab bhi `409` safety deti hain (platform/no-school edge). | User expectation: navbar hamesha current year dikhaye, setup gap na ho. |
| D10 | Academic year switch historical data ko delete/rewrite nahi karta; sirf lens/filter badalta hai. | Purana record safe. |
| D11 | Academic year switch ke baad har year-owned list/report current year default dikhaye; purana data sirf “All academic years”/explicit old-year filter se. Default mein do saal mix na hon. | Daily kaam current par, history accessible; old data safe. |
| D12 | Admission ka target academic year `enrollment` mein likha jayega, `student` par column nahi. | Student multi-year; placement per year. |
| D13 | Timetable aur fee structure year-scoped honge; unique keys bhi year include karenge. | Multi-year history bina clash. |
| D14 | Migration separate phase mein; pehle backup, phir backfill, phir constraints. | Live DB safe. |
| D15 | Student ka year-wise sach `enrollment`; class teacher year-wise `classteacherassignment`; bulk promotion `promotionbatch` + `promotiondecision`. | Promotion/repeat/leave history bina student row par year stamp kiye. |

---

## 4A. Academic year data model aur promotion-safe schema

Yeh section **promotion ke liye** hai. Rule simple hai: student ki pehchaan
`student` row hai; uska har saal ka class-section `enrollment` hai. Class teacher,
subject, teacher, chapter, exam, timetable aur fee **naye academic year mein naye
rows** hain — purane rows history ke liye wahin rehte hain.

### 4A.1 Table ownership map

| Table / area | Academic year link | Promotion ke waqt behaviour |
|---|---|---|
| `classname`, `section` | Nahi (platform master) | Reuse; class “Class 9” har saal wahi rehti hai. |
| `subject` | Nahi (school master) | Reuse; naye year mein `classroomsubject` naya row. |
| `student` | Nahi (sirf separation event field) | Identity same; naya year `enrollment` se. |
| `employee`, `guardian` | Nahi | Reuse; employment/guardianship multi-year. |
| `classroom` | Nahi (class-section master) | “Class 10-A” row stable; student ka year-wise placement `enrollment` mein. |
| `enrollment` | Haan | **Naya row** per promoted/repeated student; purana row preserved. |
| `classteacherassignment` (new) | Haan | **Naya row** per classroom per year; purana class teacher history. |
| `classroomsubject` | Haan | Naye year ke subjects naye rows; clone optional. |
| `subjectteacher` | Haan | Naye year ke teachers naye rows; purane assignment closed. |
| `chapter` | Haan | Naya syllabus naye year; optional copy, not automatic. |
| `lessonplan` | Haan | Naye plans; purane read-only. |
| `lessonplanhistory` | Via `lessonplan` | Immutable snapshot; apna year column nahi. |
| `exam` | Haan | Naye exams; purane result preserve. |
| `exam_paper` | Via `exam` | Naye papers; apna year column nahi. |
| `marks` | Via `exam` | Naya year ka exam naya; purane marks purane exam se. |
| `timetableperiod` | Haan | Naya timetable naye year; purana read-only. |
| `feestructure` | Haan | Naye fee heads/amount; purane fee card preserve. |
| `feetransaction` | Via `feestructure` | Receipt purane structure se; naya year naya structure. |
| `holiday` | Haan (optional) | Naye holidays; purane calendar preserve. |
| `leavebalance` | Haan (optional) | Naya year balance; carry-forward policy alag. |
| `attendancerecord` | Date se derive | Purani attendance preserve; filter date/year se. |
| `staffattendancerecord` | Date se derive | Same. |
| `salarypayment` | Month/date se derive | Payslip preserve; filter year se. |
| `homework`, `classdiary` | Date/classroom se derive | Purana diary preserve; new year new entries. |
| `notification`, audit logs | Nahi | Entity/timestamp se; year column nahi. |
| `promotionbatch`, `promotiondecision` (new) | From/to year | Bulk promotion ka audit aur idempotent apply. |

### 4A.2 Placement invariant

Ek hi sach, do jagah nahi:

1. `enrollment` = student ka **us academic year ka** class-section, roll aur status.
2. `student.classroom_id` = **aaj** ka placement, sirf current academic year ke
   enrollment ka mirror. Historical placement `student` par nahi.
3. Jo student current academic year mein active hai, uske liye ek enrollment hona
   chahiye; `student.classroom_id` aur current enrollment ka `classroom_id` equal hone
   chahiye. Future-year admission wale student ka aaj placement purana/null rahe.
4. Academic year switch hote hi current placement ko new year ke enrollment se
   reconcile karo; purane year ke enrollment ko chhedo nahi.

### 4A.3 `enrollment` — promotion ka centre

Existing table shape ko preserve karke yeh columns/constraints add honge:

```text
enrollment
  id                    uuid pk
  school_id             uuid not null -> school
  student_id            uuid not null -> student
  classroom_id          uuid not null -> classroom
  academic_year_id      uuid not null -> academic_year
  roll_no               text null
  status                text not null default 'active'
  joined_on             date null
  left_on               date null
  previous_enrollment_id uuid null -> enrollment.id
  created_at / updated_at

  UNIQUE (school_id, student_id, academic_year_id)
  UNIQUE (school_id, classroom_id, academic_year_id, roll_no)
         WHERE roll_no IS NOT NULL
  INDEX  (school_id, academic_year_id, classroom_id)
  INDEX  (school_id, student_id, academic_year_id)
  CHECK  (status IN ('active','promoted','repeated','transferred','left','graduated'))
  CHECK  (previous_enrollment_id IS NULL OR previous_enrollment_id <> id)
```

`status` vocabulary (text, existing style):

| Status | Meaning |
|---|---|
| `active` | Is academic year mein roll par hai. |
| `promoted` | Next academic year mein promotion ho gayi; purana row closed. |
| `repeated` | Same class dobara; next year ka naya enrollment. |
| `transferred` | Doosre school gaya; `left_on` set. |
| `left` | School chhod diya; `left_on` set. |
| `graduated` | Final class pass; next enrollment nahi. |

Rules:

- `student.classroom_id` sirf current academic year ka mirror hai; historical class
  `enrollment` se aata hai.
- `previous_enrollment_id` chain se “Class 9-A 2025-26 → Class 10-B 2026-27” dikhta hai.
- Same student/year par second enrollment DB `UNIQUE` se rukega; promotion retry
  idempotent hoga.
- Roll number same classroom/year mein duplicate nahi; doosre year same roll allowed.

### 4A.4 `classteacherassignment` — class teacher ka year-wise record

Aaj `classroom.class_teacher_id` sirf **aaj** ka teacher batata hai; new academic year
mein woh badal jayega aur history kho jayegi. Legacy assignment table pehle drop ho
chuki hai; naya schema year-wise history ke liye recreate hoga:

```text
classteacherassignment
  id                    uuid pk
  school_id             uuid not null -> school
  classroom_id          uuid not null -> classroom
  academic_year_id      uuid not null -> academic_year
  teacher_id            uuid not null -> employee
  effective_from        date not null
  effective_to          date null
  assigned_by_user_id   uuid null -> app_user
  note                  text null
  created_at            datetime not null

  UNIQUE (school_id, classroom_id, academic_year_id, effective_from)
  PARTIAL UNIQUE (school_id, classroom_id, academic_year_id)
          WHERE effective_to IS NULL
  INDEX (school_id, academic_year_id, classroom_id)
  INDEX (school_id, teacher_id, academic_year_id)
  CHECK (effective_to IS NULL OR effective_to >= effective_from)
```

- Ek classroom + academic year ka **ek open** class teacher; mid-year change purani
  row ko `effective_to` se close karke nayi row banayega.
- Promotion ke waqt naye year ke liye naya open assignment; purana row safe.
- `classroom.class_teacher_id` transition period mein current pointer rahega; reads
  `classteacherassignment` par shift honge. Duplicate truth na bane, isliye ek
  invariant test: current assignment ka teacher = `classroom.class_teacher_id`.
  Saare reads shift hone ke baad column drop hoga (Phase 5).

### 4A.5 `promotionbatch` aur `promotiondecision` — bulk promotion audit

```text
promotionbatch
  id                    uuid pk
  school_id             uuid not null -> school
  from_academic_year_id uuid not null -> academic_year
  to_academic_year_id   uuid not null -> academic_year
  status                text not null default 'draft'  -- draft/applied/cancelled
  note                  text null
  created_by_user_id    uuid null
  created_at            datetime not null
  applied_by_user_id    uuid null
  applied_at            datetime null

  PARTIAL UNIQUE (school_id, from_academic_year_id, to_academic_year_id)
          WHERE status <> 'cancelled'
  INDEX  (school_id, from_academic_year_id, status)
  INDEX  (school_id, to_academic_year_id, status)
  CHECK  (from_academic_year_id <> to_academic_year_id)
  CHECK  (status IN ('draft','applied','cancelled'))

promotiondecision
  id                    uuid pk
  school_id             uuid not null -> school
  batch_id              uuid not null -> promotionbatch
  student_id            uuid not null -> student
  from_enrollment_id    uuid not null -> enrollment
  decision              text not null
  to_classroom_id       uuid null -> classroom
  to_enrollment_id      uuid null -> enrollment
  roll_no               text null
  reason                text null
  decided_by_user_id    uuid null
  decided_at            datetime null
  applied_at            datetime null

  UNIQUE (batch_id, student_id)
  UNIQUE (to_enrollment_id) WHERE to_enrollment_id IS NOT NULL
  INDEX  (school_id, batch_id, decision)
  INDEX  (school_id, student_id, decision)
  CHECK  (decision IN ('promote','repeat','transfer','leave','graduate'))
  CHECK  (decision NOT IN ('promote','repeat') OR to_classroom_id IS NOT NULL)
  CHECK  (decision IN ('promote','repeat') OR to_classroom_id IS NULL)
  CHECK  (decision IN ('promote','repeat') OR to_enrollment_id IS NULL)
```

`decision` values:

- `promote` — next class; `to_classroom_id` required.
- `repeat` — same class; `to_classroom_id` required.
- `transfer` — doosre school; no next enrollment.
- `leave` — school chhoda; no next enrollment.
- `graduate` — final class; no next enrollment.

Rules:

- Batch pehle `draft` banta hai; office decisions review karta hai; phir `apply`.
- Batch mein sirf `from_academic_year_id` ke active enrollments preload honge; left/
  transferred/graduated student skip.
- `from_enrollment_id` us batch ke `from_academic_year_id` ka hona chahiye.
- Agar student ka `to` year mein enrollment pehle se hai to apply `409`/skip; duplicate
  placement nahi.
- `to_classroom_id` promote/repeat ke liye required; leave/transfer/graduate ke liye null.
- Apply ek transaction (ya per-class chunk) mein: naye `enrollment` banao, purane
  status close karo, `previous_enrollment_id` link karo, `to_enrollment_id` stamp karo,
  batch `applied` karo. Duplicate decision/enrollment `UNIQUE` se rukega.
- Applied batch ko delete nahi karte. Galti par applied batch ki correction future
  phase hai; draft batch ke decisions apply se pehle badal sakte hain. History preserve.
- `students.promote` permission server par enforce; UI button hide karna kaafi nahi.

### 4A.6 Promotion flow — step by step

1. **Next academic year open** karo (current banane ki zaroorat nahi; planning allowed).
2. **Draft batch** `from = current`, `to = next` banao. System active enrollments
   preload kare; proposed next class/section dikhaye, par auto-apply na kare.
3. Office har student ke liye decision set kare: promote/repeat/transfer/leave/graduate;
   target classroom aur roll number.
4. **Review:** counts, missing target classroom, already-enrolled students, left/transfer
   students, duplicate roll.
5. **Apply:** transaction/chunk mein placement service se naye `enrollment` banao;
   purane `status` close; `previous_enrollment_id` link; `to_enrollment_id` stamp;
   batch `applied`.
6. **Current placement:** agar `to` academic year current hai to placement service se
   `student.classroom_id` update karo; warna switch tak mat chhedo.
7. **Switch:** academic year current karte hi `reconcile_current_placements` chalao —
   new current year wale enrollment se `student.classroom_id` set karo; class teacher
   pointer bhi new year assignment se. Jis student ka enrollment nahi, use “not
   enrolled” flag/list mein dikhao; auto-promote na karo.
8. **New year setup:** class teacher assignment, subjects, subject teachers, chapters,
   timetable, fee structure, holidays — naye rows. Curriculum/fee copy optional CTA,
   automatic nahi.
9. **Old year:** read-only history; marks, attendance, fees, lesson plans, promotions
   wahin preserved.

### 4A.7 Kya naya banega, kya copy nahi hoga

| Cheez | New academic year |
|---|---|
| Student identity, guardian, employee | Same row reuse. |
| `enrollment` | Naya row (promote/repeat/admission); purana preserved. |
| Class teacher | Naya `classteacherassignment`; purana closed. |
| Subjects in section | Naya `classroomsubject`; optional clone. |
| Subject teacher | Naya `subjectteacher`; purana closed. |
| Chapters/syllabus | Naya `chapter`; optional copy. |
| Lesson plans | Naya plan/history; purane immutable. |
| Exams/papers/marks | Naya exam; purane marks purane exam ke saath. |
| Timetable | Naya `timetableperiod`; optional copy. |
| Fee structure | Naya `feestructure`; receipts parent se. |
| Holidays/leave balance | Naya; policy se. |
| Attendance/salary | Date/month se derive; naya column nahi. |
| Admission | Naya student + enrollment (target year). |
| Leave/transfer/graduate | Enrollment close; no fake next row. |

**Kabhi auto-copy nahi:** marks, attendance, fee transactions, lesson plan history,
promotion decisions, audit logs. Inka purana year immutable hai.

**Student leave vs staff leave:** student chhoda/transfer hua to us year ka
`enrollment` `left`/`transferred` close hoga, `separation_academic_year_id` set hoga,
next enrollment nahi banega. Staff leave `leaverequest` date se hai; `leavebalance`
academic year-wise hai; employee row multi-year same rehti hai. Employee exit par
salary/leave history dates se safe rehti hai — employee par placement-year column nahi.

### 4A.8 Invariants jo test se lock honge

- Ek school mein ek current academic year; DB partial unique index.
- Ek student ka ek academic year mein ek enrollment.
- Current year enrollment ka classroom = `student.classroom_id`.
- Ek classroom + academic year ka ek open class teacher.
- Har marks ka exam usi academic year ka; exam optional year backfill ke baad required.
- Har fee transaction ka structure usi academic year ka.
- Promotion apply idempotent: dobara call par duplicate enrollment/decision nahi.
- Applied batch delete/reverse nahi; correction history se.
- School A ke enrollment/promotion/marks School B ko kabhi na dikhein.

---

## 5. Academic year rules — ek hi jagah implement honge

### 5.1 Backend helper

Naya module: `backend/app/domains/admin/settings/academic_year_context.py`

```python
current_academic_year(session) -> AcademicYear | None
current_academic_year_id(session) -> UUID | None
require_current_academic_year(session, action: str) -> AcademicYear   # 409 with friendly message
academic_year_for_date(session, day: date) -> AcademicYear | None
academic_year_bounds(year: AcademicYear) -> tuple[date, date]
ensure_current_academic_year(session) -> AcademicYear                 # onboarding only
```

Rules:

- Sab queries tenant-scoped (`school_id`) — `tenant_of(session)`.
- `require_current_academic_year` ka `409` detail fixed aur friendly:
  `"No academic year is open. Open the current academic year from the navbar first."`
- `academic_year_for_date` pehle `start_date <= day <= end_date` se dhoondhe; na mile to
  `None`. Naam se guess nahi.
- `ensure_current_academic_year` order: current row → aaj ki date cover karne wali row ko
  current banao → warna nayi row create. Race-safe: `IntegrityError` par dobara read.
  Sirf onboarding/placement bootstrap ise call karega; Course nahi.
- `current_academic_year` helper **read-only** hai; sirf dedicated current-year
  endpoint `ensure_current_academic_year` se default row create karta hai.
- `placement.current_academic_year` isi helper par delegate hoga; public behaviour
  (return `AcademicYear`, first use par create) same rahega.

### 5.2 Permission model

| Cheez | Permission |
|---|---|
| Current academic year padhna | Koi bhi logged-in user (auth only) |
| Saare academic years ki list | `settings.read` |
| Naya academic year open | `academic_year.manage` **+** role gate: `system_admin`/`school_admin` (principal se senior; future `director`/`admin`) |
| Academic year switch | Same: `academic_year.manage` **+** senior role gate |
| Settings page ka academic year card | `settings.read`; manage button sirf senior role ko |
| Principal / vice-principal | Current year padh sakte hain, switch/open nahi |

### 5.3 Naya endpoint

`GET /settings/academic-years/current` — auth-only, `200` always:

```json
{
  "academicYear": {
    "id": "…",
    "name": "2026-27",
    "startDate": "2026-04-01",
    "endDate": "2027-03-31",
    "isCurrent": true
  }
}
```

School-bound user ke liye endpoint current year **ensure** karta hai (read-only
model helper `current_academic_year` alag hai; endpoint `ensure_current_academic_year`
call karta hai). Isliye `academicYear` normally always current row hoga; `null` sirf
platform/no-school account ya true bootstrap failure par. `404` nahi, kyunki setup
state valid UI state hai.

Frontend service: `getCurrentAcademicYear()` in `academic-year.service.ts`.
Query key: `["academic-year", "current"]`.

### 5.4 “Open” vs “Switch”

- **Open** = row banao. First row current; baad ki rows `is_current = false`.
- **Switch** = `PATCH .../{id}/current`, old flag same transaction mein clear.
- Navbar no-academic-year state mein `Open 2026-27` dikhaye — create hone par wahi current
  ban jayegi, isliye alag switch call ki zaroorat nahi.
- Existing academic year ho to “Open next academic year” alag; open karne ke baad current
  automatically switch **nahi** hoga (D3).

### 5.5 Frontend global context

- Naya `AcademicYearProvider` (`frontend/src/providers/academic-year-context.tsx`):
  - `current`, `isLoading`, `refresh`, `canManage`.
  - `useCurrentAcademicYear()` hook.
  - Dashboard layout ke andar wrap.
- `AcademicYearSelect` provider se current read kare; list sirf menu khulne par
  `getAcademicYears()` se.
- Switch/open ke baad `queryClient.invalidateQueries()` — existing behaviour,
  isliye Course, attendance, fees sab naye academic year par refresh ho jayenge.
- Year-owned lists ka **server-side default current year** hoga; frontend sirf
  `academic_year_id` tab bhejega jab user “All academic years” ya historic year chune.
  Switch ke baad purane year ke rows default list mein mix nahi honge.

---

## 6. Navbar UX — final behaviour

**Placement:** school name ke **theek neeche**, **left aligned** compact academic-year
picker hoga. Trigger small box hai jo topbar surface se match karta hai (white box
nahi). Dropdown mein current + saare past opened years, har row par
`01 Apr 2026 – 31 Mar 2027` dates. Year change par confirmation modal.
`+ Open next-year` button dropdown mein **hamesha visible** rahega; agar next year
already open ho to disabled-looking hai, click par message: only one year can be
added after the current year. Backend bhi koi beech ka year open nahi karta.

| State | Dikhega | Click |
|---|---|---|
| Academic year current hai | Normal select, `2026-27` selected | Change par confirmation; manager ko next-year CTA |
| Academic year hai, current none | Amber select | Manager list se current choose kare; non-manager read-only |
| Koi academic year hi nahi | Amber `Academic year not set` | Manager ko “Open current year” CTA; non-manager read-only |
| Mobile | Select full width, ek line | Same confirmation modal |
| Default school session | Current year `2026-27` (aaj ki date se) | Pehli read par ensure/create |

Additional rules:

- Select par `title`: `Academic year 2026-27`.
- Non-manager ko switch disabled; open/next CTA dikhega hi nahi.
- Error 409 “already open” ho to list refresh karke current selected rahe.
- Sirf `current + 1` year open ho sakta hai; past years dropdown mein read/switch ke
  liye rehte hain.
- Change par confirmation modal; cancel karne par current hi selected rahe.

---

## 7. Phase-wise implementation plan

Har phase ke aakhir mein: tests + `ruff` + `tsc` + docs update. Phase tamam hone
tak agla phase shuru nahi hoga. Sequence: Phase 0 → 1 → 2 → 3 → 4 → 4B → 5 → 6 →
7 → 8 → 9 → 10.

### Phase 0 — Plan file (COMPLETE)

> **Important - Next-phase gate:** Jab user is phase ke liye “next” bole, pehle is phase ka deep plan banao (current code, files, schema, tests, risks), phir implement karo. Bina deep plan code na likho.

- [x] `backend/phase3.md` bana.
- [x] Phase 0.1–0.6 discipline, naming aur testing rules likhe.
- [x] Current code audit likha.
- [x] Table add/derive/no-add map likha.
- [x] Decisions D1–D15 likhe.
- [x] Section 4A: academic year data ownership, enrollment/class teacher/promotion
      batch schema aur promotion flow likha.
- [x] Phase 1–10 + Phase 4B ka scope aur acceptance criteria likha.
- [x] Koi product code change nahi — sirf plan.

**Completion log:** 20 Nov 2026 — plan + promotion schema updated; implementation pending.

### Phase 1 — Backend academic year foundation + global read endpoint

> **Important - Next-phase gate:** Jab user is phase ke liye “next” bole, pehle is phase ka deep plan banao (current code, files, schema, tests, risks), phir implement karo. Bina deep plan code na likho.

**Goal:** Ek hi jagah academic year padhne/derive karne ka contract; sab logged-in users
current academic year read kar sakein; school-bound current read default year ensure
kare, baaki reads row create na karein.

**Files (expected):**

- `backend/app/domains/admin/settings/academic_year_context.py` (new)
- `backend/app/domains/admin/settings/academic_years.py`
- `backend/app/domains/admin/settings/router.py` (agar wiring chahiye)
- `backend/tests/test_academic_year.py` (extend)
- `backend/tests/test_academic_year_context.py` (new, agar alag behtar ho)

**Tasks:**

- [x] `academic_year_context.py` mein helper likho (Section 5.1).
- [x] Existing year test file ko `test_academic_year.py` par rename karo; purane
      imports/paths update karo.
- [x] `GET /settings/academic-years/current` add karo — `Depends(get_current_active_user)`,
      koi permission nahi; school ke liye current year ensure/create, response
      `{"academicYear": row | null}`.
- [x] Existing read model, open function aur route path ko `AcademicYearRead` /
      `open_academic_year` / `/academic-years` rename karo; frontend service path bhi
      isi phase mein update karo (UI rename Phase 2).
- [x] `academic_years.py` ka module docstring update karo: list `settings.read`,
      current auth-only, manage `academic_year.manage` + senior role gate.
- [x] Principal/vice ke permission lists se `academic_year.manage` hatao; sirf
      `system_admin`/`school_admin` (aur future director/admin) paas rakho.
- [x] Open/switch routes par `RequireSeniorAcademicYearManager` dependency lagao:
      permission + role codenames; principal/vice/custom role ko `403`.
- [x] Permission matrix tests update: principal/vice read-only; senior roles manage.
- [x] `test_academic_year.py` ke route-guard test mein naya current route add karo.
- [x] `AcademicYearRead` ko reuse karo; response camelCase frontend mapper se aayega.
- [x] `academic_year_for_date` ke liye date-boundary tests: 31 Mar, 1 Apr, leap day.
- [x] Tenant test: School A ka current School B ko na dikhe.
- [x] Test: first current endpoint call default year banata hai; second call duplicate
      nahi banata (idempotent current read).
- [x] Test: do current rows DB level par possible nahi (existing partial index).
- [x] `open_academic_year` ka no-current edge harden karo: pehli row current; agar
      rows hain par current none hai to aaj ki date cover karne wali row current ho,
      naya “next” row apne aap current na bane.
- [x] Course ka local `current_academic_year()` helper
      `academic_year_context.current_academic_year` par shift karo — read-only,
      missing academic year par `None`; likhne wale paths par wahi `409` guard rahega.
- [x] `placement.current_academic_year` ko `ensure_current_academic_year` par delegate
      karo; duplicate academic year-creation logic na rahe.
- [x] `phase2.md`/`README.md` mein endpoint ka zikr sirf tab karo jab code merge ho.

**Acceptance:**

- `GET /settings/academic-years/current` bina kisi permission ke har logged-in role
  ke liye `200` deta hai; anonymous `401`.
- School-bound current read par academic year **default current** ban jaye; platform/
  no-school par `academicYear: null`; `404` nahi.
- Academic-year tests pass; default-create, boundary aur role tests pass.

**Phase 1 completion — 20 Nov 2026:**

- Naya `academic_year_context.py`: current read, date lookup, `409` guard, onboarding ensure.
- Canonical routes: `GET/POST /settings/academic-years`,
  `GET /settings/academic-years/current`, `PATCH /settings/academic-years/{id}/current`.
- `GET .../current` auth-only; school-bound read ensures the default current year,
  platform/no-school returns `null`. Other GETs stay read-only.
- `AcademicYearRead` / `open_academic_year` / `make_academic_year_current` rename.
- Senior role gate: principal/vice read-only; `system_admin`/`school_admin`
  (future director/admin) can change. Permission lists and matrix tests updated.
- Current-switch now flushes old flag before setting new (partial unique index safety).
- `academic_year` model also declares `uq_academicyear_one_current` for fresh DB/tests.
- Course completion + placement now delegate to the shared helper.
- Frontend service paths point at `/settings/academic-years`; the existing selector's
  `canManage` also checks a senior role, so a stale permission grant cannot show the
  switch to a principal (UI rename remains Phase 2).
- Tests: `test_academic_year.py` + `test_permission_matrix.py` **31 passed**;
  course suite **72 passed**; `test_phase2_schema.py` **12 passed**; course frontend
  **13 passed**; ruff clean; `tsc --noEmit` clean; app OpenAPI has **237 paths** with
  the new routes.

---

### Phase 2 — Navbar: academic year sabko, hamesha

> **Important - Next-phase gate:** Jab user is phase ke liye “next” bole, pehle is phase ka deep plan banao (current code, files, schema, tests, risks), phir implement karo. Bina deep plan code na likho.

**Goal:** Navbar par `2026-27` ya amber `Academic year not set` — har role, har page.
Manager wahan se open/switch kar sake; baaki sirf dekh sake.

**Files (expected):**

- `frontend/src/components/layout/AcademicYearSelect.tsx`
- `frontend/src/components/layout/AppLayout.tsx`
- `frontend/src/providers/academic-year-context.ts` + `AcademicYearProvider.tsx` (new)
- `frontend/src/app/dashboard/layout.tsx` (provider wrap)
- `frontend/src/services/academic-year.service.ts`
- `frontend/src/types/index.ts`
- `frontend/src/lib/academic-year/view.ts` + `view.test.ts` (new, pure helpers)

**Tasks:**

- [x] `getCurrentAcademicYear()` service add karo; service/component ke purane
      “settings.read” comments ko naye auth-only current read ke hisaab se update karo.
- [x] Frontend ke purane selector/service/type names ko `getAcademicYears`,
      `AcademicYear`, `AcademicYearSelect`, `academic-year.service.ts` par rename karo;
      imports aur tests saath update karo.
- [x] Provider add karo; current query `["academic-year", "current"]`.
- [x] `AcademicYearSelect` ko provider par shift karo.
- [x] `canManage` = `academic_year.manage` **+** senior role
      (`school_admin`/`system_admin`; future director/admin); principal/vice ko
      button na dikhe, server bhi `403` de.
- [ ] Live DB ke stale `rolepermission` grants (principal/vice) cleanup Phase 10
      rollout mein; seed sirf add karta hai, remove nahi. Server role gate aur frontend
      role check already safety net hain.
- [x] `if (years.length === 0) return null` **hatao**.
- [x] No academic year state: amber select + manager CTA; read-only for non-manager.
- [x] Manager CTA: only `current + 1`; response ke baad list refresh/invalidate.
- [x] Full list manager ke control ke saath load hoti hai; non-manager current only.
- [x] Existing academic year: all past visible + switch with confirmation.
- [x] Native `Select`; change par `Modal` confirmation.
- [x] Open/switch ke baad current query bhi invalidate ho.
- [x] Pure helper `academicYearLabel`, `nextAcademicYearStart`, `academicYearChipState` +
      `node:test` tests.
- [x] `tsc --noEmit` clean.

**Acceptance:**

- Kisi bhi role se login: navbar par academic year chip ya `Academic year not set` dikhe.
- Manager no-academic-year state se ek click mein `2026-27` open kar sake.
- Non-manager ko open/switch control nahi dikhe.
- Academic year switch karne par Course/attendance/fees queries refresh hon.
- Switch ke baad current-year lists sirf naye year ka data dikhayein; purana data
  sirf “All academic years”/explicit old-year filter se aaye.
- Koi page reload ki zaroorat nahi.

**Manual check:**

1. DB mein academic year row delete/absent (staging) → navbar amber.
2. Manager open → chip green/normal `2026-27`.
3. Teacher login → sirf chip, koi switch nahi.

**Phase 2 completion — 20 Nov 2026:**

- `AcademicYearProvider` + `academic-year-context.ts`: one current-year query for the
  whole dashboard; `canManage` = permission + senior role.
- `AcademicYearSelect` always renders **below the school name, left-aligned**, as a
  compact topbar-surface picker; current year default selected; change par
  confirmation modal; saare past years visible with `01 Apr 2026 – 31 Mar 2027`;
  `+ Open 2027-28` dropdown mein always visible, disallowed par message; non-manager
  read-only.
- Full list is fetched for a manager with the control; non-manager sees current only.
- Renames done: `AcademicYear`, `getAcademicYears`, `getCurrentAcademicYear`,
  `openAcademicYear`, `setCurrentAcademicYear`, `academic-year.service.ts`,
  `AcademicYearSelect.tsx`.
- Open/switch invalidates the whole query cache and refreshes the current-year query.
- Pure helpers: label, next start, chip state, manager rule.
- Tests: academic-year helpers **5 passed**; `tsc --noEmit` clean. Browser smoke
  (staging open/switch) is still manual and not run in this environment.
- Still pending: stale live-DB `rolepermission` cleanup for principal/vice is a
  Phase 10 rollout item; server role gate already blocks them.

---

### Phase 3 — Course unblock + friendly no-academic-year UX (immediate blocker)

> **Important - Next-phase gate:** Jab user is phase ke liye “next” bole, pehle is phase ka deep plan banao (current code, files, schema, tests, risks), phir implement karo. Bina deep plan code na likho.

**Goal:** “Open the current academic year” raw error ki jagah samajh aane wala
banner/dialog; Add Subject tab tak disabled jab tak academic year na ho. Academic year open
hone par sab apne aap chalu.

**Files (expected):**

- `frontend/src/components/features/classroom/course/CoursePanel.tsx`
- `frontend/src/components/features/classroom/course/AddSubjectDialog.tsx`
- `frontend/src/components/features/classroom/SectionDetailPage.tsx`
- `frontend/src/components/ui/dialog.tsx` (reuse; edit sirf zaroorat par)
- `frontend/src/lib/course/view.ts` + `view.test.ts`
- `backend/tests/test_course_subjects.py` (409 contract)
- `backend/tests/test_course_end_to_end.py` (agar flow add ho)

**Tasks:**

- [x] CoursePanel current academic year provider se read kare.
- [x] academic year absent: panel top par banner —
      “Is school ka academic year set nahi hai. Pehle navbar se current academic year open karein.”
      + `Open academic year` button (manager) / read-only message (non-manager).
- [x] Add Subject button disabled + tooltip; click par dialog nahi.
- [x] Subject add ke ilawa jo bhi academic year-dependent write hai (chapter add, teacher
      assign, plan submit) us par wahi guard — server `409` final guard rahega.
- [x] Agar 409 aaye (race/another tab): raw detail ki jagah friendly inline error/toast;
      banner mein manager CTA; technical detail log mein rahe.
- [x] Academic year open/switch ke baad panel apne aap enable ho (context invalidation).
- [x] `view.ts` mein `canWriteCourse(currentAcademicYear)` helper + test.
- [x] Backend 409 message "academic year" par stable; service messages update; course
      suite (39 targeted tests) pass.
- [ ] Live rollout: manager navbar se `2026-27` open kare; phir Course Add Subject
      verify karo. **Yeh current blocker ka actual fix hai.** (browser smoke pending)

**Acceptance:**

- No-academic year school mein Add Subject click hi na ho / disabled dikhe.
- 409 raw JSON screen par kabhi na dikhe.
- Academic year open karte hi Add Subject kaam kare, page reload ke bina.
- Course ke existing 82 backend tests + frontend tests pass.

**Phase 3 completion — 20 Nov 2026:**

- School-bound `GET /settings/academic-years/current` ab **default current year**
  ensure karta hai; first read par `2026-27` (today's year) create, second read
  idempotent. Platform/no-school par `null`.
- CoursePanel provider se current year read karta hai; no-year par banner + manager
  CTA; Add Subject disabled + tooltip.
- 409 academic-year errors friendly inline/toast; backend messages "academic year".
- `canWriteCourse()` helper + test; panel current year open hone par auto-enable.
- Tests: backend targeted **39 passed**; frontend **19 passed**; `tsc --noEmit` clean;
  ruff clean.
- Browser/live smoke pending (no server started in this environment).

---

### Phase 4 — Admission: target academic year via `enrollment`

> **Important - Next-phase gate:** Jab user is phase ke liye “next” bole, pehle is phase ka deep plan banao (current code, files, schema, tests, risks), phir implement karo. Bina deep plan code na likho.

**Goal:** Admission **current academic year** par ho (default current); student ka
academic year placement `enrollment` mein likhe. `student` table par year column nahi.
Target academic year API field optional hai; form abhi current year hi bhejta hai.

**Aaj ka behaviour:** `place_student()` current academic year `academic_year` ko
auto-create karke `enrollment` likhta hai. Admission `_admit()` isi ko call karta hai.

**Files (expected):**

- `backend/app/domains/operations/admission/schemas.py`
- `backend/app/domains/operations/admission/service.py`
- `backend/app/domains/operations/admission/repository.py`
- `backend/app/domains/operations/admission/router.py`
- `backend/app/domains/academic/classroom/students/placement.py`
- `backend/tests/test_admission_contacts.py`
- `backend/tests/test_admission_stats.py`
- `backend/tests/test_placement_academic_year.py` (new/extend)
- `frontend/src/components/features/admission/AdmissionForm.tsx`
- `frontend/src/components/features/admission/admission-options.ts`
- `frontend/src/services/admission.service.ts`
- `frontend/src/types/index.ts`

**Tasks:**

- [x] `AdmissionApplicationCreate` mein request-only field
      `target_academic_year_id: UUID | None` add karo. Ise `student` row par
      `model_dump` se exclude karo — `Student` mein column nahi hai.
- [x] Resolve: request ka year → tenant check → warna current academic year → warna
      `ensure_current_academic_year`. Unknown/cross-tenant year `404`.
- [x] `place_student(session, student, classroom_id, year=None, update_current=True)`
      signature add karo; default `current_academic_year`; `enrollment` usi year ke saath likho.
- [x] **Current academic year admission:** `place_student` se `student.classroom_id` + enrollment.
- [x] **Future-academic year admission backend:** target year enrollment, `update_current=False`;
      form UI abhi current default hai.
- [x] Duplicate enrollment `UNIQUE(school_id, student_id, academic_year_id)` par
      race-safe upsert; duplicate row nahi.
- [x] Admission list/stats par optional `academic_year_id` filter; frontend current year
      pass karta hai, so switch par list/stats refetch.
- [x] Backfill: first current-year bootstrap par existing placed students ke liye current
      enrollment rows; `student.classroom_id` null ho to skip. (Dedicated test pending.)
- [ ] Frontend form mein “academic year” dropdown (current default; future option) —
      current release demands current year, isliye deferred.
- [ ] Admission list header/filter par current academic year + “All academic years”.
- [x] Tests: default current, admission writes enrollment; existing admission tests pass.
- [ ] Explicit future/cross-tenant/list-filter tests; separation field Phase 4B.

**Acceptance:**

- Admission save hone par `enrollment` row us academic year ki bane jo form mein chuni thi.
- `student` ki identity columns unchanged; placement sirf `enrollment` se.
- Current academic year admission puraani tarah kaam kare.
- Same student ke do academic year placements possible; same academic year duplicate nahi.
- Admission list current academic year default dikhaye; All academic years par sab.

**Phase 4 core completion — 20 Nov 2026:**

- Admission ab `place_student` se `enrollment` likhta hai; `student.classroom_id` direct
  write nahi.
- Target academic year request-only API field; default current year; future year
  backend support (`update_current=False`).
- Admission list/stats optional `academic_year_id` filter; frontend current year pass
  karta hai, isliye academic year switch par list/stats refetch.
- First current-year bootstrap existing placed students ke enrollment backfill karta hai.
- New test proves admission writes current-year enrollment; admission tests **11 passed**.
- Pending: existing-student backfill, target-year form dropdown, list header/filter,
  explicit future/cross-tenant tests. UI current-year default ke saath ship ho sakta hai.

---

### Phase 4B — Promotion-safe schema, class teacher history, promotion apply

> **Important - Next-phase gate:** Jab user is phase ke liye “next” bole, pehle is phase ka deep plan banao (current code, files, schema, tests, risks), phir implement karo. Bina deep plan code na likho.

**Goal:** Section 4A ka schema live karo: enrollment history, class teacher per year,
promotion batch/decision, switch par current placement reconcile.

**Implemented backend core (20 Nov 2026):**

- `enrollment.previous_enrollment_id` + timestamps; migration
  `f4b1c2d3e4f5_promotion_safe_schema.py`.
- `student.separation_academic_year_id` optional FK (server-managed; legacy text
  backfill pending).
- `classteacherassignment` table with open-assignment partial unique index; current
  `classroom.class_teacher_id` sync on assign.
- `promotionbatch` + `promotiondecision`, draft/decisions/apply API at
  `/promotions`; apply uses `place_student(..., commit=False)` so the batch is one
  transaction and links `previous_enrollment_id`.
- Academic-year switch now reconciles `student.classroom_id` from the new current
  year's active enrollments and class teachers from open assignments.
- Promotion tests: `tests/test_promotion.py` (3 passed); academic-year regression
  18 passed; lifecycle/classroom 14 passed; permission matrix 13 passed.

**Still pending in 4B:** promotion screen/service/types, rolling `roll_no` uniqueness,
separation-text backfill, bulk insert/chunk optimisation, `PATCH` batch edits, and
class-teacher HTTP tests with a real employee row.

**Files (expected):**

- `backend/app/domains/academic/classroom/students/models.py` (`Enrollment`, `Student`)
- `backend/app/domains/academic/classroom/students/placement.py`
- `backend/app/domains/academic/classroom/academics/models.py` (`Classroom`, class teacher)
- `backend/app/domains/academic/classroom/students/promotion/{__init__,models,schemas,service,router}.py` (new)
- `backend/app/domains/admin/settings/academic_years.py` (switch hook)
- `backend/alembic/versions/<rev>_academic_year_promotion.py` (new)
- `backend/tests/test_promotion_schema.py` (new)
- `backend/tests/test_promotion_apply.py` (new)
- `backend/tests/test_placement_academic_year.py` (extend)
- `frontend/src/components/features/students/PromotionPanel.tsx` (new, minimal)
- `frontend/src/services/promotion.service.ts`
- `frontend/src/types/index.ts`

**Schema tasks (Section 4A):**

- [ ] `enrollment.previous_enrollment_id` self-FK, `created_at/updated_at`; status
      vocabulary expand; roll unique index; backfill nothing destructive. `Enrollment`
      ka purana “stub” docstring update karo; `set_enrollment_status` naye statuses
      support kare.
- [ ] `student.separation_academic_year_id` optional FK; existing separation text
      column se backfill; legacy text ko baad ke migration mein drop. Field
      server-managed hai, admission request ise set na kare.
- [ ] `classteacherassignment` table; current `classroom.class_teacher_id` se current
      year ka row backfill; partial unique open assignment. Writes/backfill is phase;
      reads cutover Phase 5 mein. Class teacher assign karne ke liye existing
      `classes.configure`/teacher permission reuse karo; naya parallel permission nahi.
- [ ] `promotionbatch` + `promotiondecision` tables, constraints/checks/indexes.
- [ ] Ek hi student/year enrollment ka DB test; do current class teacher ka DB test.

**Service/API tasks:**

- [ ] `GET/POST /students/promotions` (draft batch), `GET/PATCH /students/promotions/{id}`.
- [ ] `POST /students/promotions/{id}/apply` — `students.promote`, transaction/chunk,
      idempotent, stale/already-applied `409`.
- [ ] Apply promote/repeat `place_student(..., year=to, update_current=...)` se kare;
      direct `enrollment`/`student.classroom_id` write na ho. `previous_enrollment_id`
      link; old status `promoted`/`repeated`; transfer/leave/graduate close only.
- [ ] `to` academic year current ho tab `student.classroom_id` update; warna switch tak
      untouched.
- [ ] Academic year switch par `reconcile_current_placements`: current year enrollment
      se `student.classroom_id` set; missing enrollment ko list/flag karo, auto-promote
      nahi. Reconciliation bhi placement service se.
- [ ] Bulk `INSERT`/chunk; per-student N+1 nahi; `UNIQUE` violation race-safe.
- [ ] Frontend minimal: batch list, student decisions, apply confirm, counts;
      non-manager read-only.

**Tests:**

- [ ] Promote: new enrollment, old status, previous link, current pointer.
- [ ] Repeat: same class, new enrollment, old `repeated`.
- [ ] Transfer/leave/graduate: no next enrollment, old closed.
- [ ] Apply twice: no duplicate; `409`/idempotent.
- [ ] Switch academic year: placements reconcile; un-enrolled student flagged.
- [ ] Class teacher change: old closed, new open, history intact.
- [ ] Cross-tenant student/batch/classroom `404`.

**Acceptance:**

- Promotion batch apply ke baad student ka naya enrollment/class sahi; purana record
  untouched.
- Same batch dobara apply nahi hota.
- Current academic year switch par `student.classroom_id` current enrollment se match.
- Class teacher ka purana year ka record safe.

---

### Phase 5 — Timetable + class teacher read cutover: academic-year-scoped periods

> **Important - Next-phase gate:** Jab user is phase ke liye “next” bole, pehle is phase ka deep plan banao (current code, files, schema, tests, risks), phir implement karo. Bina deep plan code na likho.

**Goal:** Har timetable period kis academic year ka hai pata chale; purane saal ka timetable
naye saal ke clashes na roke. Bell schedule (school day shape) year-scoped nahi.

**Implemented backend core (20 Nov 2026):**

- `timetableperiod.academic_year_id` nullable FK + index; migration
  `b7e2f4a9c1d3_timetable_academic_year.py`.
- Existing rows current year se backfill; unique keys
  `(school, academic_year, teacher/classroom, day, start)`.
- Create server-side current year stamp karta hai; read/grid/clash/period counts
  current year (legacy NULL rows fallback) filter karte hain.
- Same teacher/slot alag years mein allowed; same year duplicate `409`.
- `current_class_teacher_id` / class-teacher classroom helper current year’s
  `classteacherassignment` se padhta hai; fallback legacy pointer.
- Classroom screen’s class-teacher assign path ab history row + pointer sync karta hai.
- Notifications, chat, class grid, classroom drill-down, teacher workload and scope
  checks current-year assignment se read karte hain.
- Timetable isolation test added; combined timetable/promotion/academic/notifications/
  communications/lifecycle/classroom/permission suite **61 passed**.

**Still pending in Phase 5:** full removal of the legacy `classroom.class_teacher_id`
pointer after every remaining reader is migrated, plus timetable frontend's historic
year picker (API already supports `?academic_year_id=`; past rows are read-only).

**Files (expected):**

- `backend/app/domains/academic/classroom/timetable/models.py`
- `backend/app/domains/academic/classroom/timetable/repository.py`
- `backend/app/domains/academic/classroom/timetable/service.py`
- `backend/app/domains/academic/classroom/timetable/router.py`
- `backend/app/domains/academic/classroom/timetable/schemas.py`
- `backend/alembic/versions/<rev>_academic_year_scope_timetable.py`
- `backend/tests/test_timetable.py` (ya existing file)
- `frontend/src/components/features/classroom/timetable/TimetablePanel.tsx`
- `frontend/src/services/timetable.service.ts`
- `frontend/src/types/index.ts`

**Schema:**

- [ ] `timetableperiod.academic_year_id` FK `academic_year.id`, index, NOT NULL.
- [ ] Purane rows current academic year se backfill; current na ho to migration clear
      error de (“open an academic year first”) — silently guess na kare.
- [ ] `uq_timetableperiod_teacher_slot` drop karke
      `(school_id, teacher_id, academic_year_id, day_of_week, start_time)` banao.
- [ ] `uq_timetableperiod_class_slot` drop karke
      `(school_id, classroom_id, academic_year_id, day_of_week, start_time)` banao.
- [ ] Downgrade: constraints wapas purane shape mein, column drop (data loss note).

**Service/API:**

- [ ] Create par year server current se stamp kare; body se year accept na karo.
- [ ] Read/grid current academic year default; `?academic_year_id=` se historic view.
- [ ] Clash check current academic year ke andar; dusre saal ka same slot clash nahi.
- [ ] Teacher workload periods current academic year count kare.
- [ ] Update current academic year ka row hi edit kare; purane academic year read-only.
- [ ] 409 message mein academic year/weekday/slot saaf ho.
- [ ] Class teacher reads `classteacherassignment` se current year ka open row; write
      naya assignment + `classroom.class_teacher_id` pointer sync. Purana year read-only.
- [ ] Academic year switch par class teacher pointer bhi new year ke open assignment se
      reconcile karo; assignment na ho to null, purana teacher stale na dikhe.
- [ ] Saare reads shift hone ke baad `classroom.class_teacher_id` drop karo (separate
      migration; pehle invariant test).

**Frontend:**

- [ ] Timetable header par current academic year label (navbar se).
- [ ] Academic year switch par grid auto-refresh.
- [ ] Class teacher selector current academic year ki assignment likhe; purana year
      read-only.
- [ ] Historic academic year view read-only (agar academic year picker diya jaye).

**Tests:**

- [ ] Same teacher + same slot do alag academic years mein allowed.
- [ ] Same academic year duplicate `409`.
- [ ] Create current-year stamp; cross-tenant year `404`/`422`.
- [ ] Class teacher assignment current year; purana year read-only.
- [ ] Existing timetable API tests update.

**Acceptance:**

- Naya period current academic year mein bane.
- Purana academic year switch karke dekhne par wahi periods dikhein, edit na ho.
- Naye saal ka timetable purane saal ki clash se block na ho.

---

### Phase 6 — Fees: academic-year-scoped fee structure

> **Important - Next-phase gate:** Jab user is phase ke liye “next” bole, pehle is phase ka deep plan banao (current code, files, schema, tests, risks), phir implement karo. Bina deep plan code na likho.

**Goal:** Fee head/amount har academic year ka apna; fee card current academic year dikhaye.
Receipt (`feetransaction`) structure se year inherit kare — usme alag column nahi.

**Implemented backend core (20 Nov 2026):**

- `feestructure.academic_year_id` nullable FK + index; migration
  `c9e3a5b7d1f2_fee_structure_academic_year.py`.
- Existing fee heads current year se backfill; legacy NULL rows read fallback.
- New fee head server-side current year stamp karta hai.
- Fee card/list current year default; `?academic_year_id=` se historic read.
- Past year's fee card edit/publish `409` read-only; legacy row first update par
  current year stamp.
- Fee tests: current-year stamp + year isolation **2 passed**.
- Fee transaction par naya year column nahi; receipt still structure se inherit karega.

**Files (expected):**

- `backend/app/domains/operations/fees_structure/models.py`
- `backend/app/domains/operations/fees_structure/schemas.py`
- `backend/app/domains/operations/fees_structure/service.py`
- `backend/app/domains/operations/fees_structure/repository.py`
- `backend/app/domains/operations/fees_structure/router.py`
- `backend/tests/test_fees_structure.py` (ya existing)
- `frontend/src/components/features/operations/fees/…` (structure card/form)
- `frontend/src/services/fees.service.ts`
- `frontend/src/types/index.ts`
- `backend/alembic/versions/<rev>_academic_year_scope_fees.py`

**Tasks:**

- [ ] `feestructure.academic_year_id` FK, index, NOT NULL; separate migration
      (`academic_year_scope_fees`) — timetable migration se alag rollback.
- [ ] Backfill current academic year; current na ho to migration error.
- [ ] Create server current academic year se stamp kare; request body ka year validate.
- [ ] List/read default current; `?academic_year_id=` historic; “All academic years” option.
- [ ] Same class + fee name ka naya saal allowed; purana row preserved.
- [ ] `feetransaction` creation structure se year derive kare; transaction par
      column na add ho. Receipt/read mein academic year label parent se aaye.
- [ ] Fee collection/report current academic year default; historic receipts preserve.
- [ ] Frontend fee structure screen current academic year label + filter.
- [ ] Tests: same fee head two years; old row untouched; cross-tenant; receipt parent.

**Acceptance:**

- Naya fee head current academic year mein bane.
- Purane academic year ka fee card naye saal mein na dikhe.
- Purani fee receipt ka amount/structure na badle.
- Fee report default current, All academic years par purani entries.

---

### Phase 7 — Exams, holidays, leave balances: optional year ko consistent karo

> **Important - Next-phase gate:** Jab user is phase ke liye “next” bole, pehle is phase ka deep plan banao (current code, files, schema, tests, risks), phir implement karo. Bina deep plan code na likho.

**Goal:** Jin tables mein `academic_year_id` already hai (optional) unke null rows
backfill ho; naye records current par jayein; historic filter kaam kare.

**Implemented backend core (20 Nov 2026):**

- `exam`: naya exam server current year stamp karta hai; list current year default
  (`?academic_year_id=` historic); direct/normalized create payload ka year optional.
- `holiday`: create current year stamp karta hai; date-window calendar behavior
  preserve hai (holiday date hi actual scope hai); migration legacy rows ko date
  window se backfill karta hai.
- Migration `d4f6a8b2c9e1` existing `exam`/`holiday`/`leaverequest` null rows ko
  unki date window wale academic year se backfill karta hai.
- `leaverequest.academic_year_id` optional FK + index; migration
  `d4f6a8b2c9e1_leave_request_academic_year.py`; legacy rows `from_date` window se
  backfill; staff/student apply par year stamp.
- Leave date calculations unchanged (`labels.leave_year`), so existing balances
  and tests remain valid.
- Exam/holiday/leave + fee/timetable regression suite **98 passed**.

**Files (expected):**

- `backend/app/domains/academic/classroom/exams/models.py`
- `backend/app/domains/academic/classroom/exams/service.py`
- `backend/app/domains/admin/settings/calendar.py`
- `backend/app/domains/admin/settings/models.py` (holiday)
- `backend/app/domains/services/leave/service.py`
- `backend/tests/test_exams.py`, `test_holidays.py`, `test_leave.py` (existing)
- Frontend exams/calendar/leave pages + services/types

**Tasks:**

- [ ] `exam.academic_year_id` backfill: `start_date`/`end_date` se
      `academic_year_for_date`; na mile to current; phir bhi null ho to current.
- [ ] New exam server current stamp kare; list current default; `?academic_year_id=`
      historic. Column nullable rahe ya NOT NULL ho — migration decision note
      (recommended: backfill ke baad NOT NULL).
- [ ] Exam paper/marks child tables untouched; year exam se.
- [ ] `holiday.academic_year_id` backfill `on_date` ke academic year se; date kisi bhi
      academic year window mein na aaye to null allowed (legacy); naya holiday current.
- [ ] Holiday list/calendar current default; “All” option.
- [ ] `leavebalance.academic_year_id` abhi optional hai — `year`/current se backfill;
      create/read current default; backfill ke baad NOT NULL ka decision note karo.
      Naye academic year open par balance **auto-copy nahi** (policy decision); UI current
      dikhaye, historic read-only.
- [ ] Academic year switch par exams/calendar/leave queries refresh.
- [ ] Tests: old null exam backfilled, new exam current, historic exam visible after
      switch, holiday date→academic year, leave balance per year.

**Acceptance:**

- Koi naya exam/holiday binan academic year ke na bane.
- Purane records current/derived academic year ke saath dikhein.
- Academic year switch par list ka scope badle, data delete na ho.

---

## 8. Date-derived modules — column nahi, filter/derive

Yeh phase naye column nahi banata. Yahan academic year **reporting lens** hai.

### Phase 8 — Attendance, salary, hiring, reports

> **Important - Next-phase gate:** Jab user is phase ke liye “next” bole, pehle is phase ka deep plan banao (current code, files, schema, tests, risks), phir implement karo. Bina deep plan code na likho.

**Goal:** Date-based modules current academic year ke default filter ke saath chalein;
“All academic years” par history; `academic_year_for_date` hi sach ho.

**Implemented backend core (20 Nov 2026):**

- Shared `academic_year_window(session, academic_year_id, all_years=...)`:
  current default, named year tenant-checked (`404`), all-years no filter.
- Salary register: `academic_year_id` + `all_academic_years` params; month labels
  (`Sep 2026`) parsed to dates and filtered by April–March window.
- Hiring candidates: `academic_year_id` + `all_academic_years` params; `applied_on`
  date filtered by the same window.
- No new year column on `salarypayment`, `hiringcandidate`, attendance or staff;
  year remains derived from the row's date.
- Existing date-based behavior is preserved when no current year is open.
- Attendance/exam/holiday regression suite **98 passed**; salary/hiring use the same
  shared window and keep their date-derived behavior.

**Files (expected):**

- `backend/app/domains/admin/settings/academic_year_context.py` (reuse)
- `backend/app/domains/academic/classroom/attendance/service.py`
- `backend/app/domains/people/teachers/staff_attendance/service.py`
- `backend/app/domains/operations/salary/service.py`
- `backend/app/domains/people/staff/service.py` (hiring/joining)
- `backend/app/domains/operations/admission/service.py` (already Phase 4)
- Reports/dashboard services
- `backend/tests/test_attendance_academic_year_filters.py` (new)
- `backend/tests/test_salary_academic_year_filters.py` (new)
- Frontend attendance/salary/staff/report pages + services

**Hiring / staff:**

- [ ] Employee par year column **nahi**. Joining date se academic year derive:
      `academic_year_for_date(employee.joining_date)`.
- [ ] Hiring list/report current academic year default; “All academic years” option.
- [ ] Joining future date ho to woh future academic year count ho; current nahi.
- [ ] Interview/appointment records date-based; koi year column nahi.

**Attendance:**

- [ ] Student attendance register/date range current academic year default.
- [ ] Staff attendance same.
- [ ] `date` ko academic year bounds se filter karo; row par year add na karo.
- [ ] Monthly summary academic year ke months ke hisaab se (April–March).
- [ ] “All academic years” par date range explicit; default current.

**Salary:**

- [ ] Salary register `month`/`paid_on` se academic year derive.
- [ ] Default current academic year; “All academic years” par purane payslips.
- [ ] Salary payment par year column nahi; academic year label derived.

**Reports/dashboard:**

- [ ] Shared query param: `academic_year_id` (default current) aur `all_academic_years=true`.
- [ ] Server-side resolve; browser se aaya unknown year 404.
- [ ] Dashboard count tiles current academic year; “All” toggle optional.
- [ ] Export (CSV/PDF) header mein academic year name; current default.
- [ ] Academic year switch par reports refetch.

**Tests:**

- [ ] 31 Mar / 1 Apr boundary attendance correct academic year mein.
- [ ] Salary month April vs March.
- [ ] Joining date future/current.
- [ ] Unknown/other-tenant academic year 404.
- [ ] “All academic years” bina filter ke sab rows deta hai (tenant ke andar).

**Acceptance:**

- Attendance/salary/hiring rows mein koi naya year column nahi.
- Default screens current academic year dikhayein.
- Purana data “All academic years”/date range se accessible rahe.
- Boundary dates par galat academic year nahi.

---

## 9. App-wide polish

### Phase 9 — App-wide academic year polish (banners, filters, settings card)

> **Important - Next-phase gate:** Jab user is phase ke liye “next” bole, pehle is phase ka deep plan banao (current code, files, schema, tests, risks), phir implement karo. Bina deep plan code na likho.

**Goal:** Academic year sirf navbar ka decoration na rahe; jahan zaroori hai wahan ek hi
tarah ka banner/filter dikhe, aur settings page par bhi same source se manage ho.

**Implemented frontend (20 Nov 2026):**

- New `AcademicYearRequiredBanner` — manager ko “Open current academic year” CTA,
  non-manager ko read-only message; provider/service reuse, duplicate logic nahi.
- Banner added to Course, Admission, Fees Structure, Timetable, Attendance,
  Exams and Reports pages.
- New `AcademicYearSettingsCard` in Settings; embeds the same `AcademicYearSelect`
  and provider, so settings/navbar can never disagree.
- Navbar control remains compact, left aligned under school name, with dates,
  confirmation and always-visible next-year CTA.
- Pages that do not need a year (profile/theme/notifications) unchanged.
- `tsc --noEmit` clean.

**Files (expected):**

- `frontend/src/components/layout/AcademicYearRequiredBanner.tsx` (new)
- `frontend/src/components/layout/AcademicYearFilter.tsx` (new, optional)
- `frontend/src/app/dashboard/settings/…` (academic year card)
- Course, admission, exams, fees, timetable, attendance, reports pages
- `frontend/src/lib/academic-year/view.ts` + tests
- `backend/tests/test_permissions_academic_year.py` (new)

**Tasks:**

- [ ] `AcademicYearRequiredBanner` ek hi component se:
      - manager: “Open current academic year” CTA,
      - non-manager: “Office se academic year open karwayein”,
      - dismissible sirf dashboard ke first-run prompt par; data pages par sticky.
- [ ] Academic year-dependent pages par banner lagao: Course, Admission, Exams, Fees,
      Timetable, Attendance, Reports, Promotion. Har page apna alag message na banaye.
- [ ] Jin pages ko academic year ki zaroorat nahi (profile, settings theme, notifications
      feed) wahan banner na lagao.
- [ ] Settings page ka academic year card `AcademicYearProvider`/same service use kare;
      duplicate open/switch logic na ho.
- [ ] Date-based pages ke header mein current academic year label; filter ho to
      `Current academic year` / `All academic years`.
- [ ] First-run dashboard prompt: manager ke liye “Set up 2026-27”; dismiss ho to
      academic year open hone tak navbar amber rahe.
- [ ] Role tests: principal se senior roles (`system_admin`/`school_admin`; future
      `director`/`admin`) manage karein; principal/vice/teacher/accountant/student/staff
      read-only; non-senior ko switch route se 403.
- [ ] Mobile: banner full width, CTA thumb-friendly; year select/modal overflow na kare.

**Acceptance:**

- Har academic year-dependent page par same banner/CTA pattern.
- Non-manager ko kahin bhi open/switch nahi mile.
- Settings card aur navbar kabhi alag current academic year na dikhayein.
- First-run manager 2 click mein academic year set kar sake.

---

## 10. Hardening & rollout

### Phase 10 — Hardening, contract tests, migration, rollout

> **Important - Next-phase gate:** Jab user is phase ke liye “next” bole, pehle is phase ka deep plan banao (current code, files, schema, tests, risks), phir implement karo. Bina deep plan code na likho.

**Goal:** “Sirf jahan chahiye wahan year” ko test se lock karo; live migration
backup ke saath; deploy ke baad Course + academic year flow verify.

**Implemented hardening (20 Nov 2026):**

- `tests/test_academic_year_scope_contract.py` locks the exact set of tables that
  own `academic_year_id`; child/date tables are explicitly forbidden from carrying
  a second copy, and `student` is allowed only its `separation_academic_year_id`.
- `tests/test_phase3_migration.py` parses the revision files and asserts one head;
  the old heads are joined by no-op merge revision `e5a7b9c1d3f4`, with parent
  `d4f6a8b2c9e1` and the two legacy branches.
- Contract tests: **3 passed**; migration tests: **2 passed**.
- Live migration/backup/smoke remain deployment steps, not code steps.

**Files (expected):**

- `backend/tests/test_academic_year_scope_contract.py` (new)
- `backend/tests/test_phase3_migration.py` (new)
- `backend/tests/test_promotion_schema.py`, `test_promotion_apply.py`
- Existing course/admission/timetable/fees/attendance/salary tests
- `backend/phase3.md` (completion logs)
- `README.md` (academic year flow + scheduler note agar chahiye)
- `backend/phase2.md` (decisions/edge cases R33+)

**Tasks:**

- [ ] **Contract test:** DB inspector se `academic_year_id` wale tables ki exact set
      assert karo:
      - expected add: `timetableperiod`, `feestructure`, `classteacherassignment`
      - expected existing: `enrollment`, `subjectteacher`, `chapter`,
        `classroomsubject`, `lessonplan`, `exam`, `holiday`, `leavebalance`
      - expected absent: `student` (sirf `separation_academic_year_id` event field
        allowed), `employee`, `attendancerecord`, `staffattendancerecord`,
        `salarypayment`, `feetransaction`, `lessonplanhistory`, `chapterprogress`,
        `promotionbatch`, `promotiondecision`
      - Koi naya table galti se year column ke saath add ho to test fail.
- [ ] **Single-head migration test:** `alembic heads` ek hi ho; upgrade/downgrade
      on test DB.
- [ ] **One-current test:** DB partial unique index do current rows refuse kare.
- [ ] Full backend suite; full frontend `node --test`; `tsc --noEmit`; `ruff check`.
- [ ] Pre-deploy backup `backend/backups/phase3_<date>.dump` + SHA-256 note.
- [ ] `alembic upgrade head` live par; `alembic current` verify.
- [ ] `docker compose up -d --build`; health + route count.
- [ ] Post-deploy smoke:
      1. navbar `2026-27` (ya amber no-academic-year),
      2. manager open/switch,
      3. Course Add Subject,
      4. admission current-academic year enrollment,
      5. timetable period create,
      6. fee structure create,
      7. exam/holiday current stamp,
      8. attendance boundary date,
      9. teacher read-only.
- [ ] Backfill verification queries (counts null → 0 where expected).
- [ ] Promotion/placement smoke: draft batch, apply, switch, current placement match.
- [ ] Class teacher smoke: old year record + new year assignment both visible.
- [ ] `phase3.md` mein har phase ke completion log + actual migration revision.
- [ ] Rollback note: app image previous; migration downgrade only if needed
      (column drop = data loss, so backup first).

**Acceptance:**

- Contract test pass — year sirf allowed tables mein.
- Full suite green (existing 82 + naye tests).
- Live DB head par; backup maujood.
- Academic year open hone ke baad “Open the current academic year” error dobara nahi.
- Course, admission, timetable, fees sab current academic year mein kaam karein.

---

## 11. Migration & backfill playbook

### 11.1 Order (kabhi na badle)

1. **Academic year pehle:** manager navbar se current academic year open kare (Phase 2).
   Live DB mein aaj koi `academic_year` row nahi hai; migration ko current chahiye.
2. **Backup:** `backend/backups/phase3_<date>.dump` + size + SHA-256 note.
3. **Promotion schema (Phase 4B):** enrollment columns/status, student separation FK,
   `classteacherassignment`, `promotionbatch`, `promotiondecision`; backfill current
   class teacher/separation, phir constraints.
4. **Schema (nullable):** `timetableperiod.academic_year_id`,
   `feestructure.academic_year_id` nullable add karo.
5. **Backfill:** dono tables ke saare rows current academic year se stamp karo.
6. **Tighten:** columns NOT NULL; purane unique constraints drop karke naye
   academic-year-aware constraints banao.
7. **Exams/holidays backfill** (Phase 7) alag data step.
8. **Enrollment backfill** (Phase 4) placed students ke liye current academic year row.
9. **Class teacher / separation backfill** (Phase 4B) current class teacher assignment
   aur legacy separation year.
10. **Verify:** null counts zero, duplicate current zero, constraint names maujood.
11. **Deploy:** backend image, health, smoke.

### 11.2 Backfill sources

| Table | Source |
|---|---|
| `timetableperiod` | current academic year (timetable current-only tha) |
| `feestructure` | current academic year (fee card current-only tha) |
| `exam` | `start_date` → `end_date` → current |
| `holiday` | `on_date` ka academic year; bahar ho to null |
| `enrollment` | `student.classroom_id` + current academic year, missing rows only |
| `leavebalance` | `year` ka academic year; na mile to current |
| `classteacherassignment` | current `classroom.class_teacher_id` + current year |
| `student.separation_academic_year_id` | legacy separation text/date se |

### 11.3 Safety rules

- Academic-year column backfills idempotent hon (`WHERE academic_year_id IS NULL`);
  enrollment/class-teacher backfills bhi duplicate-safe `NOT EXISTS` se chalein.
- Ek hi transaction mein schema + backfill + constraint, jahan possible ho.
- Current academic year na ho to migration **fail loudly**, guess na kare.
- Koi row delete na ho; koi purana amount/date overwrite na ho.
- `enrollment` roll unique index lagane se pehle duplicate roll scan karo; duplicate
  mile to data clean karke index banao.
- `alembic check` ka pre-existing repo-wide drift is task ka part nahi; usse
  confuse na ho. Sirf naye migration ka drift zero hona chahiye.
- Migration offline SQL generate karne ki koshish na karo — yeh live schema
  inspect karti hai.

---

## 12. Testing & commands

### 12.1 Backend

```powershell
docker run --rm -v "D:\Prashant_saxena\Work\Educonnect\backend:/app" `
  --workdir /app --entrypoint sh eduverse-checks:latest `
  -c "python -m pytest tests/test_academic_year.py tests/test_academic_year_context.py tests/test_promotion_schema.py tests/test_promotion_apply.py -q"
```

Poora suite:

```powershell
docker run --rm -v "D:\Prashant_saxena\Work\Educonnect\backend:/app" `
  --workdir /app --entrypoint sh eduverse-checks:latest `
  -c "python -m pytest -q"
```

Ruff:

```powershell
docker run --rm -v "D:\Prashant_saxena\Work\Educonnect\backend:/app" `
  --workdir /app --entrypoint sh eduverse-checks:latest `
  -c "ruff check app tests"
```

### 12.2 Frontend

```powershell
cd frontend
node --test src/lib/academic-year/view.test.ts
node --test src/lib/course/view.test.ts
node node_modules/typescript/bin/tsc --noEmit
```

- Unit tests pure helpers ke liye (label, next year, chip state, canWriteCourse).
- Component ka manual role check: manager / teacher / accountant / student.
- Browser check: no-academic-year → navbar amber → open → chip normal → Add Subject enabled.

### 12.3 Test matrix (kam se kam)

| Case | Expected |
|---|---|
| Anonymous current academic year | `401` |
| Any role current academic year | `200`, null ya row |
| No academic year + Course add | `409`, friendly |
| No academic year + navbar | amber `Academic year not set` |
| Manager open first academic year | current `true` |
| Manager open next academic year | current `false` |
| Two current rows insert | DB `IntegrityError` |
| School A current read by School B | `null`/`404`, leak nahi |
| Timetable same slot two academic years | allowed |
| Timetable same slot same academic year | `409` |
| Fee head two academic years | dono safe |
| Exam/holiday new record | current stamp |
| Attendance 31 Mar vs 1 Apr | alag academic year |
| Salary March vs April | alag academic year |
| Employee joining future | future academic year |
| Same student/year second enrollment | DB `IntegrityError` |
| Two open class teachers same classroom/year | DB `IntegrityError` |
| Promotion apply twice | no duplicate; `409`/idempotent |
| Promotion switch | `student.classroom_id` = current enrollment |
| Transfer/leave/graduate | no next enrollment |
| Promotion batch other school | `404` |
| Year column on excluded table | contract test fail |

---

## 13. Do-not-break list

- **Course feature:** Phase 1–10 ke 82 tests, lesson plan versioning, approvals,
  notifications, D7 completion — sab unchanged.
- **Placement single writer:** admission/edit/move/lifecycle/promotion/reconcile sab
  `place_student`/placement service se; koi direct `student.classroom_id` ya
  `enrollment` write na kare.
- **Promotion history:** applied batch/decision/enrollment delete/reverse na ho;
  correction history se.
- **Class teacher pointer:** `classroom.class_teacher_id` aur current
  `classteacherassignment` teacher equal rahein, jab tak column drop na ho.
- **One current:** koi endpoint/seed/script do current rows na banaye.
- **Child tables:** `lessonplanhistory`, `chapterprogress`, `marks`,
  `exam_paper_chapter`, `feetransaction` par year column na add ho.
- **Salary:** paid amounts immutable; year sirf derived filter.
- **Attendance:** unique keys `(school, student, date, subject)` aur staff
  `(school, employee, date)` untouched.
- **Timetable:** constraint swap ek transaction mein; purane data loss na ho.
- **Tenant isolation:** academic year list/current/derive sab `school_id` scoped.
- **No hardcoded year:** `2026-27` sirf example hai; code date se derive kare.
- **No silent switch:** “Open next academic year” current ko badal na de.
- **No frontend-only stamp:** browser ka year server validation ke bina trust na ho.
- **No academic year on every table:** Section 3.5 ki list authoritative hai.

---

## 14. Open questions (recommendation ke saath)

| # | Sawal | Recommended default |
|---|---|---|
| Q1 | Future-academic year admission sirf `enrollment` mein jaye, current class na badle? | Haan; current placement tab badle jab academic year current ho. |
| Q2 | Timetable purane academic years ke liye retain karein? | Haan; warna clash/history dono adhoore. |
| Q3 | `exam.academic_year_id` NOT NULL karein? | Backfill ke baad haan. |
| Q4 | `holiday.academic_year_id` NOT NULL karein? | Nahi; legacy out-of-window dates null rahein. |
| Q5 | Naye academic year par leave balances auto-copy? | Nahi; policy/HR decision. Carry-forward later phase. |
| Q6 | “All academic years” sab read roles ko? | Haan tenant ke andar; sensitive export par manage right. |
| Q7 | `student.separation_academic_year_id` ko FK banayein? | Haan; Phase 4B mein FK + backfill, legacy text drop. |
| Q8 | Fee structure naye saal mein copy karein? | Manual “copy last year” CTA future; auto-copy nahi. |

Yeh answers Phase 4+ se pehle confirm kar lena. Jab tak confirm na ho, upar wale
recommended defaults hi plan hain.

---

## 15. Definition of done (poora feature)

- [ ] Navbar har role ko academic year ya `Academic year not set` dikhata hai.
- [ ] Principal se senior roles (`school_admin`/`system_admin`) open/switch kar sakte
      hain; principal/vice/baaki read-only.
- [ ] Current academic year read auth-only endpoint se aata hai; school-bound read
      default current year ensure karta hai; baaki GETs read-only rehte hain.
- [ ] Course no-academic-year par Add Subject disable + banner; academic year open par enabled.
- [ ] Admission target academic year `enrollment` mein likhta hai; `student` identity unchanged.
- [ ] Har promotion/repeat/transfer/leave ka enrollment history record hai; current
      `student.classroom_id` current year enrollment se match karta hai.
- [ ] Promotion batch draft/apply idempotent; duplicate enrollment/decision DB se rukta hai.
- [ ] Class teacher har academic year ka record `classteacherassignment` mein hai.
- [ ] Timetable aur fee structure academic-year-scoped; unique keys year-aware.
- [ ] Exam/holiday/leave current default; historic data preserved.
- [ ] Attendance/salary/hiring date se academic year derive karte hain; naya column nahi.
- [ ] Reports current default + All academic years; exports par academic year label.
- [ ] Contract test prove karta hai ki year sirf allowed tables mein hai.
- [ ] Full backend + frontend suite green; migration single-head; live smoke pass.
- [ ] `phase3.md` completion logs bhare hue; backup artifact note.

---

## 16. Completion log

| Phase | Status | Date | Note |
|---|---|---|---|
| Phase 0 — plan/schema file | ✅ Complete | 20 Nov 2026 | `backend/phase3.md` created/updated; code untouched. |
| Phase 1 — backend foundation | ✅ Complete | 20 Nov 2026 | Helper, current endpoint, route/role changes, tests. |
| Phase 2 — navbar | ✅ Complete | 20 Nov 2026 | Always-visible chip, provider, role gate; DB cleanup Phase 10. |
| Phase 3 — Course unblock | ✅ Complete | 20 Nov 2026 | Default current year, Course banner/guard, friendly 409. |
| Phase 4 — admission/enrollment | 🟡 Core complete | 20 Nov 2026 | Current-year enrollment + filters + backfill; target picker/list UI pending. |
| Phase 4B — promotion schema/apply | 🟡 Backend core complete | 20 Nov 2026 | Enrollment chain, class teacher history, batch draft/apply, switch reconcile; UI/roll/backfill pending. |
| Phase 5 — timetable + cutover | 🟡 Backend core complete | 20 Nov 2026 | Year-scoped periods, clash isolation, class-teacher reads; historic API/pointer drop pending. |
| Phase 6 — fees | 🟡 Backend core complete | 20 Nov 2026 | Year-scoped fee heads, current stamp, historic read; fee UI copy/history pending. |
| Phase 7 — exams/holidays/leave | 🟡 Backend core complete | 20 Nov 2026 | Exam current stamp/filter, leave request year stamp/backfill, holiday current stamp; leave balance/UI polish pending. |
| Phase 8 — date-derived | 🟡 Backend core complete | 20 Nov 2026 | Shared year window, salary/hiring filters; attendance/report UI polish pending. |
| Phase 9 — app-wide polish | ✅ Frontend complete | 20 Nov 2026 | Shared banner, settings card, page coverage; first-run dismiss prompt optional. |
| Phase 10 — hardening | 🟡 Contract/migration complete | 20 Nov 2026 | Single-head merge + contract tests; live backup/migration/smoke pending. |

---

## 17. Next step

**Phase 10 contract/migration hardening complete (20 Nov 2026).** Remaining work
is deployment, not another feature phase: backup, `alembic upgrade head`,
service rebuild and the smoke checklist.

Pending polish: promotion frontend, roll uniqueness, separation backfill,
timetable/fee/leave historic UI, first-run dismiss prompt, and final
`classroom.class_teacher_id` pointer drop.
