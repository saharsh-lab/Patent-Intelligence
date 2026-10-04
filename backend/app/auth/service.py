"""Account operations. Error messages never reveal whether an email is registered."""

import re
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.auth.models import LoginSession, User
from app.auth.passwords import (
    hash_password,
    new_session_token,
    password_problem,
    token_digest,
    verify_password,
)
from app.core.errors import AppError, ValidationFailedError

EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$")
ALLOWED_PREFERENCES = {
    "theme": {"light", "dark", "system"},
    "answer_detail": {"concise", "detailed"},
    "default_pipeline": {"agentic", "baseline"},
}
# Burns the same time as a real check when the email is unknown (no timing oracle)
_DUMMY_HASH = hash_password("dummy-password-for-timing")


class AuthError(AppError):
    def __init__(self, message: str = "Email or password is incorrect."):
        super().__init__(message, code="unauthorized", status_code=401)


def normalize_email(email: str) -> str:
    email = email.strip().lower()
    if not EMAIL.match(email) or len(email) > 254:
        raise ValidationFailedError("Enter a valid email address.")
    return email


class AuthService:
    def __init__(self, session: Session, session_days: int = 14):
        self.session = session
        self.session_days = session_days

    def register(self, *, email: str, name: str, password: str) -> User:
        email = normalize_email(email)
        name = " ".join(name.split())
        if not 1 <= len(name) <= 80:
            raise ValidationFailedError("Enter your name (up to 80 characters).")
        if problem := password_problem(password):
            raise ValidationFailedError(problem)
        if self.session.scalar(select(User.id).where(User.email == email)):
            raise AppError(
                "An account with this email already exists. Log in instead.",
                code="email_taken",
                status_code=409,
            )
        user = User(email=email, name=name, password_hash=hash_password(password))
        self.session.add(user)
        self.session.commit()
        return user

    def login(self, *, email: str, password: str, user_agent: str | None) -> tuple[User, str]:
        try:
            email = normalize_email(email)
        except ValidationFailedError:
            raise AuthError() from None
        user = self.session.scalar(select(User).where(User.email == email))
        if user is None:
            verify_password(password, _DUMMY_HASH)
            raise AuthError()
        if not verify_password(password, user.password_hash) or not user.is_active:
            raise AuthError()
        token = self._start_session(user, user_agent)
        user.last_login_at = datetime.now(UTC)
        self.session.commit()
        return user, token

    def _start_session(self, user: User, user_agent: str | None) -> str:
        token = new_session_token()
        now = datetime.now(UTC)
        self.session.add(
            LoginSession(
                user_id=user.id,
                token_hash=token_digest(token),
                user_agent=(user_agent or "")[:200] or None,
                expires_at=now + timedelta(days=self.session_days),
                last_seen_at=now,
            )
        )
        return token

    def start_session(self, user: User, user_agent: str | None) -> str:
        token = self._start_session(user, user_agent)
        self.session.commit()
        return token

    def user_for_token(self, token: str | None) -> User | None:
        if not token:
            return None
        login = self.session.scalar(
            select(LoginSession).where(LoginSession.token_hash == token_digest(token))
        )
        now = datetime.now(UTC)
        if login is None or login.revoked or login.expires_at <= now:
            return None
        if not login.user.is_active:
            return None
        if not login.last_seen_at or now - login.last_seen_at > timedelta(minutes=5):
            login.last_seen_at = now  # coarse, to avoid a write on every request
            self.session.commit()
        return login.user

    def logout(self, token: str | None) -> None:
        if token:
            self.session.execute(
                update(LoginSession)
                .where(LoginSession.token_hash == token_digest(token))
                .values(revoked=True)
            )
            self.session.commit()

    def update_profile(
        self, user: User, *, name: str | None = None, preferences: dict | None = None
    ) -> User:
        user = self.session.get(User, user.id)
        if name is not None:
            name = " ".join(name.split())
            if not 1 <= len(name) <= 80:
                raise ValidationFailedError("Enter your name (up to 80 characters).")
            user.name = name
        if preferences:
            merged = dict(user.preferences or {})
            for key, value in preferences.items():
                if key not in ALLOWED_PREFERENCES or value not in ALLOWED_PREFERENCES[key]:
                    raise ValidationFailedError(f"Unknown preference {key}={value!r}.")
                merged[key] = value
            user.preferences = merged
        self.session.commit()
        return user

    def change_password(
        self, user: User, *, current: str, new: str, keep_token: str | None
    ) -> None:
        user = self.session.get(User, user.id)
        if not verify_password(current, user.password_hash):
            raise AuthError("The current password is incorrect.")
        if problem := password_problem(new):
            raise ValidationFailedError(problem)
        user.password_hash = hash_password(new)
        # Log out every other browser: a changed password should lock out whoever knew it
        keep = token_digest(keep_token) if keep_token else None
        self.session.execute(
            update(LoginSession)
            .where(LoginSession.user_id == user.id, LoginSession.token_hash != keep)
            .values(revoked=True)
        )
        self.session.commit()
