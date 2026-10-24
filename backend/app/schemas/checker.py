"""API shapes for the Checker page: check any text, fix a sentence, the checker's record."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class CheckRequest(BaseModel):
    text: str = Field(min_length=10, max_length=8000, description="The text to check")
    document_ids: list[uuid.UUID] | None = Field(
        default=None, max_length=50, description="Check against these documents (default: all)"
    )
    patent_ids: list[uuid.UUID] | None = Field(
        default=None, max_length=50, description="Check against these imported patents"
    )


class FixRequest(BaseModel):
    action: Literal["remove", "rewrite", "restore"]
    claim_index: int | None = Field(
        default=None, ge=0, description="The sentence (verification claim index); not for restore"
    )


class VerdictCounts(BaseModel):
    supported: int = 0
    partly: int = 0
    contradicts: int = 0
    not_found: int = 0


class CheckHistoryItem(BaseModel):
    run_id: uuid.UUID
    kind: Literal["check", "answer"]
    title: str
    conversation_id: uuid.UUID | None
    created_at: datetime
    grounding_score: float | None
    original_grounding_score: float | None = Field(
        default=None, description="Before the user's fixes, when there were any"
    )
    counts: VerdictCounts
    rewritten: bool = Field(description="The checker sent the first draft back to be rewritten")
    draft_flagged: int = Field(description="Sentences flagged in the first draft")
    planted_caught: bool | None = Field(
        default=None, description="Checker test: was the planted sentence caught?"
    )
    fixes: int
    premise_terms: list[str] = Field(
        default_factory=list, description="The answer said the sources do not mention these"
    )
