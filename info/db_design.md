# Educonnect — Database Design (ER Diagram)

> **What this file is.**
> `info/db_mapping.txt` is the **target** architecture, and `info/db_mapping_2.txt`
> (where present) draws the tables one by one. **This file is the entity-relation
> view of the database as it stands today** — PostgreSQL 16, **34 tables**,
> **59 foreign keys**, **4 unique constraints**, **33 primary keys**.
>
> Everything below was read from the live schema (`information_schema` +
> `pg_constraint`), not from the model files, so it doubles as a check on them.
>
> **Registering an admission creates the student.** An application that reaches
> `Registered` is *promoted* in one transaction: a student login
> (`stu.<name>.<class-section>@school`), the `studentprofile` row the directory
> lists, the guardian login (`gau.<name>.p1@school`, reused for that parent's
> other children), and the link between them (`studentparentrelationship`). The
> application then remembers what it made (`student_id`, the two user ids,
> `promoted_at`), which is why "Registered" and "listed under Students" can no
> longer disagree. The first-time passwords are returned exactly once, by
> `POST /admissions/applications/{id}/register` (or `reset-login`); only hashes
> are stored.

## How to read the diagram

The first diagram is a **Mermaid `erDiagram`**: GitHub, GitLab and the VS Code
Markdown preview render it as a picture, and anywhere else it still reads as
plain text. The second is the same thing in plain ASCII for terminals.

| Mark | Meaning |
|---|---|
| `PK` | primary key |
| `FK` | foreign key (a relationship line below carries it) |
| `UK` | single-column unique constraint |
| `\|o--o{` | zero-or-one → zero-or-many (the child FK is **NULLable**) |
| `\|\|--o{` | exactly-one → zero-or-many (the child FK is NOT NULL) |
| `\|\|--\|\|` | one-to-one (the child FK is `UNIQUE`) |

## ER diagram (Mermaid)

