"""Read result folders for the API / Evaluation page (read-only, path-safe)."""

import json
import re
from pathlib import Path

_NAME = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")


def results_root(experiments_dir: Path) -> Path:
    return Path(experiments_dir) / "results"


def list_results(experiments_dir: Path) -> list[dict]:
    root = results_root(experiments_dir)
    entries = []
    for summary_path in root.glob("*/*/summary.json"):
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue  # an interrupted run without a summary yet, or a damaged file
        entries.append(
            {
                "experiment": summary_path.parent.parent.name,
                "run": summary_path.parent.name,
                "kind": summary.get("kind", "experiment"),
                "description": summary.get("description") or "",
                "finished_at": summary.get("finished_at"),
                "dataset": (summary.get("dataset") or {}).get("name"),
                "synthetic": bool((summary.get("dataset") or {}).get("synthetic")),
                "draft_labels": "draft"
                in str((summary.get("dataset") or {}).get("labelled_by", "")).lower(),
                "n": (summary.get("dataset") or {}).get("items")
                or (summary.get("labels") or {}).get("n"),
                "variants": [v["name"] for v in summary.get("variants", [])]
                or list(summary.get("methods", {})),
            }
        )
    return sorted(entries, key=lambda e: e["finished_at"] or "", reverse=True)


def read_result(experiments_dir: Path, experiment: str, run: str) -> dict | None:
    if not (_NAME.match(experiment) and _NAME.match(run)) or ".." in experiment + run:
        return None
    root = results_root(experiments_dir).resolve()
    folder = (root / experiment / run).resolve()
    if root not in folder.parents or not (folder / "summary.json").is_file():
        return None
    summary = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
    rows_file = {"verifier": "predictions.jsonl", "selfcheck": "rows.jsonl"}.get(
        summary.get("kind", "experiment"), "runs.jsonl"
    )
    rows = []
    if (folder / rows_file).is_file():
        with (folder / rows_file).open(encoding="utf-8") as f:
            rows = [json.loads(line) for line in f if line.strip()]
    return {"summary": summary, "rows": rows}
