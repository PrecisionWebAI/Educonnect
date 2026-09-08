from sqlmodel import Session

from app.core.security import create_access_token, verify_password

from . import repository


def authenticate_user(session: Session, username: str, password: str) -> str | None:
    user = repository.get_user_by_email(session, email=username)

    if not user or not verify_password(password, user.hashed_password):
        return None

    return create_access_token(subject=user.id)


class ScopeValidator:
    """
    Validates dynamic scopes like OWN, CHILDREN, ASSIGNED_CLASSES.
    """

    @staticmethod
    def validate(user, permission: str, session: Session, **kwargs) -> bool:
        from app.domains.users.models import RoleEnum

        if not session:
            # If no session is provided, we can't perform DB scope checks.
            # In a strict implementation, this might deny by default.
            return True

        student_id = kwargs.get("student_id")
        class_id = kwargs.get("class_id")
        teacher_id = kwargs.get("teacher_id")

        # Admin/Director typically bypass scope restrictions
        if user.role in [RoleEnum.admin, RoleEnum.director]:
            return True

        # Teacher -> Own Profile Scope
        if user.role == RoleEnum.teacher and teacher_id:
            from sqlmodel import select

            from app.domains.teachers.models import TeacherProfile

            tp = session.exec(
                select(TeacherProfile).where(TeacherProfile.user_id == user.id)
            ).first()
            if not tp or str(tp.id) != str(teacher_id):
                return False

        # Global permissions that don't require scoped parameters
        global_permissions = [
            "dashboard.read",
            "profile.read",
            "profile.update",
            "profile.change_password",
            "profile.change_avatar",
            "settings.read",
            "ai_copilot.use",
            "messages.read",
            "messages.send",
        ]

        # Parent -> Child Scope
        if user.role == RoleEnum.guardian:
            if permission in global_permissions:
                return True
            if not student_id:
                # Guardians cannot perform un-scoped reads for resource-specific endpoints
                return False
            from sqlmodel import select

            from app.domains.students.models import StudentParentRelationship

            rel = session.exec(
                select(StudentParentRelationship)
                .where(StudentParentRelationship.parent_user_id == user.id)
                .where(StudentParentRelationship.student_id == student_id)
            ).first()
            if not rel:
                return False

        # Student -> Class/Own Scope
        if user.role == RoleEnum.student:
            if permission in global_permissions:
                return True
            from sqlmodel import select

            from app.domains.students.models import StudentProfile

            sp = session.exec(
                select(StudentProfile).where(StudentProfile.user_id == user.id)
            ).first()
            if not sp:
                return False

            # If they request a specific student_id, it must be their own
            if student_id and str(sp.id) != str(student_id):
                return False

            # If they request a specific class_id, it must be their own class
            return not (class_id and str(sp.grade_class_id) != str(class_id))

        # Teacher -> Class/Subject Scope
        if user.role == RoleEnum.teacher:
            # If no scoped parameter is present, we allow it to pass so the service can filter the list (e.g. own payroll)
            # However, if they are modifying or accessing a specific class/student, we validate it.
            if not class_id and not student_id and not teacher_id:
                return True

            # Resolve student_id to class_id if class_id is not provided
            if student_id and not class_id:
                from app.domains.students.models import StudentProfile

                student = session.get(StudentProfile, int(student_id))
                if student:
                    class_id = student.grade_class_id

            if class_id:
                from sqlmodel import select

                from app.domains.teachers.models import (
                    ClassTeacherAssignment,
                    TeacherAssignment,
                    TeacherProfile,
                )

                # Check Class Teacher
                ct = session.exec(
                    select(ClassTeacherAssignment)
                    .join(
                        TeacherProfile,
                        ClassTeacherAssignment.teacher_id == TeacherProfile.id,
                    )
                    .where(TeacherProfile.user_id == user.id)
                    .where(ClassTeacherAssignment.grade_class_id == class_id)
                ).first()
                if ct:
                    return True

                subject_id = kwargs.get("subject_id")
                if not subject_id:
                    if permission.endswith(".read") or permission.endswith(".monitor"):
                        st_any = session.exec(
                            select(TeacherAssignment)
                            .join(
                                TeacherProfile,
                                TeacherAssignment.teacher_id == TeacherProfile.id,
                            )
                            .where(TeacherProfile.user_id == user.id)
                            .where(TeacherAssignment.grade_class_id == class_id)
                        ).first()
                        if st_any:
                            return True
                    return False

                # Check Subject Teacher for specific subject
                st = session.exec(
                    select(TeacherAssignment)
                    .join(
                        TeacherProfile,
                        TeacherAssignment.teacher_id == TeacherProfile.id,
                    )
                    .where(TeacherProfile.user_id == user.id)
                    .where(TeacherAssignment.grade_class_id == class_id)
                    .where(TeacherAssignment.subject_id == subject_id)
                ).first()
                if not st:
                    return False
            else:
                # If they passed student_id but we couldn't resolve class_id, deny.
                if student_id:
                    return False

        return True

    @staticmethod
    def is_class_teacher(session: Session, user_id: int, class_id: int) -> bool:
        from sqlmodel import select

        from app.domains.teachers.models import ClassTeacherAssignment, TeacherProfile

        ct = session.exec(
            select(ClassTeacherAssignment)
            .join(
                TeacherProfile, ClassTeacherAssignment.teacher_id == TeacherProfile.id
            )
            .where(TeacherProfile.user_id == user_id)
            .where(ClassTeacherAssignment.grade_class_id == class_id)
        ).first()
        return ct is not None

    @staticmethod
    def is_teacher_assigned_to_class(
        session: Session, user_id: int, class_id: int
    ) -> bool:
        from sqlmodel import select

        from app.domains.teachers.models import TeacherAssignment, TeacherProfile

        st = session.exec(
            select(TeacherAssignment)
            .join(TeacherProfile, TeacherAssignment.teacher_id == TeacherProfile.id)
            .where(TeacherProfile.user_id == user_id)
            .where(TeacherAssignment.grade_class_id == class_id)
        ).first()
        return st is not None

    @staticmethod
    def is_teacher_assigned_to_subject(
        session: Session, user_id: int, class_id: int, subject_id: int
    ) -> bool:
        from sqlmodel import select

        from app.domains.teachers.models import TeacherAssignment, TeacherProfile

        st = session.exec(
            select(TeacherAssignment)
            .join(TeacherProfile, TeacherAssignment.teacher_id == TeacherProfile.id)
            .where(TeacherProfile.user_id == user_id)
            .where(TeacherAssignment.grade_class_id == class_id)
            .where(TeacherAssignment.subject_id == subject_id)
        ).first()
        return st is not None


