"""Chat conversations. Messages are the conversation's runs: `queries.conversation_id`
links each question (and its agent run) to the conversation it was asked in."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at_column, uuid_pk

DEFAULT_TITLE = "New chat"


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = uuid_pk()
    # The user (in the separate auth database) who owns it; None in single-user mode
    owner_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    title: Mapped[str] = mapped_column(String(200), default=DEFAULT_TITLE)
    # Documents attached in this chat: answers are scoped to them
    document_ids: Mapped[list[Any]] = mapped_column(default=list, server_default="[]")
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
