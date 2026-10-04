import { describe, expect, it } from "vitest";

import { safeNext } from "./AuthForm";

describe("safeNext", () => {
  it("allows internal paths only", () => {
    expect(safeNext("/chat/42")).toBe("/chat/42");
    expect(safeNext("//evil.example")).toBe("/");
    expect(safeNext("https://evil.example")).toBe("/");
    expect(safeNext("/login")).toBe("/");
    expect(safeNext(null)).toBe("/");
  });
});
