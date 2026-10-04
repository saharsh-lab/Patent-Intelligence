"""Shared FastAPI dependencies. Tests override these to inject fakes."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.auth.deps import CurrentUser
from app.core.config import Settings, get_settings
from app.core.ownership import current_owner
from app.database.session import get_db
from app.invention.analysis import InventionAnalyzer
from app.llm.providers import LLMProvider, get_llm
from app.patents.base import PatentSource
from app.patents.registry import get_patent_sources_for
from app.rag.embeddings import EmbeddingProvider, get_embedder
from app.services.agent import AgentService
from app.services.answering import AnswerService
from app.services.chat import ChatService
from app.services.comparison import ComparisonService
from app.services.documents import DocumentService
from app.services.patents import PatentService
from app.services.watches import WatchService

SessionDep = Annotated[Session, Depends(get_db)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
EmbedderDep = Annotated[EmbeddingProvider, Depends(get_embedder)]


def get_document_service(
    session: SessionDep, settings: SettingsDep, embedder: EmbedderDep
) -> DocumentService:
    return DocumentService(session, settings, embedder)


DocumentServiceDep = Annotated[DocumentService, Depends(get_document_service)]


LLMDep = Annotated[LLMProvider, Depends(get_llm)]


def get_answer_service(
    session: SessionDep, settings: SettingsDep, embedder: EmbedderDep, llm: LLMDep
) -> AnswerService:
    return AnswerService(session, settings, embedder, llm)


AnswerServiceDep = Annotated[AnswerService, Depends(get_answer_service)]


def get_patent_sources(settings: SettingsDep) -> dict[str, PatentSource]:
    return get_patent_sources_for(settings)


def get_patent_service(
    session: SessionDep,
    settings: SettingsDep,
    embedder: EmbedderDep,
    sources: Annotated[dict[str, PatentSource], Depends(get_patent_sources)],
) -> PatentService:
    return PatentService(session, settings, embedder, sources)


PatentServiceDep = Annotated[PatentService, Depends(get_patent_service)]


def get_agent_service(
    session: SessionDep,
    settings: SettingsDep,
    embedder: EmbedderDep,
    llm: LLMDep,
    sources: Annotated[dict[str, PatentSource], Depends(get_patent_sources)],
) -> AgentService:
    return AgentService(session, settings, embedder, llm, sources)


AgentServiceDep = Annotated[AgentService, Depends(get_agent_service)]


def get_comparison_service(
    session: SessionDep,
    settings: SettingsDep,
    embedder: EmbedderDep,
    llm: LLMDep,
    sources: Annotated[dict[str, PatentSource], Depends(get_patent_sources)],
) -> ComparisonService:
    return ComparisonService(session, settings, embedder, llm, sources)


ComparisonServiceDep = Annotated[ComparisonService, Depends(get_comparison_service)]


def get_invention_analyzer(
    session: SessionDep,
    settings: SettingsDep,
    embedder: EmbedderDep,
    llm: LLMDep,
    sources: Annotated[dict[str, PatentSource], Depends(get_patent_sources)],
) -> InventionAnalyzer:
    return InventionAnalyzer(session, settings, embedder, llm, sources)


InventionAnalyzerDep = Annotated[InventionAnalyzer, Depends(get_invention_analyzer)]


def get_watch_service(
    session: SessionDep,
    settings: SettingsDep,
    embedder: EmbedderDep,
    sources: Annotated[dict[str, PatentSource], Depends(get_patent_sources)],
) -> WatchService:
    return WatchService(session, settings, embedder, sources)


WatchServiceDep = Annotated[WatchService, Depends(get_watch_service)]


def get_chat_service(
    session: SessionDep,
    settings: SettingsDep,
    embedder: EmbedderDep,
    llm: LLMDep,
    sources: Annotated[dict[str, PatentSource], Depends(get_patent_sources)],
    user: CurrentUser,
) -> ChatService:
    preferences = (user.preferences or {}) if user else {}
    pipeline = preferences.get("default_pipeline") or "agentic"
    checks = {"strict": "nli_lexical", "balanced": "nli_llm"}.get(preferences.get("verification"))
    if checks and settings.verifier_method in ("auto", "nli_llm", "nli_lexical"):
        settings = settings.model_copy(update={"verifier_method": checks})
    return ChatService(
        session, settings, embedder, llm, sources, owner_id=current_owner(), pipeline=pipeline
    )


ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]
