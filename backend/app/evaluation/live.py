"""Experiment E: answering questions about brand-new patents, with and without live data.

Patents published after the LLM's training data are fetched live from EPO. Each question
asks what a given claim of one of them specifies; the ground truth is the claim text
itself, fetched when the question set is built and frozen in it, so no human labels are
needed. Three variants answer every question:

  live         the agent with live EPO access (imports the named patent on demand)
  local_only   the same agent with no patent source (the honest answer is "not found")
  closed_book  the LLM alone, without retrieval (shows what the model claims to know)

Every answer is judged by the NLI verifier against the patent's real claims and abstract
("supported by the patent"): the same yardstick for all three variants.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError
from app.evaluation.metrics import paired_difference, percentile, summarize
from app.llm.providers import ChatMessage, LLMProvider
from app.models import Patent
from app.patents.base import PatentQuery, PatentSource
from app.patents.numbers import normalize_publication_number
from app.verification.verifiers import PARTIAL, SUPPORTED, UNSUPPORTED, Verifier, _content_words

VARIANTS = ("live", "local_only", "closed_book")
VARIANT_INFO = {
    "live": ("agentic", "Agent with live EPO access"),
    "local_only": ("agentic", "Same agent, no patent source (local documents only)"),
    "closed_book": ("llm_only", "LLM alone, no retrieval"),
}
CLOSED_BOOK_PROMPT = (
    "You are an expert on patents. Answer the user's question about a patent in a few "
    "sentences. If you do not know the patent, say so."
)
# "12. A system…", and cancelled ranges such as "3.-4. (canceled)"
_CLAIM = re.compile(r"(?m)^\s*(\d{1,3})(?:\s*[.)]?\s*[-–]\s*\d{1,3})?\s*[.)]\s*")
_CITATION = re.compile(r"\[(?:E\d+|\?)(?:\s*[,;]\s*E?\d+)*\]")
_DONT_KNOW = re.compile(
    r"\b(i (do not|don't|cannot|can't) (know|find|access)|not (aware|familiar)|no (specific )?"
    r"information|unable to (find|provide|access)|do not have (access|information)|"
    r"insufficient evidence)\b",
    re.IGNORECASE,
)
# claim boilerplate that says nothing about the invention (after the crude stemming)
_BOILERPLATE = {
    "claim",
    "wherein",
    "compris",
    "includ",
    "provid",
    "configur",
    "further",
    "more",
    "least",
    "plurality",
    "said",
    "method",
    "according",
    "any",
    "preceding",
    "other",
}
_ENGLISH = {"the", "of", "a", "and", "to", "wherein", "comprising", "said", "is", "which"}


def normalize_number(text: str) -> str:
    """Normalised publication number, or "" for labels that are not one (file names)."""
    try:
        return normalize_publication_number(text)
    except ValueError:
        return ""


# ------------------------------------------------------------------ configuration


class LiveConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str = ""
    dataset: Path  # the frozen question set (JSON) written by `live-build`
    source: str = "epo"
    topics: dict[str, str] = Field(min_length=1)  # topic name -> search keywords
    published_from: date
    published_to: date | None = None
    per_topic: int = Field(default=5, ge=1, le=20)
    countries: list[str] = Field(default_factory=lambda: ["EP"])


def load_live_config(path: Path) -> LiveConfig:
    path = Path(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["dataset"] = (path.parent / data["dataset"]).resolve()
    return LiveConfig.model_validate(data)


# ------------------------------------------------------------------ building the question set


def split_claims(claims_text: str) -> dict[int, str]:
    """Numbered claims ("1. A system…", "2. The system of claim 1…") → {number: text}."""
    starts = list(_CLAIM.finditer(claims_text or ""))
    claims = {}
    for i, match in enumerate(starts):
        end = starts[i + 1].start() if i + 1 < len(starts) else len(claims_text)
        text = re.sub(r"\s+", " ", claims_text[match.start() : end]).strip()
        number = int(match.group(1))
        body = _CLAIM.sub("", text, count=1)
        if re.search(r"(?i)claimed is\s*:?\s*$", body) or re.fullmatch(r"(?i)claims\W*", body):
            continue  # a heading such as "1. CLAIMS What is claimed is:"
        if number not in claims and "(canceled)" not in text.lower():
            claims[number] = text
    return claims


def looks_english(text: str) -> bool:
    words = re.findall(r"[a-z]+", text.lower())[:200]
    return bool(words) and sum(w in _ENGLISH for w in words) / len(words) > 0.12


def is_dependent(claim_text: str) -> bool:
    return re.search(r"(?i)\b(of|to|in) (any (one )?of )?claims? \d", claim_text) is not None


def target_words(claim_text: str) -> list[str]:
    """What a correct answer should mention: for a dependent claim, the feature it adds
    (the part after "wherein"); for an independent claim, all its content words."""
    lowered = claim_text.lower()
    dependent = is_dependent(claim_text) and "wherein" in lowered
    part = claim_text[lowered.index("wherein") :] if dependent else claim_text
    part = re.sub(r"^\d+\s*[.)]\s*", "", part)
    return sorted(_content_words(part) - _BOILERPLATE)


def _dependent_claim(claims: dict[int, str]) -> int | None:
    for number, text in sorted(claims.items()):
        if (
            number > 1
            and is_dependent(text)
            and "wherein" in text.lower()
            and len(target_words(text)) >= 4
        ):
            return number
    return None


def build_live_dataset(config: LiveConfig, source: PatentSource, log=print) -> dict:
    """Search the live source per topic, fetch each hit's claims, write the frozen set."""
    items: list[dict] = []
    seen: set[str] = set()
    for topic, keywords in config.topics.items():
        page = source.search(
            PatentQuery(
                keywords=keywords,
                date_from=config.published_from,
                date_to=config.published_to,
                limit=min(100, config.per_topic * 6),
                countries=config.countries,
            )
        )
        log(f"{topic}: {page.total} hits for {page.query_string!r}")
        taken = 0
        for record in page.results:
            number = record.publication_number
            if taken >= config.per_topic or number in seen:
                continue
            if not any(number.startswith(c) for c in config.countries):
                continue
            try:
                details = source.get_details(number)
            except AppError as exc:
                log(f"  {number}: skipped ({exc.message})")
                continue
            claims = split_claims(details.claims_text or "")
            if 1 not in claims or not looks_english(claims[1]):
                log(f"  {number}: skipped (no English claims)")
                continue
            dependent = _dependent_claim(claims)
            if dependent is None:
                log(f"  {number}: skipped (no usable dependent claim)")
                continue
            seen.add(number)
            taken += 1
            base = {
                "topic": topic,
                "publication_number": number,
                "publication_date": str(details.publication_date or record.publication_date),
                "title": details.title or record.title,
                "abstract": details.abstract or "",
                "claims": {str(n): t for n, t in claims.items()},
            }
            for kind, claim, question in (
                ("independent_claim", 1, f"What does claim 1 of {number} cover?"),
                ("dependent_claim", dependent, f"What does claim {dependent} of {number} add?"),
            ):
                items.append(
                    base
                    | {
                        "id": f"e{len(items) + 1:02d}",
                        "type": kind,
                        "claim": claim,
                        "question": question,
                        "target_words": target_words(claims[claim]),
                    }
                )
            log(f"  {number}: claims 1 and {dependent} ({details.publication_date})")
    dataset = {
        "name": config.dataset.parent.name,
        "built_at": datetime.now(UTC).isoformat(),
        "source": config.source,
        "published_from": str(config.published_from),
        "published_to": str(config.published_to) if config.published_to else None,
        "topics": config.topics,
        "labelled_by": "automatic: claim text fetched live from the patent office",
        "items": items,
    }
    config.dataset.parent.mkdir(parents=True, exist_ok=True)
    config.dataset.write_text(json.dumps(dataset, indent=2), encoding="utf-8")
    log(f"Wrote {len(items)} questions over {len(seen)} patents to {config.dataset}")
    return dataset


