# Exam/Paper Backend — Implementation & Learning Guide

> **Is doc ka kaam:** Exam/Paper AI backend ko file-by-file samjhana + implement karna.
> Har file bante hi niche `## Phase` sections mein **function-by-function** explain hota hai.
> Is doc ko padh ke tum **koi bhi naya module** (HomeWork AI, Timetable AI, etc.)
> khud bana sakte ho — ye ek ready-made production pattern hai.
>
> **Entry level:** Basic Python (functions, classes, imports) jaante ho — baaki sab yahin sikhoge.

---

## 0. Kaise padhe ye doc

1. **Pehle `1. Big Picture`** padho — poora system ek baar mein samajh aayega.
2. **`2. Stack`** mein har library ka sirf itna padho jitna us phase mein chahiye
   (har phase wahan link kiya hua hai).
3. **`5. Phase-wise changelog`** — ye doc ka sabse important part. Har file ka
   **function-by-function** breakdown hai. Padho + code khol ke dekh lo, dono saath.
4. Koi term samajh na aaye → **`8. Glossary`** (basic → advance).

---

## 1. Big Picture — architecture aur data flow

```
┌────────────────────────────────────────────────────────────────────┐
│ FRONTEND (React)                                                   │
│   PaperBuilder → frontend/src/services/exam-builder.service.ts      │
│        │  fetch("/exams/papers", ...)                             │
│        │  Authorization: Bearer <JWT>                              │
│        ▼                                                           │
│ BACKEND (FastAPI)                                                  │
│   app/main.py  →  include_router(paper_router, prefix="/exams")    │
│        │                                                           │
│        ▼                                                           │
│   app/domains/exams/    (sab directly — koi paper/ folder nahi)   │
│        │ router.py      → HTTP handshake, permissions, schema pass │
│        │ service.py     → BUSINESS LOGIC (validation, rules, gates)│
│        │ repository.py  → sirf DB queries (SQLModel/SQLAlchemy)    │
│        │ schemas.py     → Pydantic (request/response ka contract)  │
│        │ models.py      → DB tables (SQLModel)                     │
│        │                                                           │
│        │   (bada kaam] → jobs/worker.py (ARQ + Redis, async)       │
│        │                → llm/ (LangChain + Qwen 2.5 via Ollama)   │
│        │                → rag/ (Qdrant + HF embeddings)            │
│        ▼                                                           │
│   PostgreSQL (facts)  ·  Redis (queue)  ·  Qdrant (vectors)        │
│   MinIO/S3 (files)   ·  Ollama (LLM local) ·  HF API (embeddings)  │
└────────────────────────────────────────────────────────────────────┘
```

**Golden rule:** AI + teacher DONO ka kaam hai.
`AI draft karta hai → validate karta hai → repair karta hai → TEACHER decide karta hai.`
AI kabhi final paper khud approved nahi karta.

---

## 2. Stack — har library kya hai, kahan use, kyun (basic → advance)

| Layer | Library | Kya hai (basic) | Yahan kahan/kasie | Kyun (advance) |
|---|---|---|---|---|
| API | **FastAPI** | Python ka modern web framework | `router.py` — endpoints | Async support, automatic OpenAPI docs, `Depends` DI, Pydantic-integrated |
| Validations | **Pydantic** | Data validation + serialization | `schemas.py` — request/response | Invalid request API tak pahunchte hi 422; response ka contract bhi |
| ORM | **SQLModel** | SQLAlchemy + Pydantic ka fusion | `models.py`, `repository.py` | Ek class = table + schema, type-safe, SQLAlchemy ki power |
| Migrations | **Alembic** | DB schema version control | `alembic/versions/` | Production DB kabhi recreate nahi hota; migrate hota hai |
| LLM calls | **LangChain** | AI components ki toolbox | `llm/prompts.py`, `generator.py` | `ChatPromptTemplate`, `with_structured_output` — consistent, swappable |
| Workflow | **LangGraph** | LLM workflow = state machine (DAG) | `rag/graph.py` (Phase 3) | Branch, repair-loop, checkpoint, human-gate natively |
| Vector DB | **Qdrant** | "Similarity search" wali database | `rag/retriever.py` (Phase 3) | Chapter/topic filter + hybrid search, collection = tenant |
| Queue | **Redis + ARQ** | Async jobs ke liye | `jobs/worker.py` (Phase 3) | Slow AI generation ko UI block nahi karta; status polling |
| LLM model | **Ollama + Qwen 2.5** | Local LLM (free) | `llm/base.py` | ₹0, offline, OpenAI-compatible → model swap = sirf env change |
| Embeddings | **HuggingFace Inference API** | Text → vector | `rag/embeddings.py` (Phase 3) | Free tier; provider swappable (HF → local later) |
| Files | **MinIO/S3** | Object storage | uploads/exports (Phase 3) | PDF, images, generated docs |

