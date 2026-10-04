"""Verifiers: does a passage support a claim?

Each verifier scores (claim, passages) pairs and returns a verdict:
- supported            the passages state the claim
- partially_supported  some of it is stated, some is not
- unsupported          the passages do not state it (or contradict it)

Three interchangeable methods, so experiments can compare them:

| method    | how                                                    | cost / speed          |
|-----------|--------------------------------------------------------|-----------------------|
| nli       | Natural Language Inference model: P(passage ⇒ claim),  | free, local, ~1 s     |
|           | max over sentence windows of each passage              | per answer            |
| llm_judge | the LLM reads passages + claims and judges, as JSON    | one LLM call / answer |
| lexical   | share of the claim's content words found in passages   | free, instant, crude  |

NLI ("natural language inference", also called textual entailment) is a classic NLP
task: given a premise and a hypothesis, decide whether the premise *entails*,
*contradicts* or is *neutral* toward the hypothesis. Here premise = evidence passage,
hypothesis = the answer's statement.
"""

import json
import logging
import re
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import lru_cache

from app.core.errors import ConfigurationError
from app.llm.providers import ChatMessage, LLMProvider

logger = logging.getLogger(__name__)

SUPPORTED, PARTIAL, UNSUPPORTED = "supported", "partially_supported", "unsupported"


@dataclass
class Judgement:
    verdict: str
    score: float  # 0..1 support strength
    best_passage: int | None  # index into the passages given
    reason: str = ""
    contradicted: bool = False
    contradiction: float = 0.0  # highest contradiction probability seen (NLI only)


class Verifier(ABC):
    name: str

    @abstractmethod
    def judge(self, claims: list[str], passages_per_claim: list[list[str]]) -> list[Judgement]:
        """For each claim, judge it against its own list of passages."""


# ---------------------------------------------------------------- lexical


_STOP = set(
    "a an and are as at be by for from has have in into is it its of on or that the their "
    "this to was were which with each also both can may such these those than then there "
    "uses use used using based one two first second wherein comprising".split()
)


def _content_words(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9][a-z0-9\-]*", text.lower())
    # crude stemming: "sensors" ~ "sensor", "estimated" ~ "estimate"
    return {re.sub(r"(ing|ed|es|s)$", "", w) for w in words if w not in _STOP and len(w) > 2}


class LexicalVerifier(Verifier):
    name = "lexical"

    def judge(self, claims, passages_per_claim):
        out = []
        for claim, passages in zip(claims, passages_per_claim, strict=True):
            words = _content_words(claim)
            if not words or not passages:
                out.append(Judgement(UNSUPPORTED, 0.0, None, "no evidence to compare"))
                continue
            recalls = [len(words & _content_words(p)) / len(words) for p in passages]
            best = max(range(len(recalls)), key=recalls.__getitem__)
            score = recalls[best]
            verdict = SUPPORTED if score >= 0.75 else PARTIAL if score >= 0.45 else UNSUPPORTED
            out.append(
                Judgement(
                    verdict,
                    round(score, 3),
                    best,
                    f"{round(score * 100)}% of the statement's key words appear",
                )
            )
        return out


# ---------------------------------------------------------------- NLI


