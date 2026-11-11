"""Meetings reads: the calendar the Meetings screen lists, from real rows.

`/meetings` used to answer with invented slots; the `meeting` table already holds
them, ordered the way the screen shows them (soonest first).
"""

from sqlmodel import Session, select

from app.core.formatting import day

from .models import Meeting
from .schemas import MeetingItem


def list_meetings(session: Session) -> list[MeetingItem]:
    """Every meeting on the calendar, soonest first."""
    statement = select(Meeting).order_by(Meeting.meeting_date)  # type: ignore[arg-type]
    return [
        MeetingItem(
            id=meeting.id,  # type: ignore[arg-type]
            title=meeting.title,
            with_whom=meeting.with_whom,
            date=day(meeting.meeting_date),
            time=meeting.meeting_time,
            room=meeting.room or "",
            type=meeting.status,
        )
        for meeting in session.exec(statement).all()
    ]
