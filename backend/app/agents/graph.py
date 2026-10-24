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

import contextvars
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.agents import premise
from app.agents.analysis import (
    QueryAnalysis,
    analyze_llm,
    analyze_rules,
    asks_to_compare,
    is_about_assistant,
    keywords_from_text,
)
from app.agents.demo_injection import Injection, find_planted, plant_false_fact
from app.agents.everyday import (
    GENERAL_PROMPT,
    asks_for_time,
    calculator_reply,
    clock_reply,
    is_creative,
    now_in,
)
from app.agents.live import LiveAnswer
from app.agents.tools import TOOLS, Target, ToolContext, ToolResult
from app.agents.trace import TOOL_LABELS, TraceRecorder, tool_reason
from app.core.errors import AppError
from app.core.ownership import restrict, visible
from app.intelligence.comparison import ComparisonBuilder
from app.llm.providers import ChatMessage, LLMResponse
from app.models import Document, Patent
from app.rag.generation import ParsedAnswer, build_evidence, build_messages, parse_answer
from app.rag.retrieval import (
    RetrievalResult,
    RetrievedPassage,
    has_sufficient_evidence,
    retrieve,
)
from app.services.patents import PatentService
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
    # find_similar without a reference invention: a topic search ("latest patents on X")
    "find_topic": (
        "The evidence contains patents found by a patent database search for the user's "
        "topic. For each patent, give its publication number and title and say what it "
        "covers that is relevant to the question, citing passages; then say briefly how "
        "their technical approaches differ. Do not describe them as similar to an invention "
        "of the user's: the user did not provide one."
    ),
}
SEARCH_TERMS_PROMPT = (
    "Turn the user's question into a patent-database search: 2 to 4 technical keywords, "
    "using the terms patent documents use instead of everyday words (e.g. 'foreign object "
    "detection wireless charging' for 'how does a charger notice a coin'). Reply with the "
    "keywords only, separated by spaces."
)
# Chat answers (not the /ask API or experiments): written like a chat assistant's. Observed
# (2026-10-22): drafts said "In E2, the battery pack…", naming passage labels in the prose.
CHAT_STYLE = (
    "Write for someone reading in a chat: begin with a direct one- or two-sentence answer, "
    "then the details. Keep paragraphs short. Use a bulleted list when you list several "
    "items, steps or features, with the key term in **bold** at the start of an item. Do not "
    "use headings. Never write passage labels such as E2 in the text itself; put them only "
    "in square brackets after the statement they support."
)
DETAILED_STYLE = "The user prefers detailed answers: up to about 400 words."
TECHNICAL_PROMPT = (
    "Is the user's question about science, engineering, technology, a device, a material, "
    "a product or an invention? Reply with exactly one word: yes or no."
)
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
    live_search: bool
    inject_false_fact: bool  # demo mode (Phase 14): plant a false sentence in the draft
    injection: Injection | None
    external_passages: list[RetrievedPassage]  # web pages / patent abstracts, this answer only
    everyday: str | None  # "clock" | "calculator": answered exactly, no source needed
    general: dict | None  # answered from the model's general knowledge (chat only)
    premise_terms: list[str]  # the question's terms no passage uses (app/agents/premise.py)


_UNREACHABLE = re.compile(r"could not reach|timed out|ConnectError|connection", re.IGNORECASE)

# Searches whose results are used for one answer only (app/rag/transient.py)
_EXTERNAL_TOOLS = {"search_patents", "search_patent_abstracts", "search_web"}
# Searches that need nothing from each other: run at the same time when planned together
_PARALLEL_TOOLS = {"search_uploaded_documents", "search_web", "search_patent_abstracts"}
# A general question about patents: also search the patent offices' abstracts
_ABOUT_PATENTS = re.compile(
    r"\b(patent(?:s|ed)?|inventions?|prior art|assignees?|patent office)\b", re.IGNORECASE
)


