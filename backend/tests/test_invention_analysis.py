"""Invention analysis: feature extraction, candidate ranking, verified feature chart."""

import pytest

from app.core.config import PROJECT_ROOT, get_settings
from app.core.errors import ValidationFailedError
from app.invention.analysis import DISCLOSED, InventionAnalyzer
from app.invention.features import claim_elements, extract_features, grounding
from app.invention.report import to_markdown
from app.llm.providers import FakeLLM, LLMResponse
from app.models import AgentRun
from app.patents.demo import DemoPatentSource
from app.rag.embeddings import FakeEmbedder
from app.services.documents import DocumentService
from app.verification.verifiers import LexicalVerifier

CORPUS = PROJECT_ROOT / "experiments" / "datasets" / "dev" / "corpus"
BATTERY_CLAIM = (
    "1. A battery thermal management system comprising: a plurality of battery cells; a "
    "temperature sensor attached to each battery cell; a coolant pump configured to "
    "circulate a liquid coolant through cooling channels adjacent to the battery cells; and "
    "a controller configured to estimate a core temperature of each cell and to adjust a "
    "speed of the coolant pump based on the estimated core temperatures."
)


class ScriptedLLM(FakeLLM):
    def __init__(self, reply: str):
        self.reply = reply

    def complete(self, messages, *, temperature, max_tokens):
        return LLMResponse(self.reply, "scripted", 20, 20, 1)


# ------------------------------------------------------------------ features (no database)


def test_claim_elements_become_features():
    features = extract_features(BATTERY_CLAIM, llm=None)
    assert [f.origin for f in features] == ["claim_element"] * 4
    assert features[1].text == "a temperature sensor attached to each battery cell"
    assert features[1].hypothesis == "There is a temperature sensor attached to each battery cell."
    assert features[3].hypothesis.startswith("There is a controller")  # "and" removed


def test_claim_elements_stop_at_the_next_claim():
    text = "1. A pad comprising: a coil wound flat; an inverter driving it.\n2. The pad of claim 1."
    assert claim_elements(text) == ["a coil wound flat", "an inverter driving it."]


def test_llm_features_must_be_grounded_in_the_description():
    description = (
        "My charger measures the quality factor of its coil before charging. It stops "
        "charging when a metal object lowers the quality factor below a threshold."
    )
    reply = (
        '["The charger measures the quality factor of the coil before charging.", '
        '"Charging stops when a metal object lowers the quality factor below a threshold.", '
        '"The device uses a neural network trained on thermal camera images."]'  # invented
    )
    features = extract_features(description, ScriptedLLM(reply))
    assert [f.origin for f in features] == ["llm", "llm"]
    assert all("neural network" not in f.text for f in features)
    assert grounding("neural network trained on thermal camera images", description) < 0.5


def test_unusable_llm_output_falls_back_to_sentences():
    description = (
        "The sensor array measures each cell temperature. A pump moves coolant faster when "
        "any cell gets hot. The housing is sealed against water."
    )
    features = extract_features(description, ScriptedLLM("Sure! Here are some features."))
    assert [f.origin for f in features] == ["sentence"] * 3


# ------------------------------------------------------------------ analysis (database)

pytestmark_db = pytest.mark.db


@pytest.fixture
def corpus(db_session, tmp_path):
    settings = get_settings().model_copy(
        update={"upload_dir": tmp_path, "retrieval_min_similarity": 0.1}
    )
    embedder = FakeEmbedder(settings.embedding_dim)
    service = DocumentService(db_session, settings, embedder)
    docs = {}
    for name in ("battery_patent.txt", "wireless_patent.txt", "immersion_cooling.txt"):
        document, _ = service.upload(name, (CORPUS / name).read_bytes())
        docs[name] = document
    return settings, embedder, docs


def analyzer(db_session, corpus, sources=None):
    settings, embedder, _ = corpus
    return InventionAnalyzer(
        db_session, settings, embedder, FakeLLM(), sources or {}, verifier=LexicalVerifier()
    )


@pytestmark_db
def test_patent_finds_itself_with_every_feature_disclosed(db_session, corpus):
    run = analyzer(db_session, corpus).analyze(BATTERY_CLAIM, use_patent_search=False)
    result = run.answer
    top = result["candidates"][0]
    assert top["label"] == "battery_patent.txt"
    assert top["disclosed"] == len(result["features"])  # its own claim, element by element
    cell = next(c for c in result["cells"] if c["candidate"] == top["key"])
    assert cell["verdict"] == DISCLOSED and cell["passage"]["location"].startswith("battery")

    stored = db_session.get(AgentRun, run.id)
    assert stored.pipeline == "invention_analysis" and stored.status == "succeeded"
    assert [t.tool_name for t in stored.tool_calls] == [
        "extract_features",
        "rank_candidates",
        "build_feature_chart",
    ]
    assert stored.retrieval_results and all(r.cited_in_answer for r in stored.retrieval_results)


