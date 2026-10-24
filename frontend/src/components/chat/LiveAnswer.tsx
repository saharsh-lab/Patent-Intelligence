"use client";

import { type RefObject, useEffect, useRef, useState } from "react";
import useSWR from "swr";

import { renderInlines } from "@/components/ask/AnswerView";
import { AgentTrace } from "@/components/chat/AgentTrace";
import { AnswerBlocks } from "@/components/chat/AnswerBlocks";
import { type XRaySelection, XRayText } from "@/components/chat/XRay";
import { icons } from "@/components/icons";
import { fetcher } from "@/lib/api";
import { parseAnswer, parseInline, stripInterpretation } from "@/lib/citations";
import { continues, headline, type Live, type LiveSource, nextCount, plainSentence, STAGES, stageOf, visibleDraft } from "@/lib/live";
import type { ProgressOut } from "@/lib/types";
import type { ClaimResult } from "@/lib/verification";
import { TONE_LABEL, toneOf } from "@/lib/xray";

const KIND_ICON = { library: icons.file, web: icons.globe, patent: icons.search } as const;
const KIND_LABEL: Record<string, string> = { library: "Your library", web: "Web page", patent: "Patent filing" };

function useElapsed(since: number) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);
  return Math.max(0, Math.floor((now - since) / 1000));
}

/** Keep the end of a growing answer in view, unless the reader has scrolled up to read. */
export function useFollow(end: RefObject<HTMLElement | null>, growth: unknown) {
  useEffect(() => {
    const el = end.current;
    if (!el) return;
    // How far it is below the question box docked at the bottom (about 120 px tall)
    const below = el.getBoundingClientRect().bottom - (window.innerHeight - 120);
    if (below > 0 && below < 360) el.scrollIntoView({ block: "end", behavior: "smooth" });
  }, [end, growth]);
}

/** Types out text received in bursts (each poll) smoothly; a new draft starts over. */
function useTypewriter(target: string, animate: boolean): string {
  const [count, setCount] = useState(0);
  const [previous, setPrevious] = useState(target);
  if (previous !== target) {
    setPrevious(target);
    if (!continues(previous, target)) setCount(0);
  }
  useEffect(() => {
    if (!animate) return;
    let frame = requestAnimationFrame(function tick() {
      setCount((c) => nextCount(c, target.length));
      frame = requestAnimationFrame(tick);
    });
    return () => cancelAnimationFrame(frame);
  }, [target, animate]);
  return animate ? visibleDraft(target, count) : target;
}

/**
 * The answer as it happens: the agent's stage, the sources as they are found, the draft as
 * the model writes it, then each sentence taking its verdict colour as the checker gives it
 * (and, if some fail, the rewrite). Polls twice a second while the answer is written.
 */
export function LiveAnswer({ conversationId, since, testing = false }: { conversationId: string | null; since?: number; testing?: boolean }) {
  const [mountedAt] = useState(() => Date.now());
  const [showSteps, setShowSteps] = useState(false);
  // Keyed by when this view appeared: a cached poll from the previous answer (its last
  // state, still "running") must not flash up before the first fresh one
  const { data } = useSWR<ProgressOut>(
    conversationId ? [`/conversations/${conversationId}/progress`, mountedAt] : null,
    ([url]: [string, number]) => fetcher(url),
    { refreshInterval: 500, dedupingInterval: 250 },
  );
  const elapsed = useElapsed(since ?? mountedAt);
  // A finished entry belongs to the previous answer: wait for this one to start
  const progress = data?.running ? data : undefined;
  const live = progress?.live ?? null;
  const stage = stageOf(progress);
  const steps = progress?.steps ?? [];
  const end = useRef<HTMLDivElement>(null);
  useFollow(end, `${live?.phase}:${live?.sources.length}:${live?.claims.length}:${live?.flagged.length}`);

  return (
    // Screen readers hear the one-line status, not every word of the draft as it streams
    <div className="min-w-0 flex-1 space-y-3" aria-busy="true">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 text-xs">
        <ol className="flex items-center gap-1.5" aria-label="Progress">
          {STAGES.map((name, i) => (
            <li key={name} className="flex items-center gap-1.5">
              {i > 0 && <span aria-hidden className={`h-px w-3 transition-colors duration-500 sm:w-5 ${i <= stage ? "bg-cite" : "bg-line"}`} />}
              <span aria-current={i === stage ? "step" : undefined} className={`flex items-center gap-1.5 ${i === stage ? "font-semibold text-text" : i < stage ? "text-text" : "text-muted"}`}>
                <span aria-hidden className={`lv-dot ${i < stage ? "lv-done" : i === stage ? "lv-now" : ""}`} />
                {name}
                {i === 2 && (live?.attempt ?? 0) > 1 ? " ×2" : ""}
              </span>
            </li>
          ))}
        </ol>
        <span className="text-muted" role="status" aria-live="polite">
          <span key={headline(progress)} className="pi-fade inline-block">
            {headline(progress)}
          </span>
        </span>
        <span className="ml-auto font-mono text-muted tabular-nums">{elapsed}s</span>
        {steps.length > 0 && (
          <button type="button" onClick={() => setShowSteps((v) => !v)} aria-expanded={showSteps} className="text-muted underline-offset-2 hover:text-text hover:underline">
            {showSteps ? "Hide steps" : "Steps"}
          </button>
        )}
      </div>

      {testing && (
        <p className="border-l-4 border-stamp pl-3 text-xs text-muted">
          <span className="font-semibold text-stamp">Checker test:</span> one false sentence will be planted in the first draft. The checker is not told which.
        </p>
      )}
      {showSteps && (
        <div className="pi-in rounded-2xl border border-line bg-surface px-4 py-3">
          <AgentTrace steps={steps} live />
        </div>
      )}
      {live && live.sources.length > 0 && <Sources sources={live.sources} />}
      {live && live.phase !== "searching" ? (
        <Draft live={live} />
      ) : (
        <div className="space-y-2.5 pt-1" aria-hidden>
          <div className="skeleton h-3.5 w-[92%]" />
          <div className="skeleton h-3.5 w-[78%]" />
          <div className="skeleton h-3.5 w-[85%]" />
        </div>
      )}
      {elapsed >= 40 && (
        <p className="text-[11px] text-muted">The local model writes the answer and then checks every sentence; this can take a minute.</p>
      )}
      <div ref={end} className="scroll-mb-28" aria-hidden />
    </div>
  );
}

