"""Phase 0: application skeleton — health checks, request IDs, error format, config, logging."""

from app.core.config import Settings
from app.core.logging import redact


def test_liveness(client):
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_request_id_is_generated_and_returned(client):
    response = client.get("/health/live")
    assert len(response.headers["X-Request-ID"]) == 32


def test_safe_client_request_id_is_reused(client):
    response = client.get("/health/live", headers={"X-Request-ID": "abc123"})
    assert response.headers["X-Request-ID"] == "abc123"


def test_unsafe_client_request_id_is_replaced(client):
    response = client.get("/health/live", headers={"X-Request-ID": "bad id\nInjected: x"})
    assert response.headers["X-Request-ID"] != "bad id\nInjected: x"


def test_unknown_route_returns_consistent_error_shape(client):
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "http_error"
    assert error["request_id"] == response.headers["X-Request-ID"]


def test_readiness_reports_503_when_database_is_down(client, monkeypatch):
    def broken_db():
        raise ConnectionError("db down")

    monkeypatch.setattr("app.api.routes.health.check_database", broken_db)
    response = client.get("/health/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "not_ready"
    assert body["checks"]["database"]["status"] == "error"


def test_cors_origins_parsed_from_comma_separated_string():
    settings = Settings(_env_file=None, cors_origins="http://a.test, http://b.test")
    assert settings.cors_origins == ["http://a.test", "http://b.test"]


def test_secrets_are_masked_when_printed():
    settings = Settings(_env_file=None, llm_api_key="sk-supersecretvalue123")
    assert "supersecret" not in repr(settings)
    assert "supersecret" not in str(settings.llm_api_key)


def test_patent_sources_enabled_only_when_credentials_present():
    assert Settings(_env_file=None).enabled_patent_sources == []
    settings = Settings(_env_file=None, epo_ops_key="k", epo_ops_secret="s", lens_api_token="t")
    assert settings.enabled_patent_sources == ["epo", "lens"]


def test_upload_dir_is_resolved_from_project_root():
    assert Settings(_env_file=None, upload_dir="data/uploads").upload_dir.is_absolute()


def test_log_redaction():
    line = (
        "calling api_key=abc123 with Authorization: Bearer xyz.789 "
        "using sk-ABCDEFGHIJKLMNOP and postgresql+psycopg://user:hunter2@localhost/db"
    )
    cleaned = redact(line)
    for secret in ("abc123", "xyz.789", "ABCDEFGHIJKLMNOP", "hunter2"):
        assert secret not in cleaned
    assert "user:***@localhost" in cleaned


def test_tests_can_only_reach_test_databases():
    """Regression: tests must never write to development data, even through routes a
    test forgets to override (see conftest._point_everything_at_test_databases)."""
    from app.auth.config import get_auth_settings
    from app.core.config import get_settings

    settings = get_settings()
    assert settings.database_url == settings.test_database_url
    assert settings.eval_database_url == settings.test_database_url
    assert get_auth_settings().auth_database_url == get_auth_settings().auth_test_database_url
    assert "patent-rag-test-uploads" in str(settings.upload_dir)
