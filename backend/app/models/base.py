"""Shared building blocks for all ORM models."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Predictable constraint names make Alembic migrations stable and readable
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    type_annotation_map = {dict[str, Any]: JSONB, list[Any]: JSONB}


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(primary_key=True, default=uuid.uuid4)


def created_at_column() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


def json_column(column_name: str | None = None) -> Mapped[dict[str, Any]]:
    """A non-null JSONB column that defaults to an empty object."""
    args = (column_name,) if column_name else ()
    return mapped_column(*args, JSONB, default=dict, server_default="{}", nullable=False)


def metadata_column() -> Mapped[dict[str, Any]]:
    # The Python attribute is `meta` because `metadata` is reserved by SQLAlchemy,
    # but the database column is still called `metadata`.
    return json_column("metadata")
