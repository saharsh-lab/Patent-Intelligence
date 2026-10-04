// Shape of an invention analysis result (backend: app/invention/analysis.py, _summarise).
export type Verdict = "disclosed" | "partially_disclosed" | "not_found";

export interface Feature {
  id: string;
  text: string;
  hypothesis: string;
  origin: "claim_element" | "llm" | "sentence";
  disclosed_in: string[];
  partially_in: string[];
}

export interface Candidate {
  key: string;
  kind: "document" | "patent";
  id: string;
  label: string;
  title: string | null;
  url: string | null;
  overlap: number;
  disclosed: number;
  partially: number;
}

export interface CellPassage {
  chunk_id: string;
  location: string;
  text: string;
}

export interface Cell {
  feature: string;
  candidate: string;
  verdict: Verdict;
  score: number;
  reason: string;
  passage: CellPassage | null;
}

export interface InventionResult {
  description: string;
  own_document: { id: string; label: string } | null;
  features: Feature[];
  candidates: Candidate[];
  cells: Cell[];
  not_found_features: string[];
  imported_patents: string[];
  verifier: string;
  disclaimer: string;
  steps: { tool: string; success: boolean; latency_ms: number; summary?: string }[];
}

export const VERDICT_STYLE: Record<Verdict, { symbol: string; label: string; className: string }> = {
  disclosed: { symbol: "✓", label: "disclosed", className: "bg-ok-soft text-ok" },
  partially_disclosed: { symbol: "~", label: "partially disclosed", className: "bg-warn-soft text-warn" },
  not_found: { symbol: "–", label: "not found", className: "text-muted" },
};

export const ORIGIN_LABEL: Record<Feature["origin"], string> = {
  claim_element: "claim elements",
  llm: "AI-extracted, checked against your text",
  sentence: "your sentences",
};

/** Cells indexed by feature and candidate. */
export function cellIndex(cells: Cell[]): Map<string, Cell> {
  return new Map(cells.map((c) => [`${c.feature}|${c.candidate}`, c]));
}

/** Short column names D1, D2… in the order the candidates are shown. */
export function shortNames(candidates: Candidate[]): Record<string, string> {
  return Object.fromEntries(candidates.map((c, i) => [c.key, `D${i + 1}`]));
}