> **Abhi note:** Phase 1 mein sirf `FastAPI + Pydantic + SQLModel + Alembic`
> use honge. LLM/queue/vector **baad ke phases** — isliye abhi darna nahi.
---

## 3. Folder structure (annotated)

```
backend/
├── app/
│   ├── main.py                      ← sab routers yahan register hote hain
│   ├── core/
│   │   ├── config.py                ← Settings (env se) — SABKI base
│   │   ├── db.py                    ← Session engine, get_session (DI)
│   │   ├── security.py              ← password hashing etc.
│   │   └── bootstrap.py             ← startup tasks (migrations/seed)
│   └── domains/
│       └── exams/                    ← sab directly (paper/ folder nahi)
│           ├── models.py            ← PaperDraft, GenerationJob, ExamSource
│           ├── schemas.py           ← PaperDraftCreate, GenerateRequest, ...
│           ├── repository.py        ← File 5: DB queries (upsert, get, job)
│           ├── service.py           ← File 6: business logic (save/finalize)
│           ├── router.py            ← File 7: /exams/papers* endpoints
│           ├── llm/                 ← Phase 2: base.py, prompts.py, generator.py
│           ├── jobs/                ← Phase 3: worker.py (ARQ)
│           └── rag/                 ← Phase 3: ingest.py, retriever.py, graph.py
├── alembic/versions/                ← migrations
└── exam_paper_blue_print.md         ← full spec (Part 1 journey, Part 2 tech)
```

**Kaun kisko call karta hai (dependencies — bas 3 rules):**
```
router → service → repository → DB
router → schemas (validate)
service → llm/ , jobs/ , rag/ (bade kaam)
database/model kabhi controller ko nahi jaanta
```

---

## 4. Request lifecycle (ek request ka poora safar)

Example: `POST /exams/papers` (paper draft save)

```
1. React fetch karta hai → /exams/papers , JWT ke saath
2. main.py ka prefix="/exams" + exams/router.py ke routes ("/papers", ...) milte hain
3. FastAPI route match karta hai → create_or_update_paper()
4. Depends(get_session)               → DB session inject (DI)
5. Depends(RequirePermission("exams.create")) → JWT decode, permission check
6. paper_in: PaperDraftCreate         → Pydantic request validate ho jata hai
   (galat data = 422, bina auth = 401, bina permission = 403)
7. service.save_draft(...)            → business rules run (Marks Contract check)
8. repository.create_or_update(...)   → SQL query chalti hai
9. session.commit() + refresh()       → DB written
10. return response_model             → clean JSON wapas
```
---

## 5. Phase-wise changelog (function-by-function breakdown)

> Har file bante hi yahan add hoga. Yehi tumhara **khud-ka reference** hai.

### Phase 0 — Foundation
- _(File 1: yehi doc — done ✅)_
- _(File 2: `app/core/config.py` + `.env-example` — done ✅ — detail niche §5.0.1)_
- [ ] Phase 0.2: Ollama + Qwen 2.5 verify (`curl http://localhost:11434/v1/models`)

#### 5.0.1 — `app/core/config.py` + `.env-example` (File 2) ✅

**Idea:** Saari configuration ek jagah — class `Settings(BaseSettings)`.
App start hote hi `.env` padhta hai → har field typed variable ban jata hai.