```mermaid
erDiagram
    %% =====================================================================
    %% LAYER 0 — IDENTITY & ACCESS   (one login, many roles)
    %% =====================================================================
    user {
        int id PK
        varchar email UK "the login name (stu.* / gau.* for school-made logins)"
        varchar full_name
        varchar hashed_password "never stored in clear"
        bool is_active
        timestamp created_at
        varchar contact_email "the person's real email - identifies a parent"
    }
    role {
        int id PK
        varchar codename UK "system_admin, teacher, guardian ..."
        varchar label
        bool is_system "14 rows - roles are DATA, not an enum"
    }
    user_role {
        int user_id PK "FK -> user"
        int role_id PK "FK -> role"
        bool is_primary "the dashboard that opens at login"
        timestamp assigned_at
    }
    permission {
        int id PK
        varchar codename UK "classes.read, users.impersonate ..."
        varchar category
        varchar label "142 rows"
    }
    rolepermission {
        int role_id PK "FK -> role"
        int permission_id PK "FK -> permission"
    }
    impersonationlog {
        int id PK
        int actor_user_id FK "the super admin"
        int target_user_id FK "the account being viewed"
        timestamp started_at
        timestamp ended_at "NULL while the session is open"
        varchar reason
    }

    user      ||--o{ user_role        : "holds"
    role      ||--o{ user_role        : "is held by"
    role      ||--o{ rolepermission   : "grants"
    permission||--o{ rolepermission   : "is granted to"
    user      ||--o{ impersonationlog : "acts as"
    user      ||--o{ impersonationlog : "is viewed by"

    %% =====================================================================
    %% LAYER 1 — SCHOOL STRUCTURE   (the class vocabulary)
    %% =====================================================================
    classroom {
        int id PK
        varchar name UK "Nursery, LKG, UKG, Class 1 ... Class 12"
        int level "position in the school, 0 = Nursery"
        varchar stage "pre_primary ... senior_secondary"
    }
    section {
        int id PK
        varchar name "A ... J"
        int classroom_id FK
    }
    %% section has UNIQUE(classroom_id, name): a class-section pair cannot repeat
    subject {
        int id PK
        varchar name UK
        varchar code UK "MAT, SCI, ENG ..."
    }

    classroom ||--o{ section : "has 10 sections (A-J)"

    %% =====================================================================
    %% LAYER 2 — PEOPLE   (a profile row per hat a login wears)
    %% =====================================================================
    studentprofile {
        int id PK
        int user_id FK "UNIQUE - one profile per login"
        varchar admission_number UK
        date date_of_birth
        varchar guardian_name
        varchar gender "NULLable"
        int classroom_id FK "NULLable - admission not finished"
        int section_id FK "NULLable - admission not finished"
    }
    teacherprofile {
        int id PK
        int user_id FK "UNIQUE - one profile per login"
        varchar department
        varchar qualification
        date joining_date
    }
    studentparentrelationship {
        int id PK
        int student_id FK "the child"
        int parent_user_id FK "the adult's own login"
        varchar relationship_type "Father, Mother, Guardian"
    }

    user           ||--o| studentprofile             : "login for"
    user           ||--o| teacherprofile             : "login for"
    classroom      |o--o{ studentprofile             : "placed in"
    section        |o--o{ studentprofile             : "sits in"
    studentprofile ||--o{ studentparentrelationship  : "has adults"
    user           ||--o{ studentparentrelationship  : "is the adult of"

    %% =====================================================================
    %% LAYER 3 — TEACHING & ATTENDANCE
    %% =====================================================================
    attendancerecord {
        int id PK
        int student_id FK
        int classroom_id FK
        int section_id FK
        int subject_id FK "NULLable - daily register vs per period"
        date date
        enum status "present|absent|leave|late|half_day"
        varchar remarks "NULLable"
        int overridden_by_id FK "NULLable - staff who corrected it"
    }
    attendanceauditlog {
        int id PK
        int attendance_record_id FK
        int changed_by_id FK
        timestamp changed_at
        enum previous_status "NULLable"
        enum new_status
        varchar previous_remarks "NULLable"
        varchar new_remarks "NULLable"
    }
    homeworkassignment {
        int id PK
        varchar title
        text description
        int classroom_id FK
        int section_id FK "NULLable - whole class vs one section"
        int subject_id FK
        int teacher_id FK
        date due_date
    }
    homeworksubmission {
        int id PK
        int homework_id FK
        int student_id FK
        varchar content_url "NULLable while pending"
        enum status "pending|submitted|graded"
        varchar teacher_feedback "NULLable"
    }
    classdiary {
        int id PK
        int student_id FK
        int teacher_id FK
        date date
        text note
    }
    timetableperiod {
        int id PK
        int classroom_id FK
        int section_id FK "NULLable"
        int subject_id FK
        int teacher_id FK
        enum day_of_week "monday ... sunday"
        time start_time
        time end_time
        varchar room "NULLable - free text"
    }
    teacherassignment {
        int id PK
        int teacher_id FK
        int classroom_id FK
        int section_id FK "NULLable"
        int subject_id FK
    }
    classteacherassignment {
        int id PK
        int teacher_id FK
        int classroom_id FK
        int section_id FK "NULLable"
    }

    studentprofile      ||--o{ attendancerecord          : "attends"
    classroom           ||--o{ attendancerecord          : "for"
    section             ||--o{ attendancerecord          : "in"
    subject             |o--o{ attendancerecord          : "period"
    user                |o--o{ attendancerecord          : "overrode"
    attendancerecord    ||--o{ attendanceauditlog        : "is corrected by"
    user                ||--o{ attendanceauditlog        : "changed"
    classroom           ||--o{ homeworkassignment        : "set in"
    section             |o--o{ homeworkassignment        : "for"
    subject             ||--o{ homeworkassignment        : "about"
    teacherprofile      ||--o{ homeworkassignment        : "set by"
    homeworkassignment  ||--o{ homeworksubmission        : "receives"
    studentprofile      ||--o{ homeworksubmission        : "submits"
    studentprofile      ||--o{ classdiary                : "is noted about"
    teacherprofile      ||--o{ classdiary                : "writes"
    classroom           ||--o{ timetableperiod           : "is timetabled"
    section             |o--o{ timetableperiod           : "for"
    subject             ||--o{ timetableperiod           : "teaches"
    teacherprofile      ||--o{ timetableperiod           : "teaches"
    teacherprofile      ||--o{ teacherassignment         : "teaches subject"
    classroom           ||--o{ teacherassignment         : "in"
    section             |o--o{ teacherassignment         : "in"
    subject             ||--o{ teacherassignment         : "subject"
    teacherprofile      ||--o{ classteacherassignment    : "is class teacher of"
    classroom           ||--o{ classteacherassignment    : "in"
    section             |o--o{ classteacherassignment    : "in"


    %% =====================================================================
    %% LAYER 4 — FINANCE
    %% =====================================================================
    feestructure {
        int id PK
        varchar name "Tuition Fee, Transport Fee ..."
        decimal amount
        int classroom_id FK "the class the head applies to"
        enum frequency "monthly|term|yearly|one_time"
        varchar due_day "NULLable - free text"
        varchar status "Draft until published, then Active"
    }
    feetransaction {
        int id PK
        int student_id FK
        int fee_structure_id FK
        decimal amount_paid "may be less than the card"
        date date
        enum payment_mode "cash|upi|card|cheque|bank_transfer"
        varchar receipt_number UK
    }
    salarypayment {
        int id PK
        varchar staff_code "EMP-0040"
        varchar staff_name "snapshot, not a FK"
        varchar designation "snapshot"
        varchar department "snapshot"
        varchar month "Sep 2026 - the label the screen groups by"
        decimal gross
        decimal deductions
        decimal net
        varchar status "Pending -> Processing -> Paid"
        date paid_on "NULLable - not paid yet"
    }

    classroom      ||--o{ feestructure   : "is charged"
    feestructure   ||--o{ feetransaction : "is paid through"
    studentprofile ||--o{ feetransaction : "pays"

    %% =====================================================================
    %% LAYER 5 — ADMISSIONS & HIRING   (no foreign keys - by design)
    %% =====================================================================
    admissionapplication {
        int id PK
        varchar application_no UK "ADM-2026-0141"
        varchar status "Draft | Registered"
        date created_on
        varchar student_first_name "everything else NULLable:"
        varchar student_last_name "a draft is saved half-filled"
        varchar applied_for_class_level "free text - the family asks by name"
        varchar applied_section_preference
        varchar father_name
        varchar mother_name
        varchar guardian_name
        varchar previous_school_name
        varchar separation_reason "set when the student leaves"
        date separation_date
        int student_id FK "UNIQUE - the student this form created"
        int student_user_id FK "the student's login (stu.*)"
        int guardian_user_id FK "the guardian's login (gau.*)"
        timestamp promoted_at "when that happened"
    }
    staffvacancy {
        int id PK
        varchar role "Chemistry Teacher"
        varchar department
        int openings "unfilled seats"
        varchar status "Open | Closed"
    }
    hiringcandidate {
        int id PK
        varchar candidate_no UK "CAN-2026-0040"
        varchar candidate_name
        varchar role
        varchar department
        varchar qualification "NULLable"
        int experience
        date applied_on
        date interview_on "NULLable"
        varchar emp_id "stamped only when Hired: EMP-0040"
        varchar status "Resume|Shortlisted|Interview|Hired|Rejected"
    }
    %% No relationship lines here on purpose:
    %%   admissionapplication -> an applicant is not a student yet, and the
    %%   requested class is free text, so there is nothing to point at - until it
    %%   is Registered, at which point the promotion link above is filled.
    %%   salarypayment / staffvacancy / hiringcandidate -> matched by
    %%   staff_code, role + department, so the post can be closed without
    %%   erasing the pipeline history.

    %% ---------------------------------------------------------------------
    %% The promotion: registering an application creates the real records.
    %% ---------------------------------------------------------------------
    admissionapplication ||--o| studentprofile           : "creates (once)"
    user                 |o--o{ admissionapplication     : "is the student login of"
    user                 |o--o{ admissionapplication     : "is the guardian login of"


    %% =====================================================================
    %% LAYER 6 — EXAMS & AI PAPER BUILDER   (RAG content library)
    %% =====================================================================
    examsource {
        int id PK
        int classroom_id FK "NULLable - uploaded with a class NAME"
        int subject_id FK "NULLable - uploaded with a subject NAME"
        int created_by FK "NULLable"
        enum source_type "pdf|image|url|text|bank"
        varchar title
        varchar class_name "always filled - retrieval filters on it"
        varchar subject "always filled"
        varchar board
        varchar teacher_name
        varchar kind
        varchar strictness
        json chapters "['Life Processes', ...]"
        json tags
        varchar storage_key "NULLable - object storage key"
        json metadata_json
        int page_count "NULLable"
        varchar status "pending|ingesting|ready|failed"
        int chunk_count
        varchar error "NULLable"
        varchar content_hash "stops double embedding"
        int replaces_id FK "NULLable - self reference, version chain"
        int version
        timestamp created_at
        timestamp updated_at
    }
    questionusagelog {
        int id PK
        varchar fingerprint "hash of the normalised question text"
        text text
        int paper_id FK "NULLable"
        varchar class_name
        varchar subject
        varchar chapter
        varchar topic
        varchar qtype
        int marks
        int created_by FK "NULLable"
        timestamp used_at
    }
    paperdraft {
        int id PK
        varchar title
        int classroom_id FK "NULLable - built from a class NAME"
        int subject_id FK "NULLable"
        int created_by FK "NULLable"
        varchar class_name
        varchar subject
        varchar board
        varchar exam_type
        varchar language
        json chapters
        json sources
        json instructions
        json scope
        json constraints
        int total_marks "the marks contract"
        int duration_minutes
        json blueprint
        json coverage_plan
        enum coverage_mode "auto|marks|percent"
        json part_a "AI questions"
        json part_b "teacher's own questions"
        enum status "draft|in_review|approved"
        timestamp created_at
        timestamp updated_at
    }
    generationjob {
        int id PK
        int paper_id FK "NULLable - stateless runs save no draft"
        enum status "queued|running|done|failed|canceled"
        json graph_state
        json stages
        json blueprint_snapshot
        json coverage_snapshot
        json config_snapshot
        json result_snapshot
        json model_info
        varchar error "NULLable"
        varchar trace_id "NULLable"
        timestamp created_at
        timestamp updated_at
    }

    classroom   |o--o{ examsource        : "filed under"
    subject     |o--o{ examsource        : "about"
    user        |o--o{ examsource        : "uploaded"
    examsource  |o--o{ examsource        : "replaces (version chain)"
    paperdraft  |o--o{ questionusagelog  : "used the question"
    user        |o--o{ questionusagelog  : "created"
    classroom   |o--o{ paperdraft        : "for"
    subject     |o--o{ paperdraft        : "about"
    user        |o--o{ paperdraft        : "authored"
    paperdraft  |o--o{ generationjob     : "was generated by"

    %% =====================================================================
    %% LAYER 7 — COMMUNICATION   (chat)
    %% =====================================================================
    chatthread {
        int id PK
        varchar name "NULL for a direct chat"
        bool is_group
    }
    chatthreadparticipant {
        int thread_id PK "FK -> chatthread"
        int user_id PK "FK -> user"
    }
    chatmessage {
        int id PK
        int thread_id FK
        int sender_id FK
        text content_text
        varchar attachment_url "NULLable - a link, not a blob"
        timestamp created_at
    }

    chatthread ||--o{ chatthreadparticipant : "includes"
    user       ||--o{ chatthreadparticipant : "joins"
    chatthread ||--o{ chatmessage           : "holds"
    user       ||--o{ chatmessage           : "sends"

    %% =====================================================================
    %% LAYER 8 — SYSTEM
    %% =====================================================================
    alembic_version {
        varchar version_num PK "the migration the DB is at"
    }
```

