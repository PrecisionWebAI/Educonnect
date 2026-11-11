"""Notification reads/writes for the signed-in person, from `notification`.

`GET /notifications` used to answer with invented rows; the table already holds
them and `user_id` says whose they are - a teacher's bell never shows a
guardian's rows.
"""

from sqlmodel import Session, select

from app.core.formatting import stamp
from app.domains.admin.users.models import User

from .models import Notification
from .schemas import NotificationItem


def list_notifications(session: Session, user: User) -> list[NotificationItem]:
    """This person's notifications, newest first."""
    statement = (
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())  # type: ignore[attr-defined]
    )
    return [
        NotificationItem(
            id=n.id,  # type: ignore[arg-type]
            title=n.title,
            body=n.body,
            kind=n.kind,
            time=stamp(n.created_at),
            read=n.read,
            to=None,
        )
        for n in session.exec(statement).all()
    ]


def mark_notifications_read(session: Session, user: User) -> dict:
    """Mark every unread notification for this person as read."""
    statement = select(Notification).where(
        Notification.user_id == user.id, Notification.read == False  # noqa: E712
    )
    updated = 0
    for notification in session.exec(statement).all():
        notification.read = True
        session.add(notification)
        updated += 1
    session.commit()
    return {"status": "ok", "updated": updated}
