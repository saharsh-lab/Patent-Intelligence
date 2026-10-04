"""API response/request shapes for documents and chunk search (what the frontend sees)."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models import Chunk, Document


class DocumentOut(BaseModel):
    id: uuid.UUID
    filename: str
    title: str | None
    mime_type: str
    size_bytes: int
    status: str
    error_message: str | None
    page_count: int | None
    uploaded_at: datetime
    chunk_count: int
    sections_found: list[str]
    section_detection: str | None
    patent_numbers_detected: list[str]

    @classmethod
    def from_model(cls, doc: Document, chunk_count: int | None = None) -> "DocumentOut":
        meta = doc.meta or {}
        return cls(
            id=doc.id,
            filename=doc.filename,
            title=doc.title,
            mime_type=doc.mime_type,
            size_bytes=doc.size_bytes,
            status=doc.status,
            error_message=doc.error_message,
            page_count=doc.page_count,
            uploaded_at=doc.uploaded_at,
            chunk_count=chunk_count if chunk_count is not None else meta.get("chunk_count", 0),
            sections_found=meta.get("sections_found", []),
            section_detection=meta.get("section_detection"),
            patent_numbers_detected=meta.get("patent_numbers_detected", []),
        )


class UploadResponse(BaseModel):
    document: DocumentOut
    duplicate: bool = Field(description="True if this exact file was already uploaded")


class ChunkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    chunk_index: int
    section: str | None
    page_number: int | None
    char_start: int | None
    char_end: int | None
    token_count: int | None
    text: str
    meta: dict


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    method: Literal["vector", "keyword"] = "vector"
    top_k: int = Field(default=5, ge=1, le=50)
    document_ids: list[uuid.UUID] | None = None


class SearchHit(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID | None
    patent_id: uuid.UUID | None
    source_label: str
    section: str | None
    page_number: int | None
    score: float
    method: str
    text: str

    @classmethod
    def from_chunk(cls, chunk: Chunk, score: float, method: str) -> "SearchHit":
        if chunk.document is not None:
            label = chunk.document.filename
        elif chunk.patent is not None:
            label = chunk.patent.publication_number
        else:
            label = "unknown"
        return cls(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            patent_id=chunk.patent_id,
            source_label=label,
            section=chunk.section,
            page_number=chunk.page_number,
            score=round(score, 4),
            method=method,
            text=chunk.text,
        )