## ER diagram (plain ASCII)

The same entities, for terminals, code review and `git diff` — no renderer needed.

```
                       ┌──────────────────┐
                       │       user       │  ONE login per person.
                       │──────────────────│  No role column: a person's
                       │ id (PK)          │  roles live in user_role.
                       │ email (UK)       │
                       │ hashed_password  │
                       │ is_active        │
                       └────┬────────┬────┘
                            │ 1:N    │ 1:N
                            │        └───────► user_role ──N:1──► role ──1:N──► rolepermission ──N:1──► permission
                            │                   (PK user_id,      (codename UK)                        (codename UK)
                            │                    PK role_id)      is_system                            category
                            │                                    ──► roles are DATA, not an enum         142 rows
                            │
        ┌───────────────────┼────────────────────┬─────────────────────┬───────────────────────┐
        │ 1:1 (user_id UK)  │ 1:1 (user_id UK)   │ N:1 (parent side)   │ N:1 x2 (actor+target) │ N:1 (sender/member)
        ▼                   ▼                    ▼                     ▼                       ▼
  studentprofile      teacherprofile   studentparentrelationship   impersonationlog   chatthreadparticipant
  ──────────────      ──────────────   ─────────────────────────   ────────────────   ───────────────────
  id (PK)             id (PK)          id (PK)                     id (PK)            thread_id (PK)
  user_id (FK,UK)     user_id (FK,UK)  student_id (FK)             actor_user_id(FK)  user_id (PK)
  admission_no (UK)   department       parent_user_id (FK)         target_user_id     ──► chatmessage
  date_of_birth       qualification    relationship_type           started_at             (thread_id, sender_id,
  guardian_name       joining_date                                  ended_at?              content_text)
  gender?                                                           reason?
  classroom_id?  ──────────────┐
  section_id?    ────────┐     │
                         │     │
   ┌─────────────────────┘     └──────────────────────────┐
   │                                                      │
   ▼                                                      ▼
┌──────────────────┐                             ┌──────────────────┐
│     section      │  N:1                        │   classroom      │
│──────────────────│────────────────────────────►│──────────────────│
│ id (PK)          │                             │ id (PK)          │
│ name (A..J)      │  UNIQUE(classroom_id, name) │ name (UK)        │
│ classroom_id(FK) │                             │ level, stage     │
└──────────────────┘                             └────┬─────────────┘
                                                      │ 1:N  (the class vocabulary:
                                                      │       every academic row
   every academic row carries classroom_id + section_id│       carries this id)
                                                      │
   ┌──────────────┬──────────────┬───────────────┬────┴──────────┬───────────────┐
   ▼              ▼              ▼               ▼               ▼               ▼
attendancerecord  homeworkassignment  timetableperiod  feestructure   examsource?  paperdraft?
   │                 │                  │                │              │
   ├─► attendanceauditlog              (subject_id,     └─► feetransaction        (self: replaces_id)
   │  (record → corrections)            teacher_id)         (student_id → studentprofile)
   ├─► homeworksubmission
   │  (student_id → studentprofile)
   └─► teacherassignment / classteacherassignment / classdiary
        (teacher_id → teacherprofile)

┌────────────────────────────┐        ┌──────────────────────────┐
│  questionusagelog          │        │  generationjob           │
│  paper_id ────────────────►│◄───────│  paper_id ───────────────│
│  (anti-repeat ledger)      │        │  (async run status)      │
└────────────────────────────┘        └──────────────────────────┘
              ▲                                   ▲
              └─────────── paperdraft ────────────┘
                        (classroom_id?, subject_id?, created_by?)

 STANDALONE (deliberately no foreign key)
   admissionapplication   the applicant is not a student yet, and the requested
                          class is free text ("Class 6"), not a classroom_id
   salarypayment          a register keeps snapshots of name/designation/dept
   staffvacancy           hiring matches by role + department, so a post can be
   hiringcandidate        closed without erasing the pipeline history
   alembic_version        Alembic's own bookkeeping
```


