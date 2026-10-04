"""Chat conversations: create, list, rename, delete; send messages; attach documents."""

import uuid
from typing import Annotated

from fastapi import APIRouter, File, Response, UploadFile, status
from sqlalchemy import func, select

from app.api.deps import ChatServiceDep, SettingsDep
from app.core.errors import FileTooLargeError
from app.models import Query
from app.schemas.chat import (
    AttachSource,
    ChatMessageOut,
    ConversationCreate,
    ConversationDetail,
    ConversationRename,
    ConversationSummary,
    MessageIn,
)
from app.schemas.documents import DocumentOut, UploadResponse

router = APIRouter(prefix="/conversations", tags=["chat"])


def _summary(service, conversation) -> ConversationSummary:
    count = service.session.scalar(
        select(func.count(Query.id)).where(Query.conversation_id == conversation.id)
    )
    return ConversationSummary.of(
        conversation, service.documents(conversation), count or 0, service.patents(conversation)
    )


@router.get("", response_model=list[ConversationSummary])
def list_conversations(service: ChatServiceDep):
    return [_summary(service, c) for c in service.list_conversations()]


@router.post("", response_model=ConversationDetail, status_code=status.HTTP_201_CREATED)
def create_conversation(body: ConversationCreate, service: ChatServiceDep):
    conversation = service.create(body.title)
    return ConversationDetail(**_summary(service, conversation).model_dump(), messages=[])


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: uuid.UUID, service: ChatServiceDep):
    conversation = service.get(conversation_id)
    return ConversationDetail(
        **_summary(service, conversation).model_dump(),
        messages=[ChatMessageOut.of(run) for run in service.messages(conversation)],
    )


@router.patch("/{conversation_id}", response_model=ConversationSummary)
def rename_conversation(
    conversation_id: uuid.UUID, body: ConversationRename, service: ChatServiceDep
):
    return _summary(service, service.rename(conversation_id, body.title))


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(conversation_id: uuid.UUID, service: ChatServiceDep):
    service.delete(conversation_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{conversation_id}/messages", response_model=ChatMessageOut)
def send_message(conversation_id: uuid.UUID, body: MessageIn, service: ChatServiceDep):
    """Answers with the user's preferred pipeline; follow-ups are rewritten using the
    conversation (memory) and answers are scoped to the attached documents."""
    return ChatMessageOut.of(
        service.send(conversation_id, body.message, live_search=body.live_search)
    )


@router.post(
    "/{conversation_id}/documents",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
)
def attach_document(
    conversation_id: uuid.UUID,
    file: Annotated[UploadFile, File(description="PDF, DOCX or TXT")],
    service: ChatServiceDep,
    settings: SettingsDep,
    response: Response,
):
    limit = settings.max_upload_bytes
    data = file.file.read(limit + 1)
    if len(data) > limit:
        raise FileTooLargeError(f"File exceeds the {settings.max_upload_mb} MB limit.")
    document, created = service.attach_upload(conversation_id, file.filename, data)
    if not created:
        response.status_code = status.HTTP_200_OK
    return UploadResponse(document=DocumentOut.from_model(document), duplicate=not created)


@router.post("/{conversation_id}/sources", response_model=ConversationSummary)
def attach_source(conversation_id: uuid.UUID, body: AttachSource, service: ChatServiceDep):
    """Attach a document from your library or an imported patent (no upload)."""
    conversation = service.attach_existing(
        conversation_id, document_id=body.document_id, patent_id=body.patent_id
    )
    return _summary(service, conversation)


@router.delete("/{conversation_id}/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def detach_document(conversation_id: uuid.UUID, document_id: uuid.UUID, service: ChatServiceDep):
    service.detach(conversation_id, document_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
