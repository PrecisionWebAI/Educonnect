# Educonnect

Automation of Schools Workflow

## Project Structure

```
├── backend/          # FastAPI + SQLModel API (uv-managed)
│   ├── app/          # Application code (core config, domain routers/models)
│   ├── alembic/      # Database migrations
│   ├── scripts/      # Demo seed data
│   └── Dockerfile    # Backend image (used by docker-compose.yml)
└── frontend/         # Next.js + Tailwind CSS app
```

## Run the Backend with Docker (Local)

The single root `docker-compose.yml` runs the full backend stack — FastAPI API + PostgreSQL — in containers:

```bash
docker compose up --build          # start in foreground
docker compose up --build -d       # start in background
docker compose down                # stop (data persists in the volume)
```

- OpenAPI docs: <http://localhost:8000/docs>
- Health check: <http://localhost:8000/health>

Notes:

- On startup the API automatically creates the database/schema, applies Alembic
  migrations, and seeds demo data (see `app/core/bootstrap.py`).
- The container entrypoint (`backend/docker-entrypoint.sh`) runs that same
  bootstrap *before* uvicorn starts: it waits for PostgreSQL to accept
  connections, then applies migrations and the seed scripts
  (`backend/scripts/seed.py`, then the app-level catalogs, then the demo roll
  `backend/scripts/auto_seeder_by_admission_form_and_teacher_form.py`). Every step
  is idempotent, so it is safe on each start — watch the `[bootstrap]` / `[seed]`
  lines in `docker compose logs`. Tune the wait with `DB_WAIT_SECONDS` (default `60`).
- **Demo data** comes from that last step, and it is written **through the app's own
  forms**: students by submitting the admission form (so each one gets a login, a
  guardian login, a class-section and an application row) and teachers by submitting
  the hire form. It fills both schools, every class (nursery … class 12), sections
  A-D, 15-25 students each, plus a register and a few leave requests. It only
  inserts what is missing, so restarts are quick and a half-filled database is
  completed. Every seeded account signs in with **`demo@1234`** (override it with
  `SEED_DEMO_PASSWORD`). Set `SEED_DEMO_DATA=0` to leave the database without
  demo students and staff.

### Configuration

Everything the stack reads comes from the environment. There is exactly one
inventory of it — **`backend/.env-example`** — and exactly one place in the code
that reads it, `backend/app/core/config.py`:

```bash
cp backend/.env-example backend/.env     # git-ignored; fill in the blanks
```

`backend/.env` is loaded no matter which directory `uvicorn`, `alembic`,
`pytest` or `docker compose` is started from, and it reaches the API container
through `env_file:` in `backend/docker-compose.yml`. Only three values are
overridden there, because inside the compose network "localhost" means the
container itself: `DB_HOST` (`db`), `DB_PORT` (`5432`) and `LLM_BASE_URL`
(`host.docker.internal`).

| Group | Variables | Notes |
| --- | --- | --- |
| Environment | `ENVIRONMENT` | `local` / `staging` / `production`. Anything but `local` refuses to start with the placeholder `SECRET_KEY`. |
| Database | `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_SCHEMA` | Or one `DATABASE_URL_OVERRIDE` (the Supabase URI), which wins over all of them. |
| TLS | `DB_SSLMODE` | `require` for Supabase, empty locally. |
| Auth | `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES` | `SECRET_KEY` has no usable non-local default. |
| CORS | `CORS_ORIGINS`, `CORS_ORIGIN_REGEX` | Comma-separated; no deployed URL is baked into the code. |
| Seeds | `SEED_DEMO_DATA`, `SEED_DEMO_PASSWORD`, `SEED_PLATFORM_ADMIN_LOGIN`, `SEED_PLATFORM_ADMIN_PASSWORD`, `SEED_SCHOOL_ADMIN_PASSWORD` | The admin passwords are read only when that account is first created. |
| AI / LLM | `LLM_*`, `DIFFICULTY_MIX`, `BLOOM_MIX` | Switching to OpenAI/Gemini is a change of `LLM_PROVIDER` + `LLM_BASE_URL` + `LLM_API_KEY`, never code. |
| Embeddings / RAG | `EMBEDDING_*`, `HUGGINGFACE_API_KEY`, `QDRANT_*`, `RETRIEVAL_*`, `CHUNK_*` | `EMBEDDING_PROVIDER=dummy` runs the whole RAG pipeline offline. |
| Other | `REDIS_URL`, `MINIO_*`, `UPLOAD_*`, `OCR_*` | The MinIO credentials have no defaults in code. |
| Debug | `SQL_ECHO` | `1` logs every SQL statement. |

**Frontend:** `frontend/.env.example` → `frontend/.env.local` (git-ignored).
`NEXT_PUBLIC_API_BASE_URL` is inlined into the bundle at build time, so it must
be the URL the *browser* can reach, and a deployed build needs it set there too.

**Host-side compose knobs** (`PG_HOST_PORT`, `API_PORT`, `DB_WAIT_SECONDS`) live
in the root `.env.example`: if your machine already runs PostgreSQL on port
**5432**, copy it to `.env` and set `PG_HOST_PORT` (e.g. `PG_HOST_PORT=5433`) so
the containerized DB doesn't clash. Override `API_PORT` the same way.
- Requires Docker Desktop (Docker >= 24 / Compose v2).

## Run Locally (without Docker)

Backend development server with auto-reload:

```bash
cd backend
uv run fastapi dev
```

Visit <http://localhost:8000> — the app connects to the PostgreSQL settings in
`backend/.env`.

### Deploy to FastAPI Cloud

Sign up and log in at <https://fastapicloud.com>, then deploy with:

```bash
cd backend
uv run fastapi deploy
```

## Quick Commands

You can run commands using `make` from the repo root:

| Command | Action |
|---|---|
| `make dev` | Start development server with auto-reload (`fastapi dev app/main.py`) |
| `make start` | Start server in production mode (`fastapi run app/main.py`) |
| `make check` | Run lint & formatting checks (`ruff check` & `ruff format --check`) |
| `make fix` | Auto-fix lint issues and format all code |
| `make lint` | Run Ruff lint check only |
| `make lint-fix` | Run Ruff lint auto-fix only |
| `make format` | Run Ruff code formatter only |
| `make format-check` | Check formatting without modifying files |
| `make migrate` | Run database migrations (`alembic upgrade head`) |
| `make hooks` | Install Git hooks for `pre-commit` and `pre-push` |
| `make docker` | Build & run the full backend stack (FastAPI + PostgreSQL) with Docker |
| `make docker-up` | Same as `make docker` but detached (background) |
| `make docker-down` | Stop the Docker stack |
| `make docker-logs` | Stream backend logs |

## Code Quality & Git Hooks

This project uses [Ruff](https://docs.astral.sh/ruff/) and [pre-commit](https://pre-commit.com/) to automatically check and format code on both **pre-commit** and **pre-push**.

### Install Git Hooks

```bash
make hooks
```

### Run All Pre-commit Hooks Manually

```bash
uv run --directory backend pre-commit run --all-files
```

## Learn More

- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Pre-commit Documentation](https://pre-commit.com/)
