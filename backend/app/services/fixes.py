"""Fix one sentence of a stored answer: remove it, or rewrite it from its source.

These are the user's edits, not the system's output, so nothing the system wrote is lost:
the first fix keeps the original answer and its verdicts (answer["original"]), every fix is
listed (answer["fixes"]), and "restore" puts the original back. The claim_verifications
rows stay as the record of the system's own check. A rewrite is checked like any answer
sentence and is refused when the sources do not back it either.
"""

import re
import uuid
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import NotFoundError, ValidationFailedError
from app.core.ownership import visible
from app.llm.providers import ChatMessage, LLMProvider, visible_text
from app.models import AgentRun
from app.verification.checker import (
    Claim,
    explain,
    report_from_json,
    stored_premise,
    verify_against,
)
from app.verification.issues import _STOP, _WORD
from app.verification.verifiers import UNSUPPORTED, build_verifier

FixAction = Literal["remove", "rewrite", "restore"]

REWRITE_PROMPT = """\
You correct one sentence of an answer so that it says only what the evidence passages \
between <evidence> and </evidence> state.
Rules:
1. Keep the sentence's topic. Change, drop or add only what the passages require.
2. End the sentence with the label(s) of the passage(s) that support it, e.g. [E1].
3. Use only the passages, never your own knowledge.
4. If the passages say nothing on this topic, reply exactly: NONE
Reply with the corrected sentence only."""

_BULLET = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+")
_LABELS = re.compile(r"\[(E\d+)\]")
_FIRST_SENTENCE = re.compile(r"(?<=[.!?\]])\s+(?=[A-Z])")
MAX_PASSAGES = 3


class SentenceFixer:
    def __init__(self, session: Session, settings: Settings, llm: LLMProvider):
        self.session = session
        self.settings = settings
        self.llm = llm

    def fix(self, run_id: uuid.UUID, claim_index: int | None, action: FixAction) -> AgentRun:
        run = self.session.get(AgentRun, run_id)
        if run is None or not visible(run.query.owner_id):
            raise NotFoundError("Answer not found.")
        answer = dict(run.answer or {})
        if action == "restore":
            return self._restore(run, answer)
        verification = answer.get("verification")
        if run.status != "succeeded" or not verification or not run.answer_text:
            raise ValidationFailedError("Only a checked answer can be fixed.")
        claim = next(
            (
                c
                for c in verification["claims"]
                if c["index"] == claim_index and c.get("location", "answer") == "answer"
            ),
            None,
        )
        if claim is None:
            raise NotFoundError("That sentence is not in the answer any more.")
        written = _BULLET.sub("", claim.get("source_text") or claim["text"]).strip()
        if written not in run.answer_text:
            raise ValidationFailedError("That sentence is not in the answer any more.")

        if action == "remove":
            text = _without(run.answer_text, written)
            claims = [c for c in verification["claims"] if c is not claim]
            after, verdict, cited = None, None, []
        else:
            result = self._rewrite(claim, answer.get("evidence", []))
            after, verdict, cited = result.source_text, result.verdict, result.cited
            text = run.answer_text.replace(written, after, 1)
            claims = [asdict(result) if c is claim else c for c in verification["claims"]]

        answer.setdefault(
            "original",
            {
                "text": run.answer_text,
                "verification": verification,
                "grounding_score": run.grounding_score,
                "sentences": answer.get("sentences", []),
            },
        )
        report = report_from_json(verification | {"claims": claims})
        answer["verification"] = report.to_json()
        answer["text"] = text
        edited = claim.get("source_text") or claim["text"]
        answer["sentences"] = [
            s if s["text"] != edited else s | {"text": after, "citations": cited}
            for s in answer.get("sentences", [])
            if after or s["text"] != edited
        ]
        answer["fixes"] = [
            *answer.get("fixes", []),
            {
                "index": claim["index"],
                "action": action,
                "before": written,
                "after": after,
                "verdict": verdict,
                "at": datetime.now(UTC).isoformat(),
            },
        ]
        run.answer = answer
        run.answer_text = text
        run.grounding_score = report.grounding_score
        self.session.commit()
        return run

    def _restore(self, run: AgentRun, answer: dict) -> AgentRun:
        original = answer.pop("original", None)
        if original is None:
            raise ValidationFailedError("This answer has not been edited.")
        answer["text"] = original["text"]
        answer["verification"] = original["verification"]
        answer["sentences"] = original["sentences"]
        answer.pop("fixes", None)
        run.answer = answer
        run.answer_text = original["text"]
        run.grounding_score = original["grounding_score"]
        self.session.commit()
        return run

    def _rewrite(self, claim: dict, evidence: list[dict]):
        premise = {e["label"]: stored_premise(e) for e in evidence if e.get("label")}
        labels = _passages_for(claim, premise)
        if not labels:
            raise ValidationFailedError("No passage to rewrite this sentence from.")
        block = "\n\n".join(f"[{label}] {premise[label]}" for label in labels)
        reply = self.llm.complete(
            [
                ChatMessage("system", REWRITE_PROMPT),
                ChatMessage(
                    "user",
                    f"Sentence: {claim['text']}\n\n<evidence>\n{block}\n</evidence>",
                ),
            ],
            temperature=0.0,
            max_tokens=200,
        )
        sentence = " ".join(visible_text(reply.text).split())
        sentence = _FIRST_SENTENCE.split(sentence, maxsplit=1)[0].strip()
        if not sentence or sentence.upper().startswith("NONE"):
            raise ValidationFailedError(
                "The sources say nothing that could correct this sentence. Remove it instead."
            )
        cited = [label for label in _LABELS.findall(sentence) if label in premise]
        sentence = _LABELS.sub(lambda m: m.group(0) if m.group(1) in premise else "", sentence)
        checked = Claim(
            re.sub(r"\s*\[(?:E\d+|\?)\]", "", sentence).strip(), cited, "answer", sentence
        )
        verifier = build_verifier(
            self.settings.verifier_method, nli_model=self.settings.verifier_nli_model, llm=self.llm
        )
        result = explain(
            verify_against(
                verifier,
                [checked],
                premise,
                uncited_supported=self.settings.verifier_uncited_supported,
            ),
            premise,
        )[0]
        if result.verdict == UNSUPPORTED:
            raise ValidationFailedError(
                "The sources do not back a corrected version either. Remove the sentence instead."
            )
        result.index = claim["index"]
        return result


def _passages_for(claim: dict, premise: dict[str, str]) -> list[str]:
    """The passages the sentence was checked against, then the ones sharing most words."""
    chosen = [
        label
        for label in [*claim.get("supporting", []), *claim.get("cited", []), claim.get("closest")]
        if label in premise
    ]
    wanted = {w.lower() for w in _WORD.findall(claim["text"]) if w.lower() not in _STOP}
    ranked = sorted(
        premise, key=lambda lbl: -len(wanted & {w.lower() for w in _WORD.findall(premise[lbl])})
    )
    return list(dict.fromkeys(chosen + ranked))[:MAX_PASSAGES]


def _without(text: str, sentence: str) -> str:
    """The text with one sentence taken out, and no empty list item or gap left behind."""
    start = text.find(sentence)
    before, after = text[:start], text[start + len(sentence) :]
    if after.startswith(" "):
        after = after[1:]
    elif before.endswith(" "):
        before = before[:-1]
    out = re.sub(r"(?m)^[ \t]*(?:[-*•]|\d+[.)])[ \t]*\n?(?=\n|\Z)", "", before + after)
    return re.sub(r"\n{3,}", "\n\n", out).strip()
