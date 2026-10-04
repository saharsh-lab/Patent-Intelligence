"""Aggregate scored rows into a summary, and write the result files.

Result folder (experiments/results/<experiment>/<timestamp>/):
    config.yaml        the experiment config as run
    environment.json   versions, dataset hash, every variant's settings (no secrets)
    runs.jsonl         one scored row per (variant, question, repeat), written live
    runs.csv           the same rows for spreadsheets
    summary.json       means, 95% CIs, paired differences (read by the Evaluation page)
    report.md          human-readable tables
"""

import csv
import json
from collections import defaultdict
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.evaluation.dataset import Dataset
from app.evaluation.metrics import paired_difference, percentile, summarize
from app.evaluation.scoring import METRICS

SMALL_N = 30  # below this many questions, say so next to every result


def aggregate(
    rows: list[dict],
    *,
    config,
    dataset: Dataset,
    experiment_id: str,
    started_at: datetime,
    snapshots: dict[str, dict],
    extra_warnings: list[str] | None = None,
) -> dict[str, Any]:
    variants = [v.name for v in config.variants]
    answerable = {item.id: item.answerable for item in dataset.items}

    # Questions are the unit: average repeats per question first
    per_item: dict[str, dict[str, dict[str, float]]] = {
        v: {m.key: {} for m in METRICS} for v in variants
    }
    collected: dict[tuple, list[float]] = defaultdict(list)
    for row in rows:
        for m in METRICS:
            value = row.get(m.key)
            if isinstance(value, int | float):
                collected[(row["variant"], m.key, row["item_id"])].append(float(value))
    for (variant, key, item_id), values in collected.items():
        per_item[variant][key][item_id] = sum(values) / len(values)

    results = {
        v: {m.key: summarize(list(per_item[v][m.key].values()), seed=config.seed) for m in METRICS}
        for v in variants
    }
    latency = {}
    for v in variants:
        values = [r["latency_ms"] for r in rows if r["variant"] == v and r.get("latency_ms")]
        latency[v] = {"p50": percentile(values, 50), "p95": percentile(values, 95)}

    comparisons = []
    reference = variants[0]
    for v in variants[1:]:
        for m in METRICS:
            diff = paired_difference(per_item[reference][m.key], per_item[v][m.key], config.seed)
            if diff:
                comparisons.append({"reference": reference, "variant": v, "metric": m.key} | diff)

    by_type: dict[str, dict[str, dict[str, float | None]]] = {}
    item_type = {item.id: item.type for item in dataset.items}
    for v in variants:
        by_type[v] = {}
        for t in sorted({item_type[i] for i in {r["item_id"] for r in rows}}):
            by_type[v][t] = {}
            for m in METRICS:
                values = [x for i, x in per_item[v][m.key].items() if item_type[i] == t]
                by_type[v][t][m.key] = sum(values) / len(values) if values else None

    n_items = len({r["item_id"] for r in rows})
    warnings = list(extra_warnings or [])
    if dataset.synthetic:
        warnings.append(
            "Synthetic development dataset: these numbers test the framework only and must "
            "not be reported as research results."
        )
    if "draft" in dataset.labelled_by.lower():
        warnings.append(
            f"Draft labels ({dataset.labelled_by}): not verified by two people yet, so these "
            "numbers must not be reported."
        )
    if n_items < SMALL_N:
        warnings.append(
            f"Only {n_items} questions: confidence intervals are wide; treat differences as "
            "indicative unless the interval excludes 0."
        )
    failed = sum(r["status"] == "failed" for r in rows)
    if failed:
        warnings.append(f"{failed} run(s) failed and are excluded from quality metrics.")

    return {
        "kind": "experiment",
        "experiment": config.name,
        "run": experiment_id.split("/", 1)[1],
        "description": config.description,
        "started_at": started_at.isoformat(),
        "finished_at": datetime.now(UTC).isoformat(),
        "dataset": {
            "name": dataset.name,
            "items": n_items,
            "synthetic": dataset.synthetic,
            "labelled_by": dataset.labelled_by,
            "sha256": dataset.fingerprint(),
        },
        "repeats": config.repeats,
        "eval_k": config.eval_k,
        "variants": [
            {
                "name": v.name,
                "pipeline": v.pipeline,
                "description": v.description,
                "settings": {**config.settings, **v.settings},
                "run_config": snapshots.get(v.name),
            }
            for v in config.variants
        ],
        "metrics": [asdict(m) for m in METRICS],
        "results": results,
        "latency": latency,
        "comparisons": comparisons,
        "by_type": by_type,
        "threshold_sweep": {v: threshold_sweep(rows, v, answerable) for v in variants},
        "runs": {"total": len(rows), "failed": failed},
        "warnings": warnings,
    }


