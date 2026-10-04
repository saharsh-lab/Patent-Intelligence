"""Command line for the evaluation framework.

    python -m app.evaluation validate  --dataset ../experiments/datasets/dev/dataset.yaml
    python -m app.evaluation run       --config  ../experiments/configs/smoke.yaml
    python -m app.evaluation export-claims --result ../experiments/results/<exp>/<run>
    python -m app.evaluation verifier  --config  ../experiments/configs/exp_i_verifiers.yaml

Experiments run against EVAL_DATABASE_URL (a separate database, created and migrated
automatically), because the runner deletes and re-ingests its corpus.
"""

import argparse
import logging
import os
import sys
from collections import Counter
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import PROJECT_ROOT, get_settings
from app.core.logging import configure_logging
from app.evaluation.config import ConfigError, load_config, variant_settings
from app.evaluation.dataset import DatasetError, load_dataset


def _log(message: str) -> None:
    print(message, flush=True)  # flush: progress must show up even when output is piped


def prepare_eval_database(url: str, dev_url: str):
    """Create (if missing) and migrate the evaluation database; return an engine."""
    if make_url(url).render_as_string(hide_password=False) == make_url(dev_url).render_as_string(
        hide_password=False
    ):
        raise SystemExit(
            "EVAL_DATABASE_URL must differ from DATABASE_URL: experiments delete documents."
        )
    target = make_url(url)
    admin = create_engine(target.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": target.database}
        ).scalar()
        if not exists:
            print(f"Creating database {target.database}")
            conn.execute(text(f'CREATE DATABASE "{target.database}"'))
    admin.dispose()

    from alembic import command
    from alembic.config import Config

    backend = Path(__file__).resolve().parents[2]
    cfg = Config(str(backend / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend / "alembic"))
    cfg.attributes["database_url"] = url
    cfg.attributes["configure_logger"] = False
    command.upgrade(cfg, "head")
    return create_engine(url, hide_parameters=True)


def cmd_validate(args) -> int:
    dataset = load_dataset(args.dataset)
    types = Counter(item.type for item in dataset.items)
    labels = sum(len(item.relevant) for item in dataset.items)
    print(f"Dataset {dataset.name!r}: {len(dataset.items)} questions, {labels} relevance labels")
    print(f"  corpus: {', '.join(e.filename for e in dataset.corpus)}")
    print("  types: " + ", ".join(f"{t} {n}" for t, n in sorted(types.items())))
    print(f"  answerable: {sum(i.answerable for i in dataset.items)}")
    print(f"  synthetic: {dataset.synthetic}  labelled by: {dataset.labelled_by}")
    print(f"  sha256: {dataset.fingerprint()[:16]}…")
    if not args.check_labels:
        return 0
    problems = check_labels(dataset, get_settings())
    for problem in problems:
        print(f"  ✗ {problem}")
    print(f"  label check: {'OK' if not problems else f'{len(problems)} problem(s)'}")
    return 1 if problems else 0


def check_labels(dataset, settings) -> list[str]:
    """Chunk the corpus with both strategies (no database) and report every relevance
    label that matches no passage: a mistyped quote, or one split by fixed-size chunking."""
    from app.rag.ingestion import process_document

    problems = []
    for strategy in ("section_aware", "fixed"):
        passages = []
        for entry in dataset.corpus:
            processed = process_document(
                entry.filename,
                entry.path.read_bytes(),
                strategy=strategy,
                max_tokens=settings.chunk_max_tokens,
                overlap_tokens=settings.chunk_overlap_tokens,
                max_pages=settings.max_pdf_pages,
            )
            passages += [
                {
                    "source_label": entry.filename,
                    "section": chunk.section,
                    "claim_number": (chunk.meta or {}).get("claim_number"),
                    "text": chunk.text,
                }
                for chunk in processed.chunks
            ]
        for item in dataset.items:
            for label in item.relevant:
                if label.patent and not label.doc:
                    continue  # external patents are not in the corpus
                if not any(label.matches(p, dataset.doc_of_source) for p in passages):
                    problems.append(f"{item.id}: {label.describe()} matches nothing ({strategy})")

    # A key fact that none of the item's labelled documents contains can never be stated
    # with support, so it would cap key-fact recall below 100% for every system.
    from app.evaluation.dataset import normalize

    texts = {
        e.id: normalize(e.path.read_text(encoding="utf-8", errors="ignore")) for e in dataset.corpus
    }
    for item in dataset.items:
        docs = {label.doc for label in item.relevant if label.doc}
        for fact in item.key_facts:
            if docs and not any(normalize(fact) in texts[d] for d in docs if d in texts):
                problems.append(f"{item.id}: key fact {fact!r} is not in {sorted(docs)}")
    return problems


