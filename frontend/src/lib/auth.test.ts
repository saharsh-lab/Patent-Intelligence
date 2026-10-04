import { describe, expect, it } from "vitest";

import { greeting, initials } from "./auth";

describe("auth helpers", () => {
  it("makes initials", () => {
    expect(initials("Ada Lovelace")).toBe("AL");
    expect(initials("  saharsh ")).toBe("S");
    expect(initials("Mary Ann Evans")).toBe("ME");
  });

  it("greets by time of day", () => {
    expect(greeting(new Date(2026, 0, 1, 9))).toBe("Good morning");
    expect(greeting(new Date(2026, 0, 1, 14))).toBe("Good afternoon");
    expect(greeting(new Date(2026, 0, 1, 21))).toBe("Good evening");
  });
});
