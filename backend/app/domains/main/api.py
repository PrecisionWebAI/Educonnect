"""The Main group's router: dashboard, chat, notifications, copilot."""

from fastapi import APIRouter

from .chat.router import router as chat
from .copilot.router import router as copilot
from .dashboard.router import router as dashboard
from .notifications.router import router as notifications

router = APIRouter()
router.include_router(dashboard, prefix="/dashboard", tags=["Dashboard"])
router.include_router(chat, prefix="/chat", tags=["Chat"])
router.include_router(notifications, prefix="/notifications", tags=["Notifications"])
router.include_router(copilot, prefix="/copilot", tags=["Copilot"])
