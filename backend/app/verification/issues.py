"""What exactly is wrong with a flagged statement: the words the X-ray marks.

Display only. These are computed after the verdict and never change it, so the verdicts
measured in Experiment I stay as they were. Four kinds, each pointing at words in the
statement as written:

- number     a quantity the passage does not have ("120 degrees" where it says "40 °C")
- direction  a direction word reversed in the same phrase ("decreases" for "increases")
- negation   a "not"/"no" the passage does not have
- unstated   content words the passage never uses (an added detail)

A statement *contradicts* its passage only on concrete evidence: a different number with
the same unit, or a reversed direction. The NLI model's own contradiction score is not
used for this: on the development labels it gave 0.8-0.99 to many correct paraphrases.
"""

import re
from dataclasses import dataclass

from app.verification.verifiers import (
    _NEGATION,
    _QUANTITY,
    _STOP,
    _UNIT_ALIASES,
    _UNITS,
    _flipped,
)

# Above this share of unstated words the statement is about something the passage does
# not discuss at all; marking every word would only add noise.
MAX_UNSTATED_SHARE = 0.75

_WORD = re.compile(r"[A-Za-z][A-Za-z0-9\-]*")
_LABEL = re.compile(r"\s*\[(?:E\d+|\?)\]")
# Not worth marking as "not in the passage": helper verbs, and unit names (numbers are
# checked with their units above, "degrees Celsius" against "°C")
_IGNORE = (
    _STOP
    | set(
        "does did do done being been will would could should must might shall not very just "
        "only when what how why where who whom whose through about celsius fahrenheit degree "
        "degrees percent hertz kelvin".split()
    )
    | set(_UNIT_ALIASES)
    | _UNITS
)


@dataclass
class Issue:
    kind: str  # number | direction | negation | unstated
    text: str  # the words in the statement, exactly as written
    passage_says: str | None = None  # what the passage has instead, when it has something
    conflict: bool = False  # concrete evidence that the statement contradicts the passage


def _stem(word: str) -> str:
    return re.sub(r"(ing|ed|es|s)$", "", word.lower())


def _present(stem: str, stems: set[str]) -> bool:
    """`stem` occurs in the passage, allowing a different ending ("controll" ~ "control")."""
    if stem in stems:
        return True
    if len(stem) < 6:
        return False
    return any(s[:5] == stem[:5] and abs(len(s) - len(stem)) <= 3 for s in stems)


def _quantities(text: str) -> list[tuple[str, str, str]]:
    """(number, unit, words as written) for each quantity in the text."""
    out = []
    for match in _QUANTITY.finditer(text):
        number, unit = match.group(1), re.sub(r"\s+", "", (match.group(2) or "").lower())
        unit = _UNIT_ALIASES.get(unit, unit)
        unit = unit if unit in _UNITS else ""
        written = match.group(0).strip() if unit else number
        out.append((number.replace(",", "."), unit, written))
    return out


def find_issues(statement: str, passage: str) -> list[Issue]:
    statement = _LABEL.sub("", statement)
    issues: list[Issue] = []

    have = _quantities(passage)
    numbers = {(n, u) for n, u, _ in have}
    for number, unit, written in _quantities(statement):
        if (number, unit) in numbers or (not unit and any(n == number for n, _ in numbers)):
            continue
        instead = next((w for n, u, w in have if unit and u == unit), None)
        issues.append(Issue("number", written, instead, conflict=instead is not None))

    flipped = _flipped(statement, passage, phrase_only=True)
    if flipped:
        word, opposite = flipped
        said = re.search(rf"\b{word}\w*", statement, re.IGNORECASE)
        instead = re.search(rf"\b{opposite}\w*", passage, re.IGNORECASE)
        if said:
            issues.append(
                Issue("direction", said.group(0), instead.group(0) if instead else opposite, True)
            )

    negation = _NEGATION.search(statement)
    if negation and not _NEGATION.search(passage):
        issues.append(Issue("negation", negation.group(0).strip()))

    marked = " ".join(i.text.lower() for i in issues)
    stems = {_stem(w) for w in _WORD.findall(passage)}
    words = [
        w
        for w in _WORD.findall(statement)
        if w.lower() not in _IGNORE and len(w) > 2 and w.lower() not in marked
    ]
    missing = [w for w in words if not _present(_stem(w), stems)]
    if missing and len(missing) / len(words) <= MAX_UNSTATED_SHARE:
        issues += [Issue("unstated", phrase) for phrase in _phrases(statement, missing)]
    return issues


def _phrases(statement: str, missing: list[str]) -> list[str]:
    """Neighbouring missing words as one phrase ("PID controller"), exactly as written."""
    wanted = {w.lower() for w in missing}
    spans: list[list[int]] = []
    for match in _WORD.finditer(statement):
        if match.group(0).lower() not in wanted:
            spans.append([])  # breaks the phrase
            continue
        current = spans[-1] if spans else []
        if current and not statement[current[1] : match.start()].strip(" -"):
            current[1] = match.end()
        else:
            spans.append([match.start(), match.end()])
    return list(dict.fromkeys(statement[s[0] : s[1]] for s in spans if s))


def contradicts(issues: list[Issue]) -> bool:
    return any(issue.conflict for issue in issues)


def closest_passage(statement: str, premise: dict[str, str]) -> str | None:
    """The label of the passage sharing most content words with the statement."""
    wanted = {_stem(w) for w in _WORD.findall(statement) if w.lower() not in _IGNORE}
    best, best_share = None, 0.0
    for label, text in premise.items():
        stems = {_stem(w) for w in _WORD.findall(text)}
        share = len(wanted & stems) / len(wanted) if wanted else 0.0
        if share > best_share:
            best, best_share = label, share
    return best
