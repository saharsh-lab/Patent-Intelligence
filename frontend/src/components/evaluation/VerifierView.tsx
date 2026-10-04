import { Badge, Panel } from "@/components/ui";
import { VERDICTS, type VerifierSummary } from "@/lib/evaluation";
import { formatDateTime } from "@/lib/format";

const SHORT: Record<string, string> = {
  supported: "supported",
  partially_supported: "partial",
  unsupported: "unsupported",
};
const ABBR: Record<string, string> = {
  supported: "sup.",
  partially_supported: "part.",
  unsupported: "unsup.",
};

const f = (v: number | null | undefined, digits = 3) =>
  v === null || v === undefined ? "—" : v.toFixed(digits);

/** Experiment I: agreement of each verifier method with human verdicts. */
export function VerifierView({ summary }: { summary: VerifierSummary }) {
  const methods = Object.entries(summary.methods);
  return (
    <div className="space-y-5">
      <section className="rounded border border-line bg-surface px-4 py-3">
        <div className="flex flex-wrap items-baseline gap-x-3">
          <h2 className="font-mono text-sm font-semibold">
            {summary.experiment}
          </h2>
          <span className="text-xs text-muted">
            {formatDateTime(summary.finished_at)}
          </span>
        </div>
        {summary.description && (
          <p className="mt-1 text-sm">{summary.description}</p>
        )}
        <div className="mt-2 flex flex-wrap gap-1.5">
          <Badge>{summary.labels.n} labelled statements</Badge>
          {VERDICTS.map((v) => (
            <Badge key={v}>
              {SHORT[v]} {summary.labels.distribution[v] ?? 0}
            </Badge>
          ))}
        </div>
        {summary.warnings.length > 0 && (
          <ul className="mt-3 rounded border border-warn/30 bg-warn-soft px-3 py-2 text-xs text-warn">
            {summary.warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        )}
      </section>

      <Panel title="Agreement with human labels">
        <div className="-m-4 overflow-x-auto">
          <table className="w-full min-w-[640px] border-collapse text-sm">
            <thead>
              <tr className="border-b border-line bg-surface-2 text-left text-xs text-muted">
                <th className="px-4 py-2 font-medium">Method</th>
                <th className="px-4 py-2 font-medium">Accuracy [95% CI]</th>
                <th
                  className="px-4 py-2 font-medium"
                  title="Agreement corrected for chance: 0 = chance, 1 = perfect"
                >
                  Cohen&apos;s κ
                </th>
                <th className="px-4 py-2 font-medium">Macro-F1</th>
                <th
                  className="px-4 py-2 font-medium"
                  title="Positive class: statements humans judged unsupported"
                >
                  Hallucination detection P / R / F1
                </th>
                <th className="px-4 py-2 font-medium">ms / statement</th>
              </tr>
            </thead>
            <tbody>
              {methods.map(([method, m]) => (
                <tr
                  key={method}
                  className="border-b border-line last:border-0 tabular-nums"
                >
                  <td className="px-4 py-1.5">
                    <span className="font-medium">{method}</span>
                    {m.model && (
                      <span className="ml-1.5 font-mono text-[11px] text-muted">
                        {m.model}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-1.5">
                    {f(m.accuracy)}
                    {m.accuracy_ci.ci_low !== null && (
                      <span className="ml-1.5 text-xs text-muted">
                        [{f(m.accuracy_ci.ci_low)}, {f(m.accuracy_ci.ci_high)}]
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-1.5">{f(m.cohen_kappa)}</td>
                  <td className="px-4 py-1.5">{f(m.macro_f1)}</td>
                  <td className="px-4 py-1.5">
                    {f(m.detection.precision, 2)} / {f(m.detection.recall, 2)} /{" "}
                    {f(m.detection.f1, 2)}
                  </td>
                  <td className="px-4 py-1.5">{Math.round(m.ms_per_claim)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {methods.map(([method, m]) => (
          <Panel key={method} title={`Confusion matrix — ${method}`}>
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-center text-xs tabular-nums">
                <thead>
                  <tr>
                    <th className="p-1 text-left font-medium text-muted">
                      human ↓ verifier →
                    </th>
                    {VERDICTS.map((v) => (
                      <th
                        key={v}
                        className="p-1 font-medium text-muted"
                        title={SHORT[v]}
                      >
                        {ABBR[v]}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {VERDICTS.map((h) => (
                    <tr key={h}>
                      <th className="p-1 text-left font-medium text-muted">
                        {SHORT[h]}
                      </th>
                      {VERDICTS.map((p) => (
                        <td
                          key={p}
                          className={`border border-line p-1.5 ${h === p ? "bg-ok-soft font-semibold text-ok" : m.confusion[h][p] ? "bg-bad-soft text-bad" : ""}`}
                        >
                          {m.confusion[h][p]}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
        ))}
      </div>
    </div>
  );
}