| Cheez | Kya hai (basic) | Kyun (production) |
|---|---|---|
| `BaseSettings` | env vars ko typed fields mein badlta hai (pydantic-settings) | Saari config ek class mein, autocomplete + type-safe |
| `Field(default=0.3, ge=0.0, le=1.0)` | default + range validation | Galat env value (temp=5) → **startup pe hi error** (runtime surprise nahi) |
| `extra="ignore"` | `.env` mein extra vars = ignore | Backward-compatible — purane vars kharab nahi hote |
| Default values | `.env` na bhi ho to bhi app chalta hai | Dev/Demo ke liye zero-setup |

**Naye blocks jo add hue:**
- **LLM:** `LLM_PROVIDER=ollama · LLM_BASE_URL · LLM_MODEL=qwen2.5:7b · LLM_TEMPERATURE`
- **Embeddings:** `EMBEDDING_PROVIDER=hf · HUGGINGFACE_API_KEY · EMBEDDING_MODEL · EMBEDDING_DIMENSIONS`
- **Queue:** `REDIS_URL · GENERATION_QUEUE`  ·  **Storage:** `MINIO_*`

**Pattern jo aage har AI module mein dikhega (factory ready):**
```
LLM_PROVIDER=ollama  →  Phase 2 ka llm/base.py factory ise padega
EMBEDDING_PROVIDER=hf → Phase 3 ka embeddings factory ise padega
=> Provider badalo = sirf .env, code untouched. Qwen → GPT/Gemini/any.
```

**Verify command (chala kar dekha ✅):**
```
cd backend && python -c "from app.core.config import settings; print(settings.LLM_MODEL)"
# → qwen2.5:7b
```

### Phase 1 — REST spine (no LLM)
- _(File 3: `exams/models.py` — done ✅ — detail §5.1.1 — `paper/` folder hataake direct exams/)_
- _(File 4: `exams/schemas.py` — done ✅ — detail §5.1.2 — Marks Contract validator verified ✅)_
- _(File 5: `exams/repository.py` — done ✅ — detail §5.1.3 — sqlite smoke-test passed ✅)_
- _(File 6: `exams/service.py` — done ✅ — detail §5.1.4 — service + JSONB gotcha fixed ✅)_
- _(File 7: `exams/router.py` — done ✅ — detail §5.1.5 — E2E HTTP flow passed ✅)_
- _(File 8: Alembic migration — done ✅ — detail §5 File 8 — Postgres pe apply + 15 columns verified ✅)_
- [ ] Frontend service wiring (`exam-builder.service.ts` — mock fallback ko real API pe)

#### 5.1.0 — Restructure: `paper/` folder hataaya, sab directly `exams/` (File 3.5) ✅

**Kya kiya:** `app/domains/exams/paper/` folder delete; models/schemas seedha
`app/domains/exams/{models,schemas}.py` mein; purani (ExamTerm/ExamPaper/ExamResult)
files replace. repository/service/router = importable stubs (File 5/6/7 inhe bharenge).

- **Kyun:** user ne bola — nested `paper/` folder nahi, sab direct exams domain.
- **Risk check kiya:** sirf `main.py` exams router ko bahar se import karta tha; koi
  aur domain exams ke models use nahi karta → safe delete.
- **Alembic history:** purani migrations delete NAHI ki (history sacred); DB mein
  purane tables padi reh sakti hain — harm nahi. Naye tables explicit migration se
  aayenge (File: migration).
- **Verify:** `python -c "import app.main"` → `APP BOOT OK, routes: 20` ✅

#### 5.1.1 — `exams/models.py` (File 3) ✅

**Kya banaya:** 3 nayi tables + 4 enums (sab existing `exampaper` se alag — **naya build, purana untouched**).

| Table | Kya hai | Kaunse column dikhane layak |
|---|---|---|
| `PaperDraft` | AI paper draft | `total_marks` (Marks Contract), `blueprint`/`coverage_plan`/`part_a`/`part_b` (JSON), `status` |
| `GenerationJob` | Async generation record | `paper_id`(FK+index), `status`, `graph_state` (checkpoint), `trace_id` |
| `ExamSource` | Content library row | `source_type`, `chapters`(JSON), `storage_key`, `metadata_json`, `version` |

