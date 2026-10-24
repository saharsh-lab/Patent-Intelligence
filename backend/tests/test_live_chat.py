"""Live chat: the answer streamed as it is written, sources as they are found, the
checker's verdicts as they come, searches at the same time, instant replies about the
assistant itself, and follow-up suggestions."""

import time
import uuid
from types import SimpleNamespace

import httpx
import pytest
from sqlalchemy import create_engine

from app.agents import graph as graph_module
from app.agents.analysis import analyze_rules, is_small_talk
from app.agents.graph import AgentGraph, Step
from app.agents.live import LiveAnswer
from app.agents.tools import TOOLS, ToolContext, ToolResult
from app.core.config import get_settings
from app.core.errors import ExternalServiceError
from app.core.ownership import owner_scope, scoped
from app.core.security import rate_rules
from app.llm.providers import ChatMessage, FakeLLM, LLMResponse, OpenAICompatibleLLM, visible_text
from app.services import progress
from app.services.chat import parse_suggestions
from tests.test_phase8_verification_api import QUESTION, make_api

# ---------------------------------------------------------------- streaming


class FakeStream:
    def __init__(self, status: int, lines: list[str], fail_after: int | None = None):
        self.status_code, self.lines, self.fail_after = status, lines, fail_after

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def iter_lines(self):
        for i, line in enumerate(self.lines):
            if self.fail_after is not None and i >= self.fail_after:
                raise httpx.ReadError("connection lost")
            yield line


def event(text: str) -> str:
    return 'data: {"choices":[{"delta":{"content":' + repr(text).replace("'", '"') + "}}]}"


LLM = OpenAICompatibleLLM("http://localhost:11434/v1", "", "qwen3:8b")
MESSAGES = [ChatMessage("user", "How is the pump controlled?")]


def test_stream_shows_the_reply_as_it_is_written_without_reasoning(monkeypatch):
    lines = [
        event("<think>plan"),
        event("</think>The pump"),
        event(" speeds up [E1]."),
        'data: {"choices":[],"usage":{"prompt_tokens":11,"completion_tokens":5}}',
        "data: [DONE]",
    ]
    monkeypatch.setattr(httpx, "stream", lambda *a, **k: FakeStream(200, lines))
    seen: list[str] = []
    response = LLM.stream(MESSAGES, temperature=0, max_tokens=50, on_text=seen.append)
    assert seen == ["", "The pump", "The pump speeds up [E1]."]
    assert response.text == "The pump speeds up [E1]."
    assert (response.prompt_tokens, response.usage_estimated) == (11, False)


def test_without_streaming_the_whole_reply_arrives_at_once(monkeypatch):
    monkeypatch.setattr(httpx, "stream", lambda *a, **k: FakeStream(404, []))
    monkeypatch.setattr(
        OpenAICompatibleLLM, "complete", lambda self, m, **k: LLMResponse("Whole.", "m", 1, 1, 5)
    )
    seen: list[str] = []
    assert LLM.stream(MESSAGES, temperature=0, max_tokens=5, on_text=seen.append).text == "Whole."
    assert seen == ["Whole."]
    # FakeLLM (and any provider without streaming) behaves the same way
    assert FakeLLM().stream(MESSAGES, temperature=0, max_tokens=5, on_text=seen.append).text


def test_a_stream_that_breaks_off_is_an_error_not_half_an_answer(monkeypatch):
    lines = [event("The pump"), event(" speeds")]
    monkeypatch.setattr(httpx, "stream", lambda *a, **k: FakeStream(200, lines, fail_after=1))
    with pytest.raises(ExternalServiceError):
        LLM.stream(MESSAGES, temperature=0, max_tokens=5, on_text=lambda text: None)


def test_reasoning_is_never_shown():
    assert visible_text("<think>still thinking") == ""
    assert visible_text("<think>done</think>\nAnswer") == "Answer"


# ---------------------------------------------------------------- live answer


def test_live_answer_draft_hides_the_insufficient_evidence_marker():
    states = []
    live = LiveAnswer(states.append)
    live.text("The pump speeds up [E1].\nINSUFFICIENT_EVIDENCE: the flow rate is not given")
    live.checked(None)
    assert states[-1]["draft"] == "The pump speeds up [E1]." and states[-1]["phase"] == "checked"


