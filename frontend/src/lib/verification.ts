// Claim-level verification results (backend: VerificationReport.to_json()).

export type Verdict = "supported" | "partially_supported" | "unsupported";

export interface ClaimResult {
  index: number;
  text: string;
  cited: string[];
  verdict: Verdict;
  score: number;
  reason: string;
  supporting: string[];
  misattributed: boolean;
  location: string;
  source_text: string;
}

export interface Verification {
  method: string;
  grounding_score: number | null;
  counts: Record<Verdict | "misattributed" | "contradicted", number>;
  claims: ClaimResult[];
  skipped: string[];
}

export interface VerificationAttempt {
  attempt: number;
  grounding_score: number | null;
  counts: Verification["counts"];
  answer_text: string;
  kept: boolean;
}

export type Segment = { text: string; claim?: ClaimResult };

/** Split answer text into pieces, marking the pieces that are verified claims. */
export function splitByClaims(text: string, claims: ClaimResult[]): Segment[] {
  const found: { start: number; end: number; claim: ClaimResult }[] = [];
  for (const claim of claims) {
    // claims from bullet lines carry the bullet; list items are rendered without it
    const needle = claim.source_text?.replace(/^\s*(?:[-*•]|\d+[.)])\s+/, "").trim();
    if (!needle) continue;
    const start = text.indexOf(needle);
    if (start >= 0 && !found.some((f) => start < f.end && start + needle.length > f.start)) {
      found.push({ start, end: start + needle.length, claim });
    }
  }
  found.sort((a, b) => a.start - b.start);
  const segments: Segment[] = [];
  let cursor = 0;
  for (const f of found) {
    if (f.start > cursor) segments.push({ text: text.slice(cursor, f.start) });
    segments.push({ text: text.slice(f.start, f.end), claim: f.claim });
    cursor = f.end;
  }
  if (cursor < text.length) segments.push({ text: text.slice(cursor) });
  return segments;
}

export const VERDICT_LABEL: Record<Verdict, string> = {
  supported: "Supported",
  partially_supported: "Partly supported",
  unsupported: "Unsupported",
};

export const VERDICT_STYLE: Record<Verdict, string> = {
  supported: "",
  partially_supported: "bg-warn-soft decoration-warn underline decoration-dotted underline-offset-4",
  unsupported: "bg-bad-soft decoration-bad underline decoration-wavy underline-offset-4",
};
