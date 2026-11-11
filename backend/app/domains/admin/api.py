"""The Admin group's router: the sign-in list and the school's settings."""

from fastapi import APIRouter

from .settings.router import router as settings
from .users.router import router as users

router = APIRouter()
router.include_router(users, prefix="/users", tags=["Users"])
router.include_router(settings, prefix="/settings", tags=["Settings"])
