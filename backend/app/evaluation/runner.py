"""Experiment runner: answer every question with every variant, score, and save.

    for each variant:                      e.g. baseline, agentic
        settings = .env + config overrides (validated first, for every variant)
        (re)ingest the corpus if chunking or embedding model changed
        for each question × repeat:
            run the pipeline → stored agent_run (as in the app)
            score it against the labels → one row
            clear patents the agent imported (no leakage between questions)
    aggregate rows → summary.json, runs.csv, report.md

The runner works on whatever session it is given. The command line gives it the
separate evaluation database (it deletes and re-ingests documents, so it must never
touch the development database); tests give it the rolled-back test session.
"""

import json
import logging
import platform
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path

import yaml
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError
from app.evaluation.config import ExperimentConfig, public_settings, variant_settings
from app.evaluation.dataset import Dataset, EvalItem, load_dataset
from app.evaluation.report import aggregate, write_report
from app.evaluation.scoring import METRIC_KEYS, score_run
from app.llm.providers import LLMProvider, build_llm
from app.models import AgentRun, Document, Evaluation, Patent
from app.patents.registry import build_sources
from app.rag.embeddings import EmbeddingProvider, build_embedder
from app.services.agent import AgentService
from app.services.answering import AnswerService
from app.services.documents import DocumentService

logger = logging.getLogger(__name__)

MAX_CONSECUTIVE_FAILURES = 3  # e.g. the LLM server is down: stop instead of failing 100×


class ExperimentAborted(RuntimeError):
    pass


