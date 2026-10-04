"""Accounts: registration, login sessions, protection of data endpoints, profiles."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.auth.config import get_auth_settings
from app.auth.db import get_auth_db
from app.auth.models import LoginSession, User
from app.auth.passwords import hash_password, password_problem, token_digest, verify_password
from app.main import create_app

pytestmark = pytest.mark.db

PASSWORD = "correct-horse-7"


# ------------------------------------------------------------------ passwords (no database)


def test_password_hashing():
    stored = hash_password(PASSWORD)
    assert stored.startswith("scrypt$") and PASSWORD not in stored
    assert verify_password(PASSWORD, stored)
    assert not verify_password("wrong-password-1", stored)
    assert hash_password(PASSWORD) != stored  # a fresh random salt every time
    assert not verify_password(PASSWORD, "garbage")


@pytest.mark.parametrize(
    ("password", "ok"),
    [("short1", False), ("onlyletters", False), ("12345678", False), (PASSWORD, True)],
)
def test_password_policy(password, ok):
    assert (password_problem(password) is None) is ok


# ------------------------------------------------------------------ API (auth test database)


@pytest.fixture(scope="module")
def auth_engine():
    from scripts.migrate_auth import migrate

    url = get_auth_settings().auth_test_database_url
    try:
        migrate(url)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Auth test database unavailable: {exc!r}"[:200])
    engine = create_engine(url)
    yield engine
    engine.dispose()


@pytest.fixture
def auth_db(auth_engine) -> Iterator[Session]:
    connection = auth_engine.connect()
    outer = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    yield session
    session.close()
    outer.rollback()
    connection.close()


@pytest.fixture
def api(auth_db, monkeypatch) -> TestClient:
    monkeypatch.setenv("AUTH_REQUIRED", "true")
    get_auth_settings.cache_clear()
    app = create_app()
    app.dependency_overrides[get_auth_db] = lambda: auth_db
    client = TestClient(app)
    yield client
    get_auth_settings.cache_clear()


def register(api, email="ada@example.com", name="Ada Lovelace"):
    return api.post("/auth/register", json={"email": email, "name": name, "password": PASSWORD})


def test_data_endpoints_need_login(api):
    response = api.get("/documents")
    assert response.status_code == 401 and response.json()["error"]["code"] == "unauthorized"
    assert api.get("/health/live").status_code == 200  # health stays open
    status = api.get("/auth/me").json()
    assert status == {"authenticated": False, "auth_required": True, "user": None}


def test_register_logs_in_with_a_secure_cookie(api, auth_db):
    response = register(api, email="  Ada@Example.com ")
    assert response.status_code == 201
    assert response.json()["email"] == "ada@example.com"  # normalised
    cookie = response.headers["set-cookie"]
    assert "pi_session=" in cookie and "HttpOnly" in cookie and "SameSite=lax" in cookie
    assert api.get("/auth/me").json()["user"]["name"] == "Ada Lovelace"

    # Only a hash of the session token is stored
    token = api.cookies.get("pi_session")
    stored = auth_db.scalar(select(LoginSession.token_hash))
    assert stored == token_digest(token) and stored != token
    user = auth_db.scalar(select(User))
    assert user.password_hash.startswith("scrypt$")


def test_duplicate_email_and_bad_input(api):
    register(api)
    assert register(api).status_code == 409
    bad = api.post("/auth/register", json={"email": "x@y.io", "name": "X", "password": "short"})
    assert bad.status_code == 422 and "at least 8" in bad.json()["error"]["message"]
    bad = api.post(
        "/auth/register", json={"email": "not-an-email", "name": "X", "password": PASSWORD}
    )
    assert bad.status_code == 422


def test_login_logout_and_generic_errors(api):
    register(api)
    api.post("/auth/logout")
    assert api.get("/auth/me").json()["authenticated"] is False

    wrong = api.post("/auth/login", json={"email": "ada@example.com", "password": "nope-nope-1"})
    unknown = api.post("/auth/login", json={"email": "who@example.com", "password": PASSWORD})
    # Same answer for a wrong password and an unknown email: no account enumeration
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["error"]["message"] == unknown.json()["error"]["message"]

    assert (
        api.post("/auth/login", json={"email": "ADA@example.com", "password": PASSWORD}).status_code
        == 200
    )
    assert api.get("/auth/me").json()["authenticated"] is True


def test_logout_revokes_the_session_server_side(api):
    register(api)
    token = api.cookies.get("pi_session")
    api.post("/auth/logout")
    api.cookies.set("pi_session", token)  # a stolen copy of the cookie no longer works
    assert api.get("/auth/me").json()["authenticated"] is False


def test_profile_and_preferences(api):
    register(api)
    updated = api.patch("/auth/me", json={"name": "Ada", "preferences": {"theme": "dark"}})
    assert updated.json()["name"] == "Ada" and updated.json()["preferences"] == {"theme": "dark"}
    bad = api.patch("/auth/me", json={"preferences": {"theme": "neon"}})
    assert bad.status_code == 422


def test_password_change_logs_out_other_browsers(api, auth_db):
    register(api)
    other = TestClient(api.app)
    assert (
        other.post(
            "/auth/login", json={"email": "ada@example.com", "password": PASSWORD}
        ).status_code
        == 200
    )

    wrong = api.post(
        "/auth/password", json={"current_password": "x" * 9 + "1", "new_password": "new-pass-123"}
    )
    assert wrong.status_code == 401
    ok = api.post(
        "/auth/password", json={"current_password": PASSWORD, "new_password": "new-pass-123"}
    )
    assert ok.status_code == 204
    assert api.get("/auth/me").json()["authenticated"] is True  # this browser stays in
    assert other.get("/auth/me").json()["authenticated"] is False  # the other is logged out


def test_auth_database_is_separate(auth_engine):
    from app.core.config import get_settings

    with auth_engine.connect() as conn:
        tables = set(
            conn.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname='public'")
            ).scalars()
        )
    assert {"users", "login_sessions"} <= tables and "documents" not in tables
    assert get_auth_settings().auth_database_url != get_settings().database_url


def test_owner_scope_reaches_endpoint_threads(api):
    """The middleware's owner must be visible inside sync endpoints (worker threads),
    because the search layer filters documents by it."""
    from app.auth.middleware import NOBODY
    from app.core.ownership import current_owner, scoped

    @api.app.get("/__owner")
    def owner():
        return {"scoped": scoped(), "owner": str(current_owner())}

    assert api.get("/__owner").json() == {"scoped": True, "owner": str(NOBODY)}  # anonymous
    user_id = register(api).json()["id"]
    assert api.get("/__owner").json() == {"scoped": True, "owner": user_id}
