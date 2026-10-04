"""Phase 9 (with database): the experiment runner, claim export, verifier scoring, API."""

import csv
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.config import PROJECT_ROOT, get_settings
from app.evaluation.config import ExperimentConfig, VariantConfig
from app.evaluation.runner import ExperimentAborted, ExperimentRunner
from app.evaluation.verifier_eval import (
    VerifierExperiment,
    evaluate_verifiers,
    export_claims,
    load_labels,
)
from app.llm.providers import FakeLLM
from app.main import create_app
from app.models import AgentRun, Document, Evaluation

pytestmark = pytest.mark.db

DEV = PROJECT_ROOT / "experiments" / "datasets" / "dev" / "dataset.yaml"
FAKE = {
    "llm_provider": "fake",
    "embedding_provider": "fake",
    "reranker_enabled": False,
    "verifier_method": "lexical",
}


def make_runner(db_session, tmp_path, **kwargs):
    settings = get_settings().model_copy(update={"upload_dir": tmp_path / "uploads"})
    logs: list[str] = []
    runner = ExperimentRunner(db_session, settings, tmp_path / "results", log=logs.append, **kwargs)
    return runner, logs


def config(variants, items=None, **extra):
    return ExperimentConfig(
        name="t", dataset=DEV, settings=FAKE, variants=variants, items=items, **extra
    )


@pytest.fixture(scope="module")
def smoke(db_engine, tmp_path_factory):
    """One full smoke run (20 questions × 2 pipelines), shared by several tests.

    All tests in this module use this fixture's session: the runner deletes documents,
    and a second open transaction doing the same would wait on its row locks forever."""
    from sqlalchemy.orm import Session

    tmp_path = tmp_path_factory.mktemp("smoke")
    connection = db_engine.connect()
    outer = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    runner, logs = make_runner(session, tmp_path)
    out = runner.run(
        config(
            [
                VariantConfig(name="baseline", pipeline="baseline"),
                VariantConfig(
                    name="agentic", pipeline="agentic", settings={"agent_planner": "rules"}
                ),
            ]
        )
    )
    yield session, out, logs, tmp_path
    session.close()
    outer.rollback()
    connection.close()


def test_runner_writes_complete_results(smoke):
    session, out, logs, _ = smoke
    assert {p.name for p in out.iterdir()} >= {
        "config.yaml",
        "environment.json",
        "runs.jsonl",
        "runs.csv",
        "summary.json",
        "report.md",
    }
    rows = [json.loads(line) for line in (out / "runs.jsonl").read_text().splitlines()]
    assert len(rows) == 40 and all(r["status"] != "failed" for r in rows)
    # interleaved (each question runs with every variant before the next question) and
    # counterbalanced (the variant that goes first rotates)
    assert [(r["item_id"], r["variant"]) for r in rows[:4]] == [
        ("q01", "baseline"),
        ("q01", "agentic"),
        ("q02", "agentic"),
        ("q02", "baseline"),
    ]
    # the untimed warm-up runs were deleted again
    assert session.scalar(select(func.count(AgentRun.id))) == 40

    summary = json.loads((out / "summary.json").read_text())
    agentic, baseline = summary["results"]["agentic"], summary["results"]["baseline"]
    assert agentic["intent_correct"]["n"] == 20 and agentic["intent_correct"]["mean"] == 1.0
    assert baseline["intent_correct"]["n"] == 0  # not applicable to the baseline
    assert baseline["recall_at_k"]["n"] == 17  # the 3 unanswerable questions are excluded
    assert any("FAKE models" in w for w in summary["warnings"])
    assert any("Synthetic" in w for w in summary["warnings"])
    assert summary["variants"][1]["run_config"]["agent"]["planner"] == "rules"

    env = json.loads((out / "environment.json").read_text())
    assert "llm_api_key" not in env["variant_settings"]["agentic"]  # no secrets in results
    assert "| Recall@k |" in (out / "report.md").read_text()
    assert sum("Ingesting corpus" in line for line in logs) == 1  # same corpus for both


def test_runner_stores_metrics_and_isolates_corpus(smoke):
    session, *_ = smoke
    assert session.scalar(select(func.count(Document.id))) == 3  # only the dataset's documents
    names = set(session.scalars(select(Evaluation.metric_name).distinct()))
    assert {"recall_at_k", "grounding_score", "latency_ms", "tool_recall"} <= names


def test_comparison_questions_use_balanced_evidence(smoke):
    _, out, _, _ = smoke
    rows = [json.loads(line) for line in (out / "runs.jsonl").read_text().splitlines()]
    q16 = next(r for r in rows if r["variant"] == "agentic" and r["item_id"] == "q16")
    assert q16["tools_used"] == ["compare_patents"] and q16["intent"] == "compare"
    assert q16["context_recall"] == 1.0  # evidence from both documents


