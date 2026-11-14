# PHASES — Teachers module ka master plan (Hinglish)

> Yeh file hi is kaam ka `PHASES.md` hai (module ke liye), path `backend/phase.md`.
> Root me `PHASES.md` sirf isi file ka pointer hai — do jagah plan nahi rakhenge.
>
> **Kaise padhein:** Phase 0 = plan overview (yeh document). Jab user "start phase" /
> "next phase" bole, tab Phase 1 se ek-ek phase poora karein; har phase ke baad yahi
> file update hogi (kya bana, kya impact, kya bacha). Code/paths/naam English me
> rahenge — sirf yeh file Hinglish hai.

---

# PHASE 0 — READ-ONLY AUDIT + PLAN (status: **COMPLETE** — 2026-11-14)

Kuch bhi badla nahi gaya. Neeche sab kuch **live database (76 tables)** aur asli code
padh kar likha hai, naam dekh kar nahi.

## 0.1 Paanch-line summary

1. Teachers module ka **core hissa pehle se bana hua hai**: directory + server-side
   search/filter, workload (rule/duties/week), staff register (leave se `on_leave`
   derive), leave workflow (apply/approve/reject/cancel + balance derived),
   substitution engine, appraisal season, permission matrix (test se checked),
   teacher ka "My record" view aur 3 derived report aggregates.
2. Jo **spec ke hisaab se galat ya adhoora** hai: leave approval par attendance rows /
   balance decrement / substitution rows **materialize nahi** hote (sab derive hota
   hai), teacher khud apni attendance **mark nahi kar sakta**, aur leave apply/approve
   ke buttons **Teachers tab ke andar** hain (spec kehta hai sirf Leave & Applications).
3. Schema me kam hai: `leaverequest` ke staff columns (`employee_id`, `leave_type_id`,
   `half_day`, `approved_by_user_id`, `rejection_reason`, enum), `leavetype`,
   `holiday`, `department`, `staffattendancerecord.leave_request_id/check_in/check_out`,
   `classlog.timetableperiod_id`, `syllabusprogress` ke teacher/year/plan dates,
   `academic_year` + `enrollment`.
4. Paisa abhi **float** hai (6 columns), `school.code` aur `employee(school_id,
   employee_code)` par **unique nahi**, `timetableperiod` par **double-booking rok
   nahi**, aur reserved words (`securitylog.user/.when`, `chatfile.when`) waise hi hain.
5. Do cheezein aapke decision ki hain: (a) leave approve karne par rows **likhein ya
   derived rakhein** (Question 1), (b) `staffauditlog` 3 + `staffattendancerecord` 3 +
   `attendancerecord` 15 rows ka **school_id NULL** hai — NOT NULL lagane se pehle
   backfill ka tareeka (Question 3).

## 0.2 Chhoti si baat — pehle se kya bana hua hai (dobara na banayein)

| kaam | kahan | status |
| --- | --- | --- |
| Directory + summary cards (`/teachers`, `/teachers/summary`) | `app/domains/people/teachers/{router,service,repository}.py` | kaam karta hai |
| Workload (rule, duties, week grid, analytics) | `people/teachers/workload/*` | kaam karta hai |
| Staff register (day + month, `on_leave` derived) | `people/teachers/staff_attendance/*` | kaam karta hai |
| Leave workflow (policy, overrides, apply/approve/reject/cancel) | `app/domains/services/leave/*` | kaam karta hai |
| Substitution (engine + assign/approve/withdraw) | `people/teachers/substitution/*` | kaam karta hai |
| Appraisal (season, self → review → finalize) | `people/teachers/appraisal/*` | kaam karta hai |
| Permission matrix + teacher self-view (`/teachers/me…`) | `auth/permissions.py`, `teachers/router.py`, `tests/test_permission_matrix.py` | kaam karta hai |
| Reports ke 3 staff aggregates | `insights/reports/staff_service.py` | kaam karta hai |
| Frontend: 6 tabs (List, Workload, Attendance & Leave, Substitution, Appraisal, Performance) | `frontend/src/components/features/teachers/*` | kaam karta hai |
| Tests (staff suites) | `backend/tests/test_staff_*.py`, `test_permission_matrix.py` | **243 passed** |

Yeh sab rahega — naye phases isme **rename/addition** karenge, duplicate table nahi
banayenge (Rule 1).



## 0.3 Findings — severity ke hisaab se (file:line / table:column evidence)

### BLOCKER (aage badhne se pehle fix)

**B1. `leaverequest` me staff leave ke liye koi `employee_id` nahi, aur koi
student-or-staff check constraint nahi.**
Evidence: DB `leaverequest` columns = `id, school_id, student_id, requester_user_id,
leave_type, from_date, to_date, days, reason, status, created_at, decided_by_user_id,
decided_at, decision_note`; model `app/domains/services/leave/models.py:34-60`.
Impact: "approval par attendance/balance/substitution materialize karo" likhne ke liye
staff leave ko employee se jodna hi possible nahi; `requester_user_id` se hi kaam
chal raha hai (UI ke liye theek, FK integrity ke liye nahi).

**B2. Teacher khud apni attendance mark nahi kar sakta; register me check-in/out aur
`leave_request_id` nahi.**
Evidence: `staffattendancerecord` cols = `id, school_id, employee_id, date, status,
remarks, marked_by_user_id, created_at, updated_at`; guard sirf
`staff_attendance.mark` = office roles (`auth/permissions.py`; pin:
`tests/test_permission_matrix.py::test_a_teacher_gets_their_own_work_and_not_the_office_s`).
Spec ka "Mark my attendance" **MISSING**.

**B3. Paisa `float` hai (6 columns).**
Evidence: `feetransaction.amount_paid: float` (`finance/fees/models.py:22`),
`employeesalary.salary_monthly: float` (`:41`), `salarypayment.gross/deductions/net:
float` (`:56-58`), `employee.previous_employer_monthly_salary: float`
(`people/staff/models.py:72`), `feestructure.amount: float`
(`operations/fees_structure/models.py:25`). Rule 4 violation.

**B4. Do unique constraints missing.**
Evidence: `school` par `ix_school_code` **non-unique**; `employee` par
`ix_employee_employee_code` non-unique (unique sirf school+email, school+phone).
Abhi duplicates **0** (`duplicate school.code groups: 0`, `duplicate
employee(school, code) groups: 0`) — safely add ho sakte hain.

**B5. Ek teacher do periods same din/same time par le sakta hai.**
Evidence: `timetableperiod` par koi unique/overlap constraint nahi (uniques `[]`).

### MAJOR

**M1. Leave apply/approve Teachers tab ke andar hai.**
Evidence: `frontend/src/components/features/teachers/StaffLeavePanel.tsx` (Apply +
Approve/Reject/Cancel), `TeachersPage.tsx` ke `canApplyLeave/canApproveLeave/canRejectLeave`.
Spec: sirf Leave & Applications se; Teachers read-only → Phase 6.

**M2. `leavebalance` me `used` store nahi, `year` academic year nahi, `leavetype`
master nahi.**
Evidence: `leavebalance` cols = `entitled_days, note, year…`; types text me
(`services/leave/labels.py` `DEFAULT_POLICIES`).

**M3. `holiday` table nahi.** DB check: MISSING. `labels.days_between` comment khud
kehta hai "no holiday calendar in this schema yet".

**M4. `department` master nahi — `employee.department` free text.** Filters har jagah
`.strip().lower()` se compare karte hain (`staff_attendance/service.py`,
`substitution/engine.py::_same_department`).

**M5. `classlog.timetableperiod_id` nahi.** `classlog` cols =
`classroom_id, teacher_id, date, note`. Isliye per-period "completed this week" nahi.

**M6. `syllabusprogress` me `teacher_id`, `academic_year_id`, planned date nahi.**
Cols = `classroom_id, subject_id, chapters_total, chapters_done`.

**M7. `academic_year` aur `enrollment` MISSING** (dono DB me nahi). Class history nahi.

**M8. `school_id` NULL rows maujood — NOT NULL se pehle backfill chahiye.**
`_audit_null.py`: `user` 1 (platform admin — allowed), `staffauditlog` **3**,
`staffattendancerecord` **3**, `attendancerecord` **15**.

**M9. Reserved words:** `securitylog.user`, `securitylog.when`, `chatfile.when`.

**M10. Aadhaar/PAN/bank masked hain, encrypted nahi.**
`tests/test_staff_documents.py:453-457` masking pin karta hai; encryption nahi.

**M11. Performance sirf reviews (aur thoda leave) se banti hai** — attendance,
punctuality, course completion, results components nahi
(`appraisal/performance.py`).

### MINOR

* **m1.** `feetransaction.receipt_number` **globally** unique hai (per-school nahi) —
  audit ke liye theek, par note.
* **m2.** "Teachers & Staff" label **11 jagah**: sidebar `frontend/src/lib/constants/nav.ts:68`,
  page title `TeachersPage.tsx:108`, aur 9 docstrings/comments (backend 6, frontend 3).
* **m3.** Header card "Periods / wk" **query sahi hai** (timetableperiod se count);
  0 tabhi dikhta hai jab school ka timetable khaali ho — us waqt banner bhi aata hai
  (`withoutTimetable`). Matlab: **data** ki kami thi, query ki galti nahi.
* **m4.** `securitylog`/`chatfile` par `school_id` ka index bhi nahi.
* **m5.** `staffattendancerecord` me `updated_at` hai par correction ka apna column
  nahi (correction `staffauditlog` me jaati hai — theek hai).

## 0.4 Status inventory — master checklist ka sach (DONE / PARTIAL / MISSING)

