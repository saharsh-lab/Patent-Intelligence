"use client";

import { Badge, Panel } from "@/components/ui";
import { formatPercent } from "@/lib/format";
import type { AskResponse } from "@/lib/types";
import { type Verification, type VerificationAttempt, VERDICT_LABEL } from "@/lib/verification";

const METHOD: Record<string, string> = {
  nli: "NLI entailment model",
  llm_judge: "LLM judge",
  lexical: "word overlap (baseline)",
};

function tone(score: number | null | undefined) {
  if (score == null) return "neutral" as const;
  return score >= 0.8 ? ("ok" as const) : score >= 0.5 ? ("warn" as const) : ("bad" as const);
}

/** Claim-level verification: grounding score, regeneration history, and the claims at issue. */
export function VerificationPanel({ run, onCite }: { run: AskResponse; onCite: (label: string) => void }) {
  const verification = run.verification as unknown as Verification | null | undefined;
  if (!verification) return null;
  const attempts = (run.verification_attempts ?? []) as unknown as VerificationAttempt[];
  const issues = verification.claims.filter((c) => c.verdict !== "supported");
  const c = verification.counts;

  return (
    <Panel
      title="Claim verification"
      aside={<span className="text-xs text-muted">Checked with {METHOD[verification.method] ?? verification.method}</span>}
    >
      <div className="flex flex-wrap items-center gap-3">
        <Badge tone={tone(verification.grounding_score)}>
          Grounding {formatPercent(verification.grounding_score)}
        </Badge>
        <span className="text-sm text-muted">
          {verification.claims.length} statements checked: {c.supported} supported, {c.partially_supported} partly,{" "}
          {c.unsupported} unsupported
          {c.misattributed > 0 && `, ${c.misattributed} cited the wrong passage`}
        </span>
      </div>

      {attempts.length > 1 && (
        <ol className="mt-3 flex flex-wrap items-center gap-2 text-xs">
          {attempts.map((a, i) => (
            <li key={a.attempt} className="flex items-center gap-2">
              {i > 0 && <span className="text-muted">→ regenerated with feedback →</span>}
              <span className={`rounded border px-2 py-1 ${a.kept ? "border-accent bg-accent-soft" : "border-line text-muted"}`}>
                Attempt {a.attempt}: {formatPercent(a.grounding_score)}
                {a.kept ? " (shown)" : " (discarded)"}
              </span>
            </li>
          ))}
        </ol>
      )}

      {issues.length > 0 ? (
        <ul className="mt-3 space-y-2">
          {issues.map((claim) => (
            <li key={`${claim.location}-${claim.index}`} className="rounded border border-line px-3 py-2 text-sm">
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone={claim.verdict === "unsupported" ? "bad" : "warn"}>{VERDICT_LABEL[claim.verdict]}</Badge>
                {claim.location !== "answer" && <span className="font-mono text-[11px] text-muted">{claim.location}</span>}
              </div>
              <p className="mt-1">{claim.text}</p>
              <p className="mt-0.5 text-xs text-muted">
                {claim.reason}
                {claim.supporting.length > 0 && " · evidence: "}
                {claim.supporting.map((label) => (
                  <button key={label} type="button" onClick={() => onCite(label)} className="mx-0.5 font-mono text-accent hover:underline">
                    {label}
                  </button>
                ))}
              </p>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-3 text-sm text-ok">Every checked statement is supported by the passage it cites.</p>
      )}
      <p className="mt-3 text-xs text-muted">
        Automatic verification can be wrong in both directions; it flags statements to double-check, not final judgements.
      </p>
    </Panel>
  );
}