class AgentGraph:
    def __init__(
        self,
        ctx: ToolContext,
        *,
        planner: str,
        similar_import_limit: int,
        max_recoveries: int,
        tool_policy: str = "select",
        live_fallback: bool = False,
        web_search: bool = False,
        live_import_limit: int = 3,
        trace: TraceRecorder | None = None,
        live: LiveAnswer | None = None,
        parallel_searches: bool = False,
        general_fallback: bool = False,
        timezone: str | None = None,
        chat_style: str | None = None,
    ):
        self.ctx = ctx
        self.planner = planner  # "rules" | "llm"
        # "select": choose tools for the question (the agent). "all": run every tool whose
        # inputs are available, whatever the question (the Experiment F control).
        self.tool_policy = tool_policy
        self.similar_import_limit = similar_import_limit
        self.max_recoveries = max_recoveries
        self.live_fallback = live_fallback
        # Unscoped questions also search the web (and patent abstracts when about patents)
        self.web_search = web_search
        self.live_import_limit = live_import_limit
        self._live_terms: str | None = None
        self._technical: bool | None = None
        self._verifier = None
        self.trace = trace or TraceRecorder()
        # The chat's live view: sources found, the draft as it is written, the verdicts
        self.live = live
        self.parallel_searches = parallel_searches
        # Chat only: with no source for an answer, the model's own knowledge, labelled as such
        self.general_fallback = general_fallback
        self.timezone = timezone  # the user's, for "what day is it?"
        self.chat_style = chat_style  # None (API, experiments) | "concise" | "detailed"
        self.graph = self._build()

    # ------------------------------------------------------------------ graph

    def _build(self):
        g = StateGraph(AgentState)
        traced = self.trace.traced  # a trace row per node (tools get rows in execute)
        g.add_node("analyze", traced("analyze", self.analyze))
        g.add_node("resolve_targets", traced("resolve_targets", self.resolve_targets))
        g.add_node("plan", traced("plan", self.plan))
        g.add_node("execute", self.execute)
        g.add_node("check", lambda state: {})
        g.add_node("recover", traced("recover", self.recover))
        g.add_node("generate", traced("generate", self.generate))
        g.add_node("finish", traced("finish", self.finish))
        g.add_node("verify", traced("verify", self.verify))
        g.add_node("regenerate", traced("regenerate", self.regenerate))

        g.add_edge(START, "analyze")
        g.add_node("small_talk", traced("small_talk", self.small_talk))
        g.add_node("everyday", traced("everyday", self.everyday))
        g.add_node("general", traced("general", self.general))
        g.add_conditional_edges(
            "analyze",
            self.route_after_analyze,
            {
                "finish": "finish",
                "small_talk": "small_talk",
                "everyday": "everyday",
                "general": "general",
                "resolve_targets": "resolve_targets",
            },
        )
        g.add_edge("small_talk", END)
        g.add_edge("everyday", END)
        g.add_edge("general", END)
        g.add_edge("resolve_targets", "plan")
        g.add_edge("plan", "execute")
        g.add_edge("execute", "check")
        g.add_conditional_edges(
            "check",
            self.route_after_check,
            {"generate": "generate", "recover": "recover", "finish": "finish"},
        )
        g.add_edge("recover", "execute")
        g.add_conditional_edges(
            "generate", self.route_after_generate, {"recover": "recover", "verify": "verify"}
        )
        g.add_conditional_edges(
            "verify",
            self.route_after_verify,
            {"regenerate": "regenerate", "general": "general", "end": END},
        )
        g.add_edge("regenerate", "verify")
        g.add_conditional_edges(
            "finish",
            lambda s: "general" if self._general_allowed(s) else "end",
            {"general": "general", "end": END},
        )
        return g.compile()

    def run(
        self,
        question: str,
        document_ids: list,
        patent_ids: list,
        *,
        live_search: bool = False,
        inject_false_fact: bool = False,
    ) -> AgentState:
        initial: AgentState = {
            "question": question,
            "live_search": live_search,
            "inject_false_fact": inject_false_fact,
            "injection": None,
            "document_ids": document_ids,
            "patent_ids": patent_ids,
            "tool_log": [],
            "passages": [],
            "direct_passages": [],
            "external_passages": [],
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
        # A writing task in the chat ("write a poem about…") goes to the model directly:
        # no need for the planner's call (2.5 s)
        writing_task = self.general_fallback and is_creative(question)
        analysis = (
            analyze_llm(question, self.ctx.llm)
            if self.planner == "llm" and not writing_task
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
        elif (
            analysis.intent == "find_similar"
            and self.web_search
            and self._task(state) == "find_topic"
            and self.ctx.patents.sources
        ):
            # A topic search ("latest patents on X"): answer from the hits' abstracts,
            # without importing them into the library
            steps.append(
                Step(
                    "search_patent_abstracts",
                    {"keywords": self._live_keywords(state), "question": question},
                )
            )
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
            if self._can_search_live(state) and (self.web_search or state.get("live_search")):
                # Patent filings also answer technology questions ("how do battery packs use
                # immersion cooling?" found only a Wikipedia page on cooling electronics,
                # 2026-10-11). The LLM planner rules out off-topic questions; without it,
                # only questions that mention patents go to the patent offices.
                in_scope = analysis.analyzer.startswith("llm") and analysis.analyzer not in (
                    "llm_fallback_rules",
                    "llm_scope_override",
                )
                about_patents = bool(
                    state.get("live_search")
                    or _ABOUT_PATENTS.search(question)
                    or in_scope
                    or (
                        analysis.analyzer == "llm_scope_override"
                        and self.ctx.patents.sources
                        and self._is_technical(question)
                    )
                )
                steps += self._live_steps(state, patents=about_patents)
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
        external = list(state.get("external_passages") or [])
        retrievals = list(state["retrievals"])
        concepts = state.get("concepts", "")
        candidates = list(state["candidates"])
        queue = list(state["steps"])

        while queue:
            batch = self._parallel_batch(queue)
            if len(batch) > 1:
                del queue[: len(batch)]
                outcomes = self._run_parallel(batch, state)
            else:
                step = queue.pop(0)
                args = {k: v for k, v in step.args.items() if k != "import_top"}
                args = self._resolve_args(args, targets, concepts, state)
                if args is None:
                    log.append(
                        self._log(step.tool, step.args, False, "skipped: no indexed target", 0)
                    )
                    continue
                outcomes = [(step, *self._call_tool(step.tool, args, state, self.ctx))]
            for step, entry, result in outcomes:
                log.append(entry)
                if result is None:
                    continue
                queue = self._absorb(step, result, targets, queue)
                if step.tool == "extract_key_concepts":
                    concepts = result.data.get("keywords", "")
                if step.tool == "search_patents":
                    candidates = result.data.get("candidates", [])
                if result.external:
                    external.extend(result.passages)
                else:
                    (direct if result.direct else passages).extend(result.passages)
                if result.retrieval is not None:
                    retrievals.append(result.retrieval)
                if self.live is not None:
                    self.live.found(result.passages)

        return {
            "targets": targets,
            "tool_log": log,
            "passages": passages,
            "direct_passages": direct,
            "external_passages": external,
            "retrievals": retrievals,
            "concepts": concepts,
            "candidates": candidates,
            "steps": [],
        }

    def _call_tool(
        self, tool: str, args: dict, state: AgentState, ctx: ToolContext
    ) -> tuple[dict, ToolResult | None]:
        """Run one tool: a trace row while it runs; its log entry, and its result (None
        if it failed)."""
        started = time.perf_counter()
        row = self.trace.start(
            "tool", tool, TOOL_LABELS.get(tool, tool), why=tool_reason(tool, args, state)
        )
        try:
            result: ToolResult = TOOLS[tool](ctx, **args)
        except AppError as exc:
            # Undo any half-finished database work (e.g. a partly indexed patent)
            ctx.session.rollback()
            self.trace.end(row, exc.message, ok=False)
            return self._log(tool, args, False, exc.message, started), None
        self.trace.end(row, result.summary)
        entry = self._log(tool, args, True, result.summary, started)
        if result.data.get("sources"):
            entry["sources"] = result.data["sources"]  # which external databases were used
        return entry, result

    def _parallel_batch(self, queue: list[Step]) -> list[Step]:
        """The independent searches at the head of the queue (library, web, patent
        abstracts): their inputs are the question itself, not another tool's output.
        Each needs its own database connection, so not on a session bound to one
        connection (the tests' transaction)."""
        if not self.parallel_searches or not isinstance(self.ctx.session.get_bind(), Engine):
            return []
        batch = []
        for step in queue:
            if step.tool not in _PARALLEL_TOOLS or any(
                isinstance(v, str) and v.startswith("$") for v in step.args.values()
            ):
                break
            batch.append(step)
        return batch

    def _run_parallel(self, steps: list[Step], state: AgentState) -> list[tuple]:
        """Run independent searches at the same time. The first keeps the request's
        session, the others get their own; local models still take turns (the inference
        lock), so the gain is the waiting on the web and the patent offices. Results are
        used in plan order: the answer is the same as when they run one after another."""
        bind = self.ctx.session.get_bind()

        def run(index: int, step: Step):
            if index == 0:
                return self._call_tool(step.tool, step.args, state, self.ctx)
            session = Session(bind=bind)
            ctx = replace(
                self.ctx,
                session=session,
                patents=PatentService(
                    session, self.ctx.settings, self.ctx.embedder, self.ctx.patents.sources
                ),
            )
            try:
                outcome = self._call_tool(step.tool, step.args, state, ctx)
                session.commit()  # e.g. cached search results
                return outcome
            finally:
                session.close()

        with ThreadPoolExecutor(max_workers=len(steps)) as pool:
            # Each thread runs in a copy of this context: the owner scope (whose documents
            # are visible) must hold there too
            futures = [
                pool.submit(contextvars.copy_context().run, run, i, step)
                for i, step in enumerate(steps)
            ]
            return [(step, *f.result()) for step, f in zip(steps, futures, strict=True)]

    def _absorb(
        self, step: Step, result: ToolResult, targets: list[Target], queue: list[Step]
    ) -> list[Step]:
        """Fold a tool's new targets into `targets` (in place); returns the queue, with
        imports of the best search results first."""

        for new in result.new_targets:  # an external number was fetched & indexed
            targets[:] = [
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
        if step.tool == "search_patents":
            candidates = result.data.get("candidates", [])
            own = {t.number for t in targets if t.number}
            fresh = [c for c in candidates if c["publication_number"] not in own]
            # Among the most relevant, prefer patents whose claims can be imported
            preferred = [c for c in fresh[:10] if c.get("full_text")]
            import_top = step.args.get("import_top") or 0
            picks = (preferred + [c for c in fresh if c not in preferred])[:import_top]
            queue = [
                Step(
                    "get_patent_details",
                    {"number": c["publication_number"], "source": c["source"]},
                )
                for c in picks
            ] + queue
        return queue

    def route_after_check(self, state: AgentState) -> str:
        if self._unavailable_patents(state):
            # Never answer about a named patent from other documents' passages
            # (Experiment E found claim 2 of a local patent attributed to the asked one).
            return "finish"
        if self._missing_similar_patents(state):
            # Passages about the user's OWN invention are not evidence of similar patents
            can_retry = state["attempts"] < self.max_recoveries and self._recovery_plan(state)
            return "recover" if can_retry else "finish"
        if state["direct_passages"] or state.get("external_passages"):
            return "generate"  # the model judges web/abstract relevance (it may abstain)
        merged = self._merged_retrieval(state)
        sufficient, _ = has_sufficient_evidence(merged, self.ctx.retrieval)
        if sufficient:
            return "generate"
        if state["attempts"] < self.max_recoveries and self._recovery_plan(state):
            return "recover"
        if self.live_fallback and self._can_search_live(state):
            return "recover"
        return "finish"

    def route_after_analyze(self, state: AgentState) -> str:
        intent = state["analysis"].intent
        if intent in ("out_of_scope", "small_talk", "everyday"):
            return "finish" if intent == "out_of_scope" else intent
        if self._general_allowed(state, searched=False) and is_creative(state["question"]):
            return "general"  # "write a poem about batteries": no source to search
        return "resolve_targets"

    def _general_allowed(self, state: AgentState, searched: bool = True) -> bool:
        """Chat only: a general question (no document attached or named, not a request for
        patents or a comparison) that the sources could not answer."""
        analysis = state["analysis"]
        parsed = state.get("parsed")
        return bool(
            self.general_fallback
            and analysis.intent in ("document_qa", "out_of_scope")
            and not state["document_ids"]
            and not state["patent_ids"]
            and not analysis.refers_to_scope
            and not analysis.publication_numbers
            and (not searched or (parsed is not None and parsed.status != "answered"))
        )

    def everyday(self, state: AgentState) -> dict:
        """Date/time from the clock, arithmetic from the calculator: exact, no source."""
        question = state["question"]
        if asks_for_time(question):
            kind, text = "clock", clock_reply(question, self.timezone)
        else:
            kind, text = "calculator", calculator_reply(question) or ""
        return {
            "parsed": ParsedAnswer(status="answered", text=text),
            "evidence": [],
            "final_passages": [],
            "llm_response": None,
            "comparison": None,
            "verification": None,
            "everyday": kind,
        }

    def general(self, state: AgentState) -> dict:
        """An answer from the model's general knowledge, when no source had one (chat only).
        Not checked: the checker needs passages to check against. The page labels it."""
        settings = self.ctx.settings
        today = now_in(self.timezone)
        messages = [
            ChatMessage("system", GENERAL_PROMPT.format(today=f"{today:%A, %d %B %Y}")),
            ChatMessage("user", state["question"]),
        ]
        searched = state.get("parsed")
        if self.live is not None:
            self.live.general()
            response = self.ctx.llm.stream(
                messages,
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
                on_text=self.live.text,
            )
        else:
            response = self.ctx.llm.complete(
                messages, temperature=settings.llm_temperature, max_tokens=settings.llm_max_tokens
            )
        text = re.sub(r"(?s)<think>.*?</think>", "", response.text).strip()
        if not text or text.upper().startswith("INSUFFICIENT_EVIDENCE"):
            return {}  # keep "not found" rather than an empty answer or a marker
        return {
            "parsed": ParsedAnswer(status="answered", text=text),
            "evidence": [],
            "final_passages": [],
            "llm_response": response,
            "comparison": None,
            "verification": None,
            "general": {
                "searched": searched is not None,
                "not_found": searched.insufficient_reason if searched is not None else None,
            },
        }

    def small_talk(self, state: AgentState) -> dict:
        """A short reply to greetings and thanks: no retrieval, no LLM, nothing to verify."""
        text = state["question"].strip().lower()
        scoped = bool(state["document_ids"] or state["patent_ids"])
        if re.match(r"(thank|thx|ty\b|ok|okay|cool|great|nice|awesome|perfect)", text):
            reply = "You're welcome! Ask me anything else about patents whenever you like."
        elif re.match(r"(bye|goodbye|see you)", text):
            reply = "Goodbye! Your conversation is saved; you can continue it any time."
        elif is_about_assistant(text):
            reply = (
                "Yes, ask me anything. I'm built for technology and patents: I search "
                + ("the attached document, " if scoped else "your documents, ")
                + "patent filings and the web, then answer with every sentence linked to its "
                "source and checked by a hallucination checker. For example:\n\n"
                '- How a technology works: "How do solid-state batteries work?"\n'
                '- A patent you attach: "What does claim 1 cover?"\n'
                '- Patents on a topic: "Latest patents on battery immersion cooling"\n'
                "- Comparing documents, mapping a field or checking an idea (the tools "
                "under the question box)\n\n"
                "Other topics I answer from the web where I can. I don't give legal opinions."
            )
        elif scoped:
            reply = (
                "Hello! Ask me anything about the attached document, for example "
                '"Summarise this patent in plain language", "What does claim 1 cover?" or '
                '"What problem does it solve?". Every answer cites its sources and each '
                "sentence is checked against them."
            )
        else:
            reply = (
                "Hello! Ask me anything: I search your library, the patent offices and the "
                'web, and answer from what I find, e.g. "What are the latest patents on '
                'battery immersion cooling?" or "How do solid-state batteries work?". I '
                "cite the source of every sentence and check each one, and I do not give "
                "legal opinions."
            )
        parsed = ParsedAnswer(status="answered", text=reply)
        return {
            "parsed": parsed,
            "evidence": [],
            "final_passages": [],
            "llm_response": None,
            "comparison": None,
            "verification": None,
        }

    def route_after_generate(self, state: AgentState) -> str:
        parsed = state.get("parsed")
        if (
            parsed is not None
            and parsed.status == "insufficient_evidence"
            and self.live_fallback
            and self._can_search_live(state)
        ):
            # The model read the library's passages and found no answer: try the
            # patent databases once before giving up.
            return "recover"
        return "verify"

    def recover(self, state: AgentState) -> dict:
        description, steps = self._recovery_plan(state)
        logger.info("Agent recovery: %s", description)
        update = {
            "steps": steps,
            "attempts": state["attempts"] + 1,
            "recoveries": state["recoveries"] + [description],
        }
        parsed = state.get("parsed")
        if parsed is not None and parsed.status == "insufficient_evidence":
            # The model judged these passages insufficient: answer from the new ones
            update |= {
                "passages": [],
                "direct_passages": [],
                "retrievals": [],
                "external_passages": [],
            }
        return update

    def _task(self, state: AgentState) -> str:
        """Which answer instructions apply; a similar-patent search without the user's own
        document is a topic search."""
        intent = state["analysis"].intent
        if intent == "find_similar" and not (
            state["document_ids"] or state["analysis"].refers_to_scope
        ):
            return "find_topic"
        return intent

    def _can_search_live(self, state: AgentState) -> bool:
        """A general question (no document selected or named) that the web or the patent
        databases could answer, and no such search has been made for it yet."""
        analysis = state["analysis"]
        return bool(
            (self._patents_allowed(state, decide=False) or self.ctx.web is not None)
            and analysis.intent == "document_qa"
            and not state["document_ids"]
            and not state["patent_ids"]
            and not analysis.refers_to_scope
            and not any(t.kind in ("document", "patent", "external") for t in state["targets"])
            and not any(e["tool_name"] in _EXTERNAL_TOOLS for e in state["tool_log"])
            # the web takes the whole question; the patent offices need keywords
            and (self.ctx.web is not None or self._live_keywords(state))
        )

    def _patents_allowed(self, state: AgentState, decide: bool = True) -> bool:
        """The patent offices are searched only for questions that could be about patents:
        when the LLM planner judged a question off-topic ("a good pasta recipe?"), the web
        may answer it, the patent offices may not (2026-10-10: general questions should be
        answered like a general assistant), unless a second look finds it technical.
        `decide=False`: no model call, only what is already known."""
        if not self.ctx.patents.sources:
            return False
        if state["analysis"].analyzer != "llm_scope_override":
            return True
        return self._is_technical(state["question"]) if decide else bool(self._technical)

    def _is_technical(self, question: str) -> bool:
        """A second look at a question the planner called off-topic. Observed (2026-10-22):
        Qwen3 judged "How do solid-state batteries work?" out of scope, so only the web was
        searched and it answered about solid-state drives. A one-word check (about 0.5 s;
        11 of 11 right on a test list) lets patent filings answer technology questions."""
        if self._technical is None:
            self._technical = False
            if self.ctx.use_llm_helpers:
                try:
                    response = self.ctx.llm.complete(
                        [ChatMessage("system", TECHNICAL_PROMPT), ChatMessage("user", question)],
                        temperature=0.0,
                        max_tokens=3,
                    )
                    reply = re.sub(r"(?s)<think>.*?</think>", "", response.text).strip().lower()
                    self._technical = reply.startswith("yes")
                except Exception:  # noqa: BLE001 - then the planner's judgement stands
                    logger.info("Technology check failed; keeping the planner's judgement")
        return self._technical

    def _live_keywords(self, state: AgentState) -> str:
        """Search terms for the patent databases. Observed (2026-10-04): the question's own
        words ("wireless charger detect coin") found a coin-operated charging kiosk; patents
        say "foreign object detection". With an LLM available, it rewrites the terms once."""
        fallback = state["analysis"].search_keywords or keywords_from_text(state["question"])
        if self._live_terms is None:
            self._live_terms = fallback
            if self.ctx.use_llm_helpers:
                try:
                    response = self.ctx.llm.complete(
                        [
                            ChatMessage("system", SEARCH_TERMS_PROMPT),
                            ChatMessage("user", state["question"]),
                        ],
                        temperature=0.0,
                        max_tokens=30,
                    )
                    text = re.sub(r"(?s)<think>.*?</think>", "", response.text)
                    words = re.findall(r"[A-Za-z][A-Za-z0-9\-]+", text)[:4]
                    if len(words) >= 2:
                        self._live_terms = " ".join(words).lower()
                except Exception:  # noqa: BLE001 - the question's own words still work
                    logger.info("Search-term rewrite failed; using the question's keywords")
        return self._live_terms

    def _live_steps(self, state: AgentState, patents: bool = True) -> list[Step]:
        """The web and/or the patent offices, used for this answer only (no import)."""
        steps = []
        if self.ctx.web is not None:
            args = {"query": state["question"]}
            if state["analysis"].search_keywords:
                args["terms"] = state["analysis"].search_keywords
            steps.append(Step("search_web", args))
        if patents and self._patents_allowed(state) and self._live_keywords(state):
            steps.append(
                Step(
                    "search_patent_abstracts",
                    {"keywords": self._live_keywords(state), "question": state["question"]},
                )
            )
        return steps

    def generate(self, state: AgentState) -> dict:
        analysis = state["analysis"]
        indexed = [t for t in state["targets"] if t.kind in ("document", "patent") and t.id]
        if analysis.intent == "compare" and len(indexed) >= 2:
            return self._generate_comparison(state, indexed[:4])
        passages = self._final_passages(state)
        evidence = build_evidence(passages, self.ctx.settings.max_context_tokens)
        instructions = (
            [TASK_INSTRUCTIONS[self._task(state)]] if self._task(state) in TASK_INSTRUCTIONS else []
        )
        instructions += self._style()
        question = state["question"]
        terms = self._premise_terms(question, evidence)
        if terms:
            instructions.append(premise.instruction(terms))
        if analysis.legal_question:
            instructions.append(LEGAL_INSTRUCTION)
            # Observed: given the legal question verbatim, Qwen3 refused entirely. Asking the
            # technical question the system CAN answer yields the useful part; the original
            # question is still stored with the run and the UI shows a legal disclaimer.
            question = (
                "Describe and compare the technical features of the sources in the evidence. "
                f'(The user asked: "{question}". Do not give a legal opinion.)'
            )
        response = self._write(
            build_messages(question, evidence, instructions=" ".join(instructions) or None),
            evidence,
        )
        parsed = parse_answer(response.text, {item.label for item in evidence})
        injection = None
        if state.get("inject_false_fact") and state.get("injection") is None:
            planted = plant_false_fact(parsed, {item.label for item in evidence})
            if planted is not None:
                parsed, injection = planted
                logger.info("Demo mode: planted a false sentence (%s)", injection.kind)
        if self.live is not None and parsed.status == "answered":
            self.live.checking(parsed.text)
        return {
            "injection": injection or state.get("injection"),
            "parsed": parsed,
            "evidence": evidence,
            "llm_response": response,
            "final_passages": passages,
            "premise_terms": terms,
        }

    def _premise_terms(self, question: str, evidence: list) -> list[str]:
        if not self.ctx.settings.agent_premise_check or not evidence:
            return []
        return premise.unstated_terms(question, [item.passage.chunk.text for item in evidence])

    def _style(self) -> list[str]:
        if self.chat_style is None:
            return []
        return [CHAT_STYLE] + ([DETAILED_STYLE] if self.chat_style == "detailed" else [])

    def _write(self, messages: list[ChatMessage], evidence: list) -> LLMResponse:
        """The answer-writing LLM call; streamed to the live view when there is one (the
        reply is the same either way)."""
        settings = self.ctx.settings
        if self.live is None:
            return self.ctx.llm.complete(
                messages, temperature=settings.llm_temperature, max_tokens=settings.llm_max_tokens
            )
        self.live.writing(evidence)
        return self.ctx.llm.stream(
            messages,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            on_text=self.live.text,
        )

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
            self.verifier,
            parsed,
            state["evidence"],
            comparison=state.get("comparison"),
            uncited_supported=self.ctx.settings.verifier_uncited_supported,
            premise_terms=state.get("premise_terms"),
        )
        if self.live is not None and state.get("comparison") is None:
            self.live.checked(report)
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
        if self._general_allowed(state):
            return "general"  # the model read the passages and found no answer in them
        report = state.get("verification")
        settings = self.ctx.settings
        latest = state["verify_attempts"][-1]["report"] if state["verify_attempts"] else None
        if (
            report is None
            or settings.verify_mode != "regenerate"
            or state.get("comparison") is not None  # tables are flagged, not rewritten
            or state["regenerations"] >= settings.max_regenerations
            or latest is None
            or not latest.unsupported()
        ):
            return "end"
        if (latest.grounding_score or 0.0) >= settings.grounding_threshold:
            # Demo mode: one planted sentence among many can leave grounding above the
            # threshold; when the checker caught it, rewrite anyway so the demo shows the
            # full loop (flag -> feedback -> corrected answer).
            injection = state.get("injection")
            caught = injection and find_planted(latest.unsupported(), injection)
            return "regenerate" if caught and state["regenerations"] == 0 else "end"
        return "regenerate"

    def regenerate(self, state: AgentState) -> dict:
        """Retrieve evidence for each unsupported statement, then rewrite with feedback."""
        started = time.perf_counter()
        report = state["verify_attempts"][-1]["report"]
        if self.live is not None:
            self.live.rewriting([c.source_text or c.text for c in report.unsupported()])
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
            [TASK_INSTRUCTIONS[self._task(state)]] if self._task(state) in TASK_INSTRUCTIONS else []
        )
        instructions += self._style()
        if analysis.legal_question:
            instructions.append(LEGAL_INSTRUCTION)
        if state.get("premise_terms"):
            instructions.append(premise.instruction(state["premise_terms"]))
        instructions.append(regeneration_instructions(report))
        response = self._write(
            build_messages(state["question"], evidence, instructions=" ".join(instructions)),
            evidence,
        )
        parsed = parse_answer(response.text, {item.label for item in evidence})
        if self.live is not None and parsed.status == "answered":
            self.live.checking(parsed.text)
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

    def _unavailable_patents(self, state: AgentState) -> list[str]:
        """Patent numbers named in the question that are neither indexed nor retrievable."""
        return [t.number for t in state["targets"] if t.kind == "external" and t.number]

    def finish(self, state: AgentState) -> dict:
        reason = state.get("stop_reason")
        unavailable = self._unavailable_patents(state)
        if not reason and unavailable:
            failures = [
                e["output_summary"]
                for e in state["tool_log"]
                if e["tool_name"] == "get_patent_details" and not e["success"]
            ]
            names = ", ".join(unavailable)
            reason = (
                f"{names} {'is' if len(unavailable) == 1 else 'are'} not in your library and "
                "could not be retrieved from a patent database"
                + (f" ({failures[-1]})" if failures else "")
                + ". Upload the document or connect a patent database to ask about it."
            )
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
            unreachable = [f for f in failures if _UNREACHABLE.search(f or "")]
            if unreachable and len(unreachable) == len(failures):
                reason = (
                    "The web and patent offices could not be reached just now (is the internet "
                    "connection working?), and your library has nothing on this. Please try "
                    "again in a moment."
                )
            elif failures:
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
        return (
            state["analysis"].intent == "find_similar"
            and not state["candidates"]
            and not state.get("external_passages")  # a topic search found abstracts
        )

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
        if self.live_fallback and self._can_search_live(state):
            return (
                "nothing in the library answers this; searching the patent databases",
                self._live_steps(state),
            )
        return None

    def _final_passages(self, state: AgentState) -> list[RetrievedPassage]:
        seen, merged = set(), []
        ranked = sorted(state["passages"], key=lambda p: p.rank)
        external = state.get("external_passages") or []
        if external:
            # Interleave library and external passages so each gets a fair share of the
            # evidence budget (their scores are not comparable)
            mixed = []
            for i in range(max(len(ranked), len(external))):
                mixed += ranked[i : i + 1] + external[i : i + 1]
            ranked = mixed
        for passage in state["direct_passages"] + ranked:
            if passage.chunk.id not in seen:
                seen.add(passage.chunk.id)
                merged.append(passage)
        merged = merged[:MAX_EVIDENCE]
        for rank, passage in enumerate(merged, start=1):
            passage.rank = rank
        return merged
