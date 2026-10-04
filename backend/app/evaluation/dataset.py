"""The labelled question set: format, loading, validation, and relevance matching.

A dataset is a YAML file next to its corpus files:

    name: dev
    corpus:                       # documents ingested before the experiment
      - {id: battery, file: corpus/battery_patent.txt}
    items:
      - id: q01
        type: lookup
        question: How fast does the controller sample the thermistors?
        relevant:                 # which passages answer it (ground truth)
          - {doc: battery, contains: "samples every thermistor"}
        key_facts: ["10 Hz"]      # facts a correct answer must state
        expected_intent: document_qa
        expected_tools: [search_uploaded_documents]

Why relevance is labelled by *content* (document + a short quote, claim number or
section) and not by chunk ID: chunk IDs change whenever the corpus is re-chunked,
so ID labels would make Experiment B (chunking strategies) impossible to score.
A retrieved passage is relevant if it comes from the labelled document and
satisfies every condition given (all of contains / claim / section).
"""

import hashlib
import re
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import yaml

from app.patents.numbers import parse_publication_number
from app.services.documents import sanitize_filename

ITEM_TYPES = (
    "lookup",  # a fact stated in one passage
    "claim_explanation",  # what does claim N add / cover
    "multi_passage",  # needs facts from several passages
    "comparison",  # compare two documents/patents
    "similar_search",  # find similar patents (needs patent sources)
    "patent_lookup",  # question about a patent by publication number
    "unanswerable",  # not in the corpus: the system should abstain
    "legal",  # asks for a legal opinion: must be reframed as technical
)
INTENTS = ("document_qa", "patent_lookup", "find_similar", "compare", "out_of_scope")
TOOLS = (
    "search_uploaded_documents",
    "retrieve_evidence",
    "retrieve_document_section",
    "search_patents",
    "get_patent_details",
    "compare_patents",
    "extract_key_concepts",
)


class DatasetError(ValueError):
    """The dataset file is malformed; the message says where."""


def normalize(text: str) -> str:
    """Lower-case, unify whitespace and dashes, so quotes match despite line breaks."""
    text = text.lower().replace("‐", "-").replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", text).strip()


@dataclass(frozen=True)
class RelevanceLabel:
    doc: str | None = None  # corpus id
    patent: str | None = None  # publication number, e.g. EP1234567A1
    contains: str | None = None
    claim: int | None = None
    section: str | None = None
    # Start of the claim/section's text, filled in when the dataset is loaded. Lets a
    # claim or section label also match chunks that carry no claim/section metadata
    # (fixed-size chunking), so Experiment B is not biased against fixed chunks.
    anchor: str | None = None

    def matches(self, passage: dict, doc_of_source: dict[str, str]) -> bool:
        """`passage` is one entry of a run's stored `answer.evidence` list."""
        if self.doc is not None and doc_of_source.get(passage.get("source_label") or "") != (
            self.doc
        ):
            return False
        if self.patent is not None and _patent_key(passage.get("source_label")) != _patent_key(
            self.patent
        ):
            return False
        text = normalize(passage["text"])
        if self.contains and normalize(self.contains) not in text:
            return False
        structural = (self.claim is None or passage.get("claim_number") == self.claim) and (
            self.section is None or passage.get("section") == self.section
        )
        if structural:
            return True
        return bool(self.anchor) and normalize(self.anchor) in text

    def describe(self) -> str:
        parts = [self.doc or self.patent or "?"]
        if self.claim is not None:
            parts.append(f"claim {self.claim}")
        if self.section:
            parts.append(self.section)
        if self.contains:
            parts.append(f'"{self.contains}"')
        return " · ".join(parts)


def _patent_key(number: str | None) -> str | None:
    if not number:
        return None
    try:
        parsed = parse_publication_number(number)
        return f"{parsed.country}{parsed.number}"  # ignore kind code (A1/B2) differences
    except ValueError:
        return re.sub(r"\W", "", number).upper()


@dataclass
class CorpusEntry:
    id: str
    path: Path

    @property
    def filename(self) -> str:
        """The name the document gets when uploaded (= `source_label` of its passages)."""
        return sanitize_filename(self.path.name)


