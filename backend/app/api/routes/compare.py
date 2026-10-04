"""Structured patent comparison."""

import uuid
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field, model_validator

from app.api.deps import ComparisonServiceDep
from app.schemas.answers import AskResponse

router = APIRouter(tags=["compare"])


class SourceRefIn(BaseModel):
    document_id: uuid.UUID | None = None
    patent_id: uuid.UUID | None = None
    publication_number: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def _exactly_one(self):
        if (
            sum(v is not None for v in (self.document_id, self.patent_id, self.publication_number))
            != 1
        ):
            raise ValueError("Give exactly one of document_id, patent_id or publication_number.")
        return self


class CompareRequest(BaseModel):
    sources: list[SourceRefIn] = Field(min_length=2, max_length=4)
    question: str | None = Field(default=None, max_length=1000)
    mode: Literal["auto", "llm", "extractive"] = "auto"


@router.post("/compare", response_model=AskResponse)
def compare(body: CompareRequest, service: ComparisonServiceDep) -> AskResponse:
    """Compare 2–4 sources aspect by aspect. The response's `comparison` holds the table;
    every cell cites evidence from its own source."""
    run = service.compare(
        [ref.model_dump() for ref in body.sources], question=body.question, mode=body.mode
    )
    return AskResponse.from_run(run)
