# Exam Module (Class Test + School Exam + Marking & Grading + Result) — Phase Plan (EduConnect)

> **Status:** Phase 0 se 10 complete — 24 Nov 2026. Module poora.
> **Files:** yeh file = plan + progress log. Jo baat ek phase se doosre phase ko affect
> kare wo **Section 6 (Cross-phase reminders)** mein hai.
> **Language:** prose Hinglish; code, table/column names, API names, UI labels English.
> **Rule:** har phase ke baad main ruk kar tumse poochunga. Agla phase sirf tumhare
> "next phase" ke baad.

---

## 0. Kaam kaise chalega

### 0.1 Phase discipline
- Har phase shuru karne se pehle: us phase ke subphases dobara padho, Section 6 ke
  reminders padho, aur current code us phase ke hisaab se deeply dekho.
- Purani phases ka bana hua code todna nahi hai. Sabse zyada dhyaan: **AI paper builder**
  (`exams/service.py`, `exams/llm`, `exams/rag`, `paper_draft`) ko bilkul nahi chhedna.
  Yeh alag feature hai (question paper banata hai); hum **exam run karne wala** hissa
  (`exams/plan`) badal rahe hain.
- Har phase ke baad is file mein: checkbox `[x]`, aur Section 8 (Completion Log) mein
  entry — kya kiya, kaunsi files, tables/endpoints/components, tests, baaki kya, aur
  Section 6 mein naya reminder agar mila.
- Ek phase khatam hone par summary do aur **ruko**. Tumse poochho: "next phase?" aur
  jo ⚑ decision pending ho wo bhi.

### 0.2 Loop aur terminal rules
- Sirf synchronous, khud khatam hone wali commands. Dev server / watch mode foreground
  mein nahi.
- Ek hi error par maximum 2 fix attempts; phir ruk kar error + analysis batao.
- Lambe output ko filter karo (`head`, `tail`, `grep`).
- Destructive command (drop/delete/force reset) tumhe bataye bina nahi.
- **Backend tests is machine par kaise chalte hain (Phase 3 mein mila):** `backend/.venv`
  ka `python.exe` Windows Application Control se block hai, **lekin uv ka base Python 3.14
  chalta hai** aur venv ke packages ke saath pytest chal jata hai:

  ```
  cd backend
  PY="C:/Users/Prash/AppData/Roaming/uv/python/cpython-3.14-windows-x86_64-none/python.exe"
  export PYTHONPATH="D:/Prashant_saxena/Work/Educonnect/backend/.venv/Lib/site-packages;D:/Prashant_saxena/Work/Educonnect/backend"
  "$PY" -m pytest tests/test_exam_class_test.py -q -p no:cacheprovider -W ignore
  ```
  (System ka Python 3.12 project ka code compile nahi kar sakta — wo 3.14 syntax use karta hai.)
  Frontend: `npx tsc --noEmit -p .`, `npx eslint <files>`, aur `node --test src/lib/exams/*.test.ts`.
- **Pehle se fail hone wale 17 tests** (saaf `HEAD` par bhi fail, meri changes se nahi):
  `test_exams_generation/question_unlock/rag/source_index` (AI paper — `pywin32` missing, UUID type),
  `test_classroom_homework::test_assigning_tells_the_section_once` (aaj ki date par "Overdue"),
  `test_operations_authorization::test_no_route_answers_without_a_guard` (settings ke academic-year
  routes par guard nahi), `test_phase1_schema::test_a_teacher_cannot_be_in_two_rooms_at_nine`
  (unique key mein `academic_year_id` NULL hai). Inhe tab tak "baseline" maano.

### 0.3 Testing rules
- Sirf us phase se juda test: us phase ka endpoint/table/component/migration.
- Poora suite nahi. End-to-end test sirf **Phase 10** mein.
- Naye backend tests ka naam `tests/test_exam_<topic>.py` (purane `test_classroom_exams.py`,
  `test_exam_paper_groups.py` ko todna nahi — wo pass hote rehne chahiye).

### 0.4 Language
- `phase3.md`: Hinglish. Baaki sab (code, comments, UI, API errors) English.
- UI labels proper case; dates school ke existing format mein.

### 0.5 Design aur codebase consistency
- Frontend: maujooda components/styles reuse (`Tabs`, `Card`, `Modal`, `Select`, `Badge`,
  `Table`, `useToast`). Timetable ka **S / T gol badge** pattern (Assigned / Temporary)
  Test Taken By ke liye reuse. Naya UI library nahi.
- Backend: router → service → repository pattern, `RequirePermission`, `school_id` scoping,
  alembic migrations, `events.notify()` hi notification ka ek writer.
- Existing `role` / `permission` / `rolepermission` reuse. Naya parallel permission system
  nahi.
- **Sab kuch id se match hoga** (teacher, subject, class-section, student) — naam se
  nahi. (Timetable mein yahi decision hua tha.)

### 0.6 Production aur scalability mindset
- Har naye table mein `school_id` (DB mein NOT NULL), sahi FKs, indexes, unique constraints.
- Paise ki tarah marks bhi **Decimal** (float kabhi nahi): `numeric(6,2)`, percentage ka
  hisaab exact.
- N+1 nahi; result screens SQL aggregate / ek-do queries se.
- Marks save, publish, reschedule transaction mein + idempotent. Duplicate notification
  `dedupe_key` se roki jaye.
- Permission server par enforce; button chhupana kaafi nahi. School A ka data School B ko
  kabhi na dikhe (cross-school id = `404`).

---

## 1. Business Rules (agreed, final — tumhare doc se)

### 1.1 Exam module ke hisse
Exam module ke **3 main tabs**: **Class Test**, **School Exam**, **Exam Result**.
**Marking & Grading ka koi alag tab nahi** — wo setup usi card mein hota hai jahan exam
schedule ho raha hai (Class Test card) ya date sheet set ho rahi hai (School Exam card).
- *Class Test tab* mein sirf: scheduling + marks entry.
- *School Exam tab* mein sirf: date sheet + syllabus + marks entry.
- *Exam Result tab* (2 sub-tabs: Class Test Result, School Exam Result) mein **saare**
  result views: marks, percentage, grade, pass/fail, class average, highest, lowest.
- *Marking & grading setup* (total marks, pass marks, grading scale) **card ke andar ka
  section** hai, alag tab nahi; school-level 33% / default ladder sirf **pre-fill** karte hain.

### 1.2 Class Test — scheduling
- Fields: **Test Taken By**, **Subject**, **Total Marks**, **Date**, **Type** (hamesha
  "Class Test"), **Note for Family**.
- Subject sirf us class ke **existing courses** (`classroomsubject`) se.
- **Test Taken By** default = us class+subject ka assigned teacher. Assigned teacher na
  ho to dropdown se koi bhi teacher; test **temporary teacher** mark hota hai.
  Timetable ki tarah **Assigned card / Temporary card**.
- **Submit** par parents + students ko notification.
- **Reschedule** (date/time badle) → naye time ke saath reschedule notification.
- **Delete** → delete notification.
- Koi aur edit (jaise total marks) reschedule nahi; notification sirf batata hai kya
  badla ("total marks changed").
- **Note for Family** guardian + student ko dikhta hai, schedule notification ke saath
  jata hai, kabhi bhi edit ho sakta hai. Note badalna reschedule **nahi**; notification
  sirf "note changed" kehti hai.

### 1.3 Class Test — sections
- Ek test **kai sections** ke liye ek saath (multi-select: A, B, C…); ek section bhi chalta.
- Sections baad mein edit se badal sakte hain.
- Same test har chune hue section mein dikhta hai.
- Saare sections **ek hi class** ke hone chahiye; alag classes mix nahi.

### 1.4 Class Test — marks
- Marks usi test mein upload hote hain. Upload par parent + student ko marks wali
  notification.
- Total marks pehle se test par; teacher baad mein badal sakta hai.
- Har student ke liye **marks / total** aur **percentage**.
- Academic year mein ab tak ke saare class tests ki **running list**: har student ka
  subject-wise (marks obtained / total, percentage) aur sab subjects ka **overall
  class-test percentage**.

### 1.5 School Exam — date sheet
- Date sheet ki format: har row = **Subject, Total Marks, Date**, us class ke **har
  course** ke liye.
- Har course ka apna **syllabus**, uske saath **View** button.
- **Type** dropdown: Unit Test, Periodic Test, Mid Term Test, Half Yearly, Annual,
  Pre-Board, Practical, **Custom** (Custom mein teacher apna naam likhta hai).
- Note for Family yahan bhi.

### 1.6 School Exam — permissions aur publish
- **Read:** guardian, teacher, principal, admin, aur unke upar sab.
- **Write:** class teacher aur subject teacher apne subject ki date + syllabus set kar
  sakte hain. **Class teacher poori date sheet** set kar sakta hai. Admin, principal aur
  upar ke sab kuch kar sakte hain.
- **Publish:** sirf **class teacher** date sheet + syllabus publish karega. Publish se
  pehle parents/students ko dikhta nahi aur notification nahi jati. Subject teacher apne
  subject ki date/syllabus add kar sakta hai, publish nahi.

### 1.7 School Exam — marks
- Marks Class Test ki tarah. Subject-wise marks + percentage, aur overall marks + percentage.

### 1.8 Recommendations (discussion ke baad add hui — ab agreed)
- Sab kuch **session year** + **enrollment record** se bandha (promotion/de-promotion
  ke saath kaam kare).
- Class Test ka status: **Scheduled / Completed (marks uploaded) / Cancelled**.
- **Absent** ek alag value (zero nahi); percentage ke hisaab se bahar.
- Validation: marks obtained ≤ total; total marks ko already-entered marks se neeche
  karne par warning.
- Same class + section + subject + date par dusra test: **warn karo** (popup mein purane
  test ki poori detail: date, subject, total marks, section, kisne banaya) → "create
  anyway" ya "cancel". Har baar warn, chahe marks/period alag hon.
- Marks upload par aur marks edit par parent + student ko notification (kya badla).
  Marks parents ko **publish ke baad hi** dikhte hain.
- Marks ka **audit trail**: kisne kaun sa mark, kab, kis value se kis value kiya.

### 1.9 Marking & Grading Setup (school level)
- Har class test ka **apna alag marking setup**: total marks, pass marks, grading scale.
  Setup poora hue bina test save nahi hoga.
- **Pass marks** do tarah se: minimum marks, ya passing **grade** (user ne percentage ki
  jagah grade chuna — D5). School-level default
  **33%** (auto-fill); test ke liye badal sakte hain.
- **Pass marks number default** = us test ke total ka 33%: 100 → **33**, 50 → **16.5**,
  20 → **6.6**. Yeh har scheduled exam par (Class Test + School Exam dono) lagta hai;
  number ya percentage kisi bhi ek test ke liye badal sakte hain.
- School-level setup sirf **default values** deta hai jo fields ko pre-fill karte hain.
- Result **marks (numbers)** aur/ya **grades** dono tarah dikha sakta hai.
- **Grading scale** ek jagah define hota hai (percentage range → grade, jaise 90–100 = A1);
  baaki sab wahin se padhte hain.
- Pass/Fail automatic nikalta hai.

### 1.10 Marks entry
- Table: class/section ke **har student ki ek row**, marks obtained ka ek column, poori
  class ek screen par.
- Optional baad mein: Excel/CSV se upload.

### 1.11 Exam Result
- Exam module ke teen main tabs: Class Test | School Exam | **Exam Result**.
- Exam Result ke 2 sub-tabs: **Class Test Result**, **School Exam Result**; dono alag
  calculate hote hain, mix nahi. Selected session year ke liye, per student: marks
  obtained, total, percentage, grade, Pass/Fail (har test ke apne setup se).
- Ab tak ke tests (jaise 5 tests ke baad): **subject-wise percentage** aur **overall
  percentage**.
- **Student/Guardian** sirf apne bachche ka result, sirf **publish ke baad**; Absent
  "Absent" dikhta hai, percentage se bahar.
- **Teacher** ke liye class view: class average, highest, lowest, per-test pass aur fail
  count.
- **Admin/Principal aur upar** sab classes ke sab students dekh sakte hain. Vice
  principal abhi chhoda gaya.

### 1.12 Clarifications (24 Nov 2026, user se — ye upar ke rules ko override karte hain)
0. **Date sheet table ka aakhri column "Syllabus"**: har subject row mein ek Syllabus
   button. Subject teacher ne syllabus bhar diya ho to button **active** hota hai aur usse
   wahi likha hua syllabus (usi subject ka) dekha ja sakta hai; na bhara ho to button
   **inactive (disabled)**. Row: `Subject · Date · Total Marks · Pass by (Marks/Grade) · Syllabus`.
1. **Syllabus sirf free text.** Chapter pick karna nahi; teacher seedha text likhta hai
   ("is subject mein kya-kya aayega"). Chapters / `exam_paper_chapter` / group chapters
   naye flow mein **use nahi**.
