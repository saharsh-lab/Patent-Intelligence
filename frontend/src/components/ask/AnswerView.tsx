"use client";

import type { ReactNode } from "react";

import { Badge, StatusBadge } from "@/components/ui";
import { type Inline, parseAnswer, parseInline, stripInterpretation } from "@/lib/citations";
import {
  type ClaimResult,
  splitByClaims,
  type Verification,
  VERDICT_LABEL,
  VERDICT_STYLE,
} from "@/lib/verification";
import { formatMs, formatPercent } from "@/lib/format";
import type { AskResponse } from "@/lib/types";

function CitationChip({ label, onClick }: { label: string; onClick: (label: string) => void }) {
  return (
    <button
      type="button"
      onClick={() => onClick(label)}
      // Reference style: a blue circled number that pops in with a spring
      className="pi-cite mx-[2px] inline-grid h-[1.45em] min-w-[1.45em] place-items-center rounded-full border-[1.5px] border-cite px-[3px] align-[0.2em] font-sans text-[0.68rem] leading-none font-semibold text-cite transition-colors hover:bg-cite hover:text-white"
      title={`Show evidence ${label}`}
      aria-label={`Show evidence ${label}`}
    >
      {label.replace(/^E/, "")}
    </button>
  );
}

export function renderInlines(inlines: Inline[], onCite: (label: string) => void): ReactNode[] {
  return inlines.map((part, i) => {
    switch (part.kind) {
      case "citation":
        return <CitationChip key={i} label={part.label} onClick={onCite} />;
      case "invalid-citation":
        return (
          <span
            key={i}
            className="mx-0.5 rounded-sm bg-bad-soft px-1 font-mono text-[11px] text-bad"
            title="The model cited a passage that was not provided. This citation was removed."
          >
            unverified
          </span>
        );
      case "bold":
        return <strong key={i}>{part.text}</strong>;
      default:
        return <span key={i}>{part.text}</span>;
    }
  });
}

function Metric({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <div title={hint}>
      <dt className="text-[11px] uppercase tracking-wide text-muted">{label}</dt>
      <dd className="font-mono text-sm">{value}</dd>
    </div>
  );
}

export function RunSummary({ run }: { run: AskResponse }) {
  const m = run.metrics;
  return (
    <div className="rounded border border-line bg-surface-2 px-4 py-3">
      <p className="text-sm">
        <span className="text-muted">Sources searched:</span> {run.summary.sources_searched.join(" + ")}
        <span className="mx-2 text-line-strong">|</span>
        <span className="text-muted">Passages retrieved:</span> {run.summary.passages_retrieved}
        <span className="mx-2 text-line-strong">|</span>
        <span className="text-muted">Cited:</span> {run.summary.passages_cited}
        {!run.summary.llm_called && (
          <>
            <span className="mx-2 text-line-strong">|</span>
            <span className="text-muted">LLM not called (no relevant evidence)</span>
          </>
        )}
      </p>
      <dl className="mt-3 grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-4 lg:grid-cols-7">
        <Metric label="Latency" value={formatMs(m.latency_ms)} hint={Object.entries(m.timings_ms).map(([k, v]) => `${k}: ${v} ms`).join("\n")} />
        <Metric
          label={run.pipeline === "agentic" ? "Tools" : "Retrieval"}
          value={formatMs(
            Object.entries(m.timings_ms)
              .filter(([step]) => step !== "generate")
              .reduce((total, [, ms]) => total + ms, 0),
          )}
        />
        <Metric label="Generation" value={formatMs(m.timings_ms.generate)} />
        <Metric label="Tokens in / out" value={m.prompt_tokens != null ? `${m.prompt_tokens} / ${m.completion_tokens}` : "—"} />
        <Metric
          label="Citation coverage"
          value={formatPercent(m.citation_coverage)}
          hint="Share of answer sentences that cite evidence (does not check that the evidence supports them; see Grounding)."
        />
        <Metric
          label="Grounding"
          value={formatPercent(run.grounding_score)}
          hint="Claim-level verification: (supported + 0.5 × partly supported) ÷ checked statements."
        />
        <Metric label="Est. cost" value={m.cost_usd != null ? `$${m.cost_usd.toFixed(4)}` : "—"} />
      </dl>
    </div>
  );
}