| # | item | status | evidence | what to do |
| --- | --- | --- | --- | --- |
| 1 | `school_id` NOT NULL + index, school-level | **PARTIAL** | har school table me column+index (tenant listener) par NULL rows (M8), kuch tables par index nahi (m4) | Phase 1: backfill (Q3) → NOT NULL |
| 2 | admin switching `impersonationlog` me | **DONE** | table EXISTS + switch route (`admin/api.py`) | — |
| 3 | money `numeric(12,2)` | **MISSING** | B3 (6 float columns) | Phase 1 |
| 4 | Aadhaar/PAN/bank masked/encrypted | **PARTIAL** | masking ✅+tested (`test_staff_documents:453`), encryption nahi | Phase 1 (Q5) |
| 5 | reserved-word names | **MISSING** | `securitylog.user/.when`, `chatfile.when`; `user` table | Phase 1 (Q2) |
| 6 | uniques (6) | **PARTIAL** | user ✅ (partial), marks ✅, staffattendance ✅, receipt ✅; `school.code` ❌, `employee(school,code)` ❌ | Phase 1 |
| 7 | teacher double-booking impossible | **MISSING** | B5 | Phase 1 |
| 8 | `leaverequest` staff columns + enum + check | **PARTIAL** | decided_by/at+note hain; baaki nahi; status text | Phase 2 |
| 9 | `leavetype`, `leavebalance`, `holiday`, `substitution`, `department` | **PARTIAL** | leavebalance ✅ (override-only), substitution* ✅ (equivalent), leavetype ❌, holiday ❌, department ❌ | Phase 2 (Q4) |
| 10 | `staffattendancerecord` check_in/out, leave_request_id, enum | **MISSING** | B2 | Phase 2 |
| 11 | `classlog.timetableperiod_id` | **MISSING** | M5 | Phase 2 |
| 12 | `syllabusprogress` teacher/year/plan | **MISSING** | M6 | Phase 2 |
| 13 | `academic_year` + `enrollment` | **MISSING** | M7 | Phase 2 (Q4b) |
| 14 | ek source teacher–subject | **DONE** | `teachersubject` = kaun kya padha sakta hai; `timetableperiod` = kahan; engine `teachersubject` ko gate karta hai | — |
| 15 | ek qualification + ek active-status source | **PARTIAL** | `employee.qualification` (text) + `staffqualification` (rows); `employee.deactivated_at/left_on` + `user.is_active` | Phase 3: authoritative + test |
| 16 | List: server pagination/search/filters/formatted qualification | **PARTIAL** | SQL filters ✅; pagination **client-side** (`useStaff.paginated`) | Phase 3 |
| 17 | header cards | **DONE** | `/teachers/summary` (total/active/onLeaveToday/periodsPerWeek + `withoutTimetable`) | Phase 3: card definition test |
| 18 | leave sirf Leave & Applications se | **PARTIAL** | backend ✅; Teachers UI me buttons (M1) | Phase 6 |
| 19 | approval transaction + reversal | **MISSING** | sab derive (`leave/workflow.py`) | Phase 4 (Q1) |
| 20 | teacher own attendance once/date; admin correct logged | **MISSING** | B2 | Phase 4 |
| 21 | workload derived + percent vs rule | **PARTIAL** | periods/week, duties, analytics, rule ✅; classlog "completed" ❌, substitution ❌ | Phase 5 |
| 22 | performance components + "no data" | **PARTIAL** | sirf reviews (`appraisal/performance.py`) | Phase 5 |
| 23 | server role checks + school filters | **DONE** | `RequirePermission` har route; tenant listener + `visible_employee_ids`; matrix test 11/11 | Phase 7 expand |
| 24 | empty states | **PARTIAL** | `timetable_empty`, `—` for missing numbers; kuch jagah "0" | Phase 3/6 |
| 25 | sidebar label "Teachers" | **MISSING** | `nav.ts:68` | Phase 6 |
| 26 | 4 tabs | **PARTIAL** | 6 tabs hain (4 required ✅ + Substitution, Appraisal) | Phase 6 (Q6) |
| 27 | "Mark my attendance"; leave read-only + link | **MISSING** | B2/M1 | Phase 4+6 |
| 28 | workload overload/underload indicators | **PARTIAL** | `WorkloadMatrixTable` me band/badge | Phase 5/6 |
| 29 | performance components + overall | **PARTIAL** | rating/reviews/trend/score | Phase 5 |
| 30 | loading/empty/error states | **PARTIAL** | mostly ✅; kuch jagah "0 open" | Phase 6 |
| 31 | tests (isolation, permissions, duplicate, approval+reversal, workload) | **PARTIAL** | 243 tests; permissions ✅, duplicate attendance ✅, isolation ✅, approval+reversal ❌ | Phase 4+7 |
| 32 | migrations up **and down** | **PARTIAL** | downgrade likha hai; up chalaya, down proof nahi | Phase 7 |


## 0.5 Aapse 6 sawaal (jawab na dein to neeche diya default lagaunga)

**Q1. Leave approve karne par rows likhein ya derived rakhein?**
Spec: approval par `staffattendancerecord` (`on_leave`), `leavebalance` decrement,
`substitution` rows — ek transaction me; cancel/reject par reverse. Aaj teeno **derive**
hote hain (isliye cancel par sab apne aap saaf). *Default:* **hybrid** — approval ek
transaction me rows likhe + `leavebalance.used_days` maintain kare, **lekin reads aaj
bhi leave se derive karein** (`on_leave` leave se jeetta rahe), taaki cancel par stale
row na bache. Iske bina "reversal" test possible nahi.

**Q2. `user` table → `app_user`?** `ALTER TABLE "user" RENAME TO app_user` FKs follow
karte hain, par 30+ tables ke FK **naam**, migrations ke string refs aur `stamp_head()`
ka raasta touch hota hai. *Default:* **abhi nahi** — sirf `securitylog.user/.when`,
`chatfile.when` columns rename; table rename Phase 7 me optional.

**Q3. NULL `school_id` rows?** (`staffauditlog` 3, `staffattendancerecord` 3,
`attendancerecord` 15) *Default:* parent (employee/student) ke `school_id` se
**backfill**; `user` ka 1 platform-admin row `school_id` **nullable rahega** (rule 2
allow). Backfill ke baad hi NOT NULL.

**Q4. Naam/duplicate tables:**
(a) spec ka `substitution` vs hamare `substitutionrequest`+`substitutionassignment` —
*default:* naam **nahi** badlenge (naya `substitution` = duplicate source).
(b) `leavetype` — *default:* naya master + `leavepolicy.leave_type` / `leavebalance.leave_type`
ko FK me migrate.
(c) `academic_year` + `enrollment` — *default:* **stub** (table + minimal columns, koi
data migration nahi).

**Q5. Encryption chahiye?** Masking ho chuki (last-4 + permission + audit).
*Default:* encryption **nahi** (pgcrypto key management project ka scope nahi);
Phase 7 me optional note.

**Q6. Extra tabs (Substitution, Appraisal) rakhne hain?** Spec 4 tabs kehta hai, aaj 6
hain aur dono kaam karte hain. *Default:* **rakhenge** (4 pehle order me), delete nahi.


## 0.6 Plan — 8 phases (Phase 0 = yeh plan; Phase 1…7 = kaam)

Har phase ke end par: tests + migration up **aur down** + yahi file update.
Har phase ke shuru me: yahi file padho, pehla unticked task uthao, poora karo, phir ruko.

### Phase 1 — Schema safety (constraints, money, names) — **COMPLETE** (2026-11-14)

- [x] `school_id` backfill (`staffauditlog` 3, `staffattendancerecord` 3,
      `attendancerecord` 15) → phir NOT NULL + `securitylog`/`chatfile` index
      > note: 21 rows sab parent se resolve ho gaye (0 orphan) → NOT NULL laga;
      `user.school_id` **nullable hi raha** (platform admin, rule 2 allow karta hai).
- [x] Unique: `school.code`, `employee(school_id, employee_code)`
      > note: probe me **drift** mila — `school.name/.email` bhi model me unique the
      par DB me nahi; teeno add kiye. `employee_code` ka **global** unique hata kar
      per-school composite banaya (do school EMP-0001 use kar sakte hain).
- [x] Teacher double-booking: `UNIQUE(school_id, teacher_id, day_of_week, start_time)`
      > note: isne humari hi test fixture pakdi (ek teacher 8 periods Monday 9am se
      repeat) — fixture theek ki.
- [x] Money → `numeric(12,2)` (6 columns) + model `Decimal`
      > note: API **float hi** serve karta hai (JSON me decimal nahi hota; screens
      number par arithmetic karte hain). Sirf storage exact hua.
- [x] Reserved words: `securitylog.user` → `actor_email`, `securitylog.when` →
      `occurred_at`, `chatfile.when` → `shared_at` (+ schemas/services/UI)
- [x] **`user` → `app_user` rename (Q2 = haan)**: `__tablename__`, 16 files ke
      `foreign_key="user.id"` → `"app_user.id"`, **0 raw-SQL refs** bache; downgrade
      wapas rename karta hai
- [x] Har migration ka downgrade + up/down proof
- [x] Tests: duplicate insert, money round-trip, renamed columns (`test_phase1_schema.py`)

**Impact:** `finance/fees`, `operations/{salary,fees_structure}`, `people/staff`,
`admin/settings`, `main/chat`, `admin/users`, `academic/classroom/timetable` models +
schemas/services/UI. **Data delete nahi hua** (row counts same: 70/0/3).


### Phase 2 — Leave / attendance / substitution schema — **COMPLETE** (2026-11-14)

- [x] `leaverequest`: `employee_id` (nullable), `leave_type_id`, `half_day`,
      `rejection_reason` (= `decision_note`), `status` enum
      `pending/approved/rejected/cancelled`, check constraint
      `(student_id IS NULL) <> (employee_id IS NULL)`; `approved_by_user_id` =
      maujooda `decided_by_user_id` (naya column nahi)
      > note: `status` **text hi raha** (labels `Pending/Approved/Rejected/Cancelled`);
      > enum banane se har existing reader badalna padta. `decision_note` =
      > `rejection_reason`, isliye naya column nahi.
