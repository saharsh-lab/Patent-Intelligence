import { describe, expect, it } from "vitest";

import { bestIndex, diffTone, formatDiff, formatMetric, type Comparison, type Stat } from "./evaluation";

const stat = (mean: number | null, n = 5): Stat => ({ n, mean, ci_low: null, ci_high: null });

describe("formatMetric", () => {
  it("formats each metric kind", () => {
    expect(formatMetric(0.8333, "percent")).toBe("83.3%");
    expect(formatMetric(1520, "ms")).toBe("1.5 s");
    expect(formatMetric(0.5, "ratio")).toBe("0.500");
    expect(formatMetric(686.4, "tokens")).toBe("686.4");
    expect(formatMetric(null, "percent")).toBe("—");
  });

  it("shows percentage differences as percentage points", () => {
    expect(formatDiff(0.125, "percent")).toBe("+12.5 pp");
    expect(formatDiff(-30, "ms")).toBe("−30 ms");
  });
});

describe("bestIndex", () => {
  it("respects the metric's direction", () => {
    expect(bestIndex([stat(0.5), stat(0.9)], true)).toBe(1);
    expect(bestIndex([stat(120), stat(80)], false)).toBe(1);
  });

  it("has no best for ties, descriptive metrics, or missing values", () => {
    expect(bestIndex([stat(0.5), stat(0.5)], true)).toBeNull();
    expect(bestIndex([stat(0.5), stat(0.9)], null)).toBeNull();
    expect(bestIndex([stat(0.5), stat(null, 0)], true)).toBeNull();
  });
});

describe("diffTone", () => {
  const c = (mean_diff: number, clear: boolean) => ({ mean_diff, clear }) as Comparison;
  it("colours only clear differences, by direction", () => {
    expect(diffTone(c(0.2, true), true)).toBe("ok");
    expect(diffTone(c(0.2, true), false)).toBe("bad");
    expect(diffTone(c(0.2, false), true)).toBeNull();
  });
});
