"""SQLAlchemy sync engine for MySQL (PyMySQL driver).

Every thread gets its own connection from the pool (pool_pre_ping keeps
stale sockets from surfacing). FastAPI route handlers call get_db() as a
Depends; the job-runner threads open their own session directly.
"""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from ..config import settings

engine = create_engine(
    settings.mysql_url,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=10,
    max_overflow=20,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency — yields a session and closes it when done."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
