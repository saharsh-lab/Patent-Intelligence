"""The Checker upgrade: the exact wrong words, contradicted vs not found, the false-premise
note, fixing a sentence, checking any text, and the checker's record."""

import pytest

from app.agents.premise import acknowledged, instruction, unstated_terms
from app.llm.providers import FakeLLM
from app.rag.generation import parse_answer
from app.services import answering
from app.services.fixes import _without
from app.verification.checker import ClaimResult, claims_from_answer, explain
from app.verification.issues import find_issues
from app.verification.verifiers import SUPPORTED, UNSUPPORTED, Judgement, Verifier
from tests.test_phase8_verification_api import make_api

PASSAGE = (
    "Source: battery.txt, claim 3.\nThe controller keeps the coolant below 40 °C and the "
    "resistance of the coil increases when the pump 120 runs."
)


def kinds(statement, passage=PASSAGE):
    return [(i.kind, i.text, i.passage_says, i.conflict) for i in find_issues(statement, passage)]


# ------------------------------------------------------------------ the wrong words


def test_a_changed_number_is_marked_with_what_the_passage_says():
    assert kinds("The controller keeps the coolant below 120 degrees Celsius [E1].") == [
        ("number", "120 degrees", "40 °C", True)
    ]


def test_a_reversed_direction_is_a_contradiction():
    assert kinds("The resistance of the coil decreases when the pump runs.") == [
        ("direction", "decreases", "increases", True)
    ]


def test_an_added_detail_is_marked_but_is_not_a_contradiction():
    found = kinds("A PID controller keeps the coolant below 40 °C.")
    assert found == [("unstated", "PID", None, False)]


def test_neighbouring_unstated_words_are_one_phrase():
    found = kinds("The controller keeps the coolant below 40 °C using a neural network.")
    assert ("unstated", "neural network", None, False) in found


def test_a_statement_about_something_else_is_not_marked_word_by_word():
    assert kinds("Solar panels charge the vehicle overnight through a wireless pad.") == []


def test_reference_numerals_and_units_are_not_marked():
    assert kinds("The pump 120 keeps the coolant below 40 degrees Celsius.") == []


def claim(text, verdict, cited=(), supporting=()):
    return ClaimResult(0, text, list(cited), verdict, 0.1, "", list(supporting))


def test_explain_marks_flagged_statements_only():
    premise = {"E1": PASSAGE, "E2": "Source: other.txt.\nSolar panels on the roof."}
    wrong = claim("The coolant stays below 120 degrees Celsius.", UNSUPPORTED, cited=["E1"])
    right = claim("The coolant stays below 40 °C.", SUPPORTED, cited=["E1"], supporting=["E1"])
    uncited = claim("The coil resistance increases when a PID controller runs.", UNSUPPORTED)
    explain([wrong, right, uncited], premise)
    assert wrong.contradicts and wrong.issues[0]["passage_says"] == "40 °C"
    assert right.issues == [] and not right.contradicts
    # no citation: explained against the closest passage, and not found (not contradicted)
    assert uncited.closest == "E1" and not uncited.contradicts
    assert {"kind": "unstated", "text": "PID", "passage_says": None, "conflict": False} in (
        uncited.issues
    )


# ------------------------------------------------------------------ false premises

KALMAN = [
    "The state estimate is updated by a Kalman filter from the measured temperature.",
    "Claim 1. A method comprising estimating a cell temperature with a Kalman filter.",
]


def test_terms_the_passages_never_use_are_found():
    question = "Which neural network does the Kalman-filter patent train?"
    assert unstated_terms(question, KALMAN) == ["neural network"]
    assert unstated_terms("How is the cell temperature estimated?", KALMAN) == []
    assert "neural network" in instruction(["neural network"])


def test_the_note_counts_only_when_the_answer_says_so():
    said = "The sources do not mention a neural network. It uses a Kalman filter [E1]."
    assert acknowledged(said, ["neural network"]) == ["neural network"]
    assert acknowledged("It uses a Kalman filter [E1].", ["neural network"]) == []


def test_the_absence_sentence_is_not_checked_as_a_claim():
    text = "The patent does not mention a neural network. It uses a Kalman filter [E1]."
    parsed = parse_answer(text, {"E1"})
    claims, skipped = claims_from_answer(parsed, ["neural network"])
    assert [c.text for c in claims] == ["It uses a Kalman filter."]
    assert skipped == ["The patent does not mention a neural network."]
    # without a premise note nothing changes (the measured pipeline)
    assert len(claims_from_answer(parsed)[0]) == 2


# ------------------------------------------------------------------ removing a sentence


def test_removing_a_sentence_leaves_no_gap_or_empty_list_item():
    assert _without("One [E1]. Two [E2]. Three [E1].", "Two [E2].") == "One [E1]. Three [E1]."
    assert _without("Intro:\n- First [E1].\n- Second [E2].", "Second [E2].") == (
        "Intro:\n- First [E1]."
    )


# ------------------------------------------------------------------ API


TRUE = "The controller samples every thermistor at 10 Hz."
FALSE = "Cooling channels run between the rows of cells and keep them below 90 degrees Celsius."


class FlagsNinety(Verifier):
    """Stands in for the real checker: rejects the sentence with the wrong number."""

    name = "flags_ninety"

    def judge(self, claims, passages_per_claim):
        return [
            Judgement(UNSUPPORTED if "90" in c else SUPPORTED, 0.2 if "90" in c else 0.9, 0, "")
            for c in claims
        ]


