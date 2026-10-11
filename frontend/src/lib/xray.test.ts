import { describe, expect, it } from "vitest";

import type { ClaimResult, VerificationAttempt } from "./verification";
import { checkedAgainst, countTones, type DemoInjection, draftHistory, highlightShared, injectionOutcome, overlap, plantedClaim, stem, toneOf } from "./xray";

const claim = (text: string, verdict: ClaimResult["verdict"], extra: Partial<ClaimResult> = {}): ClaimResult => ({
  index: 0, text, cited: ["E1"], verdict, score: 0.9, reason: "", supporting: [],
  misattributed: false, location: "answer", source_text: text, ...extra,
});

describe("toneOf", () => {
  it("colours by verdict, and a misattributed sentence is amber", () => {
    expect(toneOf(claim("a", "supported"))).toBe("ok");
    expect(toneOf(claim("a", "partially_supported"))).toBe("warn");
    expect(toneOf(claim("a", "supported", { misattributed: true }))).toBe("warn");
    expect(toneOf(claim("a", "unsupported"))).toBe("bad");
    expect(countTones([claim("a", "supported"), claim("b", "unsupported")])).toEqual({ ok: 1, warn: 0, bad: 1 });
  });
});

describe("checkedAgainst", () => {
  it("prefers the passage that supported the sentence, else what it cited", () => {
    expect(checkedAgainst(claim("a", "partially_supported", { cited: ["E1"], supporting: ["E3"] }))).toEqual(["E3"]);
    expect(checkedAgainst(claim("a", "unsupported", { cited: ["E2", "?"] }))).toEqual(["E2"]);
    expect(checkedAgainst(claim("a", "unsupported", { cited: [] }))).toEqual([]);
  });
});

describe("highlightShared", () => {
  it("marks the passage words the sentence uses, joining neighbours, and keeps the text intact", () => {
    const passage = "A controller adjusts the speed of the coolant pump based on core temperatures.";
    const pieces = highlightShared(passage, "The controller sets the coolant pump speed [E1].");
    expect(pieces.map((p) => p.text).join("")).toBe(passage);
    expect(pieces.filter((p) => p.shared).map((p) => p.text)).toEqual(["controller", "speed", "coolant pump"]);
  });

  it("matches simple word forms and ignores stop words and citation labels", () => {
    expect(stem("sensors")).toBe("sensor");
    expect(stem("controlled")).toBe("controll");
    const shared = highlightShared("The sensors are placed on each cell.", "Each sensor is placed [E1] on the cells.")
      .filter((p) => p.shared)
      .map((p) => p.text);
    expect(shared).toEqual(["sensors", "placed", "cell"]);
    expect(overlap("It is nuclear powered [E1].", "A battery pack with sensors.")).toBe(0);
  });
});

describe("draftHistory", () => {
  const attempt = (n: number, kept: boolean, claims?: ClaimResult[]): VerificationAttempt => ({
    attempt: n, grounding_score: kept ? 1 : 0.5, counts: { supported: 0, partially_supported: 0, unsupported: 0, misattributed: 0, contradicted: 0 },
    answer_text: "", kept, claims,
  });

  it("lists draft sentences that were flagged and dropped from the final answer", () => {
    const pump = claim("The pump runs [E1].", "supported");
    const mars = claim("It runs on Martian steam [E1].", "unsupported");
    const history = draftHistory([attempt(1, false, [pump, mars]), attempt(2, true, [pump])]);
    expect(history?.removed.map((c) => c.text)).toEqual(["It runs on Martian steam [E1]."]);
    expect(history?.final.attempt).toBe(2);
  });

  it("shows the discarded attempt as the draft when the first one was kept", () => {
    const history = draftHistory([attempt(1, true, []), attempt(2, false, [])]);
    expect([history?.final.attempt, history?.draft.attempt]).toEqual([1, 2]);
  });

  it("is empty without a regeneration or for answers stored before sentence verdicts were kept", () => {
    expect(draftHistory([attempt(1, true, [])])).toBeNull();
    expect(draftHistory([attempt(1, false), attempt(2, true)])).toBeNull();
  });
});

describe("demo injection", () => {
  const injection = (extra: Partial<DemoInjection> = {}): DemoInjection => ({
    kind: "changed_number", description: "changed a number", planted: "Cells stay below 135 °C [E1].",
    original: "Cells stay below 45 °C [E1].", checked: true, verdict: "unsupported", reason: "", caught: true,
    in_final_answer: false, ...extra,
  });

  it("finds the planted sentence whatever its citation", () => {
    const planted = claim("Cells stay below 135 °C [E2].", "unsupported");
    expect(plantedClaim([claim("Other [E1].", "supported"), planted], injection())).toBe(planted);
    expect(plantedClaim([planted], null)).toBeUndefined();
  });

  it("states the outcome honestly, including a miss", () => {
    expect(injectionOutcome(injection()).tone).toBe("ok");
    expect(injectionOutcome(injection({ caught: false, in_final_answer: true })).text).toMatch(/missed/);
    expect(injectionOutcome(injection({ in_final_answer: true })).tone).toBe("warn");
  });
});
