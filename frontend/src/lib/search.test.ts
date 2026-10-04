import { afterEach, describe, expect, it, vi } from "vitest";

import { SUGGESTIONS, SearchError, demoResult, describeError, followUpSuggestions, runTurn, normalizeResult, plainAnswer, toNumberedCitations, tokenizeAnswer } from "./search";

const evidence = (over: Record<string, unknown>) => ({
  label: "E1",
  cited: true,
  chunk_id: "c1",
  document_id: null,
  patent_id: "p1",
  source_label: "US10804750B2",
  source_type: "epo",
  source_url: "https://worldwide.espacenet.com/x",
  source_title: "Q-factor detection method",
  section: "claims",
  claim_number: 1,
  page_number: null,
  text: "A method comprising…",
  rank: 1,
  method: "hybrid",
  score: 0.03,
  vector_similarity: 0.71,
  keyword_score: 0.1,
  rerank_score: null,
  ...over,
});

describe("normalizeResult", () => {
  it("maps the backend AskResponse to numbered sources", () => {
    const result = normalizeResult(
      {
        status: "succeeded",
        answer: "It measures Q [E2][E1]. Unknown [?].\n\nInterpretation: guess.",
        interpretation: "guess.",
        legal_question: false,
        evidence: [
          evidence({ label: "E2", chunk_id: "c2", rank: 2, claim_number: null, section: "abstract" }),
          evidence({}),
          evidence({ label: null, cited: false, chunk_id: "c3", rank: 3 }),
        ],
      },
      "q",
    );
    expect(result.status).toBe("answered");
    expect(result.answer).toBe("It measures Q [2][1]. Unknown.");
    expect(result.sources.map((s) => s.id)).toEqual([1, 2]);
    expect(result.sources[0]).toMatchObject({
      title: "Q-factor detection method",
      patent_number: "US10804750B2",
      location: "Claim 1",
      score: 0.71,
    });
    expect(result.sources[1].location).toBe("Abstract");
    expect(result.interpretation).toBe("guess.");
  });

  it("treats uploads as non-patents and reports insufficient evidence", () => {
    const result = normalizeResult(
      {
        status: "insufficient_evidence",
        answer: null,
        insufficient_reason: "Nothing relevant.",
        evidence: [evidence({ label: null, source_type: "upload", source_label: "notes.pdf", source_title: null })],
      },
      "q",
    );
    expect(result.status).toBe("insufficient");
    expect(result.note).toBe("Nothing relevant.");
    expect(result.sources[0]).toMatchObject({ id: 1, title: "notes.pdf", patent_number: null });
  });

  it("throws on a failed run", () => {
    expect(() => normalizeResult({ status: "failed", error_message: "LLM down", evidence: [] }, "q")).toThrow("LLM down");
  });

  it("accepts the simple { answer, sources } contract", () => {
    const result = normalizeResult(
      {
        answer: "Yes [1].",
        sources: [{ id: 1, title: "T", patent_number: "EP1", assignee: "A", year: 2020, snippet: "s", score: 82 }],
      },
      "q",
    );
    expect(result.sources[0]).toMatchObject({ id: 1, assignee: "A", year: 2020, score: 0.82 });
    expect(result.status).toBe("answered");
  });
});

describe("tokenizeAnswer", () => {
  it("splits words, bold and citations with spacing", () => {
    const { blocks, count } = tokenizeAnswer("The **quality factor** drops [1][2].\n\n- one [3]\n- two");
    expect(count).toBe(10);
    const p = blocks[0];
    if (p.kind !== "paragraph") throw new Error("expected paragraph");
    expect(p.tokens.map((t) => (t.kind === "cite" ? `[${t.id}]` : t.text))).toEqual([
      "The", "quality", "factor", "drops", "[1]", "[2]", ".",
    ]);
    expect(p.tokens[1]).toMatchObject({ bold: true, space: true });
    expect(p.tokens[6]).toMatchObject({ space: false });
    expect(blocks[1].kind).toBe("list");
  });
});

describe("helpers", () => {
  it("renumbers citations", () => {
    expect(toNumberedCitations("a [E12] b [?]")).toBe("a [12] b");
  });

  it("builds demo answers only from synthetic records whose citations exist", () => {
    for (const q of [...SUGGESTIONS, "something unrelated"]) {
      const r = demoResult(q);
      expect(r.demo).toBe(true);
      expect(r.sources.every((s) => s.patent_number?.startsWith("XX"))).toBe(true);
      const cited = [...r.answer.matchAll(/\[(\d+)\]/g)].map((m) => Number(m[1]));
      expect(cited.every((n) => r.sources.some((s) => s.id === n))).toBe(true);
    }
    expect(demoResult("wireless charging coins").sources[0].patent_number).toBe("XX0000002B1");
  });

  it("copies plain text with a source list", () => {
    expect(plainAnswer(demoResult("immersion"))).toMatch(/Sources:\n\[1\] Battery management system/);
  });
});

describe("describeError", () => {
  it("explains a wrong BACKEND_URL separately from a dead backend", () => {
    expect(describeError(new SearchError("unreachable", "", 404)).title).toMatch(/BACKEND_URL/);
    expect(describeError(new SearchError("unreachable", "", 0)).title).toMatch(/not reachable/);
    expect(describeError(new SearchError("auth", "", 401)).fix).toMatch(/Sign in/);
  });
});

describe("runTurn", () => {
  afterEach(() => vi.unstubAllGlobals());
  const run = { status: "succeeded", answer: "Yes [E1].", evidence: [evidence({ patent_id: null })], legal_question: false };
  const json = (body: unknown, status = 200) =>
    new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

  it("opens a conversation for the first question and reuses it for follow-ups", async () => {
    const calls: string[] = [];
    vi.stubGlobal("fetch", async (url: string, init?: RequestInit) => {
      calls.push(`${init?.method ?? "GET"} ${url} ${init?.body ?? ""}`);
      if (url === "/api/conversations") return json({ id: "c9" }, 201);
      return json({ response: run, interpreted_as: url.includes("c9") && calls.length > 2 ? "Which cooling patent is newest?" : null });
    });
    const first = await runTurn("How does immersion cooling work?", null, []);
    expect(first.conversationId).toBe("c9");
    expect(first.result.answer).toBe("Yes [1].");
    const second = await runTurn("Which is newest?", "c9", ["How does immersion cooling work?"]);
    expect(second.interpretedAs).toBe("Which cooling patent is newest?");
    expect(calls.filter((c) => c.startsWith("POST /api/conversations ")).length).toBe(1);
    expect(calls.at(-1)).toContain('"message":"Which is newest?"');
  });

  it("falls back to /ask with earlier questions when conversations are missing", async () => {
    let asked = "";
    vi.stubGlobal("fetch", async (url: string, init?: RequestInit) => {
      if (url === "/api/conversations") return json({ detail: "Not Found" }, 404);
      asked = JSON.parse(String(init?.body)).question;
      return json(run);
    });
    const turn = await runTurn("Which is newest?", null, ["How does immersion cooling work?"]);
    expect(turn.conversationId).toBeNull();
    expect(turn.result.query).toBe("Which is newest?");
    expect(asked).toContain("How does immersion cooling work?");
    expect(asked).toContain("Follow-up: Which is newest?");
  });

  it("suggests follow-ups that fit the answer", () => {
    expect(followUpSuggestions(demoResult("immersion")).length).toBe(3);
    expect(followUpSuggestions(demoResult("wireless coins"))).toHaveLength(2);
  });
});
