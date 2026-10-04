"""Experiment I follow-up: choose a verifier on one half of the labels, report the other.

    cd backend && .venv/bin/python scripts/verifier_split_eval.py

The 150 labelled statements are split by a hash of their id (fixed, not random): the
development half was used to design the NLI + lexical rescue and its guards, the test half
was not looked at until the design was fixed. Writes
experiments/results/exp_i_verifier_choice/<timestamp>/report.md and split.json.
"""

import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import get_settings  # noqa: E402
from app.evaluation.metrics import agreement  # noqa: E402
from app.evaluation.verifier_eval import load_labels  # noqa: E402
from app.verification.verifiers import (  # noqa: E402
    SUPPORTED,
    UNSUPPORTED,
    NliLexicalVerifier,
    NliVerifier,
)

LABELS = ROOT / "experiments" / "labels" / "test_claims_A_labeled.csv"


def half_of(claim_id: str) -> str:
    return "development" if int(hashlib.sha256(claim_id.encode()).hexdigest(), 16) % 2 else "test"


def main() -> int:
    nli = NliVerifier(get_settings().verifier_nli_model)
    methods = {"nli": nli, "nli_lexical": NliLexicalVerifier(nli)}
    rows = load_labels(LABELS)
    results = {}
    for part in ("development", "test", "all"):
        subset = [r for r in rows if part == "all" or half_of(r["claim_id"]) == part]
        claims = [r["statement"] for r in subset]
        passages = [r["passage_list"] for r in subset]
        human = [r["human_verdict"] for r in subset]
        supported = [i for i, h in enumerate(human) if h == SUPPORTED]
        unsupported = [i for i, h in enumerate(human) if h == UNSUPPORTED]
        for name, verifier in methods.items():
            predicted = [j.verdict for j in verifier.judge(claims, passages)]
            stats = agreement(human, predicted)
            results.setdefault(part, {})[name] = {
                "n": len(subset),
                "accuracy": round(stats["accuracy"], 3),
                "cohen_kappa": None
                if stats["cohen_kappa"] is None
                else round(stats["cohen_kappa"], 3),
                "false_alarms": sum(predicted[i] != SUPPORTED for i in supported),
                "labelled_supported": len(supported),
                "unsupported_caught": sum(predicted[i] != SUPPORTED for i in unsupported),
                "labelled_unsupported": len(unsupported),
            }
    out = ROOT / "experiments" / "results" / "exp_i_verifier_choice"
    out = out / datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    out.mkdir(parents=True)
    (out / "split.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    lines = [
        "# Verifier choice on a development/test split of the Experiment I labels",
        "",
        f"Labels: {LABELS.name} (one team member, AI-assisted). Split by a hash of the "
        "statement id. The NLI + lexical rescue was designed on the development half only.",
        "",
        "| Half | Method | n | Accuracy | κ | False alarms (labelled supported) | "
        "Unsupported caught |",
        "|---|---|---|---|---|---|---|",
    ]
    for part, by_method in results.items():
        for name, r in by_method.items():
            lines.append(
                f"| {part} | {name} | {r['n']} | {r['accuracy']:.3f} | {r['cohen_kappa']} | "
                f"{r['false_alarms']}/{r['labelled_supported']} | "
                f"{r['unsupported_caught']}/{r['labelled_unsupported']} |"
            )
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nWrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
