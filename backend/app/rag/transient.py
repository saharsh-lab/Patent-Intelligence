"""Passages that live for one answer only: web pages and patent-office search results.

They are cited and verified like library passages but never stored in the user's library
(no import, no indexing). A TransientChunk quacks like a Chunk for the answer pipeline:
generation, citation and verification only read its text, section and source.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from app.rag.embeddings import EmbeddingProvider
from app.rag.retrieval import RetrievedPassage


@dataclass
class ExternalSource:
    kind: str  # "web" | "epo" | "wikipedia" ...
    label: str  # shown as the source: a site ("en.wikipedia.org") or a patent number
    title: str
    url: str | None = None


@dataclass
class TransientChunk:
    text: str
    external: ExternalSource
    section: str | None = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    meta: dict[str, Any] = field(default_factory=dict)
    page_number: int | None = None
    document: None = None
    patent: None = None
    document_id: None = None
    patent_id: None = None


def external_of(chunk: Any) -> ExternalSource | None:
    return getattr(chunk, "external", None)


def rank_transient(
    embedder: EmbeddingProvider,
    question: str,
    chunks: list[TransientChunk],
    limit: int,
    min_similarity: float = 0.0,
) -> list[RetrievedPassage]:
    """Order external passages by semantic similarity to the question; keep the best."""
    if not chunks:
        return []
    vectors = embedder.embed_documents([c.text for c in chunks])
    query = embedder.embed_query(question)
    scored = [
        (sum(a * b for a, b in zip(query, v, strict=True)), c)
        for c, v in zip(chunks, vectors, strict=True)
    ]
    scored.sort(key=lambda s: -s[0])
    return [
        RetrievedPassage(chunk=c, score=sim, rank=i + 1, vector_similarity=sim)
        for i, (sim, c) in enumerate(s for s in scored if s[0] >= min_similarity)
        if i < limit
    ]
