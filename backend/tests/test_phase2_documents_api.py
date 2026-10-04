"""Phase 2 (with database): upload -> ingest -> store -> list -> search -> delete via the API."""

import hashlib
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.errors import ExternalServiceError
from app.database.session import get_db
from app.main import create_app
from app.models import Chunk, Document
from app.rag.embeddings import FakeEmbedder, get_embedder
from tests.helpers import fixture_bytes, make_docx, make_pdf

pytestmark = pytest.mark.db

BATTERY = fixture_bytes("battery_patent.txt")
WIRELESS = fixture_bytes("wireless_patent.txt")


class FailingEmbedder(FakeEmbedder):
    def embed_documents(self, texts):
        raise ExternalServiceError("The embedding service is unavailable. Please try again.")


@pytest.fixture
def test_settings(tmp_path):
    return get_settings().model_copy(update={"upload_dir": tmp_path, "max_upload_mb": 1})


@pytest.fixture
def api(db_session, test_settings):
    """API client wired to the rolled-back test session, a temp upload dir, fake embeddings."""
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_embedder] = lambda: FakeEmbedder(test_settings.embedding_dim)
    with TestClient(app) as client:
        client.app_ref = app
        yield client


def upload(api, filename, data):
    return api.post("/documents", files={"file": (filename, data)})


# ------------------------------------------------------------------ upload


def test_upload_txt_creates_ready_document_with_sections(api, db_session, test_settings):
    response = upload(api, "battery.txt", BATTERY)
    assert response.status_code == 201, response.text
    body = response.json()
    doc = body["document"]
    assert body["duplicate"] is False
    assert doc["status"] == "ready"
    assert doc["title"].startswith("Battery Thermal Management System")
    assert doc["section_detection"] == "headings"
    assert "claims" in doc["sections_found"]
    assert doc["chunk_count"] > 5

    stored = db_session.get(Document, uuid.UUID(doc["id"]))
    assert stored.meta["embedding_model"].startswith("fake-hash")
    sha = hashlib.sha256(BATTERY).hexdigest()
    assert (test_settings.upload_dir / f"{sha}.txt").read_bytes() == BATTERY
    assert all(chunk.embedding is not None for chunk in stored.chunks)


def test_upload_pdf_keeps_page_numbers(api):
    pdf = make_pdf(
        [
            ["ABSTRACT", "A thermal model estimates the core temperature of each cell."],
            ["CLAIMS", "1. A system comprising a thermistor bonded to each cell."],
        ]
    )
    doc = upload(api, "patent.pdf", pdf).json()["document"]
    assert doc["page_count"] == 2
    chunks = api.get(f"/documents/{doc['id']}/chunks").json()
    pages = {c["section"]: c["page_number"] for c in chunks}
    assert pages == {"abstract": 1, "claims": 2}


def test_upload_docx(api):
    data = make_docx(["ABSTRACT", "An inverter drives the transmitter coil at 140 kHz."])
    response = upload(api, "coil.docx", data)
    assert response.status_code == 201
    assert response.json()["document"]["sections_found"] == ["abstract"]


def test_duplicate_upload_returns_existing_document(api, db_session):
    first = upload(api, "battery.txt", BATTERY).json()["document"]
    second = upload(api, "renamed-copy.txt", BATTERY)
    assert second.status_code == 200
    assert second.json() == {"document": first, "duplicate": True}
    assert db_session.scalar(select(func.count()).select_from(Document)) == 1


# ------------------------------------------------------------------ upload errors


@pytest.mark.parametrize(
    ("filename", "data", "status", "code"),
    [
        ("malware.exe", b"MZ\x90\x00binary", 415, "unsupported_file_type"),
        ("fake.pdf", b"I am not a PDF at all", 422, "invalid_document"),
        ("empty.txt", b"", 422, "empty_document"),
        ("blank.txt", b"   \n  ", 422, "empty_document"),
    ],
)
def test_invalid_uploads_are_rejected_without_storing(
    api, db_session, test_settings, filename, data, status, code
):
    response = upload(api, filename, data)
    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert db_session.scalar(select(func.count()).select_from(Document)) == 0
    assert list(test_settings.upload_dir.iterdir()) == []


def test_file_over_size_limit_is_rejected(api):
    response = upload(api, "big.txt", b"patent text " * 100_000)  # ~1.2 MB > 1 MB limit
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "file_too_large"


