from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session

from app.core.db import get_session

from . import schemas, service

router = APIRouter()


@router.post("/login", response_model=schemas.TokenResponse)
def login(
    login_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
):
    token = service.authenticate_user(
        session=session, username=login_data.username, password=login_data.password
    )

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {"access_token": token, "token_type": "bearer"}
