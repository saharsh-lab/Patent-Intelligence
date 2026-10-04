"""Document use-cases: upload + ingest, list, inspect, delete.

Upload flow:
  1. validate (extension, real file type, size, not empty)
  2. SHA-256 the bytes; if the same file was already ingested, return it (no re-embedding)
  3. save the file under a server-generated name (never the user's filename)
  4. record the document as 'processing'
  5. run the ingestion pipeline and embed the chunks in batches
  6. store chunks; mark 'ready' — or 'failed' with a readable reason

Processing happens inside the upload request. That is fine at student scale;
a background job queue would be the next step for very large files.
"""

import hashlib
import logging
import re
import time
import unicodedata
import uuid
from pathlib import Path, PurePath

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import (
    AppError,
    EmptyDocumentError,
    FileTooLargeError,
    NotFoundError,
    UnsupportedFileError,
)
from app.core.ownership import current_owner, restrict, visible
from app.models import Chunk, Document
from app.rag.embeddings import EmbeddingProvider
from app.rag.extraction import MIME_TYPES, detect_file_kind
from app.rag.ingestion import process_document

logger = logging.getLogger(__name__)


def sanitize_filename(filename: str | None) -> str:
    """Keep a display-safe base name: no directories, control characters, or huge names."""
    name = PurePath((filename or "").replace("\\", "/")).name
    name = "".join(ch for ch in name if unicodedata.category(ch)[0] != "C").strip()
    name = re.sub(r"\s+", " ", name)
    if len(name) > 255:
        stem, suffix = PurePath(name).stem, PurePath(name).suffix
        name = stem[: 255 - len(suffix)] + suffix
    return name or "untitled"


