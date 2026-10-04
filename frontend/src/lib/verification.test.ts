import { describe, expect, it } from "vitest";

import { type ClaimResult, splitByClaims } from "./verification";

const claim = (source_text: string, verdict: ClaimResult["verdict"]): ClaimResult => ({
  index: 0, text: source_text, cited: [], verdict, score: 0, reason: "", supporting: [],
  misattributed: false, location: "answer", source_text,
});

describe("splitByClaims", () => {
  it("marks claim sentences and keeps the text in between", () => {
    const text = "Intro. The pump runs [E1]. It is nuclear powered [E1]. End.";
    const segments = splitByClaims(text, [
      claim("It is nuclear powered [E1].", "unsupported"),
      claim("The pump runs [E1].", "supported"),
    ]);
    expect(segments.map((s) => [s.text, s.claim?.verdict])).toEqual([
      ["Intro. ", undefined],
      ["The pump runs [E1].", "supported"],
      [" ", undefined],
      ["It is nuclear powered [E1].", "unsupported"],
      [" End.", undefined],
    ]);
    expect(segments.map((s) => s.text).join("")).toBe(text);
  });

  it("ignores claims not found in the text", () => {
    expect(splitByClaims("Hello.", [claim("Missing.", "supported")])).toEqual([{ text: "Hello." }]);
  });
});