def threshold_sweep(rows: list[dict], variant: str, answerable: dict[str, bool]) -> list[dict]:
    """For calibrating RETRIEVAL_MIN_SIMILARITY: if the sufficiency gate used threshold t,
    how often would 'answer vs. abstain' match the labels?

    Approximation: uses only the best vector similarity (the real gate also passes any
    keyword match). Needs both answerable and unanswerable questions."""
    points = [
        (r["top_similarity"], answerable[r["item_id"]])
        for r in rows
        if r["variant"] == variant and r.get("top_similarity") is not None
    ]
    if not points or len({a for _, a in points}) < 2:
        return []
    sweep = []
    for step in range(0, 20):
        t = round(step * 0.05, 2)
        correct = sum((s >= t) == a for s, a in points)
        sweep.append({"threshold": t, "accuracy": correct / len(points), "n": len(points)})
    return sweep


# ------------------------------------------------------------------ files


def write_report(out_dir: Path, summary: dict, rows: list[dict]) -> None:
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8"
    )
    _write_csv(out_dir / "runs.csv", rows)
    (out_dir / "report.md").write_text(markdown_report(summary), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict]) -> None:
    columns: list[str] = []
    for row in rows:
        columns += [k for k in row if k not in columns]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {k: json.dumps(v) if isinstance(v, list | dict) else v for k, v in row.items()}
            )


def format_value(value: float | None, fmt: str) -> str:
    if value is None:
        return "–"
    if fmt == "percent":
        return f"{value * 100:.1f}%"
    if fmt == "ms":
        return f"{value:,.0f} ms"
    if fmt == "usd":
        return f"${value:.4f}"
    if fmt in ("count", "tokens"):
        return f"{value:,.1f}" if value % 1 else f"{value:,.0f}"
    return f"{value:.3f}"


def markdown_report(summary: dict) -> str:
    variants = [v["name"] for v in summary["variants"]]
    lines = [
        f"# {summary['experiment']} — {summary['run']}",
        "",
        summary["description"] or "",
        "",
        f"Dataset **{summary['dataset']['name']}** ({summary['dataset']['items']} questions, "
        f"labelled by {summary['dataset']['labelled_by']}), {summary['repeats']} repeat(s), "
        f"k = {summary['eval_k']}. Runs: {summary['runs']['total']} "
        f"({summary['runs']['failed']} failed).",
        "",
    ]
    for warning in summary["warnings"]:
        lines.append(f"> **Note:** {warning}")
    lines += ["", "## Variants", ""]
    for v in summary["variants"]:
        settings = ", ".join(f"`{k}={val}`" for k, val in v["settings"].items()) or "defaults"
        lines.append(f"- **{v['name']}** ({v['pipeline']}): {settings}")

    lines += ["", "## Results (mean [95% CI], n questions)", ""]
    lines.append("| Metric | " + " | ".join(variants) + " |")
    lines.append("|---|" + "---|" * len(variants))
    group = None
    for m in summary["metrics"]:
        cells = []
        for v in variants:
            s = summary["results"][v][m["key"]]
            if not s["n"]:
                cells.append("–")
                continue
            text = format_value(s["mean"], m["format"])
            if s["ci_low"] is not None:
                low = format_value(s["ci_low"], m["format"])
                high = format_value(s["ci_high"], m["format"])
                text += f" [{low}, {high}]"
            cells.append(f"{text} (n={s['n']})")
        if all(c == "–" for c in cells):
            continue
        if m["group"] != group:
            group = m["group"]
            lines.append(f"| **{group}** |" + " |" * len(variants))
        lines.append(f"| {m['label']} | " + " | ".join(cells) + " |")

    lines += ["", "Latency percentiles:", ""]
    for v in variants:
        p = summary["latency"][v]
        lines.append(
            f"- {v}: p50 {format_value(p['p50'], 'ms')}, p95 {format_value(p['p95'], 'ms')}"
        )

    if summary["comparisons"]:
        info = {m["key"]: m for m in summary["metrics"]}
        lines += ["", f"## Paired differences vs. {variants[0]}", ""]
        lines.append("| Variant | Metric | Δ mean [95% CI] | wins/losses/ties | clear? |")
        lines.append("|---|---|---|---|---|")
        for c in summary["comparisons"]:
            m = info[c["metric"]]
            fmt = "ratio" if m["format"] == "percent" else m["format"]
            ci = (
                f" [{format_value(c['ci_low'], fmt)}, {format_value(c['ci_high'], fmt)}]"
                if c["ci_low"] is not None
                else ""
            )
            lines.append(
                f"| {c['variant']} | {m['label']} | {format_value(c['mean_diff'], fmt)}{ci} | "
                f"{c['wins']}/{c['losses']}/{c['ties']} | {'yes' if c['clear'] else 'no'} |"
            )
        lines += [
            "",
            "'clear' = the 95% interval excludes 0. Otherwise: no clear difference on this "
            "dataset (not the same as 'no difference').",
        ]
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------ tables for the report

