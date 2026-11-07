from uuid import UUID
from sqlmodel import Session, select

from app.domains.auth.models import Role, UserRole
from app.domains.auth.roles import has_role, primary_role_name, primary_role_names
from app.domains.users.models import User

from . import repository
from .models import ChatMessage, ChatThread
from .schemas import ChatMessageCreate, ChatMessageRead, ChatThreadCreate


def _classroom_ids_of(students: list) -> set[UUID]:
    """The class-sections these students sit in (`student.classroom_id`).

    A student has **one** placement - the room - and the class and the section
    letter hang off it (`classroom.class_id` / `classroom.section_id`), so every
    question about "which class are they in" is answered from this id.
    """
    return {student.classroom_id for student in students if student.classroom_id}


def _guardian_user_ids_of_students(
    session: Session, student_ids: list[UUID]
) -> set[UUID]:
    """The logins of the guardians linked to these students, when they have one.

    A guardian is a person shared by siblings (`guardian` +
    `student_guardian_relationship`), so this reads the link and not a column on
    the child; a parent who has no login yet contributes nothing.
    """
    from app.domains.students.models import Guardian, StudentGuardianRelationship

    if not student_ids:
        return set()
    return {
        user_id
        for user_id in session.exec(
            select(Guardian.user_id)
            .join(
                StudentGuardianRelationship,
                StudentGuardianRelationship.guardian_id == Guardian.id,
            )
            .where(StudentGuardianRelationship.student_id.in_(student_ids))
        ).all()
        if user_id
    }


def _teacher_user_ids_of_classrooms(
    session: Session, classroom_ids: set[UUID]
) -> set[UUID]:
    """The logins of the teachers who work in these class-sections.

    A teacher reaches a child two ways, and both count: taking a subject in the
    room (`subjectteacher`, keyed by `classroom_id`) or running it
    (`classroom.class_teacher_id`). The `employee` row is what holds the login.
    """
    from app.domains.academics.models import Classroom, SubjectTeacher
    from app.domains.staff.models import Employee

    if not classroom_ids:
        return set()
    employee_ids = set(
        session.exec(
            select(SubjectTeacher.teacher_id).where(
                SubjectTeacher.classroom_id.in_(classroom_ids)
            )
        ).all()
    )
    employee_ids.update(
        class_teacher_id
        for class_teacher_id in session.exec(
            select(Classroom.class_teacher_id).where(
                Classroom.id.in_(classroom_ids),
                Classroom.class_teacher_id.is_not(None),
            )
        ).all()
        if class_teacher_id
    )
    if not employee_ids:
        return set()
    return {
        user_id
        for user_id in session.exec(
            select(Employee.user_id).where(Employee.id.in_(employee_ids))
        ).all()
        if user_id
    }