export function Highlighted({
  raw,
  claims,
  onCite,
}: {
  raw: string;
  claims: ClaimResult[];
  onCite: (label: string) => void;
}) {
  return (
    <>
      {splitByClaims(raw, claims).map((segment, i) =>
        segment.claim ? (
          <span
            key={i}
            className={`rounded-sm ${VERDICT_STYLE[segment.claim.verdict]}`}
            title={`${VERDICT_LABEL[segment.claim.verdict]}: ${segment.claim.reason}`}
          >
            {renderInlines(parseInline(segment.text), onCite)}
          </span>
        ) : (
          <span key={i}>{renderInlines(parseInline(segment.text), onCite)}</span>
        ),
      )}
    </>
  );
}

export function AnswerView({ run, onCite }: { run: AskResponse; onCite: (label: string) => void }) {
  const body = run.answer ? stripInterpretation(run.answer) : "";
  const blocks = parseAnswer(body);
  const verification = run.verification as unknown as Verification | null | undefined;
  const claims = (verification?.claims ?? []).filter((c) => c.location === "answer");

  return (
    <article className="rounded border border-line bg-surface">
      <header className="flex flex-wrap items-center gap-2 border-b border-line px-4 py-2.5">
        <StatusBadge status={run.status} />
        <Badge>{run.pipeline === "baseline_rag" ? "Baseline RAG" : "Agent"}</Badge>
        {run.metrics.invalid_citations.length > 0 && (
          <Badge tone="bad">{run.metrics.invalid_citations.length} fabricated citation(s) removed</Badge>
        )}
      </header>
      <div className="px-4 py-4">
        <p className="mb-3 text-sm text-muted">{run.question}</p>
        {run.legal_question && (
          <p className="mb-3 rounded border border-warn/40 bg-warn-soft px-3 py-2 text-sm">
            This question asks for a legal opinion (e.g. validity or infringement). The system cannot
            provide one; it reports technical information from the evidence only.
          </p>
        )}

        {run.status === "succeeded" && (
          <>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">
              Answer from evidence
            </p>
            <div className="space-y-3 leading-relaxed">
              {blocks.map((block, i) =>
                block.kind === "list" ? (
                  <ul key={i} className="list-disc space-y-1 pl-5">
                    {block.raws.map((raw, j) => (
                      <li key={j}>
                        <Highlighted raw={raw} claims={claims} onCite={onCite} />
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p key={i}>
                    <Highlighted raw={block.raw} claims={claims} onCite={onCite} />
                  </p>
                ),
              )}
              {claims.some((c) => c.verdict !== "supported") && (
                <p className="flex flex-wrap gap-3 pt-1 text-xs text-muted">
                  <span className={`rounded-sm px-1 ${VERDICT_STYLE.partially_supported}`}>partly supported</span>
                  <span className={`rounded-sm px-1 ${VERDICT_STYLE.unsupported}`}>not supported by the evidence</span>
                  <span>Hover a sentence for the reason.</span>
                </p>
              )}
            </div>
            {run.interpretation && (
              <div className="mt-4 border-l-2 border-warn bg-warn-soft px-3 py-2">
                <p className="text-xs font-semibold uppercase tracking-wide text-warn">
                  Model interpretation: not directly stated in the evidence
                </p>
                <p className="mt-1 text-sm">{run.interpretation}</p>
              </div>
            )}
          </>
        )}

        {run.status === "insufficient_evidence" && (
          <div className="border-l-2 border-warn bg-warn-soft px-3 py-2">
            <p className="font-medium">I could not find sufficient evidence to answer this reliably.</p>
            {run.insufficient_reason && <p className="mt-1 text-sm text-muted">{run.insufficient_reason}</p>}
          </div>
        )}

        {run.status === "failed" && (
          <div className="border-l-2 border-bad bg-bad-soft px-3 py-2 text-sm">
            <p className="font-medium text-bad">This run failed.</p>
            {run.error_message && <p className="mt-1">{run.error_message}</p>}
          </div>
        )}
      </div>
    </article>
  );
}