@pytestmark_db
def test_own_document_is_excluded_from_candidates(db_session, corpus):
    battery = corpus[2]["battery_patent.txt"]
    run = analyzer(db_session, corpus).analyze(document_id=battery.id, use_patent_search=False)
    labels = [c["label"] for c in run.answer["candidates"]]
    assert "battery_patent.txt" not in labels and labels  # other documents remain
    assert run.answer["own_document"]["label"] == "battery_patent.txt"
    assert run.answer["features"][0]["origin"] == "claim_element"  # from the draft's claim 1


@pytestmark_db
def test_patent_search_imports_external_candidates(db_session, corpus):
    run = analyzer(db_session, corpus, {"demo": DemoPatentSource()}).analyze(
        BATTERY_CLAIM, use_patent_search=True, max_candidates=6
    )
    assert run.answer["imported_patents"]  # synthetic demo patents were fetched and indexed
    assert any(c["kind"] == "patent" for c in run.answer["candidates"])
    assert run.answer["steps"][1]["tool"] == "search_patents"


@pytestmark_db
def test_report_and_validation(db_session, corpus):
    run = analyzer(db_session, corpus).analyze(BATTERY_CLAIM, use_patent_search=False)
    report = to_markdown(run.answer)
    assert "not an assessment of novelty" in report
    assert "| Feature | D1 |" in report and "## Evidence" in report
    with pytest.raises(ValidationFailedError):
        analyzer(db_session, corpus).analyze("A pump.", use_patent_search=False)


@pytestmark_db
def test_selfcheck_uses_first_independent_claim_when_claim_1_is_cancelled(db_session, corpus):
    from app.evaluation.selfcheck import first_independent_claim

    settings, embedder, docs = corpus
    text = (
        "TITLE\nContinuation patent\n\nCLAIMS\n\n1.-14. (canceled)\n\n"
        "15. A system for detecting an object, comprising: a resonant circuit; and a "
        "controller.\n\n16. The system of claim 15, wherein the circuit is an L-C circuit.\n"
    )
    document, _ = DocumentService(db_session, settings, embedder).upload(
        "continuation.txt", text.encode()
    )
    assert first_independent_claim(db_session, document).startswith("15. A system")
    battery = first_independent_claim(db_session, docs["battery_patent.txt"])
    assert battery.startswith("1.")


@pytestmark_db
def test_selfcheck_on_the_dev_corpus(db_session, corpus, tmp_path):
    import json

    from app.evaluation.selfcheck import SelfCheckConfig, run_selfcheck

    _, _, docs = corpus
    config = SelfCheckConfig(
        name="sc",
        dataset=PROJECT_ROOT / "experiments" / "datasets" / "dev" / "dataset.yaml",
        domains={"battery": "battery", "wireless": "wireless", "immersion": "battery"},
    )
    ids = {
        "battery": docs["battery_patent.txt"].id,
        "wireless": docs["wireless_patent.txt"].id,
        "immersion": docs["immersion_cooling.txt"].id,
    }
    out = run_selfcheck(
        db_session, analyzer(db_session, corpus), config, ids, tmp_path, log=lambda _: None
    )
    summary = json.loads((out / "summary.json").read_text())
    assert summary["kind"] == "selfcheck" and summary["dataset"]["items"] == 3
    assert summary["results"]["self_found_at_1"]["mean"] == 1.0  # each finds itself first
    rows = [json.loads(line) for line in (out / "rows.jsonl").open()]
    battery = next(r for r in rows if r["doc"] == "battery")
    assert battery["top_candidates"][0] == "immersion_cooling.txt"  # nearest neighbour
    assert battery["same_domain_at_1"] == 1.0
    assert "Own patent ranked first" in (out / "report.md").read_text()


@pytestmark_db
def test_invention_api(db_session, corpus):
    from fastapi.testclient import TestClient

    from app.api.deps import get_patent_sources
    from app.database.session import get_db
    from app.llm.providers import get_llm
    from app.main import create_app
    from app.rag.embeddings import get_embedder

    settings, embedder, _ = corpus
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_embedder] = lambda: embedder
    app.dependency_overrides[get_llm] = lambda: FakeLLM()
    app.dependency_overrides[get_patent_sources] = lambda: {}
    api = TestClient(app)

    created = api.post("/analysis/invention", json={"description": BATTERY_CLAIM})
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["status"] == "succeeded"
    assert body["result"]["candidates"][0]["label"] == "battery_patent.txt"

    listed = api.get("/analysis/invention").json()
    assert listed[0]["run_id"] == body["run_id"] and listed[0]["features"] == 4
    assert api.get(f"/analysis/invention/{body['run_id']}").json()["status"] == "succeeded"

    report = api.get(f"/analysis/invention/{body['run_id']}/report.md")
    assert report.headers["content-type"].startswith("text/markdown")
    assert "attachment" in report.headers["content-disposition"]
    assert "## Feature chart" in report.text

    assert api.post("/analysis/invention", json={}).status_code == 422
    assert api.get("/analysis/invention/00000000-0000-0000-0000-000000000000").status_code == 404
