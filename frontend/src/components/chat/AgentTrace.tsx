"use client";

import { useEffect, useState } from "react";
import useSWR from "swr";

import { ScanStatus } from "@/components/search/LoadingState";
import { fetcher } from "@/lib/api";
import { formatMs } from "@/lib/format";
import type { ProgressOut as Progress, TraceStep } from "@/lib/types";

function Marker({ step }: { step: TraceStep }) {
  const size = step.kind === "tool" ? "h-3.5 w-3.5" : "h-[18px] w-[18px]";
  if (step.status === "running")
    return <span className={`${size} block animate-spin rounded-full border-2 border-cite border-t-transparent`} aria-label="running" />;
  if (step.status === "failed")
    return (
      <span className={`${size} grid place-items-center rounded-full bg-bad text-[10px] leading-none text-white`} aria-label="failed">
        ✕
      </span>
    );
  return (
    <span className={`${size} grid place-items-center rounded-full bg-ok text-[10px] leading-none text-white`} aria-label="done">
      ✓
    </span>
  );
}

/** The agent's path for one answer: stages, the tools it picked and why, and timings. */
export function AgentTrace({ steps, live = false }: { steps: TraceStep[]; live?: boolean }) {
  return (
    <ol className="relative isolate space-y-2.5 before:absolute before:top-2 before:bottom-2 before:left-[8px] before:w-px before:bg-line" aria-live={live ? "polite" : undefined}>
      {steps.map((step, i) => (
        <li key={`${step.name}-${step.at_ms}-${i}`} className={`pi-in relative flex gap-3 ${step.kind === "tool" ? "pl-6" : ""}`}>
          <span className={`relative z-10 mt-[3px] grid shrink-0 place-items-center bg-surface ${step.kind === "tool" ? "h-[18px] w-[18px]" : ""}`}>
            <Marker step={step} />
          </span>
          <div className="min-w-0 flex-1">
            <p className="flex flex-wrap items-baseline gap-x-2 text-sm">
              <span className={step.kind === "step" ? "font-medium" : ""}>{step.label}</span>
              {step.kind === "tool" && <code className="font-mono text-[10.5px] text-muted">{step.name}</code>}
              <span className="ml-auto font-mono text-[11px] text-muted tabular-nums">
                {step.status === "running" ? "…" : formatMs(step.ms)}
              </span>
            </p>
            {step.why && <p className="text-xs text-muted italic">Why: {step.why}</p>}
            {step.detail && (
              <p className={`text-xs ${step.status === "failed" ? "text-bad" : "text-muted"}`}>{step.detail}</p>
            )}
          </div>
        </li>
      ))}
    </ol>
  );
}

/** Summary line for a finished trace. */
export function traceSummary(steps: TraceStep[]) {
  const last = steps.at(-1);
  const total = last ? last.at_ms + (last.ms ?? 0) : 0;
  const tools = steps.filter((s) => s.kind === "tool").length;
  const rewrites = steps.filter((s) => s.name === "regenerate").length;
  return `${formatMs(total)} in total · ${tools} tool call${tools === 1 ? "" : "s"}${rewrites ? ` · rewritten ${rewrites}×` : ""}`;
}

function useElapsed(since: number) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);
  return Math.max(0, Math.floor((now - since) / 1000));
}

/** While an answer is being written: the agent's steps as they happen (polled each second).
 *  Until the first step arrives (or for the baseline pipeline), the plain progress box. */
export function LiveTrace({ conversationId, since, stages }: { conversationId: string | null; since?: number; stages: string[] }) {
  const [mountedAt] = useState(() => Date.now()); // asked just now, unless told otherwise
  const { data } = useSWR<Progress>(conversationId ? `/conversations/${conversationId}/progress` : null, fetcher, {
    refreshInterval: 1000,
    dedupingInterval: 500,
  });
  const started = since ?? mountedAt;
  const elapsed = useElapsed(started);
  // A finished trace here belongs to the previous answer: wait for this one's first step
  const steps = data?.running ? data.steps : [];
  if (!steps.length) return <ScanStatus height={84} stages={stages} since={started} className="pi-in min-w-0 flex-1 text-sm" />;
  return (
    <div className="pi-in min-w-0 flex-1 border border-line bg-surface px-4 py-3">
      <p className="mb-2.5 flex items-center gap-2 text-xs text-muted">
        <span className="font-semibold tracking-wide text-text uppercase">Agent at work</span>
        <span className="ml-auto font-mono tabular-nums">{elapsed}s</span>
      </p>
      <AgentTrace steps={steps} live />
      {elapsed >= 25 && <p className="mt-2.5 text-[11px] text-muted">Checking every sentence with the local model can take a minute or two.</p>}
    </div>
  );
}
