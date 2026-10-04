"""Patent monitoring: watches find new publications, once, ranked and imported."""

from dataclasses import replace
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_patent_sources
from app.core.config import get_settings
from app.database.session import get_db
from app.main import create_app
from app.models import Patent
from app.models.watch import WatchHit
from app.patents import demo
from app.patents.demo import DemoPatentSource
from app.rag.embeddings import FakeEmbedder, get_embedder
from app.services.watches import WatchService

pytestmark = pytest.mark.db


@pytest.fixture
def service(db_session, tmp_path):
    settings = get_settings().model_copy(update={"upload_dir": tmp_path})
    return WatchService(
        db_session, settings, FakeEmbedder(settings.embedding_dim), {"demo": DemoPatentSource()}
    )


def test_watch_finds_publications_once_and_imports_the_top(service, db_session):
    watch = service.create(
        name="cooling", keywords="battery coolant", import_top=1, lookback_days=4000
    )
    first = service.check(watch.id)
    assert first.error is None and first.new_hits >= 1
    assert len(first.imported) == 1  # only the top hit is imported
    assert db_session.get(Patent, db_session.get(WatchHit, watch.hits[0].id).imported_patent_id)

    second = service.check(watch.id)  # nothing new published since
    assert second.new_hits == 0 and len(service.get(watch.id).hits) == first.new_hits
    assert service.unseen_count(watch.id) == first.new_hits
    service.mark_seen(watch.id)
    assert service.unseen_count(watch.id) == 0


def test_a_newly_published_patent_is_found_at_the_next_check(service, monkeypatch):
    watch = service.create(
        name="cooling", keywords="battery coolant", import_top=0, lookback_days=4000
    )
    before = service.check(watch.id).new_hits

    fresh = replace(
        demo._RECORDS[0], publication_number="XX0000099A1", publication_date=date.today()
    )
    monkeypatch.setattr(demo, "_RECORDS", [*demo._RECORDS, fresh])
    after = service.check(watch.id)
    assert after.new_hits == 1  # only the new publication
    # (inside one test transaction all rows share now(), so check membership, not order)
    numbers = {h.publication_number for h in service.get(watch.id).hits}
    assert "XX0000099A1" in numbers and len(numbers) == before + 1
    assert before >= 1


def test_failed_search_is_recorded_not_raised(db_session, tmp_path):
    class Broken(DemoPatentSource):
        def search(self, query):
            raise ConnectionError("EPO unreachable")

    settings = get_settings().model_copy(update={"upload_dir": tmp_path})
    service = WatchService(
        db_session, settings, FakeEmbedder(settings.embedding_dim), {"demo": Broken()}
    )
    watch = service.create(name="x", keywords="pump")
    outcome = service.check(watch.id)
    assert outcome.error and service.get(watch.id).last_error
    assert service.get(watch.id).last_checked_at is not None


def test_watch_api(db_session, tmp_path):
    settings = get_settings().model_copy(update={"upload_dir": tmp_path})
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_embedder] = lambda: FakeEmbedder(settings.embedding_dim)
    app.dependency_overrides[get_patent_sources] = lambda: {"demo": DemoPatentSource()}
    api = TestClient(app)

    assert api.post("/watches", json={"name": "empty"}).status_code == 422  # no criteria
    created = api.post(
        "/watches",
        json={"name": "cooling", "keywords": "battery coolant", "lookback_days": 365 * 10},
    )
    assert created.status_code == 201, created.text
    watch_id = created.json()["id"]

    checked = api.post(f"/watches/{watch_id}/check").json()
    assert checked["new_hits"] >= 1 and checked["error"] is None
    listed = api.get("/watches").json()
    assert listed[0]["unseen"] == checked["new_hits"]
    hits = api.get(f"/watches/{watch_id}/hits").json()
    assert hits[0]["publication_number"].startswith("XX")

    assert api.post(f"/watches/{watch_id}/seen").status_code == 204
    assert api.get("/watches").json()[0]["unseen"] == 0
    assert api.patch(f"/watches/{watch_id}?active=false").json()["active"] is False
    assert api.delete(f"/watches/{watch_id}").status_code == 204
    assert api.get("/watches").json() == []
