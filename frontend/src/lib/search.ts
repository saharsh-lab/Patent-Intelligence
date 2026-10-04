// Data layer for the search page: one request, one normalised result.
//
// The backend's POST /ask returns { answer, evidence[...] } with citations like [E3].
// The page works on a simpler shape, { answer, sources: [{ id, title, patent_number,
// assignee, year, snippet, score }] } with citations like [3]. normalizeResult()
// accepts either shape, so a backend that already returns `sources` also works.
//
// When the backend cannot be reached, the page falls back to demoResult(): answers
// written only from the backend's own SYNTHETIC demo patents (app/patents/demo.py,
// country code "XX"), clearly labelled as demo data in the UI.
import { sectionLabel } from "./format";
import { stripInterpretation } from "./citations";
import type { AskResponse, EvidenceOut, PatentOut } from "./types";

export interface Source {
  id: number;
  title: string;
  patent_number: string | null;
  assignee: string | null;
  year: number | null;
  snippet: string;
  /** 0..1, or null when the backend gave no comparable score */
  score: number | null;
  /** "Claim 1", "Abstract", … */
  location?: string | null;
  url?: string | null;
  cited?: boolean;
  patentId?: string | null;
  synthetic?: boolean;
}

export interface SearchResult {
  query: string;
  answer: string;
  sources: Source[];
  status: "answered" | "insufficient";
  /** Why there is no answer (status "insufficient") */
  note?: string | null;
  interpretation?: string | null;
  legal?: boolean;
  demo?: boolean;
}

export type SearchErrorKind = "unreachable" | "auth" | "invalid" | "busy" | "server";

export class SearchError extends Error {
  constructor(
    public kind: SearchErrorKind,
    message: string,
    public status = 0,
  ) {
    super(message);
    this.name = "SearchError";
  }
}

/** What went wrong and how to fix it, in plain words, for the error panel. */
export function describeError(error: SearchError): { title: string; fix: string } {
  switch (error.kind) {
    case "unreachable":
      return {
        title: "The search service is not reachable.",
        fix: "Start the backend API and check that BACKEND_URL points to it, then try again.",
      };
    case "auth":
      return { title: "Your session has ended.", fix: "Sign in again, then repeat the search." };
    case "invalid":
      return {
        title: error.message || "The question could not be processed.",
        fix: "Rephrase the question in a sentence or two (under 2,000 characters).",
      };
    case "busy":
      return { title: "Too many searches at once.", fix: "Wait a few seconds, then try again." };
    default:
      return {
        title: error.message || "The backend failed while answering.",
        fix: "Try again. If it keeps failing, check the API logs for this request.",
      };
  }
}

// ---------------------------------------------------------------------------
// Request

/** Ask the backend. Throws SearchError; an aborted request throws the AbortError. */
export async function runSearch(query: string, signal?: AbortSignal): Promise<SearchResult> {
  let response: Response;
  try {
    response = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: query }),
      signal,
    });
  } catch (e) {
    if (signal?.aborted) throw e;
    throw new SearchError("unreachable", "Cannot reach the server.");
  }

  if (!response.ok) throw await toSearchError(response);
  const result = normalizeResult(await response.json(), query);
  await enrichPatents(result, signal);
  return result;
}

async function toSearchError(response: Response): Promise<SearchError> {
  let message = "";
  let isBackendJson = false;
  try {
    const body = await response.json();
    message = body?.error?.message ?? (typeof body?.detail === "string" ? body.detail : "");
    isBackendJson = true;
  } catch {
    // Not JSON: the Next.js proxy's own error page, i.e. the backend is down
  }
  const s = response.status;
  if (s === 401 || s === 403) return new SearchError("auth", message, s);
  if (s === 400 || s === 413 || s === 422) return new SearchError("invalid", message, s);
  if (s === 429) return new SearchError("busy", message, s);
  if (!isBackendJson && (s === 500 || s === 502 || s === 503 || s === 504)) {
    return new SearchError("unreachable", "The backend is not responding.", s);
  }
  return new SearchError("server", message, s);
}

