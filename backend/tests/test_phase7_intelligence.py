"""Phase 7: family deduplication, similarity ranking, and structured cited comparison."""

from dataclasses import replace
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_patent_sources
from app.core.config import get_settings
from app.database.session import get_db
from app.intelligence.comparison import NOT_STATED, ComparisonBuilder, _lead
from app.intelligence.dedup import group_by_family
from app.intelligence.similarity import rank_by_similarity
from app.llm.providers import FakeLLM, LLMResponse, get_llm
from app.main import create_app
from app.patents.base import PatentQuery, PatentRecord, PatentSearchPage, PatentSource
from app.rag.embeddings import FakeEmbedder, get_embedder
from app.rag.retrieval import RetrievalConfig
from tests.helpers import fixture_bytes


def rec(number, *, family=None, kind=None, title="t", abstract="a", pub=None, source="stub"):
    return PatentRecord(
        source=source,
        publication_number=number,
        country=number[:2],
        kind_code=kind or number[-2:],
        family_id=family,
        title=title,
        abstract=abstract,
        publication_date=pub,
    )


# ------------------------------------------------------------------ dedup (no DB)


def test_application_and_grant_are_one_invention():
    groups = group_by_family([rec("EP1234567A1"), rec("EP1234567B1"), rec("EP7654321A1")])
    assert [g.representative.publication_number for g in groups] == ["EP1234567B1", "EP7654321A1"]
    assert groups[0].also_published_as == ["EP1234567A1"]


def test_family_members_across_countries_prefer_full_text_office():
    groups = group_by_family(
        [
            rec("US10123456B2", family="F1"),
            rec("WO2020123456A1", family="F1"),
            rec("EP3456789A1", family="F1"),
            rec("CN110000000A", family="F2", kind="A"),
        ]
    )
    assert [g.representative.publication_number for g in groups] == ["EP3456789A1", "CN110000000A"]
    assert set(groups[0].also_published_as) == {"US10123456B2", "WO2020123456A1"}


def test_newer_publication_wins_tie():
    groups = group_by_family(
        [
            rec("EP1111111A1", family="F", pub=date(2019, 1, 1)),
            rec("EP2222222A1", family="F", pub=date(2021, 1, 1)),
        ]
    )
    assert groups[0].representative.publication_number == "EP2222222A1"


# ------------------------------------------------------------------ similarity (no DB)


def test_rank_by_similarity_prefers_shared_meaning():
    embedder = FakeEmbedder(256)
    records = [
        rec("XX1A1", title="Coffee machine", abstract="steam brewing espresso"),
        rec("XX2A1", title="Battery cooling", abstract="coolant pump cools battery cells"),
    ]
    ranked = rank_by_similarity(embedder, "battery coolant pump temperature", records)
    assert [s.record.publication_number for s in ranked] == ["XX2A1", "XX1A1"]
    assert ranked[0].similarity > ranked[1].similarity


# ------------------------------------------------------------------ comparison parsing (no DB)


def builder():
    return ComparisonBuilder(None, FakeEmbedder(8), None, RetrievalConfig())


def test_cell_rejects_citations_from_other_sources():
    label_source = {"E1": "S1", "E2": "S1", "E3": "S2"}
    cell = builder()._cell(
        {"text": "Uses a pump [E1]", "citations": ["E1", "E3", "E9"]}, "S1", label_source
    )
    assert (cell.text, cell.citations, cell.invalid) == ("Uses a pump", ["E1"], ["E3", "E9"])
    assert builder()._cell({"text": "Not stated in the evidence."}, "S2", label_source).text == (
        NOT_STATED
    )
    assert builder()._cell("garbage", "S1", label_source).text == NOT_STATED


def test_points_record_which_sources_they_cite():
    points = builder()._points(
        [{"text": "Both cool cells", "citations": ["E1", "E3"]}, {"text": "", "citations": []}],
        {"E1": "S1", "E3": "S2"},
    )
    assert len(points) == 1 and points[0].sources == ["S1", "S2"]


def test_lead_trims_to_first_sentences():
    text = "1. A battery pack comprising cells. " + "More detail here. " * 30
    assert _lead(text).startswith("A battery pack comprising cells.")
    assert len(_lead(text)) <= 225


# ------------------------------------------------------------------ API (DB)


