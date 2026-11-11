"""Settings reads: the sign-in accounts, the school's own details, security, gateways.

The users list and the school info are read from the real `user` and `school`
tables - the Settings screen shows live rows, not a copy. The security log and the
gateway statuses come from their own tables.
"""

from sqlmodel import Session, select

from app.domains.admin.platform.models import School
from app.domains.admin.users.models import User
from app.domains.auth.roles import primary_role_names

from .models import GatewayStatus as GatewayStatusModel
from .models import SecurityLog as SecurityLogModel
from .schemas import GatewayStatus, SchoolInfo, SecurityLog, SettingUser


def list_setting_users(session: Session) -> list[SettingUser]:
    """Settings > Users: every sign-in, with the role it acts as."""
    users = list(session.exec(select(User).order_by(User.full_name)).all())  # type: ignore[arg-type]
    # One query for every role instead of one per person: the screen lists the
    # whole school, so a per-user lookup is an N+1 on the slowest page.
    roles = primary_role_names(session, [user.id for user in users])
    return [
        SettingUser(
            id=user.id,  # type: ignore[arg-type]
            name=user.full_name,
            email=user.email,
            role=roles.get(user.id) or "Staff",  # type: ignore[arg-type]
            status="Active" if user.is_active else "Disabled",
        )
        for user in users
    ]


def list_school_info(session: Session, user: User) -> list[SchoolInfo]:
    """Settings > School info: the fields of this school."""
    school = session.get(School, user.school_id) if user.school_id else None
    if school is None:
        return []
    return [
        SchoolInfo(id="name", label="School name", value=school.name),
        SchoolInfo(id="code", label="School code", value=school.code),
        SchoolInfo(id="email", label="Contact email", value=school.email),
        SchoolInfo(id="phone", label="Phone", value=school.phone or ""),
        SchoolInfo(id="address", label="Address", value=school.address or ""),
    ]


def list_security_logs(session: Session) -> list[SecurityLog]:
    """Settings > Security: the sign-in events the school recorded."""
    return [
        SecurityLog(
            id=log.id,  # type: ignore[arg-type]
            event=log.event,
            user=log.user,
            when=log.when,
        )
        for log in session.exec(select(SecurityLogModel)).all()
    ]


def list_gateways(session: Session) -> list[GatewayStatus]:
    """Settings > Integrations: message/SMS gateway statuses."""
    return [
        GatewayStatus(
            id=gateway.id,  # type: ignore[arg-type]
            name=gateway.name,
            type=gateway.type,
            status=gateway.status,
            quota=gateway.quota,
        )
        for gateway in session.exec(select(GatewayStatusModel)).all()
    ]