def test_scanned_pdf_is_recorded_as_failed_with_reason(api):
    import pymupdf

    doc = pymupdf.open()
    doc.new_page()
    response = upload(api, "scan.pdf", doc.tobytes())
    assert response.status_code == 422
    assert "OCR" in response.json()["error"]["message"]
    listed = api.get("/documents").json()
    assert listed[0]["status"] == "failed"
    assert "OCR" in listed[0]["error_message"]


def test_embedding_failure_marks_document_failed_and_retry_succeeds(api, test_settings):
    api.app_ref.dependency_overrides[get_embedder] = lambda: FailingEmbedder(
        test_settings.embedding_dim
    )
    response = upload(api, "battery.txt", BATTERY)
    assert response.status_code == 502
    assert api.get("/documents").json()[0]["status"] == "failed"

    api.app_ref.dependency_overrides[get_embedder] = lambda: FakeEmbedder(
        test_settings.embedding_dim
    )
    retry = upload(api, "battery.txt", BATTERY)
    assert retry.status_code == 201
    assert [d["status"] for d in api.get("/documents").json()] == ["ready"]


# ------------------------------------------------------------------ read / search / delete


def test_list_and_get_documents(api):
    upload(api, "battery.txt", BATTERY)
    upload(api, "wireless.txt", WIRELESS)
    listed = api.get("/documents").json()
    assert {d["filename"] for d in listed} == {"battery.txt", "wireless.txt"}
    assert all(d["chunk_count"] > 0 for d in listed)
    one = api.get(f"/documents/{listed[0]['id']}").json()
    assert one["id"] == listed[0]["id"]


def test_chunks_can_be_filtered_by_section(api):
    doc = upload(api, "battery.txt", BATTERY).json()["document"]
    claims = api.get(f"/documents/{doc['id']}/chunks", params={"section": "claims"}).json()
    assert [c["meta"]["claim_number"] for c in claims] == [1, 2, 3, 4, 5]
    assert "embedding" not in claims[0]  # vectors are never sent to the browser


def test_vector_search_finds_relevant_passage(api):
    battery = upload(api, "battery.txt", BATTERY).json()["document"]
    upload(api, "wireless.txt", WIRELESS)
    hits = api.post(
        "/search/chunks", json={"query": "coolant pump speed core temperature", "top_k": 3}
    ).json()
    assert hits[0]["document_id"] == battery["id"]
    assert hits[0]["source_label"] == "battery.txt"
    assert hits[0]["score"] >= hits[-1]["score"]


def test_keyword_search_and_document_scoping(api):
    upload(api, "battery.txt", BATTERY)
    wireless = upload(api, "wireless.txt", WIRELESS).json()["document"]
    hits = api.post("/search/chunks", json={"query": "thermistor", "method": "keyword"}).json()
    assert hits and all(h["source_label"] == "battery.txt" for h in hits)

    scoped = api.post(
        "/search/chunks",
        json={"query": "temperature", "document_ids": [wireless["id"]], "top_k": 10},
    ).json()
    assert all(h["document_id"] == wireless["id"] for h in scoped)


def test_search_validates_input(api):
    assert api.post("/search/chunks", json={"query": ""}).status_code == 422
    assert api.post("/search/chunks", json={"query": "x", "top_k": 500}).status_code == 422


def test_delete_removes_document_chunks_and_file(api, db_session, test_settings):
    doc = upload(api, "battery.txt", BATTERY).json()["document"]
    assert api.delete(f"/documents/{doc['id']}").status_code == 204
    assert api.get(f"/documents/{doc['id']}").status_code == 404
    assert db_session.scalar(select(func.count()).select_from(Chunk)) == 0
    assert list(test_settings.upload_dir.iterdir()) == []


def test_unknown_and_malformed_ids(api):
    assert api.get(f"/documents/{uuid.uuid4()}").json()["error"]["code"] == "not_found"
    assert api.get("/documents/not-a-uuid").status_code == 422


def test_reupload_with_new_embedding_model_reembeds(api, test_settings):
    first = upload(api, "battery.txt", BATTERY).json()["document"]

    other_model = FakeEmbedder(test_settings.embedding_dim)
    other_model.name = "other-model"
    api.app_ref.dependency_overrides[get_embedder] = lambda: other_model
    second = upload(api, "battery.txt", BATTERY)
    assert second.status_code == 201
    assert second.json()["document"]["id"] != first["id"]


def test_vector_search_ignores_chunks_from_other_embedding_models(api, db_session):
    upload(api, "battery.txt", BATTERY)
    db_session.query(Chunk).update({Chunk.embedding_model: "some-older-model"})
    db_session.flush()
    assert api.post("/search/chunks", json={"query": "coolant"}).json() == []
