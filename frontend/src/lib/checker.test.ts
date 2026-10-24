import { describe, expect, it } from "vitest";

import { sentenceCount, shortTitle, totals } from "./checker";
import type { CheckHistoryItem } from "./types";

const item = (extra: Partial<CheckHistoryItem> = {}): CheckHistoryItem => ({
  run_id: "r",
  kind: "answer",
  title: "q",
  conversation_id: null,
  created_at: "2026-10-23T10:00:00Z",
  grounding_score: 1,
  counts: { supported: 2, partly: 0, contradicts: 0, not_found: 0 },
  rewritten: false,
  draft_flagged: 0,
  fixes: 0,
  ...extra,
});

describe("totals", () => {
  it("adds up what the checker found across answers and checks", () => {
    const t = totals([
      item(),
      item({ counts: { supported: 1, partly: 1, contradicts: 1, not_found: 2 }, rewritten: true, planted_caught: true, fixes: 1 }),
      item({ planted_caught: false }),
    ]);
    expect(t).toEqual({ items: 3, sentences: 9, flagged: 4, contradicted: 1, rewritten: 1, planted: { caught: 1, total: 2 }, edited: 1 });
  });
});

describe("sentenceCount", () => {
  it("counts full statements only", () => {
    expect(sentenceCount("The pump runs at night. Yes. The cells are cooled by water glycol.\nOk")).toBe(2);
  });
});

describe("shortTitle", () => {
  it("flattens and shortens", () => {
    expect(shortTitle("one   two\nthree", 40)).toBe("one two three");
    expect(shortTitle("x".repeat(20), 10)).toBe(`${"x".repeat(9)}…`);
  });
});
