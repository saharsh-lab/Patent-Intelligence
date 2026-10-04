"""Phase 8 (no database): verifiers, claim extraction, misattribution, grounding score."""

import sys
import types

import pytest

from app.llm.providers import FakeLLM, LLMResponse
from app.rag.generation import parse_answer
from app.verification import verifiers as verifiers_module
from app.verification.checker import (
    Claim,
    VerificationReport,
    claims_from_answer,
    claims_from_comparison,
    verify_claims,
)
from app.verification.verifiers import (
    PARTIAL,
    SUPPORTED,
    UNSUPPORTED,
    LexicalVerifier,
    LlmJudgeVerifier,
    NliVerifier,
    build_verifier,
)
from tests.test_phase3_generation import fake_passage

PUMP = "The controller raises the coolant pump speed when a cell exceeds 40 degrees Celsius."
SENSOR = "Each cell carries a thermistor bonded to its casing."


# ------------------------------------------------------------------ lexical


@pytest.mark.parametrize(
    ("claim", "verdict"),
    [
        ("The controller raises the coolant pump speed above 40 degrees.", SUPPORTED),
        ("The controller raises pump speed using a lidar sensor array.", PARTIAL),
        ("The device is powered by a nuclear reactor.", UNSUPPORTED),
    ],
)
def test_lexical_verdicts(claim, verdict):
    [judgement] = LexicalVerifier().judge([claim], [[PUMP]])
    assert judgement.verdict == verdict


def test_lexical_without_passages_is_unsupported():
    assert LexicalVerifier().judge(["Anything at all here."], [[]])[0].verdict == UNSUPPORTED


# ------------------------------------------------------------------ NLI (stand-in model)


class FakeCrossEncoder:
    """Mimics sentence-transformers' CrossEncoder for an NLI model.

    Label order deliberately differs from the real model's, to check we read id2label."""

    def __init__(self, name):
        self.model = types.SimpleNamespace(
            config=types.SimpleNamespace(
                id2label={0: "ENTAILMENT", 1: "NEUTRAL", 2: "CONTRADICTION"}
            )
        )

    def predict(self, pairs, apply_softmax, show_progress_bar):
        out = []
        for premise, hypothesis in pairs:
            if "minute" in hypothesis:
                out.append([0.01, 0.04, 0.95])  # contradiction
            elif hypothesis.split()[0].lower() in premise.lower():
                out.append([0.90, 0.08, 0.02])  # entailment
            elif "weak" in hypothesis:
                out.append([0.30, 0.65, 0.05])
            else:
                out.append([0.03, 0.95, 0.02])  # neutral
        return out


@pytest.fixture
def nli(monkeypatch):
    monkeypatch.setitem(
        sys.modules, "sentence_transformers", types.SimpleNamespace(CrossEncoder=FakeCrossEncoder)
    )
    return NliVerifier("fake-nli")


def test_nli_verdicts_and_best_passage(nli):
    claims = ["thermistor sampling", "sampled once per minute", "weak hint", "unrelated text"]
    passages = [["A cell sensor.", "The thermistor samples at 10 Hz."]] + [[PUMP]] * 3
    results = nli.judge(claims, passages)
    assert [r.verdict for r in results] == [SUPPORTED, UNSUPPORTED, PARTIAL, UNSUPPORTED]
    assert results[0].best_passage == 1
    assert results[1].contradicted and "contradicted" in results[1].reason
    assert "not stated" in results[3].reason


def test_auto_method_prefers_nli_when_available(monkeypatch):
    monkeypatch.setitem(
        sys.modules, "sentence_transformers", types.SimpleNamespace(CrossEncoder=FakeCrossEncoder)
    )
    verifiers_module._shared_nli.cache_clear()
    assert build_verifier("auto", nli_model="x", llm=None).name == "nli_lexical"
    assert build_verifier("nli", nli_model="x", llm=None).name == "nli"
    assert build_verifier("lexical", nli_model="x", llm=None).name == "lexical"


# ------------------------------------------------------------------ LLM judge


