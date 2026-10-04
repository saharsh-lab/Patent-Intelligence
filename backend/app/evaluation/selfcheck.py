"""Label-free, scalable evaluation of invention analysis ("self-check").

For every patent in a corpus, its own claim 1 is used as the invention description:

- **included:** the patent itself is searchable. A correct system ranks it first among
  the candidates and marks its claim's features as disclosed in it. This tests retrieval
  and the verifier end to end, with the right answer known by construction.
- **excluded:** the patent is hidden (as when a user analyses their own draft). The
  closest documents found should come from the same technical domain.

No human labels are needed, so this scales to any number of new patents; the only input
is a domain name per corpus document. It complements the hand-labelled question sets,
which remain the main evidence (self-check questions are easier: they share wording).

    experiments/configs/selfcheck_invention.yaml:
        name: selfcheck_invention
        dataset: ../datasets/real_test_v1/dataset.yaml   # its corpus is used
        domains: {fod_coils: wireless_charging, kalman: battery_thermal, ...}
"""

import json
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.evaluation.config import ConfigError
from app.evaluation.dataset import Dataset, load_dataset
from app.evaluation.metrics import summarize
from app.invention.analysis import DISCLOSED, PARTIALLY, InventionAnalyzer
from app.models import Chunk, Document


class SelfCheckConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(pattern=r"^[A-Za-z0-9_.-]{1,60}$")
    description: str = ""
    dataset: Path
    domains: dict[str, str]
    max_candidates: int = Field(default=5, ge=1, le=10)
    seed: int = 0


def load_selfcheck_config(path: Path) -> SelfCheckConfig:
    path = Path(path).resolve()
    try:
        config = SelfCheckConfig.model_validate(yaml.safe_load(path.read_text("utf-8")))
    except (OSError, yaml.YAMLError, ValidationError) as exc:
        raise ConfigError(f"Invalid self-check config {path}:\n{exc}") from exc
    config.dataset = (path.parent / config.dataset).resolve()
    return config


_DEPENDENT = re.compile(r"\b(?:of|to|in) claims? \d", re.IGNORECASE)
_CANCELED = re.compile(r"\((?:canceled|cancelled)\)", re.IGNORECASE)


def first_independent_claim(session: Session, document: Document) -> str | None:
    """Claim 1 normally; the first claim that is neither cancelled nor dependent otherwise
    (e.g. after "1.-14. (canceled)" in a continuation)."""
    chunks = session.scalars(
        select(Chunk)
        .where(Chunk.document_id == document.id)
        .where(Chunk.meta["claim_number"].isnot(None))
        .order_by(Chunk.meta["claim_number"].as_integer())
    )
    for chunk in chunks:
        if not _CANCELED.search(chunk.text) and not _DEPENDENT.search(chunk.text):
            return chunk.text
    return None


