"""Removing a login - and everything that hangs off it.

A login is a person's account, cited by half the product: their roles, the chat threads
they are in, the messages they wrote, their notifications, the tickets they raised and
the leave they asked for. Deleting the `user` row alone leaves all of that pointing at
nothing, so every screen that removes a person goes through here.

Only ever called when the login has **nothing left to open** - `release_login` in
`app/core/lifecycle.py` is the rule that decides that, because the same person may still
be somebody here (a parent whose child left, a teacher who was let go).
"""

from uuid import UUID

from sqlmodel import Session, select

from app.domains.auth.models import UserRole
from app.domains.users.models import User


def delete_login(session: Session, user_id: UUID | None) -> bool:
    """Delete a login and its role/chat/notification/ticket references.

    Returns `True` when a login was actually removed, `False` when there was none - so a
    caller can report what happened instead of guessing.
    """
    if not user_id:
        return False
    user = session.get(User, user_id)
    if user is None:
        return False

    from app.domains.chat.models import ChatMessage, ChatThreadParticipant
    from app.domains.operations.models import LeaveRequest, Notification, SupportTicket

    for row in session.exec(select(UserRole).where(UserRole.user_id == user_id)).all():
        session.delete(row)
    for row in session.exec(
        select(ChatThreadParticipant).where(ChatThreadParticipant.user_id == user_id)
    ).all():
        session.delete(row)
    for row in session.exec(
        select(ChatMessage).where(ChatMessage.sender_id == user_id)
    ).all():
        session.delete(row)
    for row in session.exec(
        select(Notification).where(Notification.user_id == user_id)
    ).all():
        session.delete(row)
    for row in session.exec(
        select(SupportTicket).where(SupportTicket.reporter_user_id == user_id)
    ).all():
        session.delete(row)
    for row in session.exec(
        select(LeaveRequest).where(LeaveRequest.requester_user_id == user_id)
    ).all():
        session.delete(row)

    session.delete(user)
    session.commit()
    return True