@pytest.fixture
def api(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(answering, "build_verifier", lambda *a, **k: FlagsNinety())
    return make_api(db_session, tmp_path, FakeLLM())


def check(api, text):
    response = api.post("/check", json={"text": text})
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.db
def test_checking_a_text_judges_each_sentence_against_its_closest_passages(api):
    body = check(api, f"{TRUE} {FALSE}")
    assert body["pipeline"] == "fact_check" and body["status"] == "succeeded"
    true, false = body["verification"]["claims"]
    assert true["verdict"] == "supported" and true["supporting"] == [true["supporting"][0]]
    assert false["verdict"] == "unsupported" and false["closest"]
    assert false["contradicts"] is True  # the passage it is closest to says 40 °C
    assert any(i["text"] == "90 degrees" for i in false["issues"])
    assert body["grounding_score"] == 0.5
    assert {e["label"] for e in body["evidence"]} >= {true["supporting"][0], false["closest"]}


@pytest.mark.db
def test_a_text_with_nothing_to_check_says_so(api):
    body = check(api, "Hello there. Thanks a lot!")
    assert (
        body["status"] == "insufficient_evidence"
        and "full statement" in (body["insufficient_reason"])
    )


@pytest.mark.db
def test_removing_then_restoring_a_sentence(api):
    body = check(api, f"{TRUE} {FALSE}")
    run, index = body["run_id"], body["verification"]["claims"][1]["index"]

    fixed = api.post(f"/runs/{run}/fix", json={"action": "remove", "claim_index": index}).json()
    assert FALSE not in fixed["answer"] and TRUE in fixed["answer"]
    assert fixed["grounding_score"] == 1.0
    assert [f["action"] for f in fixed["fixes"]] == ["remove"]
    assert len(fixed["verification"]["claims"]) == 1

    again = api.post(f"/runs/{run}/fix", json={"action": "remove", "claim_index": index})
    assert again.status_code == 404  # already gone

    restored = api.post(f"/runs/{run}/fix", json={"action": "restore"}).json()
    assert FALSE in restored["answer"] and restored["fixes"] == []
    assert restored["grounding_score"] == 0.5


@pytest.mark.db
def test_rewriting_a_sentence_from_its_source(api):
    body = check(api, f"{TRUE} {FALSE}")
    run, index = body["run_id"], body["verification"]["claims"][1]["index"]
    fixed = api.post(f"/runs/{run}/fix", json={"action": "rewrite", "claim_index": index})
    assert fixed.status_code == 200, fixed.text
    fixed = fixed.json()
    rewrite = fixed["fixes"][0]
    # FakeLLM quotes the passage, which the checker then backs
    assert rewrite["after"] and rewrite["after"] in fixed["answer"] and FALSE not in fixed["answer"]
    assert rewrite["verdict"] == "supported" and fixed["grounding_score"] == 1.0


@pytest.mark.db
def test_another_users_answer_cannot_be_fixed(api):
    response = api.post(
        "/runs/00000000-0000-0000-0000-000000000000/fix",
        json={"action": "remove", "claim_index": 0},
    )
    assert response.status_code == 404


@pytest.mark.db
def test_the_record_lists_checks_and_answers_with_their_verdicts(api):
    body = check(api, f"{TRUE} {FALSE}")
    api.post("/ask", json={"question": "How often does the controller sample the thermistors?"})
    history = api.get("/checker/history").json()
    kinds_ = {item["kind"] for item in history}
    assert kinds_ == {"check", "answer"}
    item = next(i for i in history if i["run_id"] == body["run_id"])
    assert item["counts"] == {"supported": 1, "partly": 0, "contradicts": 1, "not_found": 0}


class SaysNotMentioned(FakeLLM):
    """Writes the false-premise sentence when the writer is told about one."""

    def __init__(self):
        self.prompts: list[str] = []

    def complete(self, messages, *, temperature, max_tokens):
        prompt = "\n".join(m.content for m in messages)
        self.prompts.append(prompt)
        response = super().complete(messages, temperature=temperature, max_tokens=max_tokens)
        if "The question mentions" in prompt and "[E" in response.text:
            response.text = "The sources do not mention a neural network.\n" + response.text
        return response


@pytest.mark.db
def test_a_false_premise_is_named_and_not_checked(db_session, tmp_path):
    llm = SaysNotMentioned()
    api = make_api(db_session, tmp_path, llm)
    body = api.post(
        "/ask", json={"question": "Which neural network does the battery controller train?"}
    ).json()
    assert any('"neural network"' in p for p in llm.prompts)
    assert body["premise"] == {"terms": ["neural network"], "acknowledged": ["neural network"]}
    checked = [c["text"] for c in body["verification"]["claims"]]
    assert not any("neural network" in c for c in checked)


@pytest.mark.db
def test_the_premise_check_can_be_turned_off(db_session, tmp_path):
    llm = SaysNotMentioned()
    api = make_api(db_session, tmp_path, llm, agent_premise_check=False)
    body = api.post(
        "/ask", json={"question": "Which neural network does the battery controller train?"}
    ).json()
    assert body["premise"] is None and not any("The question mentions" in p for p in llm.prompts)
