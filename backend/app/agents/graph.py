"""The agent as a LangGraph state machine.

    START → analyze ──(out of scope)──────────────────────────────► finish → END
               │
               └──► resolve_targets → plan → execute → check ──(enough)──► generate → END
                                                ▲          ├──(retry)──► recover ─┐
                                                └──────────┼──────────────────────┘
                                                           └──(give up)──► finish → END

Each node is a plain function that reads the shared `AgentState` and returns the
fields it changes. LangGraph runs the nodes and follows the edges; the
conditional edges after `analyze` and `check` are where the agent *decides*.

Why a graph instead of a free-running "LLM calls tools in a loop" agent?
- Every possible path is visible (and drawable for the report), testable, and bounded:
  at most `max_recoveries` retries, so cost and latency cannot run away.
- The LLM is used where language understanding helps (classifying the question,
  choosing search terms, writing the answer); control flow stays deterministic.
"""

import logging
import time
from dataclasses import dataclass, replace
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from sqlalchemy import select

from app.agents.analysis import (
    QueryAnalysis,
    analyze_llm,
    analyze_rules,
    asks_to_compare,
    keywords_from_text,
)
from app.agents.tools import TOOLS, Target, ToolContext, ToolResult
from app.core.errors import AppError
from app.core.ownership import restrict, visible
from app.intelligence.comparison import ComparisonBuilder
from app.llm.providers import LLMResponse
from app.models import Document, Patent
from app.rag.generation import ParsedAnswer, build_evidence, build_messages, parse_answer
from app.rag.retrieval import (
    RetrievalResult,
    RetrievedPassage,
    has_sufficient_evidence,
    retrieve,
)
from app.verification.checker import (
    VerificationReport,
    regeneration_instructions,
    verify_answer,
)
from app.verification.verifiers import build_verifier

logger = logging.getLogger(__name__)

MAX_EVIDENCE = 12

TASK_INSTRUCTIONS = {
    "compare": (
        "Compare the patents/documents in the evidence. Structure the answer as: a one-line "
        "overview of each, then 'Technical similarities', then 'Technical differences'. Cite "
        "every point. Compare technical features only."
    ),
    "find_similar": (
        "The evidence contains the user's invention and potentially relevant patents found by "
        "a patent search. For each found patent, give its publication number and title and "
        "describe the technical overlap with the user's invention, citing passages. Describe "
        "technical similarity only, never legal similarity, novelty or infringement."
    ),
}
LEGAL_INSTRUCTION = (
    "The user asked for a legal opinion. Start by saying that you cannot assess validity, "
    "infringement or legal scope, then give only the technical facts the evidence supports."
)


@dataclass
class Step:
    tool: str
    args: dict[str, Any]


class AgentState(TypedDict, total=False):
    question: str
    document_ids: list
    patent_ids: list
    analysis: QueryAnalysis
    targets: list[Target]
    steps: list[Step]
    tool_log: list[dict]
    passages: list[RetrievedPassage]
    direct_passages: list[RetrievedPassage]
    retrievals: list[RetrievalResult]
    concepts: str
    candidates: list[dict]
    attempts: int
    recoveries: list[str]
    stop_reason: str | None
    parsed: ParsedAnswer
    evidence: list
    llm_response: LLMResponse | None
    final_passages: list[RetrievedPassage]
    comparison: dict | None
    verification: VerificationReport | None
    verify_attempts: list[dict]
    regenerations: int
    extra_timings: dict[str, int]
    regeneration_added_passages: int


