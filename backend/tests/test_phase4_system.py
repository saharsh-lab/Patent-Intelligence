"""Phase 4: the /system/info endpoint used by the UI exposes config but never secrets."""

import json

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.database.session import get_db
from app.main import create_app

pytestmark = pytest.mark.db


def test_system_info_has_config_and_no_secrets(db_session):
    settings = get_settings().model_copy(
        update={
            "llm_api_key": "sk-should-never-leak-123",
            "epo_ops_secret": "epo-secret-value",
            "llm_provider": "openai_compatible",
        }
    )
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as client:
        response = client.get("/system/info")
    assert response.status_code == 200
    body = response.json()
    assert body["retrieval"]["top_k"] == settings.retrieval_top_k
    assert body["counts"] == {"documents": 0, "chunks": 0, "runs": 0}
    raw = json.dumps(body)
    for secret in ("sk-should-never-leak-123", "epo-secret-value", "change_me_local_only"):
        assert secret not in raw
