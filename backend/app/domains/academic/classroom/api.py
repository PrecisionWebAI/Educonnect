"""The Classroom hub's router: the Classroom screen plus every tab it opens."""

from fastapi import APIRouter

from .academics.router import router as academics
from .attendance.router import router as attendance
from .course.router import classroom_router as section_course
from .course.router import router as course
from .exams.plan.router import router as exam_plan
from .exams.router import router as exams
from .homework.router import router as homework
from .router import router as classroom
from .students.router import router as students
from .timetable.router import router as timetable

router = APIRouter()
router.include_router(classroom, prefix="/classroom", tags=["Classroom"])
router.include_router(section_course, prefix="/classroom", tags=["Course"])
router.include_router(course, prefix="/course", tags=["Course"])
router.include_router(academics, prefix="/academics", tags=["Academics"])

router.include_router(students, prefix="/students", tags=["Students"])
router.include_router(attendance, prefix="/attendance", tags=["Attendance"])
router.include_router(homework, prefix="/homework", tags=["Homework & Diary"])
router.include_router(timetable, prefix="/timetable", tags=["Timetable"])
router.include_router(exams, prefix="/exams", tags=["Exams"])
router.include_router(exam_plan, prefix="/exams", tags=["Exams"])