# ------------------------------------------------------------------ scoring


def statements_of(answer: str) -> list[str]:
    text = re.sub(r"\s+([.,;:!?])", r"\1", _CITATION.sub("", answer or ""))
    sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [s.strip(" -*•") for s in sentences if len(s.split()) >= 4]


def premises_for(item: dict) -> list[str]:
    claims = item["claims"]
    passages = [claims[str(item["claim"])]]
    if item["claim"] != 1 and "1" in claims:
        passages.append(claims["1"])  # a dependent claim includes claim 1's features
    if item.get("abstract"):
        passages.append(item["abstract"])
    return passages


def score_answer(item: dict, answer: str, abstained: bool, verifier: Verifier) -> dict:
    """Metrics that do not depend on how the answer was produced."""
    row: dict[str, Any] = {"abstained": float(abstained)}
    targets = set(target_words(item["claims"][str(item["claim"])]))
    words = _content_words(answer or "")
    row["claim_recall"] = 0.0 if abstained else len(targets & words) / max(1, len(targets))
    statements = [] if abstained else statements_of(answer)
    if statements:
        premises = premises_for(item)
        verdicts = [j.verdict for j in verifier.judge(statements, [premises] * len(statements))]
        points = {SUPPORTED: 1.0, PARTIAL: 0.5, UNSUPPORTED: 0.0}
        row["supported_by_patent"] = sum(points[v] for v in verdicts) / len(verdicts)
        row["unsupported_share"] = verdicts.count(UNSUPPORTED) / len(verdicts)
        row["statements"] = len(verdicts)
    return row


