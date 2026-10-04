"""Metric formulas and statistics. Pure functions: no database, no models.

Retrieval (needs labelled relevant passages):
    precision@k   = relevant passages in the top k ÷ k
    recall@k      = labels found in the top k ÷ all labels of the question
    MRR           = 1 ÷ rank of the first relevant passage (0 if none)
Agent (needs labelled expected tools):
    tool precision = expected tools used ÷ tools used
    tool recall    = expected tools used ÷ expected tools
Verifier vs. human labels:
    accuracy, Cohen's kappa (agreement corrected for chance), per-class F1, and
    hallucination detection (positive class = "unsupported").

Statistics: questions are the unit of analysis. Each metric is averaged per question
(over repeats), then a bootstrap gives a 95% confidence interval for the mean.
Two variants are compared *paired* (same questions), which is more sensitive than
comparing two independent means.
"""

import math
import random
from collections.abc import Iterable, Sequence

VERDICTS = ("supported", "partially_supported", "unsupported")


# ------------------------------------------------------------------ retrieval


def retrieval_metrics(matches: Sequence[set[int]], n_labels: int, k: int) -> dict[str, float]:
    """`matches[i]` = indices of the relevance labels that retrieved passage i satisfies
    (rank order). A passage is relevant if it satisfies at least one label; a label is
    found if at least one passage satisfies it."""
    if n_labels <= 0:
        raise ValueError("retrieval metrics need at least one relevance label")
    relevant = [bool(m) for m in matches]
    found_at_k = set().union(*matches[:k]) if matches else set()
    found_all = set().union(*matches) if matches else set()
    first = next((i for i, r in enumerate(relevant) if r), None)
    return {
        "precision_at_k": sum(relevant[:k]) / k,
        "recall_at_k": len(found_at_k) / n_labels,
        "hit_at_k": float(any(relevant[:k])),
        "mrr": 0.0 if first is None else 1.0 / (first + 1),
        # over everything given to the LLM, whatever its length
        "context_precision": sum(relevant) / len(relevant) if relevant else 0.0,
        "context_recall": len(found_all) / n_labels,
    }


# ------------------------------------------------------------------ agent


def tool_selection(expected: Iterable[str], used: Iterable[str]) -> dict[str, float]:
    """Compares *sets* of tool names (order and repeats are ignored)."""
    expected, used = set(expected), set(used)
    hit = len(expected & used)
    return {
        "tool_precision": hit / len(used) if used else float(not expected),
        "tool_recall": hit / len(expected) if expected else 1.0,
        "tools_exact": float(expected == used),
    }


# ------------------------------------------------------------------ answers


def key_fact_recall(answer: str, facts: Sequence[str]) -> float | None:
    """Share of expected facts that appear (case/whitespace-insensitive) in the answer.

    A cheap, deterministic correctness proxy: it rewards stating "10 Hz", it cannot
    judge paraphrases ("ten times per second"). Labelled facts should be short.
    """
    if not facts:
        return None
    from app.evaluation.dataset import normalize

    text = normalize(answer)
    return sum(normalize(f) in text for f in facts) / len(facts)


# ------------------------------------------------------------------ verifier agreement


