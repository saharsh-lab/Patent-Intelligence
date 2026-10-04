"""Step 4 of ingestion: split a structured document into chunks.

Why chunk at all? Retrieval works best on focused passages, and an LLM can only
read a limited amount of text. A chunk is the unit we search, cite and show.

Two strategies (compared in Experiment B):

- section_aware (default): never mixes two patent sections in one chunk, makes
  every patent claim its own chunk (claims are the legally central part and are
  often asked about individually), and prefers to break at paragraph ends.
- fixed: a plain sliding window of N tokens that ignores structure — the
  common baseline in RAG papers.

Every chunk's text is an exact slice of the document text (`char_start` to
`char_end`), so the UI can highlight the precise cited passage later.
"""

import bisect
import re
from dataclasses import dataclass, field
from typing import Literal

from app.rag.sections import CLAIM_START, Block, StructuredDocument

_TOKEN = re.compile(r"\w+|[^\w\s]")
_SENTENCE_END = re.compile(r"(?<=[.!?;])\s+(?=[A-Z0-9(\[\"'])")
# Abbreviations after which a period does NOT end a sentence (common in patents)
_ABBREVIATIONS = ("fig.", "figs.", "no.", "nos.", "e.g.", "i.e.", "etc.", "approx.", "ref.")


def approx_tokens(text: str) -> int:
    """Rough token count (words + punctuation). Real tokenizers differ by ~10-30%."""
    return len(_TOKEN.findall(text))


@dataclass
class ChunkDraft:
    index: int
    text: str
    section: str | None
    page_number: int | None
    char_start: int
    char_end: int
    token_count: int
    meta: dict = field(default_factory=dict)


@dataclass
class _Unit:
    """A sentence-sized span of the document text, the smallest thing we pack into chunks."""

    start: int
    end: int
    tokens: int
    ends_block: bool


def chunk_document(
    doc: StructuredDocument,
    *,
    strategy: Literal["section_aware", "fixed"] = "section_aware",
    max_tokens: int = 400,
    overlap_tokens: int = 60,
) -> list[ChunkDraft]:
    if overlap_tokens >= max_tokens:
        raise ValueError("overlap_tokens must be smaller than max_tokens")
    if strategy == "fixed":
        spans = _fixed_windows(doc.text, max_tokens, overlap_tokens)
        drafts = [_draft(doc, start, end, kind="window") for start, end in spans]
    else:
        drafts = _section_aware(doc, max_tokens, overlap_tokens)
    for index, draft in enumerate(drafts):
        draft.index = index
    return drafts


# ----------------------------------------------------------------- section-aware


def _section_aware(doc: StructuredDocument, max_tokens: int, overlap: int) -> list[ChunkDraft]:
    drafts: list[ChunkDraft] = []
    for group, is_claim in _content_groups(doc.blocks):
        units = _units(doc.text, group, max_tokens)
        for start, end in _pack(units, max_tokens, overlap):
            draft = _draft(doc, start, end, kind="claim" if is_claim else "passage")
            if is_claim:
                match = CLAIM_START.match(doc.text[group[0].char_start : group[0].char_end])
                if match:
                    draft.meta["claim_number"] = int(match.group(1))
            drafts.append(draft)
    return drafts


def _content_groups(blocks: list[Block]) -> list[tuple[list[Block], bool]]:
    """Group consecutive non-heading blocks of the same section; one group per claim."""
    groups: list[tuple[list[Block], bool]] = []
    current: list[Block] = []
    current_is_claim = False
    for block in blocks:
        if block.is_heading:
            if current:
                groups.append((current, current_is_claim))
            current, current_is_claim = [], False
            continue
        starts_claim = block.section == "claims" and bool(CLAIM_START.match(block.text))
        section_changed = bool(current) and current[-1].section != block.section
        if current and (starts_claim or section_changed):
            groups.append((current, current_is_claim))
            current = []
        if not current:
            current_is_claim = starts_claim
        current.append(block)
    if current:
        groups.append((current, current_is_claim))
    return groups


