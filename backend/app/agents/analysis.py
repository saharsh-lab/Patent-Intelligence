"""Step 1 of the agent: understand what the question asks for.

Output is a `QueryAnalysis`: the intent, any patent numbers, a requested section
or claim, search keywords, and whether it asks for a legal opinion.

Two analysers:
- rules: regular expressions and keyword cues. Free, instant, deterministic.
- llm:   asks the LLM for a JSON classification. Better at paraphrases
         ("anything out there like my invention?"). Falls back to rules if the
         reply is not valid JSON.

Safety: the LLM may only *classify*. Patent numbers are accepted only if they
literally appear in the question, so the planner can't invent a patent to fetch.
"""

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from typing import Literal

from app.llm.providers import ChatMessage, LLMProvider
from app.patents.numbers import parse_publication_number

logger = logging.getLogger(__name__)

Intent = Literal["document_qa", "patent_lookup", "find_similar", "compare", "out_of_scope"]
INTENTS: tuple[str, ...] = (
    "document_qa",
    "patent_lookup",
    "find_similar",
    "compare",
    "out_of_scope",
)
SECTIONS = ("abstract", "claims", "description", "background", "summary", "technical_field")

_NUMBER = re.compile(
    r"\b(EP|US|WO|XX|JP|CN|DE|GB|FR|KR|CA|AU)[\s-]?(\d[\d\s,/]{4,}\d)\s?([ABCUT]\d?)?\b",
    re.IGNORECASE,
)
_CLAIM = re.compile(r"\bclaims?\s+(\d{1,3})\b", re.IGNORECASE)
_COMPARE = re.compile(
    r"\b(compare|comparison|contrast|differences?|differ|versus|vs\.?|similarities)\b", re.I
)
_SIMILAR = re.compile(
    r"\b(similar|prior art|related patents?|other patents|patents like|comparable|"
    r"find patents|search for patents|existing patents|competing|"
    # topic searches in the patent databases: "latest patents on X", "patents about X"
    r"(latest|recent|new|newest) patents|patents (on|about|regarding|covering|related to)|"
    r"(show|list|get|give)( me)? (some |the )?patents)\b",
    re.IGNORECASE,
)
# Wording that can justify a similar-patent search even when the rules don't see it
# ("Is anything out there like my invention?")
_SIMILAR_HINT = re.compile(
    r"\b(similar|like|prior art|patents|existing|related|comparable|competitors?|alternatives?)\b",
    re.IGNORECASE,
)
_LEGAL = re.compile(
    r"\b(infring\w*|invalid\w*|valid|validity|enforceab\w*|freedom to operate|fto|lawsuit|"
    r"sue|legal advice|patentab\w*|novelty opinion)\b",
    re.IGNORECASE,
)
# "my patent", "my battery patent", "this uploaded document", "these two documents"
# (up to 3 words in between)
_SCOPE_REFERENCE = re.compile(
    r"\b(this|these|both|my|our|the uploaded|uploaded|attached|current|selected)\s+"
    r"(?:[\w-]+\s+){0,3}?(patent|document|invention|application|file|idea|design)s?\b",
    re.IGNORECASE,
)
_SECTION_WORDS = {
    "abstract": "abstract",
    "background": "background",
    "summary": "summary",
    "technical field": "technical_field",
    "detailed description": "description",
    "description": "description",
}
_STOPWORDS = set(
    (
        "a an and are as at be by can do does for from has have how i in into is it its me my "
        "of on or our patent patents that the their this to was what when where which who why "
        "will with find search show list any some there about like similar compare other "
        "invention uploaded document please claim claims add adds describe explain summarize "
        "summarise tell infringe infringes infringement valid validity "
        "related recent latest new newest regarding covering give get all"
    ).split()
)


@dataclass
class QueryAnalysis:
    intent: Intent
    publication_numbers: list[str] = field(default_factory=list)
    section: str | None = None
    claim_number: int | None = None
    search_keywords: str = ""
    legal_question: bool = False
    refers_to_scope: bool = False  # "this patent", "my invention"
    analyzer: str = "rules"  # rules | llm | llm_fallback_rules

    def to_json(self) -> dict:
        return asdict(self)


def find_publication_numbers(text: str) -> list[str]:
    numbers = []
    for match in _NUMBER.finditer(text):
        try:
            numbers.append(parse_publication_number(match.group(0)).normalized)
        except ValueError:
            continue
    return list(dict.fromkeys(numbers))


def asks_to_compare(question: str) -> bool:
    return bool(_COMPARE.search(question))


def keywords_from_text(text: str, limit: int = 4) -> str:
    """Crude keyword extraction: content words, longest (most specific) first."""
    words = [w for w in re.findall(r"[a-zA-Z][a-zA-Z\-]{2,}", text.lower()) if w not in _STOPWORDS]
    unique = list(dict.fromkeys(words))
    ranked = sorted(unique, key=lambda w: (-len(w), unique.index(w)))[:limit]
    return " ".join(sorted(ranked, key=unique.index))


