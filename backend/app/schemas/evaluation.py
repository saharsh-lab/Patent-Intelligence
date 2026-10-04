"""API shapes for experiment results (the Evaluation page)."""

from typing import Any

from pydantic import BaseModel


class EvaluationListItem(BaseModel):
    experiment: str
    run: str
    kind: str  # experiment | verifier
    description: str
    finished_at: str | None
    dataset: str | None
    synthetic: bool
    draft_labels: bool = False  # labels not yet verified by the team
    n: int | None  # questions (experiment) or labelled statements (verifier)
    variants: list[str]  # variant names, or verifier methods


class EvaluationResult(BaseModel):
    # summary.json as written by app.evaluation.report / verifier_eval (see those modules)
    summary: dict[str, Any]
    rows: list[dict[str, Any]]
