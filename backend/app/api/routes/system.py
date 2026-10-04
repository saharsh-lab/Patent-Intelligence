"""Non-secret configuration for the UI's Settings page and run displays.

Only explicitly listed, harmless values are returned. Secrets (API keys, the
database URL) are never included.
"""

from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.deps import SessionDep, SettingsDep
from app.models import AgentRun, Chunk, Document
from app.rag.generation import PROMPT_VERSION

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/info")
def system_info(settings: SettingsDep, session: SessionDep) -> dict:
    return {
        "app_env": settings.app_env,
        "llm": {
            "provider": settings.llm_provider,
            "model": settings.llm_model if settings.llm_provider != "fake" else "fake-extractive",
            "temperature": settings.llm_temperature,
            "max_tokens": settings.llm_max_tokens,
            "reasoning_effort": settings.llm_reasoning_effort or None,
            "prompt_version": PROMPT_VERSION,
        },
        "embeddings": {
            "provider": settings.embedding_provider,
            "model": settings.embedding_model
            if settings.embedding_provider != "fake"
            else "fake-hash",
            "dimensions": settings.embedding_dim,
        },
        "retrieval": {
            "mode": settings.retrieval_mode,
            "top_k": settings.retrieval_top_k,
            "candidate_k": settings.retrieval_candidate_k,
            "min_similarity": settings.retrieval_min_similarity,
            "max_context_tokens": settings.max_context_tokens,
            "reranker_enabled": settings.reranker_enabled,
            "reranker_model": settings.reranker_model if settings.reranker_enabled else None,
        },
        "chunking": {
            "strategy": settings.chunking_strategy,
            "max_tokens": settings.chunk_max_tokens,
            "overlap_tokens": settings.chunk_overlap_tokens,
        },
        "uploads": {
            "max_upload_mb": settings.max_upload_mb,
            "allowed_extensions": list(settings.allowed_extensions),
        },
        "patent_sources": settings.enabled_patent_sources,
        "counts": {
            "documents": session.scalar(select(func.count()).select_from(Document)),
            "chunks": session.scalar(select(func.count()).select_from(Chunk)),
            "runs": session.scalar(select(func.count()).select_from(AgentRun)),
        },
    }
