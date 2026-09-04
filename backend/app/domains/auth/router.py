from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import Session

from app.core.db import get_session
from app.domains.auth.dependencies import get_current_active_user
from app.domains.users import repository as user_repository
from app.domains.users.models import RoleEnum, User

from . import schemas, service

router = APIRouter()

ROLE_MAP = {
    RoleEnum.director: "DIRECTOR",
    RoleEnum.principal: "PRINCIPAL",
    RoleEnum.hod: "HOD",
    RoleEnum.teacher: "SUBJECT_TEACHER",
    RoleEnum.student: "STUDENT",
    RoleEnum.parent: "GUARDIAN",
    RoleEnum.accountant: "ACCOUNTANT",
    RoleEnum.admin: "ADMIN",
}


def _build_user_dict(user: User) -> dict:
    role_str = ROLE_MAP.get(user.role, "STAFF")
    return {
        "id": user.id,
        "username": user.email.split("@")[0],
        "email": user.email,
        "fullName": user.full_name,
        "roles": [role_str],
        "department": "Academics",
    }


@router.post("/login", response_model=schemas.TokenResponse)
@router.post("/token", response_model=schemas.TokenResponse)
async def login(
    request: Request,
    session: Session = Depends(get_session),
):
    content_type = request.headers.get("content-type", "")
    username = ""
    password = ""

    if "application/json" in content_type:
        body = await request.json()
        username = body.get("username") or body.get("identifier") or ""
        password = body.get("password") or ""
    else:
        form = await request.form()
        username = form.get("username") or ""
        password = form.get("password") or ""

    # Try authenticate by email
    user = user_repository.get_user_by_email(session, email=username)
    # If not found by email, try matching username (e.g. "admin" for "admin@eduverse.com" or "principal")
    if not user:
        from sqlmodel import select

        all_users = session.exec(select(User)).all()
        for u in all_users:
            if (
                u.email.split("@")[0].lower() == username.lower()
                or u.role.lower() == username.lower()
            ):
                user = u
                username = u.email
                break

    token = service.authenticate_user(
        session=session, username=username, password=password
    )

    if not token or not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "access_token": token,
        "token_type": "bearer",
        "refresh_token": f"refresh_{token[:16]}",
        "user": _build_user_dict(user),
    }


@router.get("/me")
def get_me(current_user: User = Depends(get_current_active_user)):
    return _build_user_dict(current_user)


@router.post("/logout")
def logout():
    return {"status": "ok", "detail": "Logged out successfully"}