**Naye concepts (basic → advance):**
1. **`enum.StrEnum`** — DB mein string value, code mein readable. `CoverageMode.marks.value == "marks"` ✅
2. **`Field(foreign_key="gradeclass.id", index=True)`** — FK = DB-level integrity; *index* = queries fast (job by paper, source by class).
3. **`sa_type=JSON` + `default_factory=dict`** — flexible dict columns. **`default={}` kabhi nahi** (same object sab rows share karega — classic Python gotcha). `default_factory` = har row ko nayi dict.
4. **`datetime.utcnow`** — project convention (attendance/chat same).
5. **`metadata_json`** naam — `metadata` nahi likha, kyunki SQLModel mein `.metadata` already hota hai (table registry) — **name clash bug** se bachna hai.
6. **Snapshots in GenerationJob** — `blueprint_snapshot`/`coverage_snapshot`: job start par config freeze. Baad mein draft change ho to bhi job ko pata rahega kis plan pe generate karna hai.

**Kyun naye table, existing `exampaper` kyun nahi?**
- `exampaper` marks/results flow ka hai — uski FK `exam_term_id`-based hai.
- PaperBuilder ka struktur alag (blueprint+coverage+part_a/b) — **alag table = alag purpose** = backward-compatible + clean.

> **Note:** `alembic/env.py` abhi paper models import nahi karta — migration step mein add hoga, warna autogenerate naye tables nahi dekhega.

#### 5.1.2 — `exams/schemas.py` (File 4) ✅

**Idea:** Har API ka request/response **Pydantic schema** se bind hota hai — FastAPI
khud validate karta hai. TOP cheez: **Marks Contract server-side** yahan enforce hota hai.

**Kya banaya (schema → kya karta hai):**

| Schema | Use-case | Zaroori baat |
|---|---|---|
| `BlueprintSectionIn` | Blueprint ka ek section `{type, count, marksEach}` | `count ge=0`, `marksEach ge=1` |
| `CoveragePlanIn` + children | Coverage plan `{mode, chapters:[{chapter, targetMarks, topics}]}` | Frontend `CoveragePlan.js` se 1:1 |
| `QuestionIn` | Question shape (AI + teacher dono) | Ek hi schema — reuse ✅ |
| `SourceIn` | Generation ko sources | `SourceItem.js` se 1:1 |
| **`PaperDraftCreate`** | `POST /papers` body | **STAR — validators yahin** |
| `GenerationRequest` | `POST /papers/generate` body | Marks Contract check yahin bhi |
| `PaperDraftRead` / `PaperSavedRead` / `JobRead` | Response contracts | API ka "kya milega" promise |
| `QuestionPatch` | PATCH question | Sab optional — partial update |
| `FinalizeRequest` | Finalize body | sirf note abhi |

**The STAR — `model_validator(mode="after")` (2 rules):**

```python
@model_validator(mode="after")
def check_marks_contract(self):
    total = blueprint_total(self.blueprint)  # Σ (count × marksEach)
    if self.blueprint and total != self.total_marks:
        raise ValueError(f"Marks Contract fail: ...")
    return self


@model_validator(mode="after")
def check_coverage_within_cap(self):
    allocated = sum(c.targetMarks for c in self.coverage_plan.chapters)
    cap = self.total_marks if mode == marks else 100
    if allocated > cap:
        raise ValueError(...)
    return self
```

| Concept | Basic | Advance (production) |
|---|---|---|
| `model_validator(mode="after")` | Saare fields validate hone ke baad ek aur check | Cross-field rules yahin — alag-alag jagah nahi |
| `raise ValueError` | Validator fail → **FastAPI 422** | Client ko clean error, server crash nahi |
| `Field(ge=1, le=200)` | Single-field bound | Env/garbage data pehle hi pakdo |
| EK schema, 2 jagah | `PaperDraftCreate` + `GenerationRequest` dono mein marks-rule | Dono API ka random drift nahi |