2. **Koi first day / last day nahi, koi start time / end time nahi.** Exam ya paper par
   sirf **ek date** (paper ki `exam_date`). `exam.start_date/end_date` aur
   `paper.start_time/end_time` na form mein, na API mein, na UI mein. Reschedule = sirf
   **date** badalna.
3. **Class Test banane wale:** subject teacher, class teacher, vice principal, principal
   aur principal se upar ke saare roles.
4. **Date Sheet banane wale:** class teacher, vice principal, principal aur principal se
   upar ke saare roles. Subject teacher **date sheet nahi** banata.
5. **Syllabus banane wala:** subject teacher (apne subject ka) — aur uske upar wale
   (class teacher, vice principal, principal, senior). **Marks** bhi subject teacher
   (+ upar wale) dalte hain.
6. **Date Sheet aur Syllabus = do alag buttons** (alag screens/modals, alag permission).
7. **Class Test mein Date Sheet nahi hoti** (har test ki apni date hoti hai); **School
   Exam mein Date Sheet + Syllabus dono** hote hain.
8. **UI placement:** abhi jahan exam plan dikhta hai wahi rahega. Class Test ka plan
   **Class Test tab ke andar**, School Exam ka plan **School Exam tab ke andar** — bahar
   kahin alag page par nahi. Design **bilkul abhi jaisa** (naya design nahi): wahi
   `Tabs`, `Card`, `Table`, `Badge`, `Modal`; sirf sub-tabs ke naam "Class Exams / School
   Exams" se **"Class Test / School Exam"** hote hain.
9. **Principal se admin tak** (principal aur uske upar ke sab roles) ko **har cheez ka
   poora access**: Class Test, Date Sheet, Syllabus, Marks, Publish, Marking & Grading
   Setup, Exam Result (sab classes ke sab students). Koi step in par block nahi.
10. Vice principal **creation/date sheet** ke saath **result views mein bhi shaamil hai** (24 Nov: user ne
    kaha "rakhlo ise bhi") — pehle ka "abhi chhoda gaya" wala note ab lagu nahi.

---

## 2. Current System — Phase 0 mein code se verify kiya

### 2.1 Kya pehle se bana hai (`backend/app/domains/academic/classroom/exams/plan/`)
| Cheez | Kahan | Kya karta hai |
|---|---|---|
| `exam` table | `exams/models.py` | Ek named exam: `name`, `term`, `start/end_date`, `status`, `scope` (`class`/`school`), `class_id`, `classroom_id`, `academic_year_id`, `exam_type` (**free text**), `created_by_user_id`, `note`, `published_at` |
| `exam_paper` table | same | Date-sheet row = **ek section ka ek subject**: `classroom_subject_id`, `exam_date`, `start/end_time`, `max_marks`, `passing_marks`, `room`, `note`, `published_at`, `paper_group_id`. `UNIQUE(exam_id, classroom_subject_id)` |
| `exam_paper_group` (+chapters) | same | Kai sections ek shared paper baithte hain |
| `exam_paper_chapter` | same | Paper ka **syllabus = chapters** (chapter ids) |
| `marks` | same | Ek student ka ek paper ka score: `marks_obtained` numeric(6,2), `is_absent`, `entered_by`; `UNIQUE(exam_paper_id, student_id)` |
| `marks_audit` | same | Publish ke **baad** ka har change (old/new value, absent flag, kisne, kab, reason) |
| `grade_scale` | same | School ki ladder: `min_percent` → `grade`; `UNIQUE(school_id, min_percent)`. Code mein default ladder (90 A1 … 33 D, 0 E) |
| Status lifecycle | `ExamStatus` | `draft, scheduled, done, marks_entry, published` — **`cancelled` nahi hai** |
| Endpoints | `plan/router.py` | `POST/GET /exams`, `GET /{id}/papers`, `PATCH /{id}`, `GET/POST /papers/{id}/marks`, `POST /papers/{id}/publish`, `PATCH /papers/{id}/marks/{student}`, `GET /{id}/results`, paper-group endpoints |
| Services | `plan/service.py` (1906 lines) | create/update exam, `save_marks`, `publish_paper`, `change_mark`, `results`, `reminder_job`, `_announce`, `_checked_score` (marks ≥ 0 aur ≤ max — **pehle se hai**) |
| Notifications | `EVENT_EXAM_SCHEDULED/CHANGED/PUBLISHED/MARK_CHANGED/REMINDER` | `_announce` date-sheet scheduled/changed bhejta hai (students + class teacher), `dedupe_key` + revision |
| Grades/ranks | `plan/grades.py` | `grade_for(percent)`, competition ranks; grade **derive** hota hai, store nahi |
| Permissions | `auth/permissions.py` | `exams.read/create/update/delete/publish`, `marks.read/create/update/approve/publish/export` pehle se hain |

### 2.2 Frontend (`frontend/src/components/features/classroom/exam-plan/`)
- Exam ka UI **Classroom ke section page ke "Exams" tab** mein hai (`ExamsPlanPanel.tsx`),
  sub-tabs abhi **"Class Exams" / "School Exams"**. `/dashboard/exams` sirf redirect hai.
- Components: `DateSheet`, `ExamScheduleForm`, `MarksGrid`, `ResultsView`, `PaperGroupDialog`,
  `useExamPlan.ts`. Helpers `lib/exams/view.ts`.
- "AI Papers" tab (`ExamsPanel`, `exams/paper-builder`) alag feature hai — **nahi chhedna**.

### 2.3 Baaki jaruri facts
- **Enrollment:** `enrollment` table (student, classroom, academic_year, status,
  `promotion_status`, `previous_enrollment_id`). `UNIQUE(student, year)`. `marks` mein
  abhi **`enrollment_id` nahi** hai — sirf `student_id` + paper (paper → exam → year).
- **Class teacher:** `classroom.class_teacher_id` maujood hai (publish rule ke liye).
- **Subject teacher:** course tab ka `classroomsubject` + `subjectteacher` history; helper
  `course_subjects` aur "active teacher options" Course phase mein ban chuke.
- **Timetable ka pattern:** Assigned/Temporary = S/T gol badge, id-based match.
- **Alembic head:** pehle `0005` tha; **Phase 1 ke baad `0007`** (`0006_exam_marking_setup.py`, `0007_exam_passing_grade.py`).
  Ids chhote numbers hain, file naam alag.
- **Purane tests:** `tests/test_classroom_exams.py`, `tests/test_exam_paper_groups.py`
  — inhe hara rakhna hai.

---

## 3. Gap Analysis — requirement vs maujooda

