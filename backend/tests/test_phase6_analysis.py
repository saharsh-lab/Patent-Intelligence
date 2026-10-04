"""Phase 6 (no database): query analysis — rules and LLM planner with safe fallback."""

import pytest

from app.agents.analysis import analyze_llm, analyze_rules, find_publication_numbers
from app.llm.providers import FakeLLM, LLMResponse


@pytest.mark.parametrize(
    ("question", "intent", "numbers", "section", "claim"),
    [
        ("How is the coolant pump speed controlled?", "document_qa", [], None, None),
        ("What does claim 3 of my patent add?", "document_qa", [], "claims", 3),
        ("Summarize the abstract", "document_qa", [], "abstract", None),
        ("What does EP1234567A1 claim?", "patent_lookup", ["EP1234567A1"], "claims", None),
        ("Find patents similar to my uploaded invention", "find_similar", [], None, None),
        (
            "Is there prior art for wireless charging foreign object detection?",
            "find_similar",
            [],
            None,
            None,
        ),
        (
            "Compare EP 1234567 A1 with US 10,123,456 B2",
            "compare",
            ["EP1234567A1", "US10123456B2"],
            None,
            None,
        ),
        (
            "What are the differences between my patent and XX0000001A1?",
            "compare",
            ["XX0000001A1"],
            None,
            None,
        ),
    ],
)
def test_rule_based_intents(question, intent, numbers, section, claim):
    analysis = analyze_rules(question)
    assert analysis.intent == intent
    assert analysis.publication_numbers == numbers
    assert analysis.section == section
    assert analysis.claim_number == claim
    assert analysis.analyzer == "rules"


def test_legal_questions_are_flagged():
    assert analyze_rules("Does my design infringe EP1234567?").legal_question
    assert analyze_rules("Is claim 1 of XX0000001A1 valid?").legal_question
    assert not analyze_rules("How does the pump work?").legal_question


def test_search_keywords_skip_filler_words():
    assert analyze_rules("Find patents about inductive charging coils").search_keywords == (
        "inductive charging coils"
    )


def test_publication_number_extraction_ignores_non_numbers():
    assert find_publication_numbers("EP 1 234 567 B1 and WO2020/123456A1, not US 12") == [
        "EP1234567B1",
        "WO2020123456A1",
    ]


class ScriptedLLM(FakeLLM):
    def __init__(self, reply: str):
        self.reply = reply

    def complete(self, messages, *, temperature, max_tokens):
        return LLMResponse(self.reply, "scripted", 10, 5, 1)


def test_llm_planner_used_when_valid():
    reply = (
        '{"intent": "find_similar", "publication_numbers": [], "section": null, '
        '"claim_number": null, "search_keywords": "battery cooling plate", "legal_question": false}'
    )
    analysis = analyze_llm("Is anything out there like my battery idea?", ScriptedLLM(reply))
    assert analysis.analyzer == "llm"
    assert analysis.intent == "find_similar"
    assert analysis.search_keywords == "battery cooling plate"


def test_llm_cannot_invent_patent_numbers():
    reply = '{"intent": "patent_lookup", "publication_numbers": ["EP9999999A1"]}'
    analysis = analyze_llm("Tell me about the pump patent", ScriptedLLM(reply))
    assert analysis.publication_numbers == []  # not in the question → discarded


@pytest.mark.parametrize("reply", ["Sure! The intent is compare.", "", "[1, 2]"])
def test_llm_planner_falls_back_to_rules(reply):
    analysis = analyze_llm("Compare EP1234567A1 with EP7654321B1", ScriptedLLM(reply))
    assert analysis.analyzer == "llm_fallback_rules"
    assert analysis.intent == "compare"


def test_invalid_llm_intent_keeps_other_llm_fields():
    # Observed with Qwen3: intent "legal_question" is not one of ours
    reply = (
        '{"intent": "legal_question", "search_keywords": "battery cooling", "legal_question": true}'
    )
    analysis = analyze_llm("Does my battery patent infringe XX0000001A1?", ScriptedLLM(reply))
    assert analysis.analyzer == "llm_rules_intent"
    assert analysis.intent == "compare"  # rules: legal + number + "my ... patent"
    assert analysis.search_keywords == "battery cooling"
    assert analysis.legal_question and analysis.refers_to_scope


def test_llm_planner_tolerates_text_around_json():
    reply = 'Here you go:\n```json\n{"intent": "find_similar"}\n```'
    assert analyze_llm("Anything like my pump?", ScriptedLLM(reply)).intent == "find_similar"


@pytest.mark.parametrize(
    "question",
    ["Compare how these two documents cool the cells.", "Do both patents use a pump?"],
)
def test_plural_scope_references(question):
    # Found by the Phase 9 dev set: "these two documents" was not recognised
    assert analyze_rules(question).refers_to_scope


def test_llm_cannot_refuse_or_invent_sections():
    # Found in Phase 9 (Experiment A, Qwen3): a technical question was called out of
    # scope, and ordinary questions got a section the question never named.
    reply = '{"intent": "out_of_scope", "section": "description", "claim_number": 7}'
    analysis = analyze_llm("What coolant does the pump circulate?", ScriptedLLM(reply))
    assert analysis.intent == "document_qa" and analysis.analyzer == "llm_scope_override"
    assert analysis.section is None and analysis.claim_number is None

    reply = '{"intent": "document_qa", "section": "claims", "claim_number": 3}'
    analysis = analyze_llm("What does claim 3 add?", ScriptedLLM(reply))
    assert (analysis.section, analysis.claim_number) == ("claims", 3)


@pytest.mark.parametrize(
    ("question", "intent"),
    [
        ("Which kinds of pumps can be used inside the cooling module?", "document_qa"),
        ("Is anything out there like my invention?", "find_similar"),
    ],
)
def test_llm_similar_search_needs_wording(question, intent):
    # Phase 10 (real patents): plain lookups were labelled find_similar by Qwen3
    reply = '{"intent": "find_similar"}'
    assert analyze_llm(question, ScriptedLLM(reply)).intent == intent
