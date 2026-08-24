from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.domains.auth import router as auth_router

app = FastAPI(
    title="EduVerse API",
    description="Backend API for the EduVerse School Automation Platform",
    version="1.0.0",
)

# Configure CORS
origins = [
    "http://localhost",
    "http://localhost:3000",
    # Add your frontend domains here
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth_router.router, prefix="/auth", tags=["Auth"])


@app.get("/")
def root():
    return {"message": "Welcome to EduVerse API"}


@app.get("/health")
def health():
    return {"status": "ok"}
