"""Check all active patent watches once (for cron / launchd).

    cd backend && .venv/bin/python -m scripts.check_watches

Example crontab line (every day at 07:00):
    0 7 * * * cd /path/to/RAG/backend && .venv/bin/python -m scripts.check_watches
"""

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.database.session import get_sessionmaker
from app.patents.registry import get_patent_sources_for
from app.rag.embeddings import get_embedder
from app.services.watches import WatchService


def main() -> int:
    settings = get_settings()
    configure_logging(settings.log_level)
    with get_sessionmaker()() as session:
        service = WatchService(session, settings, get_embedder(), get_patent_sources_for(settings))
        outcomes = service.check_all()
    for o in outcomes:
        status = f"error: {o.error}" if o.error else f"{o.new_hits} new, imported {o.imported}"
        print(f"watch {o.watch_id}: {status}")
    return 1 if any(o.error for o in outcomes) else 0


if __name__ == "__main__":
    raise SystemExit(main())
