"""Chat upgrade (2026-10-22): everyday questions answered exactly, general knowledge when no
source has the answer (labelled, chat only), the chat writing style, Stop, the optional cloud
model and keeping the local model loaded."""

import threading
from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from app.agents.everyday import asks_for_time, calculation, clock_reply, is_creative
from app.agents.graph import CHAT_STYLE, DETAILED_STYLE, AgentGraph
from app.core import warmup
from app.core.config import get_settings
from app.llm.providers import FakeLLM, LLMResponse, OpenAICompatibleLLM, cloud_llm
from app.services import progress
from tests.helpers import fixture_bytes
from tests.test_live_chat import NoLLM
from tests.test_phase8_verification_api import QUESTION, make_api

# ---------------------------------------------------------------- exact answers (no DB)


def test_the_calculator_is_exact_and_runs_nothing_but_arithmetic():
    assert calculation("What is 15% of 240?") == ("15% of 240", "36")
    assert calculation("how much is 7 x 8?") == ("7 × 8", "56")
    assert calculation("calculate 1,200 / 3") == ("1200 / 3", "400")
    for not_a_sum in ["__import__('os').system('ls')", "2**10000", "1/0", "What is 5G?", "2023"]:
        assert calculation(not_a_sum) is None


def test_the_clock_answers_in_the_users_time_zone():
    assert "(Asia/Kolkata)" in clock_reply("What day is it?", "Asia/Kolkata")
    assert "(" not in clock_reply("What day is it?", "Not/AZone")  # unknown: server time, no label
    assert asks_for_time("what's the date today?")
    assert not asks_for_time("What date was the patent filed?")


def test_only_writing_tasks_skip_the_search():
    assert is_creative("Write a poem about batteries") and is_creative("Tell me a joke")
    assert not is_creative("Write a summary of my patent")


def test_chat_answers_get_the_chat_style_and_the_api_does_not():
    ctx = SimpleNamespace(settings=get_settings())
    graph = AgentGraph.__new__(AgentGraph)
    graph.ctx, graph.chat_style = ctx, None
    assert graph._style() == []
    graph.chat_style = "detailed"
    assert graph._style() == [CHAT_STYLE, DETAILED_STYLE]


# ---------------------------------------------------------------- through the chat


@pytest.mark.db
def test_date_and_sums_are_answered_at_once_without_the_model(db_session, tmp_path):
    api = make_api(db_session, tmp_path, NoLLM())
    cid = api.post("/conversations", json={}).json()["id"]
    run = api.post(
        f"/conversations/{cid}/messages",
        json={"message": "What day is it?", "timezone": "Asia/Tokyo"},
    ).json()["response"]
    assert (run["intent"], run["everyday"], run["evidence"]) == ("everyday", "clock", [])
    assert "Asia/Tokyo" in run["answer"]
    run = api.post(f"/conversations/{cid}/messages", json={"message": "12*7"}).json()
    assert run["response"]["answer"] == "12 × 7 = **84**"
    suggestions = api.post(f"/conversations/{cid}/messages/{run['run_id']}/suggestions")
    assert suggestions.json()["suggestions"] == []


class GeneralKnowledge(FakeLLM):
    """No source has the answer; from general knowledge the model knows it."""

    def __init__(self):
        self.prompts = []

    def complete(self, messages, *, temperature, max_tokens):
        system = messages[0].content
        self.prompts.append(messages[-1].content)
        if system.startswith("You are the assistant of a patent research app"):
            return LLMResponse("Hamlet was written by **William Shakespeare**.", "m", 9, 9, 1)
        return LLMResponse("INSUFFICIENT_EVIDENCE: not in the evidence", "m", 9, 9, 1)


@pytest.mark.db
def test_a_question_no_source_answers_gets_a_labelled_general_answer(db_session, tmp_path):
    api = make_api(db_session, tmp_path, GeneralKnowledge())
    cid = api.post("/conversations", json={}).json()["id"]
    run = api.post(f"/conversations/{cid}/messages", json={"message": "Who wrote Hamlet?"}).json()
    body = run["response"]
    assert body["status"] == "succeeded" and "Shakespeare" in body["answer"]
    assert body["general"]["searched"] is True and body["general"]["not_found"]
    assert body["verification"] is None and body["evidence"] == []
    assert "search_uploaded_documents" in [s["tool_name"] for s in body["steps"]]
    assert [r["name"] for r in body["trace"]][-1] == "general"