**Verify kiya (checks passed ✅):**
```
blueprint 5MCQ×1 + 2Short×2 = 9, total_marks=9  → SAVE allowed
total_marks=10 (blueprint total 9)               → 422 BLOCKED  (Marks Contract)
coverage sum 12 > total 10                        → 422 BLOCKED  (coverage overflow)
percent mode 70% <= 100                          → allowed (30% = Random)
```

**Frontend alignment note:** frontend `grade_class_id`/`subject_id` nahi bhejta —
isliye `PaperDraft` model mein woh **nullable** rakhe (models.py comment dekho).
Jab class/subject lookup API banegi to service resolve karke IDs bharega.

#### 5.1.3 — `exams/repository.py` (File 5) ✅

**Idea:** Repository = **sirf SQL**, koi business logic nahi. Service logic
rakhti hai, HTTP router patli hota hai, aur DB se ye layer baat karta hai.

| Function | Kya karta hai | Concept |
|---|---|---|
| `get_paper_by_id` | PK se paper | `session.get(Model, id)` — sabse simple query |
| `create_paper` | Naya row | `add → commit → refresh` (id + defaults wapas) |
| `update_paper` | Partial update | `setattr` loop = generic, naye column par bhi kaam karega |
| **`upsert_paper`** | Update-ho-to-warna-create | **IDEMPOTENCY** — same request 2 baar = 2 rows nahi |
| `list_papers` | Recent papers (teacher filter) | `select().where().order_by().limit()` — SQLAlchemy standard |
| `create_generation_job` | Job banana (queued) | Snapshots = config freeze at job start |
| `get_latest_job_by_paper` | Polling ke liye | `order_by desc().limit(1)` = "sabse naya" |
| `update_job_status` | Progress update | `stages` dict mein current + history; `error` fail par |

**Production rules jo is file mein message hain:**
1. Repo **None return** karta hai, **HTTPException nahi** — service decide karegi ki 404 dena hai ya kya.
2. **Upsert** = draft save karne ka safe tarika (refresh se bhi data intact).
3. Har function ka **ek hi kaam** — test karna asaan.

**Smoke-test kiya (sqlite in-memory, 6 checks ✅):**
```
1) created paper id = 1 | status = draft
2) updated title = v2 | same row id = 1 | total rows = 1   ← UPSERT ✎ (update kiya, duplicate nahi)
3) get_paper_by_id ok: True
4) job status = queued | trace = trace-abc
5) latest job id = 1
6) job final = done | stage = completed | error = None
```

> **Sikho:** test ke liye ek chhota temp script banao → run karo → hatao.
> (Production mein ye pytest banega — Phase 4.)

#### 5.1.4 — `exams/service.py` (File 6) ✅

**Idea:** Service = **dimaag**. Router HTTP samhalta hai, repository SQL,
service checks/gates/rules chala ke result banata hai.

| Function | Kya karta hai | Production note |
|---|---|---|
| `_get_paper_or_404` | Paper dhundho, nahi to 404 | Common helper — har endpoint reuse |
| `new_trace_id` | Unique job id | Debugging + logs |
| `save_draft` | Schema → upsert | `model_dump(exclude_unset=True)` = sirf bheje hue fields |
| `enqueue_generation` | Job record (queued) | Snapshots freeze; Phase 3 mein ARQ yahin aayega |
| `get_job_status` | Latest job | Polling API base |
| `recommend_marks` | Rules se marks | **Deterministic** (AI nahi) — testable + predictable |
| `add_custom_question` | part_b append | recommendedMarks server-side |
| `patch_question` | Lock/edit question | **JSONB GOTCHA yahan solve hui Hindi** |
| `finalize_paper` | Marks gate → approved | Hard gate → 409 on fail |

**⭐ THE lesson — JSONB GOTCHA (asli production wala):**
```
Scenario: patched question list and part_a got no "locked" key.
Cause:   SQLAlchemy JSON columns ko STRUCTURE se compare karta hai.
         In-place mutation se committed snapshot bhi mutate ho gaya
         (wahi object) → assignment "no change" maana gaya → UPDATE nahi chali.
Fix:     mutation se PEHLE deepcopy → copy pe change → assign.
         Ab committed se structure alag = dirty ✓
```
> Ye library ka bug nahi — **JSONB columns ka nature** hai. Yaad rakhna:
> JSONB ko in-place mutate karke same object assign mat karo.

