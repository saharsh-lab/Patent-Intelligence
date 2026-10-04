"""Patent monitoring: saved searches ("watches") and the new publications they find.

    patent_watches ─< watch_hits

A watch is a saved search (keywords and/or CPC classes), optionally ranked against one
of the user's documents. Each check asks the patent databases for publications since
the last check; publications not seen before become hits, ranked by similarity to the
reference document, and the most similar ones are imported so they can be analysed.
"""

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, created_at_column, uuid_pk


class PatentWatch(Base):
    __tablename__ = "patent_watches"

    id: Mapped[uuid.UUID] = uuid_pk()
    owner_id: Mapped[uuid.UUID | None] = mapped_column(index=True)  # user (auth database)
    name: Mapped[str] = mapped_column(String(120))
    keywords: Mapped[str] = mapped_column(Text, default="", server_default="")
    cpc: Mapped[list[Any]] = mapped_column(default=list, server_default="[]")
    # Rank new publications by similarity to this document (e.g. the user's invention)
    reference_document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL")
    )
    import_top: Mapped[int] = mapped_column(Integer, default=3, server_default="3")
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    # Publications on or after this date are looked for at the next check
    since: Mapped[date] = mapped_column(Date)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_column()

    hits: Mapped[list["WatchHit"]] = relationship(
        back_populates="watch",
        cascade="all, delete-orphan",
        passive_deletes=True,
        # newest check first; within one check, most similar first (= import order)
        order_by="(WatchHit.found_at.desc(), WatchHit.similarity.desc().nulls_last(), "
        "WatchHit.publication_date.desc().nulls_last())",
    )


class WatchHit(Base):
    __tablename__ = "watch_hits"
    __table_args__ = (UniqueConstraint("watch_id", "publication_number"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    watch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patent_watches.id", ondelete="CASCADE"), index=True
    )
    source: Mapped[str] = mapped_column(String(32))
    publication_number: Mapped[str] = mapped_column(String(64))
    title: Mapped[str | None] = mapped_column(Text)
    abstract: Mapped[str | None] = mapped_column(Text)
    applicants: Mapped[list[Any]] = mapped_column(default=list, server_default="[]")
    publication_date: Mapped[date | None] = mapped_column(Date)
    url: Mapped[str | None] = mapped_column(Text)
    # Cosine similarity to the watch's reference document (None without a reference)
    similarity: Mapped[float | None] = mapped_column(Float)
    imported_patent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("patents.id", ondelete="SET NULL")
    )
    seen: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    found_at: Mapped[datetime] = created_at_column()

    watch: Mapped[PatentWatch] = relationship(back_populates="hits")
