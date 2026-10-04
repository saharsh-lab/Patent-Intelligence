"""Shared pytest fixtures.

Tests never use the development database: `db_engine` connects to the separate
`patent_rag_test` database, upgrades it to the latest migration once, and each
test runs inside a transaction that is rolled back afterwards, so tests cannot
leave data behind or affect each other.
"""

import os
from collections.abc import Iterator

import pytest

os.environ["APP_ENV"] = "test"
# Tests must be deterministic and free: never call paid APIs by default
os.environ["LLM_PROVIDER"] = "fake"
os.environ["EMBEDDING_PROVIDER"] = "fake"
# Deterministic, model-free claim verification (NLI is tested with a stand-in model)
os.environ["VERIFIER_METHOD"] = "lexical"
# Rate limits are tested explicitly (test_phase11_security.py); elsewhere they'd make
# tests depend on how many requests a module happens to send per minute
os.environ["RATE_LIMIT_ENABLED"] = "false"
# Accounts are tested explicitly (test_auth.py); other tests act as the single local user
os.environ["AUTH_REQUIRED"] = "false"


def _point_everything_at_test_databases() -> None:
    """Safety net: whatever a test forgets to override, it can only reach test data.

    Found the hard way: an account test that replaced only the auth database let the
    "first user adopts existing data" step update the real development database."""
    import tempfile

    from app.auth.config import AuthSettings
    from app.core.config import Settings

    main = Settings()
    auth = AuthSettings()
    os.environ["DATABASE_URL"] = main.test_database_url
    os.environ["EVAL_DATABASE_URL"] = main.test_database_url
    os.environ["AUTH_DATABASE_URL"] = auth.auth_test_database_url
    os.environ["UPLOAD_DIR"] = tempfile.mkdtemp(prefix="patent-rag-test-uploads-")


_point_everything_at_test_databases()

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import Engine, create_engine, text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def db_engine() -> Iterator[Engine]:
    from alembic import command
    from alembic.config import Config

    url = get_settings().test_database_url
    engine = create_engine(url, hide_parameters=True, connect_args={"connect_timeout": 3})
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Test database unavailable (run `docker compose up -d db`): {exc!r}"[:300])

    cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "..", "alembic"))
    cfg.attributes["database_url"] = url
    cfg.attributes["configure_logger"] = False
    command.upgrade(cfg, "head")
    # Every test inserts rows and rolls back. Rolled-back rows leave dead entries in the
    # HNSW index until VACUUM; after many runs they made approximate vector search flaky.
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text("VACUUM chunks"))
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine: Engine) -> Iterator[Session]:
    """A session whose changes are rolled back after the test (even if it commits)."""
    connection = db_engine.connect()
    outer = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        outer.rollback()
        connection.close()