/** Fill assignee and year from the patent records (one extra call; failures ignored). */
async function enrichPatents(result: SearchResult, signal?: AbortSignal) {
  const wanted = result.sources.filter((s) => s.patentId && (!s.assignee || !s.year));
  if (!wanted.length) return;
  try {
    const response = await fetch("/api/patents", { signal });
    if (!response.ok) return;
    const patents = (await response.json()) as PatentOut[];
    const byId = new Map(patents.map((p) => [p.id, p]));
    for (const source of wanted) {
      const patent = byId.get(source.patentId!);
      if (!patent) continue;
      source.assignee ??= patent.applicants?.[0] ?? null;
      source.year ??= patent.publication_date ? Number(patent.publication_date.slice(0, 4)) : null;
      source.patent_number ??= patent.publication_number;
      if (!source.title || source.title === source.patent_number) source.title = patent.title ?? source.title;
    }
  } catch {
    // Metadata is a nicety; the answer stands without it
  }
}

// ---------------------------------------------------------------------------
// Normalisation

const clamp01 = (n: number) => Math.max(0, Math.min(1, n));

function toScore(value: unknown): number | null {
  if (typeof value !== "number" || Number.isNaN(value)) return null;
  return clamp01(value > 1 ? value / 100 : value);
}

/** Accepts the backend's AskResponse or the simple { answer, sources } contract. */
export function normalizeResult(raw: unknown, query: string): SearchResult {
  const data = (raw ?? {}) as Record<string, unknown>;

  if (Array.isArray(data.sources)) {
    const sources = (data.sources as Record<string, unknown>[]).map((s, i) => ({
      id: Number(s.id ?? i + 1),
      title: String(s.title ?? s.patent_number ?? `Source ${i + 1}`),
      patent_number: (s.patent_number as string) ?? null,
      assignee: (s.assignee as string) ?? null,
      year: s.year != null ? Number(s.year) : null,
      snippet: String(s.snippet ?? ""),
      score: toScore(s.score),
      url: (s.url as string) ?? null,
      cited: true,
    }));
    const answer = String(data.answer ?? "");
    return { query, answer, sources, status: answer.trim() ? "answered" : "insufficient" };
  }

  const run = data as unknown as AskResponse;
  if (run.status === "failed") {
    throw new SearchError("server", run.error_message || "The backend failed while answering.");
  }
  const evidence = (run.evidence ?? []) as EvidenceOut[];
  const labelled = evidence
    .filter((e) => e.label && /^E\d+$/.test(e.label))
    .sort((a, b) => labelNumber(a.label!) - labelNumber(b.label!));
  // Without labels (no answer was written) show the best retrieved passages, uncited
  const chosen = labelled.length
    ? labelled.map((e) => ({ e, id: labelNumber(e.label!) }))
    : [...evidence].sort((a, b) => a.rank - b.rank).slice(0, 5).map((e, i) => ({ e, id: i + 1 }));

  const sources: Source[] = chosen.map(({ e, id }) => {
    const isPatent = e.source_type !== "upload";
    return {
      id,
      title: e.source_title || e.source_label,
      patent_number: isPatent ? e.source_label : null,
      assignee: null,
      year: null,
      snippet: e.text,
      score: toScore(e.vector_similarity ?? (e.score <= 1 ? e.score : null)),
      location: e.claim_number ? `Claim ${e.claim_number}` : e.section ? sectionLabel(e.section) : null,
      url: e.source_url ?? null,
      cited: e.cited,
      patentId: e.patent_id,
      synthetic: e.source_type === "demo",
    };
  });

  const answer = run.answer ? toNumberedCitations(stripInterpretation(run.answer)) : "";
  const answered = run.status === "succeeded" && !!answer.trim();
  return {
    query,
    answer,
    sources,
    status: answered ? "answered" : "insufficient",
    note: answered ? null : run.insufficient_reason || "The sources do not contain enough to answer this.",
    interpretation: answered ? run.interpretation : null,
    legal: !!run.legal_question,
  };
}

const labelNumber = (label: string) => Number(label.slice(1));