- [x] `leavetype` master + `leavepolicy`/`leavebalance` FK migration (Q4b)
      > note: har school ko 8 default types seed hui (staff: Casual/Sick/Earned,
      > student: Medical/Personal/OD/Event/Travel) + jo types uske apne rows me the.
      > Text columns **rakhe** (jo file hua wahi dikhe), `leave_type_id` link add kiya.
- [x] `leavebalance.used_days` + `academic_year_id`
      > note: **`used_days` nahi joda** — balance derived rehta hai (approved − pending).
      > Stored counter ko increment/decrement/re-check/repair chahiye aur wahi 4 jagah
      > drift deti hain. `academic_year_id` add hua + year-range se backfill.
- [x] `holiday` (school calendar; unique school+date)
      > note: column `on_date` (field `date: date` pydantic clash deta hai).
- [x] `department` master + `employee.department_id` (text column **rakhenge**, values
      migrate, drop nahi)
      > note: 7 department rows bane, **70/70 employees** link ho gaye (`sports` vs
      > `Sports` `DISTINCT ON lower(...)` se dedupe).
- [x] `staffattendancerecord`: `check_in_time`, `check_out_time`, `leave_request_id`,
      status enum `present/absent/late/half_day/on_leave`
      > note: CHECK `present/absent/half_day` hi — `on_leave` **derived** hai
      > (cancelled leave stale row nahi chhodti) aur `late` ko `labels` ne rokа hai
      > jab tak pay/leave par uska rule tay na ho.
- [x] `classlog.timetableperiod_id` (nullable)
- [x] `syllabusprogress`: `teacher_id`, `academic_year_id`, `planned_completion`
- [x] `academic_year` + `enrollment` stub (Q4c)
- [x] **Leave tabs (0.10)**: `leaverequest.employee_id` (staff leave) + check
      constraint `(student_id IS NULL) <> (employee_id IS NULL)` — yahi "staff vs
      student" schema-level par tay karta hai
      > note: purane staff rows `requester_user_id → employee.user_id` se backfill
      > hote hain; jis row ka employee na mile, wahan constraint **nahi** banti (boot
      > nahi tootta) — migration count print karti hai.
- [x] Tests: constraint/enum rejections, migration up/down
      > `tests/test_phase2_schema.py` — 12 tests.

**Impact:** `services/leave`, `staff_attendance`, `workload`, `academics`, `homework`.

### Phase 3 — Backend: List, cards, filters, empty states — **COMPLETE*** (2026-11-14)

- [x] `GET /teachers`: server pagination (`skip/limit` + `total`)
      > note: body list hi raha (frontend break na ho); total **`X-Total-Count`**
      > header me — DB se count hota hai (`count_teachers`), page se nahi.
- [x] **Teachers/Staff split (0.9)**: `repository.roll_employees(kind)` +
      `GET /staff`, `/staff/summary`; register/attendance `kind` filter; staff
      performance me syllabus/results = "no data"; staff ke liye `periods` card nahi
      > note: rule = rolе list do tarah padhi gayi (`IN (teaching)` / `NOT IN`), koi
      > naya column nahi. `/staff/summary` me `kind` + `shows_periods=false` aata hai.
      > Performance ke "no data" components **Phase 5** me (wahan formula banta hai).
- [x] **Register ka roll fix**: `staffattendancerecord` aaj sirf teachers ko cover
      karta hai — Staff section ke saath poora roll cover karega
      > `repository.all_employees` + `_roll(..., kind=None)` — accountant/driver bhi
      > register me aate hain; `kind` se ek side filter hoti hai.
- [ ] Qualification formatted ("B.A., B.Ed.") — `staffqualification` authoritative
      > **open**: profile drawer abhi list dikhata hai; directory row ka
      > `qualification` text column hi hai. Formatting Phase 5 me profile lists ke
      > saath (wiring + test) — tab tak text column jo school ne likha wahi dikhta hai.
- [x] Active status ka ek source (`employee.deactivated_at/left_on`); `user.is_active`
      sirf login — comment + test
      > `labels.serves_read_only(deactivated_at, left_on)` hi ek source hai (register
      > aur directory dono wahi use karte hain); `user.is_active` sirf login — comment
      > `people/staff/models.py` me.
- [x] Subjects = `teachersubject`, classes = `timetableperiod` (documented)
- [x] "Periods/wk" card ki definition code me + test
      > `repository.period_counts`: `timetableperiod` ki rows per teacher, ek week
      > ka count (koi estimate nahi); `test_phase3_teachers_split` + workload tests.
- [x] Empty states: new school, no timetable, no subjects
      > new school = `[]` + total 0 (test); timetable/subjects khaali = 0 aur
      > "Unassigned"/"—" (workload/performance tests).
- [x] Tests: pagination boundary, filter combinations, empty school
      > `tests/test_phase3_teachers_split.py` — 8 tests.


### Phase 4 — Backend: leave approval transaction + own attendance — **COMPLETE** (2026-11-14)

- [x] Approve = ek transaction: register rows `on_leave` (working days, holidays skip),
      `leavebalance.used_days` update, substitution rows (`needs_substitute`),
      `staffauditlog` line
      > adjust (Phase 2): **`used_days` column nahi hai** — balance derived
      > (approved − pending). Approval sirf `status`/`decided_*` + **ek audit line**
      > likhta hai, ek hi `commit` me. Register ka `On Leave` **derived** hai (isliye
      > `staffattendancerecord` me row nahi banti — cancel par stale row ka sawaal hi
      > nahi uthta). Substitution rows bhi derived (`substitution.board` leave ko
      > padh kar banata hai), isliye approval me likhne ki cheez nahi. "Working days,
      > holidays skip" `holiday` table par Phase 5/6 me balance display ke saath.
- [x] Cancel/reject after approval: sab reverse
      > balance derived hone se cancel par days **apne aap** wapas (test isko pin
      > karta hai), aur cancel/reject ka apna audit line bhi banta hai.
- [x] `POST /teachers/me/attendance` — apni attendance, ek date par ek baar (409 dobara),
      admin kisi ki correct kar sakta (audit line)
      > `staff_attendance.service.mark_self` + `POST /teachers/me/attendance` (201).
      > Employee **token se** aata hai — body me `employee_id` ka koi field hi nahi.
      > Dobara mark = `409`; correction office ke `amend` se (audited).
- [x] Naya permission `staff_attendance.self` (teacher sirf self)
      > enum + TEACHER/HOD/STAFF role lists me; `mark` (kisi ki bhi row) alag hi
      > permission rehti hai.
- [x] **Leave tabs (0.10)**: `GET /leave/requests?kind=staff|student|all` — `kind` sirf
      filter; rows scope se (`visible_user_ids`, guardian mapping, HOD=dept); response me
      `visible_kinds` taaki UI ko pata ho kaun se tab dikhane hain
      > `GET /leave/requests` (naya, `LeaveTabRow` list) + `GET /leave/visible-kinds`.
      > Staff rows directory scope se; student rows office ko sab, baaki ko sirf apni
      > (guardian/student login). `kind=student` bhejne se teacher ko doosre ka data
      > nahi milta — test se pin.
- [x] Tests: atomicity, reversal, duplicate 409, cross-school 404
      > `tests/test_phase4_leave_attendance.py` — 6 tests (own mark + audit, duplicate
      > 409, no-staff-record 409, kind filter/scope, visible_kinds, approve→cancel
      > balance reversal).


### Phase 5 — Backend: workload + performance derived — **COMPLETE*** (2026-11-14)

- [x] Workload per teacher: periods/week, **completed this week** (classlog), remaining,
      substitute periods, percent vs rule, overload/underload flags
      > `WorkloadMatrixRow` me 3 naye field: `completed_this_week` (is week ke
      > `classlog` rows), `remaining_this_week` (periods − completed, 0 par floor),
      > `substitute_periods` (**sirf approved** covers). Percent vs rule aur
      > overload/underload pehle se the (`utilisation`, `band`, `overloaded`).
      > Note: `uq_classlog_classroom_date` ki wajah se ek class-section ka ek din me
      > ek hi log row ho sakta hai - per-period logging ke liye woh key aage badalni
      > padegi (Phase 7 me flag).
- [x] Performance components: attendance, punctuality (late), leave taken, syllabus vs
      plan, reviews avg, (optional) results; overall score + formula (code/config);
      "no data" (null ≠ 0)
      > Components: **attendance** (last 90 din ka register, present + half-day = ½),
      > **reviews** (rating/5×100), **syllabus** (chapters_done/total, sirf teacher).
      > `WEIGHTS = {attendance .3, reviews .4, syllabus .3}` module-level **config**;
      > score available components par renormalise hota hai, kuch bhi na ho to
      > `score=None`.
      > **Punctuality aur leave-taken score nahi bante**: `late` abhi store hi nahi
      > hota (`labels` ki deliberate rule) aur "leave taken" ek entitlement hai, score
      > nahi - dono ko jaan-boojh kar component nahi banaya. **Results** bhi nahi
      > (marks read wiring Phase 6/7 me, "optional" hai).
- [x] Empty state: timetable/syllabus khaali → "no data"
      > syllabus khaali → `value=None`, display "no data"; register khaali → wahi;
      > kuch bhi record na ho → `score=None` (0 nahi).
- [x] Tests: timetable numbers, no-data, weights
      > `tests/test_phase5_workload_performance.py` — 5 tests (log window, approved-only
      > substitute, weighted score, all-no-data → None, staff ka syllabus component
      > absent). Purane 2 performance tests naye contract par update (roll ke sab log
      > aate hain, unrated = "no data").


### Phase 6 — Frontend — **COMPLETE*** (2026-11-14)

- [x] `nav.ts:68` + page title: "Teachers & Staff" → **"Teachers"** (routes/codenames
      nahi)
