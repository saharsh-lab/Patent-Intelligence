"""Invention analysis engine: features → candidate documents → verified feature chart.

Steps (each timed and stored with the run):
1. features      split the description into technical features (features.py)
2. patent_search optional: search the configured patent databases with the features'
                 key terms and import the top results, so they become searchable
3. candidates    for each feature, hybrid retrieval over the whole index; documents are
                 ranked by Reciprocal Rank Fusion across features (a document that matches
                 many features ranks high); the invention's own document is excluded
4. chart         for each (feature, candidate): retrieve that candidate's best passages
                 for the feature and let the verifier judge whether they disclose it
                 → disclosed / partially disclosed / not found, with the passage cited
5. summary       overlap per candidate, coverage per feature, and the features that no
                 retrieved document discloses

Runs are stored as `agent_runs` (pipeline = "invention_analysis") with their tool steps
and cited passages, so they can be listed, reopened and evaluated like answers.
"""

import logging
import time
import uuid
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.analysis import keywords_from_text
from app.core.config import Settings
from app.core.errors import AppError, NotFoundError, ValidationFailedError
from app.core.ownership import current_owner, visible
from app.invention.features import Feature, extract_features
from app.llm.providers import LLMProvider
from app.models import AgentRun, Chunk, Document, Query, RetrievalResult, ToolCall
from app.patents.base import PatentQuery, PatentSource
from app.rag.embeddings import EmbeddingProvider
from app.rag.retrieval import RetrievalConfig, RetrievedPassage, retrieve
from app.services.patents import PatentService
from app.verification.verifiers import PARTIAL, SUPPORTED, Verifier, build_verifier

logger = logging.getLogger(__name__)

PIPELINE = "invention_analysis"
DISCLOSED, PARTIALLY, NOT_FOUND = "disclosed", "partially_disclosed", "not_found"
VERDICT_OF = {SUPPORTED: DISCLOSED, PARTIAL: PARTIALLY}
PASSAGES_PER_CELL = 3
DISCLAIMER = (
    "Technical comparison of the retrieved documents only. It is not an assessment of "
    "novelty, patentability, validity or infringement, and documents that were not "
    "retrieved may disclose the same features."
)


@dataclass
class Candidate:
    key: str  # "document:<uuid>" or "patent:<uuid>"
    kind: str  # document | patent
    id: uuid.UUID
    label: str  # filename or publication number
    title: str | None
    url: str | None
    rank_score: float = 0.0
    features_matched: int = 0


