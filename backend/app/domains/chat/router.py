import json

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import get_current_active_user, get_current_user_ws
from app.domains.users.models import User

from . import service
from .schemas import (
    ChatMessageCreate,
    ChatMessageRead,
    ChatThreadCreate,
    ChatThreadRead,
)
from .sockets import manager

router = APIRouter()


@router.post(
    "/threads", response_model=ChatThreadRead, status_code=status.HTTP_201_CREATED
)
def create_thread(
    thread_in: ChatThreadCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Create a new 1:1 or group thread.
    """
    return service.create_thread(
        session=session, thread_in=thread_in, current_user_id=current_user.id
    )


@router.get("/threads", response_model=list[ChatThreadRead])
def read_threads(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Fetch all threads the current user is a part of.
    """
    return service.get_threads_for_user(session=session, user_id=current_user.id)


@router.post(
    "/threads/{thread_id}/messages",
    response_model=ChatMessageRead,
    status_code=status.HTTP_201_CREATED,
)
def send_message(
    thread_id: int,
    message_in: ChatMessageCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Send a message.
    """
    return service.create_message(
        session=session,
        thread_id=thread_id,
        message_in=message_in,
        sender_id=current_user.id,
    )


@router.get("/threads/{thread_id}/messages", response_model=list[ChatMessageRead])
def read_messages(
    thread_id: int,
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Fetch message history.
    """
    return service.get_messages_for_thread(
        session=session, thread_id=thread_id, skip=skip, limit=limit
    )


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket, token: str, session: Session = Depends(get_session)
):
    user = await get_current_user_ws(token, session)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(websocket, user.id)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                action = payload.get("action")
                if action == "send_message":
                    thread_id = payload.get("thread_id")
                    content = payload.get("content_text")
                    attachment_url = payload.get("attachment_url")

                    if thread_id and content:
                        msg_in = ChatMessageCreate(
                            content_text=content, attachment_url=attachment_url
                        )
                        service.create_message(session, thread_id, msg_in, user.id)
            except Exception:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket, user.id)