class Hallucinating(FakeLLM):
    """First draft: quotes the evidence, plus one invented sentence. Then quotes only."""

    def __init__(self):
        self.calls = 0

    def complete(self, messages, *, temperature, max_tokens):
        response = super().complete(messages, temperature=temperature, max_tokens=max_tokens)
        self.calls += 1
        if self.calls == 1:
            response.text += " The coolant pump is painted purple by tiny robots on Mars [E1]."
        return response


@pytest.mark.db
def test_chat_shows_sources_draft_verdicts_and_the_rewrite_as_they_happen(
    db_session, tmp_path, monkeypatch
):
    states = []
    original = progress.publish_live
    monkeypatch.setattr(
        progress, "publish_live", lambda key, live: (states.append(live), original(key, live))
    )
    api = make_api(db_session, tmp_path, Hallucinating())
    cid = api.post("/conversations", json={}).json()["id"]
    reply = api.post(f"/conversations/{cid}/messages", json={"message": QUESTION}).json()

    phases = [s["phase"] for s in states]
    order = [p for i, p in enumerate(phases) if i == 0 or phases[i - 1] != p]
    assert order == [
        "searching",
        "writing",
        "checking",
        "checked",
        "rewriting",
        "writing",
        "checking",
        "checked",
    ]
    assert states[0]["sources"][0] == {
        "kind": "library",
        "label": "battery.txt",
        "title": states[0]["sources"][0]["title"],
        "url": None,
    }
    writing = next(s for s in states if s["phase"] == "writing")
    assert writing["evidence"][0]["label"] == "E1"
    assert writing["evidence"][0]["source"] == "battery.txt"
    flagged = next(s for s in states if s["phase"] == "rewriting")["flagged"]
    assert any("purple" in sentence for sentence in flagged)
    first_check = next(s for s in states if s["phase"] == "checked")
    assert any(c["verdict"] == "unsupported" for c in first_check["claims"])
    assert states[-1]["attempt"] == 2
    # what was shown last is the answer that was kept
    assert "purple" not in reply["response"]["answer"]
    assert states[-1]["draft"] == reply["response"]["answer"]
    # the poll returns the live answer until the next question starts
    polled = api.get(f"/conversations/{cid}/progress").json()
    assert polled["running"] is False and polled["live"]["attempt"] == 2


