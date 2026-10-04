import { Badge, Panel } from "@/components/ui";
import { formatMetric, type SelfCheckRow, type SelfCheckSummary } from "@/lib/evaluation";
import { formatDateTime } from "@/lib/format";

/** Experiment S: each patent's own claim analysed as a new invention (no labels needed). */
export function SelfCheckView({ summary, rows }: { summary: SelfCheckSummary; rows: SelfCheckRow[] }) {
  const metrics = Object.entries(summary.results);
  return (
    <div className="space-y-5">
      <section className="rounded border border-line bg-surface px-4 py-3">
        <div className="flex flex-wrap items-baseline gap-x-3">
          <h2 className="font-mono text-sm font-semibold">{summary.experiment}</h2>
          <span className="text-xs text-muted">{formatDateTime(summary.finished_at)}</span>
        </div>
        {summary.description && <p className="mt-1 text-sm">{summary.description}</p>}
        <div className="mt-2 flex flex-wrap gap-1.5">
          <Badge>{summary.dataset.items} patents</Badge>
          <Badge>{summary.dataset.name}</Badge>
          <Badge>verifier {summary.verifier}</Badge>
          <Badge>{summary.models.llm}</Badge>
          <Badge tone="ok">no labels needed</Badge>
        </div>
        {summary.warnings.length > 0 && (
          <ul className="mt-3 rounded border border-warn/30 bg-warn-soft px-3 py-2 text-xs text-warn">
            {summary.warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        )}
      </section>

      <Panel title="Results">
        <div className="-m-4 overflow-x-auto">
          <table className="w-full min-w-[480px] border-collapse text-sm">
            <thead>
              <tr className="border-b border-line bg-surface-2 text-left text-xs text-muted">
                <th className="px-4 py-2 font-medium">Metric</th>
                <th className="px-4 py-2 font-medium">Mean [95% CI]</th>
                <th className="px-4 py-2 font-medium">n</th>
              </tr>
            </thead>
            <tbody>
              {metrics.map(([key, m]) => {
                const format = key.includes("latency") ? "ms" : "percent";
                return (
                  <tr key={key} className="border-b border-line last:border-0 tabular-nums">
                    <td className="px-4 py-1.5">{m.label.replace(/ \(ms\)$/, "")}</td>
                    <td className="px-4 py-1.5">
                      {formatMetric(m.mean, format)}
                      {m.ci_low !== null && (
                        <span className="ml-1.5 text-xs text-muted">
                          [{formatMetric(m.ci_low, format)}, {formatMetric(m.ci_high, format)}]
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-1.5">{m.n}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Panel>

      <Panel title="Per patent">
        <div className="-m-4 overflow-x-auto">
          <table className="w-full min-w-[640px] border-collapse text-sm">
            <thead>
              <tr className="border-b border-line bg-surface-2 text-left text-xs text-muted">
                <th className="px-4 py-2 font-medium">Patent</th>
                <th className="px-4 py-2 font-medium">Domain</th>
                <th className="px-4 py-2 font-medium">Self rank</th>
                <th className="px-4 py-2 font-medium">Own features found</th>
                <th className="px-4 py-2 font-medium">Closest other documents</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.doc} className="border-b border-line align-top last:border-0">
                  <td className="px-4 py-1.5 font-medium">{r.doc}</td>
                  <td className="px-4 py-1.5 text-muted">{r.domain.replace(/_/g, " ")}</td>
                  <td className="px-4 py-1.5 tabular-nums">
                    <Badge tone={r.self_rank === 1 ? "ok" : "warn"}>{r.self_rank ?? "not found"}</Badge>
                  </td>
                  <td className="px-4 py-1.5 tabular-nums">{formatMetric(r.self_coverage ?? null, "percent")}</td>
                  <td className="px-4 py-1.5 font-mono text-xs text-muted">{r.top_candidates.join(", ") || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
