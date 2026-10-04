"""Document endpoints: upload, list, inspect chunks, delete."""

import uuid
from typing import Annotated

from fastapi import APIRouter, File, Query, Request, Response, UploadFile, status

from app.api.deps import DocumentServiceDep, SettingsDep
from app.core.errors import FileTooLargeError
from app.schemas.documents import ChunkOut, DocumentOut, UploadResponse

router = APIRouter(prefix="/documents", tags=["documents"])

# Multipart encoding adds some bytes around the file itself
_MULTIPART_OVERHEAD = 64 * 1024


@router.post("", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
def upload_document(
    request: Request,
    response: Response,
    service: DocumentServiceDep,
    settings: SettingsDep,
    file: Annotated[UploadFile, File(description="PDF, DOCX or TXT, up to MAX_UPLOAD_MB")],
) -> UploadResponse:
    limit = settings.max_upload_bytes
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > limit + _MULTIPART_OVERHEAD:
        raise FileTooLargeError(f"File exceeds the {settings.max_upload_mb} MB limit.")
    data = file.file.read(limit + 1)  # read at most one byte past the limit

    document, created = service.upload(file.filename, data)
    if not created:
        response.status_code = status.HTTP_200_OK
    return UploadResponse(document=DocumentOut.from_model(document), duplicate=not created)


@router.get("", response_model=list[DocumentOut])
def list_documents(service: DocumentServiceDep) -> list[DocumentOut]:
    return [DocumentOut.from_model(doc, count) for doc, count in service.list_documents()]


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: uuid.UUID, service: DocumentServiceDep) -> DocumentOut:
    return DocumentOut.from_model(service.get(document_id))


@router.get("/{document_id}/chunks", response_model=list[ChunkOut])
def list_chunks(
    document_id: uuid.UUID,
    service: DocumentServiceDep,
    section: str | None = Query(default=None, max_length=32),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[ChunkOut]:
    chunks = service.chunks(document_id, section=section, limit=limit, offset=offset)
    return [ChunkOut.model_validate(chunk) for chunk in chunks]


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: uuid.UUID, service: DocumentServiceDep) -> None:
    service.delete(document_id)