# Sentence ends; also the ";" / ":" that separate the elements of a patent claim
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[\[(A-Z0-9])|(?<=[;:])\s+")
MAX_WINDOWS = 24  # per passage; bounds cost for very long passages


def premise_windows(premise: str) -> list[str]:
    """The passage, plus every sentence and every pair of neighbouring sentences.

    Observed (Phase 9): the small NLI model loses entailment when the premise has extra
    sentences. "The controller samples every thermistor at 10 Hz." scored p=0.99 against
    that sentence alone, but p=0.04-0.38 against its 3-sentence paragraph. Scoring
    sentence windows and taking the maximum (as in SummaC, Laban et al. 2022) fixes this.
    Pairs cover statements that join two sentences. A leading "Source: ..." line is kept
    on every window, because it tells the model which claim/section the text is from.
    """
    header, body = "", premise
    if premise.startswith("Source:") and "\n" in premise:
        header, body = premise.split("\n", 1)
        header += "\n"
    sentences = [s.strip() for s in _SENTENCE_END.split(body) if s.strip()]
    windows = [premise]
    if len(sentences) > 1:
        windows += [header + s for s in sentences]
        windows += [header + a + " " + b for a, b in zip(sentences, sentences[1:], strict=False)]
    return list(dict.fromkeys(windows))[: MAX_WINDOWS + 1]


class NliVerifier(Verifier):
    name = "nli"

    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model = None
        self._labels: dict[str, int] = {}
        self._lock = threading.Lock()

    def _load(self):
        with self._lock:
            if self._model is None:
                try:
                    from sentence_transformers import CrossEncoder
                except ImportError as exc:
                    raise ConfigurationError(
                        "The NLI verifier needs: pip install -r requirements-ml.txt"
                    ) from exc
                model = CrossEncoder(self.model_name)
                self._labels = {v.lower(): int(k) for k, v in model.model.config.id2label.items()}
                if not {"entailment", "contradiction"} <= set(self._labels):
                    raise ConfigurationError(f"{self.model_name} is not an NLI model.")
                self._model = model
        return self._model

    def judge(self, claims, passages_per_claim):
        model = self._load()
        pairs, owner = [], []
        for i, (claim, passages) in enumerate(zip(claims, passages_per_claim, strict=True)):
            for j, passage in enumerate(passages):
                for window in premise_windows(passage):
                    pairs.append((window, claim))
                    owner.append((i, j))
        probs = model.predict(pairs, apply_softmax=True, show_progress_bar=False) if pairs else []
        entail_i, contra_i = self._labels["entailment"], self._labels["contradiction"]

        best: dict[int, tuple[float, int]] = {}  # claim → (max entailment, passage)
        max_contra: dict[int, float] = {}
        for (i, j), p in zip(owner, probs, strict=True):
            entail, contra = float(p[entail_i]), float(p[contra_i])
            if i not in best or entail > best[i][0]:
                best[i] = (entail, j)
            max_contra[i] = max(max_contra.get(i, 0.0), contra)

        out = []
        for i in range(len(claims)):
            if i not in best:
                out.append(Judgement(UNSUPPORTED, 0.0, None, "no evidence to compare"))
                continue
            (entail, j), contra = best[i], max_contra[i]
            if entail >= 0.5:
                verdict, reason = SUPPORTED, f"entailed (p={entail:.2f})"
            elif entail >= 0.15:
                verdict, reason = PARTIAL, f"weakly entailed (p={entail:.2f})"
            elif contra >= 0.5:
                verdict, reason = UNSUPPORTED, f"contradicted (p={contra:.2f})"
            else:
                verdict, reason = UNSUPPORTED, f"not stated in the passage (p={entail:.2f})"
            contradicted = verdict == UNSUPPORTED and contra >= 0.5
            out.append(
                Judgement(
                    verdict,
                    round(entail, 3),
                    j,
                    reason,
                    contradicted=contradicted,
                    contradiction=round(contra, 3),
                )
            )
        return out


@lru_cache
def _shared_nli(model_name: str) -> NliVerifier:
    return NliVerifier(model_name)


# ---------------------------------------------------------------- NLI + lexical rescue

_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
_NEGATION = re.compile(r"\b(not|no|never|without|neither|nor|cannot|none)\b|n't\b", re.IGNORECASE)


_OPPOSITES = [
    ("increase", "decrease"),
    ("higher", "lower"),
    ("more", "less"),
    ("above", "below"),
    ("before", "after"),
    ("maximum", "minimum"),
    ("upper", "lower"),
    ("inlet", "outlet"),
    ("open", "close"),
    ("enable", "disable"),
    ("heat", "cool"),
    ("left", "right"),
    ("first", "second"),
    ("inside", "outside"),
    ("series", "parallel"),
]


def _has(word: str, text: str) -> bool:
    return re.search(rf"\b{word}", text, re.IGNORECASE) is not None


def safe_to_rescue(claim: str, passage: str) -> bool:
    """Word overlap is fooled by a changed number, an added negation or a swapped
    direction ("increases" for "decreases"): refuse the rescue in those cases."""
    if not set(_NUMBER.findall(claim)) <= set(_NUMBER.findall(passage)):
        return False
    if _NEGATION.search(claim) and not _NEGATION.search(passage):
        return False
    for a, b in _OPPOSITES:
        for word, opposite in ((a, b), (b, a)):
            if _has(word, claim) and not _has(word, passage) and _has(opposite, passage):
                return False
    return True


class NliLexicalVerifier(Verifier):
    """NLI, with a guarded second look at the statements it does not support.

    Observed (Experiment I, 2026-10-04): the small NLI model flagged 30% of statements a
    labeller judged supported, mostly paraphrases ("combines these likelihoods" for "a
    combined probability ... used to select the token") and metadata ("the patent's title
    is ..."). If at least 75% of the key words of such a statement appear in one passage
    (the lexical verifier's "supported" level), its numbers match, and it adds no negation
    or opposite direction word, it counts as supported. Requiring all key words removed
    almost all of the gain on the development labels (23 vs 11 false alarms of 69). Known
    limit: one unstated detail in a short statement can pass. See docs/report 6.6.
    """

    name = "nli_lexical"

    def __init__(self, nli: NliVerifier):
        self.nli = nli
        self.lexical = LexicalVerifier()

    def judge(self, claims, passages_per_claim):
        nli = self.nli.judge(claims, passages_per_claim)
        lexical = self.lexical.judge(claims, passages_per_claim)
        out = []
        for claim, passages, n, w in zip(claims, passages_per_claim, nli, lexical, strict=True):
            rescue = (
                n.verdict != SUPPORTED
                and w.verdict == SUPPORTED
                and w.best_passage is not None
                # NLI's contradiction score is not used: the small model gave 0.8-0.99 to
                # many correct paraphrases on the development labels
                and safe_to_rescue(claim, passages[w.best_passage])
            )
            if rescue:
                out.append(
                    Judgement(
                        SUPPORTED,
                        w.score,
                        w.best_passage,
                        f"all key terms in the passage ({w.reason}); NLI p={n.score:.2f}",
                        contradiction=n.contradiction,
                    )
                )
            else:
                out.append(n)
        return out


# ---------------------------------------------------------------- LLM judge


_JUDGE_PROMPT = """\
You check whether statements are supported by evidence passages. For each numbered
statement, read ONLY the passages listed under it and reply with ONLY a JSON array:
[{"id": 1, "verdict": "supported" | "partially_supported" | "unsupported", "reason": "..."}]
- supported: the passages state it (paraphrase is fine)
- partially_supported: part of it is stated, part is not
- unsupported: not stated, or contradicted
Judge only against the passages, not your own knowledge. Reasons under 15 words."""


class LlmJudgeVerifier(Verifier):
    name = "llm_judge"
    _SCORES = {SUPPORTED: 1.0, PARTIAL: 0.5, UNSUPPORTED: 0.0}

    def __init__(self, llm: LLMProvider):
        self.llm = llm
        self.last_usage: tuple[int, int] = (0, 0)

    def judge(self, claims, passages_per_claim):
        if not claims:
            return []
        blocks = []
        for i, (claim, passages) in enumerate(zip(claims, passages_per_claim, strict=True), 1):
            evidence = "\n".join(f"  [P{j + 1}] {p}" for j, p in enumerate(passages)) or "  (none)"
            blocks.append(f"Statement {i}: {claim}\nPassages:\n{evidence}")
        response = self.llm.complete(
            [ChatMessage("system", _JUDGE_PROMPT), ChatMessage("user", "\n\n".join(blocks))],
            temperature=0.0,
            max_tokens=80 * len(claims) + 50,
        )
        self.last_usage = (response.prompt_tokens, response.completion_tokens)
        verdicts: dict[int, tuple[str, str]] = {}
        try:
            data = json.loads(re.search(r"\[.*\]", response.text, re.DOTALL).group(0))
            for item in data:
                if item.get("verdict") in self._SCORES:
                    verdicts[int(item["id"])] = (item["verdict"], str(item.get("reason", "")))
        except (AttributeError, ValueError, TypeError, KeyError):
            logger.info("LLM judge reply was not valid JSON")
        out = []
        for i, passages in enumerate(passages_per_claim, 1):
            verdict, reason = verdicts.get(i, (UNSUPPORTED, "judge gave no valid verdict"))
            out.append(Judgement(verdict, self._SCORES[verdict], 0 if passages else None, reason))
        return out


def build_verifier(method: str, *, nli_model: str, llm: LLMProvider | None) -> Verifier:
    if method == "auto":
        try:
            import sentence_transformers  # noqa: F401

            method = "nli_lexical"
        except ImportError:
            method = "lexical"
    if method == "nli":
        return _shared_nli(nli_model)
    if method == "nli_lexical":
        return NliLexicalVerifier(_shared_nli(nli_model))
    if method == "llm_judge":
        if llm is None:
            raise ConfigurationError("The LLM judge verifier needs an LLM.")
        return LlmJudgeVerifier(llm)
    return LexicalVerifier()
