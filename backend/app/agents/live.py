"""The answer as it happens, for the chat page (polled about twice a second).

    searching  → sources appear as the tools find them
    writing    → the draft, word by word as the model writes it
    checking   → the finished draft, while every sentence is checked
    checked    → each sentence's verdict
    rewriting  → the sentences that failed, then a new draft is written (writing again)

Only a view: the agent behaves the same with or without it (no LiveAnswer is given for
experiments or the /ask API), and the stored answer is what the page shows at the end.
"""

import logging
import re
import time
from collections.abc import Callable

from app.core.errors import AnswerStopped
from app.rag.generation import EvidenceItem, source_label
from app.rag.retrieval import RetrievedPassage
from app.rag.transient import external_of
from app.verification.checker import VerificationReport

logger = logging.getLogger(__name__)

MAX_SOURCES = 16  # shown while searching; the evidence list has them all
_TEXT_EVERY = 0.12  # seconds between draft updates (the page polls about every 0.5 s)
_MARKER = re.compile(r"(?m)^\s*INSUFFICIENT_EVIDENCE\s*:?.*$")


def source_of(passage: RetrievedPassage) -> dict:
    """Where a passage comes from, as the chat shows it: kind, name, title and link."""
    chunk = passage.chunk
    external = external_of(chunk)
    if external is not None:
        kind = "patent" if chunk.section == "abstract" else "web"
        return {"kind": kind, "label": external.label, "title": external.title, "url": external.url}
    if chunk.document is not None:
        title = chunk.document.title or chunk.document.filename
        return {"kind": "library", "label": chunk.document.filename, "title": title, "url": None}
    title = getattr(chunk.patent, "title", None) or source_label(passage)
    return {"kind": "patent", "label": source_label(passage), "title": title, "url": None}


def _numbered(item: EvidenceItem) -> dict:
    """An evidence passage as the draft cites it: E1 → its source."""
    source = source_of(item.passage)
    return {
        "label": item.label,
        "kind": source["kind"],
        "source": source["label"],
        "title": source["title"],
        "url": source["url"],
    }


class LiveAnswer:
    def __init__(self, sink: Callable[[dict], None]):
        self.sink = sink
        self.state: dict = {
            "phase": "searching",
            "attempt": 0,
            "draft": "",
            "sources": [],
            "evidence": [],
            "claims": [],
            "flagged": [],
            "general": False,
        }
        self._last_text = 0.0

    def _push(self) -> None:
        try:
            self.sink({**self.state})
        except AnswerStopped:
            raise  # the user pressed Stop
        except Exception:  # noqa: BLE001 - a display problem must never stop an answer
            logger.warning("Live answer sink failed", exc_info=True)

    def found(self, passages: list[RetrievedPassage]) -> None:
        """Sources a tool just found (shown while the agent is still searching)."""
        known = {(s["kind"], s["label"]) for s in self.state["sources"]}
        added = []
        for passage in passages:
            source = source_of(passage)
            if (source["kind"], source["label"]) not in known:
                known.add((source["kind"], source["label"]))
                added.append(source)
        if added:
            self.state["sources"] = (self.state["sources"] + added)[:MAX_SOURCES]
            self._push()

    def writing(self, evidence: list[EvidenceItem]) -> None:
        """A draft is about to be written from these numbered passages."""
        self.state |= {
            "phase": "writing",
            "attempt": self.state["attempt"] + 1,
            "draft": "",
            "claims": [],
            "evidence": [_numbered(e) for e in evidence],
        }
        self._push()

    def general(self) -> None:
        """No source had the answer: the model answers from its general knowledge."""
        self.state |= {
            "phase": "writing",
            "attempt": self.state["attempt"] + 1,
            "draft": "",
            "claims": [],
            "evidence": [],
            "general": True,
        }
        self._push()

    def text(self, draft: str) -> None:
        """The draft so far (the INSUFFICIENT_EVIDENCE marker is not prose to show)."""
        self.state["draft"] = _MARKER.sub("", draft).rstrip()
        now = time.monotonic()
        if now - self._last_text >= _TEXT_EVERY:
            self._last_text = now
            self._push()

    def checking(self, text: str) -> None:
        """The finished draft (after parsing; in demo mode with the planted sentence)."""
        self.state |= {"phase": "checking", "draft": text, "claims": []}
        self._push()

    def checked(self, report: VerificationReport | None) -> None:
        claims = report.to_json()["claims"] if report else []
        self.state |= {"phase": "checked", "claims": claims}
        self._push()

    def rewriting(self, unsupported: list[str]) -> None:
        self.state |= {"phase": "rewriting", "flagged": unsupported}
        self._push()
