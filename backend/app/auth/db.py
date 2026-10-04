"""Engine and sessions for the separate auth database."""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, MetaData, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.auth.config import get_auth_settings
from app.models.base import NAMING_CONVENTION


class AuthBase(DeclarativeBase):
    """Separate metadata: these tables are created in the auth database only."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


@lru_cache
def get_auth_engine() -> Engine:
    return create_engine(
        get_auth_settings().auth_database_url,
        pool_pre_ping=True,
        hide_parameters=True,
        connect_args={"connect_timeout": 5},
    )


@lru_cache
def get_auth_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_auth_engine(), autoflush=False, expire_on_commit=False)


def get_auth_db() -> Iterator[Session]:
    session = get_auth_sessionmaker()()
    try:
        yield session
    finally:
        session.close()
