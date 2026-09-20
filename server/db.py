"""SQLite engine and session (SQLAlchemy 2.x)."""
from sqlalchemy import create_engine, event
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker

import config

engine = create_engine(
    URL.create("sqlite", database=str(config.DB_PATH)),
    connect_args={"check_same_thread": False},  # sync handlers run in FastAPI's thread pool
)


@event.listens_for(engine, "connect")
def _enable_foreign_keys(dbapi_connection, _record):
    # SQLite ignores foreign keys unless this is switched on for every connection.
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session():
    with SessionLocal() as session:
        yield session
