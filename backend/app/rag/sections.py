"""Step 3 of ingestion: recognise patent structure.

Patents usually contain the same sections (Abstract, Background, Summary,
Detailed Description, Claims), announced by headings. We look for those
headings and label every block of text with the section it belongs to.

Not every patent PDF follows the same layout, so this is deliberately
forgiving: if no headings are found at all, blocks get section=None and
citations fall back to page numbers. `section_detection` records which case
happened, so we can measure how often detection works.
"""

import re
from dataclasses import dataclass, field

from app.rag.extraction import Page

# Order matters: the first pattern that fully matches a heading wins.
_SECTION_PATTERNS = [
    (
        "claims",
        r"(the invention claimed is|what is claimed is|claimed is|we claim|i claim|claims?)",
    ),
    ("abstract", r"abstract( of the (disclosure|invention))?"),
    ("title", r"title( of (the )?invention)?"),
    (
        "technical_field",
        r"(technical field|field( of (the )?(invention|disclosure))?|field of application)",
    ),
    (
        "background",
        r"(background( of (the )?(invention|disclosure))?|background art"
        r"|description of (the )?related art|prior art)",
    ),
    (
        "summary",
        r"((brief )?summary( of (the )?(invention|disclosure))?|disclosure of (the )?invention)",
    ),
    (
        "drawings",
        r"(brief description of (the )?(several views of the )?drawings?"
        r"|description of (the )?(drawings?|figures))",
    ),
    (
        "description",
        r"(detailed description( of .{0,60})?|description of (the )?(preferred )?embodiments?"
        r"|description)",
    ),
]
_COMPILED = [(name, re.compile(pattern, re.IGNORECASE)) for name, pattern in _SECTION_PATTERNS]

# Strips decorations before a heading: INID codes "(57)", numbering "1." / "II."
_HEADING_PREFIX = re.compile(r"^(\(\d{2}\)\s*)?(([IVX]+|\d{1,2})\.\s+)?", re.IGNORECASE)

# "What is claimed is: 1. A device..." — claims intro followed by text on the same line
CLAIMS_INTRO = re.compile(
    r"^(the invention claimed is|what is claimed is|we claim|i claim)\s*:?\s*(?=[^\s:])",
    re.IGNORECASE,
)
# Start of a numbered claim ("1. A system ...", "12) The method ...")
CLAIM_START = re.compile(r"^(\d{1,3})\s*[.)]\s+(?=\S)")
# Numbered paragraph marker used in patent descriptions: "[0012]"
PARAGRAPH_MARKER = re.compile(r"^\[\d{4,5}\]")

_PATENT_NUMBER_PATTERNS = [
    re.compile(r"\bUS\s?(\d{1,2},?\d{3},?\d{3}|\d{4}/?\d{7})\s?([AB]\d)?\b"),
    re.compile(r"\bEP\s?\d\s?\d{3}\s?\d{3}\s?([AB]\d)?\b"),
    re.compile(r"\bWO\s?\d{4}/?\s?\d{6}\s?(A\d)?\b"),
]


def match_heading(line: str) -> str | None:
    """Return the canonical section name if this line is a section heading."""
    text = line.strip()
    if not text or len(text) > 80:
        return None
    text = _HEADING_PREFIX.sub("", text).rstrip(" :.").strip()
    for name, pattern in _COMPILED:
        if pattern.fullmatch(text):
            return name
    return None


@dataclass
class Block:
    text: str
    page_number: int | None
    section: str | None
    is_heading: bool
    char_start: int
    char_end: int


@dataclass
class StructuredDocument:
    """A cleaned document as one string plus labelled, located blocks."""

    text: str
    blocks: list[Block]
    page_count: int | None
    section_detection: str  # "headings" | "none"
    sections_found: list[str] = field(default_factory=list)
    title: str | None = None
    patent_numbers: list[str] = field(default_factory=list)


def structure_document(pages: list[Page], *, front_page_text: str = "") -> StructuredDocument:
    """Label blocks with sections and lay them out as one text with character offsets.

    `front_page_text` is the *uncleaned* first page: patent numbers often sit in the
    running header, which cleaning removes.
    """
    headings_present = any(match_heading(b) for page in pages for b in page.blocks)
    current = "front_matter" if headings_present else None

    blocks: list[Block] = []
    parts: list[str] = []
    offset = 0
    for page in pages:
        for raw in page.blocks:
            heading = match_heading(raw)
            if heading:
                current = heading
            if parts:
                offset += 2  # the "\n\n" separator between blocks
            blocks.append(
                Block(
                    text=raw,
                    page_number=page.number,
                    section=current,
                    is_heading=heading is not None,
                    char_start=offset,
                    char_end=offset + len(raw),
                )
            )
            parts.append(raw)
            offset += len(raw)

    text = "\n\n".join(parts)
    sections_found = list(
        dict.fromkeys(b.section for b in blocks if b.section and b.section != "front_matter")
    )
    numbered_pages = [p.number for p in pages if p.number is not None]
    return StructuredDocument(
        text=text,
        blocks=blocks,
        page_count=max(numbered_pages) if numbered_pages else None,
        section_detection="headings" if headings_present else "none",
        sections_found=sections_found,
        title=_guess_title(blocks),
        patent_numbers=_find_patent_numbers(front_page_text + "\n" + text[:4000]),
    )


def _guess_title(blocks: list[Block]) -> str | None:
    # 1) Text right after an explicit "Title" heading
    for i, block in enumerate(blocks):
        if block.is_heading and block.section == "title" and i + 1 < len(blocks):
            candidate = blocks[i + 1]
            if not candidate.is_heading:
                return candidate.text[:300]
    # 2) First short, wordy block near the start that is not a heading or a number line
    for block in blocks[:15]:
        words = block.text.split()
        digits = sum(ch.isdigit() for ch in block.text)
        if not block.is_heading and 3 <= len(words) <= 30 and digits / len(block.text) < 0.1:
            return block.text[:300]
    return None


def _find_patent_numbers(text: str) -> list[str]:
    found = []
    for pattern in _PATENT_NUMBER_PATTERNS:
        for match in pattern.finditer(text):
            found.append(re.sub(r"[\s,/]", "", match.group(0)))
    return list(dict.fromkeys(found))[:5]
