"""Answer a question with the baseline RAG pipeline, recording everything for evaluation.

    question → hybrid retrieval → (enough evidence?) → LLM with numbered evidence
             → parse & check citations → stored answer

"Baseline" because it always does the same steps over uploaded documents. The
agent (Phase 6) will decide which steps and sources to use, and Experiment A
compares the two. Every run is stored with a snapshot of its settings, so
results can be traced back to exactly how they were produced.
"""

import logging
import time
import uuid
from dataclasses import asdict
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError
from app.core.ownership import current_owner
from app.llm.providers import LLMProvider, estimate_cost_usd
from app.models import AgentRun, Chunk, ClaimVerification, Query, RetrievalResult
from app.rag.embeddings import EmbeddingProvider
from app.rag.generation import (
    PROMPT_VERSION,
    EvidenceItem,
    ParsedAnswer,
    build_evidence,
    build_messages,
    parse_answer,
)
from app.rag.reranker import Reranker, get_reranker_for
from app.rag.retrieval import (
    RetrievalConfig,
    RetrievedPassage,
    has_sufficient_evidence,
    retrieve,
)
from app.verification.checker import VerificationReport, verify_answer
from app.verification.verifiers import build_verifier

logger = logging.getLogger(__name__)

PIPELINE = "baseline_rag"


