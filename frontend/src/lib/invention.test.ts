import { describe, expect, it } from "vitest";

import { cellIndex, shortNames, type Candidate, type Cell } from "./invention";

describe("invention helpers", () => {
  it("indexes cells by feature and candidate", () => {
    const cells = [
      { feature: "F1", candidate: "document:a", verdict: "disclosed" },
      { feature: "F2", candidate: "document:a", verdict: "not_found" },
    ] as Cell[];
    const index = cellIndex(cells);
    expect(index.get("F1|document:a")?.verdict).toBe("disclosed");
    expect(index.get("F3|document:a")).toBeUndefined();
  });

  it("names columns D1, D2 in display order", () => {
    const candidates = [{ key: "patent:x" }, { key: "document:y" }] as Candidate[];
    expect(shortNames(candidates)).toEqual({ "patent:x": "D1", "document:y": "D2" });
  });
});