class AgentGraph:
    def __init__(
        self,
        ctx: ToolContext,
        *,
        planner: str,
        similar_import_limit: int,
        max_recoveries: int,
        tool_policy: str = "select",
    ):
        self.ctx = ctx
        self.planner = planner  # "rules" | "llm"
        # "select": choose tools for the question (the agent). "all": run every tool whose
        # inputs are available, whatever the question (the Experiment F control).
        self.tool_policy = tool_policy
        self.similar_import_limit = similar_import_limit
        self.max_recoveries = max_recoveries
        self._verifier = None
        self.graph = self._build()

    # ------------------------------------------------------------------ graph

    def _build(self):
        g = StateGraph(AgentState)
        g.add_node("analyze", self.analyze)
        g.add_node("resolve_targets", self.resolve_targets)
        g.add_node("plan", self.plan)
        g.add_node("execute", self.execute)
        g.add_node("check", lambda state: {})
        g.add_node("recover", self.recover)
        g.add_node("generate", self.generate)
        g.add_node("finish", self.finish)
        g.add_node("verify", self.verify)
        g.add_node("regenerate", self.regenerate)

        g.add_edge(START, "analyze")
        g.add_conditional_edges(
            "analyze",
            lambda s: "finish" if s["analysis"].intent == "out_of_scope" else "resolve_targets",
            {"finish": "finish", "resolve_targets": "resolve_targets"},
        )
        g.add_edge("resolve_targets", "plan")
        g.add_edge("plan", "execute")
        g.add_edge("execute", "check")
        g.add_conditional_edges(
            "check",
            self.route_after_check,
            {"generate": "generate", "recover": "recover", "finish": "finish"},
        )
        g.add_edge("recover", "execute")
        g.add_edge("generate", "verify")
        g.add_conditional_edges(
            "verify", self.route_after_verify, {"regenerate": "regenerate", "end": END}
        )
        g.add_edge("regenerate", "verify")
        g.add_edge("finish", END)
        return g.compile()

    def run(self, question: str, document_ids: list, patent_ids: list) -> AgentState:
        initial: AgentState = {
            "question": question,
            "document_ids": document_ids,
            "patent_ids": patent_ids,
            "tool_log": [],
            "passages": [],
            "direct_passages": [],
            "retrievals": [],
            "attempts": 0,
            "recoveries": [],
            "stop_reason": None,
            "candidates": [],
            "verify_attempts": [],
            "regenerations": 0,
            "extra_timings": {},
            "verification": None,
        }
        return self.graph.invoke(initial)

    def mermaid(self) -> str:
        return self.graph.get_graph().draw_mermaid()

    # ------------------------------------------------------------------ nodes

    def analyze(self, state: AgentState) -> dict:
        question = state["question"]
        started = time.perf_counter()
        analysis = (
            analyze_llm(question, self.ctx.llm)
            if self.planner == "llm"
            else analyze_rules(question)
        )
        # Timed: with the LLM planner this is a full LLM call (Phase 10 found it missing)
        timings = {
            **state["extra_timings"],
            "0. analyze": round((time.perf_counter() - started) * 1000),
        }
        update: dict = {"analysis": analysis, "extra_timings": timings}
        if analysis.intent == "out_of_scope":
            update["stop_reason"] = (
                "This question is outside the scope of patent research assistance."
            )
        return update

    def resolve_targets(self, state: AgentState) -> dict:
        """Map patent numbers and 'my/this patent' to concrete indexed sources."""
        session, analysis = self.ctx.session, state["analysis"]
        targets: list[Target] = []
        for number in analysis.publication_numbers:
            patent = session.scalar(
                select(Patent)
                .where(Patent.publication_number.op("~")(f"^{number}([A-Z][0-9]?)?$"))
                .limit(1)
            )
            if patent:
                targets.append(
                    Target(
                        "patent", patent.publication_number, patent.id, patent.publication_number
                    )
                )
                continue
            document = session.scalar(
                restrict(select(Document), Document.owner_id)
                .where(Document.meta["patent_numbers_detected"].contains([number]))
                .limit(1)
            )
            if document:
                targets.append(
                    Target("document", document.title or document.filename, document.id, number)
                )
            else:
                targets.append(Target("external", number, number=number))

        known = {t.id for t in targets if t.id}
        for doc_id in state["document_ids"]:
            doc = session.get(Document, doc_id)
            if doc and visible(doc.owner_id) and doc.id not in known:
                targets.append(Target("document", doc.title or doc.filename, doc.id))
        for patent_id in state["patent_ids"]:
            patent = session.get(Patent, patent_id)
            if patent and patent.id not in known:
                targets.append(
                    Target(
                        "patent", patent.publication_number, patent.id, patent.publication_number
                    )
                )

        if self._needs_subject(analysis, targets):
            subject = self._subject_from_question(
                state["question"],
                exclude={t.id for t in targets if t.id},
                own_documents_only=analysis.refers_to_scope,
            )
            if subject:
                targets.insert(0, subject)
        update: dict = {"targets": targets}
        # Two or more documents in scope + "compare"/"differences", or a legal question
        # ("does A infringe B?"): answer with a balanced technical comparison. Only known
        # here, because the question text alone doesn't say how many documents are selected.
        # (Found by the Phase 9 dev set: "Compare these two documents" was answered as Q&A.)
        if (
            analysis.intent == "document_qa"
            and len(targets) >= 2
            and (asks_to_compare(state["question"]) or analysis.legal_question)
        ):
            update["analysis"] = replace(analysis, intent="compare")
        return update

    @staticmethod
    def _needs_subject(analysis: QueryAnalysis, targets: list[Target]) -> bool:
        """Does the question talk about a document/patent it doesn't identify by number?"""
        if analysis.intent == "compare":
            return len(targets) < 2 and (analysis.refers_to_scope or not targets)
        if targets:
            return False
        return (
            analysis.intent == "find_similar"
            or analysis.refers_to_scope
            or analysis.section is not None
        )

    def _subject_from_question(
        self, question: str, *, exclude: set, own_documents_only: bool
    ) -> Target | None:
        """Find the indexed document/patent the question names, e.g. "the battery patent".

        1. Title match: the source whose title shares the most content words with the
           question (ties → ambiguous → none).
        2. Otherwise, if exactly one document is uploaded, "my patent" must mean it.
        Never guesses between several candidates. "my/this ..." refers to the user's own
        uploaded documents, so imported external patents are not candidates then.
        """
        session = self.ctx.session
        words = set(keywords_from_text(question, limit=20).split())
        candidates: list[tuple[int, Target]] = []
        ready = restrict(select(Document), Document.owner_id).where(Document.status == "ready")
        for doc in session.scalars(ready):
            title_words = set(keywords_from_text(f"{doc.title} {doc.filename}", limit=30).split())
            target = Target("document", doc.title or doc.filename, doc.id)
            candidates.append((len(words & title_words), target))
        for patent in [] if own_documents_only else session.scalars(select(Patent)):
            title_words = set(keywords_from_text(patent.title or "", limit=30).split())
            target = Target(
                "patent", patent.publication_number, patent.id, patent.publication_number
            )
            candidates.append((len(words & title_words), target))
        candidates = [c for c in candidates if c[1].id not in exclude]
        scored = sorted((c for c in candidates if c[0] > 0), key=lambda c: -c[0])
        if scored and (len(scored) == 1 or scored[0][0] > scored[1][0]):
            return scored[0][1]
        documents = [t for _, t in candidates if t.kind == "document"]
        return documents[0] if len(documents) == 1 else None

    def plan(self, state: AgentState) -> dict:
        if self.tool_policy == "all":
            return {"steps": self._every_tool(state)}
        analysis, targets, question = state["analysis"], state["targets"], state["question"]
        steps = [
            Step("get_patent_details", {"number": t.number})
            for t in targets
            if t.kind == "external"
        ]
        subjects = [t for t in targets]  # resolved to indexed targets at execution time

        if analysis.intent == "compare" and len(subjects) >= 2:
            steps.append(Step("compare_patents", {"query": question, "targets": "$targets"}))
        elif analysis.intent == "find_similar" and not subjects and not analysis.search_keywords:
            return {
                "steps": [],
                "stop_reason": (
                    "Which invention should I find similar patents for? Select a document in "
                    "the search scope, name it (e.g. 'my battery patent'), or describe it."
                ),
            }
        elif analysis.intent == "find_similar":
            if subjects:
                steps.append(Step("extract_key_concepts", {"target": "$first_target"}))
                keywords = "$concepts"
            else:
                keywords = analysis.search_keywords
            steps.append(
                Step(
                    "search_patents",
                    {
                        "keywords": keywords,
                        "reference": "$first_target_optional",
                        "import_top": self.similar_import_limit,
                    },
                )
            )
            steps.append(Step("compare_patents", {"query": question, "targets": "$targets"}))
        elif subjects:
            if analysis.section:
                steps.append(
                    Step(
                        "retrieve_document_section",
                        {
                            "target": "$first_target",
                            "section": analysis.section,
                            "claim_number": analysis.claim_number,
                        },
                    )
                )
            steps.append(Step("retrieve_evidence", {"query": question, "targets": "$targets"}))
        else:
            steps.append(Step("search_uploaded_documents", {"query": question}))
        return {"steps": steps}

    def _every_tool(self, state: AgentState) -> list[Step]:
        """Experiment F control: no tool selection. Every tool runs if its inputs exist;
        intent is still classified, but only to format the answer."""
        analysis, targets, question = state["analysis"], state["targets"], state["question"]
        steps = [
            Step("get_patent_details", {"number": t.number})
            for t in targets
            if t.kind == "external"
        ]
        steps.append(Step("search_uploaded_documents", {"query": question}))
        if targets:
            steps.append(Step("retrieve_evidence", {"query": question, "targets": "$targets"}))
            steps.append(Step("extract_key_concepts", {"target": "$first_target"}))
            if analysis.section:
                steps.append(
                    Step(
                        "retrieve_document_section",
                        {
                            "target": "$first_target",
                            "section": analysis.section,
                            "claim_number": analysis.claim_number,
                        },
                    )
                )
        if self.ctx.patents.sources:  # a tool with no configured database is unavailable
            steps.append(
                Step(
                    "search_patents",
                    {
                        "keywords": "$concepts" if targets else analysis.search_keywords,
                        "reference": "$first_target_optional",
                        "import_top": self.similar_import_limit,
                    },
                )
            )
        if len(targets) >= 2:
            steps.append(Step("compare_patents", {"query": question, "targets": "$targets"}))
        return steps

    def execute(self, state: AgentState) -> dict:
        targets = list(state["targets"])
        log = list(state["tool_log"])
        passages = list(state["passages"])
        direct = list(state["direct_passages"])
        retrievals = list(state["retrievals"])
        concepts = state.get("concepts", "")
        candidates = list(state["candidates"])
        queue = list(state["steps"])

        while queue:
            step = queue.pop(0)
            import_top = step.args.get("import_top")
            args = {k: v for k, v in step.args.items() if k != "import_top"}
            args = self._resolve_args(args, targets, concepts, state)
            if args is None:
                log.append(self._log(step.tool, step.args, False, "skipped: no indexed target", 0))
                continue
            started = time.perf_counter()
            try:
                result: ToolResult = TOOLS[step.tool](self.ctx, **args)
            except AppError as exc:
                # Undo any half-finished database work (e.g. a partly indexed patent)
                self.ctx.session.rollback()
                log.append(self._log(step.tool, args, False, exc.message, started))
                continue
            entry = self._log(step.tool, args, True, result.summary, started)
            if result.data.get("sources"):
                entry["sources"] = result.data["sources"]  # which external databases were used
            log.append(entry)

            for new in result.new_targets:  # an external number was fetched & indexed
                targets = [
                    t
                    for t in targets
                    if not (
                        t.kind == "external"
                        and t.number
                        and new.number
                        and new.number.startswith(t.number)
                    )
                ]
                if all(t.id != new.id for t in targets):
                    targets.append(new)
            if step.tool == "extract_key_concepts":
                concepts = result.data.get("keywords", "")
            if step.tool == "search_patents":
                candidates = result.data.get("candidates", [])
                own = {t.number for t in targets if t.number}
                picks = [c for c in candidates if c["publication_number"] not in own][
                    : import_top or 0
                ]
                queue = [
                    Step(
                        "get_patent_details",
                        {"number": c["publication_number"], "source": c["source"]},
                    )
                    for c in picks
                ] + queue
            (direct if result.direct else passages).extend(result.passages)
            if result.retrieval is not None:
                retrievals.append(result.retrieval)

        return {
            "targets": targets,
            "tool_log": log,
            "passages": passages,
            "direct_passages": direct,
            "retrievals": retrievals,
            "concepts": concepts,
            "candidates": candidates,
            "steps": [],
        }

    def route_after_check(self, state: AgentState) -> str:
        if self._missing_similar_patents(state):
            # Passages about the user's OWN invention are not evidence of similar patents
            can_retry = state["attempts"] < self.max_recoveries and self._recovery_plan(state)
            return "recover" if can_retry else "finish"
        if state["direct_passages"]:
            return "generate"
        merged = self._merged_retrieval(state)
        sufficient, _ = has_sufficient_evidence(merged, self.ctx.retrieval)
        if sufficient:
            return "generate"
        if state["attempts"] < self.max_recoveries and self._recovery_plan(state):
            return "recover"
        return "finish"

    def recover(self, state: AgentState) -> dict:
        description, steps = self._recovery_plan(state)
        logger.info("Agent recovery: %s", description)
        return {
            "steps": steps,
            "attempts": state["attempts"] + 1,
            "recoveries": state["recoveries"] + [description],
        }

    def generate(self, state: AgentState) -> dict:
        analysis = state["analysis"]
        indexed = [t for t in state["targets"] if t.kind in ("document", "patent") and t.id]
        if analysis.intent == "compare" and len(indexed) >= 2:
            return self._generate_comparison(state, indexed[:4])
        passages = self._final_passages(state)
        evidence = build_evidence(passages, self.ctx.settings.max_context_tokens)
        instructions = (
            [TASK_INSTRUCTIONS[analysis.intent]] if analysis.intent in TASK_INSTRUCTIONS else []
        )
        question = state["question"]
        if analysis.legal_question:
            instructions.append(LEGAL_INSTRUCTION)
            # Observed: given the legal question verbatim, Qwen3 refused entirely. Asking the
            # technical question the system CAN answer yields the useful part; the original
            # question is still stored with the run and the UI shows a legal disclaimer.
            question = (
                "Describe and compare the technical features of the sources in the evidence. "
                f'(The user asked: "{question}". Do not give a legal opinion.)'
            )
        response = self.ctx.llm.complete(
            build_messages(question, evidence, instructions=" ".join(instructions) or None),
            temperature=self.ctx.settings.llm_temperature,
            max_tokens=self.ctx.settings.llm_max_tokens,
        )
        parsed = parse_answer(response.text, {item.label for item in evidence})
        return {
            "parsed": parsed,
            "evidence": evidence,
            "llm_response": response,
            "final_passages": passages,
        }

    def _generate_comparison(self, state: AgentState, targets: list[Target]) -> dict:
        """Compare intent: a structured, cited table instead of free text."""
        builder = ComparisonBuilder(
            self.ctx.session, self.ctx.embedder, self.ctx.llm, self.ctx.retrieval
        )
        sources = builder.resolve([(t.kind, t.id) for t in targets])
        mode = "extractive" if self.ctx.settings.llm_provider == "fake" else "llm"
        question = state["question"]
        if state["analysis"].legal_question:
            question = f'Technical comparison only. (The user asked: "{question}".)'
        result = builder.build(sources, question, mode=mode)
        parsed = parse_answer(result.answer_text(), set(result.label_source))
        parsed.cited_labels = result.cited_labels()  # table cells count as citations too
        return {
            "parsed": parsed,
            "evidence": result.evidence,
            "llm_response": result.llm_response,
            "final_passages": [item.passage for item in result.evidence],
            "comparison": result.to_json(),
        }

    # ------------------------------------------------------------------ verification

    @property
    def verifier(self):
        if self._verifier is None:
            s = self.ctx.settings
            self._verifier = build_verifier(
                s.verifier_method, nli_model=s.verifier_nli_model, llm=self.ctx.llm
            )
        return self._verifier

    def verify(self, state: AgentState) -> dict:
        """Check every claim; after a regeneration, keep whichever attempt is better grounded."""
        parsed = state["parsed"]
        if self.ctx.settings.verify_mode == "off" or parsed.status != "answered":
            return {"verification": None}
        started = time.perf_counter()
        report = verify_answer(
            self.verifier, parsed, state["evidence"], comparison=state.get("comparison")
        )
        attempt = {
            "parsed": parsed,
            "evidence": state["evidence"],
            "final_passages": state["final_passages"],
            "llm_response": state["llm_response"],
            "comparison": state.get("comparison"),
            "report": report,
        }
        attempts = state["verify_attempts"] + [attempt]
        timings = dict(state["extra_timings"])
        timings[f"verify {len(attempts)}"] = round((time.perf_counter() - started) * 1000)
        # Later attempts win ties: they were made with more evidence and feedback
        best = max(reversed(attempts), key=lambda a: a["report"].grounding_score or 0.0)
        return {
            "verify_attempts": attempts,
            "extra_timings": timings,
            "verification": best["report"],
            "parsed": best["parsed"],
            "evidence": best["evidence"],
            "final_passages": best["final_passages"],
            "llm_response": best["llm_response"],
            "comparison": best["comparison"],
        }

    def route_after_verify(self, state: AgentState) -> str:
        report = state.get("verification")
        settings = self.ctx.settings
        latest = state["verify_attempts"][-1]["report"] if state["verify_attempts"] else None
        if (
            report is None
            or settings.verify_mode != "regenerate"
            or state.get("comparison") is not None  # tables are flagged, not rewritten
            or state["regenerations"] >= settings.max_regenerations
            or latest is None
            or (latest.grounding_score or 0.0) >= settings.grounding_threshold
            or not latest.unsupported()
        ):
            return "end"
        return "regenerate"

    def regenerate(self, state: AgentState) -> dict:
        """Retrieve evidence for each unsupported statement, then rewrite with feedback."""
        started = time.perf_counter()
        report = state["verify_attempts"][-1]["report"]
        indexed = [t for t in state["targets"] if t.kind in ("document", "patent") and t.id]
        scope = {}
        if indexed:
            scope = {
                "document_ids": [t.id for t in indexed if t.kind == "document"],
                "patent_ids": [t.id for t in indexed if t.kind == "patent"],
            }
        elif state["document_ids"] or state["patent_ids"]:
            scope = {"document_ids": state["document_ids"], "patent_ids": state["patent_ids"]}

        passages = list(state["final_passages"])
        seen = {p.chunk.id for p in passages}
        added = 0
        for claim in report.unsupported()[:3]:
            hits = retrieve(
                self.ctx.session,
                claim.text,
                embedder=self.ctx.embedder,
                config=self.ctx.retrieval,
                **scope,
            ).passages[:2]
            for hit in hits:
                if hit.chunk.id not in seen:
                    seen.add(hit.chunk.id)
                    passages.append(hit)
                    added += 1
        for rank, passage in enumerate(passages, start=1):
            passage.rank = rank

        analysis = state["analysis"]
        evidence = build_evidence(passages, self.ctx.settings.max_context_tokens + 600)
        instructions = (
            [TASK_INSTRUCTIONS[analysis.intent]] if analysis.intent in TASK_INSTRUCTIONS else []
        )
        if analysis.legal_question:
            instructions.append(LEGAL_INSTRUCTION)
        instructions.append(regeneration_instructions(report))
        response = self.ctx.llm.complete(
            build_messages(state["question"], evidence, instructions=" ".join(instructions)),
            temperature=self.ctx.settings.llm_temperature,
            max_tokens=self.ctx.settings.llm_max_tokens,
        )
        parsed = parse_answer(response.text, {item.label for item in evidence})
        timings = dict(state["extra_timings"])
        timings[f"regenerate {state['regenerations'] + 1}"] = round(
            (time.perf_counter() - started) * 1000
        )
        return {
            "parsed": parsed,
            "evidence": evidence,
            "final_passages": passages,
            "llm_response": response,
            "regenerations": state["regenerations"] + 1,
            "extra_timings": timings,
            "regeneration_added_passages": added,
        }

    def finish(self, state: AgentState) -> dict:
        reason = state.get("stop_reason")
        if not reason and self._missing_similar_patents(state):
            searched = [
                e["input"].get("keywords")
                for e in state["tool_log"]
                if e["tool_name"] == "search_patents" and e["success"]
            ]
            if searched:
                reason = (
                    "The patent search found no potentially relevant patents "
                    f"(searched for: {', '.join(repr(k) for k in searched)})."
                )
        if not reason:
            failures = [
                entry["output_summary"] for entry in state["tool_log"] if not entry["success"]
            ]
            if failures:
                reason = "Evidence could not be gathered: " + "; ".join(failures)
            else:
                _, reason = has_sufficient_evidence(
                    self._merged_retrieval(state), self.ctx.retrieval
                )
                reason = reason or "No relevant evidence was found."
        parsed = ParsedAnswer(status="insufficient_evidence", text="", insufficient_reason=reason)
        return {
            "parsed": parsed,
            "evidence": [],
            "llm_response": None,
            "final_passages": self._final_passages(state),
        }

    # ------------------------------------------------------------------ helpers

    def _resolve_args(self, args: dict, targets: list[Target], concepts: str, state: AgentState):
        indexed = [t for t in targets if t.kind in ("document", "patent") and t.id]
        resolved = dict(args)
        for key, value in args.items():
            if value == "$targets":
                if not indexed:
                    return None
                resolved[key] = indexed
            elif value == "$first_target":
                if not indexed:
                    return None
                resolved[key] = indexed[0]
            elif value == "$first_target_optional":
                resolved[key] = indexed[0] if indexed else None
            elif value == "$concepts":
                resolved[key] = concepts or state["analysis"].search_keywords
                if not resolved[key]:
                    return None
        return resolved

    @staticmethod
    def _log(tool: str, args: dict, success: bool, summary: str, started: float) -> dict:
        def plain(value):
            if isinstance(value, Target):
                return value.to_json()
            if isinstance(value, list):
                return [plain(v) for v in value]
            return value if isinstance(value, (str, int, float, bool, type(None))) else str(value)

        return {
            "tool_name": tool,
            "input": {k: plain(v) for k, v in args.items()},
            "success": success,
            "output_summary": summary,
            "latency_ms": round((time.perf_counter() - started) * 1000) if started else 0,
        }

    @staticmethod
    def _missing_similar_patents(state: AgentState) -> bool:
        return state["analysis"].intent == "find_similar" and not state["candidates"]

    def _merged_retrieval(self, state: AgentState) -> RetrievalResult:
        retrievals = state["retrievals"]
        sims = [
            r.best_vector_similarity for r in retrievals if r.best_vector_similarity is not None
        ]
        return RetrievalResult(
            passages=state["passages"],
            best_vector_similarity=max(sims) if sims else None,
            keyword_matches=sum(r.keyword_matches for r in retrievals),
            candidates_considered=sum(r.candidates_considered for r in retrievals),
        )

    def _recovery_plan(self, state: AgentState):
        """Pick one fallback strategy, or None if nothing sensible is left to try."""
        log = state["tool_log"]
        searched = [e for e in log if e["tool_name"] == "search_patents"]
        if searched and searched[-1]["success"] and not state["candidates"]:
            words = str(searched[-1]["input"].get("keywords", "")).split()
            if len(words) > 1:
                fewer = " ".join(words[: max(1, len(words) - 1)])
                return (
                    f'patent search found nothing; retrying with fewer keywords "{fewer}"',
                    [
                        Step(
                            "search_patents",
                            {
                                "keywords": fewer,
                                "reference": "$first_target_optional",
                                "import_top": self.similar_import_limit,
                            },
                        ),
                        Step(
                            "compare_patents", {"query": state["question"], "targets": "$targets"}
                        ),
                    ],
                )
        used_scope = any(e["tool_name"] in ("retrieve_evidence", "compare_patents") for e in log)
        searched_all = any(e["tool_name"] == "search_uploaded_documents" for e in log)
        if (
            used_scope
            and not searched_all
            and not state["document_ids"]
            and not state["patent_ids"]
        ):
            return (
                "scoped search found too little; searching all indexed sources",
                [Step("search_uploaded_documents", {"query": state["question"]})],
            )
        return None

    def _final_passages(self, state: AgentState) -> list[RetrievedPassage]:
        seen, merged = set(), []
        ranked = sorted(state["passages"], key=lambda p: p.rank)
        for passage in state["direct_passages"] + ranked:
            if passage.chunk.id not in seen:
                seen.add(passage.chunk.id)
                merged.append(passage)
        merged = merged[:MAX_EVIDENCE]
        for rank, passage in enumerate(merged, start=1):
            passage.rank = rank
        return merged
