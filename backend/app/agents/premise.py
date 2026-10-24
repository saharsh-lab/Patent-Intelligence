"""False premises: a question that assumes something the sources never mention.

Observed (report 7.3): asked "which neural network does the Kalman-filter patent train?",
the agent described the Kalman filter and never said the patent has no neural network;
the checker then flagged most of the answer. So before writing, the question's terms that
no passage uses are found here and given to the writer, which is asked to say plainly that
the sources do not mention them when the question assumes they do.

Word-based, so it errs towards noticing: a synonym ("car" for "vehicle") is absent by this
test too. Two things keep that harmless: the writer is told to ignore the note when the
term is only another word for something in the passages, and the user sees the note only
when the answer itself says the sources do not mention the term.
"""

import re

from app.agents.analysis import _STOPWORDS
from app.verification.checker import states_absence
from app.verification.issues import _present, _stem

# Words that frame a question rather than name something in it
_FRAME = _STOPWORDS | set(
    "did is are was were been being an used use uses using work works working mean means "
    "meaning purpose role function main key part parts kind type types example examples "
    "way ways reason reasons happen happens difference differences between versus compared "
    "provide provides provided source sources passage passages text answer question mention "
    "mentions mentioned say says said state states stated much many more most does not "
    "should would could know possible exactly also only just each both either one two".split()
)
_WORD = re.compile(r"[A-Za-z][A-Za-z0-9\-]*")
MAX_TERMS = 3


def unstated_terms(question: str, passages: list[str]) -> list[str]:
    """Phrases of the question (as written) whose words no passage uses."""
    stems = {_stem(w) for text in passages for w in _WORD.findall(text)}

    def present(word: str) -> bool:
        parts = [p for p in word.split("-") if p]
        return _present(_stem(word), stems) or all(_present(_stem(p), stems) for p in parts)

    runs: list[list[re.Match]] = [[]]
    for match in _WORD.finditer(question):
        word = match.group(0)
        if word.lower() in _FRAME or len(word) < 3:
            runs.append([])
            continue
        last = runs[-1]
        if last and question[last[-1].end() : match.start()].strip(" -"):
            runs.append([])  # punctuation in between: a new phrase
        runs[-1].append(match)

    terms = []
    for run in filter(None, runs):
        words = [m.group(0) for m in run]
        absent = [w for w in words if not present(w)]
        if not absent:
            continue
        if len(words) == 1 and not (len(words[0]) >= 6 or words[0].isupper()):
            continue  # short single words are mostly verbs ("train", "run")
        if len(absent) == len(words) or (len(words) > 1 and len(absent) * 2 >= len(words)):
            terms.append(question[run[0].start() : run[-1].end()])
    return list(dict.fromkeys(terms))[:MAX_TERMS]


def _quoted(terms: list[str]) -> str:
    quoted = [f'"{t}"' for t in terms]
    return quoted[0] if len(quoted) == 1 else ", ".join(quoted[:-1]) + " and " + quoted[-1]


def instruction(terms: list[str]) -> str:
    one = len(terms) == 1
    return (
        f"The question mentions {_quoted(terms)}, which none of the passages mention. If the "
        f"question assumes the sources describe {'it' if one else 'them'}, begin the answer by "
        f"saying plainly, without a citation, that the sources do not mention {_quoted(terms)}; "
        "then give what the passages do say that is relevant, with citations. If "
        f"{'it is' if one else 'they are'} only a different word for something the passages "
        "describe, ignore this note."
    )


def acknowledged(answer: str, terms: list[str]) -> list[str]:
    """The terms the answer itself says the sources do not mention."""
    sentences = re.split(r"(?<=[.!?])\s+|\n+", answer)
    return [t for t in terms if any(states_absence(s, [t]) for s in sentences)]