class DocumentService:
    def __init__(self, session: Session, settings: Settings, embedder: EmbeddingProvider):
        self.session = session
        self.settings = settings
        self.embedder = embedder

    # ------------------------------------------------------------------ upload

    def upload(self, filename: str | None, data: bytes) -> tuple[Document, bool]:
        """Ingest a file. Returns (document, created); created=False for duplicates."""
        name = sanitize_filename(filename)
        extension = PurePath(name).suffix.lower()
        if extension not in self.settings.allowed_extensions:
            allowed = ", ".join(self.settings.allowed_extensions)
            raise UnsupportedFileError(f"Unsupported file type '{extension}'. Allowed: {allowed}.")
        if len(data) > self.settings.max_upload_bytes:
            raise FileTooLargeError(f"File exceeds the {self.settings.max_upload_mb} MB limit.")
        if not data.strip():
            raise EmptyDocumentError("The uploaded file is empty.")
        kind = detect_file_kind(name, data)  # rejects e.g. a renamed .exe before we store it

        sha256 = hashlib.sha256(data).hexdigest()
        owner = current_owner()
        existing = self.session.scalar(
            select(Document).where(
                Document.content_sha256 == sha256,
                Document.owner_id.is_(None) if owner is None else Document.owner_id == owner,
            )
        )
        if existing is not None:
            same_model = existing.meta.get("embedding_model") == self.embedder.name
            if existing.status == "ready" and same_model:
                logger.info("Duplicate upload of document %s", existing.id)
                return existing, False
            # Earlier attempt failed, or it was embedded by another model: redo from scratch
            self.delete(existing.id)

        storage_path = self._store_file(sha256, extension, data)
        document = Document(
            owner_id=owner,
            filename=name,
            title=PurePath(name).stem,
            mime_type=MIME_TYPES[kind],
            size_bytes=len(data),
            content_sha256=sha256,
            storage_path=str(storage_path),
            status="processing",
        )
        self.session.add(document)
        self.session.commit()

        try:
            self._ingest(document, name, data)
        except AppError as exc:
            self._mark_failed(document, exc.message)
            raise
        except Exception as exc:
            logger.exception("Ingestion failed for document %s", document.id)
            self._mark_failed(document, "Processing failed due to an internal error.")
            raise AppError(
                "The document could not be processed.", code="ingestion_failed", status_code=500
            ) from exc
        return document, True

    def _ingest(self, document: Document, filename: str, data: bytes) -> None:
        started = time.perf_counter()
        processed = process_document(
            filename,
            data,
            strategy=self.settings.chunking_strategy,
            max_tokens=self.settings.chunk_max_tokens,
            overlap_tokens=self.settings.chunk_overlap_tokens,
            max_pages=self.settings.max_pdf_pages,
        )
        structured, drafts = processed.structured, processed.chunks
        if not drafts:
            raise EmptyDocumentError("No text passages could be extracted from this document.")

        vectors: list[list[float]] = []
        batch = self.settings.embedding_batch_size
        for i in range(0, len(drafts), batch):
            vectors.extend(self.embedder.embed_documents([d.text for d in drafts[i : i + batch]]))

        for draft, vector in zip(drafts, vectors, strict=True):
            self.session.add(
                Chunk(
                    document_id=document.id,
                    chunk_index=draft.index,
                    text=draft.text,
                    section=draft.section,
                    page_number=draft.page_number,
                    char_start=draft.char_start,
                    char_end=draft.char_end,
                    token_count=draft.token_count,
                    embedding=vector,
                    embedding_model=self.embedder.name,
                    meta=draft.meta,
                )
            )

        document.status = "ready"
        document.page_count = structured.page_count
        if structured.title:
            document.title = structured.title
        document.meta = {
            "file_kind": processed.kind,
            "chunk_count": len(drafts),
            "chunking_strategy": self.settings.chunking_strategy,
            "section_detection": structured.section_detection,
            "sections_found": structured.sections_found,
            "patent_numbers_detected": structured.patent_numbers,
            "embedding_model": self.embedder.name,
            "processing_ms": round((time.perf_counter() - started) * 1000),
        }
        self.session.commit()
        logger.info(
            "Ingested document %s: %d chunks, sections=%s",
            document.id,
            len(drafts),
            structured.sections_found or "none detected",
        )

    def _mark_failed(self, document: Document, message: str) -> None:
        self.session.rollback()
        document = self.session.get(Document, document.id)
        if document is not None:
            document.status = "failed"
            document.error_message = message
            self.session.commit()

    def _store_file(self, sha256: str, extension: str, data: bytes) -> Path:
        directory = self.settings.upload_dir
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{sha256}{extension}"
        temporary = path.with_suffix(f".{uuid.uuid4().hex}.tmp")
        temporary.write_bytes(data)
        temporary.replace(path)  # atomic: never leaves a half-written file
        return path

    # ------------------------------------------------------------------ read / delete

    def list_documents(self) -> list[tuple[Document, int]]:
        chunk_counts = (
            select(Chunk.document_id, func.count().label("n"))
            .group_by(Chunk.document_id)
            .subquery()
        )
        rows = self.session.execute(
            restrict(select(Document, func.coalesce(chunk_counts.c.n, 0)), Document.owner_id)
            .outerjoin(chunk_counts, chunk_counts.c.document_id == Document.id)
            .order_by(Document.uploaded_at.desc())
        )
        return [(doc, count) for doc, count in rows]

    def get(self, document_id: uuid.UUID) -> Document:
        document = self.session.get(Document, document_id)
        if document is None or not visible(document.owner_id):
            raise NotFoundError("Document not found.")  # same answer for "not yours"
        return document

    def chunks(
        self,
        document_id: uuid.UUID,
        *,
        section: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Chunk]:
        self.get(document_id)
        stmt = select(Chunk).where(Chunk.document_id == document_id)
        if section:
            stmt = stmt.where(Chunk.section == section)
        stmt = stmt.order_by(Chunk.chunk_index).limit(limit).offset(offset)
        return list(self.session.scalars(stmt))

    def delete(self, document_id: uuid.UUID) -> None:
        document = self.get(document_id)
        path = Path(document.storage_path)
        self.session.delete(document)
        self.session.commit()
        # Files are stored by content hash, so another user's copy may share this file
        still_used = self.session.scalar(
            select(Document.id).where(Document.storage_path == str(path)).limit(1)
        )
        # Only delete files inside the upload directory (defence against bad paths)
        if not still_used and path.is_relative_to(self.settings.upload_dir):
            path.unlink(missing_ok=True)
