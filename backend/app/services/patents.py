"""Patent use-cases: search external sources, import a patent as evidence, manage imports.

Search:  query every selected source (each cached), tolerate per-source failures,
         mark results that are already imported.
Import:  fetch full details (claims/description where available), store a `patents`
         row, and index title/abstract/claims/description as chunks with embeddings,
         reusing the same cleaning → sections → chunking pipeline as uploads.
         Imported patents are then searchable by Ask AI exactly like uploaded documents.
"""

import logging
import time
import uuid
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError, NotFoundError, ValidationFailedError
from app.core.ownership import visible
from app.intelligence.dedup import group_by_family
from app.intelligence.similarity import invention_text, rank_by_similarity
from app.models import Chunk, Document, Patent
from app.patents.base import PatentQuery, PatentRecord, PatentSource
from app.patents.cache import (
    ApiCacheStore,
    page_from_json,
    page_to_json,
    record_from_json,
    record_to_json,
)
from app.patents.numbers import parse_publication_number
from app.rag.chunking import chunk_document
from app.rag.cleaning import clean_pages
from app.rag.embeddings import EmbeddingProvider
from app.rag.extraction import Page
from app.rag.sections import CLAIM_START, structure_document

logger = logging.getLogger(__name__)


@dataclass
class SourceOutcome:
    source: str
    total: int = 0
    returned: int = 0
    query_string: str = ""
    cached: bool = False
    latency_ms: int = 0
    error: str | None = None


@dataclass
class ResultItem:
    record: PatentRecord
    imported_id: uuid.UUID | None = None
    similarity: float | None = None  # semantic similarity to the reference invention
    also_published_as: list[str] = field(default_factory=list)  # same family


@dataclass
class SearchOutcome:
    results: list[ResultItem]
    sources: list[SourceOutcome] = field(default_factory=list)
    deduplicated: int = 0  # how many results were merged into another family member
    reference_label: str | None = None  # what results were ranked against


def patent_pages(record: PatentRecord) -> list[Page]:
    """Lay a patent out like a document with headings, so the normal pipeline applies."""
    blocks: list[str] = []
    if record.title:
        blocks += ["TITLE", record.title]
    if record.abstract:
        blocks += ["ABSTRACT", record.abstract]
    if record.claims_text:
        blocks.append("CLAIMS")
        claims = [c.strip() for c in record.claims_text.split("\n\n") if c.strip()]
        for number, claim in enumerate(claims, start=1):
            # Some offices omit claim numbers in full text; add them so claims stay addressable
            blocks.append(claim if CLAIM_START.match(claim) else f"{number}. {claim}")
    if record.description_text:
        blocks.append("DESCRIPTION")
        blocks += [p.strip() for p in record.description_text.split("\n\n") if p.strip()]
    return [Page(number=None, blocks=blocks)]


