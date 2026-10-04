"""Phase 8 (with database): claim verification, grounding scores, and regeneration."""

import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.deps import get_patent_sources
from app.core.config import get_settings
from app.database.session import get_db
from app.llm.providers import FakeLLM, get_llm
from app.main import create_app
from app.models import AgentRun, ClaimVerification, RetrievalResult
from app.rag.embeddings import FakeEmbedder, get_embedder
from tests.helpers import fixture_bytes

pytestmark = pytest.mark.db

HALLUCINATION = "The battery pack is powered by a small nuclear reactor mounted on the roof"


class HallucinatingLLM(FakeLLM):
    """Answers like FakeLLM (quotes evidence) but adds an invented sentence on chosen calls."""

    def __init__(self, hallucinate_on: set[int]):
        self.hallucinate_on = hallucinate_on
        self.calls: list[str] = []

    def complete(self, messages, *, temperature, max_tokens):
        prompt = "\n".join(m.content for m in messages)
        self.calls.append(prompt)
        response = super().complete(messages, temperature=temperature, max_tokens=max_tokens)
        if len(self.calls) in self.hallucinate_on and "[E1]" in response.text:
            response.text += f" {HALLUCINATION} [E1]."
        return response


def make_api(db_session, tmp_path, llm, **overrides):
    settings = get_settings().model_copy(
        update={
            "upload_dir": tmp_path,
            "retrieval_min_similarity": 0.1,
            "agent_planner": "rules",
            "verifier_method": "lexical",
            **overrides,
        }
    )
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_embedder] = lambda: FakeEmbedder(settings.embedding_dim)
    app.dependency_overrides[get_llm] = lambda: llm
    app.dependency_overrides[get_patent_sources] = lambda: {}
    client = TestClient(app)
    client.post("/documents", files={"file": ("battery.txt", fixture_bytes("battery_patent.txt"))})
    return client


QUESTION = "How does the controller decide when to increase the coolant pump speed?"


def ask(api, **extra):
    response = api.post("/ask", json={"question": QUESTION, **extra})
    assert response.status_code == 200, response.text
    return response.json()


def test_baseline_reports_verification_and_stores_claims(db_session, tmp_path):
    api = make_api(db_session, tmp_path, FakeLLM())
    body = ask(api, pipeline="baseline")
    verification = body["verification"]
    assert verification["method"] == "lexical"
    assert verification["claims"] and body["grounding_score"] == verification["grounding_score"]
    assert body["grounding_score"] == 1.0  # FakeLLM quotes its evidence verbatim

    rows = db_session.scalars(
        select(ClaimVerification).where(ClaimVerification.agent_run_id == body["run_id"])
    ).all()
    assert len(rows) == len(verification["claims"])
    result_id = rows[0].evidence_ids[0]["retrieval_result_id"]
    assert db_session.get(RetrievalResult, result_id).agent_run_id.hex == body["run_id"].replace(
        "-", ""
    )


def test_hallucination_is_detected_and_regenerated_away(db_session, tmp_path):
    llm = HallucinatingLLM(hallucinate_on={1})
    api = make_api(db_session, tmp_path, llm)
    body = ask(api)

    attempts = body["verification_attempts"]
    assert len(attempts) == 2
    assert attempts[0]["counts"]["unsupported"] >= 1 and attempts[0]["grounding_score"] < 0.8
    assert attempts[1]["kept"] is True and attempts[1]["grounding_score"] == 1.0
    assert HALLUCINATION not in body["answer"]
    assert body["grounding_score"] == 1.0
    # the regeneration prompt named the unsupported statement
    assert "NOT supported" in llm.calls[1] and HALLUCINATION in llm.calls[1]
    assert any(k.startswith("regenerate") for k in body["metrics"]["timings_ms"])


def test_worse_regeneration_is_not_kept(db_session, tmp_path):
    class GetsWorse(HallucinatingLLM):
        def complete(self, messages, *, temperature, max_tokens):
            response = super().complete(messages, temperature=temperature, max_tokens=max_tokens)
            if len(self.calls) == 2:  # regenerated answer: entirely invented
                response.text = (
                    f"{HALLUCINATION} [E1]. It also runs on steam turbines imported from Mars [E1]."
                )
            return response

    api = make_api(db_session, tmp_path, GetsWorse(hallucinate_on={1}))
    body = ask(api)
    attempts = body["verification_attempts"]
    assert [a["kept"] for a in attempts] == [True, False]
    assert body["grounding_score"] == attempts[0]["grounding_score"]


@pytest.mark.parametrize("overrides", [{"verify_mode": "report"}, {"max_regenerations": 0}])
def test_no_regeneration_when_disabled(db_session, tmp_path, overrides):
    llm = HallucinatingLLM(hallucinate_on={1})
    api = make_api(db_session, tmp_path, llm, **overrides)
    body = ask(api)
    assert body["verification_attempts"] == [] and len(llm.calls) == 1
    unsupported = [c for c in body["verification"]["claims"] if c["verdict"] == "unsupported"]
    assert [c["text"] for c in unsupported] == [f"{HALLUCINATION}."]


def test_baseline_never_regenerates(db_session, tmp_path):
    llm = HallucinatingLLM(hallucinate_on={1})
    api = make_api(db_session, tmp_path, llm)
    body = ask(api, pipeline="baseline")
    assert len(llm.calls) == 1 and body["grounding_score"] < 1.0


def test_verification_off(db_session, tmp_path):
    api = make_api(db_session, tmp_path, FakeLLM(), verify_mode="off")
    body = ask(api)
    assert body["verification"] is None and body["grounding_score"] is None


def test_comparison_cells_are_verified(db_session, tmp_path):
    api = make_api(db_session, tmp_path, FakeLLM())
    wireless = api.post(
        "/documents", files={"file": ("w.txt", fixture_bytes("wireless_patent.txt"))}
    )
    docs = {d["filename"]: d["id"] for d in api.get("/documents").json()}
    body = api.post(
        "/compare",
        json={
            "sources": [
                {"document_id": docs["battery.txt"]},
                {"document_id": wireless.json()["document"]["id"]},
            ]
        },
    ).json()
    claims = body["verification"]["claims"]
    assert claims and all(re.match(r"cell:\w+:S[12]", c["location"]) for c in claims)
    assert body["grounding_score"] >= 0.9  # extractive cells quote their own passages
    run = db_session.get(AgentRun, body["run_id"])
    assert len(run.claim_verifications) == len(claims)
