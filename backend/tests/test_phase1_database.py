"""Phase 1: PostgreSQL + pgvector schema, constraints, and vector/keyword search."""

import hashlib
import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.models import (
    AgentRun,
    Chunk,
    Document,
    Patent,
    Query,
    RetrievalResult,
    ToolCall,
)
from app.rag.vector_store import keyword_search, vector_search

pytestmark = pytest.mark.db

DIM = get_settings().embedding_dim


def basis(*weights: tuple[int, float]) -> list[float]:
    """Build a test embedding: zeros except the given (position, value) pairs."""
    vec = [0.0] * DIM
    for position, value in weights:
        vec[position] = value
    return vec


def make_document(session, name: str = "sample.pdf") -> Document:
    doc = Document(
        filename=name,
        mime_type="application/pdf",
        size_bytes=1234,
        content_sha256=hashlib.sha256(name.encode()).hexdigest(),
        storage_path=f"/tmp/{name}",
    )
    session.add(doc)
    session.flush()
    return doc


@pytest.fixture
def corpus(db_session):
    """One uploaded document and one patent, each with chunks pointing in known directions."""
    doc = make_document(db_session)
    patent = Patent(source="epo", publication_number="EP1234567A1", title="Wireless charger")
    db_session.add(patent)
    db_session.flush()
    chunks = {
        "battery": Chunk(
            document=doc,
            chunk_index=0,
            section="abstract",
            page_number=1,
            text="A battery management system monitors cell temperature using sensors.",
            embedding=basis((0, 1.0)),
        ),
        "battery_claim": Chunk(
            document=doc,
            chunk_index=1,
            section="claims",
            page_number=4,
            text="1. A system comprising a temperature sensor coupled to a battery cell.",
            embedding=basis((0, 0.9), (1, 0.1)),
        ),
        "wireless": Chunk(
            patent=patent,
            chunk_index=0,
            section="abstract",
            text="An inductive coil transfers power wirelessly to a mobile device.",
            embedding=basis((2, 1.0)),
        ),
    }
    db_session.add_all(chunks.values())
    db_session.flush()
    return {"doc": doc, "patent": patent, **chunks}


# ---------------------------------------------------------------- schema


def test_all_tables_exist(db_engine):
    tables = set(inspect(db_engine).get_table_names())
    expected = {
        "documents",
        "patents",
        "chunks",
        "api_cache",
        "queries",
        "agent_runs",
        "tool_calls",
        "retrieval_results",
        "claim_verifications",
        "evaluations",
    }
    assert expected <= tables


def test_pgvector_extension_installed(db_session):
    version = db_session.execute(
        text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
    ).scalar_one()
    assert version


