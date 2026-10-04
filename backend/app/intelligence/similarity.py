"""Rank candidate patents by *technical* (semantic) similarity to an invention.

Patent databases return results in their own order (often by date or keyword
match). To decide which candidates are most relevant, we compare meanings:

    invention text  = title + abstract + first claim of the user's document/patent
    candidate text  = title + abstract from the search result
    similarity      = cosine similarity of their embeddings (−1 … 1, higher = closer)

This is semantic similarity of descriptions, NOT legal similarity, novelty or
infringement, and the UI says so.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models import Chunk, Document, Patent
from app.patents.base import PatentRecord
from app.rag.embeddings import EmbeddingProvider


@dataclass
class ScoredRecord:
    record: PatentRecord
    similarity: float


def invention_text(
    session: Session, *, document_id: uuid.UUID | None = None, patent_id: uuid.UUID | None = None
) -> tuple[str, str]:
    """(label, text) describing an indexed document or patent."""
    if document_id:
        owner = session.get(Document, document_id)
        if owner is None:
            raise NotFoundError("Document not found.")
        label, title = owner.filename, owner.title or ""
        column = Chunk.document_id
        owner_id = document_id
    else:
        owner = session.get(Patent, patent_id)
        if owner is None:
            raise NotFoundError("Patent not found.")
        label, title = owner.publication_number, owner.title or ""
        column = Chunk.patent_id
        owner_id = patent_id

    def first(section: str) -> str:
        chunk = session.scalar(
            select(Chunk)
            .where(column == owner_id, Chunk.section == section)
            .order_by(Chunk.chunk_index)
            .limit(1)
        )
        return chunk.text if chunk else ""

    parts = [title, first("abstract"), first("claims")]
    if not any(parts[1:]):  # no recognisable sections: use the beginning of the document
        start = session.scalars(
            select(Chunk).where(column == owner_id).order_by(Chunk.chunk_index).limit(2)
        ).all()
        parts += [c.text for c in start]
    return label, "\n".join(p for p in parts if p)[:4000]


def record_text(record: PatentRecord) -> str:
    return "\n".join(p for p in (record.title, record.abstract) if p)


def rank_by_similarity(
    embedder: EmbeddingProvider, reference_text: str, records: list[PatentRecord]
) -> list[ScoredRecord]:
    if not records:
        return []
    texts = [record_text(r) or r.publication_number for r in records]
    vectors = embedder.embed_documents([reference_text, *texts])
    reference, candidates = vectors[0], vectors[1:]
    scored = [
        ScoredRecord(record, sum(a * b for a, b in zip(reference, vector, strict=True)))
        for record, vector in zip(records, candidates, strict=True)
    ]
    return sorted(scored, key=lambda s: s.similarity, reverse=True)
