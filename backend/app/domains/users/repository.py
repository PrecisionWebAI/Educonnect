from sqlmodel import Session, select

from app.core.security import get_password_hash

from .models import User, UserCreate


def get_user_by_id(session: Session, user_id: int) -> User | None:
    return session.get(User, user_id)


def get_user_by_email(session: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    return session.exec(statement).first()


def get_users(session: Session, skip: int = 0, limit: int = 100) -> list[User]:
    statement = select(User).offset(skip).limit(limit)
    return list(session.exec(statement).all())


def create_user(
    session: Session, user_create: UserCreate, *, school_id: int | None = None
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
