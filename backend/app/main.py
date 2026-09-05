from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.bootstrap import bootstrap
from app.domains.academics import router as academics_router
from app.domains.admissions import router as admissions_router
from app.domains.attendance import router as attendance_router
from app.domains.auth import router as auth_router
from app.domains.chat import router as chat_router
from app.domains.exams import router as exams_router
from app.domains.finance import router as finance_router
from app.domains.homework import router as homework_router
from app.domains.students import router as students_router
from app.domains.teachers import router as teachers_router
from app.domains.timetable import router as timetable_router
from app.domains.users import router as users_router

@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Ensure DB/schema/migrations/seed data exist before serving requests
    bootstrap()
    yield


app = FastAPI(
    title="EduVerse API",
    description="Backend API for the EduVerse School Automation Platform",
    version="1.0.0",
    lifespan=lifespan,
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
app.include_router(users_router.router, prefix="/users", tags=["Users"])
app.include_router(academics_router.router, prefix="/academics", tags=["Academics"])
app.include_router(students_router.router, prefix="/students", tags=["Students"])
app.include_router(teachers_router.router, prefix="/teachers", tags=["Teachers"])
app.include_router(attendance_router.router, prefix="/attendance", tags=["Attendance"])
app.include_router(finance_router.router, prefix="/finance", tags=["Finance"])
app.include_router(
    homework_router.router, prefix="/homework", tags=["Homework & Diary"]
)
app.include_router(timetable_router.router, prefix="/timetable", tags=["Timetable"])
app.include_router(exams_router.router, prefix="/exams", tags=["Exams"])
app.include_router(admissions_router.router, prefix="/admissions", tags=["Admissions"])
app.include_router(chat_router.router, prefix="/chat", tags=["Chat"])


@app.get("/")
def root():
    return {"message": "Welcome to EduVerse API"}


@app.get("/health")
def health():
    return {"status": "ok"}
