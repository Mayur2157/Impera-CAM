"""SQLAlchemy sync engine: a local SQLite file by default, MySQL (PyMySQL) on a server.

Every thread gets its own connection from the pool (pool_pre_ping keeps
stale sockets from surfacing). FastAPI route handlers call get_db() as a
Depends; the job-runner threads open their own session directly.
"""
from __future__ import annotations

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from ..config import settings

_SQLITE = settings.mysql_url.startswith("sqlite")

engine = create_engine(
    settings.mysql_url,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    echo=False,
    # SQLite connections are shared by FastAPI's threadpool and the local job
    # threads; a writer waits up to 30 s for another instead of failing
    connect_args={"check_same_thread": False, "timeout": 30} if _SQLITE else {},
)

if _SQLITE:
    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _record):
        # WAL lets the pages poll for progress while a job thread is writing
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA busy_timeout=30000")
        cur.close()

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
