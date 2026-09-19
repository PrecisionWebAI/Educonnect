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
│   app/domains/exams/paper/                                         │
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
│       └── exams/
│           ├── models.py            ← ExamTerm, ExamPaper, ExamResult (existing)
│           ├── schemas.py           ← Create/Read schemas (existing)
│           ├── repository.py        ← DB queries (existing)
│           ├── service.py           ← business logic (existing)
│           ├── router.py            ← /exams/* endpoints (existing)
│           └── paper/               ← ★ NAYA — humara module (exam/paper)
│               ├── models.py        ← PaperDraft, GenerationJob, ExamSource, ...
│               ├── schemas.py       ← PaperDraftCreate, GenerateRequest, ...
│               ├── repository.py
│               ├── service.py
│               ├── router.py        ← APIRouter(prefix="/papers")
│               ├── llm/             ← Phase 2: base.py, prompts.py, generator.py
│               ├── jobs/            ← Phase 3: worker.py (ARQ)
│               └── rag/             ← Phase 3: ingest.py, retriever.py, graph.py
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
2. main.py ka prefix="/exams" + paper/router.py ka prefix="/papers" milta hai
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
- _(File 3: `paper/models.py` + `paper/__init__.py` — done ✅ — detail §5.1.1)_
- [ ] `paper/schemas.py` — PaperDraftCreate + Marks Contract validator
- [ ] `paper/repository.py` — upsert, get, job, usage-log
- [ ] `paper/service.py` — save_draft, finalize gate, recommend_marks
- [ ] `paper/router.py` — 7 endpoints
- [ ] Alembic migration (+ `alembic/env.py` mein paper models import)
- [ ] Frontend service wiring (`exam-builder.service.ts`)

#### 5.1.1 — `paper/models.py` + `paper/__init__.py` (File 3) ✅

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

### Phase 2 — LLM (Qwen 2.5 via Ollama)
- [ ] `paper/llm/base.py`, `prompts.py`, `generator.py`, `services.py`

### Phase 3 — Async + RAG (ARQ, Qdrant, HF embeddings, LangGraph)
- [ ] `paper/jobs/worker.py`, `paper/rag/ingest.py`, `retriever.py`, `graph.py`

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
| **APIRouter** | Endpoints ka ek group; `main.py` use  poor app mein jodta hai | `paper/router.py` |
| **Depends** | FastAPI ka dependency injection — function ke args auto-fill (session, user) | har endpoint |
| **BaseModel** | Pydantic — data validate aur shape deta hai | `schemas.py` |
| **SQLModel** | Table + Pydantic ek saath; `table=True` = DB row | `models.py` |
| **RequirePermission** | JWT decode → user nikalta hai → permission check | auth se aata hai |
| **ChatPromptTemplate** | LLM prompt ka reusable template (system+human messages) → Phase 2 mein detail | `llm/prompts.py` |
| **with_structured_output** | LLM ko Pydantic schema ka strict JSON nikalne force karta hai | `llm/generator.py` |
| **BaseSettings** | `.env` ko typed settings object mein badlta hai (pydantic-settings) | `core/config.py` |
| **Field(default, ge, le)** | Pydantic field — default + validation constraints | `core/config.py` |
| **StrEnum** | Enum jiska value string hota hai — DB readable, code readable | `paper/models.py` |
| **sa_type=JSON** | Column ko Postgres JSONB banana (dict/list store karne ke liye) | `paper/models.py` |
| **default_factory** | Mutable default ka safe tarika (`default={}` = shared-instance bug) | `paper/models.py` |
| **index=True** | DB index banata hai — frequently-filtered column ke liye | `paper/models.py` |