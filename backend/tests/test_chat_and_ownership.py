"""Chat conversations with memory, and per-user data isolation."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.deps import get_patent_sources
from app.auth.config import get_auth_settings
from app.auth.db import get_auth_db
from app.core.config import get_settings
from app.database.session import get_db
from app.llm.providers import FakeLLM, LLMResponse, get_llm
from app.main import create_app
from app.rag.embeddings import FakeEmbedder, get_embedder
from app.services.chat import ChatService, _accept_rewrite
from tests.helpers import fixture_bytes

pytestmark = pytest.mark.db
PASSWORD = "correct-horse-7"


# ------------------------------------------------------------------ rewrite guard (no DB)


@pytest.mark.parametrize(
    ("reply", "expected"),
    [
        ("What does claim 2 of US9178361B2 add?", "What does claim 2 of US9178361B2 add?"),
        ('Standalone question: "How is the pump controlled?"', "How is the pump controlled?"),
        ("<think>hmm</think>What is claim 3?", "What is claim 3?"),
        ("", "what about claim 2?"),  # empty → keep the user's words
        ("A" * 400, "what about claim 2?"),  # rambling → keep
        ("Claim 2 adds X.\n\nIt also adds Y.", "what about claim 2?"),  # an answer → keep
    ],
)
def test_rewrite_guard(reply, expected):
    assert _accept_rewrite("what about claim 2?", reply) == expected


# ------------------------------------------------------------------ fixtures


@pytest.fixture(scope="module")
def auth_engine():
    from scripts.migrate_auth import migrate

    url = get_auth_settings().auth_test_database_url
    migrate(url)
    engine = create_engine(url)
    yield engine
    engine.dispose()


@pytest.fixture
def auth_db(auth_engine) -> Iterator[Session]:
    connection = auth_engine.connect()
    outer = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    yield session
    session.close()
    outer.rollback()
    connection.close()


@pytest.fixture
def app_factory(db_session, auth_db, tmp_path, monkeypatch):
    """Builds clients; with accounts switched on when `accounts=True`."""

    def make(accounts: bool, llm=None):
        monkeypatch.setenv("AUTH_REQUIRED", "true" if accounts else "false")
        get_auth_settings.cache_clear()
        settings = get_settings().model_copy(
            update={
                "upload_dir": tmp_path,
                "retrieval_min_similarity": 0.1,
                "agent_planner": "rules",
            }
        )
        app = create_app()
        app.dependency_overrides[get_db] = lambda: db_session
        app.dependency_overrides[get_auth_db] = lambda: auth_db
        app.dependency_overrides[get_settings] = lambda: settings
        app.dependency_overrides[get_embedder] = lambda: FakeEmbedder(settings.embedding_dim)
        app.dependency_overrides[get_llm] = lambda: llm or FakeLLM()
        app.dependency_overrides[get_patent_sources] = lambda: {}
        return app

    yield make
    get_auth_settings.cache_clear()


def user(app, email):
    client = TestClient(app)
    response = client.post(
        "/auth/register", json={"email": email, "name": email.split("@")[0], "password": PASSWORD}
    )
    assert response.status_code == 201, response.text
    return client


# ------------------------------------------------------------------ chat


def test_conversation_lifecycle_with_attached_document(app_factory):
    api = TestClient(app_factory(accounts=False))
    conversation = api.post("/conversations", json={}).json()
    assert conversation["title"] == "New chat" and conversation["messages"] == []
    cid = conversation["id"]

    attached = api.post(
        f"/conversations/{cid}/documents",
        files={"file": ("battery.txt", fixture_bytes("battery_patent.txt"))},
    )
    assert attached.status_code == 201
    detail = api.get(f"/conversations/{cid}").json()
    assert [d["filename"] for d in detail["documents"]] == ["battery.txt"]
    assert detail["title"] != "New chat"  # named after the first document

    sent = api.post(
        f"/conversations/{cid}/messages", json={"message": "How is the coolant pump controlled?"}
    )
    assert sent.status_code == 200, sent.text
    message = sent.json()
    assert message["user_message"] == "How is the coolant pump controlled?"
    assert message["response"]["status"] == "succeeded"
    # answers are scoped to the attached document
    assert {e["source_label"] for e in message["response"]["evidence"]} == {"battery.txt"}

    listed = api.get("/conversations").json()
    assert listed[0]["id"] == cid and listed[0]["message_count"] == 1

    assert (
        api.patch(f"/conversations/{cid}", json={"title": "Battery cooling"}).json()["title"]
        == "Battery cooling"
    )
    doc_id = detail["documents"][0]["id"]
    assert api.delete(f"/conversations/{cid}/documents/{doc_id}").status_code == 204
    assert api.get(f"/conversations/{cid}").json()["documents"] == []
    assert api.get(f"/documents/{doc_id}").status_code == 200  # detaching keeps the document

    assert api.delete(f"/conversations/{cid}").status_code == 204
    assert api.get(f"/conversations/{cid}").status_code == 404


def test_follow_up_is_rewritten_with_memory(db_session, tmp_path):
    class Scripted(FakeLLM):
        """Answers like FakeLLM; returns a fixed rewrite when asked to rewrite."""

        def complete(self, messages, *, temperature, max_tokens):
            if "standalone question" in messages[0].content:
                assert "coolant pump" in messages[1].content  # the history is given
                return LLMResponse("What does claim 3 of the battery patent add?", "s", 10, 10, 1)
            return super().complete(messages, temperature=temperature, max_tokens=max_tokens)

    settings = get_settings().model_copy(
        update={
            "upload_dir": tmp_path,
            "llm_provider": "openai_compatible",
            "agent_planner": "rules",
            "retrieval_min_similarity": 0.1,
        }
    )
    service = ChatService(
        db_session, settings, FakeEmbedder(settings.embedding_dim), Scripted(), {}, owner_id=None
    )
    conversation = service.create()
    service.attach_upload(conversation.id, "battery.txt", fixture_bytes("battery_patent.txt"))
    service.send(conversation.id, "How is the coolant pump controlled?")  # no history: unchanged
    run = service.send(conversation.id, "and what does claim 3 add?")
    assert run.query.query_text == "What does claim 3 of the battery patent add?"
    assert run.query.meta["user_message"] == "and what does claim 3 add?"
    assert run.query.meta["interpreted_as"] == "What does claim 3 of the battery patent add?"


# ------------------------------------------------------------------ data isolation


def test_users_cannot_see_each_others_data(app_factory):
    app = app_factory(accounts=True)
    alice, bob = user(app, "alice@example.com"), user(app, "bob@example.com")

    doc = alice.post(
        "/documents", files={"file": ("battery.txt", fixture_bytes("battery_patent.txt"))}
    ).json()
    doc_id = doc["document"]["id"]
    chat_a = alice.post("/conversations", json={"title": "Alice's chat"}).json()["id"]
    alice.post(
        f"/conversations/{chat_a}/messages", json={"message": "How is the coolant pump controlled?"}
    )

    # Bob sees none of it ...
    assert bob.get("/documents").json() == []
    assert bob.get(f"/documents/{doc_id}").status_code == 404
    assert bob.get("/conversations").json() == []
    assert bob.get(f"/conversations/{chat_a}").status_code == 404
    assert (
        bob.post(f"/conversations/{chat_a}/messages", json={"message": "hi there"}).status_code
        == 404
    )
    assert bob.get("/runs").json() == []
    # ... not even through search or questions
    hits = bob.post("/search/chunks", json={"query": "coolant pump", "method": "keyword"}).json()
    assert hits == []
    answer = bob.post("/ask", json={"question": "How is the coolant pump controlled?"}).json()
    assert answer["status"] == "insufficient_evidence" and answer["evidence"] == []
    scoped = bob.post("/ask", json={"question": "Pump?", "document_ids": [doc_id]}).json()
    assert scoped["evidence"] == []  # naming Alice's document id does not help

    # Alice still sees her own
    assert [d["id"] for d in alice.get("/documents").json()] == [doc_id]
    assert alice.get("/runs").json()


def test_same_file_uploaded_by_two_users_gives_separate_copies(app_factory):
    app = app_factory(accounts=True)
    alice, bob = user(app, "alice@example.com"), user(app, "bob@example.com")
    a = alice.post(
        "/documents", files={"file": ("b.txt", fixture_bytes("battery_patent.txt"))}
    ).json()
    b = bob.post(
        "/documents", files={"file": ("b.txt", fixture_bytes("battery_patent.txt"))}
    ).json()
    assert b["duplicate"] is False and a["document"]["id"] != b["document"]["id"]
    again = bob.post(
        "/documents", files={"file": ("b.txt", fixture_bytes("battery_patent.txt"))}
    ).json()
    assert again["duplicate"] is True and again["document"]["id"] == b["document"]["id"]

    assert alice.delete(f"/documents/{a['document']['id']}").status_code == 204
    # Bob's copy (same stored file) still works
    chunks = bob.get(f"/documents/{b['document']['id']}/chunks").json()
    assert chunks


def test_first_account_adopts_data_created_before_accounts(app_factory):
    legacy = TestClient(app_factory(accounts=False))  # single-user mode: no owner
    doc_id = legacy.post(
        "/documents", files={"file": ("b.txt", fixture_bytes("battery_patent.txt"))}
    ).json()["document"]["id"]

    app = app_factory(accounts=True)
    first, second = user(app, "first@example.com"), user(app, "second@example.com")
    assert [d["id"] for d in first.get("/documents").json()] == [doc_id]
    assert second.get("/documents").json() == []


def test_attach_library_document_and_imported_patent(app_factory, db_session):
    from app.models import Patent

    api = TestClient(app_factory(accounts=False))
    doc_id = api.post(
        "/documents", files={"file": ("b.txt", fixture_bytes("battery_patent.txt"))}
    ).json()["document"]["id"]
    patent = Patent(source="demo", publication_number="XX0000001A1", title="Cooling plate")
    db_session.add(patent)
    db_session.commit()

    cid = api.post("/conversations", json={}).json()["id"]
    attached = api.post(f"/conversations/{cid}/sources", json={"document_id": doc_id})
    assert attached.status_code == 200 and attached.json()["documents"][0]["kind"] == "document"
    both = api.post(f"/conversations/{cid}/sources", json={"patent_id": str(patent.id)}).json()
    assert [d["kind"] for d in both["documents"]] == ["document", "patent"]
    assert both["documents"][1]["filename"] == "XX0000001A1"
    assert api.delete(f"/conversations/{cid}/documents/{patent.id}").status_code == 204
    assert [d["kind"] for d in api.get(f"/conversations/{cid}").json()["documents"]] == ["document"]
    missing = api.post(f"/conversations/{cid}/sources", json={"document_id": str(patent.id)})
    assert missing.status_code == 404
