"""Alembic environment for the separate auth database (users, login sessions)."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app.auth import models  # noqa: F401 - registers the tables
from app.auth.config import get_auth_settings
from app.auth.db import AuthBase

config = context.config
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = AuthBase.metadata


def _url() -> str:
    return config.attributes.get("database_url") or get_auth_settings().auth_database_url


def run_migrations_offline() -> None:
    context.configure(url=_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
