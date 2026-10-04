"""Split an invention description into technical features.

Two methods, chosen automatically:
- **Claim elements (rules):** if the text contains a claim ("… comprising: a; b; and c"),
  each element is one feature, exactly as the patent drafter separated them.
- **LLM:** otherwise the LLM lists the features as short standalone sentences. Every
  feature must reuse the description's own words (content-word overlap ≥ 50%), so the
  LLM cannot add features the user never described; unusable output falls back to
  sentences of the description.

Features are phrased as standalone statements ("There is a coolant pump that…") because
they become NLI hypotheses: "the invention includes X" would be judged against another
patent's text, where "the invention" means something else.
"""

import json
import logging
import re
from dataclasses import asdict, dataclass

from app.llm.providers import ChatMessage, LLMProvider

logger = logging.getLogger(__name__)

MAX_FEATURES = 8
MIN_GROUNDING = 0.5

_STOP = set(
    "a an and are as at be by for from has have in into is it its of on or that the their "
    "this to was were which with each also both can may such these those than then there "
    "wherein comprising configured invention system device method apparatus".split()
)


@dataclass
class Feature:
    id: str  # F1, F2, …
    text: str  # as shown to the user
    hypothesis: str  # standalone sentence used for the NLI check
    origin: str  # claim_element | llm | sentence

    def to_json(self) -> dict:
        return asdict(self)


def _words(text: str) -> set[str]:
    words = re.findall(r"[a-z][a-z0-9\-]+", text.lower())
    return {re.sub(r"(ing|ed|es|s)$", "", w) for w in words if w not in _STOP and len(w) > 2}


def grounding(feature: str, description: str) -> float:
    """Share of the feature's content words that occur in the description."""
    words = _words(feature)
    return len(words & _words(description)) / len(words) if words else 0.0


def _as_hypothesis(element: str) -> str:
    element = element.strip().rstrip(";,.").strip()
    element = re.sub(r"^(and|or)\s+", "", element, flags=re.IGNORECASE)
    if re.match(r"^(a|an|one|two|three|several|multiple|plural|at least)\b", element, re.I):
        return f"There is {element[0].lower()}{element[1:]}."
    return element[0].upper() + element[1:] + "."


_CLAIM = re.compile(r"\bcompris(?:ing|es)\s*:", re.IGNORECASE)


def claim_elements(text: str) -> list[str]:
    """Elements of the first claim-like statement: text after 'comprising:' split at ';'."""
    match = _CLAIM.search(text)
    if not match:
        return []
    body = text[match.end() :]
    body = re.split(r"\n\s*\d+\.\s", body)[0]  # stop at the next numbered claim
    elements = [e.strip() for e in re.split(r";", body) if len(e.split()) >= 3]
    return elements[:MAX_FEATURES]


_PROMPT = """\
List the distinct technical features of the invention described by the user.
Rules:
- 3 to 8 features; each one component, step or property, in ONE short sentence.
- Use the user's own words. Do not add anything the description does not state.
- Write each as a standalone statement, e.g. "A pump circulates coolant through the
  channels." Never write "the invention", "my", "our" or "the user".
Reply with ONLY a JSON array of strings."""


def extract_features(description: str, llm: LLMProvider | None = None) -> list[Feature]:
    elements = claim_elements(description)
    if len(elements) >= 2:
        return [
            Feature(f"F{i}", e.rstrip(";,. "), _as_hypothesis(e), "claim_element")
            for i, e in enumerate(elements, 1)
        ]

    if llm is not None:
        features = _llm_features(description, llm)
        if len(features) >= 2:
            return features

    # Fallback: the description's own sentences
    sentences = [
        s.strip()
        for s in re.split(r"(?<=[.!?])\s+", " ".join(description.split()))
        if len(s.split()) >= 5
    ]
    return [
        Feature(f"F{i}", s.rstrip("."), s if s.endswith(".") else s + ".", "sentence")
        for i, s in enumerate(sentences[:MAX_FEATURES], 1)
    ]


def _llm_features(description: str, llm: LLMProvider) -> list[Feature]:
    try:
        response = llm.complete(
            [ChatMessage("system", _PROMPT), ChatMessage("user", description)],
            temperature=0.0,
            max_tokens=500,
        )
        items = json.loads(re.search(r"\[.*\]", response.text, re.DOTALL).group(0))
    except Exception as exc:  # noqa: BLE001 - any failure falls back to sentences
        logger.info("Feature extraction by LLM failed (%s)", type(exc).__name__)
        return []
    features, seen = [], set()
    for item in items if isinstance(items, list) else []:
        text = " ".join(str(item).split()).strip()
        key = text.lower()
        if not text or key in seen or grounding(text, description) < MIN_GROUNDING:
            continue  # empty, duplicate, or not grounded in what the user wrote
        seen.add(key)
        sentence = text if text.endswith(".") else text + "."
        features.append(Feature(f"F{len(features) + 1}", text.rstrip("."), sentence, "llm"))
        if len(features) == MAX_FEATURES:
            break
    return features
