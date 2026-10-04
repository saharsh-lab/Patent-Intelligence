"""Invention analysis: describe an invention, get a cited feature-by-feature comparison
with the closest documents found (technical comparison only, not legal advice)."""

import uuid

from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import InventionAnalyzerDep, SessionDep
from app.core.errors import NotFoundError
from app.core.ownership import restrict, visible
from app.invention.analysis import PIPELINE
from app.invention.report import to_markdown
from app.models import AgentRun
from app.models import Query as QueryModel
from app.schemas.invention import InventionAnalysisOut, InventionListItem, InventionRequest

router = APIRouter(prefix="/analysis/invention", tags=["invention analysis"])


def _out(run: AgentRun) -> InventionAnalysisOut:
    return InventionAnalysisOut(
        run_id=run.id,
        status=run.status,
        created_at=run.started_at,
        latency_ms=run.latency_ms,
        result=run.answer,
    )


def _get(session, run_id: uuid.UUID) -> AgentRun:
    run = session.get(AgentRun, run_id)
    if run is None or run.pipeline != PIPELINE or not visible(run.query.owner_id):
        raise NotFoundError("Analysis not found.")
    return run


@router.post("", response_model=InventionAnalysisOut)
def analyze_invention(body: InventionRequest, analyzer: InventionAnalyzerDep):
    """Takes ~1–3 minutes with local models: features, search, then one check per
    feature × document."""
    run = analyzer.analyze(
        body.description,
        document_id=body.document_id,
        use_patent_search=body.use_patent_search,
        max_candidates=body.max_candidates,
    )
    return _out(run)


@router.get("", response_model=list[InventionListItem])
def list_analyses(session: SessionDep, limit: int = Query(default=20, ge=1, le=100)):
    runs = session.scalars(
        restrict(select(AgentRun), QueryModel.owner_id)
        .options(selectinload(AgentRun.query))
        .join(AgentRun.query)
        .where(AgentRun.pipeline == PIPELINE)
        .order_by(AgentRun.started_at.desc())
        .limit(limit)
    )
    items = []
    for run in runs:
        result = run.answer or {}
        candidates = result.get("candidates") or []
        items.append(
            InventionListItem(
                run_id=run.id,
                status=run.status,
                created_at=run.started_at,
                description=run.query.query_text[:200],
                features=len(result.get("features") or []),
                top_candidate=candidates[0]["label"] if candidates else None,
            )
        )
    return items


@router.get("/{run_id}", response_model=InventionAnalysisOut)
def get_analysis(run_id: uuid.UUID, session: SessionDep):
    return _out(_get(session, run_id))


@router.get("/{run_id}/report.md", response_class=PlainTextResponse)
def download_report(run_id: uuid.UUID, session: SessionDep):
    run = _get(session, run_id)
    if run.status != "succeeded" or not run.answer:
        raise NotFoundError("This analysis has no report (it did not complete).")
    text = to_markdown(run.answer, created_at=run.started_at.strftime("%Y-%m-%d %H:%M UTC"))
    return PlainTextResponse(
        text,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="invention-analysis-{run_id}.md"'},
    )