def test_models_match_migrations():
    """`alembic check` fails if someone changes a model without writing a migration."""
    here = os.path.dirname(__file__)
    cfg = Config(os.path.join(here, "..", "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(here, "..", "alembic"))
    cfg.attributes["database_url"] = get_settings().test_database_url
    cfg.attributes["configure_logger"] = False
    command.check(cfg)


# ---------------------------------------------------------------- search


def test_vector_search_orders_by_similarity(db_session, corpus):
    hits = vector_search(db_session, basis((0, 1.0)), top_k=3)
    assert [h.chunk.id for h in hits] == [
        corpus["battery"].id,
        corpus["battery_claim"].id,
        corpus["wireless"].id,
    ]
    assert hits[0].score == pytest.approx(1.0)  # identical direction
    assert hits[-1].score == pytest.approx(0.0)  # orthogonal = unrelated


def test_vector_search_can_be_scoped_to_a_patent(db_session, corpus):
    hits = vector_search(db_session, basis((0, 1.0)), patent_ids=[corpus["patent"].id])
    assert [h.chunk.id for h in hits] == [corpus["wireless"].id]


def test_vector_search_keeps_citation_metadata(db_session, corpus):
    top = vector_search(db_session, basis((0, 0.9), (1, 0.1)), top_k=1)[0].chunk
    assert (top.document.filename, top.page_number, top.section) == ("sample.pdf", 4, "claims")


def test_keyword_search_uses_stemming(db_session, corpus):
    # "sensors" in the query matches "sensor" / "sensors" in the text
    hits = keyword_search(db_session, "temperature sensors")
    assert {h.chunk.id for h in hits} == {corpus["battery"].id, corpus["battery_claim"].id}


def test_keyword_search_no_match_returns_empty(db_session, corpus):
    assert keyword_search(db_session, "photosynthesis") == []


def test_hnsw_index_is_usable(db_session, corpus):
    # With 3 rows PostgreSQL would normally just scan the table; disable that to prove
    # the HNSW index can serve the nearest-neighbour query.
    db_session.execute(text("SET LOCAL enable_seqscan = off"))
    vector_literal = "[" + ",".join(["1"] + ["0"] * (DIM - 1)) + "]"
    plan = db_session.execute(
        text(
            "EXPLAIN SELECT id FROM chunks "
            f"ORDER BY embedding <=> '{vector_literal}'::vector LIMIT 3"
        )
    ).scalars()
    assert "ix_chunks_embedding_hnsw" in "\n".join(plan)


# ---------------------------------------------------------------- constraints


def test_chunk_must_have_exactly_one_owner(db_session, corpus):
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(Chunk(chunk_index=99, text="orphan"))
        db_session.flush()
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(
            Chunk(document=corpus["doc"], patent=corpus["patent"], chunk_index=99, text="both")
        )
        db_session.flush()


def test_duplicate_upload_is_rejected(db_session):
    make_document(db_session, "same.pdf")
    with pytest.raises(IntegrityError), db_session.begin_nested():
        make_document(db_session, "same.pdf")


def test_invalid_document_status_is_rejected(db_session):
    doc = make_document(db_session)
    with pytest.raises(IntegrityError), db_session.begin_nested():
        doc.status = "banana"
        db_session.flush()


def test_deleting_document_deletes_its_chunks(db_session, corpus):
    doc_id = corpus["doc"].id
    db_session.delete(corpus["doc"])
    db_session.flush()
    remaining = db_session.scalars(select(Chunk).where(Chunk.document_id == doc_id)).all()
    assert remaining == []


# ---------------------------------------------------------------- run records


def test_agent_run_records_tools_and_evidence(db_session, corpus):
    query = Query(query_text="How does the patent measure battery temperature?")
    run = AgentRun(query=query, pipeline="agentic", config={"top_k": 5})
    run.tool_calls.append(
        ToolCall(step_index=0, tool_name="search_uploaded_documents", success=True)
    )
    run.retrieval_results.append(
        RetrievalResult(
            rank=1,
            source_type="upload",
            chunk_id=corpus["battery"].id,
            method="vector",
            score=0.93,
            retrieved_text=corpus["battery"].text,
        )
    )
    db_session.add(run)
    db_session.flush()
    db_session.expire_all()

    stored = db_session.get(AgentRun, run.id)
    assert stored.status == "running"
    assert stored.config == {"top_k": 5}
    assert [t.tool_name for t in stored.tool_calls] == ["search_uploaded_documents"]
    assert stored.retrieval_results[0].chunk_id == corpus["battery"].id


def test_run_history_survives_document_deletion(db_session, corpus):
    run = AgentRun(query=Query(query_text="q"), pipeline="baseline_rag")
    result = RetrievalResult(
        rank=1,
        source_type="upload",
        chunk_id=corpus["battery"].id,
        method="vector",
        retrieved_text=corpus["battery"].text,
    )
    run.retrieval_results.append(result)
    db_session.add(run)
    db_session.flush()

    original_text = corpus["battery"].text
    db_session.delete(corpus["doc"])
    db_session.flush()
    db_session.expire_all()

    kept = db_session.get(RetrievalResult, result.id)
    assert kept.chunk_id is None
    assert kept.retrieved_text == original_text


def test_scoped_vector_search_finds_small_document_in_big_corpus(db_session):
    """Scoped search must find a small document's passage even when 300 other passages are
    globally nearer to the query (guards against filter-after-HNSW returning nothing)."""
    big, small = make_document(db_session, "big.pdf"), make_document(db_session, "small.pdf")
    db_session.add_all(
        Chunk(
            document=big, chunk_index=i, text=f"big {i}", embedding=basis((0, 1.0), (1 + i, 0.01))
        )
        for i in range(300)
    )
    db_session.add(Chunk(document=small, chunk_index=0, text="small", embedding=basis((900, 1.0))))
    db_session.flush()
    db_session.execute(text("SET LOCAL enable_seqscan = off"))  # force the HNSW index path
    hits = vector_search(db_session, basis((0, 1.0)), top_k=3, document_ids=[small.id])
    assert [h.chunk.text for h in hits] == ["small"]
