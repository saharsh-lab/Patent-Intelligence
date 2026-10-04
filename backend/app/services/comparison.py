"""Compare 2–4 sources (uploaded documents, imported patents, or patent numbers to fetch)
as a structured, cited table. Each comparison is stored as a run (pipeline "comparison")
so it appears in history and can be evaluated like any other answer."""

import time
import uuid
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError, ValidationFailedError
from app.core.ownership import visible
from app.intelligence.comparison import ComparisonBuilder
from app.llm.providers import LLMProvider, estimate_cost_usd
from app.models import AgentRun, Document, Patent
from app.patents.base import PatentSource
from app.patents.registry import choose_source
from app.rag.embeddings import EmbeddingProvider
from app.rag.generation import parse_answer
from app.services.answering import AnswerService
from app.services.patents import PatentService


class ComparisonService(AnswerService):
    pipeline = "comparison"

    def __init__(
        self,
        session: Session,
        settings: Settings,
        embedder: EmbeddingProvider,
        llm: LLMProvider,
        patent_sources: dict[str, PatentSource],
    ):
        super().__init__(session, settings, embedder, llm)
        self.patents = PatentService(session, settings, embedder, patent_sources)

    def resolve_mode(self, mode: str) -> str:
        if mode == "auto":
            return "extractive" if self.settings.llm_provider == "fake" else "llm"
        return mode

    def compare(
        self, refs: list[dict], question: str | None = None, mode: str = "auto"
    ) -> AgentRun:
        started = time.perf_counter()
        resolved = self._resolve_refs(refs)
        if len({r for r in resolved}) != len(resolved):
            raise ValidationFailedError("Choose different sources to compare.")
        mode = self.resolve_mode(mode)
        config, _ = self._retrieval_setup(None, None, False)
        builder = ComparisonBuilder(self.session, self.embedder, self.llm, config)
        sources = builder.resolve(resolved)
        title = question or "Compare " + " with ".join(s.label for s in sources)
        run = self._start_run(
            title,
            None,
            [i for k, i in resolved if k == "document"],
            [i for k, i in resolved if k == "patent"],
            plan={
                "intent": "compare",
                "sources": sorted(
                    {
                        "uploaded_documents" if k == "document" else "imported_patents"
                        for k, _ in resolved
                    }
                ),
            },
            config=self._config_snapshot(config, None) | {"comparison_mode": mode},
        )
        try:
            result = builder.build(sources, question or "", mode=mode)
        except AppError as exc:
            self._fail(run, exc.message, started)
            raise
        passages = [item.passage for item in result.evidence]
        results = [self._record(run, p) for p in passages]
        response = result.llm_response
        if response is not None:
            run.prompt_tokens, run.completion_tokens = (
                response.prompt_tokens,
                response.completion_tokens,
            )
            run.cost_usd = Decimal(str(round(estimate_cost_usd(response, self.settings), 6)))
        parsed = parse_answer(result.answer_text(), set(result.label_source))
        parsed.cited_labels = result.cited_labels()  # table cells count as citations too
        timings = {"gather evidence": result.gather_ms}
        if response:
            timings["generate"] = response.latency_ms
        table = result.to_json()
        verification = self._verify(run, parsed, result.evidence, timings, comparison=table)
        self._finish(
            run,
            parsed,
            result.evidence,
            passages,
            results,
            response,
            timings,
            started,
            extra_answer={"comparison": table},
            verification=verification,
        )
        return run

    def _resolve_refs(self, refs: list[dict]) -> list[tuple[str, uuid.UUID]]:
        if not 2 <= len(refs) <= 4:
            raise ValidationFailedError("Select between 2 and 4 sources to compare.")
        resolved = []
        for ref in refs:
            if ref.get("document_id"):
                doc = self.session.get(Document, ref["document_id"])
                if doc is None or doc.status != "ready" or not visible(doc.owner_id):
                    raise ValidationFailedError("A selected document is not available.")
                resolved.append(("document", doc.id))
            elif ref.get("patent_id"):
                if self.session.get(Patent, ref["patent_id"]) is None:
                    raise ValidationFailedError("A selected patent is not available.")
                resolved.append(("patent", ref["patent_id"]))
            elif ref.get("publication_number"):
                number = ref["publication_number"]
                patent, _ = self.patents.import_patent(
                    choose_source(self.patents.sources, number.strip().upper()), number
                )
                resolved.append(("patent", patent.id))
            else:
                raise ValidationFailedError("Each source needs a document, patent or number.")
        return resolved
