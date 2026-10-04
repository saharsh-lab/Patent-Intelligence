"""Phase 5 (with database): patent search, caching, import as evidence, and asking about patents."""

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.api.deps import get_patent_sources
from app.core.config import get_settings
from app.database.session import get_db
from app.llm.providers import FakeLLM, get_llm
from app.main import create_app
from app.models import ApiCache, Chunk, Patent
from app.patents.demo import DemoPatentSource
from app.patents.epo import EpoOpsSource
from app.rag.embeddings import FakeEmbedder, get_embedder
from tests.helpers import fixture_bytes
from tests.test_phase5_epo import FakeOps

pytestmark = pytest.mark.db


@pytest.fixture
def ops():
    return FakeOps()


@pytest.fixture
def sources(ops):
    epo = EpoOpsSource("key", "secret", http=httpx.Client(transport=httpx.MockTransport(ops)))
    return {"epo": epo, "demo": DemoPatentSource()}


@pytest.fixture
def api(db_session, tmp_path, sources):
    settings = get_settings().model_copy(
        update={"upload_dir": tmp_path, "retrieval_min_similarity": 0.1, "patent_demo_source": True}
    )
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_embedder] = lambda: FakeEmbedder(settings.embedding_dim)
    app.dependency_overrides[get_llm] = lambda: FakeLLM()
    app.dependency_overrides[get_patent_sources] = lambda: sources
    with TestClient(app) as client:
        yield client


def search(api, **body):
    response = api.post("/patents/search", json=body)
    assert response.status_code == 200, response.text
    return response.json()


def test_sources_endpoint_reports_status(api):
    statuses = {s["name"]: s["status"] for s in api.get("/patents/sources").json()}
    assert statuses["lens"] == "planned"
    assert statuses["demo"] == "available"


def test_search_epo_and_cache(api, ops, db_session):
    body = search(api, keywords="battery thermal", sources=["epo"], rank_by_relevance=False)
    assert [r["publication_number"] for r in body["results"]] == ["EP1234567A1", "WO2020123456A1"]
    assert all(r["full_text_likely"] for r in body["results"])  # EP and WO
    assert body["sources"][0]["cached"] is False
    assert body["sources"][0]["query_string"] == 'ta all "battery thermal"'

    calls_before = len(ops.calls)
    again = search(  # same query, other case
        api, keywords="Battery Thermal", sources=["epo"], rank_by_relevance=False
    )
    assert again["sources"][0]["cached"] is True
    assert len(ops.calls) == calls_before  # served from the database cache
    assert db_session.scalar(select(func.count()).select_from(ApiCache)) == 1


def test_one_failing_source_does_not_break_search(api, ops):
    ops.overrides["/search/biblio"] = httpx.Response(
        403, headers={"X-Rejection-Reason": "IndividualQuotaPerHour"}
    )
    body = search(api, keywords="battery coolant")
    by_source = {s["source"]: s for s in body["sources"]}
    assert "IndividualQuotaPerHour" in by_source["epo"]["error"]
    assert by_source["demo"]["error"] is None
    assert body["results"] and all(r["source"] == "demo" for r in body["results"])


def test_search_validation(api):
    assert api.post("/patents/search", json={"keywords": "  "}).status_code == 422
    bad_dates = {"keywords": "x", "date_from": "2024-01-01", "date_to": "2020-01-01"}
    assert api.post("/patents/search", json=bad_dates).status_code == 422
    unknown = api.post("/patents/search", json={"keywords": "x", "sources": ["lens"]})
    assert unknown.status_code == 422


def test_import_patent_creates_cited_evidence(api, db_session):
    response = api.post(
        "/patents/import", json={"source": "epo", "publication_number": "EP 1234567 A1"}
    )
    assert response.status_code == 201, response.text
    patent = response.json()["patent"]
    assert patent["publication_number"] == "EP1234567A1"
    assert patent["has_claims"] is True and patent["has_description"] is False
    assert "claims" in patent["sections_found"]

    claim_chunks = db_session.scalars(
        select(Chunk).where(Chunk.patent_id == patent["id"], Chunk.section == "claims")
    ).all()
    assert [c.meta["claim_number"] for c in claim_chunks] == [1, 2]

    again = api.post("/patents/import", json={"source": "epo", "publication_number": "EP1234567A1"})
    assert again.status_code == 200 and again.json()["already_imported"] is True

    results = search(api, keywords="battery thermal", sources=["epo"])["results"]
    imported = {r["publication_number"]: r["imported_id"] for r in results}
    assert imported["EP1234567A1"] == patent["id"]


def test_ask_about_imported_patent(api):
    patent = api.post(
        "/patents/import", json={"source": "demo", "publication_number": "XX0000002B1"}
    ).json()["patent"]
    api.post("/documents", files={"file": ("battery.txt", fixture_bytes("battery_patent.txt"))})

    body = api.post(
        "/ask",
        json={
            "question": "How does the charger detect metal objects?",
            "patent_ids": [patent["id"]],
        },
    ).json()
    assert body["status"] == "succeeded"
    assert body["summary"]["sources_searched"] == ["Imported patents"]
    assert {e["source_label"] for e in body["evidence"]} == {"XX0000002B1"}
    assert {e["source_type"] for e in body["evidence"]} == {"demo"}

    unscoped = api.post("/ask", json={"question": "How is the coolant pump controlled?"}).json()
    assert unscoped["summary"]["sources_searched"] == ["Uploaded documents", "Imported patents"]


def test_delete_imported_patent(api, db_session):
    patent = api.post(
        "/patents/import", json={"source": "demo", "publication_number": "XX0000001A1"}
    ).json()["patent"]
    assert [p["id"] for p in api.get("/patents").json()] == [patent["id"]]
    assert api.delete(f"/patents/{patent['id']}").status_code == 204
    assert db_session.scalar(select(func.count()).select_from(Patent)) == 0
    assert db_session.scalar(select(func.count()).select_from(Chunk)) == 0


def test_import_errors(api):
    bad_number = api.post("/patents/import", json={"source": "epo", "publication_number": "abc"})
    assert bad_number.status_code == 422
    missing = api.post(
        "/patents/import", json={"source": "epo", "publication_number": "EP9999999A1"}
    )
    assert missing.status_code == 502
    assert "no record" in missing.json()["error"]["message"]


def test_keyword_search_is_ranked_by_relevance_over_a_larger_pool(api, ops):
    body = search(api, keywords="battery thermal", sources=["epo"], limit=1)
    assert len(body["results"]) == 1 and body["results"][0]["similarity"] is not None
    assert body["reference_label"] == 'relevance to "battery thermal"'
    # one result shown, but a pool was fetched from the office to choose from
    searches = [c for c in ops.calls if "search" in c.url.path]
    assert searches[-1].url.params["Range"] == "1-50"


def test_full_text_only_limits_offices(api, ops):
    body = search(api, keywords="battery thermal", sources=["epo"], full_text_only=True)
    assert body["sources"][0]["query_string"] == 'ta all "battery thermal" and (pn=EP or pn=WO)'