class AnswerService:
    pipeline = PIPELINE

    def __init__(
        self,
        session: Session,
        settings: Settings,
        embedder: EmbeddingProvider,
        llm: LLMProvider,
    ):
        self.session = session
        self.settings = settings
        self.embedder = embedder
        self.llm = llm

    def ask(
        self,
        question: str,
        *,
        document_ids: list[uuid.UUID] | None = None,
        patent_ids: list[uuid.UUID] | None = None,
        conversation_id: uuid.UUID | None = None,
        top_k: int | None = None,
        retrieval_mode: str | None = None,
        rerank: bool | None = None,
    ) -> AgentRun:
        started = time.perf_counter()
        config, reranker = self._retrieval_setup(top_k, retrieval_mode, rerank)
        run = self._start_run(
            question,
            conversation_id,
            document_ids,
            patent_ids,
            plan={
                "sources": self._sources_in_scope(document_ids, patent_ids),
                "steps": ["retrieve", "generate"],
            },
            config=self._config_snapshot(config, reranker),
        )

        try:
            self._execute(run, question, config, reranker, document_ids, patent_ids, started)
        except AppError as exc:
            self._fail(run, exc.message, started)
            raise
        except Exception as exc:
            logger.exception("Answer pipeline failed for run %s", run.id)
            self._fail(run, "Internal error while answering.", started)
            raise AppError(
                "The question could not be answered.", code="answer_failed", status_code=500
            ) from exc
        return run

    # ------------------------------------------------------------------ pipeline

    def _execute(
        self,
        run: AgentRun,
        question: str,
        config: RetrievalConfig,
        reranker: Reranker | None,
        document_ids: list[uuid.UUID] | None,
        patent_ids: list[uuid.UUID] | None,
        started: float,
    ) -> None:
        retrieval = retrieve(
            self.session,
            question,
            embedder=self.embedder,
            config=config,
            reranker=reranker,
            document_ids=document_ids,
            patent_ids=patent_ids,
        )
        timings = dict(retrieval.timings_ms)
        results = [self._record(run, p) for p in retrieval.passages]

        sufficient, reason = has_sufficient_evidence(retrieval, config)
        if not sufficient:
            parsed = ParsedAnswer(
                status="insufficient_evidence", text="", insufficient_reason=reason
            )
            self._finish(run, parsed, [], retrieval.passages, results, None, timings, started)
            return

        evidence = build_evidence(retrieval.passages, self.settings.max_context_tokens)
        generation_started = time.perf_counter()
        response = self.llm.complete(
            build_messages(question, evidence),
            temperature=self.settings.llm_temperature,
            max_tokens=self.settings.llm_max_tokens,
        )
        timings["generate"] = round((time.perf_counter() - generation_started) * 1000)
        parsed = parse_answer(response.text, {item.label for item in evidence})

        run.prompt_tokens = response.prompt_tokens
        run.completion_tokens = response.completion_tokens
        run.cost_usd = Decimal(str(round(estimate_cost_usd(response, self.settings), 6)))
        run.config = {**run.config, "llm_model_reported": response.model}
        if response.usage_estimated:
            run.config = {**run.config, "token_usage_estimated": True}
        # Baseline = conventional RAG: claims are verified and reported, never regenerated
        verification = self._verify(run, parsed, evidence, timings)
        self._finish(
            run,
            parsed,
            evidence,
            retrieval.passages,
            results,
            response,
            timings,
            started,
            verification=verification,
        )

    def _verify(self, run, parsed, evidence, timings, comparison: dict | None = None):
        if self.settings.verify_mode == "off" or parsed.status != "answered":
            return None
        verify_started = time.perf_counter()
        verifier = self.verifier()
        report = verify_answer(
            verifier,
            parsed,
            evidence,
            comparison=comparison,
            uncited_supported=self.settings.verifier_uncited_supported,
        )
        timings["verify"] = round((time.perf_counter() - verify_started) * 1000)
        usage = getattr(verifier, "last_usage", None)
        if usage and any(usage):  # LLM-judge tokens count toward the run's cost
            run.prompt_tokens = (run.prompt_tokens or 0) + usage[0]
            run.completion_tokens = (run.completion_tokens or 0) + usage[1]
        return report

    def _record(self, run: AgentRun, passage: RetrievedPassage) -> RetrievalResult:
        chunk = passage.chunk
        result = RetrievalResult(
            rank=passage.rank,
            source_type="upload" if chunk.document_id else chunk.patent.source,
            chunk_id=chunk.id,
            patent_id=chunk.patent_id,
            method=passage.method,
            score=passage.score,
            rerank_score=passage.rerank_score,
            retrieved_text=chunk.text,
        )
        run.retrieval_results.append(result)
        return result

    def _finish(
        self,
        run: AgentRun,
        parsed: ParsedAnswer,
        evidence: list[EvidenceItem],
        passages: list[RetrievedPassage],
        results: list[RetrievalResult],
        response: Any,
        timings: dict[str, int],
        started: float,
        extra_answer: dict | None = None,
        verification: VerificationReport | None = None,
    ) -> None:
        label_of = {item.passage.chunk.id: item.label for item in evidence}
        cited = set(parsed.cited_labels)
        for result in results:
            result.cited_in_answer = label_of.get(result.chunk_id) in cited
        if verification is not None:
            self._store_verification(run, verification, label_of, results)

        run.status = "succeeded" if parsed.status == "answered" else "insufficient_evidence"
        run.answer_text = parsed.text or None
        run.latency_ms = round((time.perf_counter() - started) * 1000)
        run.completed_at = datetime.now(UTC)
        run.answer = {
            "text": parsed.text,
            "sentences": [asdict(s) for s in parsed.sentences],
            "interpretation": parsed.interpretation,
            "insufficient_reason": parsed.insufficient_reason,
            "missing_info": parsed.missing_info,
            "invalid_citations": parsed.invalid_citations,
            "citation_coverage": parsed.citation_coverage,
            "llm_called": response is not None,
            "evidence": [
                self._evidence_json(p, label_of.get(p.chunk.id), label_of.get(p.chunk.id) in cited)
                for p in passages
            ],
            "timings_ms": timings,
            "verification": verification.to_json() if verification else None,
            **(extra_answer or {}),
        }
        self.session.commit()
        logger.info(
            "Run %s %s: %d passages, %d cited, %d ms",
            run.id,
            run.status,
            len(passages),
            len(cited),
            run.latency_ms,
        )

    def _store_verification(
        self,
        run: AgentRun,
        report: VerificationReport,
        label_of: dict,
        results: list[RetrievalResult],
    ) -> None:
        """One claim_verifications row per checked statement + the run's grounding score."""
        self.session.flush()  # give retrieval_results their ids
        result_of_label = {label_of.get(r.chunk_id): r for r in results if r.chunk_id in label_of}
        for claim in report.claims:
            evidence = [
                {"label": label, "retrieval_result_id": str(result_of_label[label].id)}
                for label in claim.supporting or claim.cited
                if label in result_of_label
            ]
            run.claim_verifications.append(
                ClaimVerification(
                    claim_index=claim.index,
                    claim_text=claim.text,
                    verdict=claim.verdict,
                    support_score=claim.score,
                    evidence_ids=evidence,
                    method=report.method,
                )
            )
        run.grounding_score = report.grounding_score

    def verifier(self):
        return build_verifier(
            self.settings.verifier_method,
            nli_model=self.settings.verifier_nli_model,
            llm=self.llm,
        )

    def _fail(self, run: AgentRun, message: str, started: float) -> None:
        self.session.rollback()
        run = self.session.get(AgentRun, run.id)
        if run is not None:
            run.status = "failed"
            run.error_message = message
            run.latency_ms = round((time.perf_counter() - started) * 1000)
            run.completed_at = datetime.now(UTC)
            self.session.commit()

    # ------------------------------------------------------------------ helpers

    def _retrieval_setup(
        self, top_k: int | None, retrieval_mode: str | None, rerank: bool | None
    ) -> tuple[RetrievalConfig, Reranker | None]:
        config = RetrievalConfig(
            mode=retrieval_mode or self.settings.retrieval_mode,
            top_k=top_k or self.settings.retrieval_top_k,
            candidate_k=self.settings.retrieval_candidate_k,
            rrf_k=self.settings.rrf_k,
            min_similarity=self.settings.retrieval_min_similarity,
        )
        use_rerank = self.settings.reranker_enabled if rerank is None else rerank
        reranker = get_reranker_for(
            self.settings.model_copy(update={"reranker_enabled": use_rerank})
        )
        return config, reranker

    def _start_run(
        self,
        question: str,
        conversation_id: uuid.UUID | None,
        document_ids: list[uuid.UUID] | None,
        patent_ids: list[uuid.UUID] | None,
        *,
        plan: dict,
        config: dict,
    ) -> AgentRun:
        query = Query(
            owner_id=current_owner(),
            query_text=question,
            conversation_id=conversation_id,
            meta={
                "document_ids": [str(d) for d in document_ids or []],
                "patent_ids": [str(p) for p in patent_ids or []],
            },
        )
        run = AgentRun(
            query=query, pipeline=self.pipeline, status="running", plan=plan, config=config
        )
        self.session.add(run)
        self.session.commit()
        return run

    def _sources_in_scope(
        self, document_ids: list[uuid.UUID] | None, patent_ids: list[uuid.UUID] | None
    ) -> list[str]:
        """Which kinds of source this question searches (for the user-facing summary)."""
        if document_ids or patent_ids:
            return (["uploaded_documents"] if document_ids else []) + (
                ["imported_patents"] if patent_ids else []
            )
        sources = []
        if self.session.scalar(select(Chunk.id).where(Chunk.document_id.is_not(None)).limit(1)):
            sources.append("uploaded_documents")
        if self.session.scalar(select(Chunk.id).where(Chunk.patent_id.is_not(None)).limit(1)):
            sources.append("imported_patents")
        return sources or ["uploaded_documents"]

    @staticmethod
    def _evidence_json(passage: RetrievedPassage, label: str | None, cited: bool) -> dict:
        chunk = passage.chunk
        return {
            "label": label,
            "cited": cited,
            "chunk_id": str(chunk.id),
            "document_id": str(chunk.document_id) if chunk.document_id else None,
            "patent_id": str(chunk.patent_id) if chunk.patent_id else None,
            "source_label": (
                chunk.document.filename if chunk.document else chunk.patent.publication_number
            ),
            "source_type": "upload" if chunk.document else chunk.patent.source,
            "source_url": chunk.patent.url if chunk.patent else None,
            "source_title": chunk.document.title if chunk.document else chunk.patent.title,
            "section": chunk.section,
            "claim_number": (chunk.meta or {}).get("claim_number"),
            "page_number": chunk.page_number,
            "text": chunk.text,
            "rank": passage.rank,
            "method": passage.method,
            "score": passage.score,
            "vector_similarity": passage.vector_similarity,
            "keyword_score": passage.keyword_score,
            "rerank_score": passage.rerank_score,
        }

    def _config_snapshot(self, config: RetrievalConfig, reranker: Reranker | None) -> dict:
        s = self.settings
        return {
            "pipeline": self.pipeline,
            "prompt_version": PROMPT_VERSION,
            "llm_provider": s.llm_provider,
            "llm_model": self.llm.model,
            "temperature": s.llm_temperature,
            "max_tokens": s.llm_max_tokens,
            "embedding_model": self.embedder.name,
            "retrieval": asdict(config),
            "reranker": reranker.name if reranker else None,
            "max_context_tokens": s.max_context_tokens,
            "chunking_strategy": s.chunking_strategy,
            "verification": {
                "mode": s.verify_mode,
                "method": s.verifier_method,
                "nli_model": s.verifier_nli_model,
                "threshold": s.grounding_threshold,
            },
        }