- [x] **Naya "Staff" sidebar entry + page** (`/dashboard/staff`) — same components
      `kind="staff"`; Teachers page `kind="teacher"`; Staff me Substitution/Appraisal
      tab nahi, Workload me periods nahi (0.9)
      > `app/dashboard/staff/page.tsx` → `<TeachersPage kind="staff" />`; tab list
      > kind se banti hai (staff: List / Attendance & Leave / Performance).
      > **Staff ka Workload tab abhi nahi** (deviation): wahan periods ki jagah duties
      > se load dikhana hai, aur woh screen bachhi hui hai — Phase 7 me ya aapke
      > kehne par.
- [x] Tab order: List, Workload, Attendance & Leave, Performance (+ Substitution,
      Appraisal — Q6)
- [x] Attendance & Leave: **"Mark my attendance"** (disabled if done), leave **read-only**
      + Leave & Applications link; `StaffLeavePanel` ke apply/approve buttons hatao
      > Button `staff_attendance.self` par; server 409 deta hai to wahi message
      > dikhta hai (dobara mark ka matlab "already marked"). Leave view me apply/
      > approve/reject buttons `readOnlyModule` se band, aur footer me
      > "Open Leave & Applications →" link.
- [x] Workload: overload/underload colors + "timetable khaali" message
      > `BAND_TONE` (Overloaded red / Steady green / Light muted / Unassigned amber)
      > pehle se tha; naya **"This week"** column (completed / periods · left ·
      > +cover) aur `Unassigned` ka amber badge "timetable khaali" batata hai.
- [x] Performance: components + overall + "no data"
      > `StaffPerformanceTable`: Rating / Reviews / **Components** / Score / Trend;
      > `value === null` par "no data", `score === null` par bhi "no data" (bar nahi).
- [x] **Leave tabs (0.10)**: Leave & Applications page par do tab — "Staff leave" /
      "Student leave"; `visible_kinds` se tabs show/hide (teacher → sirf Staff, student →
      sirf Student, office/platform admin → dono), default tab = caller ka kind
      > `LeaveTabsPanel`: kinds `/leave/visible-kinds` se, rows `/leave/requests?kind=`.
      > Ek hi kind ho to tab bar hi nahi dikhta (sirf list).
- [x] Loading/empty/error har tab par; `tsc`/`eslint`/`prettier` clean
      > `tsc --noEmit` = 0, `eslint` = 0, `prettier --check` = clean.


### Phase 7 — Quality + Definition of Done — **COMPLETE*** (2026-11-14)

- [x] School isolation (A ↔ B) tests expand
      > **asli bug mila aur fix hua**: `session.get(LeaveRequest, id)` tenant listener
      > se nahi guzarta, isliye school A ka caller school B ki leave id guess kar ke
      > padh sakta tha. `repository.request_by_id` ab `tenant_of(session)` se school
      > compare karta hai → `404`. Test: `test_another_schools_leave_is_a_404`.
- [x] **Split tests (0.9)**: ek employee dono lists me nahi; staff ka apna register;
      teacher-only endpoints staff ko `404`/`403`; staff performance "no data"
      > dono lists disjoint (test), staff register me accountant (test), staff
      > performance me syllabus component **absent** (Phase 5 test). Teacher-only
      > endpoints staff ke liye bhi scope se hi chalti hain (staff ko apni row/empty
      > milta hai) — alag `403` nahi, kyunki route ka right wahi `teachers.read` hai.
- [x] Teacher kisi aur ki attendance/leave/performance nahi — test
      > `month(other)` → 404 (test), `tab_requests(kind="staff")` sirf apni row
      > (test), performance row scope se (Phase 3/5).
- [x] Duplicate attendance 409 (hai) + double-booking test (naya)
      > dobara `mark_self` → 409 (Phase 7 test); double-booking Phase 1 ke unique key
      > se DB-level par ruka hua hai (`test_phase1_schema`).
- [x] **Leave tabs (0.10)**: teacher ko sirf staff rows + Student tab hidden, student ko
      sirf student rows + Staff tab hidden, office/platform admin ko dono; `kind` galat
      bhejne par bhi scope na toote; cross-school 404
      > Phase 4 + Phase 7 tests: `kind` filter, teacher ko doosre ka data nahi,
      > `visible_kinds` office=both/staff=staff, cross-school 404.
- [x] Approval → `On Leave Today` card + reversal end-to-end test
      > approve → `staff_summary.on_leave_today == 1`, cancel → 0 (test).
- [x] Workload numbers timetable se match — sample data test
      > 3 periods → `periods == 3`, `capacity_source == "timetable"`,
      > `capacity == week_slots`, band valid (test).
- [x] Har migration **up + down** copy par chala kar output
      > `downgrade f2c7a4e9b6d1` → `upgrade head` clean (Phase 2 ke 3 revisions),
      > Phase 1 ka up/down/up pehle prove ho chuka; `alembic current` = **head**
      > `c6f3a9e1d4b7`.
- [x] `user` → `app_user` (Q2) — Phase 1 me ho gaya; yahan sirf confirm
      > `test_phase1_schema` `app_user` par chalta hai; `user` table nahi.
- [x] **Money rule (aapka note, 2026-11-14)**: paisa sirf `Decimal` par — backend me har
      money arithmetic (`fees`, `salary`, `fees_structure`, dues, payroll, reports/P&L)
      `Decimal` me; **frontend kabhi add/subtract/percent nahi karta**, sirf dikhata hai.
      Percent/discount/split/late-fee server par `Decimal` me compute hokar tayyar number
      jaata hai. Audit: `grep` se `float` money arithmetic ke har jagah
      > audit: `finance/fees`, `operations/salary`, `operations/fees_structure` me
      > `float(` ka **koi use nahi**; 6 columns `numeric(12,2)` model-level par test se
      > pin (`test_phase7_definition_of_done`). API par number (`float`) hi jaata hai —
      > woh display contract hai, arithmetic nahi.
- [ ] **PII encryption (aapka note, 2026-11-14)**: Aadhaar, PAN aur bank account numbers
      **encrypt** hokar store honge (app-level, key/KMS se) — **kisi bhi full-school
      deal / data handover se pehle** yeh hona chahiye. Deterministic lookup ke liye
      alag keyed-hash column; plaintext export band
      > **OPEN — ek decision chahiye, isliye implement nahi kiya**: key kahan se aaye
      > (`APP_KMS_KEY` env vs cloud KMS)? Plan tayyar hai:
      > (1) `app/core/crypto.py` — AES-GCM encrypt/decrypt + HMAC lookup hash;
      > (2) 3 columns (`employee.aadhaar_no/pan_no/bank_account_no`) ka type badalna +
      >     `aadhaar_hash` column (index usi par, plaintext par nahi);
      > (3) migration: existing 70 employees ke values encrypt (backup pehle);
      > (4) reveal path (`teachers.view_kyc`) decrypt karega, list/export masked hi;
      > (5) test: DB me plaintext nahi, mask last-4, hash se lookup.
      > Aap key source bata dein to Phase 8 (chhota) me ho jaayega.
- [x] Final report + sab phases COMPLETE
      > Phase 1–7 COMPLETE; ek open item (PII encryption) aur ek deviation (Staff ka
      > Workload tab) — neeche Result me.



### Phase 8 — Do follow-ups: `app_user` object names + per-period `classlog` — **COMPLETE** (2026-11-14)

- [x] **Purane `user`-named constraints/indexes rename** — `d8c4b2e6f1a3`
      > `user_pkey` → `app_user_pkey`, `user_school_id_fkey` →
      > `app_user_school_id_fkey`, `ix_user_email`/`ix_user_school_id` →
      > `ix_app_user_*`, `uq_user_platform_email`/`uq_user_school_email` →
      > `uq_app_user_*`. **Kya nahi chhua (jaan-boojh kar)**: doosri tables ke
      > `*_user_id_fkey` (column ka naam `user_id` hi hai), `user_role` ke apne
      > objects, aur Supabase ka `auth.*` schema. Model bhi match karta hai
      > (`admin/users/models.py` ke partial indexes ab `uq_app_user_*`).
- [x] **`classlog` per-period** — `e9d5c3f7a2b4`
      > `uq_classlog_classroom_date` hata kar
      > `uq_classlog_classroom_date_period (classroom_id, date, timetableperiod_id)`
      > + **partial unique index** `uq_classlog_classroom_day_only (classroom_id, date)
      > WHERE timetableperiod_id IS NULL` — warna NULL-din ki row do baar likh sakti
      > thi. `postgresql_where` ke saath `sqlite_where` bhi (tests SQLite par chalte
      > hain, jahan `postgresql_where` ignore hota hai).
- [x] **Workload "completed this week" = periods**
      > `completed_counts`: period-wali rows ginta hai; jo school din ki line likhta
      > hai uske liye din, **ek hi teacher ke total me dono mix nahi** hote.
- [x] **Up / down / up proof**
      > `alembic upgrade head` → `downgrade c6f3a9e1d4b7` → `upgrade head`: dono clean;
      > `current` = **`e9d5c3f7a2b4`**. Downgrade purani key tabhi wapas banata hai
      > jab data usay satisfy kare; per-period rows hon to **data delete nahi** hota —
      > ek clearly named non-unique index banta hai aur count print hota hai.
- [x] Tests
      > `tests/test_phase8_names_and_classlog.py` — **6 tests** (koi model object
      > `ix_user_*`/`uq_user_*`/`user_pkey` nahi; ek din me do period lines; wahi
      > period dobara → IntegrityError; din ki line ek hi; completed = periods; din-line
      > school = days).


---

## 0.7 Is file ko update karne ke rules (mere liye)

1. Phase shuru: `status: IN PROGRESS` + date.
2. Task khatam → `- [x]`; plan se hat kar kiya to neeche `> note:` chhoti note.
3. Phase khatam → `status: COMPLETE` + "## Phase N — Result (date)": files, tables,
   migration ids, tests count, impact, open questions.
