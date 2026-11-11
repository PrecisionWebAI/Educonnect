from uuid import UUID
from sqlalchemy import func
from sqlmodel import Session, select

from app.core.security import get_password_hash

from .models import User, UserCreate


def get_user_by_id(session: Session, user_id: UUID) -> User | None:
    return session.get(User, user_id)


def get_user_by_email(session: Session, email: str) -> User | None:
    """The account for an email, **whatever case it was typed in**.

    Addresses are stored lower-case (`app/core/text.py`), and nobody should have
    to remember how their address was capitalised to sign in: `Admin@ABC` and
    `admin@abc` are the same account. This is the lookup the login route uses.
    """
    statement = select(User).where(func.lower(User.email) == email.strip().lower())
    return session.exec(statement).first()


def get_users(session: Session, skip: int = 0, limit: int = 100) -> list[User]:
    statement = select(User).offset(skip).limit(limit)
    return list(session.exec(statement).all())


def create_user(
    session: Session, user_create: UserCreate, *, school_id: UUID | None = None
) -> User:
    db_user = User.model_validate(
        user_create,
        update={
            "hashed_password": get_password_hash(user_create.password),
            "school_id": school_id,
        },
    )
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user
