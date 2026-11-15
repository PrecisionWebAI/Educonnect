"""The notification rows one person receives - and the event behind each one.

Tenant-scoped (`TenantMixin`) like every other school-owned table, and owned by
`user_id` on top of that: the screen shows only the signed-in person's rows.

Phase 3 gives a row a **reason** (`event_type`, `entity_type`/`entity_id`) and a
**dedupe key**. The key is what makes "the bell rings once per event per person" a
database rule instead of an `if` somewhere in a service: `attendance:<student>:2026-11-16:absent`
is the same string however many times the register is saved, so the second save cannot
produce a second message.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Index, text
from sqlmodel import Field, SQLModel

from app.core.ids import UUIDMixin
from app.core.tenancy import TenantMixin
from app.domains.auth.models import utcnow


class NotificationBase(SQLModel):
    user_id: UUID = Field(foreign_key="app_user.id")
    title: str
    body: str
    kind: str  # "Attendance" / "Homework" / "Fee" / ...
    read: bool = Field(default=False)
    #: Which event produced this row (`attendance.absent`, `substitution.assigned`,
    #: `exam.reminder`). NULL for rows written before Phase 3 - the bell still shows
    #: them, they simply cannot be grouped by event.
    event_type: str | None = Field(default=None, index=True)
    #: What the row is *about* (`student`, `exam_paper`, `substitution_assignment`).
    entity_type: str | None = None
    entity_id: UUID | None = None
    #: `user_id + dedupe_key` is unique: one message per event per person. NULL means
    #: "not deduplicated" (an announcement somebody may legitimately repeat).
    dedupe_key: str | None = Field(default=None)
    #: How it is delivered. `in_app` is the only one implemented; the column exists so
    #: email/SMS is a new value, not a migration.
    channel: str = Field(default="in_app")


class Notification(NotificationBase, TenantMixin, UUIDMixin, table=True):
    created_at: datetime = Field(default_factory=utcnow)

    __table_args__ = (
        # Partial on purpose: PostgreSQL would otherwise treat every NULL dedupe key as
        # a distinct value (fine) but a non-partial unique index also blocks rows that
        # are deliberately *not* deduplicated. Only rows that name a key are unique.
        Index(
            "uq_notification_user_dedupe_key",
            "user_id",
            "dedupe_key",
            unique=True,
            postgresql_where=text("dedupe_key IS NOT NULL"),
            sqlite_where=text("dedupe_key IS NOT NULL"),
        ),
        # The bell: this person's newest rows inside this school.
        Index(
            "ix_notification_school_user_created",
            "school_id",
            "user_id",
            "created_at",
        ),
    )
