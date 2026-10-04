"use client";

import { Badge, Panel } from "@/components/ui";
import { formatMs } from "@/lib/format";
import type { AskResponse } from "@/lib/types";

const INTENT_LABELS: Record<string, string> = {
  document_qa: "Question about indexed documents",
  patent_lookup: "Look up a specific patent",
  find_similar: "Find potentially relevant patents",
  compare: "Compare patents",
  out_of_scope: "Outside patent research",
};

const TOOL_LABELS: Record<string, string> = {
  search_uploaded_documents: "Searched indexed documents and patents",
  retrieve_evidence: "Retrieved evidence from the selected sources",
  retrieve_document_section: "Read the requested section directly",
  search_patents: "Searched patent databases",
  get_patent_details: "Fetched and indexed a patent",
  compare_patents: "Collected balanced evidence from each patent",
  extract_key_concepts: "Extracted key technical concepts",
};

const PLANNER_LABELS: Record<string, string> = {
  rules: "rule-based",
  llm: "LLM",
  llm_fallback_rules: "rule-based (LLM reply was invalid)",
};

/** User-facing account of what the agent did. Shows actions and results, never hidden reasoning. */
export function WorkflowPanel({ run }: { run: AskResponse }) {
  if (run.pipeline !== "agentic") return null;
  const targets = run.targets ?? [];
  const steps = run.steps ?? [];
  const recoveries = run.recoveries ?? [];
  return (
    <Panel
      title="How this answer was produced"
      aside={run.planner && <span className="text-xs text-muted">Question analysed by {PLANNER_LABELS[run.planner] ?? run.planner} planner</span>}
    >
      <div className="mb-3 flex flex-wrap items-center gap-2 text-sm">
        <span className="text-muted">Task:</span>
        <Badge tone="accent">{INTENT_LABELS[run.intent ?? ""] ?? run.intent}</Badge>
        {targets.length > 0 && (
          <>
            <span className="ml-2 text-muted">About:</span>
            {targets.map((t, i) => (
              <Badge key={i}>{String(t.label)}</Badge>
            ))}
          </>
        )}
      </div>

      {steps.length === 0 ? (
        <p className="text-sm text-muted">No tools were needed.</p>
      ) : (
        <ol className="space-y-1.5">
          {steps.map((step) => (
            <li key={step.step_index} className="flex gap-3 text-sm">
              <span
                className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full font-mono text-[11px] ${
                  step.success ? "bg-ok-soft text-ok" : "bg-bad-soft text-bad"
                }`}
                aria-label={step.success ? "succeeded" : "failed"}
              >
                {step.success ? "✓" : "✗"}
              </span>
              <div className="min-w-0 flex-1">
                <p>
                  {TOOL_LABELS[step.tool_name] ?? step.tool_name}{" "}
                  <code className="font-mono text-[11px] text-muted">{step.tool_name}</code>
                </p>
                {step.output_summary && (
                  <p className={`text-xs ${step.success ? "text-muted" : "text-bad"}`}>{step.output_summary}</p>
                )}
              </div>
              <span className="shrink-0 font-mono text-xs text-muted">{formatMs(step.latency_ms)}</span>
            </li>
          ))}
        </ol>
      )}

      {recoveries.length > 0 && (
        <div className="mt-3 rounded bg-surface-2 px-3 py-2 text-xs">
          <p className="font-medium">Recovery</p>
          <ul className="mt-0.5 list-disc pl-4 text-muted">
            {recoveries.map((r) => <li key={r}>{r}</li>)}
          </ul>
        </div>
      )}
    </Panel>
  );
}
