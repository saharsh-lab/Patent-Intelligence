"""The agent's tools: small functions with clear inputs and outputs.

A tool never talks to the LLM about its result directly. It returns a
`ToolResult` (a human-readable summary, evidence passages, and any new
"targets" such as a freshly imported patent). Each call is logged to the
`tool_calls` table, which is what the evaluation of tool selection uses.

| Tool                        | Purpose                                                  |
|-----------------------------|----------------------------------------------------------|
| search_uploaded_documents   | hybrid search over the local index (uploads + imports)   |
| retrieve_evidence           | hybrid search restricted to specific patents/documents   |
| retrieve_document_section   | fetch a section/claim directly (no similarity search)    |
| search_patents              | search external patent databases (EPO, ...)              |
| get_patent_details          | fetch full text of a patent and index it as evidence     |
| compare_patents             | balanced evidence from each patent being compared        |
| extract_key_concepts        | technical search terms describing an invention           |
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.agents.analysis import keywords_from_text
from app.core.config import Settings
from app.core.errors import AppError
from app.llm.providers import ChatMessage, LLMProvider
from app.models import Chunk, Document, Patent
from app.patents.base import PatentQuery
from app.patents.numbers import parse_publication_number
from app.patents.registry import choose_source
from app.rag.embeddings import EmbeddingProvider
from app.rag.reranker import Reranker
from app.rag.retrieval import RetrievalConfig, RetrievalResult, RetrievedPassage, retrieve
from app.services.patents import PatentService


@dataclass
class Target:
    """Something the question is about: an uploaded document, an imported patent,
    or an external patent that still has to be fetched."""

    kind: str  # "document" | "patent" | "external"
    label: str
    id: uuid.UUID | None = None
    number: str | None = None

    def to_json(self) -> dict:
        return {
            "kind": self.kind,
            "label": self.label,
            "id": str(self.id) if self.id else None,
            "number": self.number,
        }


@dataclass
class ToolContext:
    session: Session
    settings: Settings
    embedder: EmbeddingProvider
    llm: LLMProvider
    patents: PatentService
    retrieval: RetrievalConfig
    reranker: Reranker | None = None
    use_llm_helpers: bool = False  # e.g. LLM-based concept extraction


@dataclass
class ToolResult:
    summary: str
    passages: list[RetrievedPassage] = field(default_factory=list)
    retrieval: RetrievalResult | None = None
    direct: bool = False  # passages fetched by exact section, not by similarity
    new_targets: list[Target] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)


ToolFn = Callable[..., ToolResult]
TOOLS: dict[str, ToolFn] = {}


def tool(fn: ToolFn) -> ToolFn:
    TOOLS[fn.__name__] = fn
    return fn


def _scope(targets: list[Target]) -> tuple[list[uuid.UUID], list[uuid.UUID]]:
    documents = [t.id for t in targets if t.kind == "document" and t.id]
    patents = [t.id for t in targets if t.kind == "patent" and t.id]
    return documents, patents


def _summarize_retrieval(result: RetrievalResult) -> str:
    if not result.passages:
        return "no passages found"
    best = result.best_vector_similarity
    sources = {
        p.chunk.document.filename if p.chunk.document else p.chunk.patent.publication_number
        for p in result.passages
    }
    best_text = f", best similarity {best:.2f}" if best is not None else ""
    return f"{len(result.passages)} passages from {len(sources)} source(s){best_text}"


# ---------------------------------------------------------------- local evidence


@tool
def search_uploaded_documents(
    ctx: ToolContext,
    query: str,
    document_ids: list[uuid.UUID] | None = None,
    patent_ids: list[uuid.UUID] | None = None,
) -> ToolResult:
    result = retrieve(
        ctx.session,
        query,
        embedder=ctx.embedder,
        config=ctx.retrieval,
        reranker=ctx.reranker,
        document_ids=document_ids or None,
        patent_ids=patent_ids or None,
    )
    return ToolResult(_summarize_retrieval(result), result.passages, retrieval=result)


@tool
def retrieve_evidence(ctx: ToolContext, query: str, targets: list[Target]) -> ToolResult:
    documents, patents = _scope(targets)
    if not documents and not patents:
        return ToolResult("no indexed sources to search")
    result = retrieve(
        ctx.session,
        query,
        embedder=ctx.embedder,
        config=ctx.retrieval,
        reranker=ctx.reranker,
        document_ids=documents or [],
        patent_ids=patents or [],
    )
    return ToolResult(_summarize_retrieval(result), result.passages, retrieval=result)


@tool
def retrieve_document_section(
    ctx: ToolContext, target: Target, section: str, claim_number: int | None = None, limit: int = 6
) -> ToolResult:
    if target.kind not in ("document", "patent") or not target.id:
        return ToolResult(f"{target.label} is not indexed")
    owner = Chunk.document_id if target.kind == "document" else Chunk.patent_id
    stmt = select(Chunk).where(owner == target.id, Chunk.section == section)
    if claim_number is not None:
        stmt = stmt.where(Chunk.meta["claim_number"].as_integer() == claim_number)
    chunks = list(ctx.session.scalars(stmt.order_by(Chunk.chunk_index).limit(limit)))
    passages = [
        RetrievedPassage(chunk=c, score=1.0, rank=i + 1, direct=True) for i, c in enumerate(chunks)
    ]
    what = f"claim {claim_number}" if claim_number else section
    summary = (
        f"{len(chunks)} passage(s) from {what} of {target.label}"
        if chunks
        else (f"{target.label} has no {what} section")
    )
    return ToolResult(summary, passages, direct=True)


# ---------------------------------------------------------------- external patents


@tool
def search_patents(
    ctx: ToolContext, keywords: str, limit: int = 10, reference: Target | None = None
) -> ToolResult:
    """Search external databases; merge patent families; if a reference invention is
    given, rank candidates by semantic similarity to it."""
    if not ctx.patents.sources:
        raise AppError("No patent source is configured.", code="no_patent_source")
    indexed_reference = reference if reference and reference.id else None
    outcome = ctx.patents.search(
        PatentQuery(keywords=keywords, limit=limit),
        reference_document_id=indexed_reference.id
        if indexed_reference and indexed_reference.kind == "document"
        else None,
        reference_patent_id=indexed_reference.id
        if indexed_reference and indexed_reference.kind == "patent"
        else None,
    )
    failures = [s for s in outcome.sources if s.error]
    if failures and len(failures) == len(outcome.sources):
        raise AppError("; ".join(f"{s.source}: {s.error}" for s in failures), code="search_failed")
    candidates = [
        {
            "source": item.record.source,
            "publication_number": item.record.publication_number,
            "title": item.record.title,
            "imported_id": str(item.imported_id) if item.imported_id else None,
            "similarity": item.similarity,
            "also_published_as": item.also_published_as,
        }
        for item in outcome.results
    ]
    parts = [
        f"{s.source}: {s.returned} of {s.total}" + (" (cached)" if s.cached else "")
        for s in outcome.sources
        if not s.error
    ]
    extras = []
    if outcome.deduplicated:
        extras.append(f"{outcome.deduplicated} family duplicates merged")
    if outcome.reference_label and candidates:
        best = candidates[0]
        extras.append(
            f"ranked by similarity to {outcome.reference_label} "
            f"(best {best['publication_number']} {best['similarity']:.2f})"
        )
    return ToolResult(
        f'"{keywords}" → ' + ", ".join(parts) + "".join(f"; {e}" for e in extras),
        data={
            "candidates": candidates,
            "query_strings": [s.query_string for s in outcome.sources],
            "sources": [s.source for s in outcome.sources if not s.error],
        },
    )


def _source_for(ctx: ToolContext, number: str) -> str:
    return choose_source(ctx.patents.sources, number)


@tool
def get_patent_details(ctx: ToolContext, number: str, source: str | None = None) -> ToolResult:
    source = source or _source_for(ctx, number)
    patent, created = ctx.patents.import_patent(source, number)
    meta = patent.meta or {}
    parts = [
        "claims" if meta.get("has_claims") else None,
        "description" if meta.get("has_description") else None,
    ]
    available = " + ".join(p for p in parts if p) or "bibliographic data only"
    summary = (
        f"{'imported' if created else 'already imported'} {patent.publication_number} "
        f"({available}, {meta.get('chunk_count', 0)} passages)"
    )
    return ToolResult(
        summary,
        new_targets=[
            Target(
                "patent", patent.publication_number, id=patent.id, number=patent.publication_number
            )
        ],
        data={"sources": [source]},
    )


# ---------------------------------------------------------------- analysis helpers


@tool
def compare_patents(ctx: ToolContext, query: str, targets: list[Target]) -> ToolResult:
    """For each target: its abstract, its first claim, and the passages most relevant to
    the question. Balanced so one long patent cannot crowd out the other."""
    passages: list[RetrievedPassage] = []
    per_target = max(2, ctx.retrieval.top_k // max(1, len(targets)))
    lines = []
    for target in targets:
        if target.kind not in ("document", "patent") or not target.id:
            lines.append(f"{target.label}: not indexed")
            continue
        found = []
        for section, claim in (("abstract", None), ("claims", 1)):
            found += retrieve_document_section(ctx, target, section, claim, limit=1).passages
        relevant = retrieve_evidence(ctx, query, [target]).passages[:per_target]
        seen = {p.chunk.id for p in found}
        found += [p for p in relevant if p.chunk.id not in seen]
        passages += found
        lines.append(f"{target.label}: {len(found)} passages")
    for rank, passage in enumerate(passages, start=1):
        passage.rank = rank
    return ToolResult("; ".join(lines), passages, direct=True)


@tool
def extract_key_concepts(ctx: ToolContext, target: Target) -> ToolResult:
    """Short technical search terms for an invention, from its title, abstract and claim 1."""
    if target.kind not in ("document", "patent") or not target.id:
        raise AppError(f"{target.label} is not indexed.", code="target_not_indexed")
    owner = Chunk.document_id if target.kind == "document" else Chunk.patent_id
    chunks = ctx.session.scalars(
        select(Chunk)
        .where(
            owner == target.id,
            or_(Chunk.section.in_(["title", "abstract", "claims"]), Chunk.section.is_(None)),
        )
        .order_by(Chunk.chunk_index)
        .limit(4)
    ).all()
    title = None
    if target.kind == "document":
        title = ctx.session.get(Document, target.id).title
    else:
        title = ctx.session.get(Patent, target.id).title
    text = " ".join([title or ""] + [c.text for c in chunks])[:3000]

    keywords = ""
    method = "rules"
    if ctx.use_llm_helpers:
        response = ctx.llm.complete(
            [
                ChatMessage(
                    "system",
                    "Give 3 technical search terms (single words, most specific first) that "
                    "describe the core invention in the text, for searching patent titles and "
                    "abstracts. Reply with the words only, separated by spaces.",
                ),
                ChatMessage("user", text),
            ],
            temperature=0.0,
            max_tokens=30,
        )
        keywords = " ".join(response.text.replace(",", " ").split()[:3])
        method = "llm"
    if not keywords:
        keywords = keywords_from_text(title or text, limit=3)
        method = "rules"
    return ToolResult(f'"{keywords}" ({method})', data={"keywords": keywords})


def normalize_number(text: str) -> str:
    return parse_publication_number(text).normalized
