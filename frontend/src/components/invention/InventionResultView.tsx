"use client";

import { useState } from "react";

import { Badge, Panel } from "@/components/ui";
import { formatMs } from "@/lib/format";
import {
  cellIndex,
  ORIGIN_LABEL,
  shortNames,
  VERDICT_STYLE,
  type Cell,
  type InventionResult,
} from "@/lib/invention";

export function InventionResultView({ runId, result }: { runId: string; result: InventionResult }) {
  const { features, candidates } = result;
  const cells = cellIndex(result.cells);
  const short = shortNames(candidates);
  const firstCited = result.cells.find((c) => c.passage) ?? null;
  const [selected, setSelected] = useState<Cell | null>(firstCited);
  const notFound = new Set(result.not_found_features);
  const featureText = Object.fromEntries(features.map((f) => [f.id, f.text]));
  const candidateOf = Object.fromEntries(candidates.map((c) => [c.key, c]));

  return (
    <div className="space-y-5">
      <p role="note" className="rounded border border-warn/30 bg-warn-soft px-4 py-2 text-sm text-warn">
        {result.disclaimer}
      </p>

      <div className="grid gap-5 lg:grid-cols-2">
        <Panel
          title="Technical features"
          aside={<span className="text-xs text-muted">from {ORIGIN_LABEL[features[0]?.origin ?? "sentence"]}</span>}
        >
          <ul className="space-y-1.5 text-sm">
            {features.map((f) => (
              <li key={f.id} className="flex gap-2">
                <span className="font-mono text-xs font-semibold text-accent">{f.id}</span>
                <span>
                  {f.text}
                  {notFound.has(f.id) && (
                    <span className="ml-1.5">
                      <Badge tone="warn">not found in retrieved documents</Badge>
                    </span>
                  )}
                </span>
              </li>
            ))}
          </ul>
        </Panel>

        <Panel
          title="Closest documents"
          aside={
            <a
              href={`/api/analysis/invention/${runId}/report.md`}
              className="text-xs font-medium text-accent hover:underline"
            >
              Download report (.md)
            </a>
          }
        >
          {candidates.length === 0 ? (
            <p className="text-sm text-muted">No sufficiently similar documents were found.</p>
          ) : (
            <ul className="space-y-2.5">
              {candidates.map((c) => (
                <li key={c.key} className="text-sm">
                  <div className="flex items-baseline gap-2">
                    <span className="font-mono text-xs font-semibold text-muted">{short[c.key]}</span>
                    {c.url ? (
                      <a href={c.url} target="_blank" rel="noreferrer" className="font-medium text-accent hover:underline">
                        {c.label}
                      </a>
                    ) : (
                      <span className="font-medium">{c.label}</span>
                    )}
                    {c.kind === "patent" && <Badge>imported</Badge>}
                    <span className="ml-auto tabular-nums text-xs text-muted">
                      {c.disclosed}/{features.length} disclosed{c.partially ? `, ${c.partially} partly` : ""}
                    </span>
                  </div>
                  {c.title && <p className="ml-7 truncate text-xs text-muted">{c.title}</p>}
                  <div className="mt-1 ml-7 h-1.5 rounded-full bg-surface-2" aria-hidden>
                    <div className="pi-grow h-1.5 bg-text" style={{ width: `${Math.round(c.overlap * 100)}%` }} />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>

      {candidates.length > 0 && (
        <Panel
          title="Feature chart"
          aside={
            <span className="text-xs text-muted">
              ✓ disclosed · ~ partially · – not found · click a cell for its evidence
            </span>
          }
        >
          <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
            <div className="-mx-4 -my-1 overflow-x-auto xl:mx-0">
              <table className="w-full border-collapse text-sm">
                <thead>
                  <tr className="border-b border-line text-left text-xs text-muted">
                    <th className="px-3 py-1.5 font-medium">Feature</th>
                    {candidates.map((c) => (
                      <th key={c.key} className="px-2 py-1.5 text-center font-mono font-medium" title={c.label}>
                        {short[c.key]}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {features.map((f) => (
                    <tr key={f.id} className="border-b border-line last:border-0">
                      <th scope="row" className="px-3 py-1.5 text-left font-normal">
                        <span className="font-mono text-xs font-semibold text-accent">{f.id}</span>{" "}
                        <span className="text-xs text-muted">{f.text.length > 60 ? f.text.slice(0, 60) + "…" : f.text}</span>
                      </th>
                      {candidates.map((c) => {
                        const cell = cells.get(`${f.id}|${c.key}`);
                        const style = VERDICT_STYLE[cell?.verdict ?? "not_found"];
                        const active = selected && cell && selected.feature === cell.feature && selected.candidate === cell.candidate;
                        return (
                          <td key={c.key} className="px-1 py-1 text-center">
                            <button
                              type="button"
                              disabled={!cell}
                              onClick={() => cell && setSelected(cell)}
                              aria-label={`${f.id} in ${short[c.key]}: ${style.label}`}
                              className={`h-7 w-9 rounded font-mono text-sm font-semibold ${style.className} ${
                                active ? "ring-2 ring-accent" : "hover:ring-1 hover:ring-line-strong"
                              }`}
                            >
                              {style.symbol}
                            </button>
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="rounded border border-line bg-surface-2 p-3 text-sm" aria-live="polite">
              {selected ? (
                <>
                  <p className="text-xs text-muted">
                    <span className="font-mono font-semibold text-accent">{selected.feature}</span>{" "}
                    {featureText[selected.feature]}
                  </p>
                  <p className="mt-2 flex flex-wrap items-center gap-2">
                    <span className="font-medium">
                      {short[selected.candidate]} {candidateOf[selected.candidate]?.label}
                    </span>
                    <Badge
                      tone={
                        selected.verdict === "disclosed" ? "ok" : selected.verdict === "partially_disclosed" ? "warn" : "neutral"
                      }
                    >
                      {VERDICT_STYLE[selected.verdict].label}
                    </Badge>
                    <span className="text-xs text-muted">{selected.reason}</span>
                  </p>
                  {selected.passage ? (
                    <>
                      <p className="mt-2 font-mono text-[11px] text-muted">{selected.passage.location}</p>
                      <blockquote className="mt-1 max-h-64 overflow-y-auto border-l-2 border-accent pl-3 text-sm whitespace-pre-line">
                        {selected.passage.text}
                      </blockquote>
                    </>
                  ) : (
                    <p className="mt-2 text-xs text-muted">No passage of this document disclosed the feature.</p>
                  )}
                </>
              ) : (
                <p className="text-xs text-muted">Select a cell to see the passage behind it.</p>
              )}
            </div>
          </div>
        </Panel>
      )}

      <p className="text-xs text-muted">
        Steps:{" "}
        {result.steps.map((s, i) => (
          <span key={s.tool}>
            {i > 0 && " → "}
            {s.tool.replaceAll("_", " ")} ({formatMs(s.latency_ms)}
            {s.summary ? `; ${s.summary}` : ""})
          </span>
        ))}
        . Each ✓/~ comes from retrieval and an automatic {result.verifier} check of the cited passage, not from a
        language model.
      </p>
    </div>
  );
}
