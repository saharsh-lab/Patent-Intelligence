"""API shapes for invention analysis."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator


class InventionRequest(BaseModel):
    description: str | None = Field(
        default=None, max_length=8000, description="The invention in your own words"
    )
    document_id: uuid.UUID | None = Field(
        default=None, description="Or: an uploaded draft (its abstract and claim 1 are used)"
    )
    use_patent_search: bool = Field(
        default=True, description="Also search configured patent databases (EPO)"
    )
    max_candidates: int = Field(default=5, ge=1, le=8)

    @model_validator(mode="after")
    def _one_input(self):
        if not (self.description or "").strip() and self.document_id is None:
            raise ValueError("Describe the invention or select a document.")
        return self


class InventionAnalysisOut(BaseModel):
    run_id: uuid.UUID
    status: str
    created_at: datetime
    latency_ms: int | None
    # features, candidates, cells, not_found_features, steps, disclaimer (see
    # app.invention.analysis.InventionAnalyzer._summarise)
    result: dict[str, Any] | None


class InventionListItem(BaseModel):
    run_id: uuid.UUID
    status: str
    created_at: datetime
    description: str
    features: int
    top_candidate: str | None
