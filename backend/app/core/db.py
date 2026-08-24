from sqlmodel import Session, create_engine

from app.core.config import settings

# In Postgres, the URL scheme for psycopg2 should be postgresql:// (or postgresql+psycopg2://)
# If the user has a different driver, it might be adjusted here.
engine = create_engine(settings.DATABASE_URL, echo=True)


def get_session():
    with Session(engine) as session:
        yield session
