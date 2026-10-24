// The Checker page: pure helpers. Backend: app/api/routes/checker.py.
import type { CheckHistoryItem } from "./types";

export interface CheckerTotals {
  /** Chat answers and text checks with at least one checked sentence */
  items: number;
  sentences: number;
  flagged: number;
  contradicted: number;
  /** Answers the checker sent back to be rewritten before they were shown */
  rewritten: number;
  planted: { caught: number; total: number };
  edited: number;
}

export function totals(history: CheckHistoryItem[]): CheckerTotals {
  const out: CheckerTotals = { items: history.length, sentences: 0, flagged: 0, contradicted: 0, rewritten: 0, planted: { caught: 0, total: 0 }, edited: 0 };
  for (const item of history) {
    const { supported, partly, contradicts, not_found } = item.counts;
    out.sentences += supported + partly + contradicts + not_found;
    out.flagged += partly + contradicts + not_found;
    out.contradicted += contradicts;
    if (item.rewritten) out.rewritten += 1;
    if (item.planted_caught !== null && item.planted_caught !== undefined) {
      out.planted.total += 1;
      if (item.planted_caught) out.planted.caught += 1;
    }
    if (item.fixes > 0) out.edited += 1;
  }
  return out;
}

/** About how many sentences a text has (for "Checking 6 sentences…"). */
export function sentenceCount(text: string): number {
  return text
    .split(/(?<=[.!?])\s+|\n+/)
    .filter((s) => s.trim().split(/\s+/).length >= 4).length;
}

/** A short title for a past check: the start of its text. */
export function shortTitle(text: string, max = 90): string {
  const flat = text.replace(/\s+/g, " ").trim();
  return flat.length > max ? `${flat.slice(0, max - 1).trimEnd()}…` : flat;
}
