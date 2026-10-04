"""Experiment I: how accurate is each claim verifier, measured against human labels?

Workflow:
1. `export-claims` takes the answers from an experiment result and writes a CSV of
   (statement, cited passages) pairs with an empty `human_verdict` column. The
   system's own verdict is deliberately NOT included, so labellers are not anchored.
2. A person fills in `human_verdict` (supported / partially_supported / unsupported,
   or s / p / u) following docs/labelling_guide.md.
3. `verifier` runs each verifier method on the labelled rows and reports agreement
   (accuracy, Cohen's kappa, detection precision/recall for unsupported statements).

Each row is judged against its cited passages individually and joined, exactly as the
first pass of `verification.checker.verify_claims` does.
"""

import csv
import json
import random
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.evaluation.config import ConfigError, check_overrides
from app.evaluation.metrics import VERDICTS, agreement, summarize
from app.llm.providers import LLMProvider, build_llm
from app.models import AgentRun
from app.verification.verifiers import build_verifier

COLUMNS = ["claim_id", "question", "statement", "cited", "passages", "human_verdict", "notes"]
PASSAGE_SEPARATOR = "\n\n----------\n\n"
SHORT = {
    "s": "supported",
    "p": "partially_supported",
    "partial": "partially_supported",
    "u": "unsupported",
}


# ------------------------------------------------------------------ export


def _premise(evidence: dict) -> str:
    """Same text the verifier sees: location line + passage (see checker.premise_for)."""
    location = [evidence.get("source_label") or "?"]
    if evidence.get("section"):
        claim = evidence.get("claim_number")
        location.append(f"claim {claim}" if claim else evidence["section"])
    if evidence.get("page_number"):
        location.append(f"page {evidence['page_number']}")
    return f"Source: {', '.join(location)}.\n{evidence['text']}"


def claims_for_labelling(runs: list[AgentRun]) -> list[dict]:
    rows, seen = [], set()
    for run in runs:
        answer = run.answer or {}
        verification = answer.get("verification") or {}
        by_label = {e["label"]: e for e in answer.get("evidence") or [] if e.get("label")}
        for claim in verification.get("claims") or []:
            cited = [label for label in claim["cited"] if label in by_label]
            if not cited:  # nothing cited: nothing to judge the statement against
                continue
            passages = [_premise(by_label[label]) for label in cited]
            key = (claim["text"], tuple(passages))
            if key in seen:  # the same statement over the same passages (e.g. repeats)
                continue
            seen.add(key)
            rows.append(
                {
                    "claim_id": f"{run.id}:{claim['index']}",
                    "question": run.query.query_text,
                    "statement": claim["text"],
                    "cited": " ".join(cited),
                    "passages": PASSAGE_SEPARATOR.join(passages),
                    "human_verdict": "",
                    "notes": "",
                }
            )
    return rows


def export_claims(
    session: Session, result_dir: Path, out_path: Path, *, sample: int | None = None, seed=0
) -> int:
    run_ids = []
    with (Path(result_dir) / "runs.jsonl").open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            if row.get("run_id"):
                run_ids.append(uuid.UUID(row["run_id"]))
    runs = [run for run in (session.get(AgentRun, rid) for rid in run_ids) if run is not None]
    if not runs:
        raise ValueError(
            "None of this result's runs are in the database (export needs the evaluation "
            "database the experiment was run on)."
        )
    rows = claims_for_labelling(runs)
    if sample and len(rows) > sample:
        rows = random.Random(seed).sample(rows, sample)  # random, so not only easy cases
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


# ------------------------------------------------------------------ labels


def normalize_verdict(value: str) -> str | None:
    value = (value or "").strip().lower().replace(" ", "_")
    if value in VERDICTS:
        return value
    return SHORT.get(value)


def load_labels(path: Path) -> list[dict]:
    """Labelled rows only; rows with an empty verdict are skipped, invalid ones rejected."""
    rows = []
    with Path(path).open(newline="", encoding="utf-8-sig") as f:  # Excel adds a BOM
        reader = csv.DictReader(f)
        missing = {"statement", "passages", "human_verdict"} - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path}: missing columns {sorted(missing)}")
        for line, row in enumerate(reader, start=2):
            if not (row.get("human_verdict") or "").strip():
                if (row.get("notes") or "").startswith("TO SETTLE"):
                    # skipping these would drop exactly the hard cases from the evaluation
                    raise ValueError(
                        f"{path} line {line}: a disagreement between the labellers is not "
                        "settled yet (fill in human_verdict)"
                    )
                continue
            verdict = normalize_verdict(row["human_verdict"])
            if verdict is None:
                raise ValueError(
                    f"{path} line {line}: human_verdict {row['human_verdict']!r} is not one "
                    f"of {VERDICTS} (or s/p/u)"
                )
            passages = [p for p in row["passages"].split(PASSAGE_SEPARATOR) if p.strip()]
            rows.append(row | {"human_verdict": verdict, "passage_list": passages})
    if not rows:
        raise ValueError(f"{path}: no labelled rows yet (fill in the human_verdict column)")
    return rows