@dataclass
class EvalItem:
    id: str
    type: str
    question: str
    scope: list[str] = field(default_factory=list)  # corpus ids to restrict the search to
    answerable: bool = True
    relevant: list[RelevanceLabel] = field(default_factory=list)
    key_facts: list[str] = field(default_factory=list)
    expected_intent: str | None = None
    expected_tools: list[str] | None = None
    legal: bool | None = None  # should the system flag this as a legal question?
    notes: str = ""


@dataclass
class Dataset:
    name: str
    path: Path
    description: str
    synthetic: bool  # synthetic documents: for testing the framework, never for reporting
    labelled_by: str
    corpus: list[CorpusEntry]
    items: list[EvalItem]

    @property
    def doc_of_source(self) -> dict[str, str]:
        """Evidence `source_label` (the uploaded filename) → corpus id."""
        return {entry.filename: entry.id for entry in self.corpus}

    def fingerprint(self) -> str:
        """SHA-256 over the dataset file and every corpus file: identifies the exact data."""
        digest = hashlib.sha256(self.path.read_bytes())
        for entry in sorted(self.corpus, key=lambda e: e.id):
            digest.update(entry.id.encode())
            digest.update(entry.path.read_bytes())
        return digest.hexdigest()


# ------------------------------------------------------------------ loading


