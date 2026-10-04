"use client";

import { Fragment, useState } from "react";

import { Badge, Panel } from "@/components/ui";
import {
  bestIndex,
  diffTone,
  formatDiff,
  formatMetric,
  type ExperimentSummary,
  type MetricInfo,
  type RunRow,
} from "@/lib/evaluation";
import { formatDateTime } from "@/lib/format";

export function ExperimentView({ summary, rows }: { summary: ExperimentSummary; rows: RunRow[] }) {
  return (
    <div className="space-y-5">
      <Overview summary={summary} />
      <ResultsTable summary={summary} />
      {summary.comparisons.length > 0 && <Differences summary={summary} />}
      <PerQuestion summary={summary} rows={rows} />
    </div>
  );
}

function Overview({ summary }: { summary: ExperimentSummary }) {
  return (
    <section className="rounded border border-line bg-surface px-4 py-3">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <h2 className="font-mono text-sm font-semibold">{summary.experiment}</h2>
        <span className="text-xs text-muted">{formatDateTime(summary.finished_at)}</span>
      </div>
      {summary.description && <p className="mt-1 text-sm">{summary.description}</p>}
      <div className="mt-2 flex flex-wrap gap-1.5">
        <Badge>dataset {summary.dataset.name}</Badge>
        <Badge>{summary.dataset.items} questions</Badge>
        <Badge>{summary.repeats} repeat{summary.repeats === 1 ? "" : "s"}</Badge>
        <Badge>k = {summary.eval_k}</Badge>
        <Badge tone={summary.runs.failed ? "bad" : "neutral"}>
          {summary.runs.total} runs, {summary.runs.failed} failed
        </Badge>
      </div>
      {summary.warnings.length > 0 && (
        <ul className="mt-3 space-y-1 rounded border border-warn/30 bg-warn-soft px-3 py-2 text-xs text-warn">
          {summary.warnings.map((w) => (
            <li key={w}>{w}</li>
          ))}
        </ul>
      )}
      <ul className="mt-3 space-y-1 text-sm">
        {summary.variants.map((v) => (
          <li key={v.name} className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
            <span className="font-medium">{v.name}</span>
            <span className="text-xs text-muted">{v.pipeline}</span>
            {Object.entries(v.settings).map(([k, value]) => (
              <code key={k} className="rounded-sm bg-surface-2 px-1 font-mono text-[11px] text-muted">
                {k}={String(value)}
              </code>
            ))}
            {v.description && <span className="text-xs text-muted">— {v.description}</span>}
          </li>
        ))}
      </ul>
    </section>
  );
}

