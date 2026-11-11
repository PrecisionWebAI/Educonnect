from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import RequirePermission

from . import service
from .schemas import GatewayStatus, SchoolInfo, SecurityLog, SettingUser

router = APIRouter()

_can_read = RequirePermission("settings.read")


@router.get("/users", response_model=list[SettingUser])
def read_setting_users(
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """Every sign-in, with the role it acts as."""
    return service.list_setting_users(session=session)


@router.get("/school-info", response_model=list[SchoolInfo])
def read_school_info(
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """The fields of this school, as the Settings screen lists them."""
    return service.list_school_info(session=session, user=current_user)


@router.get("/security-logs", response_model=list[SecurityLog])
def read_security_logs(
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """The sign-in events the school recorded."""
    return service.list_security_logs(session=session)


@router.get("/gateways", response_model=list[GatewayStatus])
def read_gateways(
    session: Session = Depends(get_session),
    current_user=Depends(_can_read),
):
    """Message/SMS gateway statuses."""
    return service.list_gateways(session=session)
