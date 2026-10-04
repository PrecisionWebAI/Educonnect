"""Authentication + authorization (PBAC) in a multi-role world.

`authenticate_user` turns an e-mail/password pair into a token. The interesting
part is `AuthorizationService`: the permissions a person holds are the **union of
their roles**, so a principal who also teaches can approve a paper (principal
permission) *and* mark attendance (teacher permission) with one login.

Scope rules are per role as well, and a request is allowed when **any** of the
roles the person holds allows it. That is what makes several roles additive
instead of mutually exclusive:

    principal + guardian -> may open any class (principal)
                            and their own child's records (guardian)
    teacher + librarian  -> may mark their classes (teacher)
                            and issue books (librarian)

Before this, a person had exactly one role and the checks read
`user.role == RoleEnum.teacher`; the equivalent now is membership of the loaded
role set, via `roles_of(user)` from `auth/roles.py`.
"""

from sqlmodel import Session, select

from app.core.security import create_access_token, verify_password
from app.domains.auth.roles import role_codenames, roles_of
from app.domains.users.models import User

from . import repository

#: Permissions that describe the caller's own account rather than a record: they
#: never need a scope parameter, so every role may use them.
GLOBAL_PERMISSIONS = frozenset(
    {
        "dashboard.read",
        "profile.read",
        "profile.update",
        "profile.change_password",
        "profile.change_avatar",
        "settings.read",
        "ai_copilot.use",
        "messages.read",
        "messages.send",
        "announcements.read",
    }
)

#: Roles that see the whole school and skip scope narrowing entirely.
BYPASS_ROLES = frozenset({"system_admin", "owner"})

#: Roles whose scope is "the classes/subjects I am assigned to".
TEACHING_ROLES = frozenset(
    {
        "principal",
        "vice_principal",
        "hod",
        "class_teacher",
        "subject_teacher",
        "teacher",
    }
)


def authenticate_user(session: Session, username: str, password: str) -> str | None:
    user = repository.get_user_by_email(session, email=username)

    if not user or not verify_password(password, user.hashed_password):
        return None

    return create_access_token(subject=user.id)


def build_session_user(
    user: User, session: Session, actor_id: int | None = None
) -> dict:
    """The identity payload that login and `/auth/me` return.

    `roles` is a list because a person holds several; `permissions` is the union
    across them - exactly what the backend enforces - and `role` repeats the
    primary role for the places that still want a single answer.

    When `actor_id` is given the session is an impersonated one, and
    `impersonatedBy` names the administrator the UI should offer to return to.
    """
    from app.domains.auth.permissions_repository import get_permissions_for_roles

    held = role_codenames(session, user.id)
    permissions = sorted(get_permissions_for_roles(session, held))
    # Cache on the object so the rest of this request does not query again.
    user._resolved_permissions = set(permissions)

    roles = [codename.upper() for codename in held]
    payload: dict = {
        "id": user.id,
        "username": user.email.split("@")[0],
        "email": user.email,
        "fullName": user.full_name,
        "roles": roles,
        "role": roles[0] if roles else "STAFF",
        "permissions": permissions,
    }

    if actor_id is not None:
        actor = session.get(User, actor_id)
        payload["impersonatedBy"] = (
            {"id": actor.id, "fullName": actor.full_name, "email": actor.email}
            if actor
            else None
        )
    return payload