class ScriptedLLM(FakeLLM):
    def __init__(self, reply):
        self.reply = reply

    def complete(self, messages, *, temperature, max_tokens):
        return LLMResponse(self.reply, "scripted", 30, 10, 1)


def test_llm_judge_parses_verdicts_and_defaults_missing_to_unsupported():
    reply = (
        'Result: [{"id": 1, "verdict": "supported", "reason": "stated"}, '
        '{"id": 2, "verdict": "maybe"}]'
    )
    judge = LlmJudgeVerifier(ScriptedLLM(reply))
    results = judge.judge(["a claim here", "another claim"], [[PUMP], [PUMP]])
    assert [r.verdict for r in results] == [SUPPORTED, UNSUPPORTED]
    assert results[1].reason == "judge gave no valid verdict"
    assert judge.last_usage == (30, 10)


def test_llm_judge_invalid_json():
    results = LlmJudgeVerifier(ScriptedLLM("I think they are fine.")).judge(["c one two"], [[PUMP]])
    assert results[0].verdict == UNSUPPORTED


# ------------------------------------------------------------------ claims & misattribution


def evidence_for(*texts):
    from app.rag.generation import build_evidence

    return build_evidence([fake_passage(t, rank=i + 1) for i, t in enumerate(texts)], 5000)


def test_claims_skip_disclaimers_short_bits_and_interpretation():
    parsed = parse_answer(
        "I cannot assess validity or infringement of patents. The controller raises the pump "
        "speed [E1]. Yes. The evidence does not mention a filing date.\n\nInterpretation: "
        "It is probably efficient.",
        {"E1"},
    )
    claims, skipped = claims_from_answer(parsed)
    assert [c.text for c in claims] == ["The controller raises the pump speed."]
    assert claims[0].cited == ["E1"]
    assert len(skipped) == 2


def test_misattributed_and_uncited_claims_are_partial():
    evidence = evidence_for(SENSOR, PUMP)
    claims = [
        Claim("The controller raises the coolant pump speed above 40 degrees Celsius.", ["E1"]),
        Claim("Each cell carries a thermistor bonded to its casing.", []),
        Claim("The device is powered by a nuclear reactor.", ["E1"]),
    ]
    results = verify_claims(LexicalVerifier(), claims, evidence)
    assert (results[0].verdict, results[0].misattributed, results[0].supporting) == (
        PARTIAL,
        True,
        ["E2"],
    )
    assert "which it did not cite" in results[0].reason
    assert (results[1].verdict, results[1].misattributed) == (PARTIAL, True)
    assert results[1].reason.startswith("uncited")
    assert results[2].verdict == UNSUPPORTED

    report = VerificationReport("lexical", results)
    assert report.grounding_score == pytest.approx((0.5 + 0.5 + 0) / 3, abs=1e-3)
    assert report.counts()["misattributed"] == 2


def test_comparison_claims_cover_cells_and_prose_points():
    table = {
        "cells": {
            "components": {
                "S1": {"text": "Pump, sensor and controller", "citations": ["E1"]},
                "S2": {"text": "Not stated in the evidence", "citations": []},
            }
        },
        "similarities": [
            {"text": "All sources mention: pump", "citations": ["E1"]},
            {"text": "Both use a coolant pump", "citations": ["E1", "E3"]},
        ],
        "differences": [{"text": "Only S2 uses immersion cooling", "citations": ["E3"]}],
    }
    claims = claims_from_comparison(table)
    assert [(c.location, c.text) for c in claims] == [
        ("cell:components:S1", "Pump, sensor and controller"),
        ("similarity", "Both use a coolant pump"),
    ]


def test_claim_combining_two_cited_passages_is_checked_against_both():
    evidence = evidence_for("The pack has a coolant pump.", "The pack has a cold plate.")
    claim = Claim("The pack has a coolant pump and a cold plate.", ["E1", "E2"])
    [result] = verify_claims(LexicalVerifier(), [claim], evidence)
    assert result.verdict == SUPPORTED and result.supporting == ["E1", "E2"]


