"""Phase 6 (with database): the agent chooses and runs tools, recovers, records steps."""

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.agents.graph import LEGAL_INSTRUCTION, AgentGraph
from app.agents.tools import ToolContext
from app.api.deps import get_patent_sources
from app.core.config import get_settings
from app.database.session import get_db
from app.llm.providers import FakeLLM, LLMResponse, get_llm
from app.main import create_app
from app.models import AgentRun, ToolCall
from app.patents.demo import DemoPatentSource
from app.patents.epo import EpoOpsSource
from app.rag.embeddings import FakeEmbedder, get_embedder
from app.rag.retrieval import RetrievalConfig
from app.services.patents import PatentService
from tests.helpers import fixture_bytes
from tests.test_phase5_epo import FakeOps, load

pytestmark = pytest.mark.db


class RecordingLLM(FakeLLM):
    """Fake LLM that remembers every prompt and can be scripted per call."""

    def __init__(self, replies: list[str] | None = None):
        self.prompts: list[str] = []
        self.replies = list(replies or [])

    def complete(self, messages, *, temperature, max_tokens):
        self.prompts.append("\n".join(m.content for m in messages))
        if self.replies:
            return LLMResponse(self.replies.pop(0), "scripted", 40, 8, 1)
        return super().complete(messages, temperature=temperature, max_tokens=max_tokens)


@pytest.fixture
def settings(tmp_path):
    return get_settings().model_copy(
        update={
            "upload_dir": tmp_path,
            "retrieval_min_similarity": 0.1,
            "patent_demo_source": True,
            "agent_planner": "rules",
            "agent_similar_import_limit": 2,
        }
    )


@pytest.fixture
def llm():
    return RecordingLLM()


@pytest.fixture
def sources():
    return {"demo": DemoPatentSource()}


@pytest.fixture
def api(db_session, settings, llm, sources):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_embedder] = lambda: FakeEmbedder(settings.embedding_dim)
    app.dependency_overrides[get_llm] = lambda: llm
    app.dependency_overrides[get_patent_sources] = lambda: sources
    with TestClient(app) as client:
        client.app_ref = app
        yield client


@pytest.fixture
def battery(api):
    response = api.post(
        "/documents", files={"file": ("battery.txt", fixture_bytes("battery_patent.txt"))}
    )
    return response.json()["document"]


def ask(api, question, **extra):
    response = api.post("/ask", json={"question": question, **extra})
    assert response.status_code == 200, response.text
    return response.json()


def tools_used(body) -> list[str]:
    return [s["tool_name"] for s in body["steps"]]


# ------------------------------------------------------------------ tool selection


def test_general_question_searches_local_index(api, battery, db_session):
    body = ask(api, "How is the coolant pump speed controlled?")
    assert body["pipeline"] == "agentic"
    assert body["intent"] == "document_qa"
    assert tools_used(body) == ["search_uploaded_documents"]
    assert body["status"] == "succeeded"
    stored = db_session.scalars(
        select(ToolCall).where(ToolCall.agent_run_id == body["run_id"])
    ).all()
    assert [(c.tool_name, c.success) for c in stored] == [("search_uploaded_documents", True)]


def test_claim_question_fetches_that_claim_first(api, battery):
    body = ask(api, "What does claim 3 of my patent add?", document_ids=[battery["id"]])
    assert tools_used(body) == ["retrieve_document_section", "retrieve_evidence"]
    first = body["evidence"][0]
    assert (first["section"], first["claim_number"], first["rank"]) == ("claims", 3, 1)


def test_unknown_patent_number_is_fetched_then_used(api, battery):
    body = ask(api, "What does XX0000002B1 claim?")
    assert body["intent"] == "patent_lookup"
    assert tools_used(body) == [
        "get_patent_details",
        "retrieve_document_section",
        "retrieve_evidence",
    ]
    assert {e["source_label"] for e in body["evidence"]} == {"XX0000002B1"}
    assert body["targets"][0]["kind"] == "patent"
    assert "Demo patents" in body["summary"]["sources_searched"]


def test_find_similar_searches_imports_and_compares(api, battery):
    body = ask(api, "Find patents similar to my uploaded invention")
    assert body["intent"] == "find_similar"
    tools = tools_used(body)
    assert tools[:2] == ["extract_key_concepts", "search_patents"]
    assert tools.count("get_patent_details") == 2  # agent_similar_import_limit
    assert tools[-1] == "compare_patents"
    sources = {e["source_label"] for e in body["evidence"]}
    assert "battery.txt" in sources and any(s.startswith("XX") for s in sources)