def load_dataset(path: Path) -> Dataset:
    path = Path(path).resolve()
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise DatasetError(f"Cannot read dataset {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise DatasetError(f"{path}: expected a mapping at the top level")
    _only(raw, {"name", "description", "synthetic", "labelled_by", "corpus", "items"}, "dataset")

    corpus = []
    for i, entry in enumerate(_list(raw, "corpus")):
        where = f"corpus[{i}]"
        _only(entry, {"id", "file"}, where)
        file = (path.parent / _str(entry, "file", where)).resolve()
        if not file.is_file():
            raise DatasetError(f"{where}: file not found: {file}")
        corpus.append(CorpusEntry(_str(entry, "id", where), file))
    _unique([c.id for c in corpus], "corpus id")
    _unique([c.filename for c in corpus], "corpus file name")  # filenames identify sources

    corpus_ids = {c.id for c in corpus}
    items = [_parse_item(entry, i, corpus_ids) for i, entry in enumerate(_list(raw, "items"))]
    _unique([item.id for item in items], "item id")
    if not items:
        raise DatasetError(f"{path}: no items")

    dataset = Dataset(
        name=str(raw.get("name") or path.stem),
        path=path,
        description=str(raw.get("description") or ""),
        synthetic=bool(raw.get("synthetic", False)),
        labelled_by=str(raw.get("labelled_by") or "unknown"),
        corpus=corpus,
        items=items,
    )
    _anchor_labels(dataset)
    return dataset


ANCHOR_CHARS = 150  # shorter than the fixed chunker's 60-token overlap: always in one chunk


def _anchor_labels(dataset: Dataset) -> None:
    """Give claim/section labels the opening text of that claim/section (see `anchor`)."""
    needed = {
        label.doc
        for item in dataset.items
        for label in item.relevant
        if label.doc and (label.claim is not None or label.section)
    }
    if not needed:
        return
    from app.rag.ingestion import process_document

    starts: dict[tuple, str] = {}
    for entry in dataset.corpus:
        if entry.id not in needed:
            continue
        processed = process_document(
            entry.filename,
            entry.path.read_bytes(),
            strategy="section_aware",
            max_tokens=400,
            overlap_tokens=60,
            max_pages=1000,
        )
        for chunk in processed.chunks:
            opening = _opening(chunk.text)
            claim = (chunk.meta or {}).get("claim_number")
            if claim is not None:
                starts.setdefault((entry.id, "claim", claim), opening)
            starts.setdefault((entry.id, "section", chunk.section), opening)

    for item in dataset.items:
        anchored = []
        for label in item.relevant:
            key = None
            if label.doc and label.claim is not None:
                key = (label.doc, "claim", label.claim)
            elif label.doc and label.section:
                key = (label.doc, "section", label.section)
            if key is not None and key not in starts:
                what = f"claim {label.claim}" if label.claim is not None else label.section
                raise DatasetError(f"item {item.id}: {label.doc} has no {what}")
            anchored.append(replace(label, anchor=starts[key]) if key else label)
        item.relevant = anchored


def _opening(text: str) -> str:
    text = " ".join(text.split())
    if len(text) <= ANCHOR_CHARS:
        return text
    return text[:ANCHOR_CHARS].rsplit(" ", 1)[0]


_ITEM_KEYS = {
    "id",
    "type",
    "question",
    "scope",
    "answerable",
    "relevant",
    "key_facts",
    "expected_intent",
    "expected_tools",
    "legal",
    "notes",
}


def _parse_item(entry: Any, index: int, corpus_ids: set[str]) -> EvalItem:
    where = f"items[{index}]"
    if not isinstance(entry, dict):
        raise DatasetError(f"{where}: expected a mapping")
    _only(entry, _ITEM_KEYS, where)
    item_id = _str(entry, "id", where)
    where = f"item {item_id}"
    item_type = _str(entry, "type", where)
    if item_type not in ITEM_TYPES:
        raise DatasetError(f"{where}: unknown type {item_type!r} (allowed: {ITEM_TYPES})")

    scope = [str(s) for s in entry.get("scope") or []]
    for doc in scope:
        if doc not in corpus_ids:
            raise DatasetError(f"{where}: scope refers to unknown corpus id {doc!r}")

    labels = []
    for j, label in enumerate(entry.get("relevant") or []):
        lw = f"{where} relevant[{j}]"
        _only(label, {"doc", "patent", "contains", "claim", "section"}, lw)
        if not (label.get("doc") or label.get("patent")):
            raise DatasetError(f"{lw}: needs 'doc' (corpus id) or 'patent' (number)")
        if label.get("doc") and label["doc"] not in corpus_ids:
            raise DatasetError(f"{lw}: unknown corpus id {label['doc']!r}")
        if not ({"contains", "claim", "section"} & set(label)) and not label.get("patent"):
            raise DatasetError(f"{lw}: add 'contains', 'claim' or 'section' to locate the passage")
        labels.append(
            RelevanceLabel(
                doc=label.get("doc"),
                patent=label.get("patent"),
                contains=label.get("contains"),
                claim=int(label["claim"]) if label.get("claim") is not None else None,
                section=label.get("section"),
            )
        )

    answerable = bool(entry.get("answerable", item_type != "unanswerable"))
    if answerable and not labels:
        raise DatasetError(f"{where}: answerable items need at least one 'relevant' label")

    intent = entry.get("expected_intent")
    if intent is not None and intent not in INTENTS:
        raise DatasetError(f"{where}: unknown expected_intent {intent!r} (allowed: {INTENTS})")
    tools = entry.get("expected_tools")
    if tools is not None:
        unknown = set(tools) - set(TOOLS)
        if unknown:
            raise DatasetError(f"{where}: unknown tools {sorted(unknown)} (allowed: {TOOLS})")

    return EvalItem(
        id=item_id,
        type=item_type,
        question=_str(entry, "question", where),
        scope=scope,
        answerable=answerable,
        relevant=labels,
        key_facts=[str(f) for f in entry.get("key_facts") or []],
        expected_intent=intent,
        expected_tools=list(tools) if tools is not None else None,
        legal=entry.get("legal"),
        notes=str(entry.get("notes") or ""),
    )


def _only(entry: Any, allowed: set[str], where: str) -> None:
    if not isinstance(entry, dict):
        raise DatasetError(f"{where}: expected a mapping")
    unknown = set(entry) - allowed
    if unknown:  # catches typos such as "relevent", which would silently drop labels
        raise DatasetError(f"{where}: unknown keys {sorted(unknown)}")


def _list(raw: dict, key: str) -> list:
    value = raw.get(key) or []
    if not isinstance(value, list):
        raise DatasetError(f"'{key}' must be a list")
    return value


def _str(entry: dict, key: str, where: str) -> str:
    value = entry.get(key)
    if value is None or not str(value).strip():
        raise DatasetError(f"{where}: missing '{key}'")
    return str(value).strip()


def _unique(values: list[str], what: str) -> None:
    seen = set()
    for value in values:
        if value in seen:
            raise DatasetError(f"duplicate {what}: {value!r}")
        seen.add(value)