class InventionAnalyzer:
    def __init__(
        self,
        session: Session,
        settings: Settings,
        embedder: EmbeddingProvider,
        llm: LLMProvider,
        patent_sources: dict[str, PatentSource],
        verifier: Verifier | None = None,
    ):
        self.session = session
        self.settings = settings
        self.embedder = embedder
        self.llm = llm
        self.sources = patent_sources
        self.verifier = verifier or build_verifier(
            settings.verifier_method, nli_model=settings.verifier_nli_model, llm=llm
        )
        self.retrieval = RetrievalConfig(
            mode=settings.retrieval_mode,
            top_k=10,
            candidate_k=settings.retrieval_candidate_k,
            rrf_k=settings.rrf_k,
            min_similarity=settings.retrieval_min_similarity,
        )

    # ------------------------------------------------------------------ public

    def analyze(
        self,
        description: str | None = None,
        *,
        document_id: uuid.UUID | None = None,
        use_patent_search: bool = True,
        max_candidates: int = 5,
    ) -> AgentRun:
        started = time.perf_counter()
        own_document = self._document(document_id) if document_id else None
        text = (description or "").strip() or (
            self._document_text(own_document) if own_document else ""
        )
        if len(text.split()) < 8:
            raise ValidationFailedError(
                "Describe the invention in at least a few sentences (or select a document)."
            )

        query = Query(
            owner_id=current_owner(),
            query_text=text[:4000],
            meta={"document_id": str(document_id or "")},
        )
        run = AgentRun(
            query=query,
            pipeline=PIPELINE,
            status="running",
            plan={"steps": []},
            config=self._config_snapshot(use_patent_search, max_candidates),
        )
        self.session.add(run)
        self.session.commit()

        steps: list[dict] = []
        try:
            result = self._run(text, own_document, use_patent_search, max_candidates, steps)
        except AppError:
            self._fail(run, started, steps)
            raise
        except Exception as exc:
            logger.exception("Invention analysis failed for run %s", run.id)
            self._fail(run, started, steps)
            raise AppError(
                "The analysis could not be completed.", code="analysis_failed", status_code=500
            ) from exc
        self._store(run, result, steps, started)
        return run

    # ------------------------------------------------------------------ pipeline

    def _run(self, text, own_document, use_patent_search, max_candidates, steps) -> dict:
        with _step(steps, "extract_features") as step:
            features = extract_features(text, self.llm)
            if not features:
                raise ValidationFailedError("No technical features could be identified.")
            step["summary"] = f"{len(features)} features ({features[0].origin})"

        imported: list[str] = []
        if use_patent_search and self.sources:
            with _step(steps, "search_patents") as step:
                imported = self._search_and_import(features)
                step["summary"] = f"imported {len(imported)}: {', '.join(imported) or '–'}"

        with _step(steps, "rank_candidates") as step:
            candidates = self._rank_candidates(features, own_document, max_candidates)
            step["summary"] = f"{len(candidates)} candidate documents"

        with _step(steps, "build_feature_chart") as step:
            cells = self._chart(features, candidates)
            step["summary"] = f"{len(cells)} feature × document checks ({self.verifier.name})"

        return self._summarise(text, features, candidates, cells, imported, own_document)

    def _search_and_import(self, features: list[Feature]) -> list[str]:
        """External search with the features' key terms; import the top results."""
        keywords = keywords_from_text(" ".join(f.text for f in features), limit=6)
        service = PatentService(self.session, self.settings, self.embedder, self.sources)
        try:
            outcome = service.search(PatentQuery(keywords=keywords, limit=10))
        except AppError as exc:
            logger.info("Patent search failed during invention analysis: %s", exc.message)
            return []
        imported = []
        for item in outcome.results[: self.settings.agent_similar_import_limit]:
            try:
                patent, _ = service.import_patent(
                    item.record.source, item.record.publication_number
                )
                imported.append(patent.publication_number)
            except AppError as exc:  # one failed import must not stop the analysis
                self.session.rollback()
                logger.info("Import of %s failed: %s", item.record.publication_number, exc)
        return imported

    def _rank_candidates(
        self, features: list[Feature], own_document: Document | None, limit: int
    ) -> list[Candidate]:
        """Reciprocal Rank Fusion over features: score(d) = Σ_features 1 / (k + rank),
        where rank is the position of d's best passage for that feature."""
        found: dict[str, Candidate] = {}
        for feature in features:
            result = retrieve(
                self.session, feature.text, embedder=self.embedder, config=self.retrieval
            )
            seen_here: set[str] = set()
            rank = 0
            for passage in result.passages:
                candidate = self._candidate_of(passage)
                if own_document is not None and candidate.id == own_document.id:
                    continue  # the invention itself is not prior art for itself
                if candidate.key in seen_here:
                    continue
                if not self._relevant(passage):
                    continue
                rank += 1
                seen_here.add(candidate.key)
                entry = found.setdefault(candidate.key, candidate)
                entry.rank_score += 1.0 / (self.retrieval.rrf_k + rank)
                entry.features_matched += 1
        ranked = sorted(found.values(), key=lambda c: (-c.rank_score, c.label))
        return ranked[:limit]

    def _relevant(self, passage: RetrievedPassage) -> bool:
        """Same lenient gate as question answering: similar enough, or a keyword match."""
        if passage.keyword_score:
            return True
        return (passage.vector_similarity or 0) >= self.retrieval.min_similarity

    def _chart(self, features: list[Feature], candidates: list[Candidate]) -> list[dict]:
        """One verifier call for all cells: each (feature, candidate) is judged against
        that candidate's best passages for the feature."""
        pairs, premises, evidence = [], [], []
        for candidate in candidates:
            scope = (
                {"document_ids": [candidate.id]}
                if candidate.kind == "document"
                else {"patent_ids": [candidate.id]}
            )
            for feature in features:
                config = replace(self.retrieval, top_k=PASSAGES_PER_CELL)
                passages = retrieve(
                    self.session, feature.text, embedder=self.embedder, config=config, **scope
                ).passages
                pairs.append((feature, candidate))
                premises.append([_premise(p) for p in passages])
                evidence.append(passages)
        judgements = self.verifier.judge([f.hypothesis for f, _ in pairs], premises)

        cells = []
        for (feature, candidate), passages, judgement in zip(
            pairs, evidence, judgements, strict=True
        ):
            verdict = VERDICT_OF.get(judgement.verdict, NOT_FOUND)
            best = (
                passages[judgement.best_passage]
                if judgement.best_passage is not None and passages
                else None
            )
            cells.append(
                {
                    "feature": feature.id,
                    "candidate": candidate.key,
                    "verdict": verdict,
                    "score": judgement.score,
                    "reason": judgement.reason,
                    "passage": _passage_json(best) if best and verdict != NOT_FOUND else None,
                }
            )
        return cells

    def _summarise(self, text, features, candidates, cells, imported, own_document) -> dict:
        points = {DISCLOSED: 1.0, PARTIALLY: 0.5, NOT_FOUND: 0.0}
        by_candidate = {
            c.key: [cell for cell in cells if cell["candidate"] == c.key] for c in candidates
        }
        candidate_json = []
        for c in candidates:
            mine = by_candidate[c.key]
            overlap = sum(points[cell["verdict"]] for cell in mine) / len(features)
            candidate_json.append(
                {
                    "key": c.key,
                    "kind": c.kind,
                    "id": str(c.id),
                    "label": c.label,
                    "title": c.title,
                    "url": c.url,
                    "rank_score": round(c.rank_score, 5),
                    "overlap": round(overlap, 4),
                    "disclosed": sum(cell["verdict"] == DISCLOSED for cell in mine),
                    "partially": sum(cell["verdict"] == PARTIALLY for cell in mine),
                }
            )
        candidate_json.sort(key=lambda c: (-c["overlap"], -c["rank_score"]))

        feature_json = []
        for f in features:
            mine = [cell for cell in cells if cell["feature"] == f.id]
            feature_json.append(
                f.to_json()
                | {
                    "disclosed_in": [c["candidate"] for c in mine if c["verdict"] == DISCLOSED],
                    "partially_in": [c["candidate"] for c in mine if c["verdict"] == PARTIALLY],
                }
            )
        not_found = [
            f["id"] for f in feature_json if not f["disclosed_in"] and not f["partially_in"]
        ]
        return {
            "description": text,
            "own_document": (
                {"id": str(own_document.id), "label": own_document.filename}
                if own_document
                else None
            ),
            "features": feature_json,
            "candidates": candidate_json,
            "cells": cells,
            "not_found_features": not_found,
            "imported_patents": imported,
            "verifier": self.verifier.name,
            "disclaimer": DISCLAIMER,
        }

    # ------------------------------------------------------------------ storage

    def _store(self, run: AgentRun, result: dict, steps: list[dict], started: float) -> None:
        run = self.session.get(AgentRun, run.id)
        for index, step in enumerate(steps):
            run.tool_calls.append(
                ToolCall(
                    step_index=index,
                    tool_name=step["tool"],
                    input={},
                    output_summary=step.get("summary"),
                    success=step["success"],
                    latency_ms=step["latency_ms"],
                )
            )
        rank = 0
        for cell in result["cells"]:
            passage = cell["passage"]
            if passage is None:
                continue
            rank += 1
            run.retrieval_results.append(
                RetrievalResult(
                    rank=rank,
                    source_type="upload" if passage["document_id"] else passage["source_type"],
                    chunk_id=uuid.UUID(passage["chunk_id"]),
                    patent_id=uuid.UUID(passage["patent_id"]) if passage["patent_id"] else None,
                    method="hybrid",
                    score=cell["score"],
                    retrieved_text=passage["text"],
                    cited_in_answer=True,
                )
            )
        run.plan = {"steps": [s["tool"] for s in steps]}
        run.answer = result | {"steps": steps}
        run.status = "succeeded"
        run.answer_text = None
        run.latency_ms = round((time.perf_counter() - started) * 1000)
        run.completed_at = datetime.now(UTC)
        usage = getattr(self.verifier, "last_usage", None)
        if usage and any(usage):
            run.prompt_tokens, run.completion_tokens = usage
        self.session.commit()

    def _fail(self, run: AgentRun, started: float, steps: list[dict]) -> None:
        self.session.rollback()
        run = self.session.get(AgentRun, run.id)
        if run is not None:
            run.status = "failed"
            run.plan = {"steps": [s["tool"] for s in steps]}
            run.latency_ms = round((time.perf_counter() - started) * 1000)
            run.completed_at = datetime.now(UTC)
            self.session.commit()

    # ------------------------------------------------------------------ helpers

    def _document(self, document_id: uuid.UUID) -> Document:
        document = self.session.get(Document, document_id)
        if document is None or document.status != "ready" or not visible(document.owner_id):
            raise NotFoundError("Document not found or not processed yet.")
        return document

    def _document_text(self, document: Document) -> str:
        """Abstract + first claim (or the first passages) of an uploaded draft."""
        chunks = self.session.scalars(
            select(Chunk).where(Chunk.document_id == document.id).order_by(Chunk.chunk_index)
        ).all()
        claim_1 = next((c.text for c in chunks if (c.meta or {}).get("claim_number") == 1), None)
        abstract = next((c.text for c in chunks if c.section == "abstract"), None)
        parts = [p for p in (abstract, claim_1) if p]
        return "\n\n".join(parts) if parts else "\n\n".join(c.text for c in chunks[:3])

    @staticmethod
    def _candidate_of(passage: RetrievedPassage) -> Candidate:
        chunk = passage.chunk
        if chunk.document is not None:
            d = chunk.document
            return Candidate(f"document:{d.id}", "document", d.id, d.filename, d.title, None)
        p = chunk.patent
        return Candidate(f"patent:{p.id}", "patent", p.id, p.publication_number, p.title, p.url)

    def _config_snapshot(self, use_patent_search: bool, max_candidates: int) -> dict:
        s = self.settings
        return {
            "pipeline": PIPELINE,
            "llm_model": self.llm.model,
            "embedding_model": self.embedder.name,
            "verifier": {"method": s.verifier_method, "nli_model": s.verifier_nli_model},
            "retrieval": {"mode": s.retrieval_mode, "candidate_k": s.retrieval_candidate_k},
            "passages_per_cell": PASSAGES_PER_CELL,
            "max_candidates": max_candidates,
            "patent_search": use_patent_search,
            "patent_sources": sorted(self.sources),
        }