PAPER_METRICS = [
    "source_recall",
    "recall_at_k",
    "mrr",
    "key_fact_recall",
    "abstention_correct",
    "grounding_score",
    "unsupported_rate",
    "latency_ms",
    "total_tokens",
]


def paper_table(summary: dict, fmt: str = "markdown", metrics: list[str] | None = None) -> str:
    """A compact results table for the report: mean [95% CI] per variant, plus the
    paired difference to the first variant, marked † when its CI excludes zero.

    Every number comes from summary.json, so tables never have to be typed by hand."""
    info = {m["key"]: m for m in summary["metrics"]}
    variants = [v["name"] for v in summary["variants"]]
    reference = variants[0]
    diffs = {(c["variant"], c["metric"]): c for c in summary["comparisons"]}
    keys = [k for k in (metrics or PAPER_METRICS) if k in info]
    keys = [k for k in keys if any(summary["results"][v][k]["n"] for v in variants)]

    def cell(variant: str, key: str) -> str:
        s, f = summary["results"][variant][key], info[key]["format"]
        if not s["n"]:
            return "–"
        text = format_value(s["mean"], f)
        if s["ci_low"] is not None:
            text += f" [{format_value(s['ci_low'], f)}, {format_value(s['ci_high'], f)}]"
        if variant != reference and (variant, key) in diffs and diffs[(variant, key)]["clear"]:
            text += " †"
        return text

    header = ["Metric", *variants]
    rows = []
    for key in keys:
        arrow = {True: " ↑", False: " ↓", None: ""}[info[key]["higher_is_better"]]
        rows.append([info[key]["label"] + arrow, *(cell(v, key) for v in variants)])

    dataset = summary["dataset"]
    caption = (
        f"{summary['experiment']}: {dataset['name']} ({dataset['items']} questions"
        f"{', synthetic' if dataset.get('synthetic') else ''}), "
        f"{summary['repeats']} repeat(s). Mean [95% bootstrap CI]; "
        f"† = paired difference to {reference} whose 95% CI excludes 0; "
        "↑/↓ = higher/lower is better."
    )
    warnings = summary.get("warnings", [])
    if fmt == "latex":

        def esc(text: str) -> str:
            for a, b in (
                ("\\", r"\textbackslash{}"),
                ("%", r"\%"),
                ("&", r"\&"),
                ("_", r"\_"),
                ("#", r"\#"),
                ("$", r"\$"),
                ("†", r"$^\dagger$"),
                ("↑", r"$\uparrow$"),
                ("↓", r"$\downarrow$"),
            ):
                text = text.replace(a, b)
            return text

        lines = [
            r"\begin{table}[ht]",
            r"\centering",
            r"\small",
            r"\begin{tabular}{l" + "r" * len(variants) + "}",
            r"\toprule",
            " & ".join(esc(h) for h in header) + r" \\",
            r"\midrule",
            *(" & ".join(esc(c) for c in row) + r" \\" for row in rows),
            r"\bottomrule",
            r"\end{tabular}",
            r"\caption{" + esc(caption) + "}",
            r"\label{tab:" + summary["experiment"].replace("_", "-") + "}",
            r"\end{table}",
        ]
        if warnings:
            lines = [f"% WARNING: {w}" for w in warnings] + lines
        return "\n".join(lines) + "\n"

    lines = [
        "| " + " | ".join(header) + " |",
        "|" + "---|" * len(header),
        *("| " + " | ".join(row) + " |" for row in rows),
        "",
        f"*{caption}*",
    ]
    if warnings:
        lines = [f"> **Not reportable:** {w}" for w in warnings] + [""] + lines
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------ results chapter