class ExperimentRunner:
    def __init__(
        self,
        session: Session,
        base_settings: Settings,
        results_root: Path,
        *,
        log: Callable[[str], None] = print,
        llm_factory: Callable[[Settings], LLMProvider] = build_llm,
        embedder_factory: Callable[[Settings], EmbeddingProvider] = build_embedder,
        sources_factory: Callable[[Settings], dict] = build_sources,
        after_corpus_load: Callable[[], None] | None = None,
    ):
        self.session = session
        self.base_settings = base_settings
        self.results_root = Path(results_root)
        self.log = log
        self.llm_factory = llm_factory
        self.embedder_factory = embedder_factory
        self.sources_factory = sources_factory
        self.after_corpus_load = after_corpus_load
        self._llms: dict[tuple, LLMProvider] = {}
        self._embedders: dict[tuple, EmbeddingProvider] = {}
        self._corpus_key: tuple | None = None
        self._corpus_ids: dict[str, uuid.UUID] = {}

    # ------------------------------------------------------------------ public

    def run(self, config: ExperimentConfig, dataset: Dataset | None = None) -> Path:
        dataset = dataset or load_dataset(config.dataset)
        items = self._select_items(config, dataset)
        # Validate every variant's settings before spending time on any of them
        settings_of = {
            v.name: variant_settings(self.base_settings, config, v) for v in config.variants
        }
        out_dir = self._result_dir(config.name)
        started_at = datetime.now(UTC)
        experiment_id = f"{config.name}/{out_dir.name}"
        self._write_inputs(out_dir, config, dataset, settings_of)
        self.log(
            f"Experiment {experiment_id}: {len(items)} questions × {len(config.variants)} "
            f"variants × {config.repeats} repeats → {out_dir}"
        )

        rows: list[dict] = []
        snapshots: dict[str, dict] = {}
        rows_file = (out_dir / "runs.jsonl").open("a", encoding="utf-8")
        failures = dict.fromkeys(settings_of, 0)
        try:
            for group in self._corpus_groups(dataset, config, settings_of):
                # Variants sharing an index run interleaved (question 1 with every
                # variant, then question 2, ...): a slow spell on the machine then hits
                # all variants alike instead of biasing whichever ran at that moment.
                # Observed in the Phase 10 rehearsal: two runs took 30 s instead of 4 s
                # while other work was running, all in the first variant.
                first = settings_of[group[0].name]
                self._ensure_corpus(dataset, first, self._embedder(first))
                services = {
                    v.name: self._service(
                        v.pipeline, settings_of[v.name], self._embedder(settings_of[v.name])
                    )
                    for v in group
                }
                for variant in group:  # load models before anything is timed
                    self._warm_up(services[variant.name], items[0])
                for position, item in enumerate(items):
                    for repeat in range(config.repeats):
                        # Rotate which variant goes first. Observed: the LLM server reuses
                        # the previous prompt's cache, so the second variant on the same
                        # question ran up to 40% faster. Rotating balances that out.
                        shift = (position + repeat) % len(group)
                        for variant in group[shift:] + group[:shift]:
                            row, run_config = self._run_item(
                                services[variant.name], item, dataset, config.eval_k
                            )
                            row |= {"variant": variant.name, "repeat": repeat}
                            if run_config and variant.name not in snapshots:
                                snapshots[variant.name] = run_config
                            rows.append(row)
                            rows_file.write(json.dumps(row, default=str) + "\n")
                            rows_file.flush()
                            self._store_metrics(experiment_id, row)
                            self._progress(variant.name, len(rows), item, row)
                            failed = row["status"] == "failed"
                            failures[variant.name] = failures[variant.name] + 1 if failed else 0
                            if failures[variant.name] >= MAX_CONSECUTIVE_FAILURES:
                                raise ExperimentAborted(
                                    f"{failures[variant.name]} runs in a row failed (last "
                                    f"error: {row.get('error')}). Is the LLM/embedding "
                                    "service running?"
                                )
        finally:
            rows_file.close()

        summary = aggregate(
            rows,
            config=config,
            dataset=dataset,
            experiment_id=experiment_id,
            started_at=started_at,
            snapshots=snapshots,
            extra_warnings=_model_warnings(settings_of),
        )
        write_report(out_dir, summary, rows)
        self.log(f"Done: {out_dir / 'report.md'}")
        return out_dir

    # ------------------------------------------------------------------ steps

    def _select_items(self, config: ExperimentConfig, dataset: Dataset) -> list[EvalItem]:
        if not config.items:
            return dataset.items
        wanted = set(config.items)
        unknown = wanted - {i.id for i in dataset.items}
        if unknown:
            raise ValueError(f"Unknown item ids: {sorted(unknown)}")
        return [i for i in dataset.items if i.id in wanted]

    def _corpus_groups(self, dataset, config, settings_of) -> list[list]:
        """Consecutive variants that use the same index (chunking + embedding model)."""
        groups: list[list] = []
        last_key = None
        for variant in config.variants:
            settings = settings_of[variant.name]
            key = self._corpus_key_for(dataset, settings, self._embedder(settings))
            if groups and key == last_key:
                groups[-1].append(variant)
            else:
                groups.append([variant])
            last_key = key
        return groups

    @staticmethod
    def _corpus_key_for(dataset: Dataset, settings: Settings, embedder) -> tuple:
        return (
            dataset.fingerprint(),
            settings.chunking_strategy,
            settings.chunk_max_tokens,
            settings.chunk_overlap_tokens,
            embedder.name,
        )

    def _warm_up(self, service: AnswerService, item: EvalItem) -> None:
        """One untimed question so model loading (LLM, NLI, reranker) is not billed to
        the first measured question. Its run is deleted again."""
        scope = [self._corpus_ids[d] for d in item.scope] or None
        try:
            run = service.ask(item.question, document_ids=scope)
            self.session.delete(self.session.get(AgentRun, run.id).query)  # cascades
            self.session.commit()
        except AppError:
            self.session.rollback()  # a real problem will show up in the measured runs
        finally:
            self._clear_imported_patents()

    def _ensure_corpus(self, dataset: Dataset, settings: Settings, embedder) -> None:
        """Ingest the dataset's documents, unless already ingested the same way."""
        key = self._corpus_key_for(dataset, settings, embedder)
        if key == self._corpus_key:
            return
        self.log(
            f"Ingesting corpus ({len(dataset.corpus)} documents, "
            f"{settings.chunking_strategy} chunking, {embedder.name})"
        )
        # Start from an empty index so only the dataset's documents can be retrieved
        self.session.execute(delete(Patent))
        self.session.execute(delete(Document))
        self.session.commit()
        self.session.expire_all()
        documents = DocumentService(self.session, settings, embedder)
        self._corpus_ids = {}
        for entry in dataset.corpus:
            document, _ = documents.upload(entry.path.name, entry.path.read_bytes())
            self._corpus_ids[entry.id] = document.id
        self._corpus_key = key
        if self.after_corpus_load:
            self.after_corpus_load()

    def _service(self, pipeline: str, settings: Settings, embedder) -> AnswerService:
        llm = self._llm(settings)
        if pipeline == "agentic":
            return AgentService(
                self.session, settings, embedder, llm, self.sources_factory(settings)
            )
        return AnswerService(self.session, settings, embedder, llm)

    def _run_item(
        self, service: AnswerService, item: EvalItem, dataset: Dataset, k: int
    ) -> tuple[dict, dict | None]:
        meta = {"item_id": item.id, "item_type": item.type, "question": item.question}
        scope = [self._corpus_ids[d] for d in item.scope] or None
        started = time.perf_counter()
        try:
            run = service.ask(item.question, document_ids=scope)
        except AppError as exc:
            self.session.rollback()
            row = dict.fromkeys(METRIC_KEYS) | {
                "status": "failed",
                "failed": 1.0,
                "error": exc.message,
                "latency_ms": round((time.perf_counter() - started) * 1000),
                "run_id": None,
            }
            return meta | row, None
        finally:
            self._clear_imported_patents()
        row = score_run(run, item, dataset, k)
        return meta | row | {"run_id": str(run.id)}, run.config

    def _clear_imported_patents(self) -> None:
        """Patents the agent imported for one question must not be evidence for the next."""
        self.session.execute(delete(Patent))
        self.session.commit()

    def _store_metrics(self, experiment_id: str, row: dict) -> None:
        """Also keep metric values in the `evaluations` table (queryable with SQL)."""
        if not row.get("run_id"):
            return
        details = {"variant": row["variant"], "item_id": row["item_id"], "repeat": row["repeat"]}
        for key in METRIC_KEYS:
            value = row.get(key)
            if isinstance(value, int | float):
                self.session.add(
                    Evaluation(
                        agent_run_id=uuid.UUID(row["run_id"]),
                        experiment=experiment_id[:64],
                        metric_name=key,
                        metric_value=float(value),
                        details=details,
                    )
                )
        self.session.commit()

    # ------------------------------------------------------------------ helpers

    def _llm(self, settings: Settings) -> LLMProvider:
        key = (
            settings.llm_provider,
            settings.llm_base_url,
            settings.llm_model,
            settings.llm_reasoning_effort,
        )
        if key not in self._llms:
            self._llms[key] = self.llm_factory(settings)
        return self._llms[key]

    def _embedder(self, settings: Settings) -> EmbeddingProvider:
        key = (settings.embedding_provider, settings.embedding_model, settings.embedding_dim)
        if key not in self._embedders:
            self._embedders[key] = self.embedder_factory(settings)
        return self._embedders[key]

    def _result_dir(self, name: str) -> Path:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        out = self.results_root / name / stamp
        n = 1
        while out.exists():  # two runs within the same second
            n += 1
            out = self.results_root / name / f"{stamp}-{n}"
        out.mkdir(parents=True)
        return out

    def _write_inputs(
        self,
        out_dir: Path,
        config: ExperimentConfig,
        dataset: Dataset,
        settings_of: dict[str, Settings],
    ) -> None:
        """Everything needed to reproduce the run, saved before it starts."""
        (out_dir / "config.yaml").write_text(
            yaml.safe_dump(config.model_dump(mode="json"), sort_keys=False), encoding="utf-8"
        )
        environment = {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "packages": _package_versions(),
            "dataset": {
                "name": dataset.name,
                "path": str(dataset.path),
                "sha256": dataset.fingerprint(),
                "synthetic": dataset.synthetic,
            },
            "variant_settings": {name: public_settings(s) for name, s in settings_of.items()},
        }
        (out_dir / "environment.json").write_text(
            json.dumps(environment, indent=2, default=str), encoding="utf-8"
        )

    def _progress(self, variant: str, done: int, item: EvalItem, row: dict) -> None:
        bits = [row["status"]]
        if row.get("grounding_score") is not None:
            bits.append(f"grounding {row['grounding_score']:.2f}")
        if row.get("recall_at_k") is not None:
            bits.append(f"R@k {row['recall_at_k']:.2f}")
        bits.append(f"{row.get('latency_ms') or 0} ms")
        self.log(f"  [{variant}] #{done} {item.id}: " + ", ".join(bits))