class _step:
    """Context manager that times one step and records success/failure."""

    def __init__(self, steps: list[dict], tool: str):
        self.entry: dict[str, Any] = {"tool": tool, "success": False, "latency_ms": 0}
        steps.append(self.entry)

    def __enter__(self) -> dict:
        self.started = time.perf_counter()
        return self.entry

    def __exit__(self, exc_type, exc, tb) -> None:
        self.entry["latency_ms"] = round((time.perf_counter() - self.started) * 1000)
        self.entry["success"] = exc_type is None


def _location(passage: RetrievedPassage) -> str:
    chunk = passage.chunk
    source = chunk.document.filename if chunk.document else chunk.patent.publication_number
    claim = (chunk.meta or {}).get("claim_number")
    where = f"claim {claim}" if claim else (chunk.section or "text")
    return f"{source}, {where}"


def _premise(passage: RetrievedPassage) -> str:
    return f"Source: {_location(passage)}.\n{passage.chunk.text}"


def _passage_json(passage: RetrievedPassage) -> dict:
    chunk = passage.chunk
    return {
        "chunk_id": str(chunk.id),
        "document_id": str(chunk.document_id) if chunk.document_id else None,
        "patent_id": str(chunk.patent_id) if chunk.patent_id else None,
        "source_type": "upload" if chunk.document_id else chunk.patent.source,
        "location": _location(passage),
        "section": chunk.section,
        "claim_number": (chunk.meta or {}).get("claim_number"),
        "page_number": chunk.page_number,
        "text": chunk.text,
    }