class ScopeValidator:
    """Per-role scope rules. One decision per held role, any of them wins."""

    @staticmethod
    def validate(user, permission: str, session: Session, **kwargs) -> bool:
        if not session:
            # Without a session the DB scope checks cannot run; the base
            # permission check has already decided, so do not invent a denial.
            return True

        held = roles_of(user) or set(role_codenames(session, user.id))
        if not held:
            return False
        if held & BYPASS_ROLES:
            return True

        checks: list[bool] = []
        if "guardian" in held:
            checks.append(
                ScopeValidator._guardian_allows(user, permission, session, kwargs)
            )
        if "student" in held:
            checks.append(
                ScopeValidator._student_allows(user, permission, session, kwargs)
            )
        if held & TEACHING_ROLES:
            checks.append(
                ScopeValidator._teaching_allows(user, permission, session, kwargs)
            )

        if not checks:
            # Roles with no scope of their own (librarian, accountant, transport,
            # staff): the permission check already decided.
            return True
        # Additive: holding a second role can only widen access, never narrow it.
        return any(checks)

    # ---- guardian: only their own children --------------------------------
    @staticmethod
    def _guardian_allows(user, permission: str, session: Session, kwargs) -> bool:
        if permission in GLOBAL_PERMISSIONS:
            return True
        student_id = kwargs.get("student_id")
        if not student_id:
            # An unscoped list request ("my children's fees") is filtered by the
            # service layer, so it may pass; a specific record may not.
            return False
        from app.domains.students.models import StudentParentRelationship

        relationship = session.exec(
            select(StudentParentRelationship)
            .where(StudentParentRelationship.parent_user_id == user.id)
            .where(StudentParentRelationship.student_id == int(student_id))
        ).first()
        return relationship is not None

    # ---- student: their own record only -----------------------------------
    @staticmethod
    def _student_allows(user, permission: str, session: Session, kwargs) -> bool:
        if permission in GLOBAL_PERMISSIONS:
            return True
        from app.domains.students.models import StudentProfile

        profile = session.exec(
            select(StudentProfile).where(StudentProfile.user_id == user.id)
        ).first()
        if not profile:
            return False

        student_id = kwargs.get("student_id")
        if student_id and str(profile.id) != str(student_id):
            return False

        class_id = kwargs.get("class_id")
        # The class they ask for must be their own (when they ask for one).
        return not (class_id and str(profile.classroom_id) != str(class_id))

    # ---- teaching roles: the classes/subjects they are assigned to --------
    @staticmethod
    def _teaching_allows(user, permission: str, session: Session, kwargs) -> bool:
        student_id = kwargs.get("student_id")
        class_id = kwargs.get("class_id")
        teacher_id = kwargs.get("teacher_id")

        # A teacher may always read their own staff record (e.g. own payslip).
        if teacher_id:
            from app.domains.teachers.models import TeacherProfile

            profile = session.exec(
                select(TeacherProfile).where(TeacherProfile.user_id == user.id)
            ).first()
            return bool(profile and str(profile.id) == str(teacher_id))

        if not class_id and not student_id:
            # Unscoped list: allowed so the service can filter it (own payroll,
            # own classes) instead of the router having to know every case.
            return True

        if student_id and not class_id:
            from app.domains.students.models import StudentProfile

            student = session.get(StudentProfile, int(student_id))
            if student:
                class_id = student.classroom_id

        if not class_id:
            return False

        from app.domains.teachers.models import ClassTeacherAssignment, TeacherProfile

        class_teacher = session.exec(
            select(ClassTeacherAssignment)
            .join(
                TeacherProfile, ClassTeacherAssignment.teacher_id == TeacherProfile.id
            )
            .where(TeacherProfile.user_id == user.id)
            .where(ClassTeacherAssignment.classroom_id == class_id)
        ).first()
        if class_teacher:
            return True

        subject_id = kwargs.get("subject_id")
        if not subject_id:
            # Reading/monitoring the whole class is fine for a subject teacher of
            # that class; writing to a specific subject is not.
            if permission.endswith(".read") or permission.endswith(".monitor"):
                return ScopeValidator.is_teacher_assigned_to_class(
                    session, user.id, int(class_id)
                )
            return False

        return ScopeValidator.is_teacher_assigned_to_subject(
            session, user.id, int(class_id), int(subject_id)
        )

    # ---- shared queries (unchanged: one indexed lookup each) --------------
    @staticmethod
    def is_class_teacher(session: Session, user_id: int, class_id: int) -> bool:
        from app.domains.teachers.models import ClassTeacherAssignment, TeacherProfile

        found = session.exec(
            select(ClassTeacherAssignment)
            .join(
                TeacherProfile, ClassTeacherAssignment.teacher_id == TeacherProfile.id
            )
            .where(TeacherProfile.user_id == user_id)
            .where(ClassTeacherAssignment.classroom_id == class_id)
        ).first()
        return found is not None

    @staticmethod
    def is_teacher_assigned_to_class(
        session: Session, user_id: int, class_id: int
    ) -> bool:
        from app.domains.teachers.models import TeacherAssignment, TeacherProfile

        found = session.exec(
            select(TeacherAssignment)
            .join(TeacherProfile, TeacherAssignment.teacher_id == TeacherProfile.id)
            .where(TeacherProfile.user_id == user_id)
            .where(TeacherAssignment.classroom_id == class_id)
        ).first()
        return found is not None

    @staticmethod
    def is_teacher_assigned_to_subject(
        session: Session, user_id: int, class_id: int, subject_id: int
    ) -> bool:
        from app.domains.teachers.models import TeacherAssignment, TeacherProfile

        found = session.exec(
            select(TeacherAssignment)
            .join(TeacherProfile, TeacherAssignment.teacher_id == TeacherProfile.id)
            .where(TeacherProfile.user_id == user_id)
            .where(TeacherAssignment.classroom_id == class_id)
            .where(TeacherAssignment.subject_id == subject_id)
        ).first()
        return found is not None