/** Sources pop in as the tools find them. */
function Sources({ sources }: { sources: LiveSource[] }) {
  const shown = sources.slice(0, 8);
  return (
    <ul className="flex flex-wrap gap-1.5" aria-label="Sources found">
      {shown.map((source) => {
        const Icon = KIND_ICON[source.kind as keyof typeof KIND_ICON] ?? icons.file;
        return (
          <li
            key={`${source.kind}:${source.label}`}
            title={`${KIND_LABEL[source.kind] ?? "Source"}: ${source.title}`}
            className="lv-chip inline-flex max-w-[15rem] items-center gap-1.5 rounded-full border border-line bg-surface px-2.5 py-1 text-xs"
          >
            <Icon width={12} height={12} className="shrink-0 text-muted" />
            <span className="truncate">{source.kind === "patent" ? source.label : source.title}</span>
          </li>
        );
      })}
      {sources.length > shown.length && <li className="self-center px-1 text-xs text-muted">+{sources.length - shown.length} more</li>}
    </ul>
  );
}

function Draft({ live }: { live: Live }) {
  const writing = live.phase === "writing";
  const text = useTypewriter(live.draft, writing);
  const claims = (live.claims as unknown as ClaimResult[]).filter((c) => c.location === "answer");
  const judged = claims.length > 0 && (live.phase === "checked" || live.phase === "rewriting");
  const [selected, setSelected] = useState<XRaySelection>(null);
  const [cited, setCited] = useState<string | null>(null);
  const blocks = parseAnswer(stripInterpretation(text));
  const source = live.evidence.find((e) => e.label === cited);
  const end = useRef<HTMLSpanElement>(null);
  useFollow(end, text.length);
  const caret = writing ? <span ref={end} className="pi-caret scroll-mb-28" aria-hidden /> : null;

  const line = (raw: string) =>
    judged ? (
      <XRayText raw={raw} claims={claims} selected={selected} onSelect={setSelected} />
    ) : (
      <>{renderInlines(parseInline(raw), (label) => setCited((c) => (c === label ? null : label)))}</>
    );

  return (
    <div className="space-y-3">
      {live.flagged.length > 0 && (live.phase === "rewriting" || live.attempt > 1) && (
        <div className="pi-in border-l-4 border-bad bg-surface px-3 py-2 text-sm">
          <p className="font-medium text-bad">
            {live.flagged.length} sentence{live.flagged.length === 1 ? " was" : "s were"} not supported by the sources.{" "}
            {live.phase === "rewriting"
              ? "Rewriting with more evidence…"
              : live.phase === "writing"
                ? "Writing a new answer without:"
                : "Rewritten without:"}
          </p>
          <ul className="mt-1 space-y-0.5 text-xs text-muted line-through decoration-bad">
            {live.flagged.map((sentence) => (
              <li key={sentence}>{plainSentence(sentence)}</li>
            ))}
          </ul>
        </div>
      )}
      <div className={`relative space-y-3 text-[0.98rem] leading-7 ${live.phase === "checking" ? "lv-checking" : ""} ${judged ? "lv-judged" : ""}`}>
        {blocks.length === 0 && caret}
        <AnswerBlocks blocks={blocks} line={line} tail={caret} />
      </div>
      {source && !judged && (
        <p className="pi-in text-xs text-muted">
          <span className="font-semibold text-cite">{source.label.replace(/^E/, "")}</span> → {KIND_LABEL[source.kind] ?? "Source"}: {source.title}
        </p>
      )}
      {selected && judged && (
        <p className="pi-in text-xs text-muted">
          <span className="font-medium text-text">{TONE_LABEL[toneOf(selected.claim)]}.</span> {selected.claim.reason}
        </p>
      )}
    </div>
  );
}
