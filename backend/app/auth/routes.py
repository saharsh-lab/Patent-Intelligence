"""/auth endpoints: register, login, logout, profile, password."""

from typing import Any

from fastapi import APIRouter, Request, Response, status
from pydantic import BaseModel, Field

from app.api.deps import SessionDep
from app.auth.adoption import adopt_unowned_data
from app.auth.config import AuthSettings
from app.auth.deps import AuthServiceDep, AuthSettingsDep, CurrentUser, session_token
from app.auth.models import User
from app.auth.service import AuthError

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterIn(BaseModel):
    email: str = Field(max_length=254)
    name: str = Field(max_length=80)
    password: str = Field(max_length=128)


class LoginIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=128)


class ProfileIn(BaseModel):
    name: str | None = Field(default=None, max_length=80)
    preferences: dict[str, str] | None = None


class PasswordIn(BaseModel):
    current_password: str = Field(max_length=128)
    new_password: str = Field(max_length=128)


class UserOut(BaseModel):
    id: str
    email: str
    name: str
    preferences: dict[str, Any]
    created_at: str

    @classmethod
    def of(cls, user: User) -> "UserOut":
        return cls(
            id=str(user.id),
            email=user.email,
            name=user.name,
            preferences=user.preferences or {},
            created_at=user.created_at.isoformat() if user.created_at else "",
        )


class AuthStatus(BaseModel):
    authenticated: bool
    auth_required: bool
    user: UserOut | None


def _set_cookie(response: Response, token: str, settings: AuthSettings) -> None:
    response.set_cookie(
        settings.session_cookie_name,
        token,
        max_age=settings.session_days * 86400,
        httponly=True,  # not readable by JavaScript: an XSS bug cannot steal it
        samesite="lax",  # not sent with cross-site POSTs: blocks CSRF
        secure=settings.session_cookie_secure,
        path="/",
    )


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(
    body: RegisterIn,
    data_session: SessionDep,
    request: Request,
    response: Response,
    service: AuthServiceDep,
    settings: AuthSettingsDep,
):
    user = service.register(email=body.email, name=body.name, password=body.password)
    adopt_unowned_data(service.session, data_session, user.id)
    token = service.start_session(user, request.headers.get("user-agent"))
    _set_cookie(response, token, settings)
    return UserOut.of(user)


@router.post("/login", response_model=UserOut)
def login(
    body: LoginIn,
    request: Request,
    response: Response,
    service: AuthServiceDep,
    settings: AuthSettingsDep,
):
    user, token = service.login(
        email=body.email, password=body.password, user_agent=request.headers.get("user-agent")
    )
    _set_cookie(response, token, settings)
    return UserOut.of(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, service: AuthServiceDep, settings: AuthSettingsDep):
    service.logout(session_token(request, settings))
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(settings.session_cookie_name, path="/")
    return response


@router.get("/me", response_model=AuthStatus)
def me(request: Request, service: AuthServiceDep, settings: AuthSettingsDep):
    user = service.user_for_token(session_token(request, settings))
    return AuthStatus(
        authenticated=user is not None,
        auth_required=settings.auth_required,
        user=UserOut.of(user) if user else None,
    )


@router.patch("/me", response_model=UserOut)
def update_me(body: ProfileIn, user: CurrentUser, service: AuthServiceDep):
    if user is None:
        raise AuthError("Please log in.")
    return UserOut.of(service.update_profile(user, name=body.name, preferences=body.preferences))


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    body: PasswordIn,
    request: Request,
    user: CurrentUser,
    service: AuthServiceDep,
    settings: AuthSettingsDep,
):
    if user is None:
        raise AuthError("Please log in.")
    service.change_password(
        user,
        current=body.current_password,
        new=body.new_password,
        keep_token=session_token(request, settings),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