def test_compare_two_patents_gets_balanced_evidence(api):
    body = ask(api, "Compare XX0000001A1 with XX0000003A1")
    assert body["intent"] == "compare"
    assert tools_used(body) == ["get_patent_details", "get_patent_details", "compare_patents"]
    labels = [e["source_label"] for e in body["evidence"]]
    assert labels.count("XX0000001A1") >= 2 and labels.count("XX0000003A1") >= 2


def test_compare_returns_structured_table(api):
    body = ask(api, "Compare XX0000001A1 with XX0000003A1")
    table = body["comparison"]
    assert table["mode"] == "extractive"  # fake LLM → no-LLM extractive comparison
    assert [src["label"] for src in table["sources"]] == ["XX0000001A1", "XX0000003A1"]
    assert "Technical similarities" in body["answer"]


def test_legal_question_is_flagged_and_disclaimed(api, battery, llm):
    body = ask(api, "Is claim 1 of XX0000001A1 valid?")
    assert body["legal_question"] is True
    assert body["intent"] == "patent_lookup"
    assert LEGAL_INSTRUCTION in llm.prompts[-1]
    assert "Do not give a legal opinion" in llm.prompts[-1]


# ------------------------------------------------------------------ failures & recovery


def test_missing_patent_source_fails_gracefully(api, sources):
    sources.clear()
    body = ask(api, "What does EP1234567A1 claim?")
    assert body["status"] == "insufficient_evidence"
    assert body["steps"][0] == {
        **body["steps"][0],
        "tool_name": "get_patent_details",
        "success": False,
    }
    assert "no suitable patent source" in body["insufficient_reason"]


def test_failed_search_is_recovered_with_fewer_keywords(api, battery, sources):
    calls = {"n": 0}
    fake = FakeOps()

    def handler(request):
        if request.url.path.endswith("/search/biblio"):
            calls["n"] += 1
            if calls["n"] == 1:
                return httpx.Response(404, text="<error>no results</error>")
            return httpx.Response(200, json=load("search_biblio.json"))
        return fake(request)

    sources.clear()
    sources["epo"] = EpoOpsSource(
        "k", "s", http=httpx.Client(transport=httpx.MockTransport(handler))
    )
    body = ask(api, "Find patents similar to my uploaded invention")
    assert len(body["recoveries"]) == 1 and "fewer keywords" in body["recoveries"][0]
    assert tools_used(body).count("search_patents") == 2
    assert calls["n"] == 2


def test_out_of_scope_label_still_searches_and_abstains_on_evidence(api, settings):
    # Phase 9: the LLM's "out_of_scope" no longer stops the agent (it once refused a valid
    # technical question). Off-topic questions abstain because no evidence is found.
    llm = RecordingLLM(replies=['{"intent": "out_of_scope"}'])
    api.app_ref.dependency_overrides[get_llm] = lambda: llm
    api.app_ref.dependency_overrides[get_settings] = lambda: settings.model_copy(
        update={"agent_planner": "llm"}
    )
    body = ask(api, "What's a good pasta recipe?")
    assert body["status"] == "insufficient_evidence"
    assert [s["tool_name"] for s in body["steps"]] == ["search_uploaded_documents"]
    assert len(llm.prompts) == 1  # only the planner call: the evidence gate stops the rest


def test_llm_usage_is_summed_over_all_calls(api, battery, settings, db_session):
    reply = '{"intent": "find_similar", "search_keywords": "battery coolant"}'
    llm = RecordingLLM(replies=[reply, "coolant temperature battery"])
    api.app_ref.dependency_overrides[get_llm] = lambda: llm
    api.app_ref.dependency_overrides[get_settings] = lambda: settings.model_copy(
        update={"agent_planner": "llm"}
    )
    body = ask(api, "Is anything out there like my invention?")
    run = db_session.get(AgentRun, body["run_id"])
    assert run.config["llm_calls"] == 3  # planner + concepts + answer
    assert run.plan["analysis"]["analyzer"] == "llm"
    assert run.prompt_tokens >= 80