def cmd_run(args) -> int:
    from app.evaluation.runner import ExperimentRunner

    config = load_config(args.config)
    if args.items:
        config.items = [i.strip() for i in args.items.split(",") if i.strip()]
    if args.repeats:
        config.repeats = args.repeats
    if args.dataset:
        config.dataset = args.dataset.resolve()
    dataset = load_dataset(config.dataset)
    settings = get_settings().model_copy(
        update={"upload_dir": PROJECT_ROOT / "data" / "eval_uploads"}
    )
    for variant in config.variants:  # fail fast on bad settings, before touching the DB
        s = variant_settings(settings, config, variant)
        print(
            f"  variant {variant.name}: pipeline={variant.pipeline} llm={s.llm_provider}:"
            f"{s.llm_model if s.llm_provider != 'fake' else 'fake'} "
            f"embeddings={s.embedding_provider}:{s.embedding_model} "
            f"chunking={s.chunking_strategy} top_k={s.retrieval_top_k} "
            f"mode={s.retrieval_mode} rerank={s.reranker_enabled} verify={s.verify_mode}/"
            f"{s.verifier_method}"
        )
    if args.dry_run:
        print("Dry run: config and dataset are valid.")
        return 0

    engine = prepare_eval_database(settings.eval_database_url, settings.database_url)

    def vacuum() -> None:  # deleted rows leave dead HNSW entries; see tests/conftest.py
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.execute(text("VACUUM chunks"))

    with Session(engine, expire_on_commit=False) as session:
        runner = ExperimentRunner(
            session,
            settings,
            settings.experiments_dir / "results",
            log=_log,
            after_corpus_load=vacuum,
        )
        runner.run(config, dataset)
    return 0


