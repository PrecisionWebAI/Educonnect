from sqlmodel import Session, create_engine

from app.core.config import settings

# In Postgres, the URL scheme for psycopg2 should be postgresql:// (or postgresql+psycopg2://)
# If the user has a different driver, it might be adjusted here.
# search_path makes all unqualified tables resolve to the configured schema (e.g. demo_school)
engine = create_engine(
    settings.DATABASE_URL,
    echo=True,
    connect_args={"options": f"-csearch_path={settings.DB_SCHEMA},public"},
)


def get_session():
    with Session(engine) as session:
        yield session