@pytest.mark.db
def test_the_ask_api_and_experiments_get_no_live_view(db_session, tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(progress, "publish_live", lambda key, live: calls.append(live))
    api = make_api(db_session, tmp_path, FakeLLM())
    assert api.post("/ask", json={"question": QUESTION}).status_code == 200
    assert calls == []


# ---------------------------------------------------------------- parallel searches


class FakeSession:
    def __init__(self, bind=None):
        self.bind = bind or create_engine("sqlite://")

    def get_bind(self):
        return self.bind

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


def _graph(parallel: bool) -> AgentGraph:
    ctx = ToolContext(
        session=FakeSession(),
        settings=get_settings(),
        embedder=None,
        llm=None,
        patents=SimpleNamespace(sources={}),
        retrieval=None,
    )
    return AgentGraph(
        ctx, planner="rules", similar_import_limit=0, max_recoveries=0, parallel_searches=parallel
    )


STEPS = [
    Step("search_uploaded_documents", {"query": "q"}),
    Step("search_web", {"query": "q"}),
    Step("search_patent_abstracts", {"keywords": "k", "question": "q"}),
    Step("compare_patents", {"query": "q", "targets": "$targets"}),
]


def test_independent_searches_run_together_and_keep_plan_order(monkeypatch):
    monkeypatch.setattr(graph_module, "Session", FakeSession)
    monkeypatch.setattr(graph_module, "PatentService", lambda *a: None)

    def slow(name):
        def tool(ctx, **args):
            time.sleep(0.3)
            return ToolResult(name, data={"session": ctx.session, "scoped": scoped()})

        return tool

    for step in STEPS[:3]:
        monkeypatch.setitem(TOOLS, step.tool, slow(step.tool))
    graph = _graph(parallel=True)
    batch = graph._parallel_batch(STEPS)
    assert [s.tool for s in batch] == [s.tool for s in STEPS[:3]]  # stops at a dependent step

    started = time.perf_counter()
    with owner_scope(uuid.uuid4()):
        outcomes = graph._run_parallel(batch, {"live_search": False})
    assert time.perf_counter() - started < 0.75  # three 0.3 s searches, not 0.9 s
    assert [entry["output_summary"] for _, entry, _ in outcomes] == [s.tool for s in STEPS[:3]]
    results = [result for _, _, result in outcomes]
    assert results[0].data["session"] is graph.ctx.session  # the first keeps the request's
    assert all(r.data["session"] is not graph.ctx.session for r in results[1:])
    assert all(r.data["scoped"] for r in results)  # whose documents are visible holds there too
    rows = [r for r in graph.trace.rows if r["kind"] == "tool"]
    assert len(rows) == 3 and all(r["status"] == "done" for r in rows)


def test_searches_run_one_after_another_when_switched_off_or_on_one_connection():
    assert _graph(parallel=False)._parallel_batch(STEPS) == []
    graph = _graph(parallel=True)
    graph.ctx.session = FakeSession(bind=SimpleNamespace())  # a connection, not an engine
    assert graph._parallel_batch(STEPS) == []


# ---------------------------------------------------------------- questions about the assistant


@pytest.mark.parametrize(
    "message",
    [
        "Can I talk anything?",
        "can i talk to you about anything",
        "Can I ask you anything?",
        "What should I ask?",
        "How do you work?",
        "Are you an AI?",
        "How can you help me?",
    ],
)
def test_questions_about_the_assistant_are_answered_at_once(message):
    assert analyze_rules(message).intent == "small_talk"


@pytest.mark.parametrize(
    "message",
    [
        "Can I patent my idea?",
        "How does it work?",
        "What do you know about solid-state batteries?",
        "Can you help me find patents on immersion cooling?",
        "Who made this invention?",
    ],
)
def test_real_questions_are_not_mistaken_for_chat(message):
    assert not is_small_talk(message)


class NoLLM(FakeLLM):
    def complete(self, messages, *, temperature, max_tokens):
        raise AssertionError("no model call is needed for this")


@pytest.mark.db
def test_can_i_talk_about_anything_gets_an_instant_helpful_reply(db_session, tmp_path):
    api = make_api(db_session, tmp_path, NoLLM())
    cid = api.post("/conversations", json={}).json()["id"]
    run = api.post(f"/conversations/{cid}/messages", json={"message": "Can I talk anything?"})
    body = run.json()["response"]
    assert body["intent"] == "small_talk" and body["evidence"] == []
    assert body["answer"].startswith("Yes, ask me anything") and "legal" in body["answer"]


# ---------------------------------------------------------------- follow-up suggestions


def test_suggestions_are_short_questions_without_repeats_or_legal_advice():
    reply = (
        "<think>x</think>1. How does the controller read the temperature?\n"
        '- "What coolant does the pump use?"\n'
        "3) Does this patent infringe on Tesla's?\n"
        "Why?\n"
        "How does the controller decide when to increase the coolant pump speed?\n"
        "Which sensors are used?"
    )
    assert parse_suggestions(reply, exclude=QUESTION) == [
        "How does the controller read the temperature?",
        "What coolant does the pump use?",
        "Which sensors are used?",
    ]


class Suggesting(FakeLLM):
    def __init__(self):
        self.suggestion_calls = 0

    def complete(self, messages, *, temperature, max_tokens):
        if messages[0].content.startswith("Suggest"):
            self.suggestion_calls += 1
            return LLMResponse("What coolant is used?\nWhich sensors are read?", "m", 1, 1, 1)
        return super().complete(messages, temperature=temperature, max_tokens=max_tokens)


@pytest.mark.db
def test_suggestions_are_written_once_and_kept_with_the_answer(db_session, tmp_path):
    llm = Suggesting()
    api = make_api(db_session, tmp_path, llm, llm_provider="openai_compatible")
    cid = api.post("/conversations", json={}).json()["id"]
    run_id = api.post(f"/conversations/{cid}/messages", json={"message": QUESTION}).json()["run_id"]
    url = f"/conversations/{cid}/messages/{run_id}/suggestions"
    first = api.post(url).json()["suggestions"]
    assert first == ["What coolant is used?", "Which sensors are read?"]
    assert api.post(url).json()["suggestions"] == first and llm.suggestion_calls == 1
    assert api.post(f"/conversations/{cid}/messages/{uuid.uuid4()}/suggestions").status_code == 404


# ---------------------------------------------------------------- polling budget


def test_live_polling_has_its_own_rate_limit():
    rules = rate_rules(get_settings())
    poll = next(r for r in rules if r.name == "poll")
    assert poll.matches("GET", "/conversations/abc/progress")
    assert not poll.matches("GET", "/conversations/abc")
    assert not poll.matches("POST", "/conversations/abc/progress")
    first = next(r for r in rules if r.matches("POST", "/conversations/abc/messages"))
    assert first.name == "llm"