**Verify (6 checks ✅):**
```
1) draft id = 1 | total = 9
2) recommend MCQ easy short = 1 | Short Hard long = 4
3) part_b size = 1 | recommended = 2
4) a1 locked = True                      ← JSONB fix proof
5) finalize status = approved
6) finalize blocked: 409 True            ← Marks Contract gate
```

#### 5.1.5 — `exams/router.py` (File 7) ✅ — PHASE 1 COMPLETE 🎉

**Idea:** Router = **patli glue**. HTTP mein aaye request ko:
`schema validate → permission check → service call → response_model`

| Endpoint | Handler | Permission |
|---|---|---|
| `GET /exams/papers` | list papers (teacher ke) | `exams.read` |
| `POST /exams/papers` | create/update draft | `exams.create` |
| `GET /exams/papers/{id}` | ek paper | `exams.read` |
| `POST /exams/papers/generate` | job enqueue | `exams.create` |
| `GET /exams/papers/{id}/job` | polling | `exams.read` |
| `POST /exams/questions/custom` | teacher question | `exams.create` |
| `PATCH /exams/papers/{id}/questions/{qid}` | lock/edit | `exams.update` |
| `POST /exams/papers/{id}/finalize` | hard gate | `exams.publish` |

**Naye concepts:**
1. **`Depends(RequirePermission("exams.create"))`** — JWT → user → `AuthorizationService.can()` → role
   ke paas permission hai? nahi → 403. `current_user.id` = `created_by` (resource scoping).
2. **`response_model`** — API ka "kya milega" ka contract (guarantee).
3. **Teacher permissions map** (`permissions.py`) — `exams.read/create/update/publish`
   pehle se `TEACHER_PERMISSIONS` mein the ✓ (0 auth changes chahiye).

**E2E TEST — poora stack HTTP se (7 checks ✅):**
```
1) POST /papers                    → 201 {paperId:1, status:draft}
2) POST /papers/generate           → 201 queued
3) GET /papers/1/job               → 200 queued | trace: tr-4cf7ff5
4) GET /papers                     → 200 count:1 (teacher scoped)
5) POST /questions/custom          → 201 part_b size:1
6) PATCH question locked=true      → 200 locked: True   ← JSONB fix HTTP tak gayi
7) POST /papers/2/finalize         → 200 approved       ← Marks gate
```
Test setup ke 2 gem tips: **TestClient + dependency_overrides** (get_session →
sqlite), aur **`sqlite://` + StaticPool** (nahi to har connection ka alag DB banta hai!).

### Phase 1.5 — File 8: Alembic migration (`alembic/versions/f7d9a1b2c3e4_add_paper_builder_tables.py`)

**Kya karta hai:** production Postgres mein 3 nayi tables banata hai (`paperdraft`,
`generationjob`, `examsource`) + 4 native enum types. Purane exam tables ko **nahi**
chhedta (history sacred).

**Structure (yeh pattern yaad rakho):**
```
revision      = 'f7d9a1b2c3e4'   ← naya id
down_revision = 'b2c3d4e5f6a7'   ← pichla head (chain!)
upgrade()   → enums create → 3 tables + indexes
downgrade() → indexes drop → tables drop → enums drop  (ulta kram)
```

**4 production lessons is file se:**

1. **Chain rule** — `down_revision` galat = migration graph toot jayega. Head
   pata karne ka command: `alembic heads` ya
   `python -c "from alembic.script import ScriptDirectory; print(ScriptDirectory('alembic').get_heads())"`.

