from sqlmodel import Session, select

from app.domains.users.models import RoleEnum, User

from . import repository
from .models import ChatMessage, ChatThread
from .schemas import ChatMessageCreate, ChatMessageRead, ChatThreadCreate


def get_authorized_contact_user_ids(
    session: Session, current_user: User
) -> set[int] | None:
    """
    Returns a set of authorized user_ids the current_user can chat with.
    If None is returned, the user can chat with anyone (e.g. Admin/Principal).
    """
    if current_user.role in [RoleEnum.admin, RoleEnum.director, RoleEnum.principal]:
        return None

    allowed_ids = set()

    # Everyone can talk to Admins and Principals
    admins_principals = session.exec(
        select(User.id).where(
            User.role.in_([RoleEnum.admin, RoleEnum.director, RoleEnum.principal])
        )
    ).all()
    allowed_ids.update(admins_principals)

    if current_user.role == RoleEnum.teacher:
        from app.domains.students.models import (
            StudentParentRelationship,
            StudentProfile,
        )
        from app.domains.teachers.models import (
            ClassTeacherAssignment,
            TeacherAssignment,
            TeacherProfile,
        )

        # Teachers can talk to other Teachers
        other_teachers = session.exec(
            select(User.id).where(User.role == RoleEnum.teacher)
        ).all()
        allowed_ids.update(other_teachers)

        tp = session.exec(
            select(TeacherProfile).where(TeacherProfile.user_id == current_user.id)
        ).first()
        if tp:
            assigned_classes_sub = session.exec(
                select(TeacherAssignment.grade_class_id).where(
                    TeacherAssignment.teacher_id == tp.id
                )
            ).all()
            assigned_classes_ct = session.exec(
                select(ClassTeacherAssignment.grade_class_id).where(
                    ClassTeacherAssignment.teacher_id == tp.id
                )
            ).all()
            all_assigned_class_ids = list(
                set(assigned_classes_sub + assigned_classes_ct)
            )

            if all_assigned_class_ids:
                students = session.exec(
                    select(StudentProfile).where(
                        StudentProfile.grade_class_id.in_(all_assigned_class_ids)
                    )
                ).all()
                student_ids = [s.id for s in students]
                student_user_ids = [s.user_id for s in students if s.user_id]
                allowed_ids.update(student_user_ids)

                if student_ids:
                    parents = session.exec(
                        select(StudentParentRelationship.parent_user_id).where(
                            StudentParentRelationship.student_id.in_(student_ids)
                        )
                    ).all()
                    allowed_ids.update(parents)

        return allowed_ids

    if current_user.role == RoleEnum.guardian:
        from app.domains.students.models import (
            StudentParentRelationship,
            StudentProfile,
        )
        from app.domains.teachers.models import (
            ClassTeacherAssignment,
            TeacherAssignment,
            TeacherProfile,
        )

        rels = session.exec(
            select(StudentParentRelationship.student_id).where(
                StudentParentRelationship.parent_user_id == current_user.id
            )
        ).all()
        if rels:
            students = session.exec(
                select(StudentProfile).where(StudentProfile.id.in_(rels))
            ).all()
            class_ids = list({s.grade_class_id for s in students if s.grade_class_id})

            if class_ids:
                sub_teachers = session.exec(
                    select(TeacherAssignment.teacher_id).where(
                        TeacherAssignment.grade_class_id.in_(class_ids)
                    )
                ).all()
                ct_teachers = session.exec(
                    select(ClassTeacherAssignment.teacher_id).where(
                        ClassTeacherAssignment.grade_class_id.in_(class_ids)
                    )
                ).all()
                all_teacher_ids = list(set(sub_teachers + ct_teachers))

                if all_teacher_ids:
                    teachers_user_ids = session.exec(
                        select(TeacherProfile.user_id).where(
                            TeacherProfile.id.in_(all_teacher_ids)
                        )
                    ).all()
                    allowed_ids.update(teachers_user_ids)

        return allowed_ids

    if current_user.role == RoleEnum.student:
        from app.domains.students.models import StudentProfile
        from app.domains.teachers.models import (
            ClassTeacherAssignment,
            TeacherAssignment,
            TeacherProfile,
        )

        sp = session.exec(
            select(StudentProfile).where(StudentProfile.user_id == current_user.id)
        ).first()
        if sp and sp.grade_class_id:
            sub_teachers = session.exec(
                select(TeacherAssignment.teacher_id).where(
                    TeacherAssignment.grade_class_id == sp.grade_class_id
                )
            ).all()
            ct_teachers = session.exec(
                select(ClassTeacherAssignment.teacher_id).where(
                    ClassTeacherAssignment.grade_class_id == sp.grade_class_id
                )
            ).all()
            all_teacher_ids = list(set(sub_teachers + ct_teachers))
            if all_teacher_ids:
                teachers_user_ids = session.exec(
                    select(TeacherProfile.user_id).where(
                        TeacherProfile.id.in_(all_teacher_ids)
                    )
                ).all()
                allowed_ids.update(teachers_user_ids)

        return allowed_ids

    return allowed_ids


