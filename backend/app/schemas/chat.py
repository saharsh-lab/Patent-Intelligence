"""API shapes for chat conversations."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models import AgentRun, Document, Patent
from app.models.conversation import Conversation
from app.schemas.answers import AskResponse


class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, max_length=200)


class ConversationRename(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class MessageIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class ConversationDocument(BaseModel):
    """An attached source: an uploaded document, or an imported patent."""

    id: uuid.UUID
    kind: str = "document"  # document | patent
    filename: str  # file name, or publication number for patents
    title: str | None
    status: str

    @classmethod
    def of(cls, d: Document) -> "ConversationDocument":
        return cls(id=d.id, filename=d.filename, title=d.title, status=d.status)

    @classmethod
    def of_patent(cls, p: Patent) -> "ConversationDocument":
        return cls(
            id=p.id, kind="patent", filename=p.publication_number, title=p.title, status="ready"
        )


class AttachSource(BaseModel):
    document_id: uuid.UUID | None = None
    patent_id: uuid.UUID | None = None


class ConversationSummary(BaseModel):
    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int
    documents: list[ConversationDocument]

    @classmethod
    def of(
        cls,
        c: Conversation,
        documents: list[Document],
        message_count: int,
        patents: list[Patent] = (),
    ) -> "ConversationSummary":
        return cls(
            id=c.id,
            title=c.title,
            created_at=c.created_at,
            updated_at=c.updated_at,
            message_count=message_count,
            documents=[ConversationDocument.of(d) for d in documents]
            + [ConversationDocument.of_patent(p) for p in patents],
        )


class ChatMessageOut(BaseModel):
    run_id: uuid.UUID
    user_message: str
    interpreted_as: str | None = Field(
        description="The standalone question answered, when memory rewrote a follow-up"
    )
    created_at: datetime
    response: AskResponse

    @classmethod
    def of(cls, run: AgentRun) -> "ChatMessageOut":
        meta = run.query.meta or {}
        return cls(
            run_id=run.id,
            user_message=meta.get("user_message") or run.query.query_text,
            interpreted_as=meta.get("interpreted_as"),
            created_at=run.started_at,
            response=AskResponse.from_run(run),
        )


class ConversationDetail(ConversationSummary):
    messages: list[ChatMessageOut]