def cmd_review(args) -> int:
    """Write a Markdown sheet for verifying a dataset: each question with the full text
    of the passages its labels point to, so reviewers need not search the patents."""
    from app.evaluation.dataset import normalize
    from app.rag.ingestion import process_document

    dataset = load_dataset(args.dataset)
    settings = get_settings()
    passages = []
    for entry in dataset.corpus:
        processed = process_document(
            entry.filename,
            entry.path.read_bytes(),
            strategy="section_aware",
            max_tokens=settings.chunk_max_tokens,
            overlap_tokens=settings.chunk_overlap_tokens,
            max_pages=settings.max_pdf_pages,
        )
        passages += [
            {
                "source_label": entry.filename,
                "section": c.section,
                "claim_number": (c.meta or {}).get("claim_number"),
                "text": c.text,
            }
            for c in processed.chunks
        ]
    title = {e.id: e.filename for e in dataset.corpus}
    lines = [
        f"# Review sheet: {dataset.name}",
        "",
        f"{len(dataset.items)} questions. For each one, check: is the question clear and "
        "realistic? Do the passages below really answer it, and is any relevant passage "
        "missing (search the corpus for it)? Are the key facts correct and short? Is the "
        "expected behaviour right? Write changes into dataset.yaml and note them in "
        "`notes`. Reviewer initials: ______",
        "",
    ]
    for item in dataset.items:
        lines += [
            f"## {item.id} ({item.type}) [ ] checked",
            "",
            f"**Q:** {item.question}",
            "",
        ]
        if item.scope:
            lines.append(f"Selected documents: {', '.join(title[d] for d in item.scope)}  ")
        if not item.answerable:
            lines.append("Expected: **abstain** (not answerable from the corpus)  ")
        lines.append(
            f"Expected intent `{item.expected_intent}`, tools `{item.expected_tools}`"
            + (f", legal flag {item.legal}" if item.legal is not None else "")
            + "  "
        )
        found_text = ""
        for label in item.relevant:
            hits = [p for p in passages if label.matches(p, dataset.doc_of_source)]
            lines += ["", f"**Label:** {label.describe()} → {len(hits)} passage(s)", ""]
            for hit in hits[:2]:
                found_text += " " + hit["text"]
                where = (
                    f"{hit['source_label']}, claim {hit['claim_number']}"
                    if hit["claim_number"]
                    else f"{hit['source_label']}, {hit['section']}"
                )
                quoted = hit["text"][:1200] + (" …" if len(hit["text"]) > 1200 else "")
                lines.append(f"> *{where}:* " + quoted.replace("\n", " "))
                lines.append("")
        if item.key_facts:
            missing = "✗ not in the passages above"
            facts = [
                f"{f} {'✓' if normalize(f) in normalize(found_text) else missing}"
                for f in item.key_facts
            ]
            lines += ["", "**Key facts:** " + "; ".join(facts)]
        if item.notes:
            lines += ["", f"*Notes:* {item.notes}"]
        lines += ["", "---", ""]
    out = args.out or args.dataset.parent / "REVIEW.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out}")
    return 0


def cmd_tables(args) -> int:
    import json

    from app.evaluation.report import paper_table

    summary = json.loads((Path(args.result) / "summary.json").read_text(encoding="utf-8"))
    if summary.get("kind") != "experiment":
        raise ValueError("tables are made from experiment results (not verifier results)")
    metrics = [m.strip() for m in args.metrics.split(",")] if args.metrics else None
    print(paper_table(summary, args.format, metrics), end="")
    return 0


def cmd_results_chapter(args) -> int:
    from app.evaluation.report import results_chapter

    settings = get_settings()
    text = results_chapter(settings.experiments_dir / "results", args.dataset_name)
    if args.out:
        args.out.write_text(text, encoding="utf-8")
        print(f"Wrote {args.out}")
    else:
        print(text, end="")
    return 0


def cmd_rescore(args) -> int:
    from app.evaluation.runner import rescore

    settings = get_settings()
    engine = prepare_eval_database(settings.eval_database_url, settings.database_url)
    with Session(engine) as session:
        rescore(session, Path(args.result).resolve(), dataset_path=args.dataset, log=_log)
    return 0


def cmd_export_claims(args) -> int:
    from app.evaluation.verifier_eval import export_claims

    settings = get_settings()
    result = Path(args.result).resolve()
    out = (
        Path(args.out)
        if args.out
        else settings.experiments_dir / "labels" / f"{result.parent.name}_{result.name}.csv"
    )
    engine = prepare_eval_database(settings.eval_database_url, settings.database_url)
    with Session(engine) as session:
        n = export_claims(session, result, out, sample=args.sample, seed=args.seed)
    print(f"Wrote {n} statements to {out}. Fill in 'human_verdict' (see docs/labelling_guide.md).")
    return 0


