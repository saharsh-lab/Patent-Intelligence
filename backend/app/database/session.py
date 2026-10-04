"""Database engine and session management.

We use SQLAlchemy 2.0 in synchronous mode. FastAPI runs synchronous endpoints in
a thread pool, so this stays simple without blocking the server.
"""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,  # transparently replace dropped connections
        pool_size=5,
        max_overflow=10,
        hide_parameters=True,  # keep query parameters (user text) out of error messages
        connect_args={"connect_timeout": 5},
    )


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one session per request, always closed afterwards."""
    session = get_sessionmaker()()
    try:
        yield session
    finally:
        session.close()


def check_database(engine: Engine | None = None) -> dict:
    """Return database and pgvector versions; raises if the database is unreachable."""
    engine = engine or get_engine()
    with engine.connect() as conn:
        pg_version = conn.execute(text("SHOW server_version")).scalar_one()
        vector_version = conn.execute(
            text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
        ).scalar_one_or_none()
    return {"postgres": pg_version, "pgvector": vector_version}
