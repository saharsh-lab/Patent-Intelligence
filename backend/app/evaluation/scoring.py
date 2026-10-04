"""Score one stored run against its labelled question → one row of metric values.

Everything is read from what the run stored (`agent_runs.answer`, `plan`, tool calls),
so a run can be re-scored later without re-running it. A metric is `None` when it does
not apply (e.g. retrieval metrics for an unanswerable question, tool metrics for the
baseline, grounding for an abstention) and is then left out of the averages.
"""

from dataclasses import dataclass

from app.evaluation.dataset import Dataset, EvalItem, _patent_key
from app.evaluation.metrics import key_fact_recall, retrieval_metrics, tool_selection
from app.models import AgentRun


@dataclass(frozen=True)
class MetricInfo:
    key: str
    label: str
    group: str
    higher_is_better: bool | None  # None: neither (descriptive only)
    format: str  # percent | ratio | ms | count | usd | tokens


METRICS = [
    MetricInfo("precision_at_k", "Precision@k", "Retrieval", True, "percent"),
    MetricInfo("recall_at_k", "Recall@k", "Retrieval", True, "percent"),
    MetricInfo("mrr", "MRR", "Retrieval", True, "ratio"),
    MetricInfo("hit_at_k", "Hit@k", "Retrieval", True, "percent"),
    MetricInfo("context_precision", "Context precision", "Retrieval", True, "percent"),
    MetricInfo("context_recall", "Context recall", "Retrieval", True, "percent"),
    MetricInfo("source_recall", "Right sources found", "Retrieval", True, "percent"),
    MetricInfo("source_precision", "Passages from right sources", "Retrieval", True, "percent"),
    MetricInfo("key_fact_recall", "Key-fact recall", "Answer", True, "percent"),
    MetricInfo("abstention_correct", "Answer/abstain correct", "Answer", True, "percent"),
    MetricInfo("citation_coverage", "Citation coverage", "Grounding", True, "percent"),
    MetricInfo("invalid_citations", "Invalid citations", "Grounding", False, "count"),
    MetricInfo("grounding_score", "Grounding score", "Grounding", True, "percent"),
    MetricInfo("unsupported_rate", "Unsupported-claim rate", "Grounding", False, "percent"),
    MetricInfo("misattribution_rate", "Misattribution rate", "Grounding", False, "percent"),
    MetricInfo("regenerated", "Regenerated", "Grounding", None, "percent"),
    MetricInfo("regeneration_gain", "Regeneration gain", "Grounding", True, "ratio"),
    MetricInfo("cell_coverage", "Table cells cited", "Comparison", True, "percent"),
    MetricInfo("cross_source_citations", "Cross-source citations", "Comparison", False, "count"),
    MetricInfo("intent_correct", "Intent accuracy", "Agent", True, "percent"),
    MetricInfo("tool_precision", "Tool precision", "Agent", True, "percent"),
    MetricInfo("tool_recall", "Tool recall", "Agent", True, "percent"),
    MetricInfo("tools_exact", "Tool set exact", "Agent", True, "percent"),
    MetricInfo("legal_flag_correct", "Legal question flagged", "Agent", True, "percent"),
    MetricInfo("failed", "Run failed", "System", False, "percent"),
    MetricInfo("latency_ms", "Latency", "System", False, "ms"),
    MetricInfo("llm_calls", "LLM calls", "System", False, "count"),
    MetricInfo("total_tokens", "Tokens", "System", False, "tokens"),
    MetricInfo("cost_usd", "Cost", "System", False, "usd"),
]
METRIC_KEYS = [m.key for m in METRICS]