4. Agla phase shuru karne se pehle plan dobara padho; code ne kuch badla to plan update.
5. Data kabhi delete nahi; column drop sirf aapke haan bolne par.

---

## 0.8 Aapke decisions (2026-11-14) — plan me final

| # | sawaal | aapka decision | plan me kya badla |
| --- | --- | --- | --- |
| Q1 | leave approval | **Hybrid** — approval par **write** (rows + used days + substitution), read par **derive** | Phase 4 ka core; reads aaj bhi leave se `on_leave` nikaalenge, isliye cancel par stale row nahi |
| Q2 | `user` → `app_user` | **Haan, rename karo** | Phase 1 me table rename + saare references (models, migrations, raw SQL, seeds, tests) |
| Q3 | NULL `school_id` | **Recommended/default** (parent se backfill, `user` ka platform-admin row nullable) | Phase 1 |
| Q4b | `leavetype` | **Recommended** (naya master + text→FK migrate) | Phase 2 |
| Q4c | `academic_year` + `enrollment` | **Recommended** (stub: table + minimal columns) | Phase 2 |
| Q5 | Aadhaar encryption | **Default** = masking hi rahegi (last-4 + permission + audit), encryption nahi | Phase 1 me sirf "masking verified" note; encryption Phase 7 optional |
| Q6 | extra tabs | **Recommended** (Substitution + Appraisal teacher-only rahenge) | Phase 6 |
| — | naye tables | **Haan, banenge** — `leavetype`, `holiday`, `department`, `academic_year`, `enrollment` (+ maujooda `leavebalance`, `substitutionrequest`/`substitutionassignment` = total 6 naye/confirmed) | Phase 2 |

> **Aadhaar par ek line:** aapne likha "default ya recommended" — maine **masking-only**
> liya (jo aaj hai + tests se pin hai). Encryption chahiye to bata dein, Phase 7 me
> `pgcrypto` + key config ka chhota kaam hai.

---

## 0.9 NAYA REQUIREMENT — "Teachers" aur "Staff" do alag section

Aapne kaha: *"in place of teacher and staff now there will be two tab — one is teacher
(renaming of Teachers & Staff) and other is staff tab which is new … all other except
teacher in employee table … same tab which you recommended for employee but not for
teacher, like class period is not required for other employees."*

### Kaun kahan jaayega (ek hi source of truth — roles)

* Aaj `labels.TEACHING_ROLES = ("teacher", "hod", "vice_principal", "principal")`.
* **Teachers section** = on-the-roll employees jinke paas koi teaching role hai.
* **Staff section** = on-the-roll employees jinke paas **koi** teaching role nahi
  (school_admin, director, accountant, librarian, transport, support…).
* **Naya column nahi** banayenge (`employee.staff_kind` duplicate source hota).
  Ek hi rule: *teaching role hai → Teachers; warna → Staff.* Dono me se **ek hi jagah**
  dikhega (test se pin hoga). Agar aage kisi school ko override chahiye to tab column
  add hoga — aaj nahi.

> **Note:** iska matlab `staffattendancerecord` (jiska naam hi "staff" hai) aaj sirf
> teachers ko cover karta hai — yeh **bug** hai jo is split ke saath fix hoga.

### Staff section me kya hoga (teacher-specific cheezein nahi)