### The eight layers

| Layer | Tables | What it is |
|---|---|---|
| 0 Identity & access | `user`, `user_role`, `role`, `permission`, `rolepermission`, `impersonationlog` | one login, many roles (additive RBAC), switch-account audit |
| 1 School structure | `classroom`, `section`, `subject` | the class vocabulary the whole UI reads |
| 2 People | `studentprofile`, `teacherprofile`, `studentparentrelationship` | one profile row per hat a login wears |
| 3 Teaching & attendance | `attendancerecord`, `attendanceauditlog`, `homeworkassignment`, `homeworksubmission`, `classdiary`, `timetableperiod`, `teacherassignment`, `classteacherassignment` | the day-to-day work |
| 4 Finance | `feestructure`, `feetransaction`, `salarypayment` | what the school charges and pays |
| 5 Admissions & hiring | `admissionapplication`, `staffvacancy`, `hiringcandidate` | people who are not students or staff yet |
| 6 Exams & AI papers | `examsource`, `questionusagelog`, `paperdraft`, `generationjob` | content library (RAG), drafts, async jobs |
| 7 Communication | `chatthread`, `chatthreadparticipant`, `chatmessage` | chat |
| 8 System | `alembic_version` | migration bookkeeping |

## Data the database holds today (demo school)

| Layer | Rows | | | |
|---|---|---|---|---|
| 0 | user **188** | user_role **188** | role **14** | permission **142** · rolepermission **900** |
| 0 | impersonationlog **12** | | | |
| 1 | classroom **15** (Nursery → Class 12) | section **150** (A–J each) | subject **12** | |
| 2 | studentprofile **51** | teacherprofile **11** | studentparentrelationship **51** | |
| 3 | attendancerecord **480** | attendanceauditlog **24** | homeworkassignment **19** | homeworksubmission **39** |
| 3 | classdiary **15** | timetableperiod **61** | teacherassignment **33** | classteacherassignment **20** |
| 4 | feestructure **17** | feetransaction **46** | salarypayment **15** | |
| 5 | admissionapplication **53** (50 Registered → 50 students, 3 Draft) | staffvacancy **12** | hiringcandidate **13** | |
| 6 | examsource **12** | questionusagelog **18** | paperdraft **12** | generationjob **13** |
| 7 | chatthread **12** | chatthreadparticipant **48** | chatmessage **64** | |