def compare_labellers(path_a: Path, path_b: Path, out: Path) -> dict:
    """Agreement between two people who labelled the same export independently.

    Writes `out`: verdicts both agree on are filled in; disagreements (and statements only
    one person labelled) are left empty with both answers in `notes`, to be settled in a
    discussion. Returns human-human agreement (κ is the ceiling for any verifier)."""

    def read(path: Path) -> tuple[list[str], dict[str, dict]]:
        with Path(path).open(newline="", encoding="utf-8-sig") as f:  # Excel adds a BOM
            reader = csv.DictReader(f)
            fields = list(reader.fieldnames or [])
            if "claim_id" not in fields or "human_verdict" not in fields:
                raise ValueError(f"{path}: not an exported label file (claim_id, human_verdict)")
            rows = {row["claim_id"]: row for row in reader}
        for line, row in enumerate(rows.values(), start=2):
            value = (row.get("human_verdict") or "").strip()
            if value and normalize_verdict(value) is None:
                raise ValueError(f"{path} line {line}: human_verdict {value!r} is not s/p/u")
        return fields, rows

    fields, rows_a = read(path_a)
    _, rows_b = read(path_b)
    if set(rows_a) != set(rows_b):
        raise ValueError("the two files contain different statements; label the same export")

    both_a, both_b, merged = [], [], []
    disagreements = unlabelled = 0
    for claim_id, row in rows_a.items():
        a = normalize_verdict(row.get("human_verdict") or "")
        b = normalize_verdict(rows_b[claim_id].get("human_verdict") or "")
        notes = [n for n in (row.get("notes"), rows_b[claim_id].get("notes")) if n]
        out_row = dict(row)
        if a and b:
            both_a.append(a)
            both_b.append(b)
        if a and a == b:
            out_row["human_verdict"] = a
            out_row["notes"] = " | ".join(notes)
        else:
            if a and b:
                disagreements += 1
            else:
                unlabelled += 1
            out_row["human_verdict"] = ""
            out_row["notes"] = f"TO SETTLE: A={a or '-'} B={b or '-'}" + (
                " | " + " | ".join(notes) if notes else ""
            )
        merged.append(out_row)

    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(merged)

    result = {
        "file_a": str(path_a),
        "file_b": str(path_b),
        "statements": len(rows_a),
        "labelled_by_both": len(both_a),
        "disagreements": disagreements,
        "missing_a_label": unlabelled,
        "agreement": agreement(both_a, both_b) if both_a else None,
    }
    out.with_suffix(".agreement.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


# ------------------------------------------------------------------ evaluation


class VerifierExperiment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(pattern=r"^[A-Za-z0-9_.-]{1,60}$")
    description: str = ""
    labels: Path
    methods: list[str] = Field(min_length=1)
    settings: dict[str, Any] = {}
    seed: int = 0

    @field_validator("methods")
    @classmethod
    def _known(cls, methods: list[str]) -> list[str]:
        unknown = set(methods) - {"nli", "nli_lexical", "llm_judge", "lexical"}
        if unknown:
            raise ValueError(f"unknown verifier methods {sorted(unknown)}")
        return methods

    @field_validator("settings", mode="before")
    @classmethod
    def _lower(cls, value: Any) -> Any:
        return {str(k).lower(): v for k, v in (value or {}).items()}


def load_verifier_config(path: Path) -> VerifierExperiment:
    path = Path(path).resolve()
    try:
        config = VerifierExperiment.model_validate(yaml.safe_load(path.read_text("utf-8")))
    except (OSError, yaml.YAMLError, ValidationError) as exc:
        raise ConfigError(f"Invalid verifier config {path}:\n{exc}") from exc
    config.labels = (path.parent / config.labels).resolve()
    check_overrides(config.settings)
    return config


def evaluate_verifiers(
    config: VerifierExperiment,
    settings: Settings,
    results_root: Path,
    *,
    llm_factory=build_llm,
    log=print,
) -> Path:
    labels = load_labels(config.labels)
    settings = Settings.model_validate(settings.model_dump() | config.settings)
    human = [row["human_verdict"] for row in labels]
    log(f"{len(labels)} labelled statements; methods: {', '.join(config.methods)}")

    llm: LLMProvider | None = None
    methods: dict[str, Any] = {}
    predictions: dict[str, list[dict]] = {}
    for method in config.methods:
        if method == "llm_judge" and llm is None:
            llm = llm_factory(settings)
        verifier = build_verifier(method, nli_model=settings.verifier_nli_model, llm=llm)
        rows, tokens = [], 0
        started = time.perf_counter()
        for row in labels:
            passages = row["passage_list"]
            candidates = passages + (["\n\n".join(passages)] if len(passages) > 1 else [])
            [judgement] = verifier.judge([row["statement"]], [candidates])
            tokens += sum(getattr(verifier, "last_usage", (0, 0)) or (0, 0))
            rows.append(
                {
                    "claim_id": row.get("claim_id"),
                    "statement": row["statement"],
                    "human": row["human_verdict"],
                    "predicted": judgement.verdict,
                    "score": judgement.score,
                    "reason": judgement.reason,
                }
            )
        elapsed = (time.perf_counter() - started) * 1000
        predicted = [r["predicted"] for r in rows]
        correct = [float(h == p) for h, p in zip(human, predicted, strict=True)]
        model = settings.verifier_nli_model if method in ("nli", "nli_lexical") else None
        if method == "llm_judge":
            model = settings.llm_model if settings.llm_provider != "fake" else "fake"
        methods[method] = agreement(human, predicted) | {
            "accuracy_ci": summarize(correct, seed=config.seed),
            "ms_per_claim": elapsed / len(labels),
            "tokens": tokens,
            "model": model,
        }
        predictions[method] = rows
        a = methods[method]
        log(
            f"  {method}: accuracy {a['accuracy']:.3f}, kappa "
            f"{a['cohen_kappa'] if a['cohen_kappa'] is None else round(a['cohen_kappa'], 3)}, "
            f"unsupported-detection F1 {a['detection']['f1']:.3f}"
        )

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = Path(results_root) / config.name / stamp
    n = 1
    while out.exists():
        n += 1
        out = Path(results_root) / config.name / f"{stamp}-{n}"
    out.mkdir(parents=True)
    distribution = {v: human.count(v) for v in VERDICTS}
    summary = {
        "kind": "verifier",
        "experiment": config.name,
        "run": out.name,
        "description": config.description,
        "finished_at": datetime.now(UTC).isoformat(),
        "labels": {"file": config.labels.name, "n": len(labels), "distribution": distribution},
        "methods": methods,
        "warnings": (
            [f"Only {len(labels)} labelled statements: accuracy intervals are wide."]
            if len(labels) < 100
            else []
        ),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    with (out / "predictions.jsonl").open("w", encoding="utf-8") as f:
        for method, rows in predictions.items():
            for row in rows:
                f.write(json.dumps({"method": method} | row) + "\n")
    (out / "report.md").write_text(_markdown(summary), encoding="utf-8")
    log(f"Done: {out / 'report.md'}")
    return out


def _markdown(summary: dict) -> str:
    lines = [
        f"# {summary['experiment']} — {summary['run']}",
        "",
        f"{summary['labels']['n']} labelled statements ({summary['labels']['file']}): "
        + ", ".join(f"{k} {v}" for k, v in summary["labels"]["distribution"].items()),
        "",
    ]
    lines += [f"> **Note:** {w}" for w in summary["warnings"]]
    lines += [
        "",
        "| Method | Accuracy [95% CI] | Cohen's κ | Macro-F1 | Unsupported detection P / R / F1 "
        "| ms/claim |",
        "|---|---|---|---|---|---|",
    ]
    for method, m in summary["methods"].items():
        ci = m["accuracy_ci"]
        acc = f"{m['accuracy']:.3f}"
        if ci["ci_low"] is not None:
            acc += f" [{ci['ci_low']:.3f}, {ci['ci_high']:.3f}]"
        kappa = "–" if m["cohen_kappa"] is None else f"{m['cohen_kappa']:.3f}"
        d = m["detection"]
        lines.append(
            f"| {method} | {acc} | {kappa} | {m['macro_f1']:.3f} | "
            f"{d['precision']:.2f} / {d['recall']:.2f} / {d['f1']:.2f} | {m['ms_per_claim']:.0f} |"
        )
    for method, m in summary["methods"].items():
        lines += ["", f"Confusion matrix — {method} (rows: human, columns: verifier)", ""]
        lines.append("| human \\ verifier | " + " | ".join(VERDICTS) + " |")
        lines.append("|---|" + "---|" * len(VERDICTS))
        for h in VERDICTS:
            counts = " | ".join(str(m["confusion"][h][p]) for p in VERDICTS)
            lines.append(f"| {h} | {counts} |")
    return "\n".join(lines) + "\n"
