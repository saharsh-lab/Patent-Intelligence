"""Phase 16: the patent landscape map."""

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_patent_sources
from app.core.config import get_settings
from app.database.session import get_db
from app.intelligence.landscape import choose_k, cluster_names, kmeans, project_2d
from app.llm.providers import FakeLLM, get_llm
from app.main import create_app
from app.patents.base import PatentRecord, PatentSearchPage, PatentSource
from app.rag.embeddings import FakeEmbedder, get_embedder
from tests.helpers import fixture_bytes

COOLING = [
    "Battery pack immersion cooling with dielectric fluid circulating around the cells",
    "Immersion cooled battery module with dielectric oil and a pump for the cells",
    "Dielectric fluid immersion cooling tank for battery cells with heat exchanger",
    "Battery cells submerged in dielectric coolant fluid with immersion pump circulation",
    "Immersion cooling of battery modules using dielectric fluid flow over cells",
    "Battery thermal management by immersion in circulating dielectric cooling fluid",
]
CHARGING = [
    "Wireless charger detecting a foreign metal object on the charging coil",
    "Foreign object detection for a wireless charging pad using coil quality factor",
    "Metal object detection in inductive wireless charging by coil resonance shift",
    "Wireless power transmitter detects foreign metal objects near the charging coil",
    "Inductive charging coil with foreign object detection by measuring power loss",
    "Detecting metal foreign objects on a wireless charging coil before power transfer",
]


def record(i, text):
    return PatentRecord(
        source="stub",
        publication_number=f"EP{1000000 + i}A1",
        title=text.split(" with ")[0],
        abstract=text,
        applicants=["Example Corp"],
    )


class StubSource(PatentSource):
    name = "stub"
    label = "Stub office"

    def __init__(self, texts):
        self.records = [record(i, t) for i, t in enumerate(texts)]

    def search(self, query):
        return PatentSearchPage("stub", len(self.records), list(self.records), query.keywords)

    def get_details(self, publication_number):
        return next(r for r in self.records if r.publication_number == publication_number)


class DownSource(StubSource):
    def search(self, query):
        from app.core.errors import AppError

        raise AppError("Could not reach the EPO patent service.", code="unreachable")


@pytest.fixture
def api(db_session, tmp_path):
    settings = get_settings().model_copy(update={"upload_dir": tmp_path, "patent_search_pool": 50})
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_embedder] = lambda: FakeEmbedder(settings.embedding_dim)
    app.dependency_overrides[get_llm] = lambda: FakeLLM()

    def use(source):
        app.dependency_overrides[get_patent_sources] = lambda: {"stub": source}

    use(StubSource(COOLING + CHARGING))
    client = TestClient(app)
    client.use = use
    return client


# ---------------------------------------------------------------- maths


def test_kmeans_separates_two_groups_and_is_repeatable():
    rng = np.random.default_rng(3)
    a = rng.normal(0, 0.1, (10, 16)) + np.eye(16)[0] * 3
    b = rng.normal(0, 0.1, (6, 16)) + np.eye(16)[1] * 3
    labels = kmeans(np.vstack([a, b]), 2)
    assert set(labels[:10]) == {0} and set(labels[10:]) == {1}  # largest cluster first
    assert (kmeans(np.vstack([a, b]), 2) == labels).all()


def test_small_maps_use_pca_and_fit_the_frame():
    coords, method = project_2d(np.random.default_rng(0).normal(size=(6, 8)))
    assert method == "PCA" and coords.shape == (6, 2) and np.abs(coords).max() == pytest.approx(1)


def test_cluster_count_and_names():
    assert [choose_k(n) for n in (5, 12, 40, 100)] == [1, 2, 3, 5]
    names = cluster_names(COOLING + CHARGING, np.array([0] * 6 + [1] * 6), 2)
    cooling_words = set(" ".join(COOLING).lower().split())
    charging_words = set(" ".join(CHARGING).lower().split())
    assert set(names[0].replace(",", " ").split()) <= cooling_words - charging_words
    assert set(names[1].replace(",", " ").split()) <= charging_words - cooling_words


def test_boilerplate_does_not_name_a_cluster():
    texts = [f"The utility model discloses a cold plate for battery {i}" for i in range(5)] + [
        f"The invention relates to a fire extinguishing sheet {i}" for i in range(5)
    ]
    names = cluster_names(texts, np.array([0] * 5 + [1] * 5), 2)
    assert "cold plate" in names[0] and "extinguishing" in names[1]
    assert not any(w in " ".join(names) for w in ("utility", "model", "invention", "relates"))


# ---------------------------------------------------------------- API


@pytest.mark.db
def test_map_groups_topics_and_stars_the_invention(api):
    body = api.post(
        "/landscape",
        json={"keywords": "battery charging", "invention": COOLING[0], "include_library": False},
    ).json()
    points = body["points"]
    assert len(points) == 12 and len(body["clusters"]) == 2
    cluster_of = {p["abstract"]: p["cluster"] for p in points}
    assert len({cluster_of[t] for t in COOLING}) == 1
    assert {cluster_of[t] for t in CHARGING}.isdisjoint({cluster_of[COOLING[0]]})
    closest = [p["abstract"] for p in points if p["closest"]]
    assert len(closest) == 5 and set(closest) <= set(COOLING)
    assert body["invention"]["label"] == "Your invention"
    assert all(-1.0001 <= p["x"] <= 1.0001 and -1.0001 <= p["y"] <= 1.0001 for p in points)
    assert body["method"] in ("t-SNE", "PCA")


@pytest.mark.db
def test_library_documents_are_placed_on_the_map(api):
    api.post("/documents", files={"file": ("battery.txt", fixture_bytes("battery_patent.txt"))})
    points = api.post("/landscape", json={"keywords": "battery"}).json()["points"]
    mine = [p for p in points if p["kind"] == "library_document"]
    assert [p["label"] for p in mine] == ["battery.txt"] and mine[0]["in_library"]


@pytest.mark.db
def test_too_few_patents_or_an_unreachable_office_are_explained(api):
    api.use(StubSource(COOLING[:3]))
    response = api.post("/landscape", json={"keywords": "battery", "include_library": False})
    assert response.status_code == 422 and "too few" in response.text
    api.use(DownSource([]))
    response = api.post("/landscape", json={"keywords": "wireless charging"})  # not cached
    assert response.status_code == 422 and "could not be reached" in response.text
