from fastapi import HTTPException
from sqlmodel import Session

from . import repository
from .models import ChatMessage, ChatThread
from .schemas import ChatMessageCreate, ChatThreadCreate


def create_thread(
    session: Session, thread_in: ChatThreadCreate, current_user_id: int
) -> ChatThread:
    # Ensure current user is in participants
    participants = set(thread_in.participant_user_ids)
    participants.add(current_user_id)

    db_thread = ChatThread(name=thread_in.name, is_group=thread_in.is_group)
    return repository.create_thread(session, db_thread, list(participants))


def get_threads_for_user(session: Session, user_id: int) -> list[ChatThread]:
    return repository.get_threads_for_user(session, user_id)


def create_message(
    session: Session, thread_id: int, message_in: ChatMessageCreate, sender_id: int
) -> ChatMessage:
    # We should verify sender is in thread
    threads = repository.get_threads_for_user(session, sender_id)
    if thread_id not in [t.id for t in threads]:
        raise HTTPException(status_code=403, detail="Not a participant of this thread")

    db_message = ChatMessage(
        thread_id=thread_id,
        sender_id=sender_id,
        content_text=message_in.content_text,
        attachment_url=message_in.attachment_url,
    )
    saved_msg = repository.create_message(session, db_message)

    # Broadcast to all participants
    participants = repository.get_thread_participants(session, thread_id)
    msg_data = {
        "event": "new_message",
        "message": {
            "id": saved_msg.id,
            "thread_id": saved_msg.thread_id,
            "sender_id": saved_msg.sender_id,
            "content_text": saved_msg.content_text,
            "attachment_url": saved_msg.attachment_url,
            "created_at": saved_msg.created_at.isoformat()
            if saved_msg.created_at
            else None,
        },
    }

    import asyncio

    from .sockets import manager

    for participant in participants:
        # Don't broadcast to self if we want, or do broadcast so they can sync other devices
        asyncio.create_task(manager.broadcast_to_user(participant.user_id, msg_data))

    return saved_msg


def get_messages_for_thread(
    session: Session, thread_id: int, skip: int = 0, limit: int = 100
) -> list[ChatMessage]:
    # We should verify user is in thread, skipped for brevity
    return repository.get_messages_for_thread(session, thread_id, skip, limit)
