"""Answer a question with the agentic pipeline (LangGraph), recording every step.

Shares run recording with the baseline (`AnswerService`), so both pipelines are
stored and evaluated identically, which Experiment A needs for a fair comparison.
Additionally stores the intent, the resolved targets, every tool call, and any
recovery attempts.
"""

import logging
import time
import uuid
from decimal import Decimal

from sqlalchemy.orm import Session

from app.agents.graph import AgentGraph
from app.agents.tools import ToolContext
from app.core.config import Settings
from app.core.errors import AppError
from app.llm.providers import LLMProvider, LLMResponse, estimate_cost_usd
from app.models import AgentRun, ToolCall
from app.patents.base import PatentSource
from app.rag.embeddings import EmbeddingProvider
from app.services.answering import AnswerService
from app.services.patents import PatentService

logger = logging.getLogger(__name__)

SOURCE_OF_TOOL = {
    "search_patents": "patent_databases",
    "get_patent_details": "patent_databases",
}


class UsageTrackingLLM(LLMProvider):
    """Wraps an LLM and adds up token usage over all calls in one run."""

    def __init__(self, inner: LLMProvider):
        self.inner = inner
        self.model = inner.model
        self.calls = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.estimated = False

    def complete(self, messages, *, temperature, max_tokens) -> LLMResponse:
        response = self.inner.complete(messages, temperature=temperature, max_tokens=max_tokens)
        self.calls += 1
        self.prompt_tokens += response.prompt_tokens
        self.completion_tokens += response.completion_tokens
        self.estimated |= response.usage_estimated
        return response


class AgentService(AnswerService):
    pipeline = "agentic"

    def __init__(
        self,
        session: Session,
        settings: Settings,
        embedder: EmbeddingProvider,
        llm: LLMProvider,
        patent_sources: dict[str, PatentSource],
    ):
        super().__init__(session, settings, embedder, llm)
        self.patent_sources = patent_sources

    def planner(self) -> str:
        if self.settings.agent_planner == "auto":
            return "rules" if self.settings.llm_provider == "fake" else "llm"
        return self.settings.agent_planner

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
        live_search: bool = False,
    ) -> AgentRun:
        """`live_search`: also search the patent databases for this question and import
        the most relevant patents (the chat's "Search patent databases" switch)."""
        started = time.perf_counter()
        config, reranker = self._retrieval_setup(top_k, retrieval_mode, rerank)
        planner = self.planner()
        snapshot = self._config_snapshot(config, reranker) | {
            "agent": {
                "planner": planner,
                "similar_import_limit": self.settings.agent_similar_import_limit,
                "max_recoveries": self.settings.agent_max_recoveries,
                "tool_policy": self.settings.agent_tool_policy,
                "patent_sources": sorted(self.patent_sources),
                "live_fallback": self.settings.agent_live_fallback,
                "live_search": live_search,
            }
        }
        run = self._start_run(
            question,
            conversation_id,
            document_ids,
            patent_ids,
            plan={"planner": planner},
            config=snapshot,
        )

        tracked = UsageTrackingLLM(self.llm)
        ctx = ToolContext(
            session=self.session,
            settings=self.settings,
            embedder=self.embedder,
            llm=tracked,
            patents=PatentService(self.session, self.settings, self.embedder, self.patent_sources),
            retrieval=config,
            reranker=reranker,
            use_llm_helpers=planner == "llm",
        )
        agent = AgentGraph(
            ctx,
            planner=planner,
            similar_import_limit=self.settings.agent_similar_import_limit,
            max_recoveries=self.settings.agent_max_recoveries,
            tool_policy=self.settings.agent_tool_policy,
            live_fallback=self.settings.agent_live_fallback,
            live_import_limit=self.settings.agent_live_import_limit,
        )
        try:
            state = agent.run(
                question, list(document_ids or []), list(patent_ids or []), live_search=live_search
            )
            self._store(run, state, tracked, started)
        except AppError as exc:
            self._fail(run, exc.message, started)
            raise
        except Exception as exc:
            logger.exception("Agent failed for run %s", run.id)
            self._fail(run, "Internal error while answering.", started)
            raise AppError(
                "The question could not be answered.", code="answer_failed", status_code=500
            ) from exc
        return run

    def _store(self, run: AgentRun, state: dict, tracked: UsageTrackingLLM, started: float) -> None:
        run = self.session.get(AgentRun, run.id)  # tools may have committed/rolled back
        log = state["tool_log"]
        for index, entry in enumerate(log):
            run.tool_calls.append(
                ToolCall(
                    step_index=index,
                    tool_name=entry["tool_name"],
                    input=entry["input"],
                    output_summary=entry["output_summary"],
                    success=entry["success"],
                    error_message=None if entry["success"] else entry["output_summary"],
                    latency_ms=entry["latency_ms"],
                )
            )
        analysis = state["analysis"]
        run.plan = {
            "planner": run.plan.get("planner"),
            "intent": analysis.intent,
            "analysis": analysis.to_json(),
            "targets": [t.to_json() for t in state.get("targets", [])],
            "steps": [entry["tool_name"] for entry in log],
            "recoveries": state["recoveries"],
            "sources": self._sources_used(state),
        }
        run.prompt_tokens = tracked.prompt_tokens or None
        run.completion_tokens = tracked.completion_tokens or None
        if tracked.calls:
            usage = LLMResponse(
                "", tracked.model, tracked.prompt_tokens, tracked.completion_tokens, 0
            )
            run.cost_usd = Decimal(str(round(estimate_cost_usd(usage, self.settings), 6)))
        run.config = {**run.config, "llm_calls": tracked.calls}
        if tracked.estimated:
            run.config = {**run.config, "token_usage_estimated": True}

        response = state.get("llm_response")
        passages = state.get("final_passages", [])
        results = [self._record(run, p) for p in passages]
        timings = {f"{i + 1}. {e['tool_name']}": e["latency_ms"] for i, e in enumerate(log)}
        if response is not None:
            timings["generate"] = response.latency_ms
        timings.update(state.get("extra_timings") or {})
        comparison = state.get("comparison")
        attempts = state.get("verify_attempts") or []
        extra: dict = {"comparison": comparison} if comparison else {}
        if len(attempts) > 1:
            # Keep the history: how grounded was each attempt, and which one was kept?
            kept = state.get("verification")
            extra["verification_attempts"] = [
                {
                    "attempt": i + 1,
                    "grounding_score": a["report"].grounding_score,
                    "counts": a["report"].counts(),
                    "answer_text": a["parsed"].text,
                    "kept": a["report"] is kept,
                }
                for i, a in enumerate(attempts)
            ]
            extra["regeneration_added_passages"] = state.get("regeneration_added_passages", 0)
        self._finish(
            run,
            state["parsed"],
            state.get("evidence", []),
            passages,
            results,
            response,
            timings,
            started,
            extra_answer=extra or None,
            verification=state.get("verification"),
        )

    @staticmethod
    def _sources_used(state: dict) -> list[str]:
        sources: list[str] = []
        for entry in state["tool_log"]:
            name = entry["tool_name"]
            if name == "search_uploaded_documents":
                sources += ["uploaded_documents", "imported_patents"]
            elif name in SOURCE_OF_TOOL:
                used = entry.get("sources") or []
                sources += [f"patents:{s}" for s in used] or [SOURCE_OF_TOOL[name]]
        for target in state.get("targets", []):
            sources.append(
                "uploaded_documents" if target.kind == "document" else "imported_patents"
            )
        return list(dict.fromkeys(sources)) or ["none"]
