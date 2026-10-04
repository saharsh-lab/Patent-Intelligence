"""HTTP hardening (Phase 11): request size limits, rate limits, security headers,
and start-up checks for production settings.

Threat model (see docs/security.md): a single-user research tool run on a laptop or a
small server behind the Next.js frontend. These measures limit cost and abuse (an LLM call
per /ask), resource exhaustion (huge uploads), and browser-side attacks on API responses.
There is no user authentication: do not expose the app to the internet without an
authenticating reverse proxy in front of it.
"""

import json
import math
import threading
import time
from collections import deque
from dataclasses import dataclass

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import Settings
from app.core.errors import ConfigurationError
from app.core.logging import request_id_var


async def _send_error(send: Send, status: int, code: str, message: str, headers=()) -> None:
    body = json.dumps(
        {"error": {"code": code, "message": message, "request_id": request_id_var.get()}}
    ).encode()
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
                *headers,
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


# ---------------------------------------------------------------- request size


class BodySizeLimitMiddleware:
    """Reject request bodies over the limit while they stream in, before any parsing.

    Without it, Starlette's multipart parser writes the whole upload to disk before the
    route's own MAX_UPLOAD_MB check runs. Uploads may be MAX_UPLOAD_MB (+ form overhead);
    every other request body is capped at MAX_JSON_BODY_KB."""

    def __init__(self, app: ASGIApp, *, upload_bytes: int, other_bytes: int):
        self.app = app
        self.upload_bytes = upload_bytes + 64 * 1024  # multipart boundaries and headers
        self.other_bytes = other_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] in ("GET", "HEAD", "OPTIONS"):
            await self.app(scope, receive, send)
            return
        is_upload = scope["path"] == "/documents" and scope["method"] == "POST"
        limit = self.upload_bytes if is_upload else self.other_bytes
        message = (
            "The file is too large."
            if is_upload
            else f"Request body is too large (limit {limit // 1024} KB)."
        )

        declared = dict(scope["headers"]).get(b"content-length")
        if declared is not None and declared.isdigit() and int(declared) > limit:
            await _send_error(send, 413, "payload_too_large", message)
            return

        received = 0
        too_large = False

        async def limited_receive() -> Message:
            nonlocal received, too_large
            msg = await receive()
            if msg["type"] == "http.request":
                received += len(msg.get("body", b""))
                if received > limit:  # chunked bodies have no Content-Length
                    too_large = True
                    raise _BodyTooLarge
            return msg

        async def guarded_send(msg: Message) -> None:
            # FastAPI turns errors while reading a body into its own 400 response; once
            # the limit is exceeded, drop whatever the app sends and answer 413 instead.
            if not too_large:
                await send(msg)

        try:
            await self.app(scope, limited_receive, guarded_send)
        except Exception:
            if not too_large:
                raise
        if too_large:
            await _send_error(send, 413, "payload_too_large", message)


class _BodyTooLarge(Exception):
    pass


# ---------------------------------------------------------------- rate limits


@dataclass(frozen=True)
class RateRule:
    name: str
    methods: tuple[str, ...]
    prefixes: tuple[str, ...]
    per_minute: int


class SlidingWindowLimiter:
    """Counts requests per (rule, client) in the last 60 seconds. In memory: limits are
    per server process, which is enough for one uvicorn worker."""

    def __init__(self, window_seconds: float = 60.0):
        self.window = window_seconds
        self._hits: dict[tuple[str, str], deque[float]] = {}
        self._lock = threading.Lock()

    def hit(self, key: tuple[str, str], limit: int, now: float | None = None) -> float:
        """Record a request; return 0 if allowed, else seconds until one is allowed."""
        now = time.monotonic() if now is None else now
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and hits[0] <= now - self.window:
                hits.popleft()
            if len(hits) >= limit:
                return hits[0] + self.window - now
            hits.append(now)
            if len(self._hits) > 10_000:  # forget idle clients
                for stale in [k for k, v in self._hits.items() if not v]:
                    del self._hits[stale]
            return 0.0


