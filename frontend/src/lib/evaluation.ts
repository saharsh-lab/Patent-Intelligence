// Shapes of experiment result files (backend: app/evaluation/report.py and
// verifier_eval.py). The API returns them as plain JSON, so they are typed by hand.
import type { components } from "@/types/api";

export type EvaluationListItem = components["schemas"]["EvaluationListItem"];

export type MetricFormat = "percent" | "ratio" | "ms" | "count" | "usd" | "tokens";

export interface MetricInfo {
  key: string;
  label: string;
  group: string;
  higher_is_better: boolean | null;
  format: MetricFormat;
}

export interface Stat {
  n: number;
  mean: number | null;
  ci_low: number | null;
  ci_high: number | null;
}

export interface Comparison {
  reference: string;
  variant: string;
  metric: string;
  n: number;
  mean_diff: number;
  ci_low: number | null;
  ci_high: number | null;
  wins: number;
  losses: number;
  ties: number;
  clear: boolean;
}

export interface ExperimentSummary {
  kind: "experiment";
  experiment: string;
  run: string;
  description: string;
  finished_at: string;
  dataset: { name: string; items: number; synthetic: boolean; labelled_by: string; sha256: string };
  repeats: number;
  eval_k: number;
  variants: { name: string; pipeline: string; description: string; settings: Record<string, unknown> }[];
  metrics: MetricInfo[];
  results: Record<string, Record<string, Stat>>;
  latency: Record<string, { p50: number | null; p95: number | null }>;
  comparisons: Comparison[];
  runs: { total: number; failed: number };
  warnings: string[];
}

export interface Agreement {
  n: number;
  accuracy: number;
  accuracy_ci: Stat;
  cohen_kappa: number | null;
  macro_f1: number;
  detection: { precision: number; recall: number; f1: number };
  confusion: Record<string, Record<string, number>>;
  ms_per_claim: number;
  model: string | null;
}

export interface VerifierSummary {
  kind: "verifier";
  experiment: string;
  run: string;
  description: string;
  finished_at: string;
  labels: { file: string; n: number; distribution: Record<string, number> };
  methods: Record<string, Agreement>;
  warnings: string[];
}

export interface SelfCheckSummary {
  kind: "selfcheck";
  experiment: string;
  run: string;
  description: string;
  finished_at: string;
  dataset: { name: string; items: number; synthetic: boolean; sha256: string };
  verifier: string;
  models: { llm: string; embeddings: string };
  results: Record<string, Stat & { label: string }>;
  warnings: string[];
}

/** One patent in a self-check (rows.jsonl). */
export interface SelfCheckRow {
  doc: string;
  domain: string;
  self_rank: number | null;
  self_coverage?: number | null;
  same_domain_at_1: number;
  same_domain_at_3?: number;
  top_candidates: string[];
  latency_included_ms: number;
  [field: string]: unknown;
}

export type Summary = ExperimentSummary | VerifierSummary | SelfCheckSummary;

/** One scored run (runs.jsonl). Metric values are null when not applicable. */
export interface RunRow {
  variant: string;
  item_id: string;
  item_type: string;
  question: string;
  repeat: number;
  status: string;
  error?: string | null;
  tools_used?: string[];
  intent?: string | null;
  [metric: string]: unknown;
}

export interface EvaluationResult {
  summary: Summary;
  rows: RunRow[];
}

export const VERDICTS = ["supported", "partially_supported", "unsupported"] as const;

export function formatMetric(value: number | null | undefined, format: MetricFormat): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  switch (format) {
    case "percent":
      return `${(value * 100).toFixed(1)}%`;
    case "ms":
      return value < 1000 ? `${Math.round(value)} ms` : `${(value / 1000).toFixed(1)} s`;
    case "usd":
      return `$${value.toFixed(4)}`;
    case "count":
    case "tokens":
      return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(1);
    default:
      return value.toFixed(3);
  }
}

/** A difference is shown in the metric's units; percentages as percentage points. */
export function formatDiff(value: number | null | undefined, format: MetricFormat): string {
  if (value === null || value === undefined) return "—";
  const sign = value > 0 ? "+" : value < 0 ? "−" : "±";
  const magnitude = Math.abs(value);
  if (format === "percent") return `${sign}${(magnitude * 100).toFixed(1)} pp`;
  return `${sign}${formatMetric(magnitude, format)}`;
}

/**
 * Index of the best variant for one metric, or null if there is no meaningful "best"
 * (descriptive metric, fewer than two variants with values, or a tie).
 */
export function bestIndex(stats: (Stat | undefined)[], higherIsBetter: boolean | null): number | null {
  if (higherIsBetter === null) return null;
  const values = stats.map((s) => (s && s.n > 0 && s.mean !== null ? s.mean : null));
  const present = values.filter((v): v is number => v !== null);
  if (present.length < 2) return null;
  const best = higherIsBetter ? Math.max(...present) : Math.min(...present);
  if (present.filter((v) => Math.abs(v - best) < 1e-9).length > 1) return null;
  return values.findIndex((v) => v !== null && Math.abs(v - best) < 1e-9);
}

/** Was the change in the good direction? (null = no clear difference / not applicable) */
export function diffTone(c: Comparison, higherIsBetter: boolean | null): "ok" | "bad" | null {
  if (!c.clear || higherIsBetter === null) return null;
  return c.mean_diff > 0 === higherIsBetter ? "ok" : "bad";
}
