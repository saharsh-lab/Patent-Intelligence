"""Demo mode: plant one false statement in the first draft, to show the checker at work.

Phase 14 (opt-in only: the chat's "Test the checker" button sends `inject_false_fact`).
The model writes its answer as usual; before verification, one sentence is made false in
a way typical of hallucinations, keeping its citation so it looks sourced:

1. changed_number   — a number in a cited sentence is changed ("25 °C" → "75 °C")
2. reversed_relation — a direction word is flipped ("increases" → "decreases")
3. invented_detail  — a plausible but unsourced sentence is added after a cited one

The checker is not told which sentence was planted. Whether it was caught is reported
as it happened, including a miss.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass

from app.rag.generation import ParsedAnswer, parse_answer

_CITATION = re.compile(r"\s*\[(?:E\d+|\?)\]")
# a number that is not part of a citation label, a claim/figure reference or a year
_NUMBER = re.compile(
    r"(?<![\w.\[¶])(?<!claim )(?<!claims )(?<!fig\. )(?<!fig )(?<!figure )(?<!¶)"
    r"(\d+(?:\.\d+)?)(?![\w\]])",
    re.IGNORECASE,
)
_FLIPS = [
    ("increases", "decreases"),
    ("increase", "decrease"),
    ("increased", "decreased"),
    ("increasing", "decreasing"),
    ("higher", "lower"),
    ("above", "below"),
    ("before", "after"),
    ("maximum", "minimum"),
    ("more", "less"),
    ("inside", "outside"),
    ("inlet", "outlet"),
    ("heats", "cools"),
    ("heating", "cooling"),
    ("enables", "disables"),
    ("prevents", "causes"),
    ("reduces", "raises"),
    ("reduce", "raise"),
    ("lowers", "raises"),
]
_INVENTED = [
    "It also requires a liquid-nitrogen stage that holds the system at -196 °C",
    "This approach was first demonstrated by NASA in 1962 for the Apollo programme",
    "The design must be certified under ISO 26262 ASIL-D before it may be used",
    "A titanium housing is mandatory because aluminium parts fail within 200 hours",
]

KINDS = {
    "changed_number": "changed a number",
    "reversed_relation": "reversed a relation",
    "invented_detail": "added an invented detail",
}


@dataclass
class Injection:
    kind: str
    planted: str  # the false sentence as it appears in the draft (with its citation)
    original: str | None  # the sentence it replaced; None when a sentence was added

    def to_json(self) -> dict:
        return asdict(self) | {"description": KINDS[self.kind]}


def _plain(sentence: str) -> str:
    return _CITATION.sub("", sentence).strip()


def _change_number(sentence: str) -> str | None:
    body = _CITATION.sub("", sentence)
    for match in _NUMBER.finditer(body):
        value = match.group(1)
        number = float(value)
        if 1900 <= number <= 2100 and "." not in value:
            continue  # a year: changing it is less clearly "a hallucinated fact"
        new = number * 3 if number else 15
        text = f"{new:.{len(value.split('.')[1])}f}" if "." in value else str(int(new))
        return sentence.replace(match.group(0), text, 1)
    return None


def _flip(sentence: str) -> str | None:
    for a, b in _FLIPS:
        for word, opposite in ((a, b), (b, a)):
            pattern = re.compile(rf"\b{word}\b", re.IGNORECASE)
            if pattern.search(sentence):
                found = pattern.search(sentence).group(0)
                new = opposite.capitalize() if found[0].isupper() else opposite
                return pattern.sub(new, sentence, count=1)
    return None


def plant_false_fact(
    parsed: ParsedAnswer, valid_labels: set[str]
) -> tuple[ParsedAnswer, Injection] | None:
    """Return the draft with one false statement, or None if there is nothing to alter."""
    if parsed.status != "answered":
        return None
    cited = [s for s in parsed.sentences if s.citations and s.text.strip() in parsed.text]
    if not cited:
        return None
    # Only alter real statements, not fragments like "1 [E1]." or "As shown in FIG [E2]."
    statements = [s for s in cited if len(re.findall(r"[A-Za-z]{2,}", _plain(s.text))) >= 5]
    cited = statements or cited
    # Prefer a sentence in the middle: the first one often restates the question
    ordered = cited[len(cited) // 2 :] + cited[: len(cited) // 2]

    for change, kind in ((_change_number, "changed_number"), (_flip, "reversed_relation")):
        for sentence in ordered if statements else []:
            original = sentence.text.strip()
            altered = change(original)
            if altered and _plain(altered) != _plain(original):
                text = parsed.text.replace(original, altered, 1)
                return parse_answer(text, valid_labels), Injection(kind, altered, original)

    anchor = ordered[0].text.strip()
    pick = int(hashlib.sha256(parsed.text.encode()).hexdigest(), 16) % len(_INVENTED)
    label = ordered[0].citations[0]
    planted = f"{_INVENTED[pick]} [{label}]."
    text = parsed.text.replace(anchor, f"{anchor} {planted}", 1)
    return parse_answer(text, valid_labels), Injection("invented_detail", planted, None)


def find_planted(claims: list, injection: Injection):
    """The verifier's result for the planted sentence (matched without citations)."""
    target = _plain(injection.planted).rstrip(".")
    for claim in claims:
        if _plain(claim.text).rstrip(".") == target or target in _plain(claim.text):
            return claim
    return None
