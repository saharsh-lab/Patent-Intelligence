import { describe, expect, it } from "vitest";

import { formatBytes, formatMs, formatPercent, locationLabel, sectionLabel } from "./format";

describe("formatters", () => {
  it("formats sizes, durations and percentages", () => {
    expect(formatBytes(512)).toBe("512 B");
    expect(formatBytes(3727)).toBe("3.6 KB");
    expect(formatBytes(5 * 1024 * 1024)).toBe("5.0 MB");
    expect(formatMs(840)).toBe("840 ms");
    expect(formatMs(20350)).toBe("20.4 s");
    expect(formatMs(null)).toBe("—");
    expect(formatPercent(0.75)).toBe("75%");
    expect(formatPercent(null)).toBe("—");
  });

  it("labels sections and locations", () => {
    expect(sectionLabel("technical_field")).toBe("Technical field");
    expect(sectionLabel(null)).toBe("Unsectioned");
    expect(locationLabel({ source_label: "a.pdf", section: "claims", claim_number: 3, page_number: 4 })).toBe(
      "a.pdf · Claim 3 · p. 4",
    );
    expect(locationLabel({ source_label: "a.txt", section: "abstract" })).toBe("a.txt · Abstract");
  });
});
