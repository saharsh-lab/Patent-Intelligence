"""General questions answered from the web: cited, verified, never stored (2026-10-10)."""

import json

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.api.deps import get_patent_sources
from app.core.config import get_settings
from app.core.logging import redact
from app.database.session import get_db
from app.llm.providers import FakeLLM, get_llm
from app.main import create_app
from app.models import Chunk, RetrievalResult
from app.rag.embeddings import FakeEmbedder, get_embedder
from app.services import agent as agent_module
from app.web.search import TavilySearch, WebResult, WebSearch, WikipediaSearch


class FakeWeb(WebSearch):
    name = "tavily"
    label = "Web (Tavily)"

    def __init__(self):
        self.queries = []

    def search(self, query, max_results):
        self.queries.append(query)
        return [
            WebResult(
                "Patent claim - Wikipedia",
                "https://en.wikipedia.org/wiki/Patent_claim",
                "In a patent, the claims define in technical terms the scope of the "
                "protection conferred by the patent.",
            ),
            WebResult("Cooking pasta", "https://example.com/pasta", "Boil water and add salt."),
        ]


@pytest.fixture
def web(monkeypatch):
    fake = FakeWeb()
    monkeypatch.setattr(agent_module, "build_web_search", lambda settings: fake)
    return fake


@pytest.fixture
def api(db_session, tmp_path):
    settings = get_settings().model_copy(
        update={"upload_dir": tmp_path, "agent_planner": "rules", "retrieval_min_similarity": 0.1}
    )
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_embedder] = lambda: FakeEmbedder(settings.embedding_dim)
    app.dependency_overrides[get_llm] = lambda: FakeLLM()
    app.dependency_overrides[get_patent_sources] = lambda: {}
    with TestClient(app) as client:
        yield client


@pytest.mark.db
def test_general_question_is_answered_from_cited_web_pages(api, web, db_session):
    body = api.post("/ask", json={"question": "What does a patent claim define?"}).json()
    assert [s["tool_name"] for s in body["steps"]] == ["search_uploaded_documents", "search_web"]
    assert web.queries == ["What does a patent claim define?"]
    assert body["status"] == "succeeded"
    page = next(e for e in body["evidence"] if e["source_label"] == "en.wikipedia.org")
    assert page["source_type"] == "tavily" and page["source_url"].endswith("/Patent_claim")
    assert body["verification"] is not None  # web evidence is checked like any other
    # used for this answer only: nothing stored as library chunks
    assert db_session.scalar(select(func.count()).select_from(Chunk)) == 0
    stored = db_session.scalars(select(RetrievalResult)).all()
    assert stored and all(r.chunk_id is None for r in stored)


@pytest.mark.db
def test_questions_about_attached_documents_do_not_search_the_web(api, web):
    from tests.helpers import fixture_bytes

    doc = api.post(
        "/documents", files={"file": ("battery.txt", fixture_bytes("battery_patent.txt"))}
    ).json()["document"]
    body = api.post(
        "/ask",
        json={"question": "How is the coolant pump controlled?", "document_ids": [doc["id"]]},
    ).json()
    assert "search_web" not in [s["tool_name"] for s in body["steps"]]
    assert web.queries == []


def test_web_search_is_off_in_experiments():
    from app.evaluation.config import ExperimentConfig, VariantConfig, variant_settings

    config = ExperimentConfig(
        name="x", dataset="d.yaml", variants=[VariantConfig(name="v", pipeline="agentic")]
    )
    assert variant_settings(get_settings(), config, config.variants[0]).agent_web_search is False


def test_tavily_request_and_response():
    seen = {}

    def handler(request):
        seen["auth"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "title": "A",
                        "url": "https://www.a.com/x",
                        "content": " text  here ",
                        "score": 0.9,
                    },
                    {"title": "No content", "url": "https://b.com", "content": ""},
                ]
            },
        )

    tavily = TavilySearch("tvly-secret", http=httpx.Client(transport=httpx.MockTransport(handler)))
    [result] = tavily.search("what is a patent", 5)
    assert seen["auth"] == "Bearer tvly-secret" and seen["body"]["search_depth"] == "basic"
    assert seen["body"]["include_answer"] is False  # we write and verify our own answer
    assert (result.site, result.content) == ("a.com", "text here")


def test_tavily_rejected_key_is_reported_without_the_key():
    tavily = TavilySearch(
        "tvly-secret",
        http=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(401))),
    )
    with pytest.raises(Exception) as err:
        tavily.search("q", 3)
    assert "TAVILY_API_KEY" in str(err.value) and "tvly-secret" not in str(err.value)


def test_wikipedia_uses_a_policy_compliant_user_agent():
    agents = []

    def handler(request):
        agents.append(request.headers["user-agent"])
        if request.url.params["action"] == "query" and "list" in request.url.params:
            return httpx.Response(200, json={"query": {"search": [{"title": "Patent"}]}})
        return httpx.Response(
            200,
            json={
                "query": {
                    "pages": {
                        "1": {
                            "title": "Patent",
                            "extract": "A patent is ...",
                            "fullurl": "https://en.wikipedia.org/wiki/Patent",
                        }
                    }
                }
            },
        )

    from app.web.search import USER_AGENT

    wiki = WikipediaSearch(
        http=httpx.Client(
            transport=httpx.MockTransport(handler), headers={"User-Agent": USER_AGENT}
        )
    )
    [page] = wiki.search("patent", 3)
    assert page.url.endswith("/Patent") and "github.com" in agents[0]


def test_tavily_keys_are_redacted_from_logs():
    assert "tvly-abcdef123456" not in redact("calling with key tvly-abcdef123456 now")


class OffTopicPlanner(FakeLLM):
    """The LLM planner calls the question out of scope; answers like FakeLLM."""

    def __init__(self):
        self.calls = 0

    def complete(self, messages, *, temperature, max_tokens):
        self.calls += 1
        if self.calls == 1:
            from app.llm.providers import LLMResponse

            return LLMResponse('{"intent": "out_of_scope"}', "planner", 10, 5, 1)
        return super().complete(messages, temperature=temperature, max_tokens=max_tokens)


@pytest.mark.db
def test_off_topic_question_goes_to_the_web_but_not_the_patent_offices(api, web):
    from app.patents.demo import DemoPatentSource

    app = api.app
    base = app.dependency_overrides[get_settings]()
    app.dependency_overrides[get_settings] = lambda: base.model_copy(
        update={"agent_planner": "llm"}
    )
    app.dependency_overrides[get_llm] = lambda: OffTopicPlanner()
    app.dependency_overrides[get_patent_sources] = lambda: {"demo": DemoPatentSource()}
    body = api.post("/ask", json={"question": "How do solid-state batteries work?"}).json()
    tools = [s["tool_name"] for s in body["steps"]]
    assert "search_web" in tools and "search_patent_abstracts" not in tools