def resolve_thread_display_name(
    session: Session, thread: ChatThread, current_user_id: int
) -> str:
    if thread.is_group:
        return thread.name or f"Group #{thread.id}"

    parts = repository.get_thread_participants(session, thread.id)
    if len(parts) == 2 or not thread.name:
        other_part = next((p for p in parts if p.user_id != current_user_id), None)
        if other_part:
            other_user = session.get(User, other_part.user_id)
            if other_user and other_user.full_name:
                return other_user.full_name

    return thread.name or f"Chat #{thread.id}"


def create_thread(
    session: Session, thread_in: ChatThreadCreate, current_user_id: int
) -> ChatThread:
    # Validate PBAC boundaries
    from fastapi import HTTPException

    current_user = session.get(User, current_user_id)
    authorized_ids = get_authorized_contact_user_ids(session, current_user)

    if authorized_ids is not None:
        for p_id in thread_in.participant_user_ids:
            if p_id not in authorized_ids:
                raise HTTPException(
                    status_code=403, detail=f"Not authorized to message user {p_id}"
                )

    participants = set(thread_in.participant_user_ids)
    participants.add(current_user_id)

    # For 1:1 direct threads, reuse existing thread if one already exists with EXACTLY these two participants
    if not thread_in.is_group and len(participants) == 2:
        other_user_id = next(uid for uid in participants if uid != current_user_id)
        current_threads = repository.get_threads_for_user(session, current_user_id)
        for t in current_threads:
            if not t.is_group:
                thread_parts = repository.get_thread_participants(session, t.id)
                p_ids = {p.user_id for p in thread_parts}
                if p_ids == {current_user_id, other_user_id}:
                    display_name = resolve_thread_display_name(
                        session, t, current_user_id
                    )
                    return ChatThread(id=t.id, name=display_name, is_group=t.is_group)

    # For 1:1 direct threads, keep name None in DB so each participant dynamically sees the other user's name
    thread_name = thread_in.name if thread_in.is_group else None

    db_thread = ChatThread(name=thread_name, is_group=thread_in.is_group)
    saved = repository.create_thread(session, db_thread, list(participants))
    display_name = resolve_thread_display_name(session, saved, current_user_id)
    return ChatThread(id=saved.id, name=display_name, is_group=saved.is_group)


def get_chat_contacts(session: Session, current_user: User) -> list[dict]:
    statement = select(User).where(User.is_active, User.id != current_user.id)
    all_users = session.exec(statement).all()

    authorized_ids = get_authorized_contact_user_ids(session, current_user)

    contacts = []
    for u in all_users:
        if authorized_ids is not None and u.id not in authorized_ids:
            continue

        role_str = u.role.value if hasattr(u.role, "value") else str(u.role)
        role_label = role_str.capitalize()

        contacts.append(
            {
                "id": u.id,
                "name": u.full_name,
                "email": u.email,
                "role": role_str,
                "roleTag": f"School {role_label}",
                "group": False,
                "relationship": f"{role_label} • {u.email}",
                "online": True,
            }
        )

    # Include group spaces from DB
    group_threads = session.exec(select(ChatThread).where(ChatThread.is_group)).all()
    for g in group_threads:
        contacts.append(
            {
                "id": 1000 + (g.id or 0),
                "name": g.name or f"Group #{g.id}",
                "email": "",
                "role": "group",
                "roleTag": "School Group Space",
                "group": True,
                "relationship": "Class & Faculty Space",
                "threadId": g.id,
                "online": True,
            }
        )

    return contacts


DEFAULT_CHANNELS = [
    {"id": 1, "name": "P. Menon (Class Teacher)", "is_group": False},
    {"id": 2, "name": "Class 10-A Notice & Discussions", "is_group": True},
    {"id": 3, "name": "Diya Sharma (Maths Teacher)", "is_group": False},
    {"id": 4, "name": "Science Dept & Faculty", "is_group": True},
    {"id": 5, "name": "Accounts & Fees Desk", "is_group": False},
    {"id": 6, "name": "Dr. S. Nair (Physics HOD)", "is_group": False},
]


