"""Turn an answer into checkable claims, verify them, and compute a grounding score.

Claims are the answer's sentences (and, for comparisons, the table cells and the
similarity/difference points). Each claim is checked:

1. against the passages it cites   → supported / partially / unsupported
2. if not supported: against ALL other evidence passages
   → if another passage supports it, the claim is true but *misattributed*
     (cited the wrong passage); it counts as partially supported.

Skipped (not factual claims about the evidence): disclaimers ("I cannot assess
validity…"), statements about missing evidence, and the "Interpretation:" paragraph,
which the UI already labels as the model's own reasoning.

    grounding score = (supported + 0.5 × partially supported) / checked claims
"""

import re
from dataclasses import asdict, dataclass, field

from app.rag.generation import EvidenceItem, ParsedAnswer
from app.verification.verifiers import PARTIAL, SUPPORTED, UNSUPPORTED, Verifier

_META = re.compile(
    r"^\s*(i cannot|i can't|i can not|the evidence (does not|doesn't|provides no)|there is no "
    r"(information|evidence)|no (information|evidence)|not stated|this (is|was) (a )?technical"
    r"|note:|disclaimer)",
    re.IGNORECASE,
)
_CITATION = re.compile(r"\s*\[(?:E\d+|\?)\]")


@dataclass
class ClaimResult:
    index: int
    text: str
    cited: list[str]
    verdict: str
    score: float
    reason: str
    supporting: list[str] = field(default_factory=list)  # labels that support it
    misattributed: bool = False  # supported only by passages it did not cite
    location: str = "answer"  # answer | cell:<aspect>:<source> | similarity | difference
    source_text: str = ""  # the sentence exactly as written in the answer (for highlighting)


@dataclass
class VerificationReport:
    method: str
    claims: list[ClaimResult]
    skipped: list[str] = field(default_factory=list)

    @property
    def grounding_score(self) -> float | None:
        if not self.claims:
            return None
        points = {SUPPORTED: 1.0, PARTIAL: 0.5, UNSUPPORTED: 0.0}
        return round(sum(points[c.verdict] for c in self.claims) / len(self.claims), 4)

    def counts(self) -> dict[str, int]:
        out = {SUPPORTED: 0, PARTIAL: 0, UNSUPPORTED: 0}
        for claim in self.claims:
            out[claim.verdict] += 1
        out["misattributed"] = sum(c.misattributed for c in self.claims)
        out["contradicted"] = sum("contradicted" in c.reason for c in self.claims)
        return out

    def unsupported(self) -> list[ClaimResult]:
        return [c for c in self.claims if c.verdict == UNSUPPORTED]

    def to_json(self) -> dict:
        return {
            "method": self.method,
            "grounding_score": self.grounding_score,
            "counts": self.counts(),
            "claims": [asdict(c) for c in self.claims],
            "skipped": self.skipped,
        }


@dataclass
class Claim:
    text: str
    cited: list[str]
    location: str = "answer"
    source_text: str = ""


def claims_from_answer(parsed: ParsedAnswer) -> tuple[list[Claim], list[str]]:
    claims, skipped = [], []
    for sentence in parsed.sentences:
        text = _CITATION.sub("", sentence.text).strip().lstrip("-*• ").strip()
        if not text or _META.match(text) or len(text.split()) < 4:
            skipped.append(text)
            continue
        claims.append(Claim(text, list(sentence.citations), source_text=sentence.text))
    return claims, skipped


def claims_from_comparison(comparison: dict) -> list[Claim]:
    claims = []
    for aspect, row in comparison["cells"].items():
        for source_key, cell in row.items():
            if cell["text"] != "Not stated in the evidence" and len(cell["text"].split()) >= 3:
                claims.append(Claim(cell["text"], cell["citations"], f"cell:{aspect}:{source_key}"))
    for kind in ("similarities", "differences"):
        for point in comparison[kind]:
            # extractive term lists ("All sources mention: …") are not prose claims
            if not point["text"].startswith(("All sources mention", "Only ")):
                location = "similarity" if kind == "similarities" else "difference"
                claims.append(Claim(point["text"], point["citations"], location))
    return claims