@pytest.mark.db
def test_the_api_and_questions_about_attached_documents_never_get_general_answers(
    db_session, tmp_path
):
    api = make_api(db_session, tmp_path, GeneralKnowledge())
    assert api.post("/ask", json={"question": "Who wrote Hamlet?"}).json()["status"] == (
        "insufficient_evidence"
    )
    cid = api.post("/conversations", json={}).json()["id"]
    api.post(
        f"/conversations/{cid}/documents",
        files={"file": ("battery.txt", fixture_bytes("battery_patent.txt"))},
    )
    body = api.post(f"/conversations/{cid}/messages", json={"message": QUESTION}).json()
    assert body["response"]["status"] == "insufficient_evidence"
    assert body["response"]["general"] is None


@pytest.mark.db
def test_a_writing_task_goes_straight_to_the_model(db_session, tmp_path):
    api = make_api(db_session, tmp_path, GeneralKnowledge())
    cid = api.post("/conversations", json={}).json()["id"]
    body = api.post(
        f"/conversations/{cid}/messages", json={"message": "Write a poem about batteries"}
    ).json()["response"]
    assert body["steps"] == [] and body["general"] == {"searched": False, "not_found": None}


class RecordingLLM(FakeLLM):
    def __init__(self):
        self.prompts = []

    def complete(self, messages, *, temperature, max_tokens):
        self.prompts.append(messages[-1].content)
        return super().complete(messages, temperature=temperature, max_tokens=max_tokens)


@pytest.mark.db
def test_only_chat_answers_are_written_in_the_chat_style(db_session, tmp_path):
    llm = RecordingLLM()
    api = make_api(db_session, tmp_path, llm)
    api.post("/ask", json={"question": QUESTION})
    assert not any(CHAT_STYLE in p for p in llm.prompts)
    cid = api.post("/conversations", json={}).json()["id"]
    api.post(f"/conversations/{cid}/messages", json={"message": QUESTION})
    assert any(CHAT_STYLE in p for p in llm.prompts)


# ---------------------------------------------------------------- Stop


@pytest.mark.db
def test_stop_ends_the_answer_and_keeps_it_marked_as_stopped(db_session, tmp_path, monkeypatch):
    original = progress.publish

    def publish(key, rows):
        original(key, rows)
        if any(r["name"] == "generate" for r in rows):
            progress.request_stop(key)  # the user presses Stop while the answer is written

    monkeypatch.setattr(progress, "publish", publish)
    api = make_api(db_session, tmp_path, FakeLLM())
    cid = api.post("/conversations", json={}).json()["id"]
    body = api.post(f"/conversations/{cid}/messages", json={"message": QUESTION}).json()
    assert body["response"]["status"] == "stopped"
    assert api.get(f"/conversations/{cid}/progress").json()["running"] is False
    assert api.post(f"/conversations/{cid}/stop").status_code == 204  # nothing running: no-op


# ---------------------------------------------------------------- models


def test_the_cloud_model_is_offered_only_with_a_key():
    settings = get_settings()
    assert cloud_llm(settings.model_copy(update={"cloud_llm_api_key": SecretStr("")})) is None
    cloud = cloud_llm(settings.model_copy(update={"cloud_llm_api_key": SecretStr("gsk-test")}))
    assert isinstance(cloud, OpenAICompatibleLLM) and cloud.model == settings.cloud_llm_model


@pytest.mark.db
def test_system_info_says_whether_the_cloud_model_exists_without_the_key(db_session, tmp_path):
    api = make_api(db_session, tmp_path, FakeLLM(), cloud_llm_api_key=SecretStr("gsk-secret-123"))
    info = api.get("/system/info")
    assert info.json()["cloud_llm"]["available"] is True
    assert "gsk-secret-123" not in info.text


def test_a_local_model_is_kept_loaded_and_a_remote_one_is_left_alone(monkeypatch):
    calls = []

    class Counter(FakeLLM):
        def complete(self, messages, *, temperature, max_tokens):
            calls.append(max_tokens)
            return super().complete(messages, temperature=temperature, max_tokens=max_tokens)

    monkeypatch.setattr("app.llm.providers.build_llm", lambda settings: Counter())
    local = get_settings().model_copy(
        update={
            "llm_provider": "openai_compatible",
            "llm_base_url": "http://localhost:11434/v1",
            "llm_keep_warm_minutes": 4.0,
        }
    )
    assert warmup.local_llm(local)
    assert not warmup.local_llm(local.model_copy(update={"llm_base_url": "https://api.x.ai/v1"}))
    stop = threading.Event()
    stop.set()  # one ping, then stop
    warmup.keep_warm(local, stop)
    assert calls == [1]
