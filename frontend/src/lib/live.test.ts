import { describe, expect, it } from "vitest";

import { checkSummary, continues, headline, nextCount, plainSentence, stageOf, visibleDraft, type Live } from "@/lib/live";
import type { ClaimResult } from "@/lib/verification";

const live = (over: Partial<Live>): Live => ({
  phase: "searching",
  attempt: 0,
  draft: "",
  sources: [],
  evidence: [],
  claims: [],
  flagged: [],
  general: false,
  ...over,
});
const tool = { kind: "tool", name: "search_web", label: "Searching the web", status: "running", detail: "", why: "", at_ms: 0, ms: null };

const claim = (verdict: ClaimResult["verdict"], over: Partial<ClaimResult> = {}): ClaimResult => ({
  index: 0,
  text: "x",
  cited: [],
  verdict,
  score: 1,
  reason: "",
  supporting: [],
  misattributed: false,
  location: "answer",
  source_text: "x",
  ...over,
});

describe("live answer", () => {
  it("follows the agent through its stages", () => {
    expect(stageOf(undefined)).toBe(0);
    expect(stageOf({ steps: [tool as never], live: null })).toBe(1);
    expect(stageOf({ steps: [], live: live({ phase: "writing", attempt: 1 }) })).toBe(2);
    expect(stageOf({ steps: [], live: live({ phase: "rewriting" }) })).toBe(2);
    expect(stageOf({ steps: [], live: live({ phase: "checked" }) })).toBe(3);
  });

  it("says what is happening in plain words", () => {
    const source = { kind: "web", label: "en.wikipedia.org", title: "Inductive charging", url: null };
    expect(headline({ steps: [tool as never], live: live({ sources: [source] }) })).toBe("Reading 1 source");
    expect(headline({ steps: [], live: live({ phase: "writing", attempt: 2 }) })).toBe("Rewriting with more evidence");
    const claims = [claim("supported"), claim("unsupported"), claim("supported", { misattributed: true })];
    expect(headline({ steps: [], live: live({ phase: "checked", claims: claims as never }) })).toBe("1 of 3 sentences supported · 2 flagged");
  });

  it("says when no source had the answer", () => {
    expect(headline({ steps: [], live: live({ phase: "writing", attempt: 1, general: true }) })).toMatch(/general knowledge/);
  });

  it("counts only the answer's sentences", () => {
    expect(checkSummary([claim("supported"), claim("supported", { location: "cell:a:b" })])).toEqual({ supported: 1, total: 1, flagged: 0 });
    expect(checkSummary([])).toBeNull();
  });

  it("never shows half a citation while typing", () => {
    expect(visibleDraft("The pump runs [E12].", 15)).toBe("The pump runs ");
    expect(visibleDraft("The pump runs [E12].", 17)).toBe("The pump runs ");
    expect(visibleDraft("A **bold** word", 3)).toBe("A ");
    expect(visibleDraft("The pump runs [E12].", 20)).toBe("The pump runs [E12].");
  });

  it("types faster the further behind it is, and starts over on a new draft", () => {
    expect(nextCount(0, 5)).toBe(1);
    expect(nextCount(0, 200)).toBe(20);
    expect(nextCount(200, 200)).toBe(200);
    expect(continues("The pump runs", "The pump runs at full speed")).toBe(true);
    expect(continues("The pump runs at full speed", "Cooling uses a pump")).toBe(false);
  });

  it("shows flagged sentences without their source numbers", () => {
    expect(plainSentence("The pump is purple [E1][E3].")).toBe("The pump is purple.");
  });
});