class AuthorizationService:
    """
    Core engine for Permission-Based Access Control (PBAC).
    """

    @staticmethod
    def has_permission(user, permission: str, session: Session = None) -> bool:
        # Fast path: if the user object already carries a resolved permissions list
        # (populated by router._build_user_dict at login / /me), use it directly.
        if (
            hasattr(user, "_resolved_permissions")
            and user._resolved_permissions is not None
        ):
            return permission in user._resolved_permissions

        # DB path: look up the role's permissions.
        if session is not None:
            from app.domains.auth.permissions_repository import get_permissions_for_role

            perms = set(get_permissions_for_role(session, user.role.value))
            # Cache on the user object for the lifetime of the request.
            user._resolved_permissions = perms
            return permission in perms

        # Fallback to the static map if no session is available (tests, etc.)
        from app.domains.auth.permissions import ROLE_PERMISSIONS_MAP

        role_val = user.role.value
        if role_val not in ROLE_PERMISSIONS_MAP:
            return False
        return permission in ROLE_PERMISSIONS_MAP[role_val]

    @staticmethod
    def can(user, permission: str, session: Session = None, **kwargs) -> bool:
        """
        Phase 1: Validates base role permission.
        Phase 2: Will dynamically validate scopes using session and kwargs.
        """
        # 1. Base Permission Check
        if not AuthorizationService.has_permission(user, permission, session=session):
            return False

        # 2. Scope Validation
        if kwargs and session:
            return ScopeValidator.validate(user, permission, session, **kwargs)

        return True

    @staticmethod
    def can_teach_class(user, session: Session, class_id: int) -> bool:
        from app.domains.users.models import RoleEnum

        if user.role in [RoleEnum.admin, RoleEnum.director, RoleEnum.principal]:
            return True
        if user.role != RoleEnum.teacher:
            return False
        return ScopeValidator.is_teacher_assigned_to_class(
            session, user.id, class_id
        ) or ScopeValidator.is_class_teacher(session, user.id, class_id)

    @staticmethod
    def can_teach_subject(
        user, session: Session, class_id: int, subject_id: int
    ) -> bool:
        from app.domains.users.models import RoleEnum

        if user.role in [RoleEnum.admin, RoleEnum.director, RoleEnum.principal]:
            return True
        if user.role != RoleEnum.teacher:
            return False
        return ScopeValidator.is_teacher_assigned_to_subject(
            session, user.id, class_id, subject_id
        )

    @staticmethod
    def can_manage_class(user, session: Session, class_id: int) -> bool:
        from app.domains.users.models import RoleEnum

        if user.role in [RoleEnum.admin, RoleEnum.director, RoleEnum.principal]:
            return True
        if user.role != RoleEnum.teacher:
            return False
        return ScopeValidator.is_class_teacher(session, user.id, class_id)

    @staticmethod
    def can_manage_class_attendance(user, session: Session, class_id: int) -> bool:
        # For attendance, maybe any assigned teacher can mark it, or only class teacher.
        # According to EduConnect standard, class attendance is marked by Class Teacher.
        return AuthorizationService.can_manage_class(user, session, class_id)
