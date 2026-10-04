"""Health endpoints.

- /health/live  : is the API process running? (no dependencies checked)
- /health/ready : can the API do useful work? (database + pgvector reachable)
"""

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.database.session import check_database

router = APIRouter(prefix="/health", tags=["health"])
logger = logging.getLogger(__name__)


@router.get("/live")
def live() -> dict:
    return {"status": "ok"}


@router.get("/ready")
def ready() -> JSONResponse:
    settings = get_settings()
    checks: dict = {
        "llm_provider": settings.llm_provider,
        "embedding_provider": settings.embedding_provider,
        "patent_sources": settings.enabled_patent_sources,
    }
    try:
        checks["database"] = {"status": "ok", **check_database()}
        if checks["database"]["pgvector"] is None:
            checks["database"]["status"] = "error"
            checks["database"]["detail"] = "pgvector extension is not installed"
    except Exception as exc:  # noqa: BLE001 - report any DB failure as 'not ready'
        logger.warning("Database health check failed: %s", type(exc).__name__)
        checks["database"] = {"status": "error", "detail": "database unreachable"}

    is_ready = checks["database"]["status"] == "ok"
    return JSONResponse(
        status_code=200 if is_ready else 503,
        content={"status": "ready" if is_ready else "not_ready", "checks": checks},
    )
