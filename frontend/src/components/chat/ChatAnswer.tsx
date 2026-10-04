"use client";

import { Highlighted, renderInlines } from "@/components/ask/AnswerView";
import { parseAnswer, parseInline, stripInterpretation } from "@/lib/citations";
import type { AskResponse } from "@/lib/types";
import type { Verification } from "@/lib/verification";

/** Plain-language summary of the sentence checks, e.g. "9 of 10 statements supported". */
export function trustSummary(verification: Verification | null | undefined) {
  const claims = verification?.claims ?? [];
  if (claims.length === 0) return null;
  const supported = claims.filter((c) => c.verdict === "supported").length;
  const unsupported = claims.filter((c) => c.verdict === "unsupported").length;
  const tone: "ok" | "warn" | "bad" = unsupported === 0 && supported === claims.length ? "ok" : unsupported / claims.length > 0.3 ? "bad" : "warn";
  return { supported, unsupported, partial: claims.length - supported - unsupported, total: claims.length, tone };
}

/** The answer itself, kept calm: text with source numbers; checks only on request. */
export function ChatAnswer({ run, onCite, showChecks }: { run: AskResponse; onCite: (label: string) => void; showChecks: boolean }) {
  const verification = run.verification as unknown as Verification | null | undefined;
  const claims = (verification?.claims ?? []).filter((c) => c.location === "answer");
  const blocks = parseAnswer(run.answer ? stripInterpretation(run.answer) : "");

  const line = (raw: string) =>
    showChecks ? <Highlighted raw={raw} claims={claims} onCite={onCite} /> : <>{renderInlines(parseInline(raw), onCite)}</>;

  return (
    // Paragraphs arrive one after another (stagger), citations pop in (pi-cite)
    <div className="stagger space-y-3 font-serif text-[1.08rem] leading-[1.65]">
      {run.legal_question && (
        <p className="rounded-lg bg-warn-soft px-3 py-2 text-sm text-warn">
          This asks for a legal opinion, which I can&apos;t give. Below is technical information from the sources only.
        </p>
      )}

      {run.status === "succeeded" &&
        blocks.map((block, i) =>
          block.kind === "list" ? (
            <ul key={i} className="list-disc space-y-1 pl-5 marker:text-cite">
              {block.raws.map((raw, j) => (
                <li key={j}>{line(raw)}</li>
              ))}
            </ul>
          ) : (
            <p key={i}>{line(block.raw)}</p>
          ),
        )}

      {run.status === "succeeded" && run.interpretation && (
        <p className="border-l-2 border-warn pl-3 text-sm text-muted">
          <span className="font-medium text-warn">My interpretation (not stated in the sources): </span>
          {run.interpretation}
        </p>
      )}

      {run.status === "insufficient_evidence" && (
        <div>
          <p>I couldn&apos;t find this in your documents, so I won&apos;t guess.</p>
          {run.insufficient_reason && <p className="mt-1 text-sm text-muted">{run.insufficient_reason}</p>}
        </div>
      )}

      {run.status === "failed" && (
        <p className="text-bad">Something went wrong while answering. {run.error_message ?? ""}</p>
      )}
    </div>
  );
}