class StubSource(PatentSource):
    """Configurable fake source: returns `records` in the given (API) order."""

    name = "stub"
    label = "Stub"

    def __init__(self, records):
        self.records = records

    def search(self, query: PatentQuery) -> PatentSearchPage:
        return PatentSearchPage("stub", len(self.records), list(self.records), query.keywords)

    def get_details(self, number):
        record = next(r for r in self.records if r.publication_number == number)
        return replace(
            record, claims_text=f"1. A system as described in {record.title}.", has_claims=True
        )


COFFEE = rec("XX0000010A1", title="Espresso machine", abstract="Steam brews coffee quickly.")
BATTERY_A1 = rec(
    "XX0000020A1",
    title="Battery coolant pump control",
    abstract="A controller raises coolant pump speed when cell temperature is high.",
)
BATTERY_B1 = rec(
    "XX0000020B1",
    title="Battery coolant pump control",
    abstract="A controller raises coolant pump speed when cell temperature is high.",
)


class ScriptedLLM(FakeLLM):
    def __init__(self, reply):
        self.reply = reply

    def complete(self, messages, *, temperature, max_tokens):
        return LLMResponse(self.reply, "scripted", 100, 50, 1)


@pytest.fixture
def settings(tmp_path):
    return get_settings().model_copy(
        update={
            "upload_dir": tmp_path,
            "retrieval_min_similarity": 0.1,
            "patent_demo_source": True,
            "agent_planner": "rules",
            "agent_similar_import_limit": 1,
        }
    )


@pytest.fixture
def sources():
    from app.patents.demo import DemoPatentSource

    return {"stub": StubSource([COFFEE, BATTERY_A1, BATTERY_B1]), "demo": DemoPatentSource()}


@pytest.fixture
def api(db_session, settings, sources):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_embedder] = lambda: FakeEmbedder(settings.embedding_dim)
    app.dependency_overrides[get_llm] = lambda: FakeLLM()
    app.dependency_overrides[get_patent_sources] = lambda: sources
    with TestClient(app) as client:
        client.app_ref = app
        yield client


@pytest.fixture
def docs(api):
    battery = api.post(
        "/documents", files={"file": ("battery.txt", fixture_bytes("battery_patent.txt"))}
    )
    wireless = api.post(
        "/documents", files={"file": ("wireless.txt", fixture_bytes("wireless_patent.txt"))}
    )
    return battery.json()["document"], wireless.json()["document"]


@pytest.mark.db
def test_search_merges_families_and_ranks_by_similarity(api, docs):
    battery, _ = docs
    body = api.post(
        "/patents/search",
        json={"keywords": "pump", "sources": ["stub"], "rank_against_document_id": battery["id"]},
    ).json()
    numbers = [r["publication_number"] for r in body["results"]]
    assert numbers == ["XX0000020B1", "XX0000010A1"]  # battery first despite API order
    assert body["results"][0]["also_published_as"] == ["XX0000020A1"]
    assert body["deduplicated"] == 1
    assert body["reference_label"] == "battery.txt"
    assert body["results"][0]["similarity"] > body["results"][1]["similarity"]


@pytest.mark.db
def test_search_without_dedup_or_ranking_keeps_api_order(api):
    body = api.post(
        "/patents/search", json={"keywords": "pump", "sources": ["stub"], "dedup": False}
    ).json()
    assert [r["publication_number"] for r in body["results"]] == [
        "XX0000010A1",
        "XX0000020A1",
        "XX0000020B1",
    ]
    assert all(r["similarity"] is None for r in body["results"])


