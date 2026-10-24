"use client";

import { useRef } from "react";
import useSWR from "swr";

import { useFollow } from "@/components/chat/LiveAnswer";

import { chat, QUICK_ACTIONS } from "@/lib/chat";

const CHIP =
  "lv-chip rounded-full border border-line bg-surface px-3.5 py-1.5 text-left text-[0.85rem] text-text transition-colors hover:border-line-strong hover:bg-surface-2 disabled:opacity-50";

/**
 * Under the latest answer: questions to ask next (written by the model once the answer is
 * shown, so they never delay it) and quick ways to continue. For a greeting or a question
 * about the assistant, example questions instead.
 */
export function FollowUps({
  conversationId,
  runId,
  onAsk,
  busy,
  examples,
}: {
  conversationId: string;
  runId: string;
  onAsk: (message: string) => void;
  busy: boolean;
  /** Fixed questions to offer instead of written ones (after small talk) */
  examples?: string[];
}) {
  const { data, isLoading } = useSWR(examples ? null : ["suggestions", conversationId, runId], () => chat.suggestions(conversationId, runId), {
    revalidateOnFocus: false,
    revalidateIfStale: false,
    shouldRetryOnError: false,
  });
  const questions = examples ?? data?.suggestions ?? [];
  const box = useRef<HTMLDivElement>(null);
  useFollow(box, questions.length); // they arrive after the answer: bring them into view

  return (
    <div ref={box} className="scroll-mb-28 space-y-2 pt-1">
      {(isLoading || questions.length > 0) && (
        <div>
          <p className="mb-1.5 text-[11px] font-semibold tracking-wide text-muted uppercase">{examples ? "Try asking" : "Ask next"}</p>
          {isLoading ? (
            <p className="flex items-center gap-2 text-xs text-muted">
              <span className="pi-busy" aria-hidden /> Thinking of follow-up questions…
            </p>
          ) : (
            <div className="flex flex-wrap gap-1.5">
              {questions.map((q, i) => (
                <button key={q} type="button" disabled={busy} onClick={() => onAsk(q)} className={CHIP} style={{ animationDelay: `${i * 80}ms` }}>
                  {q}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
      {!examples && (
        <div className="flex flex-wrap items-center gap-x-1 text-xs text-muted">
          <span className="mr-1">Make it:</span>
          {QUICK_ACTIONS.map((action, i) => (
            <span key={action.label} className="flex items-center gap-1">
              {i > 0 && <span aria-hidden>·</span>}
              <button
                type="button"
                disabled={busy}
                onClick={() => onAsk(action.message)}
                className="underline-offset-2 hover:text-text hover:underline disabled:opacity-50"
              >
                {action.label}
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
