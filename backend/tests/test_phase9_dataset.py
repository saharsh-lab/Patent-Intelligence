"""Phase 9 (no database): dataset format, relevance matching, experiment configs."""

import textwrap

import pytest

from app.core.config import PROJECT_ROOT, Settings, get_settings
from app.evaluation.config import ConfigError, load_config, variant_settings
from app.evaluation.dataset import DatasetError, RelevanceLabel, load_dataset
from app.evaluation.report import format_value, threshold_sweep
from app.evaluation.results import read_result

DEV = PROJECT_ROOT / "experiments" / "datasets" / "dev" / "dataset.yaml"
CONFIGS = PROJECT_ROOT / "experiments" / "configs"


def test_dev_dataset_loads():
    dataset = load_dataset(DEV)
    assert len(dataset.items) == 20 and dataset.synthetic
    assert {e.filename for e in dataset.corpus} == {
        "battery_patent.txt",
        "wireless_patent.txt",
        "immersion_cooling.txt",
    }
    assert sum(not i.answerable for i in dataset.items) == 3
    assert len(dataset.fingerprint()) == 64


@pytest.mark.parametrize("name", [p.stem for p in CONFIGS.glob("exp_[a-h]_*.yaml")] + ["smoke"])
def test_every_experiment_config_is_valid(name):
    config = load_config(CONFIGS / f"{name}.yaml")
    for variant in config.variants:
        variant_settings(get_settings(), config, variant)


PASSAGE = {
    "source_label": "battery_patent.txt",
    "section": "claims",
    "claim_number": 3,
    "text": "3. The system of claim 1, wherein the controller limits the charging\n current.",
}
DOCS = {"battery_patent.txt": "battery"}


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        (RelevanceLabel(doc="battery", claim=3), True),
        (RelevanceLabel(doc="battery", contains="LIMITS the charging current"), True),
        (RelevanceLabel(doc="battery", claim=3, contains="coolant"), False),  # all must hold
        (RelevanceLabel(doc="battery", section="abstract"), False),
        (RelevanceLabel(doc="wireless", claim=3), False),
    ],
)
def test_relevance_matching(label, expected):
    assert label.matches(PASSAGE, DOCS) is expected


def test_patent_labels_ignore_kind_codes():
    passage = {"source_label": "EP1234567A1", "text": "x", "section": None, "claim_number": None}
    assert RelevanceLabel(patent="EP 1234567 B1").matches(passage, {})
    assert not RelevanceLabel(patent="EP7654321").matches(passage, {})


def write_dataset(tmp_path, items: str):
    (tmp_path / "doc.txt").write_text("Some text about pumps.")
    path = tmp_path / "dataset.yaml"
    path.write_text(
        "corpus:\n  - {id: doc, file: doc.txt}\nitems:\n" + textwrap.indent(items, "  ")
    )
    return path


@pytest.mark.parametrize(
    ("items", "message"),
    [
        (  # typo: would silently drop the labels
            "- {id: a, type: lookup, question: q, relevent: [{doc: doc, claim: 1}]}",
            "unknown keys",
        ),
        ("- {id: a, type: lookup, question: q}", "at least one 'relevant'"),
        ("- {id: a, type: lookup, question: q, scope: [nope], relevant: []}", "scope"),
        ("- {id: a, type: guess, question: q}", "unknown type"),
        (
            "- {id: a, type: unanswerable, question: q, expected_tools: [web_search]}",
            "unknown tools",
        ),
        ("- {id: a, type: lookup, question: q, relevant: [{doc: doc}]}", "to locate"),
        (
            "- {id: a, type: unanswerable, question: q}\n"
            "- {id: a, type: unanswerable, question: r}",
            "duplicate item id",
        ),
    ],
)
def test_dataset_errors_are_specific(tmp_path, items, message):
    with pytest.raises(DatasetError, match=message):
        load_dataset(write_dataset(tmp_path, items))


def write_config(tmp_path, body: str):
    path = tmp_path / "exp.yaml"
    path.write_text(f"name: t\ndataset: {DEV}\n" + body)
    return path


