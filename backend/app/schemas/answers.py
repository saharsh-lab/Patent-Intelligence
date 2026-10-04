"""API shapes for asking questions and viewing past runs."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models import AgentRun

SOURCE_LABELS = {
    "uploaded_documents": "Uploaded documents",
    "imported_patents": "Imported patents",
    "patent_databases": "Patent databases",
    "patents:epo": "EPO",
    "patents:demo": "Demo patents",
    "none": "None",
}


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    document_ids: list[uuid.UUID] | None = Field(
        default=None, max_length=50, description="Limit search to these uploaded documents"
    )
    patent_ids: list[uuid.UUID] | None = Field(
        default=None, max_length=50, description="Limit search to these imported patents"
    )
    conversation_id: uuid.UUID | None = None
    # Optional overrides, mainly for experiments
    top_k: int | None = Field(default=None, ge=1, le=20)
    retrieval_mode: Literal["hybrid", "vector", "keyword"] | None = None
    rerank: bool | None = None
    pipeline: Literal["agentic", "baseline"] | None = Field(
        default=None, description="Default: DEFAULT_PIPELINE setting"
    )
    live_search: bool = Field(
        default=False,
        description="Agent only: also search the patent databases and import the best matches",
    )


class AnswerSentenceOut(BaseModel):
    text: str
    citations: list[str]


class EvidenceOut(BaseModel):
    label: str | None = Field(description="E1, E2... if this passage was given to the model")
    cited: bool
    chunk_id: str
    document_id: str | None
    patent_id: str | None
    source_label: str
    source_type: str = "upload"  # upload | epo | demo | ...
    source_url: str | None = None
    source_title: str | None = None
    section: str | None
    claim_number: int | None
    page_number: int | None
    text: str
    rank: int
    method: str
    score: float
    vector_similarity: float | None
    keyword_score: float | None
    rerank_score: float | None


class StepOut(BaseModel):
    """One tool call made by the agent (safe summary, no hidden reasoning)."""

    step_index: int
    tool_name: str
    success: bool
    output_summary: str | None
    latency_ms: int | None


class RunSummaryOut(BaseModel):
    """The safe, user-facing description of what the system did (no hidden reasoning)."""

    sources_searched: list[str]
    passages_retrieved: int
    passages_cited: int
    llm_called: bool


class RunMetricsOut(BaseModel):
    latency_ms: int | None
    timings_ms: dict[str, int]
    prompt_tokens: int | None
    completion_tokens: int | None
    cost_usd: float | None
    citation_coverage: float | None = Field(
        description="Share of answer sentences that cite evidence (not yet verified support)"
    )
    invalid_citations: list[str]


class AskResponse(BaseModel):
    run_id: uuid.UUID
    query_id: uuid.UUID
    conversation_id: uuid.UUID | None
    question: str
    status: str
    pipeline: str
    answer: str | None
    sentences: list[AnswerSentenceOut]
    interpretation: str | None
    insufficient_reason: str | None
    missing_info: str | None = None
    comparison: dict | None = Field(
        default=None, description="Structured comparison table (compare tasks only)"
    )
    grounding_score: float | None = Field(
        default=None, description="(supported + 0.5 × partially supported) / checked claims"
    )
    verification: dict | None = Field(
        default=None, description="Claim-by-claim verdicts (method, counts, claims)"
    )
    verification_attempts: list[dict] = Field(
        default_factory=list,
        description="Grounding of each attempt when the answer was regenerated",
    )
    error_message: str | None
    evidence: list[EvidenceOut]
    summary: RunSummaryOut
    metrics: RunMetricsOut
    intent: str | None = None
    planner: str | None = Field(default=None, description="rules | llm | llm_fallback_rules")
    legal_question: bool = False
    targets: list[dict] = Field(default_factory=list)
    steps: list[StepOut] = Field(default_factory=list)
    recoveries: list[str] = Field(default_factory=list)
    created_at: datetime

    @classmethod
    def from_run(cls, run: AgentRun) -> "AskResponse":
        answer = run.answer or {}
        evidence = answer.get("evidence", [])
        return cls(
            run_id=run.id,
            query_id=run.query_id,
            conversation_id=run.query.conversation_id,
            question=run.query.query_text,
            status=run.status,
            pipeline=run.pipeline,
            answer=run.answer_text,
            sentences=answer.get("sentences", []),
            interpretation=answer.get("interpretation"),
            insufficient_reason=answer.get("insufficient_reason"),
            missing_info=answer.get("missing_info"),
            comparison=answer.get("comparison"),
            grounding_score=run.grounding_score,
            verification=answer.get("verification"),
            verification_attempts=answer.get("verification_attempts", []),
            error_message=run.error_message,
            evidence=evidence,
            summary=RunSummaryOut(
                sources_searched=[
                    SOURCE_LABELS.get(s, s)
                    for s in (run.plan or {}).get("sources", ["uploaded_documents"])
                ],
                passages_retrieved=len(evidence),
                passages_cited=sum(1 for e in evidence if e["cited"]),
                llm_called=answer.get("llm_called", False),
            ),
            metrics=RunMetricsOut(
                latency_ms=run.latency_ms,
                timings_ms=answer.get("timings_ms", {}),
                prompt_tokens=run.prompt_tokens,
                completion_tokens=run.completion_tokens,
                cost_usd=float(run.cost_usd) if run.cost_usd is not None else None,
                citation_coverage=answer.get("citation_coverage"),
                invalid_citations=answer.get("invalid_citations", []),
            ),
            created_at=run.started_at,
            intent=(run.plan or {}).get("intent"),
            planner=((run.plan or {}).get("analysis") or {}).get("analyzer"),
            legal_question=bool(((run.plan or {}).get("analysis") or {}).get("legal_question")),
            targets=(run.plan or {}).get("targets", []),
            steps=[
                StepOut(
                    step_index=c.step_index,
                    tool_name=c.tool_name,
                    success=c.success,
                    output_summary=c.output_summary,
                    latency_ms=c.latency_ms,
                )
                for c in run.tool_calls
            ],
            recoveries=(run.plan or {}).get("recoveries", []),
        )


class RunListItem(BaseModel):
    run_id: uuid.UUID
    question: str
    status: str
    pipeline: str
    latency_ms: int | None
    created_at: datetime
