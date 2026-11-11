from sqlalchemy import func
from sqlmodel import Session, select

from app.domains.admin.users.models import User


def get_user_by_email(session: Session, email: str) -> User | None:
    """The account for an email, **whatever case it was typed in**.

    Addresses are stored lower-case (`app.core.text`), and nobody should have to
    remember how their address was capitalised to sign in: `Admin@ABC` and
    `admin@abc` are the same account.
    """
    statement = select(User).where(func.lower(User.email) == email.strip().lower())
    return session.exec(statement).first()

