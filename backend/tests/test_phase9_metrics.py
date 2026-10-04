"""Phase 9 (no database): metric formulas, checked against hand-computed values."""

import pytest

from app.evaluation.metrics import (
    agreement,
    bootstrap_ci,
    cohen_kappa,
    key_fact_recall,
    paired_difference,
    percentile,
    retrieval_metrics,
    tool_selection,
)


def test_retrieval_metrics_by_hand():
    # 4 passages retrieved; 2 labels. Passage 2 satisfies label 0, passage 3 labels 0 and 1.
    m = retrieval_metrics([set(), {0}, {0, 1}, set()], n_labels=2, k=2)
    assert m["precision_at_k"] == 0.5  # 1 relevant in the top 2
    assert m["recall_at_k"] == 0.5  # only label 0 found in the top 2
    assert m["mrr"] == 0.5  # first relevant at rank 2
    assert m["hit_at_k"] == 1.0
    assert m["context_precision"] == 0.5  # 2 of 4 passages relevant
    assert m["context_recall"] == 1.0  # both labels found somewhere


def test_retrieval_metrics_nothing_found():
    m = retrieval_metrics([set(), set()], n_labels=1, k=5)
    assert m["mrr"] == m["recall_at_k"] == m["hit_at_k"] == m["precision_at_k"] == 0.0
    assert retrieval_metrics([], n_labels=1, k=5)["context_precision"] == 0.0
    with pytest.raises(ValueError):
        retrieval_metrics([], n_labels=0, k=5)


def test_tool_selection():
    assert tool_selection({"a", "b"}, ["a", "c", "a"]) == {
        "tool_precision": 0.5,
        "tool_recall": 0.5,
        "tools_exact": 0.0,
    }
    assert tool_selection([], [])["tools_exact"] == 1.0
    assert tool_selection(["a"], [])["tool_recall"] == 0.0


def test_key_fact_recall_normalizes_case_and_whitespace():
    answer = "The controller samples every thermistor at 10\nHz using a Water-Glycol loop."
    assert key_fact_recall(answer, ["10 Hz", "water-glycol", "40 degrees"]) == pytest.approx(2 / 3)
    assert key_fact_recall(answer, []) is None


def test_agreement_by_hand():
    s, p, u = "supported", "partially_supported", "unsupported"
    human = [s, s, u, u, p]
    predicted = [s, u, u, u, s]
    a = agreement(human, predicted)
    assert a["accuracy"] == pytest.approx(3 / 5)
    # chance = (2/5·2/5) + (2/5·3/5) + (1/5·0) = 0.4 → κ = (0.6 − 0.4) / 0.6
    assert a["cohen_kappa"] == pytest.approx(1 / 3)
    assert a["detection"]["precision"] == pytest.approx(2 / 3)  # 3 flagged, 2 truly unsupported
    assert a["detection"]["recall"] == 1.0
    assert a["confusion"][s][u] == 1 and a["confusion"][p][s] == 1
    assert a["per_class"][p]["support"] == 1
    assert a["binary_accuracy"] == pytest.approx(3 / 5)


def test_kappa_undefined_when_everyone_uses_one_label():
    assert cohen_kappa(["supported"] * 3, ["supported"] * 3) is None


def test_percentile_matches_linear_interpolation():
    assert percentile([1, 2, 3, 4], 50) == 2.5
    assert percentile([10], 95) == 10
    assert percentile([], 50) is None


def test_bootstrap_is_seeded_and_brackets_the_mean():
    values = [0.0, 0.5, 1.0, 1.0, 0.5, 0.0, 1.0]
    low, high = bootstrap_ci(values, seed=3)
    assert (low, high) == bootstrap_ci(values, seed=3)
    assert low <= sum(values) / len(values) <= high
    assert bootstrap_ci([1.0]) == (None, None)


def test_paired_difference():
    baseline = {"q1": 0.0, "q2": 0.0, "q3": 0.0, "q4": 0.0}
    better = {"q1": 1.0, "q2": 1.0, "q3": 1.0, "q4": 1.0, "q5": 1.0}  # q5 unpaired: ignored
    d = paired_difference(baseline, better)
    assert d["n"] == 4 and d["mean_diff"] == 1.0 and d["wins"] == 4 and d["clear"] is True

    mixed = {"q1": 1.0, "q2": -1.0, "q3": 0.0, "q4": 0.0}
    d = paired_difference(baseline, mixed)
    assert (d["wins"], d["losses"], d["ties"]) == (1, 1, 2) and d["clear"] is False
    assert paired_difference({"a": 1.0}, {"b": 1.0}) is None


def test_source_metrics_are_document_level():
    from app.evaluation.dataset import EvalItem, RelevanceLabel
    from app.evaluation.scoring import source_metrics

    item = EvalItem(
        id="x",
        type="comparison",
        question="q",
        relevant=[RelevanceLabel(doc="a", claim=1), RelevanceLabel(patent="EP1234567")],
    )
    evidence = [
        {"source_label": "a.txt", "text": "anything"},
        {"source_label": "other.txt", "text": "x"},
        {"source_label": "EP1234567B1", "text": "y"},  # kind code differs: same patent
    ]
    m = source_metrics(evidence, item, {"a.txt": "a", "other.txt": "b"})
    assert m == {"source_recall": 1.0, "source_precision": 2 / 3}
