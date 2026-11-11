from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.bootstrap import bootstrap
from app.core.config import settings
from app.domains.academic.api import router as academic_router
from app.domains.admin.api import router as admin_router
from app.domains.auth import router as auth_router
from app.domains.finance.api import router as finance_router
from app.domains.insights.api import router as insights_router
from app.domains.main.api import router as main_router
from app.domains.operations.api import router as operations_router
from app.domains.people.api import router as people_router
from app.domains.services.api import router as services_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Ensure DB/schema/migrations/seed data exist before serving requests
    bootstrap()
    from app.core.api_surface import entries

    print(
        f"[startup] application successfully started - "
        f"env={settings.ENVIRONMENT}, {len(entries(_app))} routes"
    )
    yield
    print("[startup] application stopped")


app = FastAPI(
    title="EduVerse API",
    description="Backend API for the EduVerse School Automation Platform",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
origins = settings.cors_origins_list

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    # Preview/branch deploys are allowed by pattern, never by a name baked into
    # the code - `CORS_ORIGIN_REGEX` is configuration like every other origin.
    allow_origin_regex=settings.CORS_ORIGIN_REGEX or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers - one per nav group (the group's `api.py` mounts its features)
app.include_router(auth_router.router, prefix="/auth", tags=["Auth"])
app.include_router(main_router, prefix="", tags=["Main"])
app.include_router(academic_router, prefix="", tags=["Academic"])
app.include_router(people_router, prefix="", tags=["People"])
app.include_router(finance_router, prefix="", tags=["Finance"])
app.include_router(operations_router, prefix="", tags=["Operations"])
app.include_router(services_router, prefix="", tags=["Services"])
app.include_router(insights_router, prefix="", tags=["Insights"])
app.include_router(admin_router, prefix="", tags=["Admin"])


@app.get("/")
def root():
    return {"message": "Welcome to EduVerse API"}


@app.get("/health")
def health():
    return {"status": "ok"}
