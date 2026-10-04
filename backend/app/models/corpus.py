"""The knowledge the system searches over: uploaded documents, patent records, and chunks.

Design note — one `chunks` table for every source:
A chunk is a short passage of text plus its embedding. Chunks from an uploaded
PDF and chunks from a patent fetched via the EPO API live in the same table
(each chunk belongs to exactly one document OR one patent). This lets a single
SQL query do hybrid search across all sources at once, which is what the
"multi-source" part of the project needs.
"""

import uuid
from datetime import date, datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Computed,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import get_settings
from app.models.base import Base, created_at_column, metadata_column, uuid_pk

EMBEDDING_DIM = get_settings().embedding_dim


class Document(Base):
    """A file uploaded by the user (PDF / DOCX / TXT)."""

    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'processing', 'ready', 'failed')", name="valid_status"
        ),
        UniqueConstraint("owner_id", "content_sha256", postgresql_nulls_not_distinct=True),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    filename: Mapped[str] = mapped_column(String(255))
    title: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(32), default="upload", server_default="upload")
    mime_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    # SHA-256 of the file bytes: lets us detect duplicate uploads and skip re-embedding
    content_sha256: Mapped[str] = mapped_column(String(64))
    # The user (separate auth database) who uploaded it; None in single-user mode.
    # Duplicates are detected per owner (see the 0003 migration).
    owner_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    storage_path: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="pending", server_default="pending")
    error_message: Mapped[str | None] = mapped_column(Text)
    page_count: Mapped[int | None] = mapped_column(Integer)
    meta: Mapped[dict[str, Any]] = metadata_column()
    uploaded_at: Mapped[datetime] = created_at_column()

    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", passive_deletes=True
    )


class Patent(Base):
    """A patent record fetched from an external source (EPO, USPTO, Lens, ...)."""

    __tablename__ = "patents"
    __table_args__ = (UniqueConstraint("source", "publication_number"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    source: Mapped[str] = mapped_column(String(32))  # epo | uspto | wipo | lens
    # Normalised publication number, e.g. "EP1234567A1" (country + number + kind code)
    publication_number: Mapped[str] = mapped_column(String(64), index=True)
    country: Mapped[str | None] = mapped_column(String(4))
    kind_code: Mapped[str | None] = mapped_column(String(4))
    family_id: Mapped[str | None] = mapped_column(String(64), index=True)
    title: Mapped[str | None] = mapped_column(Text)
    abstract: Mapped[str | None] = mapped_column(Text)
    claims_text: Mapped[str | None] = mapped_column(Text)
    description_text: Mapped[str | None] = mapped_column(Text)
    applicants: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list, server_default="{}")
    inventors: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list, server_default="{}")
    cpc_codes: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list, server_default="{}")
    filing_date: Mapped[date | None] = mapped_column(Date)
    publication_date: Mapped[date | None] = mapped_column(Date)
    priority_date: Mapped[date | None] = mapped_column(Date)
    legal_status: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    # Original API response, kept so we can re-parse later without re-fetching
    raw: Mapped[dict[str, Any] | None] = mapped_column()
    meta: Mapped[dict[str, Any]] = metadata_column()
    fetched_at: Mapped[datetime] = created_at_column()

    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="patent", cascade="all, delete-orphan", passive_deletes=True
    )


class Chunk(Base):
    """A passage of text with its embedding — the unit of retrieval and citation."""

    __tablename__ = "chunks"
    __table_args__ = (
        # Every chunk belongs to exactly one owner: an uploaded document or a patent
        CheckConstraint("num_nonnulls(document_id, patent_id) = 1", name="exactly_one_owner"),
        UniqueConstraint("document_id", "chunk_index"),
        UniqueConstraint("patent_id", "chunk_index"),
        # HNSW = approximate nearest-neighbour index for fast vector similarity search
        Index(
            "ix_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        # GIN index over the tsvector column = fast keyword (full-text) search
        Index("ix_chunks_tsv", "tsv", postgresql_using="gin"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    patent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("patents.id", ondelete="CASCADE"), index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    # Detected patent section: title | abstract | claims | description | background | ...
    section: Mapped[str | None] = mapped_column(String(32))
    page_number: Mapped[int | None] = mapped_column(Integer)
    char_start: Mapped[int | None] = mapped_column(Integer)
    char_end: Mapped[int | None] = mapped_column(Integer)
    token_count: Mapped[int | None] = mapped_column(Integer)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM))
    embedding_model: Mapped[str | None] = mapped_column(String(128))
    # Maintained automatically by PostgreSQL from `text` (stemmed words for keyword search)
    tsv: Mapped[str] = mapped_column(
        TSVECTOR, Computed("to_tsvector('english', text)", persisted=True)
    )
    meta: Mapped[dict[str, Any]] = metadata_column()
    created_at: Mapped[datetime] = created_at_column()

    document: Mapped[Document | None] = relationship(back_populates="chunks")
    patent: Mapped[Patent | None] = relationship(back_populates="chunks")


class ApiCache(Base):
    """Cached external API responses (patent searches, patent details) to save quota and time."""

    __tablename__ = "api_cache"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)  # hash of request
    namespace: Mapped[str] = mapped_column(String(32), index=True)  # e.g. "epo.search"
    value: Mapped[dict[str, Any]] = mapped_column()
    created_at: Mapped[datetime] = created_at_column()
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
