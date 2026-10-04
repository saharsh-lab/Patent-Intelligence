"""Step 2 of ingestion: clean extracted text so chunks and embeddings are not polluted.

Problems this fixes (all common in patent PDFs):
- running headers/footers repeated on every page ("US 10,123,456 B2", "Sheet 3 of 9")
- bare page numbers
- words broken across lines with a hyphen ("transmis-\\nsion")
- hard line breaks in the middle of sentences
- typographic ligatures and odd Unicode ("ﬁ" -> "fi", non-breaking spaces)
- headings and numbered claims glued to neighbouring text
"""

import re
import unicodedata
from collections import Counter

from app.rag.extraction import Page
from app.rag.sections import CLAIM_START, CLAIMS_INTRO, PARAGRAPH_MARKER, match_heading

_PAGE_NUMBER = re.compile(
    r"^(page\s*)?[-–]?\s*\d{1,4}\s*[-–]?(\s*(of|/)\s*\d{1,4})?$", re.IGNORECASE
)
_SPACES = re.compile(r"[ \t\f\v]+")


def clean_pages(pages: list[Page]) -> list[Page]:
    pages = [Page(p.number, [_normalize(b) for b in p.blocks]) for p in pages]
    pages = _remove_running_headers(pages)
    cleaned = []
    for page in pages:
        blocks = []
        for block in page.blocks:
            for piece in _split_block(block):
                text = _join_lines(piece)
                # Skip page numbers and fragments with no letters/digits (stray punctuation)
                if _has_content(text) and not _PAGE_NUMBER.match(text):
                    blocks.append(text)
        cleaned.append(Page(page.number, blocks))
    return cleaned


def _is_short(text: str) -> bool:
    # e.g. "U.S. Patent Jan. 5, 2021 Sheet 1 of 9 US 10,123,456 B2" is 11 words
    return len(text) <= 120 and len(text.split()) <= 12


def _has_content(text: str) -> bool:
    return any(ch.isalnum() for ch in text)


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)  # also expands ligatures
    return text.replace("­", "")  # soft hyphens


def _signature(text: str) -> str:
    """Text with digits masked, so 'Sheet 1 of 9' and 'Sheet 2 of 9' look the same."""
    return re.sub(r"\d+", "#", _SPACES.sub(" ", text.lower())).strip()


def _remove_running_headers(pages: list[Page]) -> list[Page]:
    """Drop blocks that repeat at the top or bottom of most pages."""
    if len(pages) < 3:
        return pages
    edge_counts: Counter[str] = Counter()
    for page in pages:
        # Only short blocks can be headers/footers; never drop real paragraphs
        edges = {_signature(b) for b in page.blocks[:2] + page.blocks[-2:] if _is_short(b)}
        edge_counts.update(edges)
    threshold = max(3, len(pages) // 2)
    repeated = {sig for sig, count in edge_counts.items() if count >= threshold}
    if not repeated:
        return pages

    result = []
    for page in pages:
        n = len(page.blocks)
        kept = [
            block
            for i, block in enumerate(page.blocks)
            if not ((i < 2 or i >= n - 2) and _signature(block) in repeated)
        ]
        result.append(Page(page.number, kept))
    return result


def _split_block(block: str) -> list[list[str]]:
    """Split a block's lines so headings, claims and numbered paragraphs stand alone."""
    pieces: list[list[str]] = []
    current: list[str] = []
    for raw_line in block.split("\n"):
        line = _SPACES.sub(" ", raw_line).strip()
        if not line:
            if current:
                pieces.append(current)
                current = []
            continue

        intro = CLAIMS_INTRO.match(line)
        if intro:  # "What is claimed is: 1. A device..." -> heading + claim
            if current:
                pieces.append(current)
            pieces.append([intro.group(0).strip()])
            current = [line[intro.end() :]]
        elif match_heading(line):
            if current:
                pieces.append(current)
            pieces.append([line])
            current = []
        elif CLAIM_START.match(line) or PARAGRAPH_MARKER.match(line):
            if current:
                pieces.append(current)
            current = [line]
        else:
            current.append(line)
    if current:
        pieces.append(current)
    return pieces


def _join_lines(lines: list[str]) -> str:
    """Join wrapped lines into one paragraph, repairing hyphenated line breaks."""
    text = ""
    for line in lines:
        if not text:
            text = line
        elif text.endswith("-") and len(text) > 1 and text[-2].isalpha() and line[:1].islower():
            text = text[:-1] + line  # "transmis-" + "sion" -> "transmission"
        else:
            text = f"{text} {line}"
    return text.strip()
