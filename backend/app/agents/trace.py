"""Live agent trace (Phase 15): what the agent is doing, step by step, and why.

Each graph node and each tool call becomes a row: label, status (running / done /
failed), a short plain-language detail, the reason a tool was chosen, and its duration.
The rows are sent to a sink while the agent runs (the chat page polls them) and stored
with the answer afterwards. Nothing here changes what the agent does.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

NODE_LABELS = {
    "analyze": "Understanding the question",
    "resolve_targets": "Finding the documents you mean",
    "plan": "Choosing tools",
    "recover": "Trying another way",
    "generate": "Writing the answer",
    "verify": "Checking every sentence",
    "regenerate": "Rewriting with the checker's feedback",
    "finish": "Finishing",
    "small_talk": "Replying",
}
TOOL_LABELS = {
    "search_uploaded_documents": "Search your library",
    "retrieve_evidence": "Read the selected documents",
    "retrieve_document_section": "Open the requested section",
    "get_patent_details": "Fetch a patent from EPO",
    "search_patents": "Search the patent offices",
    "search_patent_abstracts": "Read patent abstracts (EPO)",
    "search_web": "Search the web",
    "extract_key_concepts": "Pull out key concepts",
    "compare_patents": "Compare the sources",
}
INTENT_LABELS = {
    "document_qa": "a question to answer from sources",
    "find_similar": "a search for related patents",
    "compare": "a comparison",
    "summarize": "a summary",
    "small_talk": "small talk",
    "out_of_scope": "outside patent research",
}


def tool_reason(tool: str, args: dict[str, Any], state: dict) -> str:
    """Why the planner picked this tool, in plain words (derived, not a model's claim)."""
    analysis = state.get("analysis")
    if tool == "search_uploaded_documents":
        return "No document was named, so the whole library is searched first."
    if tool == "retrieve_evidence":
        return "The question is about specific documents, so only they are searched."
    if tool == "retrieve_document_section":
        claim = args.get("claim_number")
        return (
            f"The question asks for claim {claim} directly."
            if claim
            else (
                f"The question asks for the {args.get('section') or 'requested'} section directly."
            )
        )
    if tool == "get_patent_details":
        return f"{args.get('number', 'A patent')} is not in the library yet, so it is fetched."
    if tool == "search_web":
        return "A general question: web pages may answer it (used for this answer only)."
    if tool == "search_patent_abstracts":
        if state.get("live_search"):
            return "The Patent DBs switch is on."
        if analysis is not None and analysis.intent == "find_similar":
            return "It asks for patents on a topic: their abstracts answer it, nothing imported."
        return "A technology question: patent filings may describe how it is done."
    if tool == "search_patents":
        return "Find similar inventions at the patent offices and import the closest."
    if tool == "extract_key_concepts":
        return "To search for similar patents, first find what the invention is about."
    if tool == "compare_patents":
        return "The question asks to compare sources side by side."
    return ""


class TraceRecorder:
    def __init__(self, sink: Callable[[list[dict]], None] | None = None):
        self.sink = sink
        self.rows: list[dict] = []
        self._t0 = time.perf_counter()

    def _ms(self) -> int:
        return round((time.perf_counter() - self._t0) * 1000)

    def _publish(self) -> None:
        if self.sink is None:
            return
        try:
            self.sink([dict(row) for row in self.rows])
        except Exception:  # noqa: BLE001 - a display problem must never stop an answer
            logger.warning("Trace sink failed", exc_info=True)

    def start(self, kind: str, name: str, label: str, why: str = "") -> dict:
        row = {
            "kind": kind,  # "step" | "tool"
            "name": name,
            "label": label,
            "status": "running",
            "detail": "",
            "why": why,
            "at_ms": self._ms(),
            "ms": None,
        }
        self.rows.append(row)
        self._publish()
        return row

    def end(self, row: dict, detail: str = "", ok: bool = True) -> None:
        row["status"] = "done" if ok else "failed"
        row["detail"] = detail
        row["ms"] = self._ms() - row["at_ms"]
        self._publish()

    def traced(self, name: str, fn: Callable[[dict], dict]) -> Callable[[dict], dict]:
        """Wrap a graph node: a row while it runs, its outcome when it ends."""

        def node(state: dict) -> dict:
            row = self.start("step", name, NODE_LABELS.get(name, name))
            try:
                update = fn(state)
            except Exception:
                self.end(row, "failed", ok=False)
                raise
            self.end(row, describe(name, state, update or {}))
            if name in ("plan", "resolve_targets") and not row["detail"]:
                self.rows.remove(row)  # nothing to say: keep the trace short
                self._publish()
            return update

        return node


def describe(node: str, state: dict, update: dict) -> str:
    """One plain-language line on what a node did."""
    if node == "analyze":
        analysis = update.get("analysis")
        if analysis is None:
            return ""
        text = f"Read as {INTENT_LABELS.get(analysis.intent, analysis.intent)}"
        if analysis.claim_number:
            text += f", about claim {analysis.claim_number}"
        if analysis.legal_question:
            text += "; it asks for a legal opinion, so only technical facts will be given"
        planner = "the LLM planner" if analysis.analyzer.startswith("llm") else "rules"
        return f"{text} (by {planner})."
    if node == "resolve_targets":
        names = [t.label for t in update.get("targets", []) if getattr(t, "label", None)]
        return f"Using {', '.join(names)}." if names else ""
    if node == "plan":
        steps = update.get("steps") or []
        if update.get("stop_reason"):
            return update["stop_reason"]
        return " → ".join(TOOL_LABELS.get(s.tool, s.tool) for s in steps)
    if node == "recover":
        recoveries = update.get("recoveries") or []
        return recoveries[-1] if recoveries else ""
    if node == "generate":
        parsed = update.get("parsed")
        if parsed is None:
            return ""
        if parsed.status != "answered":
            return "The passages did not answer the question."
        cited = ", ".join(parsed.cited_labels[:6])
        text = f"{len(parsed.sentences)} sentences, citing {cited or 'no passage'}."
        if update.get("injection") is not None and state.get("injection") is None:
            text += " Demo: one sentence was then made false (the checker is not told which)."
        return text
    if node in ("verify",):
        report = update.get("verification")
        attempts = update.get("verify_attempts") or []
        if report is None or not attempts:
            return "Nothing to check."
        latest = attempts[-1]["report"]
        counts = latest.counts()
        flagged = counts["unsupported"] + counts["partially_supported"]
        return f"{counts['supported']} of {len(latest.claims)} sentences supported" + (
            f"; {flagged} flagged." if flagged else "."
        )
    if node == "regenerate":
        added = update.get("regeneration_added_passages", 0)
        return "New draft written" + (
            f" with {added} more passage{'s' if added != 1 else ''}." if added else "."
        )
    if node == "finish":
        return update.get("stop_reason") or ""
    return ""
