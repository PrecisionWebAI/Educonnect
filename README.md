# Educonnect

Automation of Schools Workflow

## Project Structure

```
├── backend/          # FastAPI + SQLModel API (uv-managed)
│   ├── app/          # Application code (core config, domain routers/models)
│   ├── alembic/      # Database migrations
│   ├── scripts/      # Deployment seed (schools + their admin)
│   └── Dockerfile    # Backend image (used by docker-compose.yml)
└── frontend/         # Next.js + Tailwind CSS app
```

## Run the Backend with Docker (Local)

`backend/docker-compose.yml` runs the backend in a container. There is no
database container: the API talks to the Supabase project named by
`DATABASE_URL_OVERRIDE` in `backend/.env`, the same database the deployed API
serves — so a laptop and production always show the same rows.

```bash
docker compose up --build          # start in foreground
docker compose up --build -d       # start in background
docker compose down                # stop the stack
```

- OpenAPI docs: <http://localhost:8000/docs>
- Health check: <http://localhost:8000/health>

Notes:

- On startup the API applies Alembic migrations and runs the catalog seeders
  (see `app/core/bootstrap.py`). A managed database is never created — the app
  only connects to the one its DSN names.
- The container entrypoint (`backend/docker-entrypoint.sh`) runs that same
  bootstrap *before* uvicorn starts: it waits for the host inside
  `DATABASE_URL_OVERRIDE` to accept connections, then applies migrations and the
  seed scripts (`backend/scripts/seed.py`, then the app-level catalogs). Every
  step is idempotent, so it is safe on each start — watch the `[bootstrap]` /
  `[seed]` lines in `docker compose logs`. Tune the wait with `DB_WAIT_SECONDS`
  (default `60`).
- The demo roll (students, teachers, attendance) is **not** part of a boot: it is
  a manual script, `make seed-roll`.
- The seeds write catalog + deployment data only: the role catalog, the class
  catalog (15 classes / 150 sections), the RBAC grants, the schools and the one
  admin login each of them runs on. No students, teachers, staff or sample rows —
  those come from the product flows (admission, hiring).

### Configuration

Everything the stack reads comes from the environment. There is exactly one
inventory of it — **`backend/.env-example`** — and exactly one place in the code
that reads it, `backend/app/core/config.py`:

```bash
cp backend/.env-example backend/.env     # git-ignored; fill in the blanks
```

