"""Periodic watch checks inside the API process (WATCH_CHECK_INTERVAL_HOURS > 0).

A daemon thread wakes up every interval and checks all active watches with its own
database session. For servers that restart often, a cron job running
`python -m scripts.check_watches` does the same without the API.
"""

import logging
import threading

from app.core.config import Settings
from app.database.session import get_sessionmaker
from app.patents.registry import get_patent_sources_for
from app.rag.embeddings import get_embedder
from app.services.watches import WatchService

logger = logging.getLogger(__name__)


class WatchScheduler:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.interval = settings.watch_check_interval_hours * 3600
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, name="watch-scheduler", daemon=True)

    def start(self) -> None:
        logger.info("Watch checks every %s h", self.settings.watch_check_interval_hours)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def run_once(self) -> None:
        with get_sessionmaker()() as session:
            service = WatchService(
                session, self.settings, get_embedder(), get_patent_sources_for(self.settings)
            )
            for outcome in service.check_all():
                if outcome.error:
                    logger.warning("Watch %s check failed: %s", outcome.watch_id, outcome.error)

    def _loop(self) -> None:
        while not self._stop.wait(self.interval):
            try:
                self.run_once()
            except Exception:  # noqa: BLE001 - keep the scheduler alive
                logger.exception("Scheduled watch check failed")