Every table holds at least ten rows, and each one deliberately covers the states
its screen can show: all five attendance statuses, all five payment modes, every
hiring stage, a fee head that is still a Draft, a content source that failed and
one that is still ingesting, a generation job in each of its four states, an
impersonation session that was never closed, a student with no section yet (3 of
them), a student with no recorded gender (2), a student with no attendance at all,
and sections with nobody in them.

## Rules the schema follows

**Enums are database types** (adding a value is a migration): attendance status
(`present|absent|leave|late|half_day`), submission status (`pending|submitted|graded`),
fee frequency (`monthly|term|yearly|one_time`), payment mode
(`cash|upi|card|cheque|bank_transfer`), day of week, source type
(`pdf|image|url|text|bank`), paper status (`draft|in_review|approved`), coverage
mode (`auto|marks|percent`), generation job status
(`queued|running|done|failed|canceled`).
**Roles and permissions are not enums** — they are rows, so adding one is an
`INSERT` and never a migration.

**NULLable on purpose** (not an oversight):

| Column | Why it is empty sometimes |
|---|---|
| `studentprofile.classroom_id` / `section_id` | the admission is not finished; the class cards must still list the student |
| `examsource.classroom_id` / `subject_id`, `paperdraft.classroom_id` / `subject_id` | the library and the paper wizard accept a class and a subject **by name**, so the id is filled only when it can be resolved |
| `*.section_id` on homework / timetable / teacher assignments | one section row vs a whole-class row |
| `attendancerecord.subject_id` | a daily register (primary) vs a per-period register (secondary) |
| `impersonationlog.ended_at` | the switch-account session is still open |
| `hiringcandidate.interview_on` / `emp_id` | not interviewed yet / not hired yet |
| `salarypayment.paid_on` | the month is not paid yet |

