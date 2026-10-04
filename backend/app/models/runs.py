"""Records of what the system did for each question — the raw data for evaluation.

    queries ─┬─ agent_runs ─┬─ tool_calls           (which tools the agent used)
             │              ├─ retrieval_results    (which passages it found)
             │              ├─ claim_verifications  (was each answer sentence supported?)
             │              └─ evaluations          (computed metrics)

Why runs are separate from queries: in experiments the same question is answered
by several pipelines (e.g. baseline RAG vs. agentic RAG). Each answer is one
`agent_run`, and its `config` column stores the exact settings used, so every
result in the research paper can be traced back to how it was produced.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, created_at_column, json_column, metadata_column, uuid_pk


class Query(Base):
    __tablename__ = "queries"

    id: Mapped[uuid.UUID] = uuid_pk()
    # Groups follow-up questions into one conversation (no separate table needed yet)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    # The user (separate auth database) who asked; None in single-user mode / experiments
    owner_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    query_text: Mapped[str] = mapped_column(Text)
    meta: Mapped[dict[str, Any]] = metadata_column()
    created_at: Mapped[datetime] = created_at_column()

    runs: Mapped[list["AgentRun"]] = relationship(
        back_populates="query", cascade="all, delete-orphan", passive_deletes=True
    )


class AgentRun(Base):
    __tablename__ = "agent_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'succeeded', 'insufficient_evidence', 'failed')",
            name="valid_status",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    query_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("queries.id", ondelete="CASCADE"), index=True
    )
    # Which answering strategy was used: agentic | baseline_rag | fixed_pipeline ...
    pipeline: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(24), default="running", server_default="running")
    # User-facing plan summary, e.g. {"intent": "compare", "sources": ["upload", "epo"]}
    plan: Mapped[dict[str, Any] | None] = mapped_column()
    answer_text: Mapped[str | None] = mapped_column(Text)
    # Structured answer: sections, citations, comparison tables
    answer: Mapped[dict[str, Any] | None] = mapped_column()
    # Fraction of answer claims supported by evidence (0..1), from the claim verifier
    grounding_score: Mapped[float | None] = mapped_column(Float)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)
    cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    # Snapshot of the settings used (model, top_k, reranker on/off, ...) for reproducibility
    config: Mapped[dict[str, Any]] = json_column()
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = created_at_column()
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    query: Mapped[Query] = relationship(back_populates="runs")
    tool_calls: Mapped[list["ToolCall"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ToolCall.step_index",
    )
    retrieval_results: Mapped[list["RetrievalResult"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="RetrievalResult.rank",
    )
    claim_verifications: Mapped[list["ClaimVerification"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ClaimVerification.claim_index",
    )


class ToolCall(Base):
    __tablename__ = "tool_calls"

    id: Mapped[uuid.UUID] = uuid_pk()
    agent_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True
    )
    step_index: Mapped[int] = mapped_column(Integer)
    tool_name: Mapped[str] = mapped_column(String(64), index=True)
    input: Mapped[dict[str, Any]] = json_column()
    output_summary: Mapped[str | None] = mapped_column(Text)
    success: Mapped[bool] = mapped_column(Boolean)
    error_message: Mapped[str | None] = mapped_column(Text)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = created_at_column()

    run: Mapped[AgentRun] = relationship(back_populates="tool_calls")


class RetrievalResult(Base):
    __tablename__ = "retrieval_results"

    id: Mapped[uuid.UUID] = uuid_pk()
    agent_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True
    )
    rank: Mapped[int] = mapped_column(Integer)
    source_type: Mapped[str] = mapped_column(String(32))  # upload | epo | uspto | lens ...
    # SET NULL: if a document is deleted later, the historical record of the run survives
    chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("chunks.id", ondelete="SET NULL"), index=True
    )
    patent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("patents.id", ondelete="SET NULL"), index=True
    )
    method: Mapped[str] = mapped_column(String(16))  # vector | keyword | hybrid | api
    score: Mapped[float | None] = mapped_column(Float)
    rerank_score: Mapped[float | None] = mapped_column(Float)
    # Copy of the text as it was at retrieval time (evaluation must not depend on later edits)
    retrieved_text: Mapped[str] = mapped_column(Text)
    cited_in_answer: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime] = created_at_column()

    run: Mapped[AgentRun] = relationship(back_populates="retrieval_results")


class ClaimVerification(Base):
    """One factual statement from a generated answer, checked against the evidence.

    ("Claim" here means a statement in the AI's answer, not a patent claim.)
    """

    __tablename__ = "claim_verifications"
    __table_args__ = (
        CheckConstraint(
            "verdict IN ('supported', 'partially_supported', 'unsupported')",
            name="valid_verdict",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    agent_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True
    )
    claim_index: Mapped[int] = mapped_column(Integer)
    claim_text: Mapped[str] = mapped_column(Text)
    verdict: Mapped[str] = mapped_column(String(24))
    support_score: Mapped[float | None] = mapped_column(Float)
    # IDs of the retrieval_results that support (or were checked against) this claim
    evidence_ids: Mapped[list[Any]] = mapped_column(default=list, server_default="[]")
    method: Mapped[str] = mapped_column(String(32))  # e.g. nli | llm_judge | lexical
    created_at: Mapped[datetime] = created_at_column()

    run: Mapped[AgentRun] = relationship(back_populates="claim_verifications")


class Evaluation(Base):
    """A single metric value, e.g. ('faithfulness', 0.91) for one run in one experiment."""

    __tablename__ = "evaluations"

    id: Mapped[uuid.UUID] = uuid_pk()
    agent_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True
    )
    experiment: Mapped[str | None] = mapped_column(String(64), index=True)
    metric_name: Mapped[str] = mapped_column(String(64), index=True)
    metric_value: Mapped[float] = mapped_column(Float)
    details: Mapped[dict[str, Any]] = json_column()
    created_at: Mapped[datetime] = created_at_column()