function ResultsTable({ summary }: { summary: ExperimentSummary }) {
  const variants = summary.variants.map((v) => v.name);
  const shown = summary.metrics.filter((m) => variants.some((v) => summary.results[v]?.[m.key]?.n));
  const groups = [...new Set(shown.map((m) => m.group))];
  return (
    <Panel title="Results" aside={<span className="text-xs text-muted">mean · 95% CI · n questions</span>}>
      <div className="-m-4 overflow-x-auto">
        <table className="w-full min-w-[560px] border-collapse text-sm">
          <thead>
            <tr className="border-b border-line bg-surface-2 text-left">
              <th className="px-4 py-2 text-xs font-medium text-muted">Metric</th>
              {variants.map((v) => (
                <th key={v} className="px-4 py-2 font-medium">{v}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {groups.map((group) => (
              <Fragment key={group}>
                <tr className="border-b border-line">
                  <th colSpan={variants.length + 1} className="px-4 pt-3 pb-1 text-left text-xs font-semibold tracking-wide text-muted uppercase">
                    {group}
                  </th>
                </tr>
                {shown
                  .filter((m) => m.group === group)
                  .map((m) => (
                    <MetricRow key={m.key} metric={m} summary={summary} variants={variants} />
                  ))}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>
      <p className="-mx-4 -mb-4 mt-4 border-t border-line px-4 py-2 text-xs text-muted">
        Latency per run, median / p95:{" "}
        {variants.map((v, i) => (
          <span key={v} className="tabular-nums">
            {i > 0 && " · "}
            {v} {formatMetric(summary.latency[v]?.p50, "ms")} / {formatMetric(summary.latency[v]?.p95, "ms")}
          </span>
        ))}
      </p>
    </Panel>
  );
}

function MetricRow({ metric, summary, variants }: { metric: MetricInfo; summary: ExperimentSummary; variants: string[] }) {
  const stats = variants.map((v) => summary.results[v]?.[metric.key]);
  const best = bestIndex(stats, metric.higher_is_better);
  const direction = metric.higher_is_better === null ? "" : metric.higher_is_better ? " (higher is better)" : " (lower is better)";
  return (
    <tr className="border-b border-line last:border-0">
      <td className="px-4 py-1.5 text-muted" title={`${metric.label}${direction}`}>
        {metric.label}
        {metric.key === "latency_ms" && <span className="ml-1 text-xs">(mean)</span>}
      </td>
      {stats.map((s, i) => (
        <td key={variants[i]} className="px-4 py-1.5 tabular-nums">
          {!s || !s.n ? (
            <span className="text-muted">—</span>
          ) : (
            <>
              <span className={i === best ? "font-semibold text-accent" : ""}>{formatMetric(s.mean, metric.format)}</span>
              {s.ci_low !== null && (
                <span className="ml-1.5 text-xs text-muted">
                  [{formatMetric(s.ci_low, metric.format)}, {formatMetric(s.ci_high, metric.format)}]
                </span>
              )}
              <span className="ml-1.5 text-[11px] text-muted">n={s.n}</span>
            </>
          )}
        </td>
      ))}
    </tr>
  );
}

function Differences({ summary }: { summary: ExperimentSummary }) {
  const [onlyClear, setOnlyClear] = useState(false);
  const info = Object.fromEntries(summary.metrics.map((m) => [m.key, m]));
  const changed = summary.comparisons.filter((c) => c.wins + c.losses > 0);
  const shown = onlyClear ? changed.filter((c) => c.clear) : changed;
  return (
    <Panel
      title={`Paired differences vs. ${summary.comparisons[0].reference}`}
      aside={
        <label className="flex items-center gap-1.5 text-xs text-muted">
          <input type="checkbox" checked={onlyClear} onChange={(e) => setOnlyClear(e.target.checked)} />
          only clear differences
        </label>
      }
    >
      {shown.length === 0 ? (
        <p className="text-sm text-muted">
          {onlyClear ? "No difference is clear on this dataset." : "Every question scored the same in every variant."}
        </p>
      ) : (
        <div className="-m-4 overflow-x-auto">
          <table className="w-full min-w-[560px] border-collapse text-sm">
            <thead>
              <tr className="border-b border-line bg-surface-2 text-left text-xs text-muted">
                <th className="px-4 py-2 font-medium">Variant</th>
                <th className="px-4 py-2 font-medium">Metric</th>
                <th className="px-4 py-2 font-medium">Δ mean [95% CI]</th>
                <th className="px-4 py-2 font-medium" title="Questions where the variant was better / worse / equal">
                  better / worse / same
                </th>
              </tr>
            </thead>
            <tbody>
              {shown.map((c) => {
                const m = info[c.metric];
                const tone = diffTone(c, m.higher_is_better);
                return (
                  <tr key={`${c.variant}-${c.metric}`} className="border-b border-line last:border-0">
                    <td className="px-4 py-1.5">{c.variant}</td>
                    <td className="px-4 py-1.5 text-muted">{m.label}</td>
                    <td className="px-4 py-1.5 tabular-nums">
                      <span className={tone === "ok" ? "font-semibold text-ok" : tone === "bad" ? "font-semibold text-bad" : ""}>
                        {formatDiff(c.mean_diff, m.format)}
                      </span>
                      {c.ci_low !== null && (
                        <span className="ml-1.5 text-xs text-muted">
                          [{formatDiff(c.ci_low, m.format)}, {formatDiff(c.ci_high, m.format)}]
                        </span>
                      )}
                      {!c.clear && <span className="ml-1.5 text-xs text-muted">not clear</span>}
                    </td>
                    <td className="px-4 py-1.5 tabular-nums text-muted">
                      {c.wins} / {c.losses} / {c.ties}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  );
}

const COLUMNS: [string, string, MetricInfo["format"]][] = [
  ["recall_at_k", "R@k", "percent"],
  ["mrr", "MRR", "ratio"],
  ["key_fact_recall", "Key facts", "percent"],
  ["grounding_score", "Grounding", "percent"],
  ["latency_ms", "Latency", "ms"],
];

function PerQuestion({ summary, rows }: { summary: ExperimentSummary; rows: RunRow[] }) {
  const [variant, setVariant] = useState(summary.variants[0]?.name ?? "");
  const [open, setOpen] = useState<string | null>(null);
  const shown = rows.filter((r) => r.variant === variant);
  return (
    <Panel
      title="Per question"
      aside={
        <select
          value={variant}
          onChange={(e) => setVariant(e.target.value)}
          className="rounded border border-line-strong bg-surface px-2 py-1 text-xs"
          aria-label="Variant"
        >
          {summary.variants.map((v) => (
            <option key={v.name}>{v.name}</option>
          ))}
        </select>
      }
    >
      <div className="-m-4 overflow-x-auto">
        <table className="w-full min-w-[720px] border-collapse text-sm">
          <thead>
            <tr className="border-b border-line bg-surface-2 text-left text-xs text-muted">
              <th className="px-4 py-2 font-medium">Item</th>
              <th className="px-4 py-2 font-medium">Status</th>
              {COLUMNS.map(([key, label]) => (
                <th key={key} className="px-3 py-2 font-medium">{label}</th>
              ))}
              <th className="px-3 py-2 font-medium">Tools</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((r) => {
              const id = `${r.item_id}-${r.repeat}`;
              return (
                <Fragment key={id}>
                  <tr
                    className="cursor-pointer border-b border-line hover:bg-surface-2"
                    onClick={() => setOpen(open === id ? null : id)}
                    aria-expanded={open === id}
                  >
                    <td className="px-4 py-1.5">
                      <span className="font-mono text-xs">{r.item_id}</span>{" "}
                      <span className="text-xs text-muted">{r.item_type}</span>
                    </td>
                    <td className="px-4 py-1.5">
                      <Badge tone={r.status === "succeeded" ? "ok" : r.status === "failed" ? "bad" : "warn"}>
                        {r.status === "insufficient_evidence" ? "abstained" : r.status === "succeeded" ? "answered" : r.status}
                      </Badge>
                    </td>
                    {COLUMNS.map(([key, , format]) => (
                      <td key={key} className="px-3 py-1.5 tabular-nums">
                        {formatMetric(r[key] as number | null, format)}
                      </td>
                    ))}
                    <td className="px-3 py-1.5 font-mono text-[11px] text-muted">
                      {(r.tools_used ?? []).join(", ") || "—"}
                    </td>
                  </tr>
                  {open === id && (
                    <tr className="border-b border-line bg-surface-2">
                      <td colSpan={COLUMNS.length + 3} className="px-4 py-2 text-sm">
                        <p>{r.question}</p>
                        {r.error && <p className="mt-1 text-bad">{r.error}</p>}
                        <p className="mt-1 text-xs text-muted">
                          {r.intent ? `intent ${r.intent} · ` : ""}
                          relevant passages at rank {((r.relevant_ranks as number[] | undefined) ?? []).join(", ") || "—"}
                          {r.run_id ? (
                            <>
                              {" · "}
                              <span className="font-mono">run {String(r.run_id).slice(0, 8)}</span> (in the evaluation database)
                            </>
                          ) : null}
                        </p>
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}