`backend/.env` is loaded no matter which directory `uvicorn`, `alembic`,
`pytest` or `docker compose` is started from, and it reaches the API container
through `env_file:` in `backend/docker-compose.yml`. Only `LLM_BASE_URL` is
overridden there, because inside the compose network "localhost" means the
container itself (`host.docker.internal` is the host's Ollama). The database
needs no override at all: the DSN points at Supabase from every environment.

| Group | Variables | Notes |
| --- | --- | --- |
| Environment | `ENVIRONMENT` | `local` / `staging` / `production`. Anything but `local` refuses to start with the placeholder `SECRET_KEY`. |
| Database | `DATABASE_URL_OVERRIDE` | The Supabase DSN, used by a laptop *and* by the deployment. `DB_USER`/`DB_PASSWORD`/`DB_HOST`/`DB_PORT`/`DB_NAME` are the fallback for a Postgres you run yourself, and are empty here on purpose. |
| Schema | `DB_SCHEMA` | `public`. |
| TLS | `DB_SSLMODE` | `require` — Supabase terminates TLS with its own CA. |
| Auth | `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES` | `SECRET_KEY` has no usable non-local default. |
| CORS | `CORS_ORIGINS`, `CORS_ORIGIN_REGEX` | Comma-separated; no deployed URL is baked into the code. |
| Seeds | `SEED_PLATFORM_ADMIN_LOGIN`, `SEED_PLATFORM_ADMIN_PASSWORD`, `SEED_SCHOOL_ADMIN_PASSWORD` | The admin passwords are read only when that account is first created. |
| AI / LLM | `LLM_*`, `DIFFICULTY_MIX`, `BLOOM_MIX` | Switching to OpenAI/Gemini is a change of `LLM_PROVIDER` + `LLM_BASE_URL` + `LLM_API_KEY`, never code. |
| Embeddings / RAG | `EMBEDDING_*`, `HUGGINGFACE_API_KEY`, `QDRANT_*`, `RETRIEVAL_*`, `CHUNK_*` | `EMBEDDING_PROVIDER=dummy` runs the whole RAG pipeline offline. |
| Other | `REDIS_URL`, `MINIO_*`, `UPLOAD_*`, `OCR_*` | The MinIO credentials have no defaults in code. |
| Debug | `SQL_ECHO` | `1` logs every SQL statement. |

**Frontend:** `frontend/.env.example` → `frontend/.env.local` (git-ignored).
`NEXT_PUBLIC_API_BASE_URL` is inlined into the bundle at build time, so it must
be the URL the *browser* can reach, and a deployed build needs it set there too.

**Host-side compose knobs** (`API_PORT`, `DB_WAIT_SECONDS`) live in the root
`.env.example`; every one of them has a default. There is no `PG_HOST_PORT` any
more — there is no database container to map.

### How a change reaches Supabase

There is one rule, and everything else follows from it:

> **The schema is the models. A change ships as a migration; data that must
> exist ships as an idempotent seeder edit; the same command applies both, here
> and on Supabase.**

What that means in practice:

| You changed | What to do | When Supabase sees it |
| --- | --- | --- |
| A model (column, table, constraint) | add a migration (`alembic revision`), commit it | next deploy runs `bootstrap()` → `alembic upgrade head`, or you run `make db-supabase` |
| Seed data (schools, classes) | edit the seeder (it only inserts what is missing) | next boot, or `make db-supabase` |
| **Data by hand** (pgAdmin / psql / the UI) | **don't** — it has no file in git | **never**. It shows up as drift instead |

`git push` on its own changes no database; it only delivers the migration. The
change happens when `alembic upgrade head` (or a seeder) runs against Supabase.

```bash
make db-sync         # schema -> seeds -> verify, against backend/.env (Supabase)
make db-supabase     # the same three steps, against SUPABASE_DB_URL
make db-verify       # just the drift check
make seed-roll       # MANUAL demo roll through the admission + teacher forms
make audit-config    # one reader, no secret defaults, everything documented
```

`db-sync` refuses to rebuild (`--rebuild`) without `--yes` — and, on the managed
database, without a second, deliberate `--i-mean-production`: there is no local
copy to fall back on. It prints the target it is about to touch (host and
database, never the password), and fails the run if `check_schema.py` disagrees
with the code.

Row-level tooling still exists (`scripts/db_snapshot.py`,
`scripts/db_copy.py`), but it is **not** wired into `make` any more. With one
database there is nothing to compare or copy, and `db-copy` truncates the very
database it reads from — so it refuses outright when both DSNs name the same host
and database. It is kept for the day a branch/snapshot database has to be brought
in line with the real one.

### The demo roll is manual

`backend/scripts/auto_seeder_by_admission_form_and_teacher_form.py` fills a school
with students, guardians, teachers, class teachers, a register and a few leave
requests — every record through the same service the screens call
(`admissions.service.create_application`, `staff.service.create_profile`,
`classroom.service.assign_class_teacher`,
`attendance.service.bulk_create_attendance`). Nothing runs it automatically: not
the entrypoint, not `bootstrap()`, not CI.

```bash
make seed-roll ARGS="--school abc --yes"                        # sections a-d
make seed-roll ARGS="--school abc --sections a,b --min 10 --max 15 --yes"
make seed-roll ARGS="--school abc --reset --yes"                # replace an earlier roll
```

It writes to the real database, so it insists on `--yes`. `--reset` deletes that
school's demo rows first (it finds them by the `@<code>.demo` addresses it hands
out); re-running without `--reset` only inserts what is missing.

One caveat worth knowing: **new databases are built with
`scripts/init_schema.py`, not `alembic upgrade head`.** Revision
`f8d9e0f1a2b3_uuid_everywhere` rebuilds every table from the models, so replaying
the chain cannot reproduce the schema it was written for — `app/core/schema.py`
has the full story. Existing databases still take ordinary migrations, and that
is what `db-sync` uses when the tables are already there.
- Requires Docker Desktop (Docker >= 24 / Compose v2).

## Run Locally (without Docker)

Backend development server with auto-reload:

```bash
cd backend
uv run fastapi dev
```

Visit <http://localhost:8000> — the app connects to the same Supabase database as
the container does, using the DSN in `backend/.env`.

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
| `make db-sync` | Schema → seeds → verify, against the Supabase database in `backend/.env` |
| `make db-verify` | Drift check: models vs schema, then the seeded logins |
| `make seed-roll` | Manual demo roll through the admission + teacher forms (`ARGS="--school abc --yes"`) |
| `make hooks` | Install Git hooks for `pre-commit` and `pre-push` |
| `make docker` | Build & run the backend stack (FastAPI + Supabase) with Docker |
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