def source_metrics(evidence: list[dict], item: EvalItem, doc_of_source: dict) -> dict:
    """Document-level retrieval: were passages taken from the labelled documents?

    Added in Phase 10: in long real patents the same point is made in the abstract,
    summary, description and claims, so passage labels are rarely complete. Document-level
    metrics do not depend on finding every relevant passage."""
    wanted = {label.doc or label.patent for label in item.relevant}
    patent_of = {_patent_key(label.patent): label.patent for label in item.relevant if label.patent}
    found = []
    for e in evidence:
        source = doc_of_source.get(e.get("source_label") or "")
        if source is None:  # an imported patent: compare publication numbers
            source = patent_of.get(_patent_key(e.get("source_label")))
        found.append(source)
    return {
        "source_recall": len(wanted & set(found)) / len(wanted),
        "source_precision": sum(s in wanted for s in found) / len(found) if found else 0.0,
    }


def score_run(run: AgentRun, item: EvalItem, dataset: Dataset, k: int) -> dict:
    answer = run.answer or {}
    plan = run.plan or {}
    answered = run.status == "succeeded"
    row: dict = dict.fromkeys(METRIC_KEYS)
    row |= {
        "status": run.status,
        "failed": float(run.status == "failed"),
        "latency_ms": run.latency_ms,
        "llm_calls": (run.config or {}).get("llm_calls", int(bool(answer.get("llm_called")))),
        "total_tokens": (run.prompt_tokens or 0) + (run.completion_tokens or 0),
        "cost_usd": float(run.cost_usd) if run.cost_usd is not None else 0.0,
    }
    if run.status == "failed":
        row["error"] = run.error_message
        return row

    # --- retrieval (only meaningful when the question has labelled passages)
    evidence = answer.get("evidence") or []
    row["n_retrieved"] = len(evidence)
    similarities = [e["vector_similarity"] for e in evidence if e.get("vector_similarity")]
    row["top_similarity"] = max(similarities) if similarities else None
    if item.relevant:
        doc_of_source = dataset.doc_of_source
        matches = [
            {i for i, label in enumerate(item.relevant) if label.matches(e, doc_of_source)}
            for e in evidence
        ]
        row |= retrieval_metrics(matches, len(item.relevant), k)
        row["relevant_ranks"] = [i + 1 for i, m in enumerate(matches) if m]
        row |= source_metrics(evidence, item, doc_of_source)

    # --- answer
    row["abstained"] = run.status == "insufficient_evidence"
    row["abstention_correct"] = float(answered == item.answerable)
    if answered:
        row["key_fact_recall"] = key_fact_recall(answer.get("text") or "", item.key_facts)
        row["citation_coverage"] = answer.get("citation_coverage")
        row["invalid_citations"] = len(answer.get("invalid_citations") or [])

        verification = answer.get("verification")
        if verification and verification.get("claims"):
            counts, n = verification["counts"], len(verification["claims"])
            row["grounding_score"] = verification["grounding_score"]
            row["unsupported_rate"] = counts["unsupported"] / n
            row["misattribution_rate"] = counts["misattributed"] / n
            row["claims_checked"] = n
            attempts = answer.get("verification_attempts") or []
            row["regenerated"] = float(len(attempts) > 1)
            if len(attempts) > 1:
                row["regeneration_gain"] = (row["grounding_score"] or 0) - (
                    attempts[0]["grounding_score"] or 0
                )

        comparison = answer.get("comparison")
        if comparison:
            row["cell_coverage"] = comparison["metrics"].get("cell_coverage")
            row["cross_source_citations"] = comparison["metrics"].get("cross_source_citations")

    # --- agent behaviour (the baseline has no plan, intent or tool calls)
    if run.pipeline == "agentic":
        used = [call.tool_name for call in run.tool_calls]
        row["tools_used"] = used
        row["intent"] = plan.get("intent")
        if item.expected_intent:
            row["intent_correct"] = float(plan.get("intent") == item.expected_intent)
        if item.expected_tools is not None:
            row |= tool_selection(item.expected_tools, used)
        if item.legal is not None:
            flagged = bool((plan.get("analysis") or {}).get("legal_question"))
            row["legal_flag_correct"] = float(flagged == item.legal)
    return row
