"""Phase 14: demo mode plants a false sentence in the first draft; the checker should
catch it and the answer is rewritten. A miss must be reported as a miss."""

import pytest

from app.agents import demo_injection
from app.agents.demo_injection import find_planted, plant_false_fact
from app.llm.providers import FakeLLM
from app.rag.generation import parse_answer
from app.verification.verifiers import SUPPORTED, Judgement, Verifier
from tests.test_phase8_verification_api import QUESTION, make_api

LABELS = {"E1", "E2", "E3"}


def plant(text):
    return plant_false_fact(parse_answer(text, LABELS), LABELS)


def test_a_number_is_changed_but_not_claim_numbers_or_years():
    parsed, injection = plant(
        "The pump of claim 3 starts in 2019 versions [E3]. "
        "The controller keeps every cell below 45 °C during fast charging [E1]."
    )
    assert injection.kind == "changed_number"
    assert injection.original.startswith("The controller keeps every cell below 45")
    assert "below 135 °C" in injection.planted and injection.planted in parsed.text
    assert "claim 3" in parsed.text and "2019" in parsed.text


def test_a_relation_is_reversed_when_there_is_no_number():
    _, injection = plant(
        "The pump speed increases when the core temperature exceeds the threshold [E1]."
    )
    assert injection.kind == "reversed_relation"
    assert "speed decreases when" in injection.planted


def test_an_invented_detail_is_added_with_a_real_citation():
    parsed, injection = plant(
        "A patent claim defines the scope of the protection that is granted [E1]. "
        "Claims are usually written as one long sentence by the attorney [E2]."
    )
    assert injection.kind == "invented_detail" and injection.original is None
    assert injection.planted.endswith("[E2].") and injection.planted in parsed.text
    assert len(parsed.sentences) == 3


def test_nothing_is_planted_in_an_answer_without_citations():
    assert plant("INSUFFICIENT_EVIDENCE: nothing found.") is None


@pytest.mark.db
def test_planted_sentence_is_caught_and_rewritten_away(db_session, tmp_path, monkeypatch):
    # Force the invented-detail strategy: the word-overlap checker used in tests
    # reliably rejects it (it cannot see changed numbers; the NLI checker can).
    monkeypatch.setattr(demo_injection, "_change_number", lambda s: None)
    monkeypatch.setattr(demo_injection, "_flip", lambda s: None)
    api = make_api(db_session, tmp_path, FakeLLM())
    body = api.post("/ask", json={"question": QUESTION, "inject_false_fact": True}).json()

    outcome = body["demo_injection"]
    assert outcome["kind"] == "invented_detail" and outcome["caught"] is True
    assert outcome["verdict"] == "unsupported" and outcome["in_final_answer"] is False
    draft, final = body["verification_attempts"]
    assert outcome["planted"] in draft["answer_text"] and final["kept"] is True
    assert outcome["planted"] not in body["answer"]


class ApprovesEverything(Verifier):
    """A checker that misses every problem, standing in for a miss by the real one."""

    name = "approves_everything"

    def judge(self, claims, passages_per_claim):
        return [Judgement(SUPPORTED, 0.99, 0, "looks fine") for _ in claims]


@pytest.mark.db
def test_a_miss_is_reported_as_a_miss(db_session, tmp_path, monkeypatch):
    import app.agents.graph as graph

    monkeypatch.setattr(graph, "build_verifier", lambda *a, **k: ApprovesEverything())
    api = make_api(db_session, tmp_path, FakeLLM())
    body = api.post("/ask", json={"question": QUESTION, "inject_false_fact": True}).json()
    outcome = body["demo_injection"]
    assert outcome["checked"] is True and outcome["caught"] is False
    assert outcome["in_final_answer"] is True  # shown, and the page says it was missed
    assert body["verification_attempts"] == []  # nothing flagged, nothing rewritten


@pytest.mark.db
def test_demo_mode_can_be_switched_off(db_session, tmp_path):
    api = make_api(db_session, tmp_path, FakeLLM(), demo_injection_enabled=False)
    response = api.post("/ask", json={"question": QUESTION, "inject_false_fact": True})
    assert response.status_code == 422


@pytest.mark.db
def test_normal_questions_are_untouched(db_session, tmp_path):
    body = (
        make_api(db_session, tmp_path, FakeLLM()).post("/ask", json={"question": QUESTION}).json()
    )
    assert body["demo_injection"] is None


def test_find_planted_ignores_citations():
    class Claim:
        text = "It also requires a liquid-nitrogen stage [E2]."

    injection = demo_injection.Injection(
        "invented_detail", "It also requires a liquid-nitrogen stage [E1].", None
    )
    assert find_planted([Claim()], injection) is not None


def test_a_flip_never_repeats_a_word_already_in_the_sentence():
    from app.agents.demo_injection import _flip

    assert _flip("It works in both heating and cooling modes.") is None
    assert _flip("It runs in heating and cooling modes and increases efficiency.") == (
        "It runs in heating and cooling modes and decreases efficiency."
    )