def test_chunking_change_reingests_and_labels_still_match(smoke, tmp_path):
    runner, logs = make_runner(smoke[0], tmp_path)
    out = runner.run(
        config(
            [
                VariantConfig(name="sections", pipeline="baseline"),
                VariantConfig(
                    name="fixed", pipeline="baseline", settings={"chunking_strategy": "fixed"}
                ),
            ],
            items=["q01", "q09"],
        )
    )
    assert sum("Ingesting corpus" in line for line in logs) == 2
    summary = json.loads((out / "summary.json").read_text())
    for variant in ("sections", "fixed"):  # content-based labels work for both chunkings
        assert summary["results"][variant]["hit_at_k"]["mean"] == 1.0


def test_runner_aborts_after_repeated_failures(smoke, tmp_path):
    class BrokenLLM(FakeLLM):
        def complete(self, messages, *, temperature, max_tokens):
            raise ConnectionError("LLM server unreachable")

    runner, _ = make_runner(smoke[0], tmp_path, llm_factory=lambda s: BrokenLLM())
    with pytest.raises(ExperimentAborted, match="3 runs in a row failed"):
        runner.run(config([VariantConfig(name="b", pipeline="baseline")], items=None))
    rows_file = next((tmp_path / "results" / "t").glob("*/runs.jsonl"))
    assert len(rows_file.read_text().splitlines()) == 3  # partial results are kept


def test_export_label_and_score_verifiers(smoke, tmp_path):
    session, out, _, _ = smoke
    labels = tmp_path / "labels.csv"
    n = export_claims(session, out, labels, sample=10)
    assert 0 < n <= 10
    with labels.open(newline="") as f:
        rows = list(csv.DictReader(f))
    assert "Source: " in rows[0]["passages"] and rows[0]["human_verdict"] == ""
    assert "verdict" not in {k for k in rows[0] if k != "human_verdict"}  # no system verdicts

    with pytest.raises(ValueError, match="no labelled rows"):
        load_labels(labels)
    rows[0]["human_verdict"] = "s"
    rows[1]["human_verdict"] = "unsupported"
    with labels.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    experiment = VerifierExperiment(name="vi", labels=labels, methods=["lexical"])
    result = evaluate_verifiers(
        experiment, get_settings(), tmp_path / "results", log=lambda _: None
    )
    summary = json.loads((result / "summary.json").read_text())
    lexical = summary["methods"]["lexical"]
    assert lexical["n"] == 2 and 0 <= lexical["accuracy"] <= 1
    assert summary["labels"]["distribution"]["unsupported"] == 1
    assert "Confusion matrix" in (result / "report.md").read_text()


def test_bad_verdict_label_is_rejected(tmp_path):
    path = tmp_path / "l.csv"
    path.write_text("statement,passages,human_verdict\nA claim,Some passage,maybe\n")
    with pytest.raises(ValueError, match="line 2"):
        load_labels(path)


def test_evaluation_api_lists_and_reads_results(smoke):
    _, out, _, tmp_path = smoke
    settings = get_settings().model_copy(update={"experiments_dir": tmp_path})
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings
    api = TestClient(app)

    listing = api.get("/evaluations").json()
    entry = next(e for e in listing if e["run"] == out.name)
    assert entry["kind"] == "experiment" and entry["synthetic"] and entry["n"] == 20
    assert entry["variants"] == ["baseline", "agentic"]

    detail = api.get(f"/evaluations/t/{out.name}").json()
    assert detail["summary"]["experiment"] == "t" and len(detail["rows"]) == 40
    missing = api.get("/evaluations/t/19990101-000000")
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "not_found"


def test_rescore_uses_current_labels_without_rerunning(smoke, tmp_path):
    from app.evaluation.runner import rescore

    session, out, _, _ = smoke
    edited = tmp_path / "dataset.yaml"
    text = DEV.read_text().replace(
        '{doc: battery, contains: "samples every thermistor"}', "{doc: wireless, claim: 2}"
    )
    edited.write_text(text.replace("corpus/", f"{DEV.parent}/corpus/"))
    logs: list[str] = []
    new = rescore(session, out, dataset_path=edited, log=logs.append)

    rows = {(r["variant"], r["item_id"]): r for r in map(json.loads, (new / "runs.jsonl").open())}
    assert rows[("baseline", "q01")]["recall_at_k"] == 0.0  # the label now points elsewhere
    assert rows[("baseline", "q02")]["recall_at_k"] == 1.0  # untouched labels score as before
    summary = json.loads((new / "summary.json").read_text())
    assert summary["rescored_from"] == out.name
    assert any("Rescored from" in c for c in summary["caveats"])  # a note, not a blocker


def test_paper_tables_come_from_the_summary(smoke):
    from app.evaluation.report import paper_table

    _, out, _, _ = smoke
    summary = json.loads((out / "summary.json").read_text())
    markdown = paper_table(summary)
    assert "| Metric | baseline | agentic |" in markdown
    assert markdown.startswith("> **Not reportable:**")  # fake models + synthetic data
    latex = paper_table(summary, "latex", ["grounding_score", "latency_ms"])
    assert "\\begin{tabular}{lrr}" in latex and "\\%" in latex
    assert latex.startswith("% WARNING")