def test_baseline_pipeline_still_available(api, battery):
    body = ask(api, "How is the coolant pump speed controlled?", pipeline="baseline")
    assert body["pipeline"] == "baseline_rag"
    assert body["steps"] == []


# ------------------------------------------------------------------ graph structure


def test_graph_diagram_lists_all_nodes(db_session, settings):
    ctx = ToolContext(
        session=db_session,
        settings=settings,
        embedder=FakeEmbedder(settings.embedding_dim),
        llm=FakeLLM(),
        patents=PatentService(db_session, settings, FakeEmbedder(settings.embedding_dim), {}),
        retrieval=RetrievalConfig(),
    )
    diagram = AgentGraph(ctx, planner="rules", similar_import_limit=1, max_recoveries=1).mermaid()
    for node in (
        "analyze",
        "resolve_targets",
        "plan",
        "execute",
        "check",
        "recover",
        "generate",
        "finish",
    ):
        assert node in diagram


# ------------------------------------------------------------------ choosing the subject


@pytest.fixture
def both_documents(api, battery):
    wireless = api.post(
        "/documents", files={"file": ("wireless.txt", fixture_bytes("wireless_patent.txt"))}
    ).json()["document"]
    return battery, wireless


def test_subject_is_chosen_by_title_not_by_upload_order(api, both_documents):
    battery, _ = both_documents  # wireless was uploaded last
    body = ask(api, "Find patents similar to my battery thermal management invention")
    assert body["targets"][0]["id"] == battery["id"]


def test_claim_question_names_document_by_title(api, both_documents):
    body = ask(api, "What does claim 3 of the battery patent add to claim 1?")
    assert tools_used(body)[0] == "retrieve_document_section"
    assert body["evidence"][0]["claim_number"] == 3


def test_ambiguous_subject_is_not_guessed(api, both_documents, llm):
    body = ask(api, "Find patents similar to my invention")
    assert body["status"] == "insufficient_evidence"
    assert "Which invention" in body["insufficient_reason"]
    assert body["steps"] == [] and llm.prompts == []


def test_compare_of_two_numbers_does_not_add_uploaded_documents(api, both_documents):
    body = ask(api, "Compare XX0000001A1 with XX0000003A1")
    assert {t["kind"] for t in body["targets"]} == {"patent"}
    assert {e["source_label"] for e in body["evidence"]} == {"XX0000001A1", "XX0000003A1"}


def test_infringement_question_compares_my_patent_with_the_number(api, battery):
    body = ask(api, "Does my battery patent infringe XX0000001A1?")
    assert body["intent"] == "compare" and body["legal_question"] is True
    labels = {e["source_label"] for e in body["evidence"]}
    assert labels == {"battery.txt", "XX0000001A1"}


def test_my_patent_means_uploaded_document_even_if_patents_share_title_words(api, both_documents):
    battery, _ = both_documents
    # imported demo patents also have "battery" in their titles
    api.post("/patents/import", json={"source": "demo", "publication_number": "XX0000003A1"})
    body = ask(api, "Does my battery patent infringe XX0000001A1?")
    assert [t["label"] for t in body["targets"]][0] == battery["title"]
    assert {e["source_label"] for e in body["evidence"]} == {"battery.txt", "XX0000001A1"}


# ------------------------------------------------------------------ Experiment F control


def use_policy(api, settings, policy):
    api.app_ref.dependency_overrides[get_settings] = lambda: settings.model_copy(
        update={"agent_tool_policy": policy}
    )


def test_all_tools_policy_runs_every_available_tool(api, battery, settings, db_session):
    use_policy(api, settings, "all")
    body = ask(api, "How is the coolant pump speed controlled?", document_ids=[battery["id"]])
    used = tools_used(body)
    assert used[:4] == [
        "search_uploaded_documents",
        "retrieve_evidence",
        "extract_key_concepts",
        "search_patents",
    ]
    assert "get_patent_details" in used  # imports the top search results (demo source)
    assert body["status"] == "succeeded"
    assert db_session.get(AgentRun, body["run_id"]).config["agent"]["tool_policy"] == "all"


def test_all_tools_policy_skips_unavailable_patent_search(api, battery, settings):
    use_policy(api, settings, "all")
    api.app_ref.dependency_overrides[get_patent_sources] = lambda: {}
    body = ask(api, "How is the coolant pump speed controlled?")
    assert tools_used(body) == ["search_uploaded_documents"]  # no target, no patent source
