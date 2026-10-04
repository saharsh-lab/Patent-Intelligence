"""Hybrid retrieval: vector search + keyword search, fused, optionally reranked.

    question ─┬─ vector search  (top N by meaning)  ─┐
              └─ keyword search (top N by words)    ─┴─ Reciprocal Rank Fusion
                                                          │
                                         optional cross-encoder rerank
                                                          │
                                                     top k passages

Reciprocal Rank Fusion (RRF): each passage gets  Σ 1 / (k + rank)  over the
lists it appears in (k = 60 by convention). Only *ranks* are used, so we never
have to compare a cosine similarity with a keyword score, which are on
different scales. A passage ranked well by both methods rises to the top.
"""

import time
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal

from sqlalchemy.orm import Session

from app.models import Chunk
from app.rag.embeddings import EmbeddingProvider
from app.rag.reranker import Reranker
from app.rag.vector_store import keyword_search, vector_search

RetrievalMode = Literal["hybrid", "vector", "keyword"]


@dataclass
class RetrievedPassage:
    chunk: Chunk
    score: float  # fused RRF score (hybrid) or raw method score
    rank: int  # 1 = best, after fusion/reranking
    vector_similarity: float | None = None
    keyword_score: float | None = None
    rerank_score: float | None = None
    direct: bool = False  # fetched by exact section/claim, not by similarity

    @property
    def method(self) -> str:
        if self.direct:
            return "section"
        if self.vector_similarity is not None and self.keyword_score is not None:
            return "hybrid"
        return "vector" if self.vector_similarity is not None else "keyword"


@dataclass
class RetrievalConfig:
    mode: RetrievalMode = "hybrid"
    top_k: int = 6
    candidate_k: int = 30
    rrf_k: int = 60
    min_similarity: float = 0.35


@dataclass
class RetrievalResult:
    passages: list[RetrievedPassage]
    best_vector_similarity: float | None
    keyword_matches: int
    candidates_considered: int
    timings_ms: dict[str, int] = field(default_factory=dict)


def reciprocal_rank_fusion(rankings: list[list[uuid.UUID]], k: int = 60) -> dict[uuid.UUID, float]:
    scores: dict[uuid.UUID, float] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, start=1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank)
    return scores


def retrieve(
    session: Session,
    query: str,
    *,
    embedder: EmbeddingProvider,
    config: RetrievalConfig,
    reranker: Reranker | None = None,
    document_ids: Sequence[uuid.UUID] | None = None,
    patent_ids: Sequence[uuid.UUID] | None = None,
) -> RetrievalResult:
    timings: dict[str, int] = {}
    vector_hits, keyword_hits = [], []

    if config.mode in ("hybrid", "vector"):
        started = time.perf_counter()
        vector_hits = vector_search(
            session,
            embedder.embed_query(query),
            top_k=config.candidate_k,
            document_ids=document_ids,
            patent_ids=patent_ids,
            embedding_model=embedder.name,
        )
        timings["vector_search"] = _ms(started)
    if config.mode in ("hybrid", "keyword"):
        started = time.perf_counter()
        keyword_hits = keyword_search(
            session,
            query,
            top_k=config.candidate_k,
            document_ids=document_ids,
            patent_ids=patent_ids,
            match="any",
        )
        timings["keyword_search"] = _ms(started)

    chunks = {hit.chunk.id: hit.chunk for hit in vector_hits + keyword_hits}
    similarity = {hit.chunk.id: hit.score for hit in vector_hits}
    keyword_score = {hit.chunk.id: hit.score for hit in keyword_hits}
    fused = reciprocal_rank_fusion(
        [[h.chunk.id for h in hits] for hits in (vector_hits, keyword_hits) if hits],
        k=config.rrf_k,
    )
    ordered = sorted(fused, key=fused.get, reverse=True)

    passages = [
        RetrievedPassage(
            chunk=chunks[chunk_id],
            score=fused[chunk_id],
            rank=0,
            vector_similarity=similarity.get(chunk_id),
            keyword_score=keyword_score.get(chunk_id),
        )
        for chunk_id in ordered
    ]

    if reranker is not None and passages:
        started = time.perf_counter()
        scores = reranker.score(query, [p.chunk.text for p in passages])
        for passage, score in zip(passages, scores, strict=True):
            passage.rerank_score = score
        passages.sort(key=lambda p: p.rerank_score, reverse=True)
        timings["rerank"] = _ms(started)

    passages = passages[: config.top_k]
    for rank, passage in enumerate(passages, start=1):
        passage.rank = rank

    return RetrievalResult(
        passages=passages,
        best_vector_similarity=max(similarity.values()) if similarity else None,
        keyword_matches=len(keyword_hits),
        candidates_considered=len(fused),
        timings_ms=timings,
    )


def has_sufficient_evidence(result: RetrievalResult, config: RetrievalConfig) -> tuple[bool, str]:
    """Cheap check *before* calling the LLM: is anything plausibly relevant?

    Saves cost and prevents the model from 'answering' from nothing. Deliberately
    lenient: any keyword match passes, and the LLM is then instructed to reply
    INSUFFICIENT_EVIDENCE if the passages still don't answer the question.
    """
    if not result.passages:
        return False, "No passages were found in the searched documents."
    if result.keyword_matches > 0:
        return True, ""
    best = result.best_vector_similarity
    if best is None:
        return False, "No passage matched the question's keywords."
    if best >= config.min_similarity:
        return True, ""
    return False, (
        "The closest passages are not similar enough to the question "
        f"(best similarity {best:.3f} < threshold {config.min_similarity:.3f})."
    )


def _ms(started: float) -> int:
    return round((time.perf_counter() - started) * 1000)