def _evidence_metrics(item: dict, evidence: list[dict]) -> dict:
    number = normalize_number(item["publication_number"])
    from_patent = [e for e in evidence if normalize_number(e.get("source_label") or "") == number]
    return {
        "right_patent": float(bool(from_patent)),
        "right_claim": float(any(e.get("claim_number") == item["claim"] for e in from_patent)),
    }


METRICS = [  # key, label, group, higher_is_better, format
    ("abstained", "Said it could not answer", "Answer", None, "percent"),
    ("right_patent", "Evidence from the asked patent", "Retrieval", True, "percent"),
    ("right_claim", "Asked claim retrieved", "Retrieval", True, "percent"),
    ("claim_recall", "Claim content in the answer", "Answer", True, "percent"),
    ("supported_by_patent", "Statements supported by the patent", "Truthfulness", True, "percent"),
    ("unsupported_share", "Statements contradicted/unsupported", "Truthfulness", False, "percent"),
    ("latency_ms", "Latency", "System", False, "ms"),
    ("total_tokens", "Tokens", "System", False, "tokens"),
]


# ------------------------------------------------------------------ running


class LiveRunner:
    def __init__(
        self,
        session: Session,
        settings: Settings,
        embedder,
        llm: LLMProvider,
        sources: dict[str, PatentSource],
        verifier: Verifier,
        log=print,
    ):
        self.session, self.settings, self.embedder, self.llm = session, settings, embedder, llm
        self.sources, self.verifier, self.log = sources, verifier, log

    def _agent(self, sources: dict):
        from app.services.agent import AgentService

        return AgentService(self.session, self.settings, self.embedder, self.llm, sources)

    def _clear_imported_patents(self) -> None:
        """A patent imported for one question must not help the next one or another variant."""
        self.session.execute(delete(Patent))
        self.session.commit()

    def answer(self, variant: str, item: dict) -> dict:
        started = time.perf_counter()
        if variant == "closed_book":
            response = self.llm.complete(
                [ChatMessage("system", CLOSED_BOOK_PROMPT), ChatMessage("user", item["question"])],
                temperature=0.0,
                max_tokens=600,
            )
            text = re.sub(r"(?s)<think>.*?</think>", "", response.text).strip()
            row = {
                "status": "succeeded",
                "answer": text,
                "tokens": response.prompt_tokens + response.completion_tokens,
            }
            abstained = bool(_DONT_KNOW.search(text[:300]))
            evidence = None
        else:
            sources = self.sources if variant == "live" else {}
            try:
                run = self._agent(sources).ask(item["question"])
            except AppError as exc:
                self.session.rollback()
                self._clear_imported_patents()
                return {
                    "status": "failed",
                    "error": exc.message,
                    "latency_ms": round((time.perf_counter() - started) * 1000),
                }
            answer = run.answer or {}
            text = answer.get("text") or ""
            evidence = answer.get("evidence") or []
            abstained = run.status == "insufficient_evidence" or not text.strip()
            row = {
                "status": run.status,
                "answer": text,
                "tokens": (run.prompt_tokens or 0) + (run.completion_tokens or 0),
                "run_id": str(run.id),
            }
            self._clear_imported_patents()
        row["latency_ms"] = round((time.perf_counter() - started) * 1000)
        row["total_tokens"] = row.pop("tokens")
        row |= score_answer(item, text, abstained, self.verifier)
        if evidence is not None:
            row |= _evidence_metrics(item, evidence)
        return row

    def run(
        self, config: LiveConfig, results_root: Path, variants: tuple[str, ...] = VARIANTS
    ) -> Path:
        raw = config.dataset.read_bytes()
        dataset = json.loads(raw)
        items = dataset["items"]
        started_at = datetime.now(UTC)
        out = Path(results_root) / config.name / started_at.strftime("%Y%m%d-%H%M%S")
        out.mkdir(parents=True, exist_ok=False)
        self.log(f"Experiment {config.name}: {len(items)} questions × {len(variants)} variants")
        self._clear_imported_patents()
        rows = []
        for position, item in enumerate(items):
            # rotate which variant goes first, so no variant always profits from a warm cache
            shift = position % len(variants)
            order = variants[shift:] + variants[:shift]
            for variant in order:
                row = self.answer(variant, item)
                rows.append(
                    {
                        "variant": variant,
                        "item_id": item["id"],
                        "item_type": item["type"],
                        "question": item["question"],
                        "repeat": 0,
                    }
                    | row
                )
            self.log(f"  [{position + 1}/{len(items)}] {item['id']} {item['publication_number']}")
        with (out / "runs.jsonl").open("w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, default=str) + "\n")
        summary = summarize_live(config, dataset, raw, rows, started_at, variants)
        (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        (out / "report.md").write_text(markdown_live(summary), encoding="utf-8")
        self.log(f"Done: {out / 'report.md'}")
        return out


def summarize_live(
    config: LiveConfig,
    dataset: dict,
    raw: bytes,
    rows: list[dict],
    started_at: datetime,
    variants: tuple[str, ...] = VARIANTS,
) -> dict:
    ok = [r for r in rows if r["status"] != "failed"]
    results: dict[str, dict] = {}
    per_question: dict[str, dict[str, dict]] = {}
    for variant in variants:
        results[variant] = {}
        per_question[variant] = {}
        for key, *_ in METRICS:
            values = {
                r["item_id"]: float(r[key])
                for r in ok
                if r["variant"] == variant and r.get(key) is not None
            }
            per_question[variant][key] = values
            results[variant][key] = summarize(list(values.values()))
    comparisons = []
    for variant in [v for v in variants if v != "live"] if "live" in variants else []:
        for key, *_ in METRICS:
            diff = paired_difference(per_question["live"][key], per_question[variant][key])
            if diff and diff.get("mean_diff") is not None:
                comparisons.append({"reference": "live", "variant": variant, "metric": key} | diff)
    latency = {}
    for variant in variants:
        values = [r["latency_ms"] for r in rows if r["variant"] == variant]
        latency[variant] = {"p50": percentile(values, 50), "p95": percentile(values, 95)}
    dates = sorted(i["publication_date"] for i in dataset["items"])
    return {
        "kind": "experiment",
        "experiment": config.name,
        "run": started_at.strftime("%Y%m%d-%H%M%S"),
        "description": config.description,
        "started_at": started_at.isoformat(),
        "finished_at": datetime.now(UTC).isoformat(),
        "dataset": {
            "name": dataset["name"],
            "items": len(dataset["items"]),
            "patents": len({i["publication_number"] for i in dataset["items"]}),
            "published": [dates[0], dates[-1]] if dates else None,
            "synthetic": False,
            "labelled_by": dataset["labelled_by"],
            "sha256": hashlib.sha256(raw).hexdigest(),
        },
        "repeats": 1,
        "eval_k": 0,
        "variants": [
            {
                "name": v,
                "pipeline": VARIANT_INFO[v][0],
                "description": VARIANT_INFO[v][1],
                "settings": {},
            }
            for v in variants
        ],
        "metrics": [
            {"key": k, "label": label, "group": group, "higher_is_better": hib, "format": fmt}
            for k, label, group, hib, fmt in METRICS
        ],
        "results": results,
        "latency": latency,
        "comparisons": comparisons,
        "runs": {"total": len(rows), "failed": len(rows) - len(ok)},
        "warnings": [],
        "caveats": [
            "Ground truth is the patent's own claim text and abstract, fetched live and frozen "
            "in the question set; 'supported by the patent' is the NLI verifier's judgement "
            "against them (strict; see Experiment I). Statements drawn from the description "
            "are not covered by these premises and count as unsupported.",
        ],
    }


def _fmt(stat: dict, fmt: str) -> str:
    if not stat or stat.get("mean") is None:
        return "–"

    def one(v):
        if v is None:
            return "–"
        return f"{v * 100:.1f}%" if fmt == "percent" else f"{v:,.0f}"

    if stat.get("ci_low") is None:  # a single question: no interval
        return one(stat["mean"])
    return f"{one(stat['mean'])} [{one(stat['ci_low'])}, {one(stat['ci_high'])}]"


def markdown_live(summary: dict) -> str:
    d = summary["dataset"]
    variants = [v["name"] for v in summary["variants"]]
    lines = [
        f"# {summary['experiment']} — {summary['run']}",
        "",
        summary["description"],
        "",
        f"{d['items']} questions about {d['patents']} patents published "
        f"{d['published'][0]} to {d['published'][1]}, fetched live ({d['labelled_by']}). "
        f"Runs: {summary['runs']['total']} ({summary['runs']['failed']} failed).",
        "",
        *[f"> **Note:** {c}" for c in summary["caveats"]],
        "",
        "| Metric | " + " | ".join(variants) + " |",
        "|---|" + "---|" * len(variants),
    ]
    for m in summary["metrics"]:
        cells = [_fmt(summary["results"][v].get(m["key"]), m["format"]) for v in variants]
        lines.append(f"| {m['label']} | " + " | ".join(cells) + " |")
    lines += [
        "",
        "*Mean [95% bootstrap CI] over questions.*",
        "",
        "## Paired differences vs. live",
        "",
    ]
    lines += ["| Variant | Metric | Δ mean [95% CI] | clear? |", "|---|---|---|---|"]
    labels = {m["key"]: m for m in summary["metrics"]}
    for c in summary["comparisons"]:
        fmt = labels[c["metric"]]["format"]
        scale = 100 if fmt == "percent" else 1
        unit = " pp" if fmt == "percent" else ""
        lines.append(
            f"| {c['variant']} | {labels[c['metric']]['label']} | "
            f"{c['mean_diff'] * scale:+.1f}{unit} [{(c['ci_low'] or 0) * scale:+.1f}, "
            f"{(c['ci_high'] or 0) * scale:+.1f}] | {'yes' if c['clear'] else 'no'} |"
        )
    return "\n".join(lines) + "\n"
