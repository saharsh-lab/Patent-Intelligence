"""Experiment E: questions about new patents, answered live, local-only and closed-book."""

import json
from datetime import date

import pytest

from app.core.config import get_settings
from app.evaluation.live import (
    LiveConfig,
    LiveRunner,
    build_live_dataset,
    looks_english,
    score_answer,
    split_claims,
    statements_of,
    target_words,
)
from app.llm.providers import FakeLLM, LLMResponse
from app.models import Patent
from app.patents.demo import DemoPatentSource
from app.rag.embeddings import FakeEmbedder
from app.verification.verifiers import LexicalVerifier, _content_words

CLAIMS = (
    "1. A battery pack comprising: a plurality of cells; and a coolant pump.\n\n"
    "2. The battery pack of claim 1, wherein the coolant pump is a positive displacement "
    "pump driven by a brushless motor.\n\n3.-4. (canceled)\n\n5. The battery pack of claim 1."
)


def test_claims_are_split_and_targets_are_the_added_feature():
    claims = split_claims(CLAIMS)
    assert sorted(claims) == [1, 2, 5]  # cancelled claims dropped
    assert claims[2].startswith("2. The battery pack of claim 1, wherein")
    targets = target_words(claims[2])
    assert _content_words("positive displacement pump brushless motor") <= set(targets)
    assert "battery" not in targets  # only what the dependent claim adds
    assert looks_english(claims[1])
    headed = split_claims("1. CLAIMS What is claimed is:\n1. A pump comprising a rotor.\n")
    assert headed == {1: "1. A pump comprising a rotor."}
    docket = split_claims(
        "1. Attorney Docket No.: 1355.WQ00 CLAIMS What is claimed is:\n1. A rotor."
    )
    assert docket == {1: "1. A rotor."}
    independent = "1. A charger comprising a coil, wherein the object is a metal object."
    assert {"charger", "coil"} <= set(target_words(independent))  # whole claim counts
    assert not looks_english("1. Batteriepack umfassend eine Vielzahl von Zellen und eine Pumpe.")


def test_statements_drop_citations_and_fragments():
    assert statements_of("The pump is a positive displacement pump [E1]. Short one.") == [
        "The pump is a positive displacement pump."
    ]


def test_score_answer_judges_against_the_real_claims():
    claims = split_claims(CLAIMS)
    item = {
        "claim": 2,
        "claims": {str(k): v for k, v in claims.items()},
        "abstract": "",
        "target_words": target_words(claims[2]),
    }
    good = score_answer(
        item,
        "Claim 2 specifies a positive displacement coolant pump with a brushless motor.",
        False,
        LexicalVerifier(),
    )
    invented = score_answer(
        item,
        "Claim 2 adds a graphene heat spreader bonded to an aluminium housing plate.",
        False,
        LexicalVerifier(),
    )
    assert (
        good["claim_recall"] > 0.8 and good["supported_by_patent"] > invented["supported_by_patent"]
    )
    abstained = score_answer(item, "", True, LexicalVerifier())
    assert abstained["claim_recall"] == 0.0 and "supported_by_patent" not in abstained


class ScriptedLLM(FakeLLM):
    """Closed book: invents an answer. With evidence: restates the demo claim, cited."""

    def complete(self, messages, *, temperature, max_tokens):
        if "expert on patents" in messages[0].content:
            return LLMResponse(
                "It claims a solar panel with a tracking mirror array.", "f", 5, 5, 1
            )
        if "[E1]" in messages[-1].content or "E1" in messages[-1].content:
            text = (
                "The battery pack has a thermistor attached to each cell and a coolant pump, "
                "and a controller increases the pump speed when a cell is too hot [E1]."
            )
            return LLMResponse(text, "f", 50, 20, 1)
        return super().complete(messages, temperature=temperature, max_tokens=max_tokens)


@pytest.mark.db
def test_live_experiment_end_to_end(db_session, tmp_path):
    config = LiveConfig(
        name="exp_e_test",
        dataset=tmp_path / "live" / "questions.json",
        source="demo",
        topics={"battery": "battery"},
        published_from=date(2000, 1, 1),
        per_topic=1,
        countries=["XX"],
    )
    dataset = build_live_dataset(config, DemoPatentSource(), log=lambda _: None)
    assert [i["type"] for i in dataset["items"]] == ["independent_claim", "dependent_claim"]
    assert dataset["items"][0]["question"].startswith("What does claim 1 of XX")

    settings = get_settings().model_copy(
        update={"upload_dir": tmp_path, "agent_planner": "rules", "retrieval_min_similarity": 0.0}
    )
    runner = LiveRunner(
        db_session,
        settings,
        FakeEmbedder(settings.embedding_dim),
        ScriptedLLM(),
        {"demo": DemoPatentSource()},
        LexicalVerifier(),
        log=lambda _: None,
    )
    out = runner.run(config, tmp_path / "results")
    rows = [json.loads(line) for line in (out / "runs.jsonl").open()]
    by = {(r["variant"], r["item_id"]): r for r in rows}
    first = dataset["items"][0]["id"]

    assert by[("live", first)]["right_patent"] == 1.0  # imported live and retrieved
    assert by[("live", first)]["right_claim"] == 1.0
    assert by[("local_only", first)]["right_patent"] == 0.0  # no source: cannot find it
    closed = by[("closed_book", first)]
    assert closed["supported_by_patent"] < by[("live", first)]["supported_by_patent"]
    assert db_session.query(Patent).count() == 0  # imports cleared between questions

    summary = json.loads((out / "summary.json").read_text())
    assert summary["kind"] == "experiment" and summary["dataset"]["patents"] == 1
    assert {c["variant"] for c in summary["comparisons"]} == {"local_only", "closed_book"}
    assert "supported by the patent" in (out / "report.md").read_text()