def test_premise_includes_source_location():
    from app.verification.checker import premise_for

    [item] = evidence_for("3. The system of claim 1, wherein the current is limited.")
    assert premise_for(item).startswith("Source: a.pdf, claims, page 4.")


# ------------------------------------------------------------------ sentence windows (Phase 9)


def test_premise_windows_split_sentences_and_claim_elements():
    from app.verification.verifiers import premise_windows

    premise = "Source: a.txt, description.\n[0011] It samples at 10 Hz. A model estimates heat."
    windows = premise_windows(premise)
    assert windows[0] == premise
    assert "Source: a.txt, description.\n[0011] It samples at 10 Hz." in windows
    assert "Source: a.txt, description.\nA model estimates heat." in windows

    claim = "1. A system comprising: a pump; a sensor; and a controller."
    assert "a sensor;" in premise_windows(claim)
    assert premise_windows("One sentence only.") == ["One sentence only."]


class ShortPremiseNli(FakeCrossEncoder):
    """Like the real small model: entails only when the premise is a single sentence."""

    def predict(self, pairs, apply_softmax, show_progress_bar):
        out = []
        for premise, hypothesis in pairs:
            body = premise.split("\n", 1)[-1]
            single = body.count(". ") == 0
            out.append([0.95, 0.04, 0.01] if single and hypothesis in body else [0.1, 0.85, 0.05])
        return out


def test_nli_takes_the_best_sentence_window(monkeypatch):
    monkeypatch.setitem(
        sys.modules, "sentence_transformers", types.SimpleNamespace(CrossEncoder=ShortPremiseNli)
    )
    passage = "Source: a.txt, description.\nThe pump circulates coolant. It samples at 10 Hz."
    [result] = NliVerifier("fake").judge(["It samples at 10 Hz."], [[passage]])
    assert result.verdict == SUPPORTED and result.score == 0.95


# ------------------------------------------------------------------ false-alarm fixes (2026-10-04)


def test_uncited_but_supported_statement_counts_as_supported_when_enabled():
    evidence = evidence_for(SENSOR, PUMP)
    claims = [
        Claim("Each cell carries a thermistor bonded to its casing.", []),  # uncited
        Claim("The controller raises the coolant pump speed above 40 degrees Celsius.", ["E1"]),
    ]
    results = verify_claims(LexicalVerifier(), claims, evidence, uncited_supported=True)
    assert (results[0].verdict, results[0].misattributed) == (SUPPORTED, False)
    assert results[0].reason == "supported by E1 (no citation given)"
    # citing the WRONG passage is still misattribution
    assert (results[1].verdict, results[1].misattributed) == (PARTIAL, True)


def test_premise_states_the_document_title():
    from app.verification.checker import premise_for

    [item] = evidence_for("COPY SUPPRESSION FOR RAG OUTPUTS")
    item.passage.chunk.document = types.SimpleNamespace(title="COPY SUPPRESSION FOR RAG OUTPUTS")
    assert 'The title of this document is "COPY SUPPRESSION FOR RAG OUTPUTS".' in premise_for(item)


class AlwaysUnsure(verifiers_module.Verifier):
    """An NLI stand-in that supports nothing (like the small model on paraphrases)."""

    name = "unsure"

    def judge(self, claims, passages_per_claim):
        return [
            verifiers_module.Judgement(UNSUPPORTED, 0.05, 0, "unsure", contradiction=0.9)
            for _ in claims
        ]


PASSAGE = (
    "A combined probability is determined for the token from the first probability and the "
    "second probability, and the combined probability is used to select the token at 40 Hz, "
    "before it is sent."
)


@pytest.mark.parametrize(
    ("claim", "verdict"),
    [
        # paraphrase with every key word present: rescued (NLI contradiction ignored)
        (
            "The combined probability of the first and second probability selects the token.",
            SUPPORTED,
        ),
        # a changed number, an added negation, a swapped direction: never rescued
        ("The combined probability selects the token at 50 Hz.", UNSUPPORTED),
        ("The combined probability is not used to select the token.", UNSUPPORTED),
        # a direction word whose opposite the passage states ("after" vs. "before")
        ("The combined probability is used after the token is selected.", UNSUPPORTED),
        ("The token probability is determined by a neural network.", UNSUPPORTED),
    ],
)
def test_nli_lexical_rescues_paraphrases_but_not_changed_facts(claim, verdict):
    verifier = verifiers_module.NliLexicalVerifier(AlwaysUnsure())
    assert verifier.judge([claim], [[PASSAGE]])[0].verdict == verdict