EXPERIMENT_TITLES = {
    "exp_a_pipelines": "Experiment A: baseline RAG vs. agentic RAG",
    "exp_g_verification": "Experiment G: verification and regeneration",
    "exp_f_tool_selection": "Experiment F: tool selection vs. every tool",
    "exp_h_planner": "Experiment H: rules planner vs. LLM planner",
    "exp_b_chunking": "Experiment B: section-aware vs. fixed-size chunking",
    "exp_c_topk": "Experiment C: number of passages given to the LLM",
    "exp_d_rerank": "Experiment D: cross-encoder reranking",
}
EXPERIMENT_METRICS = {
    "exp_g_verification": [
        "grounding_score",
        "unsupported_rate",
        "misattribution_rate",
        "regenerated",
        "key_fact_recall",
        "latency_ms",
        "total_tokens",
    ],
    "exp_f_tool_selection": [
        "tool_precision",
        "tools_exact",
        "source_precision",
        "key_fact_recall",
        "grounding_score",
        "llm_calls",
        "total_tokens",
        "latency_ms",
    ],
    "exp_h_planner": [
        "intent_correct",
        "tool_precision",
        "tool_recall",
        "tools_exact",
        "abstention_correct",
        "grounding_score",
        "llm_calls",
        "latency_ms",
    ],
    "exp_b_chunking": [
        "source_recall",
        "recall_at_k",
        "mrr",
        "context_precision",
        "key_fact_recall",
        "grounding_score",
        "total_tokens",
    ],
    "exp_c_topk": [
        "context_recall",
        "context_precision",
        "key_fact_recall",
        "grounding_score",
        "unsupported_rate",
        "total_tokens",
        "latency_ms",
    ],
    "exp_d_rerank": [
        "source_recall",
        "recall_at_k",
        "mrr",
        "key_fact_recall",
        "grounding_score",
        "latency_ms",
    ],
}
TYPE_METRICS = ["source_recall", "key_fact_recall", "abstention_correct", "grounding_score"]


def latest_results(results_root: Path, dataset_name: str) -> dict[str, tuple[Path, dict]]:
    """Newest result per experiment on this dataset (a rescored result supersedes the run)."""
    found: dict[str, tuple[Path, dict]] = {}
    for path in sorted(Path(results_root).glob("*/*/summary.json")):
        summary = json.loads(path.read_text(encoding="utf-8"))
        if summary.get("kind") != "experiment" or summary["dataset"]["name"] != dataset_name:
            continue
        current = found.get(summary["experiment"])
        if current is None or summary["finished_at"] > current[1]["finished_at"]:
            found[summary["experiment"]] = (path.parent, summary)
    return found


def by_type_table(summary: dict, metrics: list[str] = TYPE_METRICS) -> str:
    info = {m["key"]: m for m in summary["metrics"]}
    variants = [v["name"] for v in summary["variants"]]
    types = sorted({t for v in variants for t in summary["by_type"][v]})
    header = ["Question type", *(f"{v}: {info[m]['label']}" for m in metrics for v in variants)]
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for t in types:
        cells = [
            format_value(summary["by_type"][v].get(t, {}).get(m), info[m]["format"])
            for m in metrics
            for v in variants
        ]
        lines.append(f"| {t} | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def results_chapter(results_root: Path, dataset_name: str) -> str:
    found = latest_results(results_root, dataset_name)
    lines = [
        f"# 6. Results (generated from experiment results on `{dataset_name}`)",
        "",
        "Generated by `python -m app.evaluation results-chapter`; do not edit the tables by "
        "hand: re-generate after re-scoring. Add interpretation in the text around them.",
        "",
    ]
    if not found:
        return "\n".join(lines + ["No results for this dataset yet."]) + "\n"
    first = next(iter(found.values()))[1]
    lines += [
        f"Dataset: {first['dataset']['items']} questions, labelled by "
        f"{first['dataset']['labelled_by']}, SHA-256 `{first['dataset']['sha256'][:16]}…`.",
        "",
    ]
    order = [e for e in EXPERIMENT_TITLES if e in found] + sorted(
        e for e in found if e not in EXPERIMENT_TITLES
    )
    for experiment in order:
        folder, summary = found[experiment]
        lines += [
            f"## {EXPERIMENT_TITLES.get(experiment, experiment)}",
            "",
            f"Result: `experiments/results/{experiment}/{folder.name}`; variants: "
            + "; ".join(
                f"**{v['name']}** ({v['pipeline']}"
                + (
                    ", " + ", ".join(f"{k}={val}" for k, val in v["settings"].items())
                    if v["settings"]
                    else ""
                )
                + ")"
                for v in summary["variants"]
            )
            + ".",
            "",
            paper_table(summary, "markdown", EXPERIMENT_METRICS.get(experiment)),
        ]
        latency = summary["latency"]
        lines.append(
            "Median / p95 latency: "
            + "; ".join(
                f"{v}: {format_value(p['p50'], 'ms')} / {format_value(p['p95'], 'ms')}"
                for v, p in latency.items()
            )
            + "."
        )
        lines.append("")
        if experiment == "exp_a_pipelines":
            lines += ["By question type (means):", "", by_type_table(summary)]
    return "\n".join(lines) + "\n"