2. **Postgres enum gotcha (aaj ka bug!)** — pehle attempt pe error aaya:
   ```
   psycopg2.errors.DuplicateObject: type "coveragemode" already exists
   [SQL: CREATE TYPE coveragemode AS ENUM ('auto','marks','percent')]
   ```
   **Kyun:** hum `enum.create()` se enum bana rahe the, AUR `op.create_table()`
   ke andar wahi enum phir se auto-create ho raha tha.
   **Fix:** `postgresql.ENUM(..., create_type=False)` — matlab "table ke saath
   type dobara mat banao, main khud manage kar raha hoon".
   > Ye SQLAlchemy/Alembic ka classic dard hai — ek baar seekh liya, hamesha kaam aayega.

3. **`%` escape** — `alembic/env.py` mein `settings.DATABASE_URL.replace("%", "%%")`
   already hai; password mein `%40` (@) ho to configparser interpolation tod deta hai.

4. **Migration history kabhi delete nahi** — purane exam tables DB mein pade rehne do.
   Naya feature = nayi tables + nayi migration. Data loss ka koi risk nahi.

**Verify kaise kiya (3 levels):**
```powershell
# 1) syntax
python -c "import ast; ast.parse(open('alembic/versions/f7d9...py',encoding='utf-8').read())"
# 2) chain
python -c "from alembic.script import ScriptDirectory; print(ScriptDirectory('alembic').get_heads())"
#      → HEADS: ['f7d9a1b2c3e4']   ✅
# 3) live DB (container ke andar)
docker compose exec -T backend alembic upgrade head
docker compose exec -T backend python -c "import sqlalchemy as sa; from app.core.db import engine; insp=sa.inspect(engine); print([c['name'] for c in insp.get_columns('paperdraft')])"
#      → 15 columns ✅
```

---

## 5b. ⚠️ TESTING TRAP — PowerShell + curl.exe (aaj ke 2 ghante isi ne khaye)

Aaj host se login **500** aa raha tha jabki container ke andar **200**. Do ghante
lag gaye ye samajhne mein. Asli wajah:

```powershell
# ❌ Ye PowerShell mein TOOTA JSON bhejta hai (escaping ki gaddbadi):
curl.exe -s -X POST http://127.0.0.1:8000/auth/login `
  -H "Content-Type: application/json" `
  -d "{\"username\":\"admin@eduverse.com\",\"password\":\"admin123\"}"
#    → 500 "Internal Server Error" (text/plain) — FastAPI ko malformed body mili
```

**Diagnosis ka pehla rule:** agar host se 500 aur container ke andar 200 ho,
to **sabse pehle apna client (curl) shak karo — backend nahi.**

**Sahi tarika (Python se — koi escaping dard nahi):**
```python
import json, urllib.request

req = urllib.request.Request(
    "http://127.0.0.1:8000/auth/login",
    data=json.dumps(
        {"username": "admin@eduverse.com", "password": "admin123"}
    ).encode(),
    headers={"Content-Type": "application/json"},
)
print(urllib.request.urlopen(req, timeout=15).status)  # → 200 ✅
```

**Aur bhi 2 cheezein jo aaj confusing thin:**
- `netstat` mein `[::1]:8000 LISTENING wslrelay.exe` — ye WSL ka IPv6 relay hai;
  `localhost` kabhi ispe ja sakta hai. Isliye host tests **`127.0.0.1`** se karo.
- `docker ps` empty dikhe to `docker compose ps` se confirm karo — CLI state kabhi
  cache hoti hai.

**Asli E2E (host se, Docker container pe) — 7/7 PASS ✅:**
```
1) POST /auth/login                → 200 (JWT mila)
2) POST /exams/papers              → 201 {"paperId":5,"status":"draft"}
3) POST /exams/papers (total 99)   → 422 ← Marks Contract gate ✅
4) POST /exams/papers/generate     → 201 {"id":1,"status":"queued","trace_id":"tr-..."}
5) GET  /exams/papers/5/job        → 200 {"status":"queued"}
6) POST /exams/questions/custom    → 201 (part_b updated)
7) GET  /exams/papers (no token)   → 401 ← auth gate ✅
```