def analyze_rules(question: str) -> QueryAnalysis:
    numbers = find_publication_numbers(question)
    claim = _CLAIM.search(question)
    section = None
    lowered = question.lower()
    for phrase, name in _SECTION_WORDS.items():
        if re.search(rf"\b{phrase}\b", lowered):
            section = name
            break
    if claim or re.search(r"\bclaims?\b", lowered):
        section = "claims"
    refers = bool(_SCOPE_REFERENCE.search(question))

    legal = bool(_LEGAL.search(question))
    if _COMPARE.search(question) and (len(numbers) >= 2 or (numbers and refers) or refers):
        intent: Intent = "compare"
    elif legal and numbers and (refers or len(numbers) >= 2):
        # "Does my patent infringe X?" → answer with a technical comparison + disclaimer
        intent = "compare"
    elif _SIMILAR.search(question):
        intent = "find_similar"
    elif numbers:
        intent = "patent_lookup"
    else:
        intent = "document_qa"

    return QueryAnalysis(
        intent=intent,
        publication_numbers=numbers,
        section=section,
        claim_number=int(claim.group(1)) if claim else None,
        search_keywords=keywords_from_text(_NUMBER.sub(" ", question)),
        legal_question=legal,
        refers_to_scope=refers,
    )


_PLANNER_PROMPT = """\
You classify questions sent to a patent research assistant. Reply with ONLY a JSON object:
{"intent": "...", "publication_numbers": [], "section": null, "claim_number": null,
 "search_keywords": "", "legal_question": false}

intent is one of:
- "document_qa": a question answerable from the user's uploaded/imported patents
- "patent_lookup": asks about one specific patent identified by its publication number
- "find_similar": asks to find other patents similar/related to an invention (prior art search)
- "compare": asks to compare two or more patents/inventions
- "out_of_scope": not about patents or technology at all

section: null or one of "abstract", "claims", "description", "background", "summary".
claim_number: the claim number if a specific claim is asked about, else null.
search_keywords: 2-5 technical words to search patent databases with (empty if not useful).
legal_question: true if the user asks about infringement, validity or other legal opinions.
publication_numbers: copy any patent numbers exactly as written in the question."""


def analyze_llm(question: str, llm: LLMProvider) -> QueryAnalysis:
    rules = analyze_rules(question)
    try:
        response = llm.complete(
            [ChatMessage("system", _PLANNER_PROMPT), ChatMessage("user", question)],
            temperature=0.0,
            max_tokens=200,
        )
        data = json.loads(re.search(r"\{.*\}", response.text, re.DOTALL).group(0))
        if not isinstance(data, dict):
            raise ValueError("not a JSON object")
    except Exception as exc:  # noqa: BLE001 - any failure falls back to rules
        logger.info("LLM query analysis failed (%s); using rules", type(exc).__name__)
        rules.analyzer = "llm_fallback_rules"
        return rules

    intent = data.get("intent")
    analyzer = "llm"
    if intent not in INTENTS:
        # Observed: Qwen3 answered intent "legal_question". Keep the LLM's other fields,
        # take the intent from the rules.
        intent = rules.intent
        analyzer = "llm_rules_intent"

    if (
        intent == "find_similar"
        and rules.intent != "find_similar"
        and not _SIMILAR_HINT.search(question)
    ):
        # Observed (Phase 10, real patents): Qwen3 labelled 7 plain lookups ("Which kinds of
        # pumps can be used...?") as similar-patent searches, so the agent looked for
        # external patents and then abstained. Like sections, this intent needs wording
        # from the user.
        intent = rules.intent
        analyzer = "llm_similar_override"

    if rules.intent == "find_similar" and intent in ("document_qa", "out_of_scope"):
        # Explicit wording ("find patents about…", "latest patents on…") asks for the
        # patent databases; answering from the local library alone ignores the request.
        intent = "find_similar"
        analyzer = "llm_search_override"

    if intent == "out_of_scope":
        # Observed (Phase 9, Experiment A): Qwen3 called a plain technical question about
        # an uploaded document out of scope, so the agent refused without searching.
        # A refusal must come from evidence (the sufficiency gate), not from a classifier.
        intent = rules.intent
        analyzer = "llm_scope_override"

    # Read a section directly only when the question names one. Observed: the LLM set
    # section="description" for ordinary questions, skipping search (and once missing
    # the answer). Like publication numbers, sections and claim numbers must really
    # occur in the question.
    section = None
    if rules.section is not None:
        section = data.get("section") if data.get("section") in SECTIONS else rules.section
    claim = rules.claim_number
    keywords = data.get("search_keywords")
    if intent == "find_similar" and rules.intent == "find_similar" and rules.search_keywords:
        keywords = rules.search_keywords  # without "latest", "patents", "related", …
    return QueryAnalysis(
        intent=intent,
        # Only numbers that really occur in the question (the LLM may not invent targets)
        publication_numbers=rules.publication_numbers,
        section=section,
        claim_number=claim,
        search_keywords=keywords.strip()
        if isinstance(keywords, str) and keywords.strip()
        else rules.search_keywords,
        legal_question=bool(data.get("legal_question")) or rules.legal_question,
        refers_to_scope=rules.refers_to_scope,
        analyzer=analyzer,
    )
