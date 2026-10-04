"""Low-level search over the `chunks` table.

Two complementary ways to find relevant passages:

1. Vector (semantic) search — compares meaning. The question is turned into an
   embedding and we find chunks whose embeddings are closest by *cosine
   distance* (pgvector's `<=>` operator). Finds "wireless charging coil" when
   the patent says "inductive power transfer winding".

2. Keyword (full-text) search — compares exact words. PostgreSQL stems words
   ("sensors" -> "sensor") and ranks matches. Finds exact patent numbers, part
   names and rare technical terms that embeddings can blur.

Phase 3 combines both ("hybrid retrieval"). This module only does the raw search.
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import Select, Text, cast, func, or_, select, text
from sqlalchemy.dialects.postgresql import TSQUERY
from sqlalchemy.orm import Session

from app.core.ownership import owner_clause
from app.models import Chunk, Document


@dataclass(frozen=True)
class ChunkHit:
    chunk: Chunk
    score: float  # higher = more relevant (vector: 1 - cosine distance; keyword: ts_rank)
    method: str  # "vector" | "keyword"


def _apply_scope(
    stmt: Select,
    document_ids: Sequence[uuid.UUID] | None,
    patent_ids: Sequence[uuid.UUID] | None,
) -> Select:
    """Restrict a search to specific documents and/or patents (None = search everything),
    and always to what the current user may see: public patents and their own documents
    (app/core/ownership.py; no filter outside a request, e.g. in experiments)."""
    owner = owner_clause(Document.owner_id)
    if owner is not None:
        stmt = stmt.where(
            or_(
                Chunk.document_id.is_(None), Chunk.document_id.in_(select(Document.id).where(owner))
            )
        )
    if document_ids is None and patent_ids is None:
        return stmt
    conditions = []
    if document_ids is not None:
        conditions.append(Chunk.document_id.in_(document_ids))
    if patent_ids is not None:
        conditions.append(Chunk.patent_id.in_(patent_ids))
    return stmt.where(or_(*conditions))


def vector_search(
    session: Session,
    query_embedding: Sequence[float],
    *,
    top_k: int = 5,
    document_ids: Sequence[uuid.UUID] | None = None,
    patent_ids: Sequence[uuid.UUID] | None = None,
    embedding_model: str | None = None,
) -> list[ChunkHit]:
    """Nearest chunks by cosine distance.

    Pass `embedding_model` to compare only against chunks embedded by the same model
    as the query: vectors from different models live in unrelated spaces.
    """
    # Safeguard recommended by pgvector for filtered searches: when PostgreSQL uses the HNSW
    # index, it takes ~ef_search nearest candidates and filters afterwards, which can return
    # too few rows on a large corpus. Iterative scans (pgvector >= 0.8) keep searching;
    # strict_order keeps exact ordering. SET LOCAL lasts until the transaction ends.
    session.execute(text("SET LOCAL hnsw.iterative_scan = strict_order"))
    distance = Chunk.embedding.cosine_distance(list(query_embedding))
    stmt = (
        select(Chunk, distance.label("distance"))
        .where(Chunk.embedding.is_not(None))
        .order_by(distance)
        .limit(top_k)
    )
    if embedding_model is not None:
        stmt = stmt.where(Chunk.embedding_model == embedding_model)
    stmt = _apply_scope(stmt, document_ids, patent_ids)
    return [
        ChunkHit(chunk=chunk, score=1.0 - float(dist), method="vector")
        for chunk, dist in session.execute(stmt)
    ]


def keyword_search(
    session: Session,
    query_text: str,
    *,
    top_k: int = 5,
    document_ids: Sequence[uuid.UUID] | None = None,
    patent_ids: Sequence[uuid.UUID] | None = None,
    match: Literal["all", "any"] = "all",
) -> list[ChunkHit]:
    """Full-text search.

    match="all": every word must appear (good for short search-box queries; also
                 understands "quoted phrases", OR and -exclusions).
    match="any": any word may appear, ranked by how many and how densely (good for
                 natural-language questions, where requiring every word finds nothing).
    """
    if match == "any":
        # plainto_tsquery gives 'batteri' & 'overheat'; swap AND (&) for OR (|)
        and_query = cast(func.plainto_tsquery("english", query_text), Text)
        ts_query = cast(func.replace(and_query, "&", "|"), TSQUERY)
    else:
        ts_query = func.websearch_to_tsquery("english", query_text)
    rank = func.ts_rank_cd(Chunk.tsv, ts_query)
    stmt = (
        select(Chunk, rank.label("rank"))
        .where(Chunk.tsv.op("@@")(ts_query))
        .order_by(rank.desc())
        .limit(top_k)
    )
    stmt = _apply_scope(stmt, document_ids, patent_ids)
    return [
        ChunkHit(chunk=chunk, score=float(score), method="keyword")
        for chunk, score in session.execute(stmt)
    ]
