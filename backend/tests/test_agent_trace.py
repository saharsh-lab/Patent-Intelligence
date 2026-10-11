"""Phase 15: the live agent trace (steps, tool calls, reasons, durations)."""

import pytest

from app.agents.trace import TraceRecorder, tool_reason
from app.llm.providers import FakeLLM
from tests.test_phase8_verification_api import QUESTION, make_api


def test_recorder_publishes_rows_as_they_start_and_end():
    seen = []
    trace = TraceRecorder(lambda rows: seen.append([(r["name"], r["status"]) for r in rows]))
    node = trace.traced("analyze", lambda state: {})
    node({})
    assert seen == [[("analyze", "running")], [("analyze", "done")]]
    assert trace.rows[0]["label"] == "Understanding the question" and trace.rows[0]["ms"] >= 0


def test_a_broken_sink_never_stops_the_agent():
    def broken(rows):
        raise RuntimeError("display failed")

    trace = TraceRecorder(broken)
    assert trace.traced("plan", lambda state: {"steps": []})({}) == {"steps": []}


def test_a_failing_node_is_marked_failed():
    trace = TraceRecorder()

    def boom(state):
        raise ValueError("x")

    with pytest.raises(ValueError):
        trace.traced("generate", boom)({})
    assert trace.rows[0]["status"] == "failed"


def test_tool_reasons_are_plain_language():
    assert "library" in tool_reason("search_uploaded_documents", {}, {})
    assert "claim 3" in tool_reason("retrieve_document_section", {"claim_number": 3}, {})
    assert "switch" in tool_reason("search_patent_abstracts", {}, {"live_search": True})


@pytest.mark.db
def test_answer_stores_its_trace(db_session, tmp_path):
    body = (
        make_api(db_session, tmp_path, FakeLLM()).post("/ask", json={"question": QUESTION}).json()
    )
    rows = body["trace"]
    names = [r["name"] for r in rows]
    assert names[0] == "analyze" and "search_uploaded_documents" in names
    assert names.index("generate") < names.index("verify")
    tool = next(r for r in rows if r["kind"] == "tool")
    assert tool["why"] and tool["status"] == "done" and tool["detail"]
    assert all(r["status"] == "done" and r["ms"] is not None for r in rows)
    assert [r["at_ms"] for r in rows] == sorted(r["at_ms"] for r in rows)
    verify = next(r for r in rows if r["name"] == "verify")
    assert "sentences supported" in verify["detail"]
