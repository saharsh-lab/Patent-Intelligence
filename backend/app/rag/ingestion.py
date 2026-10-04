"""The ingestion pipeline as one pure function (no database, no files on disk).

    bytes -> detect type -> extract pages -> clean -> detect sections -> chunk

Keeping this free of side effects makes it easy to test, and lets experiments
re-chunk the same documents with different settings (Experiment B).
"""

from dataclasses import dataclass
from typing import Literal

from app.rag.chunking import ChunkDraft, chunk_document
from app.rag.cleaning import clean_pages
from app.rag.extraction import FileKind, detect_file_kind, extract_pages
from app.rag.sections import StructuredDocument, structure_document


@dataclass
class ProcessedDocument:
    kind: FileKind
    structured: StructuredDocument
    chunks: list[ChunkDraft]


def process_document(
    filename: str,
    data: bytes,
    *,
    strategy: Literal["section_aware", "fixed"] = "section_aware",
    max_tokens: int = 400,
    overlap_tokens: int = 60,
    max_pages: int = 500,
) -> ProcessedDocument:
    kind = detect_file_kind(filename, data)
    raw_pages = extract_pages(kind, data, max_pages=max_pages)
    front_page = "\n".join(raw_pages[0].blocks)[:4000] if raw_pages else ""
    structured = structure_document(clean_pages(raw_pages), front_page_text=front_page)
    chunks = chunk_document(
        structured, strategy=strategy, max_tokens=max_tokens, overlap_tokens=overlap_tokens
    )
    return ProcessedDocument(kind=kind, structured=structured, chunks=chunks)