def _model_warnings(settings_of: dict[str, Settings]) -> list[str]:
    fake = sorted(
        name
        for name, s in settings_of.items()
        if s.llm_provider == "fake" or s.embedding_provider == "fake"
    )
    if not fake:
        return []
    return [
        f"Variant(s) {', '.join(fake)} used FAKE models (canned LLM answers and/or hashing "
        "embeddings): these numbers only test the framework."
    ]


def _package_versions() -> dict[str, str]:
    names = [
        "fastapi",
        "sqlalchemy",
        "langgraph",
        "pgvector",
        "pymupdf",
        "sentence-transformers",
        "torch",
    ]
    versions = {}
    for name in names:
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = "not installed"
    return versions


def rescore(
    session: Session,
    result_dir: Path,
    *,
    dataset_path: Path | None = None,
    log: Callable[[str], None] = print,
) -> Path:
    """Score an existing result's stored runs again with the current labels and scoring
    code, without calling any model. Use after labels are corrected (e.g. by the second
    labeller) or a scoring bug is fixed. Writes a new folder next to the original:
    <run>-rescored-<timestamp>."""
    result_dir = Path(result_dir)
    raw_config = yaml.safe_load((result_dir / "config.yaml").read_text(encoding="utf-8"))
    config = ExperimentConfig.model_validate(raw_config)
    if dataset_path is not None:
        config.dataset = Path(dataset_path).resolve()
    dataset = load_dataset(config.dataset)
    items = {item.id: item for item in dataset.items}
    old_summary = json.loads((result_dir / "summary.json").read_text(encoding="utf-8"))

    rows: list[dict] = []
    missing_items: set[str] = set()
    for line in (result_dir / "runs.jsonl").read_text(encoding="utf-8").splitlines():
        old = json.loads(line)
        item = items.get(old["item_id"])
        if item is None:
            missing_items.add(old["item_id"])
            continue
        meta = {
            "item_id": item.id,
            "item_type": item.type,
            "question": item.question,
            "variant": old["variant"],
            "repeat": old["repeat"],
        }
        run = session.get(AgentRun, uuid.UUID(old["run_id"])) if old.get("run_id") else None
        if run is None:
            if old.get("run_id"):
                raise ValueError(
                    f"Run {old['run_id']} is not in this database; rescoring needs the "
                    "evaluation database the experiment was run on."
                )
            rows.append(old | meta)  # a failed run stays failed
            continue
        rows.append(meta | score_run(run, item, dataset, config.eval_k) | {"run_id": old["run_id"]})

    out = result_dir.parent / f"{result_dir.name}-rescored-{datetime.now():%Y%m%d-%H%M%S}"
    out.mkdir()
    (out / "config.yaml").write_text((result_dir / "config.yaml").read_text("utf-8"), "utf-8")
    if (result_dir / "environment.json").exists():
        (out / "environment.json").write_text(
            (result_dir / "environment.json").read_text("utf-8"), "utf-8"
        )
    with (out / "runs.jsonl").open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, default=str) + "\n")

    warnings = [w for w in old_summary.get("warnings", []) if "FAKE models" in w]
    caveats = [
        f"Rescored from run {result_dir.name} with the current labels and scoring code "
        "(the answers themselves were not regenerated)."
    ]
    if missing_items:
        warnings.append(f"Items no longer in the dataset were dropped: {sorted(missing_items)}")
    summary = aggregate(
        rows,
        config=config,
        dataset=dataset,
        experiment_id=f"{config.name}/{out.name}",
        started_at=datetime.fromisoformat(old_summary["started_at"]),
        snapshots={v["name"]: v.get("run_config") for v in old_summary.get("variants", [])},
        extra_warnings=warnings,
        extra_caveats=caveats,
    )
    summary["rescored_from"] = result_dir.name
    write_report(out, summary, rows)
    log(f"Rescored {len(rows)} runs → {out / 'report.md'}")
    return out