**Uniqueness** (4 constraints): `section (classroom_id, name)`,
`studentprofile (user_id)`, `teacherprofile (user_id)` and
`admissionapplication (student_id)` — one form creates one student — plus
single-column `UNIQUE` on every `email`, `admission_number`, `receipt_number`,
`candidate_no`, `application_no`, `codename`, `classroom.name`,
`subject.name/code` and `examsource.content_hash`.

## Migration state

| | |
|---|---|
| Head revision | `d8a3b6c2f5e1` — *admission promotion link + `user.contact_email`*, on top of `c7f2a9d4e6b8` (*rename gradeclass → classroom*) |
| Renamed by that revision | the table, the 10 `grade_class_id` columns, `uq_section_grade_name`, the primary key, the name index, the id sequence and the two FK indexes |
| Drift | `alembic revision --autogenerate` reports an empty migration, so the models and this database agree |
| Implemented since | the admission → student mapping: registering now creates the student, both logins and the parent link (this file's header describes it) |
| Not built yet | `parentprofile` / `staffprofile` (target-only), a marks/results/disputes layer (the Academics screens call `/exams/marks`, `/exams/results`, `/exams/disputes` and no such endpoints exist), and the multi-school `school_id` |

## How this file was produced / how to re-check it

```sql
-- tables and columns (the `?` in this document = is_nullable)
SELECT table_name, column_name, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
ORDER BY table_name, ordinal_position;

-- every key and constraint
SELECT conrelid::regclass AS table, contype, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE connamespace = 'public'::regnamespace
ORDER BY 1, 2;

-- row counts per table
SELECT relname, n_live_tup FROM pg_stat_user_tables
WHERE schemaname = 'public' ORDER BY relname;
```

Companion files: `info/db_mapping.txt` (target architecture) ·
`info/db_mapping_2.txt` (table-by-table boxes, where present) ·
`info/project-blueprint.md` (product blueprint).

