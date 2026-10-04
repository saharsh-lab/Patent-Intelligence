"""Phase 11 (no database): rate limits, body-size limits, security headers, zip bombs,
production start-up checks."""

import io
import zipfile

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.errors import ConfigurationError, InvalidDocumentError
from app.core.security import (
    DEFAULT_DB_PASSWORD,
    SlidingWindowLimiter,
    check_production_settings,
)
from app.main import create_app
from app.rag.extraction import detect_file_kind


def make_client(monkeypatch, **env) -> TestClient:
    for key, value in env.items():
        monkeypatch.setenv(key, str(value))
    get_settings.cache_clear()
    try:
        return TestClient(create_app())
    finally:
        get_settings.cache_clear()


# ------------------------------------------------------------------ rate limits


def test_sliding_window_limiter():
    limiter = SlidingWindowLimiter(window_seconds=60)
    key = ("llm", "1.2.3.4")
    assert [limiter.hit(key, 2, now=t) for t in (0, 1)] == [0, 0]
    assert limiter.hit(key, 2, now=2) == pytest.approx(58)  # wait until the first expires
    assert limiter.hit(key, 2, now=60.5) == 0  # first hit left the window
    assert limiter.hit(("llm", "5.6.7.8"), 2, now=2) == 0  # other clients unaffected


def test_llm_endpoints_are_rate_limited(monkeypatch):
    client = make_client(monkeypatch, RATE_LIMIT_ENABLED="true", RATE_LIMIT_LLM_PER_MINUTE=2)
    # Invalid bodies (422) still count: the limit protects before any validation
    codes = [client.post("/ask", json={}).status_code for _ in range(3)]
    assert codes == [422, 422, 429]
    limited = client.post("/compare", json={})
    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "rate_limited"
    assert int(limited.headers["retry-after"]) > 0
    assert client.get("/health/live").status_code == 200  # health checks are never limited


def test_forwarded_for_is_ignored_unless_trusted(monkeypatch):
    client = make_client(monkeypatch, RATE_LIMIT_ENABLED="true", RATE_LIMIT_LLM_PER_MINUTE=1)
    client.post("/ask", json={}, headers={"X-Forwarded-For": "10.0.0.1"})
    # A spoofed header must not give a fresh budget
    spoofed = client.post("/ask", json={}, headers={"X-Forwarded-For": "10.0.0.2"})
    assert spoofed.status_code == 429


# ------------------------------------------------------------------ body size


def test_oversized_json_body_is_rejected_before_parsing(monkeypatch):
    client = make_client(monkeypatch, MAX_JSON_BODY_KB=16)
    response = client.post(
        "/ask",
        content=b'{"question": "' + b"x" * 20_000 + b'"}',
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "payload_too_large"


def test_oversized_chunked_upload_is_cut_off(monkeypatch):
    client = make_client(monkeypatch, MAX_UPLOAD_MB=1)

    def chunks():  # no Content-Length: the size is only known while streaming
        yield b'--b\r\nContent-Disposition: form-data; name="file"; filename="a.txt"\r\n\r\n'
        for _ in range(40):
            yield b"x" * 65536

    response = client.post(
        "/documents",
        content=chunks(),
        headers={"Content-Type": "multipart/form-data; boundary=b"},
    )
    assert response.status_code == 413
    assert response.json()["error"]["message"] == "The file is too large."


# ------------------------------------------------------------------ headers


def test_security_headers(client):
    response = client.get("/health/live")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["cache-control"] == "no-store"
    assert "default-src 'none'" in response.headers["content-security-policy"]
    assert "content-security-policy" not in client.get("/docs").headers  # Swagger needs CDN


# ------------------------------------------------------------------ uploads


def docx_with(entries: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries.items():
            archive.writestr(name, data)
    return buffer.getvalue()


def test_docx_zip_bomb_is_rejected():
    bomb = docx_with({"word/document.xml": b"<w/>", "word/padding.xml": b"\0" * 50_000_000})
    assert len(bomb) < 100_000  # tiny on disk...
    with pytest.raises(InvalidDocumentError, match="implausible size"):
        detect_file_kind("report.docx", bomb)  # ...but 50 MB of zeros inside


def test_normal_docx_passes():
    from tests.helpers import make_docx

    assert detect_file_kind("ok.docx", make_docx(["Claim 1. A pump."])) == "docx"


# ------------------------------------------------------------------ production checks


def production(**overrides):
    return get_settings().model_copy(
        update={
            "app_env": "production",
            "database_url": "postgresql+psycopg://u:a-real-secret@db/x",
            "cors_origins": ["https://patents.example.org"],
            "patent_demo_source": False,
            "rate_limit_enabled": True,
            **overrides,
        }
    )


def test_production_refuses_unsafe_settings():
    unsafe = production(
        database_url=f"postgresql+psycopg://u:{DEFAULT_DB_PASSWORD}@db/x",
        cors_origins=["*"],
        patent_demo_source=True,
    )
    with pytest.raises(ConfigurationError) as error:
        check_production_settings(unsafe)
    message = str(error.value)
    assert "example password" in message and "'*'" in message and "PATENT_DEMO" in message
    assert DEFAULT_DB_PASSWORD not in message.replace("example password", "")  # no secret echo


def test_production_warns_about_fake_models():
    assert check_production_settings(production(llm_provider="fake"))
    assert check_production_settings(get_settings()) == []  # development: no checks