def _units(text: str, blocks: list[Block], max_tokens: int) -> list[_Unit]:
    """Split blocks into sentences; split any over-long sentence into word windows."""
    units: list[_Unit] = []
    for block in blocks:
        sentences = _sentence_spans(text, block.char_start, block.char_end)
        for i, (start, end) in enumerate(sentences):
            last = i == len(sentences) - 1
            pieces = _split_long(text, start, end, max_tokens)
            for j, (s, e) in enumerate(pieces):
                ends_block = last and j == len(pieces) - 1
                units.append(_Unit(s, e, approx_tokens(text[s:e]), ends_block))
    return units


def _sentence_spans(text: str, start: int, end: int) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    cursor = start
    for match in _SENTENCE_END.finditer(text, start, end):
        before = text[cursor : match.start()].lower()
        if before.endswith(_ABBREVIATIONS):
            continue
        spans.append((cursor, match.start()))
        cursor = match.end()
    spans.append((cursor, end))
    return [(s, e) for s, e in spans if e > s]


def _split_long(text: str, start: int, end: int, max_tokens: int) -> list[tuple[int, int]]:
    """Cut a span longer than max_tokens at word boundaries (no overlap inside)."""
    if approx_tokens(text[start:end]) <= max_tokens:
        return [(start, end)]
    pieces = []
    piece_start = start
    count = 0
    for match in _TOKEN.finditer(text, start, end):
        if count == max_tokens:
            pieces.append((piece_start, _rstrip(text, piece_start, match.start())))
            piece_start, count = match.start(), 0
        count += 1
    pieces.append((piece_start, end))
    return pieces


def _pack(units: list[_Unit], max_tokens: int, overlap: int) -> list[tuple[int, int]]:
    """Greedily combine units into chunks of at most max_tokens, with sentence overlap."""
    spans: list[tuple[int, int]] = []
    i = 0
    while i < len(units):
        first = i
        tokens = 0
        while i < len(units) and (i == first or tokens + units[i].tokens <= max_tokens):
            tokens += units[i].tokens
            i += 1
            # Prefer to stop at a paragraph end once the chunk is reasonably full
            if units[i - 1].ends_block and tokens >= 0.6 * max_tokens:
                break
        spans.append((units[first].start, units[i - 1].end))
        if i >= len(units):
            break
        # Overlap: restart a few sentences back, so context spanning the cut is not lost
        back, carried = i, 0
        while back - 1 > first and carried + units[back - 1].tokens <= overlap:
            back -= 1
            carried += units[back].tokens
        i = back
    return spans


# ----------------------------------------------------------------- fixed baseline


def _fixed_windows(text: str, max_tokens: int, overlap: int) -> list[tuple[int, int]]:
    tokens = list(_TOKEN.finditer(text))
    step = max_tokens - overlap
    spans = []
    for first in range(0, len(tokens), step):
        window = tokens[first : first + max_tokens]
        spans.append((window[0].start(), window[-1].end()))
        if first + max_tokens >= len(tokens):
            break
    return spans


# ----------------------------------------------------------------- helpers


def _draft(doc: StructuredDocument, start: int, end: int, *, kind: str) -> ChunkDraft:
    block = _block_at(doc, start)
    end_block = _block_at(doc, max(start, end - 1))
    meta: dict = {"kind": kind}
    if end_block.page_number and end_block.page_number != block.page_number:
        meta["page_end"] = end_block.page_number
    chunk_text = doc.text[start:end]
    return ChunkDraft(
        index=0,
        text=chunk_text,
        section=block.section,
        page_number=block.page_number,
        char_start=start,
        char_end=end,
        token_count=approx_tokens(chunk_text),
        meta=meta,
    )


def _block_at(doc: StructuredDocument, offset: int) -> Block:
    starts = [b.char_start for b in doc.blocks]
    return doc.blocks[max(0, bisect.bisect_right(starts, offset) - 1)]


def _rstrip(text: str, start: int, end: int) -> int:
    while end > start and text[end - 1].isspace():
        end -= 1
    return end
