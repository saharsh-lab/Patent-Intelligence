"""Raw passage search — lets you see what retrieval finds before any LLM is involved.

Useful for debugging and demos. Phase 3 adds hybrid search and answer generation.
"""

from fastapi import APIRouter

from app.api.deps import EmbedderDep, SessionDep
from app.rag.vector_store import keyword_search, vector_search
from app.schemas.documents import SearchHit, SearchRequest

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/chunks", response_model=list[SearchHit])
def search_chunks(body: SearchRequest, session: SessionDep, embedder: EmbedderDep):
    if body.method == "vector":
        hits = vector_search(
            session,
            embedder.embed_query(body.query),
            top_k=body.top_k,
            document_ids=body.document_ids,
            embedding_model=embedder.name,
        )
    else:
        hits = keyword_search(session, body.query, top_k=body.top_k, document_ids=body.document_ids)
    return [SearchHit.from_chunk(hit.chunk, hit.score, hit.method) for hit in hits]
