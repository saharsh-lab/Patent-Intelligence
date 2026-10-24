"use client";

import { renderInlines } from "@/components/ask/AnswerView";
import { AnswerBlocks } from "@/components/chat/AnswerBlocks";
import { parseAnswer, parseInline, stripInterpretation } from "@/lib/citations";
import type { AskResponse } from "@/lib/types";
import type { ClaimResult, Verification } from "@/lib/verification";

import { type XRaySelection, XRayText, useDeveloped } from "@/components/chat/XRay";

/** Plain-language summary of the sentence checks, e.g. "9 of 10 statements supported". */
export function trustSummary(verification: Verification | null | undefined) {
  const claims = verification?.claims ?? [];
  if (claims.length === 0) return null;
  const supported = claims.filter((c) => c.verdict === "supported").length;
  const unsupported = claims.filter((c) => c.verdict === "unsupported").length;
  const tone: "ok" | "warn" | "bad" = unsupported === 0 && supported === claims.length ? "ok" : unsupported / claims.length > 0.3 ? "bad" : "warn";
  return { supported, unsupported, partial: claims.length - supported - unsupported, total: claims.length, tone };
}

type XRayMode = { selected: XRaySelection; onSelect: (s: XRaySelection) => void; planted?: ClaimResult };

/** The answer itself, kept calm: text with source numbers. In X-ray mode every checked
 *  sentence is coloured by its verdict and opens the passage it was checked against. */
export function ChatAnswer({
  run,
  onCite,
  xray,
  instant = false,
}: {
  run: AskResponse;
  onCite: (label: string) => void;
  xray?: XRayMode | null;
  /** Just watched being written: no entrance animation */
  instant?: boolean;
}) {
  const verification = run.verification as unknown as Verification | null | undefined;
  const claims = (verification?.claims ?? []).filter((c) => c.location === "answer");
  const blocks = parseAnswer(run.answer ? stripInterpretation(run.answer) : "");
  const developed = useDeveloped(!!xray);

  const line = (raw: string) =>
    xray ? (
      <XRayText raw={raw} claims={claims} selected={xray.selected} onSelect={xray.onSelect} planted={xray.planted} />
    ) : (
      <>{renderInlines(parseInline(raw), onCite)}</>
    );

  return (
    // Paragraphs arrive one after another (stagger), citations pop in (pi-cite)
    <div
      className={`${instant ? "" : "stagger"} relative space-y-3 text-[0.98rem] leading-7 ${xray ? "xr-on" : ""} ${developed ? "xr-developed" : ""}`}
    >
      {xray && <span aria-hidden className="xr-scan" />}
      {run.legal_question && (
        <p className="rounded-lg bg-warn-soft px-3 py-2 text-sm text-warn">
          This asks for a legal opinion, which I can&apos;t give. Below is technical information from the sources only.
        </p>
      )}

      {(run.status === "succeeded" || run.status === "stopped") && <AnswerBlocks blocks={blocks} line={line} />}

      {run.status === "succeeded" && run.interpretation && (
        <p className="border-l-2 border-warn pl-3 text-sm text-muted">
          <span className="font-medium text-warn">My interpretation (not stated in the sources): </span>
          {run.interpretation}
        </p>
      )}

      {run.status === "stopped" && !run.answer && <p className="text-muted">Stopped before any text was written.</p>}

      {run.status === "insufficient_evidence" && (
        <div>
          <p>
            {/could not be reached/i.test(run.insufficient_reason ?? "")
              ? "I couldn't reach my sources just now, so I won't guess."
              : "I couldn't find this in your documents or sources, so I won't guess."}
          </p>
          {run.insufficient_reason && <p className="mt-1 text-sm text-muted">{run.insufficient_reason}</p>}
        </div>
      )}

      {run.status === "failed" && (
        <p className="text-bad">Something went wrong while answering. {run.error_message ?? ""}</p>
      )}
    </div>
  );
}
