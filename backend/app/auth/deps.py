"""FastAPI dependencies for the current user.

The browser sends the session cookie with every request (same origin, through the
Next.js proxy). `require_user` protects every data endpoint; with AUTH_REQUIRED=false
(tests, single-user laptop mode) it returns None and data is not separated by user.
"""

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.auth.config import AuthSettings, get_auth_settings
from app.auth.db import get_auth_db
from app.auth.models import User
from app.auth.service import AuthError, AuthService

AuthDbDep = Annotated[Session, Depends(get_auth_db)]
AuthSettingsDep = Annotated[AuthSettings, Depends(get_auth_settings)]


def get_auth_service(session: AuthDbDep, settings: AuthSettingsDep) -> AuthService:
    return AuthService(session, settings.session_days)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def session_token(request: Request, settings: AuthSettingsDep) -> str | None:
    return request.cookies.get(settings.session_cookie_name)


def optional_user(
    request: Request, settings: AuthSettingsDep, service: AuthServiceDep
) -> User | None:
    user = service.user_for_token(session_token(request, settings))
    request.state.user = user
    return user


def require_user(
    request: Request, settings: AuthSettingsDep, service: AuthServiceDep
) -> User | None:
    user = optional_user(request, settings, service)
    if user is None and settings.auth_required:
        raise AuthError("Please log in.")
    return user


CurrentUser = Annotated[User | None, Depends(require_user)]