/** "[E2][E5]" → "[2][5]"; "[?]" (a label the model invented) is dropped. */
export function toNumberedCitations(text: string): string {
  return text.replace(/\[E(\d+)\]/g, "[$1]").replace(/\s?\[\?\]/g, "");
}

// ---------------------------------------------------------------------------
// Answer tokens, for the word-by-word reveal

export type Token =
  | { kind: "word"; text: string; bold: boolean; space: boolean; index: number }
  | { kind: "cite"; id: number; space: boolean; index: number };

export type AnswerBlock = { kind: "paragraph"; tokens: Token[] } | { kind: "list"; items: Token[][] };

const BULLET = /^\s*(?:[-*•]|\d+[.)])\s+/;
const PIECE = /(\s+)|\[(\d+)\]|\*\*([^*]+)\*\*|([^\s[*]+|[[*])/g;

/** Split the answer into paragraphs/lists of words and citation markers. */
export function tokenizeAnswer(answer: string): { blocks: AnswerBlock[]; count: number } {
  let index = 0;
  const tokenize = (text: string): Token[] => {
    const out: Token[] = [];
    let space = false;
    for (const m of text.matchAll(PIECE)) {
      if (m[1]) {
        space = true;
        continue;
      }
      if (m[2]) {
        out.push({ kind: "cite", id: Number(m[2]), space: false, index: index++ });
      } else if (m[3]) {
        m[3].split(/\s+/).filter(Boolean).forEach((word, i) => {
          out.push({ kind: "word", text: word, bold: true, space: i > 0 || (space && out.length > 0), index: index++ });
        });
      } else if (m[4]) {
        out.push({ kind: "word", text: m[4], bold: false, space: space && out.length > 0, index: index++ });
      }
      space = false;
    }
    return out;
  };

  const blocks: AnswerBlock[] = [];
  for (const chunk of answer.split(/\n\s*\n/)) {
    const lines = chunk.split("\n").filter((l) => l.trim());
    if (!lines.length) continue;
    if (lines.every((l) => BULLET.test(l))) {
      blocks.push({ kind: "list", items: lines.map((l) => tokenize(l.replace(BULLET, ""))) });
    } else {
      blocks.push({ kind: "paragraph", tokens: tokenize(lines.join(" ")) });
    }
  }
  return { blocks, count: index };
}

/** Plain text for the copy button: citations kept as [n], markdown bold removed. */
export function plainAnswer(result: SearchResult): string {
  const text = result.answer.replace(/\*\*([^*]+)\*\*/g, "$1").trim();
  const refs = result.sources.map(
    (s) => `[${s.id}] ${s.title}${s.patent_number && s.patent_number !== s.title ? ` (${s.patent_number})` : ""}`,
  );
  return refs.length ? `${text}\n\nSources:\n${refs.join("\n")}` : text;
}

// ---------------------------------------------------------------------------
// Demo fallback (synthetic data only)

export const SUGGESTIONS = [
  "How do battery packs use immersion cooling?",
  "How do wireless chargers detect metal objects?",
  "How is a battery cell's core temperature estimated?",
  "When does the controller speed up the coolant pump?",
];

const DEMO_SOURCES: Record<string, Omit<Source, "id">> = {
  thermal: {
    title: "Liquid-cooled battery pack with per-cell temperature estimation",
    patent_number: "XX0000001A1",
    assignee: "Demo Energy Systems",
    year: 2021,
    snippet:
      "1. A battery pack comprising: a plurality of cells; a thermistor attached to each cell; a coolant pump; and a controller configured to estimate a core temperature of each cell and to increase a speed of the coolant pump when an estimated core temperature exceeds a limit.\n\n2. The battery pack of claim 1, wherein the core temperature is estimated from a surface temperature and a current of the cell.",
    score: 0.86,
    location: "Claims 1–2",
    synthetic: true,
  },
  thermalDescription: {
    title: "Liquid-cooled battery pack with per-cell temperature estimation",
    patent_number: "XX0000001A1",
    assignee: "Demo Energy Systems",
    year: 2021,
    snippet:
      "The pack contains sixteen prismatic cells cooled by a cold plate. Each cell carries a thermistor. The controller runs a lumped thermal model.\n\nWhen the hottest estimated core temperature exceeds 42 degrees Celsius, the pump speed is increased in steps of ten percent.",
    score: 0.79,
    location: "Description",
    synthetic: true,
  },
  immersion: {
    title: "Battery management system with immersion cooling fluid",
    patent_number: "XX0000003A1",
    assignee: "Demo Energy Systems",
    year: 2023,
    snippet:
      "Battery cells are immersed in a dielectric fluid; temperature sensors in the fluid allow a controller to regulate fluid circulation.\n\n1. A battery system comprising cells immersed in a dielectric fluid, a fluid temperature sensor, and a controller regulating circulation of the fluid. The dielectric fluid is circulated by a pump.",
    score: 0.88,
    location: "Abstract and claim 1",
    synthetic: true,
  },
  wireless: {
    title: "Wireless charger that detects metal objects by coil quality factor",
    patent_number: "XX0000002B1",
    assignee: "Demo Charging Ltd",
    year: 2022,
    snippet:
      "An inductive charging pad measures the quality factor of its transmitter coil before power transfer and blocks charging when a metal object is present.\n\n1. A wireless charging pad comprising a transmitter coil, an inverter, and a detection circuit that measures a quality factor of the coil and disables the inverter when the quality factor is below a threshold. Coins and keys reduce the coil quality factor.",
    score: 0.91,
    location: "Abstract and claim 1",
    synthetic: true,
  },
};

const DEMO_ANSWERS: { keywords: string[]; answer: string; sources: (keyof typeof DEMO_SOURCES)[] }[] = [
  {
    keywords: ["immersion", "dielectric", "fluid", "submerged", "immersed"],
    sources: ["immersion", "thermal"],
    answer:
      "In the immersion approach, the battery cells sit directly in a **dielectric fluid**, and temperature sensors placed in that fluid let a controller regulate how the fluid circulates [1]. A pump moves the dielectric fluid around the cells [1].\n\nA related design keeps the cells dry and cools them through a cold plate instead: a coolant pump serves the pack, and a controller raises the pump speed when an estimated cell core temperature exceeds a limit [2].",
  },
  {
    keywords: ["wireless", "charger", "charging", "metal", "coin", "foreign", "object", "inductive", "coil", "quality"],
    sources: ["wireless"],
    answer:
      "The charging pad checks its own transmitter coil before sending power. It measures the coil's **quality factor**, and a detection circuit disables the inverter when that value falls below a threshold [1].\n\nMetal objects such as coins and keys lower the coil's quality factor, so their presence blocks charging [1].",
  },
  {
    keywords: ["core", "estimate", "estimated", "estimation", "thermistor", "pump", "speed", "temperature", "controller", "coolant", "cell"],
    sources: ["thermal", "thermalDescription"],
    answer:
      "Each cell carries a **thermistor** on its surface, and the controller estimates the cell's core temperature from that surface temperature together with the cell's current [1]. The estimate comes from a lumped thermal model run by the controller [2].\n\nWhen the hottest estimated core temperature exceeds 42 degrees Celsius, the controller increases the coolant pump speed in steps of ten percent [2]. The claims describe this more generally as raising the pump speed when any estimate exceeds a limit [1].",
  },
];

/** A sample answer built only from the synthetic demo patents. */
export function demoResult(query: string): SearchResult {
  const words = new Set(query.toLowerCase().match(/[a-z]{3,}/g) ?? []);
  const scored = DEMO_ANSWERS.map((a) => ({ a, hits: a.keywords.filter((k) => words.has(k)).length }));
  const best = scored.sort((x, y) => y.hits - x.hits)[0];
  const pick = best.hits > 0 ? best.a : DEMO_ANSWERS[2];
  return {
    query,
    answer: pick.answer,
    sources: pick.sources.map((key, i) => ({ id: i + 1, ...DEMO_SOURCES[key], cited: true })),
    status: "answered",
    demo: true,
  };
}