@pytest.mark.db
def test_extractive_comparison_cites_only_own_sources(api, docs, db_session):
    battery, wireless = docs
    response = api.post(
        "/compare",
        json={"sources": [{"document_id": battery["id"]}, {"document_id": wireless["id"]}]},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    table = body["comparison"]
    assert body["pipeline"] == "comparison" and table["mode"] == "extractive"
    owner = table["label_source"]
    for aspect, row in table["cells"].items():
        for source_key, cell in row.items():
            assert all(owner[label] == source_key for label in cell["citations"]), aspect
    assert table["metrics"]["cross_source_citations"] == 0
    assert table["metrics"]["cell_coverage"] == 1.0
    assert table["cells"]["main_claim"]["S1"]["text"].startswith("A battery thermal management")
    assert table["differences"]
    cell_labels = {
        lbl for row in table["cells"].values() for c in row.values() for lbl in c["citations"]
    }
    cited = {e["label"] for e in body["evidence"] if e["cited"]}
    assert cell_labels <= cited  # evidence used in table cells is marked as cited
    assert "gather evidence" in body["metrics"]["timings_ms"]
    # stored like any run
    again = api.get(f"/runs/{body['run_id']}").json()
    assert again["comparison"]["sources"] == table["sources"]


@pytest.mark.db
def test_compare_by_publication_number_imports_it(api, docs):
    battery, _ = docs
    body = api.post(
        "/compare",
        json={"sources": [{"document_id": battery["id"]}, {"publication_number": "XX0000001A1"}]},
    ).json()
    assert [s["label"] for s in body["comparison"]["sources"]] == ["battery.txt", "XX0000001A1"]
    assert "XX0000001A1" in {p["publication_number"] for p in api.get("/patents").json()}


@pytest.mark.db
def test_llm_comparison_flags_cross_source_and_fabricated_citations(api, docs):
    battery, wireless = docs
    reply = (
        '{"cells": {"technical_field": {"S1": {"text": "Battery cooling", "citations": ["E1"]},'
        ' "S2": {"text": "Wireless charging", "citations": ["E1", "E99"]}}},'
        ' "similarities": [{"text": "Both have controllers", "citations": ["E1"]}],'
        ' "differences": [{"text": "Different fields", "citations": ["E1"]}]}'
    )
    api.app_ref.dependency_overrides[get_llm] = lambda: ScriptedLLM(reply)
    body = api.post(
        "/compare",
        json={
            "mode": "llm",
            "sources": [{"document_id": battery["id"]}, {"document_id": wireless["id"]}],
        },
    ).json()
    table = body["comparison"]
    assert table["mode"] == "llm"
    s2 = table["cells"]["technical_field"]["S2"]
    assert s2["citations"] == [] and s2["invalid"] == ["E1", "E99"]
    assert table["metrics"]["cross_source_citations"] == 1  # E1 belongs to S1
    assert table["metrics"]["fabricated_citations"] == 1  # E99 does not exist
    assert table["metrics"]["one_sided_similarities"] == 1
    assert table["cells"]["problem"]["S1"]["text"] == NOT_STATED  # aspect omitted by LLM


@pytest.mark.db
def test_unusable_llm_output_falls_back_to_extractive(api, docs):
    battery, wireless = docs
    api.app_ref.dependency_overrides[get_llm] = lambda: ScriptedLLM("Sorry, I can't do JSON.")
    body = api.post(
        "/compare",
        json={
            "mode": "llm",
            "sources": [{"document_id": battery["id"]}, {"document_id": wireless["id"]}],
        },
    ).json()
    assert body["comparison"]["mode"] == "extractive_fallback"
    assert "no JSON" in body["comparison"]["fallback_reason"]


@pytest.mark.db
def test_compare_validation(api, docs):
    battery, _ = docs
    one = api.post("/compare", json={"sources": [{"document_id": battery["id"]}]})
    assert one.status_code == 422
    same = api.post(
        "/compare",
        json={"sources": [{"document_id": battery["id"]}, {"document_id": battery["id"]}]},
    )
    assert same.status_code == 422
    ambiguous = api.post(
        "/compare",
        json={
            "sources": [
                {"document_id": battery["id"], "publication_number": "XX0000001A1"},
                {"document_id": battery["id"]},
            ]
        },
    )
    assert ambiguous.status_code == 422


@pytest.mark.db
def test_agent_imports_most_similar_candidate_not_first(api, docs, sources):
    sources.pop("demo")
    body = api.post(
        "/ask", json={"question": "Find patents similar to my battery thermal management invention"}
    ).json()
    imported = [s for s in body["steps"] if s["tool_name"] == "get_patent_details"]
    assert len(imported) == 1
    assert "XX0000020B1" in imported[0]["output_summary"]  # battery family, not the coffee one
    search = next(s for s in body["steps"] if s["tool_name"] == "search_patents")
    assert "family duplicates merged" in search["output_summary"]
    assert "ranked by similarity" in search["output_summary"]