def get_authorized_contact_user_ids(
    session: Session, current_user: User
) -> set[UUID] | None:
    """
    Returns a set of authorized user_ids the current_user can chat with.
    If None is returned, the user can chat with anyone (e.g. Admin/Principal).
    """
    if has_role(current_user, "system_admin", "school_admin", "principal", "vice_principal"):
        return None

    allowed_ids = set()

    # Everyone can talk to the leadership team.
    leadership_ids = session.exec(
        select(User.id)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .where(
            Role.codename.in_(["system_admin", "school_admin", "principal", "vice_principal"])
        )
    ).all()
    allowed_ids.update(leadership_ids)

    if has_role(current_user, "teacher", "hod"):
        from app.domains.academics.models import Classroom, SubjectTeacher
        from app.domains.staff.models import Employee
        from app.domains.students.models import Student

        # Teachers can talk to other teachers (any teaching role).
        other_teachers = session.exec(
            select(User.id)
            .join(UserRole, UserRole.user_id == User.id)
            .join(Role, Role.id == UserRole.role_id)
            .where(
                Role.codename.in_(["teacher", "hod"])
            )
        ).all()
        allowed_ids.update(set(other_teachers))

        employee = session.exec(
            select(Employee).where(Employee.user_id == current_user.id)
        ).first()
        if employee:
            # The class-sections they work in: the rooms they take a subject in,
            # plus the ones they run as class teacher.
            classroom_ids = set(
                session.exec(
                    select(SubjectTeacher.classroom_id).where(
                        SubjectTeacher.teacher_id == employee.id
                    )
                ).all()
            )
            classroom_ids.update(
                session.exec(
                    select(Classroom.id).where(
                        Classroom.class_teacher_id == employee.id
                    )
                ).all()
            )
            if classroom_ids:
                students = session.exec(
                    select(Student).where(Student.classroom_id.in_(classroom_ids))
                ).all()
                # The children themselves, and the family's login(s) - so a
                # teacher can answer the parent about the child they teach.
                allowed_ids.update(s.user_id for s in students if s.user_id)
                allowed_ids.update(
                    _guardian_user_ids_of_students(session, [s.id for s in students])
                )

        return allowed_ids

    if has_role(current_user, "guardian"):
        from app.domains.students.models import (
            Guardian,
            Student,
            StudentGuardianRelationship,
        )

        # Who this parent is: the login sits on the `guardian` row, and their
        # children are the students linked to that row (siblings share both).
        guardian = session.exec(
            select(Guardian).where(Guardian.user_id == current_user.id)
        ).first()
        if guardian:
            child_ids = list(
                session.exec(
                    select(StudentGuardianRelationship.student_id).where(
                        StudentGuardianRelationship.guardian_id == guardian.id
                    )
                ).all()
            )
            if child_ids:
                children = session.exec(
                    select(Student).where(Student.id.in_(child_ids))
                ).all()
                # The teachers of the class-section each child sits in.
                allowed_ids.update(
                    _teacher_user_ids_of_classrooms(
                        session, _classroom_ids_of(children)
                    )
                )

        return allowed_ids

    if has_role(current_user, "student"):
        from app.domains.students.models import Student

        # A student talks to the teachers of the class-section they sit in.
        student = session.exec(
            select(Student).where(Student.user_id == current_user.id)
        ).first()
        if student:
            allowed_ids.update(
                _teacher_user_ids_of_classrooms(
                    session, _classroom_ids_of([student])
                )
            )

        return allowed_ids

    return allowed_ids


def resolve_thread_display_name(
    session: Session, thread: ChatThread, current_user_id: UUID
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
    session: Session, thread_in: ChatThreadCreate, current_user_id: UUID
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

    # One lookup for every contact's display role, instead of a query per row.
    roles_by_user = primary_role_names(session, [u.id for u in all_users])

    contacts = []
    for u in all_users:
        if authorized_ids is not None and u.id not in authorized_ids:
            continue

        role_str = roles_by_user.get(u.id, "")
        role_label = role_str.replace("_", " ").capitalize()

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
                "id": g.id,
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


def get_threads_for_user(session: Session, user_id: UUID) -> list[ChatThread]:
    threads = repository.get_threads_for_user(session, user_id)

    result: list[ChatThread] = []
    for t in threads:
        display_name = resolve_thread_display_name(session, t, user_id)
        result.append(ChatThread(id=t.id, name=display_name, is_group=t.is_group))
    return result


def create_message(
    session: Session, thread_id: UUID, message_in: ChatMessageCreate, sender_id: UUID
) -> ChatMessageRead:
    # Ensure thread exists in database; if not, create it
    thread = session.get(ChatThread, thread_id)
    if not thread:
        thread = ChatThread(id=thread_id, name=f"Conversation #{thread_id}", is_group=False)
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
    sender_role = primary_role_name(session, sender_id) if sender else None

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
    session: Session, thread_id: UUID, skip: int = 0, limit: int = 100
) -> list[ChatMessageRead]:
    db_msgs = repository.get_messages_for_thread(session, thread_id, skip, limit)
    user_cache: dict[UUID, User | None] = {}
    # One query for every sender's display role (no lookup per message).
    roles_by_user = primary_role_names(session, [m.sender_id for m in db_msgs])

    result: list[ChatMessageRead] = []
    for m in db_msgs:
        if m.sender_id not in user_cache:
            user_cache[m.sender_id] = session.get(User, m.sender_id)
        sender = user_cache[m.sender_id]
        sender_name = sender.full_name if sender else f"User #{m.sender_id}"
        sender_role = roles_by_user.get(m.sender_id)

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
