// Hallucination X-ray: what the UI shows about each checked sentence.
// Pure helpers; the data comes from the backend's claim-level verification.

import type { ClaimResult, Verification, VerificationAttempt } from "@/lib/verification";

export type Tone = "ok" | "warn" | "bad";

/** Green: supported. Amber: partly supported or cited the wrong passage. Red: unsupported. */
export function toneOf(claim: ClaimResult): Tone {
  if (claim.verdict === "unsupported") return "bad";
  if (claim.verdict === "partially_supported" || claim.misattributed) return "warn";
  return "ok";
}

export const TONE_LABEL: Record<Tone, string> = {
  ok: "Supported by its source",
  warn: "Partly supported",
  bad: "Not found in the sources",
};

/** The passages a sentence was judged against: the one that supported it, or else the
 *  ones it cited (an unsupported sentence has no supporting passage). */
export function checkedAgainst(claim: ClaimResult): string[] {
  return claim.supporting.length ? claim.supporting : claim.cited.filter((l) => /^E\d+$/.test(l));
}

export function countTones(claims: ClaimResult[]): Record<Tone, number> {
  const out: Record<Tone, number> = { ok: 0, warn: 0, bad: 0 };
  for (const claim of claims) out[toneOf(claim)] += 1;
  return out;
}

// Words too common to say anything about whether a passage backs a sentence
const STOP = new Set(
  ("the and for with that this from are was were has have had its it's into onto than then them they " +
    "their there these those which what when where who whom whose will would can could may might " +
    "shall should does did not but also each such any all one two per via upon about over under " +
    "being been more most other some only same both between within without using used use").split(" "),
);

/** A rough word stem so "sensors" matches "sensor" and "controlled" matches "controls". */
export function stem(word: string): string {
  const w = word.toLowerCase();
  for (const suffix of ["ing", "ed", "es", "s"]) {
    if (w.length - suffix.length >= 4 && w.endsWith(suffix)) return w.slice(0, -suffix.length);
  }
  return w;
}

const WORD = /[\p{L}\p{N}][\p{L}\p{N}-]*/gu;

/** Content words of a sentence, stemmed (citation labels like [E2] removed). */
export function contentWords(text: string): Set<string> {
  const words = text.replace(/\[(?:E\d+|\?)\]/g, " ").match(WORD) ?? [];
  return new Set(words.filter((w) => (w.length >= 3 || /\d/.test(w)) && !STOP.has(w.toLowerCase())).map(stem));
}

export type Piece = { text: string; shared: boolean };

/** Split a passage so the words it shares with the sentence can be highlighted. This is a
 *  reading aid, not what the checker model looked at: the model judges meaning. */
export function highlightShared(passage: string, sentence: string): Piece[] {
  const wanted = contentWords(sentence);
  const pieces: Piece[] = [];
  let cursor = 0;
  for (const match of passage.matchAll(WORD)) {
    const word = match[0];
    const start = match.index ?? 0;
    const shared = (word.length >= 3 || /\d/.test(word)) && !STOP.has(word.toLowerCase()) && wanted.has(stem(word));
    if (!shared) continue;
    const gap = passage.slice(cursor, start);
    const last = pieces.at(-1);
    if (last?.shared && /^ $/.test(gap)) {
      last.text += gap + word; // one highlight for neighbours: "coolant pump"
    } else {
      if (gap) pieces.push({ text: gap, shared: false });
      pieces.push({ text: word, shared: true });
    }
    cursor = start + word.length;
  }
  if (cursor < passage.length) pieces.push({ text: passage.slice(cursor), shared: false });
  return pieces;
}

/** Share of the sentence's content words that appear in the passage (0–1). */
export function overlap(sentence: string, passage: string): number {
  const wanted = contentWords(sentence);
  if (!wanted.size) return 0;
  const have = contentWords(passage);
  let n = 0;
  for (const w of wanted) if (have.has(w)) n += 1;
  return n / wanted.size;
}

export interface DraftHistory {
  draft: VerificationAttempt;
  final: VerificationAttempt;
  /** Draft sentences the checker flagged that are gone from the final answer */
  removed: ClaimResult[];
}

/** First draft vs the answer shown, when the answer was regenerated after the check. */
export function draftHistory(attempts: VerificationAttempt[] | undefined): DraftHistory | null {
  if (!attempts || attempts.length < 2) return null;
  const final = attempts.find((a) => a.kept) ?? attempts.at(-1)!;
  const draft = attempts[0] === final ? attempts[1] : attempts[0];
  if (!draft.claims || !final.claims) return null; // answers stored before the X-ray existed
  const finalText = new Set(final.claims.map((c) => c.text.trim()));
  const removed = draft.claims.filter((c) => toneOf(c) !== "ok" && !finalText.has(c.text.trim()));
  return { draft, final, removed };
}

export function answerClaims(verification: Verification | null | undefined): ClaimResult[] {
  return (verification?.claims ?? []).filter((c) => c.location === "answer");
}

/** Demo mode (Phase 14): the false sentence planted in the first draft, and what the
 *  checker made of it. Backend: app/agents/demo_injection.py. */
export interface DemoInjection {
  kind: "changed_number" | "reversed_relation" | "invented_detail";
  description: string;
  planted: string;
  original: string | null;
  checked: boolean;
  verdict: ClaimResult["verdict"] | null;
  reason: string | null;
  caught: boolean;
  in_final_answer: boolean;
}

const plainText = (text: string) => text.replace(/\s*\[(?:E\d+|\?)\]/g, "").trim().replace(/\.$/, "");

/** The claim that is the planted sentence, if this list has it. */
export function plantedClaim(claims: ClaimResult[], injection: DemoInjection | null | undefined): ClaimResult | undefined {
  if (!injection) return undefined;
  const target = plainText(injection.planted);
  return claims.find((c) => plainText(c.text) === target || plainText(c.text).includes(target));
}

/** One line on how the checker test went, honest about a miss. */
export function injectionOutcome(injection: DemoInjection): { tone: Tone; text: string } {
  if (!injection.checked) return { tone: "warn", text: "The planted sentence was not checked (the answer changed before checking)." };
  if (!injection.caught) return { tone: "bad", text: "The checker missed it: the planted sentence passed as supported." };
  if (injection.in_final_answer)
    return { tone: "warn", text: "The checker flagged it, but it is still in the answer below (marked)." };
  return { tone: "ok", text: "The checker caught it, and the answer was rewritten without it." };
}