def rate_rules(settings: Settings) -> list[RateRule]:
    """First matching rule wins. LLM-backed endpoints get the tightest budget."""
    from app.auth.config import get_auth_settings

    return [
        # Password guessing: few attempts per minute per client
        RateRule(
            "auth",
            ("POST",),
            ("/auth/login", "/auth/register", "/auth/password"),
            get_auth_settings().auth_rate_limit_per_minute,
        ),
        RateRule(
            "llm",
            ("POST",),
            ("/ask", "/compare", "/analysis", "/conversations"),
            settings.rate_limit_llm_per_minute,
        ),
        RateRule(
            "ingest",
            ("POST",),
            ("/documents", "/patents/import", "/patents/search", "/watches"),
            settings.rate_limit_ingest_per_minute,
        ),
        RateRule(
            "default",
            ("GET", "POST", "PUT", "PATCH", "DELETE"),
            ("/",),
            settings.rate_limit_default_per_minute,
        ),
    ]


class RateLimitMiddleware:
    EXEMPT = ("/health",)  # monitoring must never be throttled

    def __init__(self, app: ASGIApp, *, settings: Settings):
        self.app = app
        self.rules = rate_rules(settings)
        self.trust_proxy = settings.trust_proxy_headers
        self.limiter = SlidingWindowLimiter()

    def _client(self, scope: Scope) -> str:
        if self.trust_proxy:
            # Only safe when a proxy you control overwrites this header. The bundled
            # Next.js proxy does NOT: it keeps a client-supplied X-Forwarded-For.
            forwarded = dict(scope["headers"]).get(b"x-forwarded-for", b"").decode()
            if forwarded:
                return forwarded.split(",")[0].strip()
        client = scope.get("client")
        return client[0] if client else "unknown"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"].startswith(self.EXEMPT):
            await self.app(scope, receive, send)
            return
        path, method = scope["path"], scope["method"]
        rule = next(
            (r for r in self.rules if method in r.methods and path.startswith(r.prefixes)), None
        )
        if rule is not None:
            wait = self.limiter.hit((rule.name, self._client(scope)), rule.per_minute)
            if wait > 0:
                await _send_error(
                    send,
                    429,
                    "rate_limited",
                    f"Too many requests ({rule.per_minute} per minute for this kind of "
                    f"request). Try again in {math.ceil(wait)} s.",
                    headers=[(b"retry-after", str(math.ceil(wait)).encode())],
                )
                return
        await self.app(scope, receive, send)


# ---------------------------------------------------------------- headers


class SecurityHeadersMiddleware:
    """Headers that stop browsers from misusing API responses (sniffing them as HTML,
    framing them, caching answers about private documents)."""

    def __init__(self, app: ASGIApp, *, production: bool):
        self.app = app
        self.production = production

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        docs = scope["path"] in ("/docs", "/openapi.json", "/docs/oauth2-redirect")

        async def add_headers(msg: Message) -> None:
            if msg["type"] == "http.response.start":
                headers = list(msg.get("headers", []))
                headers += [
                    (b"x-content-type-options", b"nosniff"),
                    (b"x-frame-options", b"DENY"),
                    (b"referrer-policy", b"no-referrer"),
                    (b"cache-control", b"no-store"),
                ]
                if not docs:  # Swagger UI loads scripts from a CDN
                    headers.append(
                        (b"content-security-policy", b"default-src 'none'; frame-ancestors 'none'")
                    )
                if self.production:
                    headers.append((b"strict-transport-security", b"max-age=31536000"))
                msg["headers"] = headers
            await send(msg)

        await self.app(scope, receive, add_headers)


# ---------------------------------------------------------------- start-up checks


DEFAULT_DB_PASSWORD = "change_me_local_only"


def check_production_settings(settings: Settings) -> list[str]:
    """In production, refuse to start with settings that are only safe on a laptop.
    Returns warnings for things that are allowed but probably unintended."""
    if settings.app_env != "production":
        return []
    errors = []
    if DEFAULT_DB_PASSWORD in settings.database_url:
        errors.append("DATABASE_URL still uses the example password from .env.example")
    if "*" in settings.cors_origins:
        errors.append("CORS_ORIGINS must list origins explicitly, not '*'")
    if settings.patent_demo_source:
        errors.append("PATENT_DEMO_SOURCE must be false (synthetic patents)")
    if not settings.rate_limit_enabled:
        errors.append("RATE_LIMIT_ENABLED must be true")
    if errors:
        raise ConfigurationError("Unsafe production settings: " + "; ".join(errors))
    warnings = []
    if settings.llm_provider == "fake" or settings.embedding_provider == "fake":
        warnings.append("fake LLM/embedding provider in production: answers are canned")
    return warnings
