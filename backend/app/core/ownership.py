"""Per-user data isolation, enforced at the lowest query layer.

Services set the current owner once, at their entry point:

    with owner_scope(user_id):
        ... everything that searches the index ...

and the search functions in `rag/vector_store.py` (used by every retrieval path: the
baseline, all agent tools, regeneration, comparisons, invention analysis) add the
visibility rule automatically:

    a passage is visible  ⇔  it belongs to a public patent
                             OR to a document whose owner is the current user

Enforcing it in one place means no new feature can forget it. Outside any scope (the
evaluation runner, scripts) nothing is filtered, so experiments are unaffected.
In single-user mode (AUTH_REQUIRED=false) the owner is None and documents without an
owner are visible.
"""

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

_UNSCOPED = object()
_owner: ContextVar[object] = ContextVar("data_owner", default=_UNSCOPED)


@contextmanager
def owner_scope(owner_id: uuid.UUID | None) -> Iterator[None]:
    token = _owner.set(owner_id)
    try:
        yield
    finally:
        _owner.reset(token)


def scoped() -> bool:
    return _owner.get() is not _UNSCOPED


def current_owner() -> uuid.UUID | None:
    value = _owner.get()
    return None if value is _UNSCOPED else value  # type: ignore[return-value]


def owner_clause(column):
    """SQL condition "row belongs to the current owner", or None when unscoped."""
    if not scoped():
        return None
    owner = current_owner()
    return column.is_(None) if owner is None else column == owner


def restrict(stmt, column):
    """Add the owner condition to a SELECT (no-op when unscoped)."""
    clause = owner_clause(column)
    return stmt if clause is None else stmt.where(clause)


def visible(owner_id: uuid.UUID | None) -> bool:
    """May the current owner see a row owned by `owner_id`?"""
    return not scoped() or owner_id == current_owner()