def premise_for(item: EvidenceItem) -> str:
    """Passage text with its location, e.g. "Source: battery.txt, claim 3." + text.

    Observed: without the location, NLI could not link "Claim 3 adds X" to a passage
    that starts "3. The system of claim 1, wherein X" and judged it unsupported.
    """
    location = re.sub(r"^\[E\d+\]\s*", "", item.header).replace(" · ", ", ")
    return f"Source: {location}.\n{item.passage.chunk.text}"


def verify_claims(
    verifier: Verifier, claims: list[Claim], evidence: list[EvidenceItem]
) -> list[ClaimResult]:
    premise = {item.label: premise_for(item) for item in evidence}
    labels = list(premise)

    # Pass 1: each claim against the passages it cites — one by one, and (when it cites
    # several) all of them together, since a claim may combine facts from two passages.
    cited_sets = [[lbl for lbl in c.cited if lbl in premise] for c in claims]
    candidates: list[list[tuple[list[str], str]]] = []
    for cited in cited_sets:
        options = [([lbl], premise[lbl]) for lbl in cited]
        if len(cited) > 1:
            options.append((cited, "\n\n".join(premise[lbl] for lbl in cited)))
        candidates.append(options)
    first = verifier.judge([c.text for c in claims], [[t for _, t in o] for o in candidates])

    # Pass 2: claims not supported by their citations → against all other passages
    retry = [i for i, j in enumerate(first) if j.verdict != SUPPORTED]
    others = [[lbl for lbl in labels if lbl not in cited_sets[i]] for i in retry]
    second = (
        verifier.judge(
            [claims[i].text for i in retry], [[premise[lbl] for lbl in o] for o in others]
        )
        if retry
        else []
    )
    second_by_claim = dict(zip(retry, zip(second, others, strict=True), strict=True))

    results = []
    for index, (claim, judgement, options) in enumerate(
        zip(claims, first, candidates, strict=True)
    ):
        cited = cited_sets[index]
        verdict, score, reason = judgement.verdict, judgement.score, judgement.reason
        supporting = (
            list(options[judgement.best_passage][0])
            if (judgement.best_passage is not None and verdict != UNSUPPORTED)
            else []
        )
        misattributed = False
        if index in second_by_claim:
            other, other_labels = second_by_claim[index]
            if other.verdict == SUPPORTED and other.best_passage is not None:
                found = other_labels[other.best_passage]
                misattributed = True
                verdict, score = PARTIAL, max(score, 0.5)
                supporting = [found]
                reason = (
                    f"supported by {found}, which it did not cite"
                    if cited
                    else f"uncited; supported by {found}"
                )
        if not cited and not misattributed and verdict == UNSUPPORTED:
            reason = "no citation, and no passage supports it"
        results.append(
            ClaimResult(
                index,
                claim.text,
                claim.cited,
                verdict,
                score,
                reason,
                supporting,
                misattributed,
                claim.location,
                claim.source_text,
            )
        )
    return results


def verify_answer(
    verifier: Verifier,
    parsed: ParsedAnswer,
    evidence: list[EvidenceItem],
    comparison: dict | None = None,
) -> VerificationReport:
    """Verify an answer (or a comparison table) against the evidence it was built from."""
    if comparison is not None:
        claims, skipped = claims_from_comparison(comparison), []
    else:
        claims, skipped = claims_from_answer(parsed)
    results = verify_claims(verifier, claims, evidence) if claims else []
    return VerificationReport(verifier.name, results, skipped)


def regeneration_instructions(report: VerificationReport) -> str:
    bad = "\n".join(f"- {c.text}" for c in report.unsupported()[:5])
    return (
        "A checker found that these statements in your previous answer are NOT supported "
        f"by the evidence:\n{bad}\n"
        "Write a new answer that keeps only statements the evidence supports, each with its "
        "citation. Remove or correct the statements above; do not repeat them unless a "
        "passage now supports them."
    )