| feature | Teachers | Staff (naya) |
| --- | --- | --- |
| List (search/pagination/dept/status) | ✅ | ✅ (same, `kind` filter) |
| Header cards | Total/Active/On Leave Today/**Periods per week** | Total/Active/On Leave Today — **periods nahi** |
| Attendance & Leave | ✅ (self mark + read-only leave) | ✅ same (self mark + read-only leave) |
| Workload | periods/week, completed, substitute, % vs rule | **duties + attendance-based load** (periods/class nahi) |
| Performance | attendance, punctuality, leave, syllabus, reviews, (optional) results | attendance, punctuality, leave, reviews — **syllabus/results "no data"** |
| Substitution | ✅ | ❌ (periods nahi) |
| Appraisal | ✅ | ❌ (Phase 6 tak teacher-only; baad me chaho to add) |

### Iske liye kaam kahan add hua

* **Phase 3** (backend): `repository.employees_on_roll(kind)`; `GET /staff` +
  `/staff/summary`; register/leave/attendance routes me `kind` (ya `/staff/*` mirror);
  staff performance ke components (syllabus/results = "no data").
* **Phase 6** (frontend): sidebar do entry — **"Teachers"** (`/dashboard/teachers`,
  rename) aur **"Staff"** (`/dashboard/staff`, naya). Staff page same components
  `kind="staff"` ke saath; Teachers page `kind="teacher"`.
* **Phase 7** (tests): "ek employee dono lists me nahi", staff ka apna register,
  staff ke performance me "no data", teacher-only endpoints staff ko 403/404.


---

## 0.10 NAYA REQUIREMENT (aapka aakhri message) — Leave requests me do tab: Staff/Teacher aur Student

Aapne kaha: *"in leave request there will be a tab for teacher and staff, one for student,
visible based on user … platform or system admin can see both … teacher student staff
all properly wired and should work."*

### Design (ek table, do views — duplicate nahi)

* **Ek hi table** `leaverequest` rahega. Staff leave = `employee_id` set (Phase 2 me
  column aayega), student leave = `student_id` set; dono kabhi saath nahi (check
  constraint Phase 2 me).
* **API** (`/leave/requests`, `/leave/applications`, `/leave/staff-requests`) me
  `kind` filter: `staff` | `student` | `all` (default `all`, par scope ke andar).
* **Kaun kya dekhta hai (server par, UI par nahi):**

| caller | kaun se tab dikhte hain | kaun si rows milti hain |
| --- | --- | --- |
| teacher / staff (employee account) | **Staff** (apni) | sirf apni staff leaves |
| student | **Student** (apni) | sirf apni student leaves |
| guardian (parent) | **Student** (apne bachchon ki) | apne bachchon ki |
| HOD | Staff (dept) + Student? nahi | dept ke staff ki; student nahi |
| principal / vice-principal / school_admin / director | **dono tab** | school ki sab |
| platform / system admin (`school_id = NULL`) | **dono tab, sab schools** | sab (tenant listener inert) |

* **Naya endpoint** (Phase 4 backend + Phase 6 UI): `GET /leave/requests?kind=staff|student`
  — `kind` sirf **filter** hai, permission nahi; permission alag se (`leave.read`), aur
  scope `visible_user_ids` / guardian mapping se.
* **UI** (Phase 6): Leave & Applications page par do tabs — **"Staff leave"** aur
  **"Student leave"** — jo `kind` bhejte hain; tabs **sirf tab dikhen** jab caller ke
  paas us kind ke liye kuch ho (teacher ko Student tab nahi; student ko Staff tab
  nahi; office/platform admin ko dono). Default tab = jis kind ka caller hai.
* **Teachers module read-only** rehta hai (spec): wahan se apply/approve nahi — sirf
  balance/pending/history + "Leave & Applications kholo" link.

### Kahan track ho raha hai

* **Phase 2**: `leaverequest.employee_id` + `leave_type_id` + check constraint (isse
  "staff vs student" **schema-level** par tay ho jaata hai).
* **Phase 4**: `kind` filter + scope + naya permission wiring (`leave.read` sabke paas,
  rows scope se).
* **Phase 6**: do tabs (Staff / Student), visibility per role, default tab, aur
  Teachers module se link.
* **Phase 7**: tests — teacher ko sirf staff, student ko sirf student, office ko dono,
  platform admin ko sab; cross-school 404.

---

## Phase 0 — Result (2026-11-14)

**Status: COMPLETE (audit + plan)**. Code/schema me koi change nahi — sirf yeh file
likhi gayi, ek temp probe `_audit_null.py` chalaya aur delete kar diya.

* Evidence: live DB ke 76 tables ka inspector dump (`uniques`, indexes, columns),
  NULL/duplicate counts, aur code padha gaya — naam se kuch DONE nahi marka.
* Findings: **5 blocker, 11 major, 5 minor**, har ek file:line ya table:column ke saath.
* Status inventory: 32 items — **DONE 6, PARTIAL 17, MISSING 9**.
* Plan: Phase 1…7 (upar), har ek me checklist + impact.
* Open questions: **Q1…Q6** — sab **decided** (0.8).
* **Naya requirement (0.9)**: "Teachers" aur "Staff" do alag section — plan me add ho
  gaya (Phase 3 backend, Phase 6 frontend, Phase 7 tests).
* Next: aap "start phase" / "next phase" likhein → **Phase 1** (schema safety, jisme
  `user` → `app_user` bhi hai) shuru.

---

## Phase 1 — Result (2026-11-14)

**Status: COMPLETE.** Phase 1 ke saare 8 items live DB par lage, up/down/up proof hua,
aur naye tests green hain. **Koi data delete nahi hua.**

### Migrations (chain, ek hi head `f2c7a4e9b6d1`)

| # | file | kya kiya |
| --- | --- | --- |
| 1 | `b7e4c1a9f2d3_school_id_not_null.py` | 21 NULL `school_id` parent se backfill (staffauditlog 3, staffattendancerecord 3, attendancerecord 15) → `NOT NULL`; `ix_securitylog_school_id`, `ix_chatfile_school_id` |
| 2 | `c1f6d2b8e4a7_unique_keys_and_slot.py` | `uq_school_code`, `uq_school_name`, `uq_school_email`, `uq_employee_school_code`, `uq_timetableperiod_teacher_slot`; weaker `ix_school_*` + global `ix_employee_employee_code` drop |
| 3 | `d3a8e6b1c4f9_money_numeric_12_2.py` | 6 money columns → `numeric(12,2)` (`feestructure.amount`, `feetransaction.amount_paid`, `employeesalary.salary_monthly`, `salarypayment.gross/deductions/net`, `employee.previous_employer_monthly_salary`) |
| 4 | `e5b9c3a7f1d2_rename_reserved_columns.py` | `securitylog.user`→`actor_email`, `securitylog.when`→`occurred_at`, `chatfile.when`→`shared_at` |
| 5 | `f2c7a4e9b6d1_user_to_app_user.py` | `ALTER TABLE "user" RENAME TO app_user` (pure rename — OID se FK/index/constraint sab intact) |

### Behaviour notes (deliberate, spec-on-record)

* **`user` → `app_user` sirf rename hai**: constraint **naam** (`user_pkey`,
  `uq_user_school_email`, `fk_*_user_id`) jaan-boojh kar nahi badle — rename se kaam
  ho gaya aur churn kam raha. Naye naam chahiye to alag migration.
* **Migration 1 fail-safe hai**: `nullable=False` sirf tab lagta hai jab live count
  `NULL = 0` ho (`_null_count(table)` guard). Aisa row jo resolve na ho, column
  nullable chhod deta hai — app boot nahi tootega. **`user.school_id` nullable hi hai**
  (platform admin, rule 2).
* **Migration 2 downgrade purani shape laata hai** (global unique employee code + 3
  non-unique school indexes) — history faithful, documented.
* **Money API par `float` hi raha**, `Decimal` sirf model/DB me (`fees/models.py` me
  comment) — warna JSON serialization aur frontend arithmetic tootti.
* Naya `uq_timetableperiod_teacher_slot` ne **humari hi test fixture** pakdi
  (`test_staff_self_view` ek teacher ko 8 periods Monday 09:00 se de raha tha) —
  constraint sahi hai, fixture spread (day × slot) kar di.

### Tests

* **Naya**: `backend/tests/test_phase1_schema.py` — **9 tests, 9 passed**
  (app_user naam, per-school employee code unique, do school dono EMP-0001, double-booking
  reject, next slot ok, money round-trip, salary decimals, `user`/`when` columns gone,
  school keys unique).
* **Regression**: 16 files, **260 passed** (`phase1_schema`, `permission_matrix`,
  `staff_self_view`, `schema_columns`, `staff_performance`, `people_contracts`,
  `staff_attendance`, `staff_leave`, `staff_substitution`, `staff_appraisal`,
  `staff_workload`, `staff_profile`, `staff_documents`, `tenancy`, `fee_structure`,
  `contacts`).
* **Lint**: `ruff check` + `ruff format --check` — **All checks passed** (touched files).
* **up/down/up proof**: fingerprint (columns+types+indexes+row counts) pehle aur baad me
  **identical** — `employee` 70, `leaverequest` 0, `staffattendancerecord` 3.

### Environment caveats (Phase 1 se nahi, pehle se hain)

* `tests/test_lifecycle.py` — 4 tests `bcrypt>=4.1` vs pinned `<4.1.0` ki wajah se fail
  (passlib `__about__` probe). Dependency pin theek karna hai, code nahi.
* `tests/test_operations_authorization.py` — collect hi nahi hota (`langchain_core`
  missing). Optional dep install par yeh chalega.

### Files touched

* `alembic/versions/` (5 new), `app/core/schema.py` ke bharose koi change nahi
* `admin/users/models.py`, `admin/settings/{models,schemas,service}.py`,
  `main/chat/{models,schemas,service,repository,router}.py`,
  `finance/fees/{models,service}.py`, `operations/salary/models.py`,
  `operations/fees_structure/models.py`, `people/staff/models.py`,
  `academic/classroom/timetable/models.py` + `foreign_key="user.id"` ke 16 sites
* `frontend/src/types/index.ts`, `components/features/settings/SettingsPage.tsx`,
  `components/features/chat/ChatFilesTab.tsx`
* `backend/tests/test_phase1_schema.py` (naya), `backend/tests/test_staff_self_view.py`
  (fixture fix)

**Next: Phase 2** — leave/attendance/substitution schema (`leaverequest.employee_id` +
leave tabs ka check constraint, `leavetype`, `holiday`, `department`,
`academic_year`/`enrollment` stub). Aap "next phase" likhein.

---

## Phase 2 — Result (2026-11-14)

**Status: COMPLETE.** Schema live DB par laga (ek hi head `c6f3a9e1d4b7`), down/up proof
ho gaya, 12 naye tests pass, aur poora suite green (5 pre-existing failures chhod kar,
neeche list). **Koi column drop nahi hua, koi row delete nahi hui.**

### Migrations (chain)

| # | file | kya kiya |
| --- | --- | --- |
| 1 | `a4d1e7c9b2f5_phase2_school_masters.py` | `academic_year`, `department`, `holiday`, `enrollment` (stub); `employee.department_id` + backfill |
| 2 | `b5e2f8d0c3a6_phase2_leave_schema.py` | `leavetype` + seed (8 defaults/school + school ke apne types); `leaverequest.employee_id/leave_type_id/half_day` + `ck_leaverequest_one_subject`; `leavepolicy.leave_type_id`; `leavebalance.leave_type_id/academic_year_id` |
| 3 | `c6f3a9e1d4b7_phase2_classroom_links.py` | `classlog.timetableperiod_id`; `syllabusprogress.teacher_id/academic_year_id/planned_completion`; `staffattendancerecord.check_in_time/check_out_time/leave_request_id` + status CHECK |

### Live data (probe ke baad)

* `department` = **7** rows bane, `employee.department_id` = **70/70** employees par set
  (`sports` vs `Sports` `DISTINCT ON lower(...)` se dedupe — plain `SELECT DISTINCT`
  kaam nahi karta kyunki `gen_random_uuid()` volatile hai).
* `leavetype` = **16** rows (8 default + 8 jo school ke apne policy/request rows me the).
* `academic_year` = 0 (stub; koi session pehle se nahi tha), `enrollment` = 0.
* `leaverequest` = 0 rows, isliye `ck_leaverequest_one_subject` bina kisi backfill ke
  lag gayi (guard rehta hai: unresolved row ho to constraint nahi banti, boot nahi tootta).

### Decisions (plan se hat kar, jaan-boojh kar)

* **`leavebalance.used_days` nahi joda** — balance derived hai (approved − pending).
  Stored counter ko increment/decrement/re-check/repair chahiye; wahi 4 jagah register
  aur balance ko aapas me ladati hain. Phase 4 ko adjust kar diya.
* **`status` text hi raha** (`Pending/Approved/Rejected/Cancelled`) — DB enum banane se
  har reader badalna padta aur purane rows ka case tootta.
* **`staffattendancerecord.status` CHECK = `present/absent/half_day`** — `on_leave`
  derived (`leaverequest` se), warna cancel ki hui leave ka stale "On Leave" row reh
  jaata; `late` `labels` ne rok diya jab tak pay/leave par rule tay na ho.
* **`holiday.on_date`** (naam `date` nahi) — `date: date` pydantic clash deta hai.
* **Text columns nahi hataye**: `employee.department`, `leaverequest.leave_type`,
  `leavepolicy.leave_type`, `leavebalance.leave_type` — jo file hua wahi dikhta rahe.

### Tests / gates

* **Naya**: `tests/test_phase2_schema.py` — **12 passed** (staff leave names employee,
  both-NULL refused, both-set refused, leavetype per-school unique, holiday per-day
  unique, session dates, department unique, employee→department link, classlog period,
  syllabus three columns, enrollment one-placement, register times + `on_leave` refused).
* **Full suite**: **322 passed, 7 failed** — 2 fail `MODEL_MODULES` drift ke the
  (`appraisal`/`substitution` missing) → **fix kar diye**, `test_structure.py` ab 6/7
  (baaki `langchain_core` env). Bache hue **5 pre-existing**: 4 × `RoleEnum has no
  attribute 'admin'` (`test_assignments`, `test_authorization`) + 1 langchain router test.
* **bcrypt pin** (aapka pehla kaam): env me 5.0.0 chadha hua tha, `pyproject.toml`
  `<4.1.0` pin ke mutabik **4.0.1** install kiya → `test_lifecycle.py` **6 passed**.
* **up/down/up proof**: `downgrade f2c7a4e9b6d1` → `upgrade head` clean; ek bug pakda
  (M3 downgrade check constraint drop nahi karta tha) → guard lagaya, dono directions
  idempotent.
* **Lint**: `ruff check` + `ruff format` — **All checks passed**.

### Files touched

`app/domains/services/leave/{models,workflow}.py`,
`app/domains/admin/settings/models.py`, `app/domains/people/staff/models.py`,
`app/domains/people/teachers/staff_attendance/models.py`,
`app/domains/academic/classroom/{academics,homework,students}/models.py`,
`app/core/schema.py` (MODEL_MODULES drift), 3 migrations,
`tests/test_phase2_schema.py` (naya), `tests/test_staff_attendance.py`,
`tests/test_staff_substitution.py`, `tests/test_people_contracts.py` (staff leave ab
`employee_id` deti hai).

**Next: Phase 3** — `GET /teachers` pagination, Teachers/Staff split (0.9), register ka
roll fix, qualification/active-status single source, cards + empty states. "next phase"
likhein.


---

## Phase 3 — Result (2026-11-14)

**Status: COMPLETE** (ek item — qualification formatting — Phase 5 me, neeche). Koi
migration nahi (Phase 2 ka schema hi kaafi tha), koi data touch nahi.

### Kya bana

| cheez | kahan | kya |
| --- | --- | --- |
| Teachers/Staff split | `repository._apply_roll/_roll_subquery/roll_employees` | ek hi role list do tarah padhi — `IN (teaching)` = Teachers, `NOT IN` = Staff. Naya column nahi, isliye dono lists kabhi overlap nahi karti. |
| `/staff`, `/staff/summary` | `people/teachers/router.py` | `/teachers` jaisa hi (filters/scope shared); summary me `kind` + `shows_periods=False` (periods tile hide). |
| Pagination total | `repository.count_teachers` + router | `GET /teachers`/`/staff` ab **`X-Total-Count`** bhejte hain — DB se count, page se nahi. Body list hi raha (frontend break nahi). |
| Register roll fix | `repository.all_employees` + `staff_attendance.service._roll(..., kind)` | register ab **poore school** ka hai (accountant/driver bhi), pehle sirf teachers. `kind` se ek side filter. |
| Periods definition | `repository.period_counts` | `timetableperiod` rows per teacher/ek week — koi estimate nahi (naya test isko pin karta hai). |
| Empty school | service/repository | `[]` + total 0; `visible_ids=set()` par bhi 0 (SQL `IN ()` error nahi). |

### Decisions / notes

* **`kind` ek filter hai, permission nahi** — dono endpoints same `teachers.read` +
  `scope.visible_employee_ids` use karte hain; teacher-only account ko dono me apni
  hi row milti hai.
* **`shows_periods`** field isliye ki `periods_per_week=0` staff ke liye sach hai, par
  UI usay "0 load" na samjhe — tile hi nahi dikhni chahiye.
* **Qualification formatting open hai**: directory row ka `qualification` text column
  hai (`staffqualification` list profile drawer me dikhti hai). "B.A., B.Ed." string
  Phase 5 me profile lists ke saath wire hogi — tab tak jo school ne likha wahi
  dikhta hai (invented join nahi).
* **Staff performance** ke syllabus/results "no data" components Phase 5 me aate hain,
  kyunki wahan score ka formula banta hai; abhi staff ka summary/performance row
  periods ke bina hi sahi hai.

### Tests / gates

* **Naya**: `tests/test_phase3_teachers_split.py` — **9 passed** (opposite sides, HOD
  double-role = ek row, skip/limit pages, total filters se, search+department compose,
  empty school + empty scope, register roll me staff, periods = timetable rows,
  staff ka periods tile hidden).
* **Regression**: people/teachers ka poora set + phase1/phase2 + permission matrix +
  structure — green (jo fail hain woh pehle se: `RoleEnum.admin` × 4 aur
  `langchain_core` × 1).
* **Lint**: `ruff check` + `ruff format` — All checks passed.

**Files touched:** `people/teachers/{repository,service,router,schemas}.py`,
`people/teachers/staff_attendance/service.py`, `tests/test_phase3_teachers_split.py`.

**Next: Phase 4** — leave approval transaction (holiday-aware working days,
substitution rows, `staffauditlog`), cancel/reject reversal, `POST /teachers/me/attendance`,
`staff_attendance.self` permission, leave tabs ka `kind` filter. "next phase" likhein.


---

## Phase 4 — Result (2026-11-14)

**Status: COMPLETE.** Koi migration nahi (Phase 2 ka schema kaafi tha), koi data
rewrite nahi. Sab kuch ek hi commit/transaction me hota hai.

### Kya bana

| kaam | kahan | kya |
| --- | --- | --- |
| **Apni attendance** | `staff_attendance.service.mark_self` + `POST /teachers/me/attendance` (201) | Employee **token se** resolve hota hai — request body me `employee_id` field hi nahi, isliye kisi aur ki row mark karna possible nahi. Ek date par ek mark; dobara = **409**. Har mark ka `staffauditlog` line (`section="attendance"`, action `created`, summary "…(marked by the person)"). |
| **`staff_attendance.self`** | `auth/permissions.py` | Naya permission; TEACHER, HOD aur STAFF role lists me. `staff_attendance.mark` (kisi ki bhi row) alag hi rehta hai — office ka right. |
| **Leave tabs (0.10) — backend** | `GET /leave/requests?kind=staff\|student\|all` + `GET /leave/visible-kinds` | Ek table, do views. `kind` **filter** hai, permission nahi: staff rows directory scope se, student rows office ko sab aur baaki ko sirf apni (guardian/student login). `visible_kinds` batata hai kaun se tab draw karne hain (teacher → `["staff"]`, office → dono). |
| **Decision transaction** | `workflow.decide` (already single-commit) | Approve/reject/cancel: status + decided_by/at + note + **ek audit line**, ek `commit`. |

### Decisions (deliberate)

* **Register me `on_leave` row nahi banti** — `On Leave` derive hota hai (`leaverequest`),
  isliye cancel karte hi din wapas normal ho jaata hai; stored copy drift karti.
* **Substitution rows approval me nahi banti** — board leave se derive karta hai
  (`substitution.board`), to approve karte waqt likhne ke liye kuch nahi.
* **Balance reversal free hai** — `days_for` derived hai; test approve → cancel par
  2 → 0 pin karta hai.
* **Working days (holidays skip)** abhi display-layer ka kaam hai: `holiday` table
  Phase 2 me bani, `days` jo file hua wahi rehta hai (history rewrite nahi). Phase 5/6
  me balance/leave rows par working-day figure add hoga.

### Tests / gates

* **Naya**: `tests/test_phase4_leave_attendance.py` — **6 passed** (own mark + audit,
  duplicate 409, login-without-staff 409, `kind` filter + scope isolation,
  `visible_kinds`, approve → cancel → balance 2→0).
* **Regression**: phase1–4 + leave/attendance/self-view/substitution/permission
  matrix/tenancy/structure — **195 passed**, 1 fail = `langchain_core` env (pre-existing).
* **Lint**: `ruff check` + `ruff format` — All checks passed.

**Files touched:** `services/leave/{service,repository,router,schemas}.py`,
`people/teachers/staff_attendance/{service,schemas}.py`, `people/teachers/router.py`,
`auth/permissions.py`, `tests/test_phase4_leave_attendance.py`.

**Next: Phase 5** — workload + performance derived figures (periods/week vs rule,
completed-this-week from `classlog.timetableperiod_id`, substitute periods, percentage;
performance components with "no data" for staff), plus qualification formatting.
"next phase" likhein.


---

## Phase 5 — Result (2026-11-14)

**Status: COMPLETE** (punctuality / leave-taken / results jaan-boojh kar score me nahi).
Koi migration nahi; koi stored figure nahi - sab derive hota hai.

### Kya bana

| figure | kahan | kaise nikla |
| --- | --- | --- |
| **completed this week** | `workload.repository.completed_counts` → `WorkloadMatrixRow.completed_this_week` | is week (Mon–Sun) ke `classlog` rows per teacher - **log = fact**, timetable = plan. Ek statement, poore page ke liye. |
| **remaining this week** | matrix row | `periods - completed`, 0 par floor (negative "work left" nahi hota). |
| **substitute periods** | `workload.repository.substitute_counts` | is week ke **approved** covers; "Assigned" cover load nahi hai. |
| **percent vs rule / overload** | pehle se maujood | `utilisation`, `band`, `overloaded` - capacity rule ya timetable slots se (Phase 3/4 ka kaam). |
| **performance components** | `appraisal/performance.py` + `PerformanceComponent` | attendance (90 din ka register, half-day = ½), reviews (rating/5×100), syllabus (sirf teacher). Har component `value: None` ho sakta hai = **"no data"**. |
| **overall score** | `WEIGHTS` + `_score()` | `{attendance .3, reviews .4, syllabus .3}`, available components par renormalised; kuch bhi na ho to `score=None` (0 nahi). |
| **staff rows** | `StaffPerformance.kind` | `kind="staff"` par syllabus component **hissa hi nahi** - job me syllabus hota hi nahi. |

### Decisions

* **Punctuality (`late`) score me nahi**: `late` status abhi store hi nahi hota
  (`labels` ki deliberate rule - pay/leave par rule tay hone tak).
* **"Leave taken" score nahi banta**: woh entitlement hai, performance nahi; balance
  screen usko already dikhati hai.
* **Results bhi nahi**: marks read wiring Phase 6/7 ka kaam hai aur plan me "optional".
* **Performance ab poore roll par** (teachers + staff), pehle sirf rated teachers par
  tha; `score=None` + "no data" ne purana rationale (fabricated 0 na ho) bacha liya.
  Do purane tests isi contract par update hue.
* **`classlog` ka unique key** `(classroom_id, date)` hai, isliye per-period logging
  ek din me ek hi row de sakta hai - `completed` aaj "us din ka log" ginta hai.
  Per-period figures chahiye to key me `timetableperiod_id` jodna padega (Phase 7
  me flag, migration ke saath).

### Tests / gates

* **Naya**: `tests/test_phase5_workload_performance.py` — **5 passed** (log window,
  approved-only substitute, weighted score 100/80 → 89, all-no-data → `score=None`,
  staff ka syllabus component absent).
* **Regression**: phase1–5 + performance/workload/self-view/attendance/leave/
  substitution/appraisal/profile/documents/contracts/permission/tenancy/structure —
  **285 passed**, 1 fail = `langchain_core` env (pre-existing).
* **Lint**: `ruff check` + `ruff format` — All checks passed.

**Files touched:** `workload/{repository,schemas}.py`, `service.py` (matrix + week
counts), `schemas.py` (`PerformanceComponent`, `StaffPerformance`), 
`appraisal/performance.py`, `tests/test_phase5_workload_performance.py`,
`tests/test_staff_performance.py` (2 tests naye contract par).

**Next: Phase 6** — frontend: "Teachers & Staff" → **"Teachers"**, naya **Staff**
sidebar + page (`kind="staff"`), tabs (List/Workload/Attendance & Leave/Performance),
leave ke do tab (Staff/Student) `visible_kinds` se, "Mark my attendance" button,
qualification formatting. "next phase" likhein.


---

## Phase 6 — Result (2026-11-14)

**Status: COMPLETE** (ek deviation: Staff ka Workload tab abhi nahi — neeche).
Backend me koi change nahi; sirf frontend.

### Kya bana

| cheez | file | kya |
| --- | --- | --- |
| **"Teachers" rename** | `lib/constants/nav.ts` | "Teachers & Staff" → **"Teachers"**; route/codename jaisa tha waisa (`/dashboard/teachers`) — koi link toota nahi. |
| **Naya Staff section** | `app/dashboard/staff/page.tsx` | `<TeachersPage kind="staff" />` — same components, doosra half. Sidebar me "Staff" entry (wahi `teachers.read`). |
| **Kind-aware data** | `teachers.service.ts`, `useStaff.ts` | `getStaff(query, kind)` → `/teachers` vs `/staff`; `getStaffSummary(kind)` → `/staff/summary`; query keys me kind, isliye dono tabs ka cache alag. Performance row `kind` se filter hota hai. |
| **Tabs per kind** | `TeachersPage.tsx` | Teachers: List / Workload / Attendance & Leave / Performance / Substitution / Appraisal. Staff: List / Attendance & Leave / Performance. |
| **Periods tile** | `TeachersPage.tsx` | `summary.showsPeriods === false` par tile **draw hi nahi hoti** — `0` "no load" nahi padha jaata. |
| **Mark my attendance** | `useAttendance.ts` + `AttendanceLeaveTab.tsx` | `POST /teachers/me/attendance`, `staff_attendance.self` par; button `busy === "self"` par loading, 409 par server ka message. |
| **Leave read-only + 2 tabs** | `AttendanceLeaveTab.tsx`, **naya `LeaveTabsPanel.tsx`** | Apply/approve/reject buttons band (`readOnlyModule`) aur "Open Leave & Applications →" link; neeche **Staff leave / Student leave** tabs, kinds server se (`/leave/visible-kinds`), rows `/leave/requests?kind=`. |
| **Workload "This week"** | `WorkloadMatrixTable.tsx`, `types/index.ts` | completed / periods · `N left` · `+N cover`; log na ho to `—` (0 nahi). Band colors pehle se (Overloaded red / Steady green / Light muted / Unassigned amber). |
| **Performance table** | `StaffPerformanceTable.tsx` | Components column + `score === null` → "no data" (bar nahi); staff ke liye syllabus column hidden (`showSyllabus`). |

### Deviation (honest)

* **Staff ka Workload tab nahi** — plan me staff ke liye "duties + attendance-based
  load (periods nahi)" tha. Backend me matrix teacher-only hai
  (`/teachers/workload`), aur staff ke liye alag shape banana baaki hai. Tab staff ke
  liye hide kiya hai, taaki khaali/periods-wala matrix na dikhe. Phase 7 me ya aapke
  kehne par banega.

### Gates

* `npx tsc --noEmit` — **0 errors**
* `npx eslint src/components/features/teachers src/app/dashboard/staff/page.tsx src/lib/constants/nav.ts` — **0**
* `npx prettier --check …` — "All matched files use Prettier code style!"

**Files:** `app/dashboard/staff/page.tsx` (naya), `components/features/teachers/
{TeachersPage,AttendanceLeaveTab,StaffPerformanceTable,WorkloadMatrixTable,
LeaveTabsPanel(naya),useStaff,useAttendance}.tsx/.ts`, `services/teachers.service.ts`,
`types/index.ts`, `lib/constants/nav.ts`.

**Next: Phase 7** — quality + DoD: school-isolation aur split tests, teacher-only
endpoints staff ko 403/404, duplicate/double-booking, approval → `On Leave Today`,
workload numbers vs timetable, har migration ka up+down, money = Decimal audit,
PII encryption plan. "next phase" likhein.


---

## Phase 7 — Result (2026-11-14) — aur poore Teachers module ka final report

**Status: COMPLETE** (1 open item: PII encryption; 1 deviation: Staff ka Workload tab).

### Is phase me kya nikla

* **Asli security bug mila**: `session.get(LeaveRequest, id)` tenant listener se nahi
  guzarta, isliye ek school ka caller doosre school ki leave id guess kar ke padh sakta
  tha. Fix: `repository.request_by_id` `tenant_of(session)` se school compare karta hai →
  `404`. Test se pin (`test_another_schools_leave_is_a_404`).
* **Naya**: `tests/test_phase7_definition_of_done.py` — **9 tests** (split disjoint,
  staff register, duplicate 409, colleague ka month 404, cross-school leave 404,
  approval→`On Leave Today`→cancel, `kind` scope, workload = timetable, money
  `numeric(12,2)`).
* **Money audit**: `finance/fees`, `operations/salary`, `operations/fees_structure` me
  `float(` ka koi use nahi; 6 money columns `numeric(12,2)` test se pinned.
* **Migration proof**: `downgrade f2c7a4e9b6d1` → `upgrade head` clean; `alembic current`
  = head `c6f3a9e1d4b7`.

### Poore module ka ek nazar me

| phase | kya | status |
| --- | --- | --- |
| 0 | Audit + plan (is file me §0.1–0.10) | COMPLETE |
| 1 | Schema safety: `app_user`, uniques, double-booking, `numeric(12,2)`, reserved words | COMPLETE |
| 2 | Leave/attendance/masters: `leavetype`, `holiday`, `department`, `academic_year`, `enrollment`, `on_date`, XOR check | COMPLETE |
| 3 | Backend list: pagination + `X-Total-Count`, Teachers/Staff split, register roll fix | COMPLETE |
| 4 | Leave transaction + audit, own attendance (`staff_attendance.self`), leave tabs backend | COMPLETE |
| 5 | Workload derived (completed/remaining/covers) + performance components ("no data") | COMPLETE |
| 6 | Frontend: Teachers/Staff pages, tabs per kind, mark-my-attendance, read-only leave + 2 tabs, performance table | COMPLETE |
| 7 | DoD: isolation bug fix, split/privacy/approval/workload/money tests, migration proof | COMPLETE |

### Baaki (jaan-boojh kar open)

1. **PII encryption** (Aadhaar/PAN/bank) — plan likha hua hai (§Phase 7), **key source**
   ka decision chahiye (`APP_KMS_KEY` env vs cloud KMS). Iske bina encryption adhoora
   hoga, isliye plaintext par kaam nahi kiya.
2. **Staff ka Workload tab** (duties-based load) — backend matrix teacher-only hai;
   staff ke liye shape baaki.
3. **`classlog` unique key** `(classroom_id, date)` per-period logging rokta hai —
   `timetableperiod_id` jodne ke liye chhoti migration chahiye.

### Aakhri gates

* Backend: **ruff clean**; touched suites **171 passed** (1 fail = `langchain_core`
  env, pehle se).
* Frontend: `tsc` 0, `eslint` 0, `prettier` clean (Phase 6).
* DB: head `c6f3a9e1d4b7`, up/down proven, koi data delete nahi.

**Teachers module — Phase 1 se 7 tak — COMPLETE.** Naye kaam ke liye bas bol dein
(PII encryption / staff workload / per-period classlog).


---

## Phase 8 — Result (2026-11-14)

**Status: COMPLETE.** Do migrations, dono up/down/up proven, 6 naye tests, koi data
delete nahi.

### Migrations (chain)

| id | kya |
| --- | --- |
| `d8c4b2e6f1a3` | `app_user` ke objects ko table ke naam par: `user_pkey`→`app_user_pkey`, `user_school_id_fkey`→`app_user_school_id_fkey`, `ix_user_email`/`ix_user_school_id`→`ix_app_user_*`, `uq_user_platform_email`/`uq_user_school_email`→`uq_app_user_*` |
| `e9d5c3f7a2b4` | `classlog`: `uq_classlog_classroom_date` → `uq_classlog_classroom_date_period (classroom_id, date, timetableperiod_id)` + partial unique `uq_classlog_classroom_day_only (... WHERE timetableperiod_id IS NULL)` |

**Head: `e9d5c3f7a2b4`.**

### Kya nahi badla (aur kyun)

* Doosri tables ke `*_user_id_fkey` / `*_user_id_key`: naam **column** se aata hai
  (`user_id`), column ka naam wahi hai — `*_app_user_id_fkey` jhooth hota.
* `user_role` ke apne objects (`user_role_pkey`, `uq_user_role_user_role`): woh ek
  alag table hai, purana `user` table nahi.
* Supabase ka `auth.*` schema (`auth.users`, `sessions`, …): application ka object
  nahi hai.

### Model bhi match karta hai

`admin/users/models.py` ke partial indexes ab `uq_app_user_*` hain aur unpar
`sqlite_where` bhi hai — warna SQLite par partial index **unconditional unique** ban
jaata (tests wahin chalte hain). Isi tarah `classlog` ke partial index par
`postgresql_where` + `sqlite_where` dono hain.

### Workload figure

`completed_counts` ab **periods** ginta hai (period-wali `classlog` rows); jo school
purani din-line likhta hai uske liye **din** ginta hai — ek teacher ke total me dono
kabhi mix nahi hote.

### Down/up proof

`upgrade head` (dono lagi) → `downgrade c6f3a9e1d4b7` (dono ulti) → `upgrade head`
(dono dobara) — clean; `alembic current` = `e9d5c3f7a2b4`.
Downgrade purani `classlog` key **tabhi** wapas banata hai jab data usay satisfy kare;
per-period rows hon to data delete nahi hota — non-unique index + printed count.

### Tests / gates

* `tests/test_phase8_names_and_classlog.py` — **6 passed** (koi model object
  `ix_user_*`/`uq_user_*`/`user_pkey` nahi; ek din me do period lines; wahi period
  dobara → IntegrityError; din-line ek hi; completed = periods; din-line school = days).
* Regression (phase1/3/5/7 + workload/self-view/contracts/tenancy/permission/structure)
  — **118 passed**, 1 fail = `langchain_core` env (pre-existing).
* `ruff check` — All checks passed.

**Files:** 2 migrations, `admin/users/models.py`,
`academic/classroom/homework/models.py`,
`people/teachers/workload/repository.py`,
`tests/test_phase8_names_and_classlog.py`, `backend/phase.md`.


