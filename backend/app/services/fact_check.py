"""Check any text against your sources (the Checker page).

Each sentence of the text is checked against the passages most like it in the chosen
documents and patents (the same hybrid retrieval as answers), by the same verifier, with
the same display-only explanations as an answer's X-ray. Pasted text has no citations, so
every sentence is judged against its own closest passages and none counts as
"misattributed". Stored as a run with pipeline "fact_check" so it appears in the user's
history and can be reopened; experiments select their own runs, so it never enters one.
"""

import logging
import time
import uuid

from app.core.errors import AppError
from app.models import AgentRun
from app.rag.generation import ParsedAnswer, evidence_item, parse_answer
from app.rag.retrieval import RetrievedPassage, retrieve
from app.services.answering import AnswerService
from app.verification.checker import (
    ClaimResult,
    VerificationReport,
    claims_from_answer,
    explain,
    premise_for,
)
from app.verification.issues import closest_passage
from app.verification.verifiers import UNSUPPORTED

logger = logging.getLogger(__name__)

MAX_SENTENCES = 30
PER_SENTENCE = 4  # passages retrieved for each sentence


class FactChecker(AnswerService):
    pipeline = "fact_check"

    def check(
        self,
        text: str,
        *,
        document_ids: list[uuid.UUID] | None = None,
        patent_ids: list[uuid.UUID] | None = None,
    ) -> AgentRun:
        started = time.perf_counter()
        config, reranker = self._retrieval_setup(PER_SENTENCE, None, False)
        run = self._start_run(
            text,
            None,
            document_ids,
            patent_ids,
            plan={
                "intent": "fact_check",
                "sources": self._sources_in_scope(document_ids, patent_ids),
                "steps": ["retrieve", "verify"],
            },
            config=self._config_snapshot(config, reranker),
        )
        try:
            self._check(run, text, config, document_ids, patent_ids, started)
        except AppError as exc:
            self._fail(run, exc.message, started)
            raise
        except Exception as exc:
            logger.exception("Fact check failed for run %s", run.id)
            self._fail(run, "Internal error while checking.", started)
            raise AppError(
                "The text could not be checked.", code="check_failed", status_code=500
            ) from exc
        return run

    def _check(self, run, text, config, document_ids, patent_ids, started) -> None:
        parsed = parse_answer(text, set())
        claims, skipped = claims_from_answer(parsed) if parsed.status == "answered" else ([], [])
        claims = claims[:MAX_SENTENCES]
        if not claims:
            empty = ParsedAnswer(
                status="insufficient_evidence",
                text="",
                insufficient_reason="There is no full statement to check (at least four words).",
            )
            self._finish(run, empty, [], [], [], None, {}, started)
            return

        timings: dict[str, int] = {}
        retrieve_started = time.perf_counter()
        passages: list[RetrievedPassage] = []
        label_of: dict = {}
        per_claim: list[list[str]] = []
        for claim in claims:
            labels = []
            for hit in retrieve(
                self.session,
                claim.text,
                embedder=self.embedder,
                config=config,
                document_ids=document_ids,
                patent_ids=patent_ids,
            ).passages:
                if hit.chunk.id not in label_of:
                    label_of[hit.chunk.id] = f"E{len(passages) + 1}"
                    passages.append(hit)
                labels.append(label_of[hit.chunk.id])
            per_claim.append(labels)
        for rank, passage in enumerate(passages, start=1):
            passage.rank = rank
        timings["retrieve"] = round((time.perf_counter() - retrieve_started) * 1000)

        evidence = [evidence_item(label_of[p.chunk.id], p) for p in passages]
        premise = {item.label: premise_for(item) for item in evidence}
        verify_started = time.perf_counter()
        verifier = self.verifier()
        judgements = verifier.judge(
            [c.text for c in claims], [[premise[lbl] for lbl in labels] for labels in per_claim]
        )
        results = []
        for index, (claim, judgement, labels) in enumerate(
            zip(claims, judgements, per_claim, strict=True)
        ):
            best = labels[judgement.best_passage] if judgement.best_passage is not None else None
            supported = best is not None and judgement.verdict != UNSUPPORTED
            # Unsupported: the model's "best" passage is arbitrary when every score is near
            # zero, so the closest is the one sharing most words (of this sentence's own)
            closest = closest_passage(claim.text, {lbl: premise[lbl] for lbl in labels})
            results.append(
                ClaimResult(
                    index,
                    claim.text,
                    [],
                    judgement.verdict,
                    judgement.score,
                    judgement.reason,
                    [best] if supported else [],
                    source_text=claim.source_text,
                    closest=None if supported else closest,
                )
            )
        report = VerificationReport(verifier.name, explain(results, premise), skipped)
        timings["verify"] = round((time.perf_counter() - verify_started) * 1000)
        usage = getattr(verifier, "last_usage", None)
        if usage and any(usage):
            run.prompt_tokens, run.completion_tokens = usage

        used = list(dict.fromkeys(lbl for r in results for lbl in r.supporting))
        parsed.cited_labels = used  # shown as the passages that back the text
        records = [self._record(run, p) for p in passages]
        self._finish(
            run, parsed, evidence, passages, records, None, timings, started, verification=report
        )
