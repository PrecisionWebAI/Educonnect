"""The Academic group's router: mounts the Classroom hub."""

from fastapi import APIRouter

from .classroom.api import router as classroom

router = APIRouter()
router.include_router(classroom)
