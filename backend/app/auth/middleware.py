"""Request-scoped data owner.

For every HTTP request, find the logged-in user from the session cookie and run the
rest of the request inside `owner_scope(user_id)` (app/core/ownership.py). Context
variables are copied into the worker threads that run endpoints, so every query made
while handling the request (documents, search, agent tools, …) sees only this user's
data plus public patents.

- logged in                          → owner = user id
- not logged in, AUTH_REQUIRED=true  → owner = NOBODY (matches no document; the
                                        endpoint itself answers 401 anyway)
- AUTH_REQUIRED=false (single user)  → owner = None (documents without an owner)
"""

import uuid

import anyio
from starlette.types import ASGIApp, Receive, Scope, Send

from app.auth.config import get_auth_settings
from app.auth.db import get_auth_db
from app.auth.service import AuthService
from app.core.ownership import owner_scope

NOBODY = uuid.UUID(int=0)


def _cookie(scope: Scope, name: str) -> str | None:
    for key, value in scope.get("headers", []):
        if key == b"cookie":
            for part in value.decode("latin-1").split(";"):
                k, _, v = part.strip().partition("=")
                if k == name:
                    return v
    return None


class OwnerScopeMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        settings = get_auth_settings()
        token = _cookie(scope, settings.session_cookie_name)
        owner = await anyio.to_thread.run_sync(self._resolve, scope, token) if token else None
        if owner is None and settings.auth_required:
            owner = NOBODY
        with owner_scope(owner):
            await self.app(scope, receive, send)

    @staticmethod
    def _resolve(scope: Scope, token: str) -> uuid.UUID | None:
        # Honour test overrides of the auth database dependency
        provider = scope["app"].dependency_overrides.get(get_auth_db, get_auth_db)
        sessions = provider()
        session = next(sessions) if hasattr(sessions, "__next__") else sessions
        try:
            user = AuthService(session, get_auth_settings().session_days).user_for_token(token)
            return user.id if user else None
        finally:
            if hasattr(sessions, "close"):
                sessions.close()