class PatentService:
    def __init__(
        self,
        session: Session,
        settings: Settings,
        embedder: EmbeddingProvider,
        sources: dict[str, PatentSource],
    ):
        self.session = session
        self.settings = settings
        self.embedder = embedder
        self.sources = sources
        self.cache = ApiCacheStore(session, settings.patent_cache_ttl_hours)

    # ------------------------------------------------------------------ search

    def search(
        self,
        query: PatentQuery,
        source_names: list[str] | None = None,
        *,
        dedup: bool = True,
        reference_document_id: uuid.UUID | None = None,
        reference_patent_id: uuid.UUID | None = None,
    ) -> SearchOutcome:
        """Search sources; optionally merge patent families and rank by similarity to a
        reference invention (an uploaded document or imported patent)."""
        if query.is_empty():
            raise ValidationFailedError("Enter keywords, a CPC code or an applicant to search.")
        names = source_names or list(self.sources)
        unknown = [n for n in names if n not in self.sources]
        if unknown:
            raise ValidationFailedError(f"Patent source not available: {', '.join(unknown)}.")
        if not names:
            raise ValidationFailedError(
                "No patent source is configured. Add EPO credentials to .env (see README)."
            )

        outcome = SearchOutcome(results=[])
        records: list[PatentRecord] = []
        for name in names:
            started = time.perf_counter()
            status = SourceOutcome(source=name)
            params = {
                "keywords": query.keywords.strip().lower(),
                "cpc": sorted(query.cpc),
                "applicant": query.applicant,
                "date_from": query.date_from,
                "date_to": query.date_to,
                "limit": query.limit,
            }
            try:
                cached = self.cache.get(f"{name}.search", params)
                if cached is not None:
                    page = page_from_json(cached)
                    status.cached = True
                else:
                    page = self.sources[name].search(query)
                    self.cache.set(f"{name}.search", params, page_to_json(page))
                status.total, status.returned = page.total, len(page.results)
                status.query_string = page.query_string
                records.extend(page.results)
            except (AppError, ValueError) as exc:
                # One failing source must not break the others
                status.error = exc.message if isinstance(exc, AppError) else str(exc)
                logger.warning("Patent search failed for %s: %s", name, status.error)
            status.latency_ms = round((time.perf_counter() - started) * 1000)
            outcome.sources.append(status)

        items = [ResultItem(r) for r in records]
        if dedup:
            groups = group_by_family(records)
            items = [
                ResultItem(g.representative, also_published_as=g.also_published_as) for g in groups
            ]
            outcome.deduplicated = len(records) - len(groups)
        if reference_document_id or reference_patent_id:
            if reference_document_id:
                reference = self.session.get(Document, reference_document_id)
                if reference is None or not visible(reference.owner_id):
                    raise ValidationFailedError("The reference document is not available.")
            label, text = invention_text(
                self.session, document_id=reference_document_id, patent_id=reference_patent_id
            )
            outcome.reference_label = label
            by_number = {i.record.publication_number: i for i in items}
            ranked = rank_by_similarity(self.embedder, text, [i.record for i in items])
            items = []
            for scored in ranked:
                item = by_number[scored.record.publication_number]
                item.similarity = round(scored.similarity, 4)
                items.append(item)

        imported = self._imported_ids([i.record for i in items])
        for item in items:
            item.imported_id = imported.get((item.record.source, item.record.publication_number))
        outcome.results = items
        return outcome

    def _imported_ids(self, records: list[PatentRecord]) -> dict[tuple[str, str], uuid.UUID]:
        if not records:
            return {}
        numbers = {r.publication_number for r in records}
        rows = self.session.execute(
            select(Patent.source, Patent.publication_number, Patent.id).where(
                Patent.publication_number.in_(numbers)
            )
        )
        return {(source, number): pid for source, number, pid in rows}

    # ------------------------------------------------------------------ import

    def import_patent(self, source_name: str, publication_number: str) -> tuple[Patent, bool]:
        if source_name not in self.sources:
            raise ValidationFailedError(f"Patent source not available: {source_name}.")
        try:
            number = parse_publication_number(publication_number).normalized
        except ValueError as exc:
            raise ValidationFailedError(str(exc)) from exc

        existing = self.session.scalar(
            select(Patent).where(Patent.source == source_name, Patent.publication_number == number)
        )
        if existing is not None and existing.meta.get("embedding_model") == self.embedder.name:
            return existing, False
        if existing is not None:  # indexed with another embedding model: rebuild
            self.session.delete(existing)
            self.session.flush()

        params = {"number": number}
        cached = self.cache.get(f"{source_name}.details", params)
        if cached is not None:
            record = record_from_json(cached)
        else:
            record = self.sources[source_name].get_details(number)
            self.cache.set(f"{source_name}.details", params, record_to_json(record))

        patent = Patent(
            source=record.source,
            publication_number=record.publication_number,
            country=record.country,
            kind_code=record.kind_code,
            family_id=record.family_id,
            title=record.title,
            abstract=record.abstract,
            claims_text=record.claims_text,
            description_text=record.description_text,
            applicants=record.applicants,
            inventors=record.inventors,
            cpc_codes=record.cpc_codes,
            filing_date=record.filing_date,
            publication_date=record.publication_date,
            priority_date=record.priority_date,
            url=record.url,
            raw=record.raw or None,
        )
        self.session.add(patent)
        self.session.flush()

        structured = structure_document(clean_pages(patent_pages(record)))
        drafts = chunk_document(
            structured,
            strategy=self.settings.chunking_strategy,
            max_tokens=self.settings.chunk_max_tokens,
            overlap_tokens=self.settings.chunk_overlap_tokens,
        )
        vectors: list[list[float]] = []
        batch = self.settings.embedding_batch_size
        for i in range(0, len(drafts), batch):
            vectors.extend(self.embedder.embed_documents([d.text for d in drafts[i : i + batch]]))
        for draft, vector in zip(drafts, vectors, strict=True):
            self.session.add(
                Chunk(
                    patent_id=patent.id,
                    chunk_index=draft.index,
                    text=draft.text,
                    section=draft.section,
                    char_start=draft.char_start,
                    char_end=draft.char_end,
                    token_count=draft.token_count,
                    embedding=vector,
                    embedding_model=self.embedder.name,
                    meta=draft.meta,
                )
            )
        patent.meta = {
            "chunk_count": len(drafts),
            "has_claims": bool(record.claims_text),
            "has_description": bool(record.description_text),
            "sections_found": structured.sections_found,
            "embedding_model": self.embedder.name,
        }
        self.session.commit()
        logger.info("Imported %s from %s: %d chunks", number, source_name, len(drafts))
        return patent, True

    # ------------------------------------------------------------------ manage

    def list_imported(self) -> list[Patent]:
        return list(self.session.scalars(select(Patent).order_by(Patent.fetched_at.desc())))

    def get(self, patent_id: uuid.UUID) -> Patent:
        patent = self.session.get(Patent, patent_id)
        if patent is None:
            raise NotFoundError("Patent not found.")
        return patent

    def delete(self, patent_id: uuid.UUID) -> None:
        self.session.delete(self.get(patent_id))
        self.session.commit()

    def chunk_count(self, patent_id: uuid.UUID) -> int:
        return self.session.scalar(
            select(func.count()).select_from(Chunk).where(Chunk.patent_id == patent_id)
        )
