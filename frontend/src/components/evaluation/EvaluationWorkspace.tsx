"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import useSWR from "swr";

import { ExperimentView } from "@/components/evaluation/ExperimentView";
import { VerifierView } from "@/components/evaluation/VerifierView";
import { Badge, EmptyState, ErrorNotice, Spinner } from "@/components/ui";
import { fetcher } from "@/lib/api";
import type { EvaluationListItem, EvaluationResult } from "@/lib/evaluation";
import { formatDateTime } from "@/lib/format";

const key = (e: EvaluationListItem) => `${e.experiment}/${e.run}`;

export function EvaluationWorkspace() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const list = useSWR<EvaluationListItem[]>("/evaluations", fetcher);
  const entries = list.data ?? [];
  const selected = params.get("r") ?? (entries[0] ? key(entries[0]) : null);
  const result = useSWR<EvaluationResult>(selected ? `/evaluations/${selected}` : null, fetcher);

  if (list.error) return <ErrorNotice error={list.error} title="Could not load results" />;
  if (list.isLoading) return <Spinner label="Loading results…" />;
  if (entries.length === 0) return <HowToRun />;

  const groups = Object.entries(
    entries.reduce<Record<string, EvaluationListItem[]>>((acc, e) => {
      (acc[e.experiment] ??= []).push(e);
      return acc;
    }, {}),
  );

  return (
    <div className="grid gap-6 lg:grid-cols-[16rem_minmax(0,1fr)]">
      <nav aria-label="Experiment results" className="space-y-4">
        {groups.map(([experiment, runs]) => (
          <div key={experiment}>
            <h2 className="mb-1 font-mono text-xs font-semibold text-muted">{experiment}</h2>
            <ul className="space-y-1">
              {runs.map((e) => {
                const active = key(e) === selected;
                return (
                  <li key={e.run}>
                    <button
                      type="button"
                      onClick={() => router.replace(`${pathname}?r=${encodeURIComponent(key(e))}`, { scroll: false })}
                      aria-current={active ? "true" : undefined}
                      className={`w-full rounded border px-2.5 py-1.5 text-left text-sm ${
                        active ? "border-accent bg-accent-soft" : "border-line bg-surface hover:bg-surface-2"
                      }`}
                    >
                      <span className="block font-medium">
                        {e.finished_at ? formatDateTime(e.finished_at) : e.run}
                      </span>
                      <span className="mt-0.5 flex flex-wrap items-center gap-1 text-xs text-muted">
                        {e.kind === "verifier" ? `${e.n} labels` : `${e.n} questions`} ·{" "}
                        {e.variants.join(" vs ")}
                        {e.synthetic && <Badge tone="warn">synthetic</Badge>}
                        {!e.synthetic && e.draft_labels && <Badge tone="warn">draft labels</Badge>}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      <div className="min-w-0">
        {result.error && <ErrorNotice error={result.error} title="Could not load this result" />}
        {result.isLoading && <Spinner label="Loading result…" />}
        {result.data &&
          (result.data.summary.kind === "verifier" ? (
            <VerifierView summary={result.data.summary} />
          ) : (
            <ExperimentView summary={result.data.summary} rows={result.data.rows} />
          ))}
      </div>
    </div>
  );
}

function HowToRun() {
  return (
    <EmptyState title="No experiment results yet">
      <p>Experiments run from the command line and write their results to experiments/results/.</p>
      <pre className="mx-auto mt-3 max-w-xl overflow-x-auto rounded bg-surface-2 px-3 py-2 text-left font-mono text-xs text-text">
        {`cd backend
.venv/bin/python -m app.evaluation run --config ../experiments/configs/smoke.yaml`}
      </pre>
    </EmptyState>
  );
}
