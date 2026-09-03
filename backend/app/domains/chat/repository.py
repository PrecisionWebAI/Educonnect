from sqlmodel import Session, select

from .models import ChatMessage, ChatThread, ChatThreadParticipant


def create_thread(
    session: Session, thread: ChatThread, participant_ids: list[int]
) -> ChatThread:
    session.add(thread)
    session.commit()
    session.refresh(thread)

    for uid in participant_ids:
        participant = ChatThreadParticipant(thread_id=thread.id, user_id=uid)
        session.add(participant)
    session.commit()

    return thread


def get_threads_for_user(session: Session, user_id: int) -> list[ChatThread]:
    statement = (
        select(ChatThread)
        .join(ChatThreadParticipant)
        .where(ChatThreadParticipant.user_id == user_id)
    )
    return list(session.exec(statement).all())


def create_message(session: Session, message: ChatMessage) -> ChatMessage:
    session.add(message)
    session.commit()
    session.refresh(message)
    return message


def get_messages_for_thread(
    session: Session, thread_id: int, skip: int = 0, limit: int = 100
) -> list[ChatMessage]:
    statement = (
        select(ChatMessage)
        .where(ChatMessage.thread_id == thread_id)
        .order_by(ChatMessage.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(session.exec(statement).all())