def test_nli_lexical_known_limit_one_unstated_word_can_pass():
    # Documented trade-off: 75% key-word coverage is the rescue level (chosen on the
    # development labels); "quickly" is not in the passage but 3 of 4 key words are.
    verifier = verifiers_module.NliLexicalVerifier(AlwaysUnsure())
    claim = "The second probability is determined quickly for the token."
    assert "quickly" not in PASSAGE
    assert verifier.judge([claim], [[PASSAGE]])[0].verdict == SUPPORTED


# ------------------------------------------------------------------ second opinion (2026-10-04)


class ScriptedJudge(FakeLLM):
    model = "scripted"

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def complete(self, messages, *, temperature, max_tokens):
        self.calls.append(messages[1].content)
        return LLMResponse(self.replies.pop(0), "scripted", 10, 10, 1)


def test_second_opinion_confirms_paraphrases_and_keeps_rejections():
    llm = ScriptedJudge(
        [
            '[{"id": 1, "verdict": "supported", "reason": "probability = likelihood"},'
            ' {"id": 2, "verdict": "unsupported", "reason": "no neural network"},'
            ' {"id": 3, "verdict": "partially_supported", "reason": "cause not stated"}]'
        ]
    )
    verifier = verifiers_module.SecondOpinionVerifier(
        AlwaysUnsure(), LlmJudgeVerifier(llm, verifiers_module._SECOND_OPINION_PROMPT)
    )
    out = verifier.judge(["a b c d", "e f g h", "i j k l"], [[PASSAGE]] * 3)
    assert [j.verdict for j in out] == [SUPPORTED, UNSUPPORTED, PARTIAL]
    assert out[0].reason.startswith("confirmed by LLM judge")


def test_second_opinion_batches_and_survives_cut_off_replies():
    cut_off = '[{"id": 1, "verdict": "supported", "reason": "ok"}, {"id": 2, "verd'
    llm = ScriptedJudge([cut_off, '[{"id": 1, "verdict": "supported", "reason": "ok"}]'])
    verifier = verifiers_module.SecondOpinionVerifier(AlwaysUnsure(), LlmJudgeVerifier(llm))
    out = verifier.judge([f"statement {i} here" for i in range(5)], [[PASSAGE]] * 5)
    assert len(llm.calls) == 2  # 4 + 1 statements
    assert [j.verdict for j in out] == [SUPPORTED, UNSUPPORTED, UNSUPPORTED, UNSUPPORTED, SUPPORTED]


def test_statement_naming_another_patent_is_unsupported():
    guard = verifiers_module.AttributionGuard(LexicalVerifier())
    passage = "Source: US12563707B2.txt, abstract.\nStagnant fluid reduces the cooling capacity."
    claim = (
        "The problem addressed by US20230369708A1 is that stagnant fluid reduces cooling capacity."
    )
    [j] = guard.judge([claim], [[passage]])
    assert j.verdict == UNSUPPORTED and "from US12563707B2" in j.reason
    right = "The problem addressed by US12563707B2 is that stagnant fluid reduces cooling capacity."
    assert guard.judge([right], [[passage]])[0].verdict == SUPPORTED


def test_auto_uses_the_second_opinion_only_with_a_real_llm(monkeypatch):
    monkeypatch.setitem(
        sys.modules, "sentence_transformers", types.SimpleNamespace(CrossEncoder=FakeCrossEncoder)
    )
    verifiers_module._shared_nli.cache_clear()
    assert build_verifier("auto", nli_model="x", llm=FakeLLM()).name == "nli_lexical"
    assert build_verifier("auto", nli_model="x", llm=ScriptedJudge([])).name == "nli_llm"