def run_selfcheck(
    session: Session,
    analyzer: InventionAnalyzer,
    config: SelfCheckConfig,
    document_ids: dict[str, Any],
    results_root: Path,
    *,
    dataset: Dataset | None = None,
    settings: Settings | None = None,
    log=print,
) -> Path:
    """`document_ids`: corpus id → ingested Document id (the corpus must be indexed)."""
    dataset = dataset or load_dataset(config.dataset)
    unknown = set(config.domains) ^ {e.id for e in dataset.corpus}
    if unknown:
        raise ConfigError(f"domains must list exactly the corpus ids; mismatch: {sorted(unknown)}")
    domain_of_label = {e.filename: config.domains[e.id] for e in dataset.corpus}

    rows = []
    for entry in dataset.corpus:
        document = session.get(Document, document_ids[entry.id])
        text = first_independent_claim(session, document)
        if not text:
            log(f"  {entry.id}: no independent claim found, skipped")
            continue
        row: dict[str, Any] = {"doc": entry.id, "domain": config.domains[entry.id]}

        started = time.perf_counter()
        included = analyzer.analyze(
            text, use_patent_search=False, max_candidates=config.max_candidates
        ).answer
        row["latency_included_ms"] = round((time.perf_counter() - started) * 1000)
        labels = [c["label"] for c in included["candidates"]]
        own = next((c for c in included["candidates"] if c["label"] == entry.filename), None)
        row["features"] = len(included["features"])
        row["feature_origin"] = included["features"][0]["origin"] if included["features"] else None
        row["self_rank"] = labels.index(entry.filename) + 1 if own else None
        row["self_found_at_1"] = float(row["self_rank"] == 1)
        row["self_in_candidates"] = float(own is not None)
        if own:
            cells = [c for c in included["cells"] if c["candidate"] == own["key"]]
            row["self_disclosed_rate"] = sum(c["verdict"] == DISCLOSED for c in cells) / len(cells)
            row["self_coverage"] = own["overlap"]

        started = time.perf_counter()
        excluded = analyzer.analyze(
            text,
            document_id=document.id,
            use_patent_search=False,
            max_candidates=config.max_candidates,
        ).answer
        row["latency_excluded_ms"] = round((time.perf_counter() - started) * 1000)
        domains = [domain_of_label.get(c["label"]) for c in excluded["candidates"]]
        row["top_candidates"] = [c["label"] for c in excluded["candidates"]][:3]
        row["same_domain_at_1"] = float(bool(domains) and domains[0] == row["domain"])
        top3 = domains[:3]
        row["same_domain_at_3"] = sum(d == row["domain"] for d in top3) / len(top3) if top3 else 0.0
        row["features_found_elsewhere"] = 1 - len(excluded["not_found_features"]) / max(
            1, len(excluded["features"])
        )
        row["partial_cells"] = sum(c["verdict"] == PARTIALLY for c in excluded["cells"])
        rows.append(row)
        log(
            f"  {entry.id}: self rank {row['self_rank']}, self coverage "
            f"{row.get('self_coverage')}, same-domain@1 {row['same_domain_at_1']:.0f}"
        )

    metrics = [
        ("self_found_at_1", "Own patent ranked first"),
        ("self_in_candidates", "Own patent among candidates"),
        ("self_disclosed_rate", "Own claim features marked disclosed"),
        ("same_domain_at_1", "Closest other document from same domain"),
        ("same_domain_at_3", "Top-3 other documents from same domain"),
        ("features_found_elsewhere", "Features found in another document"),
        ("latency_included_ms", "Latency per analysis (ms)"),
    ]
    results = {
        key: summarize([r[key] for r in rows if r.get(key) is not None], seed=config.seed)
        | {"label": label}
        for key, label in metrics
    }
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = Path(results_root) / config.name / stamp
    out.mkdir(parents=True)
    summary = {
        "kind": "selfcheck",
        "experiment": config.name,
        "run": stamp,
        "description": config.description,
        "finished_at": datetime.now(UTC).isoformat(),
        "dataset": {
            "name": dataset.name,
            "items": len(rows),
            "synthetic": dataset.synthetic,
            "sha256": dataset.fingerprint(),
        },
        "verifier": analyzer.verifier.name,
        "models": {"llm": analyzer.llm.model, "embeddings": analyzer.embedder.name},
        "results": results,
        "warnings": [
            "Self-check uses each patent's own claim as the query: easier than real user "
            "descriptions (shared wording). It tests the machinery at scale; the labelled "
            "question sets remain the main evidence."
        ],
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    with (out / "rows.jsonl").open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")
    (out / "report.md").write_text(_markdown(summary, rows), encoding="utf-8")
    log(f"Done: {out / 'report.md'}")
    return out


def _markdown(summary: dict, rows: list[dict]) -> str:
    lines = [
        f"# {summary['experiment']} — {summary['run']}",
        "",
        f"{summary['dataset']['items']} patents from {summary['dataset']['name']}; verifier "
        f"{summary['verifier']}; {summary['models']['llm']} / {summary['models']['embeddings']}.",
        "",
        *(f"> **Note:** {w}" for w in summary["warnings"]),
        "",
        "| Metric | Mean [95% CI] | n |",
        "|---|---|---|",
    ]
    for result in summary["results"].values():
        if not result["n"]:
            continue
        ci = (
            f" [{result['ci_low']:.3f}, {result['ci_high']:.3f}]"
            if result["ci_low"] is not None
            else ""
        )
        lines.append(f"| {result['label']} | {result['mean']:.3f}{ci} | {result['n']} |")
    lines += ["", "| Patent | Domain | Self rank | Self coverage | Closest other documents |"]
    lines.append("|---|---|---|---|---|")
    for r in rows:
        lines.append(
            f"| {r['doc']} | {r['domain']} | {r['self_rank'] or '–'} | "
            f"{r.get('self_coverage', '–')} | {', '.join(r['top_candidates'])} |"
        )
    return "\n".join(lines) + "\n"
