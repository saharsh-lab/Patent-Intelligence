"""Patent monitoring: run saved searches and record publications not seen before.

    check(watch):
        search the patent databases for publications since `watch.since`
        → drop the ones this watch already found (unique per watch + number)
        → rank the new ones by similarity to the watch's reference document
        → store them as hits; import the top N so they can be analysed and compared
        → move `since` forward (with a few days' overlap: databases index late)

Checks run on demand (API / UI), from the command line (`python -m scripts.check_watches`,
for cron), or periodically inside the API when WATCH_CHECK_INTERVAL_HOURS > 0.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError, NotFoundError, ValidationFailedError
from app.core.ownership import current_owner, restrict, visible
from app.models import Document
from app.models.watch import PatentWatch, WatchHit
from app.patents.base import PatentQuery, PatentSource
from app.rag.embeddings import EmbeddingProvider
from app.services.patents import PatentService

logger = logging.getLogger(__name__)

OVERLAP_DAYS = 7  # re-ask for the last week: databases add publications with some delay
SEARCH_LIMIT = 50


@dataclass
class CheckOutcome:
    watch_id: uuid.UUID
    new_hits: int = 0
    imported: list[str] = field(default_factory=list)
    error: str | None = None


class WatchService:
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

    # ------------------------------------------------------------------ CRUD

    def create(
        self,
        *,
        name: str,
        keywords: str = "",
        cpc: list[str] | None = None,
        reference_document_id: uuid.UUID | None = None,
        import_top: int = 3,
        lookback_days: int = 30,
    ) -> PatentWatch:
        if not (keywords.strip() or cpc):
            raise ValidationFailedError("A watch needs keywords or a CPC class.")
        reference = (
            self.session.get(Document, reference_document_id) if reference_document_id else None
        )
        if reference_document_id and (reference is None or not visible(reference.owner_id)):
            raise NotFoundError("Reference document not found.")
        watch = PatentWatch(
            owner_id=current_owner(),
            name=name.strip(),
            keywords=keywords.strip(),
            cpc=[c.strip().upper() for c in cpc or [] if c.strip()],
            reference_document_id=reference_document_id,
            import_top=import_top,
            since=date.today() - timedelta(days=lookback_days),
        )
        self.session.add(watch)
        self.session.commit()
        return watch

    def list_watches(self) -> list[PatentWatch]:
        stmt = restrict(select(PatentWatch), PatentWatch.owner_id).order_by(PatentWatch.created_at)
        return list(self.session.scalars(stmt))

    def get(self, watch_id: uuid.UUID) -> PatentWatch:
        watch = self.session.get(PatentWatch, watch_id)
        if watch is None or not visible(watch.owner_id):
            raise NotFoundError("Watch not found.")
        return watch

    def set_active(self, watch_id: uuid.UUID, active: bool) -> PatentWatch:
        watch = self.get(watch_id)
        watch.active = active
        self.session.commit()
        return watch

    def delete(self, watch_id: uuid.UUID) -> None:
        self.session.delete(self.get(watch_id))
        self.session.commit()

    def unseen_count(self, watch_id: uuid.UUID) -> int:
        return len(
            self.session.scalars(
                select(WatchHit.id).where(WatchHit.watch_id == watch_id, WatchHit.seen.is_(False))
            ).all()
        )

    def mark_seen(self, watch_id: uuid.UUID) -> None:
        self.session.execute(
            update(WatchHit).where(WatchHit.watch_id == watch_id).values(seen=True)
        )
        self.session.commit()

    # ------------------------------------------------------------------ checking

    def check(self, watch_id: uuid.UUID) -> CheckOutcome:
        watch = self.get(watch_id)
        outcome = CheckOutcome(watch.id)
        today = date.today()
        patents = PatentService(self.session, self.settings, self.embedder, self.sources)
        try:
            result = patents.search(
                PatentQuery(
                    keywords=watch.keywords,
                    cpc=list(watch.cpc or []),
                    date_from=watch.since,
                    date_to=today,
                    limit=SEARCH_LIMIT,
                ),
                reference_document_id=watch.reference_document_id,
            )
            errors = [s.error for s in result.sources if s.error]
            if errors and len(errors) == len(result.sources):
                raise AppError("; ".join(errors), code="search_failed")
        except Exception as exc:  # noqa: BLE001 - a check must record failures, not crash
            message = exc.message if isinstance(exc, AppError) else f"{type(exc).__name__}: {exc}"
            if not isinstance(exc, AppError):
                logger.warning("Watch %s search failed: %s", watch_id, message)
            self.session.rollback()
            watch = self.get(watch_id)
            watch.last_error = message[:500]
            watch.last_checked_at = datetime.now(UTC)
            self.session.commit()
            outcome.error = message[:500]
            return outcome

        known = set(
            self.session.scalars(
                select(WatchHit.publication_number).where(WatchHit.watch_id == watch.id)
            )
        )
        new = [item for item in result.results if item.record.publication_number not in known]
        # Most similar to the reference first; without a reference, newest first
        new.sort(
            key=lambda i: (
                -(i.similarity if i.similarity is not None else -1),
                -(i.record.publication_date or date.min).toordinal(),
            )
        )
        hits = []
        for item in new:
            record = item.record
            hit = WatchHit(
                source=record.source,
                publication_number=record.publication_number,
                title=record.title,
                abstract=(record.abstract or "")[:4000] or None,
                applicants=list(record.applicants or []),
                publication_date=record.publication_date,
                url=record.url,
                similarity=item.similarity,
                imported_patent_id=item.imported_id,
            )
            watch.hits.append(hit)
            hits.append(hit)
        outcome.new_hits = len(hits)
        watch.since = max(watch.since, today - timedelta(days=OVERLAP_DAYS))
        watch.last_checked_at = datetime.now(UTC)
        watch.last_error = None
        self.session.commit()

        for hit in hits[: watch.import_top]:
            if hit.imported_patent_id:
                continue
            try:
                patent, _ = patents.import_patent(hit.source, hit.publication_number)
            except AppError as exc:  # one failed import must not lose the hits
                self.session.rollback()
                logger.info("Watch import of %s failed: %s", hit.publication_number, exc)
                continue
            hit = self.session.get(WatchHit, hit.id)
            hit.imported_patent_id = patent.id
            outcome.imported.append(patent.publication_number)
            self.session.commit()
        logger.info(
            "Watch %s: %d new publications, %d imported",
            watch.id,
            outcome.new_hits,
            len(outcome.imported),
        )
        return outcome

    def check_all(self) -> list[CheckOutcome]:
        ids = list(self.session.scalars(select(PatentWatch.id).where(PatentWatch.active.is_(True))))
        return [self.check(watch_id) for watch_id in ids]
