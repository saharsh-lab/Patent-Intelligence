"""API shapes for patent monitoring (watches)."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator

from app.models.watch import PatentWatch, WatchHit


class WatchCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    keywords: str = Field(default="", max_length=500)
    cpc: list[str] = Field(default_factory=list, max_length=10)
    reference_document_id: uuid.UUID | None = Field(
        default=None, description="Rank new publications by similarity to this document"
    )
    import_top: int = Field(default=3, ge=0, le=10)
    lookback_days: int = Field(
        default=30, ge=1, le=3650, description="First check looks back this far (days)"
    )

    @model_validator(mode="after")
    def _criteria(self):
        if not (self.keywords.strip() or self.cpc):
            raise ValueError("Enter keywords or a CPC class.")
        return self


class WatchOut(BaseModel):
    id: uuid.UUID
    name: str
    keywords: str
    cpc: list[str]
    reference_document_id: uuid.UUID | None
    import_top: int
    active: bool
    since: date
    last_checked_at: datetime | None
    last_error: str | None
    created_at: datetime
    hits: int
    unseen: int

    @classmethod
    def from_model(cls, watch: PatentWatch, unseen: int) -> "WatchOut":
        return cls(
            id=watch.id,
            name=watch.name,
            keywords=watch.keywords,
            cpc=list(watch.cpc or []),
            reference_document_id=watch.reference_document_id,
            import_top=watch.import_top,
            active=watch.active,
            since=watch.since,
            last_checked_at=watch.last_checked_at,
            last_error=watch.last_error,
            created_at=watch.created_at,
            hits=len(watch.hits),
            unseen=unseen,
        )


class WatchHitOut(BaseModel):
    id: uuid.UUID
    source: str
    publication_number: str
    title: str | None
    abstract: str | None
    applicants: list[str]
    publication_date: date | None
    url: str | None
    similarity: float | None
    imported_patent_id: uuid.UUID | None
    seen: bool
    found_at: datetime

    @classmethod
    def from_model(cls, hit: WatchHit) -> "WatchHitOut":
        return cls.model_validate(hit, from_attributes=True)


class WatchCheckOut(BaseModel):
    watch_id: uuid.UUID
    new_hits: int
    imported: list[str]
    error: str | None