def agreement(human: Sequence[str], predicted: Sequence[str]) -> dict:
    """How well a verifier's verdicts agree with human verdicts."""
    if len(human) != len(predicted):
        raise ValueError("human and predicted verdict lists differ in length")
    n = len(human)
    if n == 0:
        raise ValueError("no labelled claims")
    confusion = {h: dict.fromkeys(VERDICTS, 0) for h in VERDICTS}
    for h, p in zip(human, predicted, strict=True):
        confusion[h][p] += 1
    accuracy = sum(confusion[v][v] for v in VERDICTS) / n

    per_class = {}
    for v in VERDICTS:
        tp = confusion[v][v]
        predicted_v = sum(confusion[h][v] for h in VERDICTS)
        actual_v = sum(confusion[v].values())
        per_class[v] = _prf(tp, predicted_v, actual_v) | {"support": actual_v}
    macro_f1 = sum(per_class[v]["f1"] for v in VERDICTS if per_class[v]["support"]) / max(
        1, sum(1 for v in VERDICTS if per_class[v]["support"])
    )

    # Hallucination detection: does the verifier flag the statements humans call unsupported?
    tp = confusion["unsupported"]["unsupported"]
    detection = _prf(
        tp,
        sum(confusion[h]["unsupported"] for h in VERDICTS),
        sum(confusion["unsupported"].values()),
    )
    # Binary view: fully supported vs. not
    binary_h = [h == "supported" for h in human]
    binary_p = [p == "supported" for p in predicted]
    return {
        "n": n,
        "accuracy": accuracy,
        "cohen_kappa": cohen_kappa(human, predicted),
        "macro_f1": macro_f1,
        "binary_accuracy": sum(a == b for a, b in zip(binary_h, binary_p, strict=True)) / n,
        "detection": detection,
        "per_class": per_class,
        "confusion": confusion,  # confusion[human][predicted]
    }


def cohen_kappa(a: Sequence[str], b: Sequence[str]) -> float | None:
    """κ = (observed agreement − chance agreement) ÷ (1 − chance agreement).

    1 = perfect, 0 = no better than chance. Undefined (None) when chance agreement
    is 1, i.e. both raters always used the same single label."""
    n = len(a)
    observed = sum(x == y for x, y in zip(a, b, strict=True)) / n
    labels = set(a) | set(b)
    chance = sum((list(a).count(v) / n) * (list(b).count(v) / n) for v in labels)
    if math.isclose(chance, 1.0):
        return None
    return (observed - chance) / (1 - chance)


def _prf(tp: int, predicted: int, actual: int) -> dict[str, float]:
    precision = tp / predicted if predicted else 0.0
    recall = tp / actual if actual else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


# ------------------------------------------------------------------ statistics


def mean(values: Sequence[float]) -> float | None:
    return sum(values) / len(values) if values else None


def percentile(values: Sequence[float], q: float) -> float | None:
    """Linear-interpolation percentile (q in 0..100), like numpy's default."""
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * q / 100
    low, high = math.floor(position), math.ceil(position)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def bootstrap_ci(
    values: Sequence[float], *, n_boot: int = 2000, level: float = 0.95, seed: int = 0
) -> tuple[float | None, float | None]:
    """Percentile bootstrap confidence interval for the mean.

    Resample the questions with replacement many times, take the mean each time, and
    report the middle 95% of those means. Makes no normality assumption, which suits
    bounded scores (0..1) on small datasets. Seeded, so reports are reproducible."""
    if len(values) < 2:
        return (None, None)
    rng = random.Random(seed)
    n = len(values)
    means = sorted(sum(rng.choices(values, k=n)) / n for _ in range(n_boot))
    tail = (1 - level) / 2
    return percentile(means, tail * 100), percentile(means, (1 - tail) * 100)


def summarize(values: Sequence[float], seed: int = 0) -> dict:
    low, high = bootstrap_ci(values, seed=seed)
    return {"n": len(values), "mean": mean(values), "ci_low": low, "ci_high": high}


def paired_difference(
    baseline: dict[str, float], variant: dict[str, float], seed: int = 0
) -> dict | None:
    """variant − baseline on the questions both have values for.

    `clear` is True when the 95% interval excludes 0: a difference this dataset can
    actually support. Otherwise the honest conclusion is "no clear difference"."""
    shared = sorted(set(baseline) & set(variant))
    if not shared:
        return None
    diffs = [variant[q] - baseline[q] for q in shared]
    low, high = bootstrap_ci(diffs, seed=seed)
    return {
        "n": len(shared),
        "mean_diff": mean(diffs),
        "ci_low": low,
        "ci_high": high,
        "wins": sum(d > 1e-9 for d in diffs),
        "losses": sum(d < -1e-9 for d in diffs),
        "ties": sum(abs(d) <= 1e-9 for d in diffs),
        "clear": low is not None and (low > 0 or high < 0),
    }
