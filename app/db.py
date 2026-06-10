"""Database engine, session factory, and the declarative Base.

Configuration comes from the environment (loaded from a local .env in development).
"""

import os
from contextlib import contextmanager

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL is None:
    raise ValueError("DATABASE_URL is not set")

# When SQL_ECHO is truthy, SQLAlchemy logs every statement it runs. Off by default.
SQL_ECHO = os.getenv("SQL_ECHO", "false").strip().lower() in {"1", "true", "yes"}

# pool_pre_ping checks a pooled connection is still alive before use, so an idle
# connection dropped by a managed Postgres doesn't surface as a request error.
engine = create_engine(DATABASE_URL, echo=SQL_ECHO, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


def get_session():
    """Return a new session. The caller is responsible for closing it."""
    return SessionLocal()


@contextmanager
def session_scope():
    """Yield a session and guarantee it is closed on exit (success or error)."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