def test_config_rejects_unknown_and_forbidden_settings(tmp_path):
    bad = "variants:\n  - {name: a, pipeline: baseline, settings: {retrieval_topk: 3}}\n"
    with pytest.raises(ConfigError, match="Unknown setting"):
        load_config(write_config(tmp_path, bad))
    bad = "settings: {DATABASE_URL: x}\nvariants:\n  - {name: a, pipeline: baseline}\n"
    with pytest.raises(ConfigError, match="cannot be changed"):
        load_config(write_config(tmp_path, bad))
    bad = "variants:\n  - {name: a, pipeline: magic}\n"
    with pytest.raises(ConfigError):
        load_config(write_config(tmp_path, bad))


def test_variant_settings_precedence_and_validation(tmp_path, monkeypatch):
    config = load_config(
        write_config(
            tmp_path,
            "settings: {RETRIEVAL_TOP_K: 4, chunking_strategy: fixed}\n"
            "variants:\n"
            "  - {name: a, pipeline: baseline, settings: {retrieval_top_k: 9}}\n"
            "  - {name: b, pipeline: baseline, settings: {retrieval_top_k: 0}}\n",
        )
    )
    base = Settings(patent_demo_source=True)
    monkeypatch.setenv("RETRIEVAL_TOP_K", "2")  # must not leak in: no re-reading of .env
    a = variant_settings(base, config, config.variants[0])
    assert (a.retrieval_top_k, a.chunking_strategy) == (9, "fixed")
    assert a.patent_demo_source is False  # demo patents never enter experiments by default
    with pytest.raises(ConfigError, match="invalid settings"):
        variant_settings(base, config, config.variants[1])  # top_k must be ≥ 1


def test_threshold_sweep_and_formatting():
    rows = [
        {"variant": "v", "item_id": "a", "top_similarity": 0.8},
        {"variant": "v", "item_id": "b", "top_similarity": 0.2},
    ]
    sweep = threshold_sweep(rows, "v", {"a": True, "b": False})
    best = max(sweep, key=lambda p: p["accuracy"])
    assert best["accuracy"] == 1.0 and 0.2 < best["threshold"] <= 0.8
    assert threshold_sweep(rows, "v", {"a": True, "b": True}) == []  # needs both classes
    assert format_value(0.1234, "percent") == "12.3%"
    assert format_value(None, "ms") == "–"


@pytest.mark.parametrize(("experiment", "run"), [("..", "x"), ("a", "../../etc"), ("a/b", "c")])
def test_result_reader_rejects_path_tricks(tmp_path, experiment, run):
    assert read_result(tmp_path, experiment, run) is None


def test_claim_labels_also_match_fixed_chunks_by_their_opening_text():
    # Fixed-size chunks carry no claim number; without the anchor, claim labels could
    # never match them and Experiment B would be biased against fixed chunking.
    item = next(i for i in load_dataset(DEV).items if i.id == "q12")
    [label] = item.relevant
    assert label.anchor.startswith("3. The system of claim 1")
    fixed_chunk = {
        "source_label": "battery_patent.txt",
        "section": None,
        "claim_number": None,
        "text": "...thermistor bonded to a casing. " + label.anchor + " rises faster than...",
    }
    assert label.matches(fixed_chunk, {"battery_patent.txt": "battery"})


def test_label_check_and_review_sheet(tmp_path):
    from app.evaluation.__main__ import check_labels, main

    dataset = load_dataset(DEV)
    assert check_labels(dataset, get_settings()) == []  # every label matches, both chunkings

    out = tmp_path / "REVIEW.md"
    assert main(["review", "--dataset", str(DEV), "--out", str(out)]) == 0
    sheet = out.read_text()
    assert sheet.count("[ ] checked") == len(dataset.items)
    assert "samples every thermistor" in sheet and "10 Hz ✓" in sheet


def test_label_check_reports_a_mistyped_quote(tmp_path):
    from app.evaluation.__main__ import check_labels

    text = DEV.read_text().replace("samples every thermistor", "samples each thermistor")
    path = tmp_path / "dataset.yaml"
    path.write_text(text.replace("corpus/", f"{DEV.parent}/corpus/"))
    problems = check_labels(load_dataset(path), get_settings())
    assert any("q01" in p and "matches nothing (section_aware)" in p for p in problems)
