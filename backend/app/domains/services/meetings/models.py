"""The meeting calendar.

One `meeting` table serves both kinds of meeting the screen lists (a parent-teacher
slot and a staff huddle); `with_whom` and `status` say which is which, so the
screen shows the words the office typed instead of mapping enum names.
"""

from datetime import date

from sqlmodel import Field, SQLModel

from app.core.ids import UUIDMixin
from app.core.tenancy import TenantMixin


class MeetingBase(SQLModel):
    title: str
    with_whom: str
    meeting_date: date
    meeting_time: str  # "4 PM"
    room: str | None = None
    status: str = Field(default="Scheduled")  # Scheduled / Pending / Done


class Meeting(MeetingBase, TenantMixin, UUIDMixin, table=True):
    pass
