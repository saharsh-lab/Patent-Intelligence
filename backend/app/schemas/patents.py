"""API shapes for patent search and imported patents."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator

from app.models import Patent
from app.services.patents import ResultItem


class PatentSearchRequest(BaseModel):
    keywords: str = Field(default="", max_length=500)
    cpc: list[str] = Field(default_factory=list, max_length=10)
    applicant: str | None = Field(default=None, max_length=200)
    date_from: date | None = None
    date_to: date | None = None
    limit: int = Field(default=25, ge=1, le=100)
    sources: list[str] | None = Field(default=None, description="Default: all configured")
    dedup: bool = Field(default=True, description="Merge members of the same patent family")
    rank_against_document_id: uuid.UUID | None = Field(
        default=None, description="Rank results by semantic similarity to this document"
    )
    rank_against_patent_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def _check(self):
        if not (self.keywords.strip() or self.cpc or (self.applicant or "").strip()):
            raise ValueError("Enter keywords, a CPC code or an applicant.")
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from must be before date_to.")
        return self


class PatentResultOut(BaseModel):
    source: str
    publication_number: str
    title: str | None
    abstract: str | None
    applicants: list[str]
    inventors: list[str]
    cpc_codes: list[str]
    publication_date: date | None
    filing_date: date | None
    family_id: str | None
    url: str | None
    imported_id: uuid.UUID | None
    similarity: float | None = Field(
        default=None, description="Cosine similarity to the reference invention (not legal)"
    )
    also_published_as: list[str] = Field(default_factory=list)

    @classmethod
    def from_item(cls, item: "ResultItem"):
        record = item.record
        return cls(
            source=record.source,
            publication_number=record.publication_number,
            title=record.title,
            abstract=record.abstract,
            applicants=record.applicants,
            inventors=record.inventors,
            cpc_codes=record.cpc_codes,
            publication_date=record.publication_date,
            filing_date=record.filing_date,
            family_id=record.family_id,
            url=record.url,
            imported_id=item.imported_id,
            similarity=item.similarity,
            also_published_as=item.also_published_as,
        )


class SourceOutcomeOut(BaseModel):
    source: str
    total: int
    returned: int
    query_string: str
    cached: bool
    latency_ms: int
    error: str | None


class PatentSearchResponse(BaseModel):
    results: list[PatentResultOut]
    sources: list[SourceOutcomeOut]
    deduplicated: int = 0
    reference_label: str | None = None


class PatentImportRequest(BaseModel):
    source: str = Field(min_length=1, max_length=32)
    publication_number: str = Field(min_length=3, max_length=64)


class PatentOut(BaseModel):
    id: uuid.UUID
    source: str
    publication_number: str
    title: str | None
    abstract: str | None
    applicants: list[str]
    inventors: list[str]
    cpc_codes: list[str]
    publication_date: date | None
    filing_date: date | None
    priority_date: date | None
    family_id: str | None
    url: str | None
    has_claims: bool
    has_description: bool
    chunk_count: int
    sections_found: list[str]
    fetched_at: datetime

    @classmethod
    def from_model(cls, patent: Patent) -> "PatentOut":
        meta = patent.meta or {}
        return cls(
            id=patent.id,
            source=patent.source,
            publication_number=patent.publication_number,
            title=patent.title,
            abstract=patent.abstract,
            applicants=patent.applicants or [],
            inventors=patent.inventors or [],
            cpc_codes=patent.cpc_codes or [],
            publication_date=patent.publication_date,
            filing_date=patent.filing_date,
            priority_date=patent.priority_date,
            family_id=patent.family_id,
            url=patent.url,
            has_claims=meta.get("has_claims", bool(patent.claims_text)),
            has_description=meta.get("has_description", bool(patent.description_text)),
            chunk_count=meta.get("chunk_count", 0),
            sections_found=meta.get("sections_found", []),
            fetched_at=patent.fetched_at,
        )


class PatentImportResponse(BaseModel):
    patent: PatentOut
    already_imported: bool


class SourceStatusOut(BaseModel):
    name: str
    label: str
    status: str
    note: str