def cmd_selfcheck(args) -> int:
    """Invention-analysis self-check (label-free) on a dataset's corpus."""
    from app.evaluation.runner import ExperimentRunner
    from app.evaluation.selfcheck import load_selfcheck_config, run_selfcheck
    from app.invention.analysis import InventionAnalyzer
    from app.llm.providers import build_llm
    from app.rag.embeddings import build_embedder

    config = load_selfcheck_config(args.config)
    dataset = load_dataset(config.dataset)
    settings = get_settings().model_copy(
        update={"upload_dir": PROJECT_ROOT / "data" / "eval_uploads"}
    )
    engine = prepare_eval_database(settings.eval_database_url, settings.database_url)

    def vacuum() -> None:
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.execute(text("VACUUM chunks"))

    with Session(engine, expire_on_commit=False) as session:
        embedder = build_embedder(settings)
        runner = ExperimentRunner(
            session,
            settings,
            settings.experiments_dir / "results",
            log=_log,
            after_corpus_load=vacuum,
        )
        runner._ensure_corpus(dataset, settings, embedder)  # same isolated corpus as experiments
        analyzer = InventionAnalyzer(session, settings, embedder, build_llm(settings), {})
        run_selfcheck(
            session,
            analyzer,
            config,
            runner._corpus_ids,
            settings.experiments_dir / "results",
            dataset=dataset,
            log=_log,
        )
    return 0


def cmd_verifier(args) -> int:
    from app.evaluation.verifier_eval import evaluate_verifiers, load_verifier_config

    settings = get_settings()
    config = load_verifier_config(args.config)
    evaluate_verifiers(config, settings, settings.experiments_dir / "results", log=_log)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.evaluation", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("validate", help="check a dataset file and print its statistics")
    p.add_argument("--dataset", required=True, type=Path)
    p.add_argument(
        "--check-labels", action="store_true", help="check every label matches a passage"
    )
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("run", help="run an experiment config")
    p.add_argument("--config", required=True, type=Path)
    p.add_argument("--items", help="comma-separated item ids (quick partial run)")
    p.add_argument("--repeats", type=int, help="override the config's repeats")
    p.add_argument("--dataset", type=Path, help="run on this dataset instead of the config's")
    p.add_argument("--dry-run", action="store_true", help="validate only; run nothing")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("review", help="Markdown sheet for verifying a dataset's labels")
    p.add_argument("--dataset", required=True, type=Path)
    p.add_argument("--out", type=Path, help="default: REVIEW.md next to the dataset")
    p.set_defaults(func=cmd_review)

    p = sub.add_parser("tables", help="print a results table for the report")
    p.add_argument("--result", required=True, help="experiments/results/<experiment>/<run>")
    p.add_argument("--format", choices=["markdown", "latex"], default="markdown")
    p.add_argument("--metrics", help="comma-separated metric keys (default: a standard set)")
    p.set_defaults(func=cmd_tables)

    p = sub.add_parser("results-chapter", help="all results on a dataset as one Markdown chapter")
    p.add_argument("--dataset-name", required=True, help="e.g. real_test_v1")
    p.add_argument("--out", type=Path)
    p.set_defaults(func=cmd_results_chapter)

    p = sub.add_parser("rescore", help="re-score stored runs with current labels (no models)")
    p.add_argument("--result", required=True, help="experiments/results/<experiment>/<run>")
    p.add_argument("--dataset", type=Path, help="score against this dataset file instead")
    p.set_defaults(func=cmd_rescore)

    p = sub.add_parser("export-claims", help="CSV of answer statements for human labelling")
    p.add_argument("--result", required=True, help="experiments/results/<experiment>/<run>")
    p.add_argument("--out", help="output CSV (default: experiments/labels/<exp>_<run>.csv)")
    p.add_argument("--sample", type=int, help="random sample of this many statements")
    p.add_argument("--seed", type=int, default=0)
    p.set_defaults(func=cmd_export_claims)

    p = sub.add_parser("selfcheck", help="invention-analysis self-check (no labels needed)")
    p.add_argument("--config", required=True, type=Path)
    p.set_defaults(func=cmd_selfcheck)

    p = sub.add_parser("verifier", help="score verifier methods against human labels")
    p.add_argument("--config", required=True, type=Path)
    p.set_defaults(func=cmd_verifier)

    args = parser.parse_args(argv)
    configure_logging(os.environ.get("LOG_LEVEL", "WARNING"))
    logging.getLogger("httpx").setLevel(logging.WARNING)
    try:
        return args.func(args)
    except (ConfigError, DatasetError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
