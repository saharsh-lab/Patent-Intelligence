import { describe, expect, it } from "vitest";

import { parseAnswer, parseInline, stripInterpretation } from "./citations";

describe("parseInline", () => {
  it("splits text, citations, invalid citations and bold", () => {
    expect(parseInline("The **pump** runs [E1][E2]. Made by Acme [?].")).toEqual([
      { kind: "text", text: "The " },
      { kind: "bold", text: "pump" },
      { kind: "text", text: " runs " },
      { kind: "citation", label: "E1" },
      { kind: "citation", label: "E2" },
      { kind: "text", text: ". Made by Acme " },
      { kind: "invalid-citation" },
      { kind: "text", text: "." },
    ]);
  });

  it("treats HTML in model output as plain text", () => {
    expect(parseInline("<img src=x onerror=alert(1)>")).toEqual([
      { kind: "text", text: "<img src=x onerror=alert(1)>" },
    ]);
  });

  it("leaves patent paragraph markers alone", () => {
    expect(parseInline("see ¶0011 and [0012]")).toEqual([{ kind: "text", text: "see ¶0011 and [0012]" }]);
  });
});

describe("parseAnswer", () => {
  it("builds paragraphs and bullet lists", () => {
    const blocks = parseAnswer("Intro line\ncontinues [E1].\n\n- first [E2]\n- second\n\n1. numbered");
    expect(blocks.map((b) => b.kind)).toEqual(["paragraph", "list", "list"]);
    expect(blocks[0]).toEqual({
      kind: "paragraph",
      inlines: [{ kind: "text", text: "Intro line\ncontinues " }, { kind: "citation", label: "E1" }, { kind: "text", text: "." }],
      raw: "Intro line\ncontinues [E1].",
    });
    expect(blocks[1].kind === "list" && blocks[1].items.length).toBe(2);
  });

  it("ignores empty input", () => {
    expect(parseAnswer("  \n\n ")).toEqual([]);
  });

  it("reads chat-style markdown: a list right after a line, numbered lists, headings", () => {
    const blocks = parseAnswer("Key points:\n- **Coil** [E1]\n- Q factor\n\n### How\n1. Measure\n2. Compare");
    expect(blocks.map((b) => b.kind)).toEqual(["paragraph", "list", "heading", "list"]);
    expect(blocks[1].kind === "list" && blocks[1].ordered).toBe(false);
    expect(blocks[2]).toMatchObject({ kind: "heading", level: 3, raw: "How" });
    expect(blocks[3].kind === "list" && [blocks[3].ordered, blocks[3].raws]).toEqual([true, ["Measure", "Compare"]]);
  });
});

describe("parseInline markdown", () => {
  it("reads italics and inline code but leaves snake_case and lone stars alone", () => {
    expect(parseInline("*fast* and `max_tokens` or _slow_; snake_case_name, 2 * 3")).toEqual([
      { kind: "italic", text: "fast" },
      { kind: "text", text: " and " },
      { kind: "code", text: "max_tokens" },
      { kind: "text", text: " or " },
      { kind: "italic", text: "slow" },
      { kind: "text", text: "; snake_case_name, 2 * 3" },
    ]);
  });
});

describe("stripInterpretation", () => {
  it("removes a trailing Interpretation paragraph", () => {
    expect(stripInterpretation("Fact [E1].\n\nInterpretation: guess.")).toBe("Fact [E1].");
  });
  it("removes an inline Interpretation sentence", () => {
    expect(stripInterpretation("Fact [E1]. Interpretation: guess.")).toBe("Fact [E1].");
  });
  it("keeps text without interpretation", () => {
    expect(stripInterpretation("The interpretation of claim 1 is broad [E1].")).toBe(
      "The interpretation of claim 1 is broad [E1].",
    );
  });
});
