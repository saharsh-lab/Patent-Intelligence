"""FastAPI application entry point.

Run locally (from the `backend/` folder):
    uvicorn app.main:app --reload
Interactive API docs are then at http://localhost:8000/docs
"""

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    ask,
    compare,
    conversations,
    documents,
    evaluation,
    health,
    invention,
    patents,
    search,
    system,
    watches,
)
from app.auth.deps import require_user
from app.auth.middleware import OwnerScopeMiddleware
from app.auth.routes import router as auth_router
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestIdMiddleware
from app.core.security import (
    BodySizeLimitMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    check_production_settings,
)

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    for warning in check_production_settings(settings):  # raises on unsafe settings
        logger.warning("Production check: %s", warning)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        scheduler = None
        if settings.watch_check_interval_hours > 0:
            from app.services.watch_scheduler import WatchScheduler

            scheduler = WatchScheduler(settings)
            scheduler.start()
        yield
        if scheduler:
            scheduler.stop()

    app = FastAPI(
        lifespan=lifespan,
        title=settings.app_name,
        description=(
            "Agentic RAG for multi-source patent intelligence. "
            "Research assistance only: not legal advice."
        ),
        version="0.1.0",
        # Hide interactive docs in production
        docs_url=None if settings.app_env == "production" else "/docs",
        redoc_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )
    # Added last = runs first: size and rate limits reject requests before any work,
    # inside the request-ID middleware so their error bodies carry the request ID.
    if settings.rate_limit_enabled:
        app.add_middleware(RateLimitMiddleware, settings=settings)
    app.add_middleware(
        BodySizeLimitMiddleware,
        upload_bytes=settings.max_upload_bytes,
        other_bytes=settings.max_json_body_kb * 1024,
    )
    app.add_middleware(SecurityHeadersMiddleware, production=settings.app_env == "production")
    app.add_middleware(OwnerScopeMiddleware)  # whose data this request may see
    app.add_middleware(RequestIdMiddleware)
    register_exception_handlers(app)

    # Open: health checks and the login/registration endpoints. Everything else needs a
    # logged-in user (unless AUTH_REQUIRED=false, e.g. in tests).
    app.include_router(health.router)
    app.include_router(auth_router)
    protected = [Depends(require_user)]
    for module in (
        documents,
        search,
        ask,
        conversations,
        system,
        patents,
        compare,
        evaluation,
        invention,
        watches,
    ):
        app.include_router(module.router, dependencies=protected)
    return app


app = create_app()
