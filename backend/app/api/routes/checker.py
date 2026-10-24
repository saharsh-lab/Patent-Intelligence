"""The Checker: check any text against your sources, fix flagged sentences, and the
record of what the checker found in every answer."""

import uuid

from fastapi import APIRouter, Query
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import FactCheckerDep, SentenceFixerDep, SessionDep
from app.core.errors import ValidationFailedError
from app.core.ownership import restrict
from app.models import AgentRun
from app.models import Query as QueryModel
from app.schemas.answers import AskResponse
from app.schemas.checker import CheckHistoryItem, CheckRequest, FixRequest, VerdictCounts

router = APIRouter(tags=["checker"])


@router.post("/check", response_model=AskResponse)
def check_text(body: CheckRequest, checker: FactCheckerDep) -> AskResponse:
    """Check every sentence of a text (an AI answer, a draft) against the passages most
    like it in your documents and patents. Returns the same shape as an answer, with
    the sentence verdicts under `verification`."""
    run = checker.check(body.text, document_ids=body.document_ids, patent_ids=body.patent_ids)
    return AskResponse.from_run(run)


@router.post("/runs/{run_id}/fix", response_model=AskResponse)
def fix_sentence(run_id: uuid.UUID, body: FixRequest, fixer: SentenceFixerDep) -> AskResponse:
    """Remove a sentence, rewrite it from its source (checked again; refused if the
    sources do not back it), or restore the original answer."""
    if body.action != "restore" and body.claim_index is None:
        raise ValidationFailedError("Say which sentence to fix (claim_index).")
    return AskResponse.from_run(fixer.fix(run_id, body.claim_index, body.action))


@router.get("/checker/history", response_model=list[CheckHistoryItem])
def checker_history(
    session: SessionDep, limit: int = Query(default=50, ge=1, le=200)
) -> list[CheckHistoryItem]:
    """Your checked answers and text checks, newest first, with what the checker found."""
    stmt = (
        select(AgentRun)
        .join(AgentRun.query)
        .options(selectinload(AgentRun.query))
        .where(AgentRun.status == "succeeded")
        .order_by(AgentRun.started_at.desc())
        .limit(limit * 3)  # some answers were never checked (small talk, the clock)
    )
    items = []
    for run in session.scalars(restrict(stmt, QueryModel.owner_id)):
        item = history_item(run)
        if item is not None:
            items.append(item)
        if len(items) == limit:
            break
    return items


def history_item(run: AgentRun) -> CheckHistoryItem | None:
    answer = run.answer or {}
    verification = answer.get("verification")
    claims = [c for c in (verification or {}).get("claims", []) if c.get("location") == "answer"]
    if not claims:
        return None
    attempts = answer.get("verification_attempts") or []
    first = attempts[0].get("claims") or [] if attempts else []
    original = answer.get("original")
    planted = answer.get("demo_injection")
    return CheckHistoryItem(
        run_id=run.id,
        kind="check" if run.pipeline == "fact_check" else "answer",
        title=" ".join(run.query.query_text.split())[:160],
        conversation_id=run.query.conversation_id,
        created_at=run.started_at,
        grounding_score=run.grounding_score,
        original_grounding_score=original["grounding_score"] if original else None,
        counts=_counts(claims),
        rewritten=len(attempts) > 1,
        draft_flagged=sum(c["verdict"] != "supported" for c in first) if len(attempts) > 1 else 0,
        planted_caught=planted.get("caught") if planted else None,
        fixes=len(answer.get("fixes", [])),
        premise_terms=(answer.get("premise") or {}).get("acknowledged", []),
    )


def _counts(claims: list[dict]) -> VerdictCounts:
    counts = VerdictCounts()
    for claim in claims:
        if claim["verdict"] == "supported" and not claim.get("misattributed"):
            counts.supported += 1
        elif claim["verdict"] != "unsupported":
            counts.partly += 1
        elif claim.get("contradicts"):
            counts.contradicts += 1
        else:
            counts.not_found += 1
    return counts
