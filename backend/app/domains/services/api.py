"""The Services group's router: library, transport, meetings, tickets, leave."""

from fastapi import APIRouter

from .leave.router import router as leave
from .library.router import router as library
from .meetings.router import router as meetings
from .tickets.router import router as tickets
from .transport.router import router as transport

router = APIRouter()
router.include_router(library, prefix="/library", tags=["Library"])
router.include_router(transport, prefix="/transport", tags=["Transport"])
router.include_router(meetings, prefix="/meetings", tags=["Meetings"])
router.include_router(tickets, prefix="/tickets", tags=["Tickets"])
router.include_router(leave, prefix="/leave", tags=["Leave"])