class AuthorizationService:
    """Core engine for Permission-Based Access Control (PBAC)."""

    @staticmethod
    def has_permission(user, permission: str, session: Session = None) -> bool:
        """True when **any** role the person holds grants `permission`."""
        # Fast path: the union was resolved earlier in this request (login, /me).
        cached = getattr(user, "_resolved_permissions", None)
        if cached is not None:
            return permission in cached

        if session is not None:
            from app.domains.auth.permissions_repository import (
                get_permissions_for_roles,
            )

            held = roles_of(user) or set(role_codenames(session, user.id))
            permissions = get_permissions_for_roles(session, held)
            user._resolved_permissions = permissions
            return permission in permissions

        # Fallback with no session (scripts, tests): union the static map.
        from app.domains.auth.permissions import ROLE_PERMISSIONS_MAP

        return any(
            permission in ROLE_PERMISSIONS_MAP.get(role, []) for role in roles_of(user)
        )

    @staticmethod
    def can(user, permission: str, session: Session = None, **kwargs) -> bool:
        """Base permission **and** scope. `kwargs` carries ids from the request."""
        if not AuthorizationService.has_permission(user, permission, session=session):
            return False

        if kwargs and session:
            return ScopeValidator.validate(user, permission, session, **kwargs)

        return True

    @staticmethod
    def can_teach_class(user, session: Session, class_id: int) -> bool:
        held = roles_of(user)
        if held & BYPASS_ROLES:
            return True
        if not held & TEACHING_ROLES:
            return False
        return ScopeValidator.is_teacher_assigned_to_class(
            session, user.id, class_id
        ) or ScopeValidator.is_class_teacher(session, user.id, class_id)

    @staticmethod
    def can_teach_subject(
        user, session: Session, class_id: int, subject_id: int
    ) -> bool:
        held = roles_of(user)
        if held & BYPASS_ROLES:
            return True
        if not held & TEACHING_ROLES:
            return False
        return ScopeValidator.is_teacher_assigned_to_subject(
            session, user.id, class_id, subject_id
        )

    @staticmethod
    def can_manage_class(user, session: Session, class_id: int) -> bool:
        held = roles_of(user)
        if held & BYPASS_ROLES:
            return True
        if not held & TEACHING_ROLES:
            return False
        return ScopeValidator.is_class_teacher(session, user.id, class_id)

    @staticmethod
    def can_manage_class_attendance(user, session: Session, class_id: int) -> bool:
        # Class attendance is marked by the class teacher.
        return AuthorizationService.can_manage_class(user, session, class_id)
