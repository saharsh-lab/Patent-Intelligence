"use client";

import { Badge } from "@/components/ui";
import { formatPercent } from "@/lib/format";
import type { Verification } from "@/lib/verification";

// Shape of the backend's ComparisonResult.to_json()
export interface ComparisonCell {
  text: string;
  citations: string[];
  invalid: string[];
}
export interface ComparisonPoint extends ComparisonCell {
  sources: string[];
}
export interface Comparison {
  mode: "llm" | "extractive" | "extractive_fallback";
  fallback_reason: string | null;
  sources: { key: string; kind: string; id: string; label: string; title: string | null }[];
  aspects: { key: string; label: string }[];
  cells: Record<string, Record<string, ComparisonCell>>;
  similarities: ComparisonPoint[];
  differences: ComparisonPoint[];
  label_source: Record<string, string>;
  metrics: {
    cell_coverage: number | null;
    cross_source_citations: number;
    fabricated_citations: number;
    one_sided_similarities: number;
  };
}

const MODE_LABELS: Record<Comparison["mode"], string> = {
  llm: "LLM-written, citation-checked",
  extractive: "Extractive (quoted from passages, no LLM)",
  extractive_fallback: "Extractive fallback (LLM output was unusable)",
};

function Chips({ cell, onCite }: { cell: ComparisonCell; onCite: (label: string) => void }) {
  return (
    <>
      {cell.citations.map((label) => (
        <button
          key={label}
          type="button"
          onClick={() => onCite(label)}
          className="mx-0.5 rounded-sm bg-accent-soft px-1 font-mono text-[11px] font-medium text-accent hover:underline"
          title={`Show evidence ${label}`}
        >
          {label}
        </button>
      ))}
      {cell.invalid.length > 0 && (
        <span
          className="mx-0.5 rounded-sm bg-bad-soft px-1 font-mono text-[11px] text-bad"
          title={`Removed citations: ${cell.invalid.join(", ")} (not provided, or belonging to another source)`}
        >
          {cell.invalid.length} removed
        </span>
      )}
    </>
  );
}

function PointList({
  title,
  points,
  onCite,
  warnOneSided,
}: {
  title: string;
  points: ComparisonPoint[];
  onCite: (label: string) => void;
  warnOneSided?: boolean;
}) {
  return (
    <div>
      <h3 className="mb-1.5 text-sm font-semibold">{title}</h3>
      {points.length === 0 ? (
        <p className="text-sm text-muted">None identified in the evidence.</p>
      ) : (
        <ul className="list-disc space-y-1 pl-5 text-sm">
          {points.map((p, i) => (
            <li key={i}>
              {p.text}
              <Chips cell={p} onCite={onCite} />
              {warnOneSided && new Set(p.sources).size < 2 && (
                <span className="ml-1 text-xs text-warn" title="This similarity cites only one of the sources.">
                  (one-sided evidence)
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** Aspect × source table where every cell cites passages of its own source. */
const MARK = {
  supported: { symbol: "✓", style: "text-ok" },
  partially_supported: { symbol: "~", style: "text-warn" },
  unsupported: { symbol: "✗", style: "text-bad" },
} as const;

export function ComparisonTable({
  comparison,
  onCite,
  verification,
}: {
  comparison: Comparison;
  onCite: (label: string) => void;
  verification?: Verification | null;
}) {
  const { sources, aspects, cells, metrics } = comparison;
  const verdictOf = new Map((verification?.claims ?? []).map((c) => [c.location, c]));
  return (
    <section className="rounded border border-line bg-surface">
      <header className="flex flex-wrap items-center gap-2 border-b border-line px-4 py-2.5">
        <h2 className="text-sm font-semibold">Technical comparison</h2>
        <Badge tone={comparison.mode === "llm" ? "accent" : "neutral"}>{MODE_LABELS[comparison.mode]}</Badge>
        <span className="ml-auto flex flex-wrap gap-x-4 gap-y-1 font-mono text-[11px] text-muted">
          <span title="Share of filled cells that cite their own source">cells cited {formatPercent(metrics.cell_coverage)}</span>
          <span title="Cell citations pointing at another source's passage (removed)" className={metrics.cross_source_citations ? "text-bad" : ""}>
            cross-source {metrics.cross_source_citations}
          </span>
          <span title="Citations to passages that were never provided (removed)" className={metrics.fabricated_citations ? "text-bad" : ""}>
            fabricated {metrics.fabricated_citations}
          </span>
        </span>
      </header>
      {comparison.fallback_reason && (
        <p className="border-b border-line bg-warn-soft px-4 py-1.5 text-xs text-warn">
          LLM comparison was not usable ({comparison.fallback_reason}); showing passages quoted directly.
        </p>
      )}
      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] border-collapse text-sm">
          <thead>
            <tr className="border-b border-line bg-surface-2 text-left align-bottom">
              <th className="w-40 px-4 py-2 text-xs font-medium text-muted">Aspect</th>
              {sources.map((s) => (
                <th key={s.key} className="px-4 py-2">
                  <span className="font-mono text-xs text-muted">{s.key}</span>{" "}
                  <span className="font-medium">{s.label}</span>
                  {s.title && <p className="text-xs font-normal text-muted">{s.title}</p>}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {aspects.map((aspect) => (
              <tr key={aspect.key} className="align-top">
                <th scope="row" className="px-4 py-2.5 text-left text-xs font-medium text-muted">{aspect.label}</th>
                {sources.map((s) => {
                  const cell = cells[aspect.key]?.[s.key];
                  const empty = !cell || cell.text === "Not stated in the evidence";
                  return (
                    <td key={s.key} className={`px-4 py-2.5 ${empty ? "text-muted italic" : ""}`}>
                      {cell ? cell.text : "Not stated in the evidence"}
                      {cell && <Chips cell={cell} onCite={onCite} />}
                      {(() => {
                        const checked = verdictOf.get(`cell:${aspect.key}:${s.key}`);
                        if (!checked) return null;
                        const mark = MARK[checked.verdict];
                        return (
                          <span className={`ml-1 font-mono text-xs font-semibold ${mark.style}`} title={`Verification: ${checked.reason}`}>
                            {mark.symbol}
                          </span>
                        );
                      })()}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="grid gap-4 border-t border-line px-4 py-3 md:grid-cols-2">
        <PointList title="Technical similarities" points={comparison.similarities} onCite={onCite} warnOneSided />
        <PointList title="Technical differences" points={comparison.differences} onCite={onCite} />
      </div>
      <p className="border-t border-line px-4 py-2 text-xs text-muted">
        Technical comparison of the cited passages only; not an assessment of novelty, validity or infringement.
      </p>
    </section>
  );
}