**API contract notes (frontend se match karne ke liye):**
| Endpoint | Body/response ki khaas baat |
|---|---|
| `POST /exams/papers` | response `{paperId, status}` (schema `PaperSavedRead`), request `blueprint` **list** hai (`{"sections": [...]}` nahi!) |
| `POST /exams/papers/generate` | `total_marks` + `blueprint` + `coverage_plan` sab chahiye |
| `POST /exams/questions/custom` | nested: `{paper_id, question: {...}}` |

> **PHASE 1 + migration COMPLETE ✅** router→service→repository→DB→Postgres sab jude.
> Agla: Phase 2 — LLM (Qwen 2.5 via Ollama) + frontend wiring.

### Phase 2 — LLM (Qwen 2.5 via Ollama)
- [ ] `llm/base.py`, `prompts.py`, `generator.py`, `services.py` (direct exams/ ke andar)

### Phase 3 — Async + RAG (ARQ, Qdrant, HF embeddings, LangGraph)
- [ ] `jobs/worker.py`, `rag/ingest.py`, `retriever.py`, `graph.py` (direct exams/ ke andar)

### Phase 4 — Hardening
- [ ] tests, logging, deployment notes

---

## 6. Production principles (har file mein dikhenge)

1. **Layered architecture** — router/service/repository kabhi nahi milte (independent change).
2. **Server-side validation** — frontend kabhi trust nahi karte (Marks Contract, coverage).
3. **Permissions har endpoint par** — `RequirePermission` + resource scoping (teacher = apni school).
4. **Idempotency** — create/update upsert (same request twice = 2 rows nahi).
5. **AI structured JSON** — `with_structured_output`, plain text kabhi nahi.
6. **Async jobs + polling** — slow generation UI ko block nahi karta.
7. **Human gate last** — AI draft, teacher decides.
8. **Migrations, tests, logging, secrets-in-env** — production DB/repo ka norm.
---

## 7. How to build any new module (10-step checklist)

Jab bhi naya backend feature banana ho (e.g. Homework AI, Timetable AI):

1. `core/config.py` mein naye settings add karo (env ke saath)
2. Domain folder banao: `app/domains/<feature>/`
3. `models.py` — tables (SQLModel), enums, JSON fields
4. `schemas.py` — Create/Read + validators (server-side rules)
5. `repository.py` — sirf query functions (koi logic nahi)
6. `service.py` — business logic + permissions + errors (HTTPException)
7. `router.py` — endpoints, `Depends`, `response_model`, permissions
8. `main.py` — router register (prefix/tags)
9. Alembic migration likho (autogenerate + review)
10. pytest likho → Run karo → Logging/trace_id add karo

---

## 8. Glossary (basic → advance)

> Jaisi-jaisi libraries use hongi, yahan add hongi. Shuruaati entries:

| Term | Definition (basic) | Yahan use kahan |
|---|---|---|
| **APIRouter** | Endpoints ka ek group; `main.py` use  poor app mein jodta hai | `exams/router.py` |
| **Depends** | FastAPI ka dependency injection — function ke args auto-fill (session, user) | har endpoint |
| **BaseModel** | Pydantic — data validate aur shape deta hai | `schemas.py` |
| **SQLModel** | Table + Pydantic ek saath; `table=True` = DB row | `models.py` |
| **RequirePermission** | JWT decode → user nikalta hai → permission check | auth se aata hai |
| **ChatPromptTemplate** | LLM prompt ka reusable template (system+human messages) → Phase 2 mein detail | `llm/prompts.py` |
| **with_structured_output** | LLM ko Pydantic schema ka strict JSON nikalne force karta hai | `llm/generator.py` |
| **BaseSettings** | `.env` ko typed settings object mein badlta hai (pydantic-settings) | `core/config.py` |
| **Field(default, ge, le)** | Pydantic field — default + validation constraints | `core/config.py` |
| **StrEnum** | Enum jiska value string hota hai — DB readable, code readable | `exams/models.py` |
| **sa_type=JSON** | Column ko Postgres JSONB banana (dict/list store karne ke liye) | `exams/models.py` |
| **default_factory** | Mutable default ka safe tarika (`default={}` = shared-instance bug) | `exams/models.py` |
| **index=True** | DB index banata hai — frequently-filtered column ke liye | `exams/models.py` |