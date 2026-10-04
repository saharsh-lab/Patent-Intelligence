"""Phase 3 (with database): hybrid retrieval and the /ask pipeline end to end."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import get_settings
from app.core.errors import ExternalServiceError
from app.database.session import get_db
from app.llm.providers import FakeLLM, LLMResponse, get_llm
from app.main import create_app
from app.models import AgentRun, RetrievalResult
from app.rag.embeddings import FakeEmbedder, get_embedder
from app.rag.reranker import FakeReranker
from app.rag.retrieval import RetrievalConfig, retrieve
from tests.helpers import fixture_bytes

pytestmark = pytest.mark.db

BATTERY = fixture_bytes("battery_patent.txt")
WIRELESS = fixture_bytes("wireless_patent.txt")


class ScriptedLLM(FakeLLM):
    """Returns a fixed reply and records how often it was called."""

    def __init__(self, reply: str | None = None, error: Exception | None = None):
        self.reply, self.error, self.calls = reply, error, 0

    def complete(self, messages, *, temperature, max_tokens):
        self.calls += 1
        if self.error:
            raise self.error
        if self.reply is None:
            return super().complete(messages, temperature=temperature, max_tokens=max_tokens)
        return LLMResponse(self.reply, "scripted", 50, 10, 1)


@pytest.fixture
def test_settings(tmp_path):
    return get_settings().model_copy(
        update={"upload_dir": tmp_path, "retrieval_min_similarity": 0.2}
    )


@pytest.fixture
def llm():
    return ScriptedLLM()


@pytest.fixture
def api(db_session, test_settings, llm):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_embedder] = lambda: FakeEmbedder(test_settings.embedding_dim)
    app.dependency_overrides[get_llm] = lambda: llm
    with TestClient(app) as client:
        yield client


@pytest.fixture
def docs(api):
    battery = api.post("/documents", files={"file": ("battery.txt", BATTERY)}).json()
    wireless = api.post("/documents", files={"file": ("wireless.txt", WIRELESS)}).json()
    return {"battery": battery["document"], "wireless": wireless["document"]}


def ask(api, question, **extra):
    # Phase 3 tests cover the baseline pipeline; the agent is tested in test_phase6_*
    response = api.post("/ask", json={"question": question, "pipeline": "baseline", **extra})
    assert response.status_code == 200, response.text
    return response.json()


# ------------------------------------------------------------------ retrieval


def test_hybrid_combines_vector_and_keyword(db_session, docs, test_settings):
    embedder = FakeEmbedder(test_settings.embedding_dim)
    question = "Which sensor is bonded to the casing?"
    hybrid = retrieve(db_session, question, embedder=embedder, config=RetrievalConfig(top_k=5))
    assert {p.method for p in hybrid.passages} & {"hybrid"}
    assert "thermistor" in hybrid.passages[0].chunk.text
    assert [p.rank for p in hybrid.passages] == [1, 2, 3, 4, 5]

    vector_only = retrieve(
        db_session, question, embedder=embedder, config=RetrievalConfig(mode="vector")
    )
    keyword_only = retrieve(
        db_session, question, embedder=embedder, config=RetrievalConfig(mode="keyword")
    )
    assert {p.method for p in vector_only.passages} == {"vector"}
    assert {p.method for p in keyword_only.passages} == {"keyword"}


def test_any_word_keyword_matching_handles_questions(db_session, docs, test_settings):
    # Requiring ALL words of a natural question would match nothing
    result = retrieve(
        db_session,
        "What happens to a coin on the charging pad?",
        embedder=FakeEmbedder(test_settings.embedding_dim),
        config=RetrievalConfig(mode="keyword"),
    )
    assert result.keyword_matches > 0


def test_reranker_reorders_and_records_scores(db_session, docs, test_settings):
    result = retrieve(
        db_session,
        "quality factor transmitter coil",
        embedder=FakeEmbedder(test_settings.embedding_dim),
        config=RetrievalConfig(top_k=3),
        reranker=FakeReranker(),
    )
    scores = [p.rerank_score for p in result.passages]
    assert scores == sorted(scores, reverse=True)
    assert "rerank" in result.timings_ms


# ------------------------------------------------------------------ /ask


def test_ask_returns_cited_answer_and_records_run(api, docs, db_session):
    body = ask(api, "How is the core temperature of each cell estimated?")
    assert body["status"] == "succeeded"
    assert body["pipeline"] == "baseline_rag"
    assert "[E1]" in body["answer"]
    assert body["metrics"]["citation_coverage"] == 1.0
    assert body["summary"]["sources_searched"] == ["Uploaded documents"]
    assert body["summary"]["passages_cited"] >= 1
    cited = [e for e in body["evidence"] if e["cited"]]
    assert cited[0]["label"] == "E1" and cited[0]["source_label"] in ("battery.txt", "wireless.txt")

    run = db_session.get(AgentRun, body["run_id"])
    assert run.config["prompt_version"].startswith("grounded-answer")
    assert run.config["retrieval"]["mode"] == "hybrid"
    assert run.prompt_tokens > 0 and run.latency_ms is not None
    rows = db_session.scalars(
        select(RetrievalResult).where(RetrievalResult.agent_run_id == run.id)
    ).all()
    assert len(rows) == len(body["evidence"])
    assert sum(r.cited_in_answer for r in rows) == body["summary"]["passages_cited"]


def test_ask_without_documents_skips_llm(api, llm):
    body = ask(api, "How is the core temperature estimated?")
    assert body["status"] == "insufficient_evidence"
    assert body["summary"]["llm_called"] is False
    assert llm.calls == 0


def test_ask_off_topic_question_is_stopped_before_llm(api, docs, llm, test_settings):
    body = ask(api, "Who painted the Mona Lisa?")
    assert body["status"] == "insufficient_evidence"
    assert "similar" in body["insufficient_reason"] or "keywords" in body["insufficient_reason"]
    assert llm.calls == 0


def test_model_reported_insufficient_evidence(api, docs, llm):
    llm.reply = "INSUFFICIENT_EVIDENCE: The filing date is not in the passages."
    body = ask(api, "When was the battery patent filed?")
    assert body["status"] == "insufficient_evidence"
    assert body["insufficient_reason"] == "The filing date is not in the passages."
    assert body["summary"]["llm_called"] is True


def test_fabricated_citations_are_flagged(api, docs, llm):
    llm.reply = "The pump is variable-speed [E1]. It was made by Acme Corp [E42]."
    body = ask(api, "What kind of pump is used for the coolant?")
    assert body["metrics"]["invalid_citations"] == ["E42"]
    assert "[E42]" not in body["answer"]
    assert body["metrics"]["citation_coverage"] == 0.5


def test_llm_failure_records_failed_run(api, docs, llm, db_session):
    llm.error = ExternalServiceError("The language model service is unavailable.")
    response = api.post(
        "/ask", json={"question": "How is the coolant pumped?", "pipeline": "baseline"}
    )
    assert response.status_code == 502
    runs = api.get("/runs").json()
    assert runs[0]["status"] == "failed"
    detail = api.get(f"/runs/{runs[0]['run_id']}").json()
    assert detail["error_message"] == "The language model service is unavailable."


def test_document_scoping(api, docs):
    body = ask(
        api, "What does the detection circuit measure?", document_ids=[docs["battery"]["id"]]
    )
    assert all(e["source_label"] == "battery.txt" for e in body["evidence"])


def test_request_overrides_are_applied_and_recorded(api, docs, db_session):
    body = ask(api, "How is the coolant pumped?", top_k=2, retrieval_mode="vector", rerank=False)
    assert len(body["evidence"]) <= 2
    assert {e["method"] for e in body["evidence"]} == {"vector"}
    run = db_session.get(AgentRun, body["run_id"])
    assert run.config["retrieval"]["top_k"] == 2 and run.config["reranker"] is None


def test_run_history(api, docs):
    first = ask(api, "How is the coolant pumped?")
    ask(api, "What does claim 4 specify?")
    runs = api.get("/runs").json()
    # (order is not checked: inside one test transaction both runs share a timestamp)
    assert {r["question"] for r in runs} == {
        "What does claim 4 specify?",
        "How is the coolant pumped?",
    }
    assert api.get(f"/runs/{first['run_id']}").json()["answer"] == first["answer"]


def test_conversation_filter(api, docs):
    conversation = "8b1a6f0e-0000-4000-8000-000000000001"
    ask(api, "How is the coolant pumped?", conversation_id=conversation)
    ask(api, "What does claim 4 specify?")
    runs = api.get("/runs", params={"conversation_id": conversation}).json()
    assert [r["question"] for r in runs] == ["How is the coolant pumped?"]


def test_ask_validation(api):
    assert api.post("/ask", json={"question": "hi"}).status_code == 422
    assert api.post("/ask", json={"question": "valid question", "top_k": 99}).status_code == 422
    assert api.post("/ask", json={"question": "x" * 2001}).status_code == 422