def ensure_default_threads(session: Session, user_id: int):
    for ch in DEFAULT_CHANNELS:
        thread = session.get(ChatThread, ch["id"])
        if not thread:
            thread = ChatThread(
                id=ch["id"],
                name=ch["name"],
                is_group=ch["is_group"],
            )
            session.add(thread)
            session.commit()
            session.refresh(thread)

        participants = repository.get_thread_participants(session, thread.id)
        if user_id not in [p.user_id for p in participants]:
            participant = repository.ChatThreadParticipant(
                thread_id=thread.id, user_id=user_id
            )
            session.add(participant)
            session.commit()

    try:
        from sqlalchemy import text

        session.execute(
            text(
                "SELECT setval(pg_get_serial_sequence('chatthread', 'id'), COALESCE(max(id), 1)) FROM chatthread;"
            )
        )
        session.commit()
    except Exception:
        pass


def get_threads_for_user(session: Session, user_id: int) -> list[ChatThread]:
    threads = repository.get_threads_for_user(session, user_id)
    if not threads:
        ensure_default_threads(session, user_id)
        threads = repository.get_threads_for_user(session, user_id)

    result: list[ChatThread] = []
    for t in threads:
        display_name = resolve_thread_display_name(session, t, user_id)
        result.append(ChatThread(id=t.id, name=display_name, is_group=t.is_group))
    return result


def create_message(
    session: Session, thread_id: int, message_in: ChatMessageCreate, sender_id: int
) -> ChatMessageRead:
    # Ensure thread exists in database; if not, create it
    thread = session.get(ChatThread, thread_id)
    if not thread:
        default_ch = next(
            (ch for ch in DEFAULT_CHANNELS if ch["id"] == thread_id), None
        )
        name = default_ch["name"] if default_ch else f"Conversation #{thread_id}"
        is_group = default_ch["is_group"] if default_ch else False
        thread = ChatThread(id=thread_id, name=name, is_group=is_group)
        session.add(thread)
        session.commit()
        session.refresh(thread)

    # Ensure sender is registered as participant in this thread
    participants = repository.get_thread_participants(session, thread_id)
    if sender_id not in [p.user_id for p in participants]:
        new_participant = repository.ChatThreadParticipant(
            thread_id=thread_id, user_id=sender_id
        )
        session.add(new_participant)
        session.commit()
        participants.append(new_participant)

    db_message = ChatMessage(
        thread_id=thread_id,
        sender_id=sender_id,
        content_text=message_in.content_text,
        attachment_url=message_in.attachment_url,
    )
    saved_msg = repository.create_message(session, db_message)

    # Lookup sender info
    sender = session.get(User, sender_id)
    sender_name = sender.full_name if sender else f"User #{sender_id}"
    sender_role = (
        (sender.role.value if hasattr(sender.role, "value") else str(sender.role))
        if sender and sender.role
        else None
    )

    # Broadcast to all participants
    participants = repository.get_thread_participants(session, thread_id)
    msg_data = {
        "event": "new_message",
        "message": {
            "id": saved_msg.id,
            "thread_id": saved_msg.thread_id,
            "sender_id": saved_msg.sender_id,
            "sender_name": sender_name,
            "sender_role": sender_role,
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
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(manager.broadcast_to_user(participant.user_id, msg_data))
        except RuntimeError:
            try:
                asyncio.run(manager.broadcast_to_user(participant.user_id, msg_data))
            except Exception:
                pass

    return ChatMessageRead(
        id=saved_msg.id,
        thread_id=saved_msg.thread_id,
        sender_id=saved_msg.sender_id,
        sender_name=sender_name,
        sender_role=sender_role,
        content_text=saved_msg.content_text,
        attachment_url=saved_msg.attachment_url,
        created_at=saved_msg.created_at,
    )


def get_messages_for_thread(
    session: Session, thread_id: int, skip: int = 0, limit: int = 100
) -> list[ChatMessageRead]:
    db_msgs = repository.get_messages_for_thread(session, thread_id, skip, limit)
    user_cache: dict[int, User | None] = {}

    result: list[ChatMessageRead] = []
    for m in db_msgs:
        if m.sender_id not in user_cache:
            user_cache[m.sender_id] = session.get(User, m.sender_id)
        sender = user_cache[m.sender_id]
        sender_name = sender.full_name if sender else f"User #{m.sender_id}"
        sender_role = (
            (sender.role.value if hasattr(sender.role, "value") else str(sender.role))
            if sender and sender.role
            else None
        )

        result.append(
            ChatMessageRead(
                id=m.id,
                thread_id=m.thread_id,
                sender_id=m.sender_id,
                sender_name=sender_name,
                sender_role=sender_role,
                content_text=m.content_text,
                attachment_url=m.attachment_url,
                created_at=m.created_at,
            )
        )
    return result
