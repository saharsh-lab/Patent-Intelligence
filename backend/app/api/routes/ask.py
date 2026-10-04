"""Question answering endpoints and run history."""

import uuid

from fastapi import APIRouter, Query
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import AgentServiceDep, AnswerServiceDep, SessionDep, SettingsDep
from app.core.errors import NotFoundError
from app.core.ownership import restrict, visible
from app.models import AgentRun
from app.models import Query as QueryModel
from app.schemas.answers import AskRequest, AskResponse, RunListItem

router = APIRouter(tags=["ask"])


@router.post("/ask", response_model=AskResponse)
def ask(
    body: AskRequest,
    baseline: AnswerServiceDep,
    agent: AgentServiceDep,
    settings: SettingsDep,
) -> AskResponse:
    """Answer a question with cited evidence.

    pipeline="agentic" (default): the LangGraph agent picks tools and sources.
    pipeline="baseline": fixed retrieve-then-generate over the local index.
    Returns 200 for both answered and 'insufficient_evidence' outcomes; check `status`.
    """
    service = agent if (body.pipeline or settings.default_pipeline) == "agentic" else baseline
    run = service.ask(
        body.question,
        document_ids=body.document_ids,
        patent_ids=body.patent_ids,
        conversation_id=body.conversation_id,
        top_k=body.top_k,
        retrieval_mode=body.retrieval_mode,
        rerank=body.rerank,
    )
    return AskResponse.from_run(run)


@router.get("/runs", response_model=list[RunListItem])
def list_runs(
    session: SessionDep,
    limit: int = Query(default=20, ge=1, le=100),
    conversation_id: uuid.UUID | None = None,
) -> list[RunListItem]:
    stmt = (
        select(AgentRun)
        .options(selectinload(AgentRun.query))
        .order_by(AgentRun.started_at.desc())
        .limit(limit)
    )
    stmt = restrict(stmt.join(AgentRun.query, isouter=False), QueryModel.owner_id)
    if conversation_id:
        stmt = stmt.where(QueryModel.conversation_id == conversation_id)
    return [
        RunListItem(
            run_id=run.id,
            question=run.query.query_text,
            status=run.status,
            pipeline=run.pipeline,
            latency_ms=run.latency_ms,
            created_at=run.started_at,
        )
        for run in session.scalars(stmt)
    ]


@router.get("/runs/{run_id}", response_model=AskResponse)
def get_run(run_id: uuid.UUID, session: SessionDep) -> AskResponse:
    run = session.get(AgentRun, run_id)
    if run is None or not visible(run.query.owner_id):
        raise NotFoundError("Run not found.")
    return AskResponse.from_run(run)