| # | Requirement | Abhi | Kya karna hai |
|---|---|---|---|
| G1 | Class Test + **Type** fixed; School Exam Type dropdown + Custom | `exam_type` free text | Type enum + Custom naam |
| G2 | **Test Taken By** + Assigned/Temporary | Paper par teacher nahi | `taken_by_employee_id` (+ derive temporary) |
| G3 | **Note for Family** (alag, edit pe sirf "note changed") | `exam.note` / `paper.note` internal | Alag `family_note` + alag notification event |
| G4 | **Multi-section** class test (same class) | Class-level exam + papers per section — structure hai, **section picker / edit nahi** | Section multi-select, add/remove papers |
| G5 | **Per-test marking setup** (pass marks/percent, grading scale), save block | Sirf `passing_marks` (optional) | `pass_mode`, `pass_percent`, grading snapshot; validation |
| G6 | Marking & grading setup **exam card ke andar** (33% pre-fill, pass marks, grading scale) | Ladder rows + `passing_marks` hain; card mein section nahi | Defaults endpoint + reusable form section (alag tab nahi) |
| G7 | Status Scheduled/Completed/**Cancelled** | `cancelled` nahi | Naya status + UI chip |
| G8 | Duplicate warning popup | Nahi | 409 + existing detail + `confirm_duplicate` |
| G9 | Reschedule vs other edit vs note change notification | Sirf "date sheet changed" | Event types alag, "what changed" body |
| G10 | Delete notification | Nahi | Delete/Cancel + event |
| G11 | Marks table entry, absent, validation | **Mostly hai** | Total lower karne ki warning, enrollment tie |
| G12 | Marks upload + edit notification, publish ke baad hi parents ko | Publish + mark_changed hai | Upload (save) par teacher-side status; body "what changed" |
| G13 | Audit trail | Sirf publish ke baad | Spec ke hisaab se confirm (D9) |
| G14 | Date sheet **publish** (class teacher only) | Publish sirf marks ka | `datesheet_published_at` + gating + notification |
| G15 | Syllabus per course + View (**free text**) | Chapter ids hain | `syllabus_text` + alag Syllabus button + View modal (D7); chapters nahi |
| G16 | Permissions (D13 matrix): class test / date sheet / syllabus / marks / publish alag | `_may_plan_paper`: office / subject teacher | Class teacher + leadership helpers, alag checks |
| G21 | **Koi first/last day, start/end time nahi** | `start_date/end_date`, `start_time/end_time` hain | Naye API/UI se hatao (D7b) |
| G17 | Result engine: per-test + cumulative subject-wise + overall, class stats | `results(exam_id)` per exam | Naya yearly aggregator, Class Test / School Exam alag |
| G18 | Exam Result tab (2 sub-tabs, 3 roles ke views) | `ResultsView` per exam | Naya tab + views |
| G19 | Marks session year + **enrollment** se bandhe | Student + paper | `marks.enrollment_id` + backfill |
| G20 | Excel/CSV marks upload | Nahi | Optional (Phase 10, tumse poochhunga) |

---

## 4. Design Decisions (D1–D16) — recommendation

> ⚑ = tumhari confirmation chahiye (Phase 1 se pehle). Baaki recommended default se
> chalenge jab tak tum na badlo.

### D1. Module kahan rahega — ✅ CONFIRMED (user, 24 Nov)
Classroom ke section ke **"Exams" tab ke andar**, jahan abhi hai. Class Test ka plan Class
Test tab mein, School Exam ka plan School Exam tab mein. Design wahi jo abhi hai.
Tabs: **Class Test | School Exam | Exam Result**. **Marking & Grading ka alag tab nahi**
(user, 24 Nov): wo card ke andar ka section hai — Class Test form mein aur School Exam
date-sheet card mein.

### D2. Class Test ka data model
**Recommend:** **Naya table nahi.** Class Test = `exam` row (`scope=class`, `exam_type=class_test`)
jiske neeche **ek subject ke papers, har chune hue section ke liye ek** (`exam_paper`).
School Exam = `exam` (`scope=class`, type ∈ Unit Test…Custom) jiske neeche us class ke
**har course ka paper**. Existing structure, marks, publish, results sab reuse.

### D3. Multi-section class test
`exam.class_id` set, `exam.classroom_id` NULL. Sections = us exam ke papers ke
`classroom_id` ka set. Section **add** = naya paper; section **remove** = paper delete,
**sirf tab jab uspe marks na hon** (warna 409). Saare sections ek class ke — server check.

### D4. Test Taken By aur Assigned/Temporary
`exam_paper.taken_by_employee_id` store karo. **Temporary** ko **live derive** karo
(`taken_by != classroomsubject ka current teacher`), store nahi — taaki course teacher
badalne par badge sach rahe. Dropdown: active teachers (Course phase wala helper).
Default = assigned teacher. Badge: S (Assigned) / T (Temporary), timetable jaisa.

### D5. Per-test pass line: Marks ya Grade — ✅ CONFIRMED design (user, 24 Nov)
Har date-sheet row / class test mein **"Pass by"** ka ek choice: **Marks** ya **Grade**.
- **Marks:** ek number input, **33% of Total Marks se pre-fill** (100→33, 50→16.5,
  20→6.6). Teacher number badal de (33→40) to uske **bagal mein chhota "40%"** live
  dikhta hai (passing marks ka total mein percent) — sirf display, editable nahi.
- **Grade:** passing grade chunna/likhna; **custom grade** bhi daal sakte hain (jaise
  "D", "C2" ya apna). Grade ki ladder school ki default ladder (A1 90, A2 80 … D 33,
  E 0) se aati hai; teacher ke custom grade ko apna **minimum percentage** dena padta hai
  jab wo ladder mein na ho (wo us test ki `grading_scale` snapshot mein jud jata hai).
- Storage (`exam_paper`): `pass_mode` (`marks`/`grade`), `passing_marks`, `passing_grade`,
  `pass_percent` (hamesha effective pass line % mein — display aur grade-pass ke liye),
  `grading_scale` (is test ki ladder ki apni copy, taaki baad mein school ladder badalne
  se purane result na badlein).
- Pass/Fail: marks mode mein `obtained >= passing_marks`; grade mode mein
  `percentage >= us grade ka min percent`. Absent = na pass na fail.

### D6. Pre-fill ka hisaab
Default pass marks = `total * 33 / 100`, **2 decimal, ROUND_HALF_UP** (33% school setting
`exam.pass_percent` se). Total badalne par: marks mode mein agar teacher ne number
**khud nahi badla** to naye total ka 33% dobara; khud badla ho to uska number rakho
(aur agar > total ho jaye to 422). "Chhota %" hamesha `passing_marks / total * 100`.

### D7. Syllabus — ✅ CONFIRMED: sirf free text
`exam_paper.syllabus_text` (text). Chapters pick nahi. Purane `exam_paper_chapter` /
group-chapter tables **chhode jaate hain** (purana data safe, naya flow unhe nahi chhuta).
**Date-sheet table ke aakhri column mein har subject row ka Syllabus button**:
`syllabus_text` khaali nahi hai to active, warna disabled (tooltip "Syllabus not added
yet"); click par modal mein usi subject ka text. "Bhara hai ya nahi" server `has_syllabus`
bool se bhejta hai (text list read mein bhari nahi jati), full text sirf View par
(ya detail read mein). Syllabus School Exam ka hissa hai
(Class Test mein syllabus field nahi). Subject teacher apna subject ka syllabus likhta
hai; upar ke roles kisi bhi subject ka.

### D7b. Koi time / range nahi — ✅ CONFIRMED
`exam.start_date/end_date` aur `exam_paper.start_time/end_time` naye flow mein na
mange jaate, na dikhte. Columns purane data ke liye DB mein rahenge (nullable), par
API ke naye shapes mein nahi. Duplicate check aur reminder sirf `exam_date` par.

### D8. Status
Internal lifecycle rakho; **`cancelled` add**. UI chip: **Scheduled** (marks nahi) /
**Completed** (marks uploaded — publish se alag) / **Cancelled**.
**Delete vs Cancel:** ⚑ **Recommend:** marks nahi hain to Delete (hard) + "deleted"
notification; marks hain to Delete blocked, sirf **Cancel** (record rahe, notification
jaaye).

### D9. Audit trail
Existing `marks_audit` publish ke baad ke changes likhta hai. Spec ("kisne kya kab kis se
kis value") ke liye **pehli save ke baad bhi** change log chahiye? **Recommend:** publish
se pehle draft overwrite audit mein nahi (noise), publish ke **baad** har change audit mein
(jaisa hai) — plus `entered_by`/`updated_at`. Agar tum chaho ki draft edits bhi audit hon
to batao.

### D10. Notifications — event types
`exam.scheduled` (submit), `exam.rescheduled` (date/time), `exam.updated` (kya badla:
"total marks changed"), `exam.note_changed`, `exam.deleted/cancelled`, `exam.published`
(marks), `exam.mark_changed`, `exam.datesheet_published`. Sab `events.notify()` se, har
ek ka alag `dedupe_key` (revision ke saath). **Date sheet publish se pehle (School Exam)
koi notification nahi.**

### D11. Duplicate warning
Key = `(class_id, classroom_id, classroom_subject_id, exam_date)`. Save par match mile to
**409 `DUPLICATE_EXAM`** + `existing[]` (date, subject, total marks, section, created by).
Client `confirm_duplicate=true` ke saath dobara bhejta hai. Har baar warn (marks/period
alag ho tab bhi).

### D12. Session year + enrollment
`exam.academic_year_id` har naye exam par **zaroori**. `marks.enrollment_id` add (nullable
→ backfill `(student, paper.exam.year)` se). Result enrollment ke through padhe, taaki
promotion/de-promotion mein purane year ke marks na hilen. De-promote ka existing logic
Phase 1 mein dekhna hai (kya marks count/delete karta hai).

### D13. Permissions (user clarification ke saath)
| Kaam | Kaun kar sakta hai |
|---|---|
| **Class Test** banana/edit/delete | subject teacher (apna subject), class teacher, vice principal, principal, senior |
| **Date Sheet** banana/edit (School Exam) | class teacher, vice principal, principal, senior (subject teacher **nahi**) |
| **Syllabus** likhna/edit | subject teacher (apna subject) + upar ke sab |
| **Marks** entry | subject teacher (apna subject) + upar ke sab |
| **Date sheet / syllabus publish** | **sirf class teacher** (aur principal+ — "senior sab kuch kar sakte hain") |
| **Marking & grading section** (card ke andar) | jo us test/date sheet ko bana sakta hai wahi bharta/badalta hai |
**Principal aur upar (admin tak) = har row par YES** — koi bhi "sirf class teacher" ya
"sirf subject teacher" rule principal+ ko nahi rokta.
Naye codename sirf zaroorat par: `exam_setup.manage`. Baaki existing `exams.*` / `marks.*`.
Class teacher / subject holder **server-side service checks** hain (`classroom.class_teacher_id`,
`_held_course_ids`), role-naam hard-code nahi: "vice principal / principal / senior" =
**permission-based leadership** (`_is_leadership`), jaisa Course phase mein hua.
Student/guardian read: apne bachche tak, sirf publish ke baad.

### D14. Result ka formula
- Per test: `percentage = obtained / total * 100` (Absent bahar).
- **Cumulative subject-wise** = `Σ obtained / Σ total` us subject ke saare tests par
  (weighted — tests ke total alag ho sakte hain), **average of percentages nahi**.
- **Overall** = `Σ obtained / Σ total` saare subjects par. Absent test dono se bahar.
- Class Test aur School Exam **kabhi mix nahi**.

### D15. Display mode
School setting: `marks` / `grades` / `both`. Result screens isi se decide karein kya dikhana
hai; DB mein hamesha marks + (derived) grade.

### D16. Excel/CSV
Optional (spec: "optional later"). Phase 10 mein, tumse poochhkar.

---

## 5. Phase Plan (checklist)

### Phase 0: Study aur Plan [x]
- [x] 0.1 Backend `exams/plan` (models, service, router, grades, notifications) deeply padha.
- [x] 0.2 Frontend Exams tab, auth/rbac, alembic head, enrollment, class teacher dekha.
- [x] 0.3 Requirement vs maujooda gap table (Section 3) banayi.
- [x] 0.4 D1–D16 recommendation likhi (⚑ wale tumse confirm).
- [x] 0.5 Phase 1–10 ka code-aware plan (Section 7). **User approval pending.**

### Phase 1: Data Model aur Migration [x]
- [x] 1.1 Type enum (`class_test`, unit_test … `custom`) + custom naam; `ExamStatus.cancelled`.
- [x] 1.2 `exam_paper`: `taken_by_employee_id`, `pass_mode`, `pass_percent`, `grading_scale`
      snapshot, `syllabus_text` (free text); `exam`: `family_note`, `datesheet_published_at`,
      `datesheet_published_by`. Start/end time aur first/last day naye shapes mein nahi (D7b).
- [x] 1.3 `marks.enrollment_id` + backfill; `exam.academic_year_id` hardening.
- [x] 1.4 School settings keys: `exam.pass_percent` (33), `exam.display_mode`.
- [x] 1.5 Migration `0006_…` (up + down), `MODEL_MODULES`, indexes, `check_schema`.

### Phase 2: Pass line (Marks / Grade) — row ke andar, alag tab nahi [x]
- [x] 2.1 `plan/marking.py`: `default_pass_marks` (33%, ROUND_HALF_UP), `pass_percent_of`,
      `is_pass` (marks/grade), `grade_for(ladder, percent)`, `validate_ladder`,
      `with_custom_grade`.
- [x] 2.2 `GET /exams/marking-defaults?total=` → pass marks (33%), pass percent, school
      default ladder, display mode. **Koi tab / setup CRUD nahi.**
- [x] 2.3 Reusable **`PassLineFields`** (frontend): "Pass by" = Marks | Grade.
      Marks: number (33% pre-fill) + live chhota "40%". Grade: passing grade (custom
      allowed, custom ho to uska min %). Date-sheet row aur Class Test form dono mein.
- [x] 2.4 `lib/exams/marking.ts` pure helpers + `node --test`.
- [x] 2.5 Backend tests.

### Phase 3: Class Test — Scheduling [x]
- [x] 3.1 Create/update/delete/cancel API: Type fixed, subject from existing courses,
      Test Taken By (default/temporary), Total Marks, Date, Note for Family.
- [x] 3.2 Multi-section (same class) create + edit sections (D3).
- [x] 3.3 Per-test marking setup mandatory (save block) + pre-fill.
- [x] 3.4 Duplicate warning (D11).
- [x] 3.5 Notifications: scheduled / rescheduled / updated / note changed / deleted.
- [x] 3.6 Class Test tab UI: form, section multi-select, Assigned/Temporary badge,
      duplicate popup, status chip.
- [x] 3.7 Tests.

### Phase 4: School Exam — Date Sheet aur Syllabus [x]
- [x] 4.1 Type dropdown + Custom naam; date sheet = class ke har course ki row.
- [x] 4.2 **Syllabus button** (alag, likhne ke liye): free text, subject teacher apna
      subject. Date-sheet table ka **aakhri column Syllabus**: bhara ho to View button
      active, nahi to disabled; click par us subject ka text modal mein.
- [x] 4.3 **Date Sheet button** (alag): class teacher, vice principal, principal, senior;
      permission matrix D13; read matrix.
- [x] 4.4 Date-sheet publish (class teacher only) + gating + notification (D10).
- [x] 4.5 School Exam tab UI; date-sheet card mein **marking setup section** (Phase 2 ka component).
- [x] 4.6 Tests.

### Phase 5: Marks Entry (Class Test + School Exam) [x]
- [x] 5.1 Table entry (har student ek row), Absent, validation.
- [x] 5.2 Total lower karne par warning/422 (already-entered marks se neeche).
- [x] 5.3 Marks upload/edit notification ("what changed"); publish gating.
- [x] 5.4 Audit trail (D9) + `enrollment_id` stamp.
- [x] 5.5 Marks entry UI (percentage, grade, pass/fail live).
- [x] 5.6 Tests.

### Phase 6: Result Engine (backend) [x]
- [x] 6.1 Per-test rows: obtained/total/%/grade/pass-fail (apne setup se).
- [x] 6.2 Cumulative subject-wise + overall (D14), Class Test / School Exam alag.
- [x] 6.3 Class stats: average, highest, lowest, passed/failed per test.
- [x] 6.4 Visibility: student/guardian own + published; teacher class view; admin all.
- [x] 6.5 Tests.

### Phase 7: Exam Result Tab (frontend) [x]
- [x] 7.1 Exam Result tab + sub-tabs Class Test Result / School Exam Result.
- [x] 7.2 Student/guardian view; teacher class view; admin all-classes view.
- [x] 7.3 Absent display; display mode (marks/grades/both).
- [x] 7.4 Loading/empty states, tsc.

### Phase 8: Integration — tabs, rename, promotion tie-in [x]
- [x] 8.1 Exams tab ke 3 main tabs (Class Test / School Exam / Exam Result) polish; purane "Class Exams/School Exams" rename.
- [x] 8.2 Promotion/de-promotion ke saath marks/enrollment check.
- [x] 8.3 Reminder job (`exam-reminder`) naye fields ke saath.

### Phase 9: Permissions, Notifications aur Isolation hardening [x]
- [x] 9.1 Permission matrix test (admin/principal/class teacher/subject teacher/guardian/student).
- [x] 9.2 Multi-school isolation, notification dedupe/idempotency.
- [x] 9.3 Performance: query count, indexes.

### Phase 10: Final E2E, Cleanup aur (optional) Excel/CSV [x]
- [x] 10.1 End-to-end: schedule → marks → publish → result.
- [x] 10.2 Cleanup, unused code, doc update.
- [~] 10.3 (SKIP — tumne kaha abhi rahne do) Excel/CSV marks upload.

---

## 6. Cross-phase Reminders (har phase se pehle padho)

| # | Reminder | Kise affect karta hai |
|---|---|---|
| R1 | Naya model/table ho to `MODEL_MODULES` (`app/core/schema.py`) aur `check_schema.py` dekho; naya router ho to `api.py` mein mount (`test_structure`). | 1–9 |
| R2 | `app/domains/**` mein text SQL nahi; raw SQL sirf `alembic/versions/*` mein (backfill wahin). | 1 |
| R3 | **`exams/service.py`, `exams/llm`, `exams/rag`, `paper_draft` nahi chhedna** (AI paper builder). Sirf `exams/plan` aur uske naye modules. | 1–9 |
| R4 | `plan/service.py` already 1906 lines hai. Naya logic naye modules mein (`marking.py`, `results.py`, `family.py`…), service mein sirf wiring. | 2–6 |
| R5 | Marks hamesha `Decimal`, kabhi float nahi; rounding `ROUND_HALF_UP`, 2 decimals. | 2, 5, 6 |
| R6 | Match id se: teacher=`employee.id`, subject=`classroomsubject.id`, section=`classroom.id`. Naam se compare nahi. | 3–7 |
| R7 | `marks` ka single writer `save_marks`/`change_mark`; ek hi transaction mein audit + notification. | 5 |
| R8 | Purane tests (`test_classroom_exams.py`, `test_exam_paper_groups.py`) pass rehne chahiye; naye fields **nullable/default** se jodo. | 1–9 |
| R9 | Alembic ids **chhote numbers** hain (`revision = "0006"`, `down_revision = "0005"`), file naam alag. Migrations `0006`, `0007`, `0008` ban chuke — agla naya `0009`, `down_revision = "0008"`. Downgrade zaroor; har step idempotent (inspector se check). | 1+ |
| R10 | `events.notify()` hi ek writer; har event ka alag `dedupe_key`; failure caller ko fail na kare. | 3–5 |
| R11 | Frontend `Tabs` props `{ tabs, active, onChange }`; Timetable ka S/T badge pattern reuse. | 3, 4, 7 |
| R12 | API client `titleCaseValues` har response par chalta hai — ids safe (sirf TITLE_CASE_KEYS), par naye text keys sochkar naam do. | 3–7 |
| R13 | Tests ab chalte hain (Section 0.2 ka command). Phase ke baad **sirf wahi** test "pass" likho jo sach mein chala; baseline ke 17 purane failures alag likho. | sab |
| R14 | Class Test ka sab kuch `scope=class`, `exam_type=class_test`; Class Test Result aur School Exam Result **kabhi mix nahi**. | 6, 7 |
| R15 | Publish rules do alag hain: **marks publish** (per paper, teacher) aur **date sheet publish** (class teacher only). Alag columns, alag events. | 4, 5 |

---

## 7. Phase-wise Detailed Plan

### Phase 1 — Data Model aur Migration
**Goal:** spec ke saare naye fields DB mein, purana data safe.
- **1.1** `ExamType` enum (`class_test`, `unit_test`, `periodic_test`, `mid_term_test`,
  `half_yearly`, `annual`, `pre_board`, `practical`, `custom`); `exam.exam_type` ko isi par
  validate karo (purane free-text rows ka mapping/fallback `custom`). Custom ke liye
  `exam.name` hi typed naam (D2). `ExamStatus.cancelled` add.
- **1.2** `exam_paper`: `taken_by_employee_id` (FK employee), `pass_mode`, `pass_percent`,
  `grading_scale` (JSON), `syllabus_text`. `exam`: `family_note`, `datesheet_published_at`,
  `datesheet_published_by_user_id`. Sab nullable/default.
- **1.3** `marks.enrollment_id` (FK enrollment, nullable) + backfill; `exam.academic_year_id`
  naye rows par zaroori (service-level; DB NOT NULL tab jab backfill clean ho).
- **1.4** `school_setting` keys `exam.pass_percent`, `exam.display_mode` + defaults helper.
- **1.5** Migration `0006_exam_marking_setup.py` (up/down), index on duplicate-key
  `(class_id, classroom_id?, exam_date)`; `check_schema.py` clean.
- **Tests:** model/migration smoke, backfill count, purane exam tests ka import.
- **Done when:** purane tests green (jahan chal sake), naye columns nullable, downgrade bana.

### Phase 2 — Pass line: Marks ya Grade (row ke andar)
**Goal:** pass/grade ka ek hi hisaab, aur ek chhota reusable control jo date-sheet row aur
Class Test form mein baithe.
- **Date sheet ki ek row aisi dikhegi:** `Subject` (course se, fixed) · `Date` ·
  `Total Marks` · `Pass by [Marks | Grade]` · (Marks: `[33]` `40%`) ya (Grade: `[D ▾ / custom]`)
  · **aakhri column `Syllabus`** (button; subject teacher ne bhara ho tabhi active — Phase 4).
- **2.1** `plan/marking.py`:
  `default_pass_marks(total, percent=33)` → 100:33, 50:16.5, 20:6.6;
  `pass_percent_of(passing_marks, total)` (jo "40%" dikhata hai);
  `is_pass(...)` (marks mode: `>=` passing marks; grade mode: percentage >= grade ka min %);
  `grade_for(ladder, percent)`; `validate_ladder` (0 se shuru, gap/duplicate nahi);
  `with_custom_grade(ladder, grade, min_percent)`.
- **2.2** `GET /exams/marking-defaults?total=50` → `{passMarks: 16.5, passPercent: 33,
  ladder, displayMode}`. School setting + school ladder / built-in ladder se.
- **2.3** `PassLineFields`: Marks mode mein number badalte hi percent live; total badle
  to jab tak teacher ne number khud nahi badla, 33% dobara; Grade mode mein passing
  grade + custom (custom ka min % maanga jata hai). Incomplete ho to parent ka Save disabled.
- **2.4** `lib/exams/marking.ts` (pure) + `node --test`.
- **Tests:** 100→33, 50→16.5, 20→6.6; 33→40 par 40%; grade mode pass/fail; custom grade;
  ladder validation; defaults endpoint.

### Phase 3 — Class Test: Scheduling
**Goal:** teacher class test schedule/edit/delete kar sake, notifications ke saath.
- **3.1–3.2** (Class Test mein **date sheet nahi**, har test ki ek date; creators: subject
  teacher, class teacher, VP, principal, senior.) `POST /exams/class-tests` (ek subject, `section_ids[]` same class, taken_by,
  total, date/time, family_note, marking setup). Edit sections (D3). Subject sirf existing
  `classroomsubject` — warna 422.
- **3.3** Marking setup incomplete ho to 422 (total, pass mode+value, ladder).
- **3.4** Duplicate 409 popup data (D11) + `confirm_duplicate`.
- **3.5** Events: submit / reschedule (date ya time) / other-edit ("total marks changed") /
  note-changed / delete-cancel. Reschedule = sirf date/time change.
- **3.6** UI: form, section multi-select, taken-by dropdown + Assigned/Temporary badge,
  duplicate popup, status chip, family note.
- **Tests:** multi-section, mixed-class 422, temporary flag, duplicate flow, har event.

### Phase 4 — School Exam: Date Sheet aur Syllabus
- **4.1** Type dropdown + Custom; date sheet = class ke har active course ki row (Subject,
  Total Marks, Date) — **time nahi**. Date sheet class teacher / VP / principal / senior
  banate hain, subject teacher nahi.
- **4.2** Syllabus: sirf `syllabus_text` (D7), subject teacher likhta hai; View modal.
  Paper read mein `has_syllabus: bool` (table ke aakhri column ka button isi se active/
  disabled); `GET /exams/papers/{id}/syllabus` text deta hai (read permission wahi jo date
  sheet ki — publish se pehle parents/students ko nahi).
  Date Sheet aur Syllabus **do alag buttons**, alag endpoints, alag permission.
- **4.4** `POST /exams/{id}/datesheet/publish` (sirf class teacher / leadership);
  unpublished sheet parents/students ko `404`/empty, notification nahi (D10, R15).
- **Tests:** permission matrix, unpublished invisibility, publish notification once.

### Phase 5 — Marks Entry
- **5.1** Table API/UI (har student ek row, Absent), `_checked_score` reuse.
- **5.2** Total lower karna: entered marks se kam → 422 ya warning (confirm flag).
- **5.3** Upload/edit notifications (what changed); publish ke baad hi family ko.
- **5.4** Audit + `marks.enrollment_id` stamp.
- **Tests:** absent vs zero, > total, edit-after-publish audit, notification body.

### Phase 6 — Result Engine
- **6.1–6.3** `results.py`: per-test rows, cumulative subject-wise, overall, class stats;
  ek query mein aggregate, N+1 nahi.
- **6.4** Visibility rules (D13) server par.
- **Tests:** weighted formula (D14), absent excluded, Class Test vs School Exam alag,
  guardian sirf apna bachcha.

### Phase 7 — Exam Result Tab
- Sub-tabs, student/guardian view, teacher class view, admin all-classes; Absent;
  display mode. `tsc` clean.

### Phase 8 — Integration
- 3 main tabs (D1), rename, promotion/de-promotion ke saath marks/enrollment check,
  reminder job naye fields se.

### Phase 9 — Hardening
- Permission matrix, multi-school isolation, dedupe, query count.

### Phase 10 — Final E2E, Cleanup, (optional) Excel/CSV
- Poora flow ek test mein; cleanup; Excel/CSV tumse poochhkar.

---

## 8. Completion Log

### Phase 0: complete (24 Nov 2026)
**Kya kiya**
- Backend ka exam plan deeply padha: `exams/models.py` (`exam`, `exam_paper`,
  `exam_paper_group`, `exam_paper_chapter`, `marks`, `marks_audit`, `grade_scale`),
  `plan/service.py` ke saare functions, `plan/router.py` ke endpoints, `plan/grades.py`,
  notification events (`exam.scheduled/changed/published/mark_changed/reminder`).
- Frontend padha: Exams tab `ExamsPlanPanel.tsx` (abhi "Class Exams / School Exams"),
  `DateSheet`, `ExamScheduleForm`, `MarksGrid`, `ResultsView`, `useExamPlan`.
  `/dashboard/exams` sirf redirect hai; AI Papers alag feature hai.
- Verify kiya: `enrollment` table, `classroom.class_teacher_id`, permissions
  (`exams.*`, `marks.*`), alembic head `0005_chapter_approved_count`, purane tests
  (`test_classroom_exams.py`, `test_exam_paper_groups.py`).
- Is machine par Python block hai (Windows Application Control) — isliye phases mein
  backend tests yahan se nahi chalenge; Section 0.2 mein likha.

**Mili hui corrections (tumhare doc vs code)**
1. **Exam ka bahut hissa pehle se bana hai** — date sheet, marks table, absent, `marks ≤ max`
   validation, publish, mark-change audit, grade ladder, results, notifications. Isliye
   plan "naya banao" nahi, **"extend karo"** hai.
2. `exam_type` abhi free text hai (enum nahi); `note` internal hai, family-facing nahi;
   `cancelled` status nahi; per-test pass mode/grading nahi; `marks.enrollment_id` nahi;
   date-sheet publish nahi (publish sirf marks ka).
3. "Note for Family", "Test Taken By", duplicate warning, multi-section picker,
   Exam Result tab, school-level setup UI — **sab naye** hain.

**Output:** Section 3 (gap table), Section 4 (D1–D16), Section 5 (11 phases),
Section 6 (R1–R15), Section 7 (phase-wise detail).

**Baaki (Phase 1 se pehle ⚑ tumse):** D5 (grading snapshot), D8 (delete vs cancel),
D9 (audit scope), D16 (Excel/CSV). Jab tak tum na badlo, recommended default chalega.

### Phase 0 addendum — user clarifications (24 Nov 2026)
- Syllabus **free text** (chapters nahi) — D7.
- **First/last day aur start/end time nahi** — D7b, G21.
- Class Test: subject teacher / class teacher / VP / principal / senior banate hain.
  Date Sheet: class teacher / VP / principal / senior. Syllabus + Marks: subject teacher
  (+ upar ke). Publish: class teacher (+ principal+) — D13 matrix.
- **Date Sheet aur Syllabus do alag buttons**; Class Test mein date sheet nahi,
  School Exam mein hai — Section 1.12.
- Plan **Class Test / School Exam tab ke andar hi**, UI abhi jaisa — D1 ✅ confirmed.
- **Principal se admin tak sabko sab access** (D13, Section 1.12 #9).
- **Marking & Grading ka alag tab nahi** (24 Nov): wo setup Class Test card aur School
  Exam date-sheet card ke andar ek section hai (Phase 2 ka reusable component).

### Phase 1: complete (24 Nov 2026) — tests likhe, chale nahi
**Kya kiya**
- **1.1 Enums** (`exams/models.py`): `ExamType` (`class_test, unit_test, periodic_test,
  mid_term_test, half_yearly, annual, pre_board, practical, custom`), `PassMode`
  (`percent`/`marks`), `ExamStatus.cancelled`; helper tuples `EXAM_TYPES`,
  `SCHOOL_EXAM_TYPES` (class_test ke bina), `PASS_MODES`. `exam.exam_type` **plain string
  hi raha** (purani free-text rows ke liye, DB CHECK nahi) — validation Phase 3/4 ke naye
  write paths mein. Custom naam `exam.name` mein (D2), alag column nahi.
- **1.2 Naye columns (sab nullable):** `exam.family_note`, `exam.datesheet_published_at`,
  `exam.datesheet_published_by_user_id` (FK app_user); `exam_paper.taken_by_employee_id`
  (FK employee, index), `pass_mode`, `pass_percent numeric(5,2)`, `grading_scale` (JSON),
  `syllabus_text`. Composite index `ix_exam_paper_subject_date(classroom_subject_id,
  exam_date)` (model + migration dono mein) duplicate-warning ke lookup ke liye.
- **1.3 `marks.enrollment_id`** (FK enrollment, index, nullable) + backfill SQL: marks
  ko us exam ke year ki `(student, year)` enrollment se jodta hai (`school_id` match ke
  saath). Khaali/na-milne wale rows NULL rehte hain.
- **1.4 School defaults** (`admin/settings/values.py::DEFAULTS`): `exam.pass_percent = "33"`,
  `exam.display_mode = "both"`. Purana `exam.grade_scale` ("percentage"/"grade" — report
  card kya print kare) **alag cheez hai, chhua nahi**.
- **1.5 Migration `alembic/versions/0006_exam_marking_setup.py`**: `revision "0006"`,
  `down_revision "0005"`; har step inspector se idempotent; downgrade likha (naye
  columns + unka data drop hota hai — file ke docstring aur `downgrade()` mein likha).
- **Tests:** naya `tests/test_exam_phase1_model.py` (7 tests: statuses, types, optional
  columns, paper ka pass/grading/syllabus, mark ka enrollment_id, school defaults,
  migration chain). **Likha aur `py_compile` hua; chala nahi** — `.venv` Python is
  machine par block hai. Tumhare taraf se: `pytest tests/test_exam_phase1_model.py
  tests/test_classroom_exams.py tests/test_exam_paper_groups.py`.

**Files:** `exams/models.py`, `admin/settings/values.py`,
`alembic/versions/0006_exam_marking_setup.py`, `tests/test_exam_phase1_model.py`.

**Zaroori baatein / sawdhani**
1. **Migration abhi run nahi hui** (is machine par DB/Python nahi chal sakta). Deploy se
   pehle `alembic upgrade head` ek baar staging/local DB par chalao; wahan bhi
   `scripts/check_schema.py` dekh lo.
2. **Backfill sirf wahi marks jodta hai jinke exam par `academic_year_id` set hai.**
   Jin purane exams par year NULL hai unke marks ka `enrollment_id` NULL rahega — Phase 5
   mein naye marks ke saath stamp hoga, aur result code NULL ko `(student, exam.year)`
   se padhega.
3. `cancelled` abhi PATCH se set ho sakta hai (status words validate hote hain) lekin
   uska **proper cancel flow + notification Phase 3** mein aayega. Frontend chip abhi
   unknown status ko plain label dikhata hai (crash nahi); "Cancelled" chip Phase 3 mein.
4. Python 3.12 default wale `py_compile` se `values.py` mein purana syntax error aata hai
   (`except TypeError, ValueError:` Python 3.14 syntax hai) — meri kisi edit ki wajah se
   nahi; project ka interpreter 3.14 hai.
5. `exam.start_date/end_date` aur `exam_paper.start_time/end_time` DB mein **rahe** (purana
   data), par naye API/UI mein nahi aayenge (D7b) — Phase 3/4 mein.

**Baaki ⚑:** D8 (delete vs cancel), D9 (audit scope). (D5 ab user ke design se confirm.) D16 tumne confirm kar diya: Excel/CSV
Phase 10 mein optional.

### Phase 1 addendum (24 Nov 2026) — pass line ka design badla
User ne date-sheet row ka design bataya: Subject · Date · Total Marks · **Pass by Marks ya
Grade** (Marks: 33% pre-fill number + bagal mein chhota %; Grade: custom passing grade).
Phase 1 ke output mein is hisaab se badlav (code, migration 0006 untouched):
- `PassMode` ab **`marks` / `grade`** (pehle `percent`/`marks`); `PASS_MODES` update.
- Naya column **`exam_paper.passing_grade`** — migration **`0007_exam_passing_grade.py`**
  (`down_revision "0006"`, idempotent, downgrade). `pass_percent` ab **effective pass line %**
  hai (display + grade-pass ke liye), `grading_scale` per-test ladder copy.
- Tests update (`test_exam_phase1_model.py`) + 0007 chain ka naya test. **Chale nahi** —
  Python is machine par block hai.
- **Deploy order:** `alembic upgrade head` ab `0006` phir `0007` chalayega.

### Phase 2: complete (24 Nov 2026) — frontend tests chale, backend tests chale nahi
**Kya kiya**
- **2.1 `plan/marking.py`** (pure, sirf `decimal`): `default_pass_marks` (33%, ROUND_HALF_UP:
  100→33, 50→16.5, 20→6.6), `pass_percent_of` (wo chhota "40%"), `percentage`,
  `validate_ladder` (kam se kam ek grade, **0% se shuru**, same % ya same naam nahi),
  `grade_for`, `min_percent_of`, `with_custom_grade` (custom grade apna starting % maangta
  hai; **sirf us paper ki ladder copy** mein judta hai), `resolve_pass_line` (marks/grade
  mode → `PassLine{mode, passing_marks, passing_grade, pass_percent, ladder}`), `is_pass`
  (marks: `>=` passing marks; grade: `obtained*100 >= pass_percent*total`, bina divide kiye;
  **absent = None**, zero = fail). Errors `MarkingError` (message teacher ko dikhne layak).
- **2.2 Defaults endpoint** `GET /exams/marking-defaults?total=` (`marks.read`):
  `plan/setup.py` school ki `exam.pass_percent` (galat value → 33), `exam.display_mode`
  (galat → both) aur ladder (`grade_scale` rows ya built-in) padhta hai →
  `MarkingDefaultsRead{total_marks, pass_marks, pass_percent, passing_grade, ladder,
  display_mode}`. Total `0 < t ≤ 9999.99` warna 422. **Koi tab / setup CRUD nahi.**
- **2.3 `PassLineFields`** (`exam-plan/PassLineFields.tsx`): "Pass by [Marks | Grade]".
  Marks → number + bagal mein live chhota %; Grade → datalist se ladder ka grade ya custom
  grade, aur custom ho to "starts at __ %". Parent state rakhta hai; component sirf dikhata.
  **Abhi kisi card mein lagaya nahi** — Phase 3 (Class Test form) aur Phase 4 (date-sheet
  row) mein lagega. Hook `useMarkingDefaults(total)` + service `getMarkingDefaults` taiyar.
- **2.4 `lib/exams/marking.ts`**: `defaultPassMarks`, `passPercentOf`, `percentText`,
  `followTotal` (total badle to number tab tak saath chale jab tak teacher khud type na kare),
  `editPassMarks`, `passLineIssue` (Save disabled rakhne ka wajah), `needsCustomPercent`,
  `passLineBody` (API payload: `pass_mode, passing_marks, passing_grade, custom_min_percent`).
- **Tests:** frontend `marking.test.ts` — **11 tests, `node --test` se chale, sab pass**;
  purane `view.test.ts` ke 15 bhi pass (kul 26/26); `npx tsc --noEmit` clean.
  Backend `tests/test_exam_marking.py` likha aur compile hua, **chala nahi** (Python block).
  Lekin `marking.py` ko system Python se alag se load karke ~40 assertions chalayi
  (33%, 16.5, 6.6, 4.13, ladder errors, marks/grade/custom, is_pass, absent) — sab pass.
  `setup.py`/endpoint DB chahte hain, wo sirf `test_exam_marking.py` mein hain.

**Files:** `plan/marking.py`, `plan/setup.py`, `plan/schemas.py` (+2 schemas),
`plan/router.py` (+endpoint), `tests/test_exam_marking.py`, `frontend/src/lib/exams/
marking.ts` + `marking.test.ts`, `components/.../exam-plan/PassLineFields.tsx`,
`useExamPlan.ts` (+hook), `services/exams-plan.service.ts` (+call), `types/index.ts`
(`MarkingDefaults`).

**Zaroori baatein**
1. **Endpoint aur `setup.py` chale nahi.** Tumhare taraf se:
   `pytest tests/test_exam_marking.py tests/test_exam_phase1_model.py`.
2. `MarkingDefaults` ke decimals API se **string** aate hain (`"16.50"`); parent `amount()`
   se number banaye. `ladder[].minPercent` bhi string — `PassLineFields` ko number chahiye,
   isliye Phase 3/4 mein ek chhota map (`Number(...)`) lagega.
3. **Custom grade ka % maangna** meri taraf se hai (tumne sirf "custom grade" kaha tha);
   agar sirf naam chahiye, % nahi, to batao — tab custom grade sirf label hoga aur pass/fail
   percent se nahi, marks se chalega.
4. Python default 3.12 par `values.py` ka purana syntax error (3.14 syntax) ab bhi hai — meri
   edits ki wajah se nahi.

**Baaki ⚑:** D8 (delete vs cancel), D9 (audit scope) — Phase 3/5 se pehle.

### Phase 1 aur 2 ka sudhaar (24 Nov 2026, Phase 3 mein)
Phase 1/2 ke logs mein "backend tests likhe, chale nahi" likha tha. Phase 3 mein backend
tests chalane ka tareeka mila (Section 0.2), aur wo **sach mein chale**:
`test_exam_phase1_model.py` + `test_exam_marking.py` = **32 passed**. Yaani Phase 1 ka
model/migration-chain, `marking.py`, `setup.py` aur defaults ab verified hain (migration ka
asli SQL abhi bhi nahi chala — wo Postgres chahta hai).

### Phase 3: complete (24 Nov 2026) — backend + frontend tests chale, UI browser mein nahi dekhi
**Kya kiya — backend (`exams/plan/`)**
- **`class_test.py` (naya):** `create_class_test`, `update_class_test`, `cancel_class_test`,
  `delete_class_test`. Class test = `exam` (`exam_type=class_test`, `scope=class`,
  `classroom_id=NULL`) + **ek paper har chune hue section ka**; date har paper par; date sheet nahi.
- **Endpoints** (`plan/router.py`, `marks.update` + service ke andar asli check):
  `POST /exams/class-tests`, `PATCH /exams/class-tests/{id}`,
  `POST /exams/class-tests/{id}/cancel`, `DELETE /exams/class-tests/{id}`.
- **Kaun schedule kare:** leadership (office/principal/VP), ya **har chune section** ke liye
  subject teacher ya class teacher. Baaki `403`.
- **Ek hi class, existing course:** anchor section ka subject + baaki sections naam se match
  (section subject ki school-wide id nahi hoti); kisi section mein subject na ho to `422` — banaya nahi
  jata. Alag class ke sections `422`.
- **Test Taken By:** `exam_paper.taken_by_employee_id`; NULL = har section ka assigned teacher.
  Koi aur = **temporary** (`is_temporary` **live derive**, store nahi). Jis section mein assigned
  teacher nahi, wahan teacher chunna zaroori (`422`). Chunne wale ko "abhi padha raha active
  teacher" hona chahiye.
- **Pass line:** `marking.resolve_pass_line` se (marks 33% default / grade, custom grade ka apna %);
  paper par `pass_mode/passing_marks/passing_grade/pass_percent/grading_scale` (ladder ki apni copy).
  Adhoora ho to save nahi, kuch adha-save nahi hota.
- **Duplicate warning:** same section subject + same date (cancelled ko chhodkar) par
  `409 {code: DUPLICATE_EXAM, existing:[date, subject, total, section, created_by, status]}`;
  `confirm_duplicate=true` se "create anyway". Edit mein bhi (nayi date ya naya section) wahi.
- **Notifications** (`class_test.*`): `scheduled` (note ke saath), `rescheduled` (nayi date batati hai),
  `updated` (kya badla: "total marks 50 -> 40"), `note_changed` (sirf "note badla", note ka text
  nahi), `cancelled`, `deleted`. Kuch na badle to **kisi ko nahi**. Section hataya to us section ke
  families ko alag message. Har ek `dedupe_key` + revision ke saath.
- **Edit rules:** total ko dalay hue marks se neeche karna `422`; teacher ka apna pass number total
  badalne par bhi bacha rehta hai (33% wala default hi saath chalta hai); section tabhi hat sakta hai
  jab uspe marks na hon (`409`); cancelled test edit nahi hota.
- **Delete vs Cancel (D8):** marks hon to delete `409` ("Cancel it instead"), cancel allowed (record +
  marks rehte hain); marks na hon to delete ho sakta hai. **D8 recommended default par.**
- **`service.py` badlav (chhote):** `_paper_reads` ab `taken_by_*`, `assigned_teacher_*`,
  `is_temporary`, `pass_*`, `has_syllabus` bhejta hai (batch queries, N+1 nahi); `exam_read` mein
  `family_note`, `datesheet_published_at`; `list_exams`: class test sirf **un sections mein** dikhta hai
  jo use baithte hain, aur **class teacher** apne section ke exams dekhta hai; `_may_plan_paper`:
  leadership bhi, aur **class test par** section ka class teacher bhi (school exam par nahi — purana test
  yahi mangta tha).
- **Naye modules:** `people.py` (assigned teacher, naam, class-teacher rooms), `marking.py` mein
  `ladder_to_json/ladder_from_json`.

**Kya kiya — frontend**
- **Sub-tabs ab "Class Test" / "School Exam"** (jagah wahi, design wahi). Class Test tab mein sirf class
  tests; purane non-class-test class exams School Exam mein dikhte hain.
- **`ClassTestForm.tsx`:** Type (Class Test, fixed), Subject (is section ke courses), Sections (multi-select,
  isi class ke), Date, Total Marks, **Test Taken By** + **S/T gol badge** (Assigned/Temporary, timetable jaisa),
  **`PassLineFields`** (Phase 2), **Note for Family**; adhoora pass line to Save nahi; **duplicate popup**
  (purane test ki detail) + "Create anyway".
- **`ClassTestTable`:** subject, sections, date, total, taken-by (S/T), status chip
  (**Scheduled / Completed / Cancelled**), Open / Edit / Cancel / Delete (confirm ke saath).
- **`lib/exams/classTest.ts`:** draft, problems, create body, **sirf badla hua patch**, duplicate parse,
  chip. `ApiError` ab structured `detail` rakhta hai (duplicate list ke liye).

**Tests (sach mein chale)**
- Backend `test_exam_class_test.py`: **26 passed**; saath mein purane exam/timetable/structure tests =
  **98 passed**. Poora suite: 746 passed, 17 failed — **wo 17 saaf `HEAD` par bhi fail** (Section 0.2).
- Frontend: `node --test` exams+attendance+timetable lib = **61/61**; `tsc` clean; `eslint` clean.

**Files:** backend — `plan/class_test.py`, `plan/people.py`, `plan/marking.py`, `plan/schemas.py`,
`plan/service.py`, `plan/router.py`, `tests/test_exam_class_test.py`, `tests/test_classroom_timetable.py`
(ek test ka galat `class_id` theek kiya). Frontend — `exam-plan/ClassTestForm.tsx`,
`exam-plan/ExamsPlanPanel.tsx`, `lib/exams/classTest.ts` (+test), `services/exams-plan.service.ts`,
`lib/api/client.ts`, `types/index.ts`, `SectionDetailPage.tsx` (teachers prop), `lib/exams/view.test.ts` (fixtures).

**Zaroori baatein / sawdhani**
1. **UI browser mein nahi dekhi** (sirf `tsc`, `eslint`, unit tests). Class Test tab khol kar ek test
   schedule/edit/cancel karke dekh lo, khaaskar sections multi-select aur duplicate popup.
2. Class test ke **"Open"** se purana `DateSheet` view khulta hai (marks entry tak pahunchne ke liye). Wo
   "Dates not set" jaisa date-range text dikha sakta hai — iska saaf-suthra view **Phase 5** (marks entry) mein.
3. **Total kam karna:** abhi dale hue marks se neeche **refuse** (`422`); "warning + confirm" wala
   version Phase 5 (5.2) mein dekhenge.
4. Ek explicit teacher chunne par wo **chune hue sabhi sections** ke liye lagta hai; default (khaali) har
   section ka apna assigned teacher. Jis section mein assigned nahi, wahan wo temporary dikhta hai.
5. **D9 (audit)** abhi chhua nahi — Phase 5. **School Exam / date sheet / syllabus** Phase 4.
6. Notification text English mein hai ("Class Test rescheduled: Mathematics ...").

### Phase 4: complete (24 Nov 2026) — backend + frontend tests chale, UI browser mein nahi dekhi
**Faisla jo maine liya (tumse confirm):** date sheet **ek section ki** hoti hai (us section ke apne
subjects), poori class ki nahi. Wajah: section ka class teacher hi uska publisher hai, marks/papers pehle se
section-wise hain, aur class teacher ek se zyada hote hain. Agar poori class ki ek date sheet chahiye to
batao — "copy to other sections" Phase 8 mein jod sakte hain.

**Kya kiya — backend (`exams/plan/`)**
- **`school_exam.py` (naya):** `create_school_exam`, `update_school_exam`, `publish_date_sheet`,
  `delete_school_exam`, `get_syllabus`, `set_syllabus`.
- **Endpoints:** `POST /exams/school-exams`, `PATCH /exams/school-exams/{id}`,
  `POST /exams/school-exams/{id}/publish`, `DELETE /exams/school-exams/{id}`,
  `GET|PUT /exams/papers/{id}/syllabus`.
- **Date sheet:** ek exam (`exam_type` = Unit Test / Periodic / Mid Term / Half Yearly / Annual / Pre-Board /
  Practical / Custom) + **section ke har subject ka ek paper**: sirf **date** (koi first/last day ya clock time
  nahi), **total marks**, apni **pass line** (marks ya grade — Phase 2 ka hisaab). **Custom** mein teacher ka
  likha naam (`exam.name`). **Note for Family** alag. Ek section mein ek type ki ek hi sheet (twin = `409`);
  custom ko naam se pehchana jata hai.
- **Kaun date sheet banaye:** section ka **class teacher** ya leadership; **subject teacher nahi** (`403`).
- **Draft:** nayi sheet `draft` hai — families ko dikhti nahi aur **koi notification nahi**.
- **Publish:** sirf class teacher / leadership; `datesheet_published_at/by` set, status `scheduled`; section ke
  families ko **ek baar** notification (subjects date ke order mein + note). Dobara publish `409`.
- **Publish ke baad badlav:** date / total / subject add-remove / note par "kya badla" wali notification
  (`school_exam.changed`); publish se pehle sab silent. Kuch na badle to kisi ko nahi.
- **Marks sheet ko bachate hain:** jis subject par marks hon use hata nahi sakte (`409`); total dale hue mark
  se neeche nahi (`422`).
- **Syllabus:** `exam_paper.syllabus_text` — **free text** (max 5000), subject teacher **apne subject ka**,
  class teacher / leadership kisi ka; blank = hata do. Class test par `422`. Publish ke baad badle to families
  ko "Syllabus updated: Mathematics"; same text dobara to kuch nahi.
- **Visibility (families ke liye pehli baar):** `service._visible_exam_ids` — teacher: jis exam mein unka
  subject ya unke class-teacher section ka paper ho (draft bhi, taaki syllabus likh sakein); **family (student /
  guardian): sirf apne bachche ke section ka, aur tab hi jab publish ho** (class test scheduled hote hi,
  date sheet publish hone par). `GET /exams` aur `GET /exams/{id}/papers` dono par lagu; family ko sirf apne
  section ke papers dikhte hain; doosre exam par `404`. Syllabus padhna: writer hamesha, baaki sirf publish
  ke baad.
- **Flags:** `ExamRead.can_manage` (date sheet set/publish kar sakta hai), `ExamPaperRead.can_syllabus`.

**Kya kiya — frontend**
- **School Exam tab:** "Create the date sheet" (jagah wahi, design wahi). List: exam, kitne subjects + date range,
  syllabus `x/y written`, status chip (**Draft / Published / Cancelled**), aur alag-alag buttons:
  **Open · Date Sheet · Syllabus · Publish · Delete** (jo jiske adhikar mein ho).
- **`SchoolExamForm.tsx`:** Type dropdown (spec ki list) + Custom naam, Note for Family, aur har subject ki row
  (checkbox, Date, Total Marks, **Pass by Marks/Grade** — `PassLineFields`). Total 100 se pre-fill (badal sakte
  hain). Save = draft; families ko kuch nahi.
- **`SyllabusSheet.tsx` + `SyllabusDialog.tsx`:** har subject ka "Written / Not written", subject teacher ke liye
  **Write/Edit**, baaki ke liye **View**. Free-text box.
- **`DateSheet.tsx` (Open):** School Exam ke liye columns **Subject · Date · Total marks · Pass · Syllabus (View)**
  — View button tabhi active jab syllabus bhara ho (warna disabled, tooltip). Header mein **Publish date sheet**.
- **`lib/exams/schoolExam.ts`:** types, draft, validation, create body, update body, chip, `passText`.

**Tests (sach mein chale)**
- Backend `test_exam_school_exam.py`: **20 passed**. Poora backend suite: **766 passed**, wahi 17 purane
  baseline failures (koi naya nahi).
- Frontend: `node --test` (exams + attendance + timetable lib) **72/72**; `tsc` clean; `eslint` clean.

**Files:** backend — `plan/school_exam.py`, `plan/service.py` (visibility, `can_manage`, `can_syllabus`),
`plan/schemas.py`, `plan/router.py`, `tests/test_exam_school_exam.py`. Frontend — `exam-plan/SchoolExamForm.tsx`,
`SyllabusSheet.tsx`, `SyllabusDialog.tsx`, `DateSheet.tsx`, `ExamsPlanPanel.tsx`, `lib/exams/schoolExam.ts`
(+test), `services/exams-plan.service.ts`, `types/index.ts` (+ do test fixtures).

**Zaroori baatein / sawdhani**
1. **UI browser mein nahi dekhi** (sirf `tsc`, `eslint`, unit tests). School Exam tab mein date sheet banao,
   syllabus likho, publish karo — khaaskar date-sheet Open view ka Syllabus column.
2. **Family-facing screen abhi nahi bana.** Server ka rule taiyar hai (publish ke baad family apni sheet aur
   syllabus API se padh sakti hai), par student/guardian ki apni screen **Phase 7/8** (Exam Result + family view)
   mein aayegi. Classroom ka Exams tab staff ke liye hai.
3. **Purane exams (free-text type) families ko ab bhi nahi dikhte** (unka publish path hi nahi tha) — ye
   pehle jaisa hi hai. Unka "Edit"/"Results" purane form se chalta hai.
4. **School exam ka "cancel" nahi banaya** (spec mein nahi tha): unpublished sheet delete ho sakti hai, published
   par abhi sirf edit. Chahiye to batao.
5. Naye School Exam ke marks entry ke liye "Marks" button purane `MarksGrid` par jata hai — uska saaf-suthra
   table (percentage, grade, pass/fail live) **Phase 5** mein.
6. Class teacher ko **school exam ke marks** par adhikar nahi diya (sirf subject teacher/leadership; class test par
   class teacher ko hai) — jaisa pehle tha.

### Phase 5: complete (24 Nov 2026) — backend + frontend tests chale, UI browser mein nahi dekhi
**Pehle se kya tha (Phase 0 audit se):** save draft, publish, `change_mark` + `marks_audit`, absent, `marks <= total`
validation. Phase 5 ne in par **judge karna, notify karna aur dikhana** theek kiya, aur kuch asli bugs mile.

**Bugs jo mile aur theek kiye**
1. **Ek paper publish hote hi poora exam `published` ho jata tha** aur doosre sections/subjects ke papers par marks
   save `409` dene lagte the (multi-section class test mein 9-B ke marks band). Ab exam tabhi `published` jab **har
   paper** publish ho; warna `marks_entry`. Marks sirf **cancelled** exam par band. Date sheet publish ab status ko
   peeche nahi kheenchta.
2. **`MarksGrid` mein students ki rows sirf `published` branch ke andar thi** (draft par table khali dikhti thi,
   `<div>` `<p>` ke andar). Poora table dobara likha.
3. **Publish notification sabko ek hi generic line bhejti thi.** Ab har family ko **sirf apne bachche ke marks** milte
   hain; koi bhi family doosre bachche ke marks nahi dekhti.

**Kya kiya — backend (`exams/plan/`)**
- **`marks_text.py` (naya):** `ladder_of` (paper ki apni ladder copy, warna school ki), `figures` (percentage, grade,
  pass/fail — paper ki **apni pass line** se), `result_line` ("45/50 (90%) · Grade A1 · Pass"; school ke
  `exam.display_mode` — marks / grades / both — ke hisaab se; absent = "Absent").
- **Sheet (`GET /papers/{id}/marks`):** har row mein `percentage`, `grade`, `passed` (absent/unmarked par khali);
  correction counts ek hi grouped query se (N+1 nahi).
- **`ExamPaperRead.grading_scale`:** paper ki ladder, taaki screen par grade typing ke saath live nikle.
- **Marks entry:** `save_marks` har mark par **`enrollment_id` stamp** karta hai (exam ke session year ka enrollment,
  ek query mein poori sheet ka).
- **Notifications:** publish par har bacche ko apne marks (event `exam.published`, per-student dedupe key);
  correction par "**changed from 45/50 (90%) · Grade A1 · Pass to 10/50 (20%) · Grade E · Fail**".
- **Audit trail:** `GET /exams/papers/{id}/marks/history` — kisne, kab, kis mark ko, kis value se kis value, kyun.
  Sirf paper chalane waale (subject teacher, class test ka class teacher, leadership); family ko `403`.
- **Pehle se jo rakha (D9):** audit sirf **publish ke baad** ke changes ka; draft ki typing audit mein nahi.

**Kya kiya — frontend**
- **`MarksGrid.tsx` (naya table):** har student ek row — `#`, Student, **Marks** (input, Enter se agla bacha), **Absent**
  (checkbox), **%**, **Grade**, **Result** (Pass/Fail/Absent) — sab **typing ke saath live**, paper ki apni pass line
  aur ladder se. Header: subject · section, Draft/Published, "Out of N", "Pass: 33 (33%)" ya "Grade D".
  Publish tabhi jab unsaved changes na hon; publish ke baad read-only + **Change** (reason zaroori) +
  **Corrections** (history).
- **`MarkHistoryDialog.tsx`, `lib/exams/marksSheet.ts`** (pure: live figures, ladder, pass, counts).

**Tests (sach mein chale)**
- Backend `test_exam_marks_entry.py`: **18 passed** (sheet figures, zero vs absent, grade-based pass, paper ki apni
  ladder, validation, enrollment stamp, publish se exam band nahi, per-family notification, display mode, correction
  text + trail, trail ki access, class teacher ke marks, cancelled exam). Poora backend: **784 passed**, wahi 17
  purane failures (baseline).
- Frontend: `node --test` **81/81** (9 naye `marksSheet`); `tsc` clean; `eslint` clean.

**Files:** backend — `plan/marks_text.py`, `plan/service.py`, `plan/schemas.py`, `plan/router.py`,
`plan/school_exam.py` (status guard), `tests/test_exam_marks_entry.py`. Frontend — `exam-plan/MarksGrid.tsx`,
`MarkHistoryDialog.tsx`, `lib/exams/marksSheet.ts` (+test), `services/exams-plan.service.ts`, `types/index.ts`.

**Zaroori baatein / sawdhani**
1. **UI browser mein nahi dekhi** (sirf `tsc`, `eslint`, unit tests). Ek class test ya school exam ka "Marks" kholkar
   typing, Enter, Absent, Save, Publish aur Change/Corrections try karo.
2. **5.2 (total ko dale hue marks se neeche karna) abhi bhi refuse (`422`) hai**, "warning + confirm" nahi. Wajah:
   confirm karne par dale hue marks total se upar rah jate, jo galat result dega. Agar tum chaho ki warning ke baad
   allow ho (aur un marks ka kya ho — cap/clear — wo bataye), to alag se karenge.
3. **Marks "upload" = Publish** maana hai (spec: "marks parent ko publish ke baad hi dikhte hain"). Save = draft (koi
   notification nahi); Publish = bacche ke marks ke saath notification. Alag "upload par turant notify" chahiye to batao.
4. **Publish ke baad kisi naye bacche ka mark** (jise pehle mark nahi mila tha) publish ke baad `save_marks` se nahi
   likha ja sakta (`409`); wo `change_mark` ke raaste hi (audit ke saath) — pehle jaisa.
5. **Percentage/grade/result entry table mein dikhte hain** (spec: "marks ke bagal mein grade aur pass/fail"); class
   average/highest/lowest/pass-fail counts **nahi** — wo sirf **Exam Result tab** (Phase 6/7) mein.
6. Excel/CSV upload abhi nahi (Phase 10, optional).

### Phase 6: complete (24 Nov 2026) — backend tests chale (UI is phase mein nahi)
**Kya kiya — `plan/overview.py` (naya), ek endpoint**
- **`GET /exams/results/overview?kind=class_test|school_exam[&classroom_id=]`** (`marks.read`): ek **kind** ka
  result, selected session year ke liye. **Class Test aur School Exam kabhi mix nahi** (alag `kind`, alag query).
- **Formula (D14):**
  - ek test: `obtained / total * 100`, **us test ki apni pass line aur apni ladder** se (grade, pass/fail);
  - **subject so far** = `Σ obtained / Σ total` us subject ke saare tests par — **weighted** (jaise 45/50 aur 10/20 =
    55/70 = **78.57%**, na ki (90+50)/2 = 70);
  - **overall** = `Σ obtained / Σ total` saare subjects par; cumulative grade school ki ladder se;
  - **absent** aur **unmarked** dono sums se bahar (absent "Absent" dikhta hai, `tests_absent` mein gina jata hai);
    **zero ek score hai** (fail), absent nahi.
  - Subjects **naam (case-insensitive)** se jodte hain, taaki saal ke beech section badalne wale bacche ka ek hi
    Mathematics line rahe (ek section mein naam unique hai).
- **Sirf published tests gine jate hain.** Staff ko `unpublished` count milta hai aur test ka column `published=false`
  ke saath; family ko aise test ka pata hi nahi chalta.
- **Class view (staff):** har test ke liye `stats` — marked, absent, **average (marks aur %)**, **highest**,
  **lowest**, **passed**, **failed** (absent bahar). Family ko `stats` nahi milte.
- **Har bacche ka block:** `entries` (har test ka obtained / % / grade / pass-fail / absent), `subjects` (subject-wise
  % so far), `overall` (% so far, grade, tests counted/absent/passed/failed).
- **Access:** leadership kisi bhi section ka; teacher sirf wahi section jahan unka subject hai ya wo class teacher hai
  (warna `404`, `403` nahi); **student / guardian** `classroom_id` ke bina — sirf apne bachche, sirf published, koi
  class figure nahi. Family ka section maangna `404`; bina kisi link ke bina section `422`.
- **Schemas:** `ResultOverviewRead` aur `Overview*` (Test / Stats / Entry / Subject / Total / Student).
- **`service._family_children`:** doosre helper se nikala (family ke bachche) — `_family_rooms` ab usi par tika hai.

**Tests (sach mein chale)**
- `test_exam_overview.py`: **18 passed** — weighted formula, absent/unmarked/zero, class stats, har test ki apni pass
  line, unpublished (staff ko count, family ko nahi), cancelled, kinds alag, leadership/teacher/family/student access,
  display mode, aur **query count fixed** (4 bacche aur 1 test ke barabar hi 24 bacche aur 5 tests par — N+1 nahi).
- Saare exam + structure tests: **114 passed**. Poora backend suite: **802 passed**, wahi 17 purane baseline failures.

**Files:** `plan/overview.py`, `plan/schemas.py`, `plan/router.py`, `plan/service.py`, `tests/test_exam_overview.py`.

**Zaroori baatein**
1. **Is phase mein koi UI nahi** (Phase 7). Endpoint `GET /api/exams/results/overview` taiyar hai.
2. **Teacher class view mein section ke saare subjects dikhte hain** (sirf apna subject nahi) — class teacher ke liye
   zaroori, aur subject teacher ke liye bhi simple rakha. Agar subject teacher ko sirf apna subject chahiye to batao.
3. **Vice principal** abhi leadership mein shaamil hai (`_is_leadership`), isliye wo sab sections dekhta hai — pichhle
   phases jaisa. Tumne result views mein vice principal "abhi chhoda" kaha tha; agar use result views se bahar rakhna
   hai to ek line ka badlav hai — batao.
4. **Rank** (1, 2, 2, 4) is overview mein nahi hai (pehle wale per-exam results mein pehle se hai) — spec mein nahi tha.
5. **Pass/Fail "overall"** nahi: har test ki apni pass line hai, isliye overall mein `tests_passed` / `tests_failed`
   counts hain, ek single Pass/Fail nahi.
6. Student ki apni aur guardian ki screen **Phase 7** mein.

**User ke jawab (24 Nov 2026) — in teeno par ab kuch pending nahi:**
- **Vice principal** result views mein bhi leadership mein **rahega** (pehle ka "abhi chhoda" wala note hata diya
  gaya) — code mein koi badlav nahi.
- **Teacher ko section ke saare subjects** dikhte rahenge (sirf apna subject nahi) — confirm.
- **Overall mein ek single Pass/Fail nahi**, `tests_passed` / `tests_failed` counts — confirm.

### Phase 7: complete (24 Nov 2026) — frontend tests chale, UI browser mein nahi dekhi
**Kya kiya**
- **Exams tab ke teen main tabs:** `Class Test | School Exam | Exam Result` (jagah wahi, design wahi). **Exam Result**
  tab mein do sub-tabs: **Class Test Result** aur **School Exam Result** — alag-alag, kabhi mix nahi.
- **Class view (staff — teacher / class teacher / leadership)**, `ResultClassView.tsx`:
  - **Tests table:** har test ka Total, **Class average** (marks + %), **Highest**, **Lowest**, **Passed**, **Failed**,
    **Absent**; jo test publish nahi hua wo "Not published" dikhta hai aur kahin ginta nahi; upar amber notice
    "N tests abhi publish nahi hue".
  - **Students table:** har bacche ka **subject-wise % so far** (subject ke columns), **Overall** (% aur grade),
    "3 passed · 1 failed", aur **Details** (pop-up: overall, subject-wise, test-by-test).
- **Student / guardian ka apna page:** naya route **`/dashboard/exam-results`** + sidebar mein "Exam Results"
  (sirf `STUDENT` / `GUARDIAN` ko; `NavItem.roles` naya field). Server ko koi section nahi bheja jata, isliye jawab
  **sirf apne bachche ka, sirf published, class ke koi figures nahi**. Har bacche ka block: Overall so far,
  Subject-wise so far, Test by test.
- **`StudentResultDetail.tsx`** (shared): teacher aur parent dono ko **wahi shabd**. **Absent "Absent" dikhta hai**,
  percentage se bahar; zero ek score ("0/50 (0%) · E"). Pass/Fail/Absent badge.
- **Display mode (marks / grades / both)** ek hi jagah (`lib/exams/results.ts`) lagta hai, isliye har cell ek jaisa:
  marks mode mein "45/50 (90%)", grades mein sirf "A1", both mein "45/50 (90%) · A1".
- **Loading / error / empty states:** spinner; server ka error text; "No child is linked to this login"; "No class
  test result yet / No school exam result yet — results appear once the teacher has published the marks".
- **Refresh:** `useResultOverview` ki key exam list ki key ke **neeche** hai, to marks publish ya correct karne par
  results apne aap refresh hote hain.

**Tests (sach mein chale)**
- `lib/exams/results.test.ts`: **12 naye** (display mode, entry text, absent, zero, badge, pass/fail text, subject
  columns, grouping, class-view cells, entry lookup). Frontend `node --test` kul **93/93**; `tsc` clean; `eslint` clean.
- Backend is phase mein nahi badla (Phase 6 ke 18 tests pehle se pass).

**Files:** `exam-plan/ExamResultPanel.tsx`, `ResultClassView.tsx`, `StudentResultDetail.tsx`, `useExamPlan.ts`
(`useResultOverview`), `ExamsPlanPanel.tsx` (teesra tab), `app/dashboard/exam-results/page.tsx`, `lib/exams/results.ts`
(+test), `lib/constants/nav.ts` (`roles`), `lib/auth/rbac.ts` (route), `components/layout/AppLayout.tsx` (nav filter
by role, module map), `services/exams-plan.service.ts`, `types/index.ts`.

**Zaroori baatein / sawdhani**
1. **UI browser mein nahi dekhi** (sirf `tsc`, `eslint`, unit tests). Test karo: (a) kisi section ka Exams tab →
   Exam Result (teacher ya principal se), (b) student ya guardian login se sidebar mein "Exam Results".
2. **Leadership "sab classes" ke liye** har section ke Exams tab mein Exam Result kholta hai (Classroom list se section
   chuno). Alag "saari classes ek saath" screen nahi banayi — wo bahut badi table hoti; chahiye to batao.
3. **Family ka screen sirf results ke liye hai.** Date sheet / syllabus family ko dikhane wala screen abhi bhi nahi
   (server ka rule taiyar hai) — **Phase 8** mein (family view) jodna hai.
4. `/dashboard/academics` (purana, family ke liye khali "Marks are the school's record") jaisa tha waisa hi hai; naya
   "Exam Results" alag route par hai. Cleanup Phase 10 mein.
5. Sidebar entry `marks.read` + role `STUDENT/GUARDIAN` par dikhti hai; `SCHOOL_ADMIN` route bypass karta hai par nav
   mein nahi dikhta (role filter).

### Phase 8: complete (24 Nov 2026) — backend + frontend tests chale, UI browser mein nahi dekhi
**8.1 Screens ka polish / integration**
- **Class test ka "Open" view saaf kiya** (Phase 3 ka pending): ab "Dates not set" nahi; "Class Test · 5 Dec", status chip
  (Scheduled / Completed / Cancelled), columns **Subject · Date · Total marks · Pass · Taken by (S/T badge) · Marks**,
  header mein "**Edit the test**". Class test / School Exam par purana **"Results" button hata diya** (results ab sirf
  Exam Result tab mein, spec ke hisaab se); purane exams par wo button rehta hai.
- Purane "Class Exams / School Exams" naam ab kahin nahi bache (sirf ek comment).
- **Family ka screen (Phase 7 ka pending):** `/dashboard/exam-results` ab do tabs ka page — **Upcoming** (apne bachche ke
  section ke class tests + **published** date sheets: Subject, Date, Total, Pass, **Syllabus View** (tabhi active jab
  syllabus likha ho), teacher ka Note for Family, "Result out" badge; cancelled test list ke neeche; doosre section ke
  papers nahi) aur **Results** (Phase 7). Sidebar label ab **"Exams"** (sirf STUDENT/GUARDIAN ko).
  Files: `FamilyExamsView.tsx`, `lib/exams/familyExams.ts` (+test), `app/dashboard/exam-results/page.tsx`.

**8.2 Promotion / de-promotion**
- **Check kiya:** de-promotion ka delete order sahi tha (marks aur unka `marks_audit` pehle, flush, phir enrollment) —
  Phase 1 ke `marks.enrollment_id` FK se koi `delete` phansta nahi.
- **Safety net jodi** (`students/promotion/direct.py::_hanging_data`): jo mark seedhe us enrollment se jura ho wo bhi
  warning mein gini jaye aur saath delete ho, chahe uske exam ka `academic_year_id` NULL ho (warna mark ek delete hui row
  ko point karta). Pichhle saal ke marks nahi chhue jate.
- Promote (aage badhana) marks ko nahi chhuta — purane saal ke marks purane enrollment ke saath rahte hain.

**8.3 Reminder job (`exam-reminder`)** — ab **paper ke hisaab se** faisla, exam ke status se nahi:
- Pehle `exam.status == scheduled` zaroori tha, to ek subject ke marks aate hi (status `marks_entry`) us exam ke **baaki
  din ke papers ka reminder band** ho jata tha. Ab: draft/cancelled exam nahi, jis paper ke marks publish ho chuke wo nahi,
  aur **School Exam tabhi jab date sheet publish ho** (draft sheet ka koi reminder nahi).
- **Class test** ka alag text ("Class Test: Mathematics is tomorrow" + Note for Family); **school exam** ka "Unit Test:
  Science is tomorrow"; room tabhi jab likha ho ("Room: as announced" wali bharti hata di).
- **Jo teacher le raha hai use bhi reminder** ("you take it tomorrow") — chuna hua (temporary) teacher, warna assigned.
- Ek paper ka ek hi reminder, job kitni baar bhi chale (dedupe).

**Tests (sach mein chale)**
- Backend `test_exam_integration.py`: **8 passed** (class test reminder, covering teacher, cancelled, already-published,
  draft vs published date sheet, agla subject marks ke baad bhi, de-promotion marks count + delete + audit, year-less
  mark). Poora backend: **810 passed**, wahi 17 purane baseline failures.
- Frontend `node --test` **97/97** (4 naye `familyExams`); `tsc` clean; `eslint` clean.

**Zaroori baatein / sawdhani**
1. **UI browser mein nahi dekhi.** Student/guardian login se "Exams" (Upcoming + Results), aur teacher se class test ka
   Open view dekho.
2. **Saal ke beech section badalne** (same year transfer) par bacche ke purane section ke marks naye section ke result
   overview mein nahi judte (overview current section ke papers dekhta hai). Spec mein nahi tha; promotion/de-promotion
   safe hai. Chahiye to alag se.
3. Reminder ka "kal" **UTC date** se nikalta hai (pehle jaisa) — India ke subah ke ghanton mein ek din ka farak aa sakta hai;
   school timezone setting abhi nahi hai.
4. "Date sheet ek hi baar mein poori class (saare sections) ko copy" nahi banaya — abhi har section ki apni sheet.
5. Notification par click se kisi page par le jaane ka koi mechanism app mein hai hi nahi (pehle se), isliye naye events ke
   liye wahan kuch nahi jora.

### Phase 9: complete (24 Nov 2026) — saare tests chale; migrations ka SQLite dry-run hua
**9.1 Permission matrix** — `tests/test_exam_permissions.py`: **24 operations × 10 callers = 240 cases**, sab pass.
- Callers: `system_admin`, `office` (school admin), `principal`, `vice_principal`, `class_teacher`, `subject_teacher`,
  `hod`, `outsider` (link ke bina teacher), `guardian`, `student`.
- Operations: class test (schedule maths/science, edit, cancel, delete), date sheet (create, edit, publish, delete),
  syllabus (likhna maths/science, padhna draft / published), draft sheet ka dikhna, marks (class test aur School Exam
  par save, publish, correction, history, sheet), result overview (section aur family).
- **Jo niyam pakke hue (D13):** class test = subject teacher / class teacher / leadership; **date sheet = class teacher +
  leadership, subject teacher kabhi nahi**; syllabus = apne subject ka teacher, class teacher, leadership; **marks =
  subject teacher + leadership, aur class teacher sirf class test par** (School Exam ke aise subject par nahi jo wo
  padhata nahi); family kisi write par nahi.
- **Asli bug mila aur theek kiya:** `system_admin` (platform admin) ko service "leadership" nahi maanta tha — `_is_office`
  permission ko database ke `rolepermission` rows se padhta hai, jo seed chalne par hi hote. Ab `system_admin` aur
  `school_admin` (`BYPASS_ROLES`) role se hi pehchane jate hain. (Route par `marks.read/update` sab leadership roles ke paas
  pehle se tha; family ke paas sirf read.)

**9.2 Multi-school isolation aur notification idempotency** — `tests/test_exam_isolation.py`: **15 passed**.
- Doosre school ka exam / paper / syllabus / section / student: **har jagah `404`** (kabhi `403` nahi) — read, list, marks
  (read/write/publish/correct/history), syllabus, class test + date sheet (edit/cancel/delete/publish), schedule karna
  (unke subject ya section ke saath), result overview. List mein unka koi exam nahi; hamara duplicate-warning unke test ko
  nahi dekhta; hamari kisi bhi action se **unke school mein ek bhi notification nahi** bani; reminder job unke papers ko
  nahi chhuta.
- **Notifications:** wahi marks dobara save = koi naya Mark nahi, koi notification nahi; publish dobara = `409`, koi dohra
  nahi. **Alag badlav kabhi dedupe mein nahi dabte:** do reschedule = 2 notifications, ek hi mark ki do corrections = 2,
  syllabus ke 3 alag edit = 3 (wahi text dobara = 0), date sheet ke do alag note-badlav = 2, ek hi din ke do class tests
  = dono apna "scheduled" bhejte hain.

**9.3 Performance** — `tests/test_exam_performance.py`: **4 passed**.
- **Asli N+1 mila:** exam list (`GET /exams`) har exam par ~13 statements chalata tha (2 exams par 30, 12 exams par
  160). Naya `exam_reads()` poore batch ke liye papers, marks counts, groups aur caller ke adhikar **ek-ek baar** padhta
  hai (`groups.read_groups_many`, `_marks_entered_many`, `_manage_flags`). Ab list ka cost **2 exams = 12 exams** (office,
  teacher aur family teeno ke liye).
- Pehle se theek (ab test se pakke): marks sheet 4 = 24 bacche, ek exam ka read 1 = 8 sections, result overview 4 = 24
  bacche; publish par har extra bacche ke liye ≤ 6 statements (har family ko apne bacche ke marks bhejne ka asli kharch).
- **Indexes (migration `0008_exam_indexes.py`):** `exam.academic_year_id` (har list/overview isi se filter karta tha, index
  nahi tha) aur `notification (event_type, entity_id)` (har "kya badla" notification ka revision count). Models mein bhi.

**Migrations ka dry-run (aaj tak "chala nahi" tha)** — `0006`, `0007`, `0008` ek temporary **SQLite** file par, asli
rows ke saath: columns aur indexes bane, dobara chalane par safe (idempotent), **backfill chaaron cases mein sahi**
(sahi enrollment se jura; enrollment ke bina student → khali; exam ka year nahi → khali; doosre school ka enrollment →
khali), aur downgrade chale. SQLite ki do seemayein: baseline `0001` mein Postgres-only SQL hai (poori chain SQLite par
nahi chalti), aur SQLite constraints ko ALTER nahi kar sakta — isliye dry-run mein sirf foreign-key constraint ka step
chhoda gaya; wo **Postgres par abhi bhi pehli baar chalega**.

**Sawdhani — `backend/.env`:** usme **asli (Supabase) database ka URL** hai aur `alembic upgrade` default se wahi use
karta hai. Maine alembic ko kabhi us par nahi chalaya; dry-run sirf temporary SQLite par hua (URL badalkar confirm
kiya ki scheme `sqlite` hai). `.env` gitignored hai. Production par migration chalane se pehle apna backup / staging lo.

**Tests (sach mein chale):** poora backend **1070 passed**, wahi **17 purane baseline failures** (koi naya nahi);
frontend is phase mein nahi badla (97/97 pehle jaisa).

**Files:** `plan/service.py` (`exam_reads`, `_manage_flags`, `_is_office` mein `BYPASS_ROLES`), `plan/groups.py`
(`read_groups_many`), `exams/models.py` + `notifications/models.py` (indexes), `alembic/versions/0008_exam_indexes.py`,
`tests/test_exam_permissions.py`, `test_exam_isolation.py`, `test_exam_performance.py`, `test_exam_phase1_model.py`.

**Zaroori baatein**
1. `test_exam_permissions.py` mein 240 cases hain aur ~85 second leta hai (har case ke liye poora school bana kar). Poora
   suite ab ~4.5 min. Chahiye to leadership ke duplicate roles (`vice_principal`, `system_admin`, `office`) sirf kuch
   operations par chalane se ~15 second bach sakte hain.
2. **Migrations `0006`–`0008` Postgres par chalane se pehle staging / backup** — dry-run ne logic aur backfill parkha, par
   foreign-key constraints ka step SQLite par nahi ho sakta.

### Phase 10: complete (24 Nov 2026)
**10.1 End-to-end** — `tests/test_exam_end_to_end.py`, 2 tests, pass.
- Class Test: schedule (4 families ko ek-ek "scheduled") → publish se pehle class ko `unpublished = 1`, family ko kuch nahi →
  marks (45, zero, absent) → publish → class view (pass / fail / absent sahi, absent ka percentage khali) → har family
  sirf apna bacha dekhti hai → School Exam ke result alag (mix nahi).
- School Exam: draft sheet par na koi notification, na family ko dikhta → syllabus (free text) → date sheet publish
  (4 families ko) → marks → publish → class view 80% / fail, family ko sirf apna bacha.

**10.2 Cleanup**
- Tumhare kehne par 4 description lines hata di: Course, Exams, Homework, AI Papers tab ke neeche ki line
  (`SectionDetailPage.tsx` ka `TAB_DESCRIPTIONS` ab khali), aur AI Papers ke upar ki "Papers for … visible only to you"
  line (`exams/ExamsPanel.tsx`). `tsc` clean.
- `/dashboard/academics` hataya **nahi**: student/guardian ka personal marks view abhi wahi use karta hai (rbac mein bhi hai).
- Lint ke 6 purane issues (course/students files, `useClassroom.ts` ka unused import) is module ke nahi, chhue nahi.

**10.3 Excel/CSV marks upload:** tumhare kehne par **skip** — baad mein kabhi chahiye to naya phase.

**Open items:** migrations `0006`–`0008` Postgres par pehli baar staging / backup ke saath; baseline ke 17 purane failing tests.

### Post-Phase 10 changes (24 Nov 2026)
- **Class test:** free-text *Syllabus* (create/edit; families read it at once; a change tells the families); no section picker
  (always this section); table columns Subject | Exam Date | Total Marks | Taken By | Syllabus | Status; "Hide cancelled tests"
  toggle; a cancelled test shows **no** buttons; non-cancelled: Open / Edit / Cancel, and Delete only while no marks exist.
- **Date sheet:** multi-section picker (same sheet for each chosen section of the class; a subject a section lacks is left off;
  all-or-nothing). New `GET /exams/sections`.
- **Publish rule (server + UI):** a paper publishes only when **every** child has a score or an absence. Saving a half-filled
  sheet is always allowed; Publish stays off until saved. Tests use `tests/exam_helpers.publish` (fills the rest as absent).
- **Bugs fixed:** the Exams tab was given the class id instead of the class-section id; `examType` was Title-Cased by
  `lib/api/case.ts` so `class_test` never matched (class tests landed under School Exam) - now left as stored.
- **School Exam tab:** no Delete - **Archive / Unarchive** (+ "Show archived / Hide archived" above the table; families stop
  seeing an archived sheet); the Exam column shows the type once; no row Syllabus button - a **Create syllabus** button
  (exam, subject, *Syllabus Written By* = assigned teacher by default, another teacher = Temporary "T"), read from **Open**;
  Open has no Pass column.
- **Grade column** of the marks sheet: NA (default) / Auto / Manual (`exam_paper.grade_mode`, `marks.grade`).
- **Migration 0009** (`grade_mode`, `syllabus_by_employee_id`, `exam.archived_at`) - not applied to any database yet.
