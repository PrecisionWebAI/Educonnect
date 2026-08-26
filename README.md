# Educonnect
Automation of Schools Workflow

## Quick Commands

You can run commands using `make` from the root directory (or from within `backend/`):

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

### Git Hooks (Pre-commit & Pre-push)
Run this once to enforce checks before every commit and push:
```bash
make hooks
```
