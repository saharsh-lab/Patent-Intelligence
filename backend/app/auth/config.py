"""Auth settings, read from the same .env file as the main settings."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.config import PROJECT_ROOT


class AuthSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Separate database for accounts (users and their login sessions)
    auth_database_url: str = (
        "postgresql+psycopg://patent_rag:change_me_local_only@localhost:5434/patent_rag_auth"
    )
    auth_test_database_url: str = (
        "postgresql+psycopg://patent_rag:change_me_local_only@localhost:5434/patent_rag_auth_test"
    )
    # false = every request acts as one local user (tests, single-user laptop mode)
    auth_required: bool = True
    session_days: int = Field(default=14, ge=1, le=90)
    session_cookie_name: str = "pi_session"
    # true behind HTTPS (production): the cookie is never sent over plain HTTP
    session_cookie_secure: bool = False
    auth_rate_limit_per_minute: int = Field(default=10, ge=1)


@lru_cache
def get_auth_settings() -> AuthSettings:
    return AuthSettings()
