"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Fragment, useEffect, useMemo, useState, type ReactNode } from "react";

import { plainAnswer, tokenizeAnswer, type SearchResult, type Token } from "@/lib/search";

export type CiteHandler = (id: number, anchor: HTMLElement) => void;

/** Reveal `count` tokens over time (all at once with reduced motion). */
function useStream(count: number, key: string) {
  const reduce = useReducedMotion();
  const [state, setState] = useState({ key: "", shown: 0 });
  useEffect(() => {
    if (reduce) return;
    // ~28 ms per token (as in the reference), but long answers finish within ~4 s
    const perToken = Math.max(10, Math.min(28, 4000 / Math.max(1, count)));
    const start = performance.now();
    let frame = 0;
    const tick = (now: number) => {
      const n = Math.min(count, Math.floor((now - start) / perToken) + 1);
      setState({ key, shown: n });
      if (n < count) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [count, key, reduce]);
  if (reduce) return count;
  return state.key === key ? state.shown : 0;
}

export function AnswerPanel({
  result,
  activeId,
  onHover,
  onLeave,
  onCite,
}: {
  result: SearchResult;
  activeId: number | null;
  onHover: CiteHandler;
  onLeave: () => void;
  onCite: CiteHandler;
}) {
  const { blocks, count } = useMemo(() => tokenizeAnswer(result.answer), [result.answer]);
  const shown = useStream(count, result.query + result.answer);
  const done = shown >= count;
  const known = useMemo(() => new Set(result.sources.map((s) => s.id)), [result.sources]);

  const renderTokens = (tokens: Token[], last: boolean) => {
    const visible = tokens.filter((t) => t.index < shown);
    return (
      <>
        {visible.map((t) => (
          <Fragment key={t.index}>
            {t.space ? " " : null}
            {t.kind === "word" ? (
              <span className={`pi-word ${t.bold ? "font-semibold" : ""}`}>{t.text}</span>
            ) : known.has(t.id) ? (
              <button
                type="button"
                className={`pi-cite mx-[2px] inline-grid h-[1.5em] min-w-[1.5em] place-items-center rounded-full border-[1.5px] border-clay px-[3px] align-[0.2em] font-sans text-[0.74rem] leading-none font-semibold transition-colors duration-200 ${
                  activeId === t.id ? "bg-clay text-white" : "text-accent hover:bg-clay hover:text-white"
                }`}
                onPointerEnter={(e) => onHover(t.id, e.currentTarget)}
                onPointerLeave={onLeave}
                onFocus={(e) => onHover(t.id, e.currentTarget)}
                onBlur={onLeave}
                onClick={(e) => onCite(t.id, e.currentTarget)}
                aria-label={`Show source ${t.id}`}
                data-cite={t.id}
              >
                {t.id}
              </button>
            ) : null}
          </Fragment>
        ))}
        {last && !done && <span className="pi-caret" aria-hidden />}
      </>
    );
  };

  const lastBlock = blocks.length - 1;
  return (
    <section className="rounded-3xl border border-line bg-surface/90 p-6 shadow-card md:p-8" aria-labelledby="answer-heading">
      <div className="flex items-center justify-between gap-3">
        <h2 id="answer-heading" className="text-[13px] font-semibold tracking-wide text-muted uppercase" style={{ fontFamily: "var(--font-sans)" }}>
          Answer
        </h2>
        {result.status === "answered" && <CopyButton text={plainAnswer(result)} disabled={!done} />}
      </div>

      {result.legal && (
        <p className="mt-4 rounded-xl bg-warn-soft px-3 py-2 text-sm text-warn">
          This asks for a legal opinion, which this tool cannot give. Below is technical information from the sources only.
        </p>
      )}

      {result.status === "insufficient" ? (
        <div className="mt-4">
          <p className="font-serif text-xl leading-relaxed">The sources don&apos;t answer this, so nothing is guessed.</p>
          {result.note && <p className="mt-2 text-sm text-muted">{result.note}</p>}
          <p className="mt-2 text-sm text-muted">Try naming the technology more specifically, or import related patents into the library first.</p>
        </div>
      ) : (
        <div className="mt-4 space-y-4 font-serif text-[1.13rem] leading-[1.72] text-text md:text-[1.2rem]" aria-live="polite" aria-busy={!done}>
          {blocks.map((block, i) =>
            block.kind === "paragraph" ? (
              <p key={i}>{renderTokens(block.tokens, i === lastBlock)}</p>
            ) : (
              <ul key={i} className="list-disc space-y-1.5 pl-6 marker:text-clay">
                {block.items.map((item, j) =>
                  item.some((t) => t.index < shown) ? <li key={j}>{renderTokens(item, i === lastBlock && j === block.items.length - 1)}</li> : null,
                )}
              </ul>
            ),
          )}
        </div>
      )}

      <AnimatePresence>
        {done && result.interpretation && (
          <motion.p
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-5 border-l-2 border-stone pl-3 text-sm text-muted"
          >
            <span className="font-medium text-text">Interpretation, not stated in the sources: </span>
            {result.interpretation}
          </motion.p>
        )}
      </AnimatePresence>

      <p className="mt-6 border-t border-line pt-3 text-xs text-muted">
        Technical information from patent text only. Not legal advice; does not assess validity or infringement.
      </p>
    </section>
  );
}

function CopyButton({ text, disabled }: { text: string; disabled: boolean }) {
  const [copied, setCopied] = useState(false);
  const [failed, setFailed] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      setFailed(true);
      setTimeout(() => setFailed(false), 2200);
    }
  }

  let label: ReactNode = "Copy";
  if (copied) label = "Copied";
  if (failed) label = "Copy blocked";

  return (
    <motion.button
      type="button"
      onClick={copy}
      disabled={disabled}
      whileTap={{ scale: 0.92 }}
      className="relative flex items-center gap-1.5 overflow-hidden rounded-full border border-line-strong bg-surface px-3 py-1 text-xs font-medium text-text transition-colors hover:border-clay/60 disabled:opacity-40"
      aria-live="polite"
    >
      <span className="relative h-3.5 w-3.5">
        <AnimatePresence initial={false} mode="popLayout">
          {copied ? (
            <motion.svg key="check" viewBox="0 0 24 24" className="absolute inset-0 text-ok" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" aria-hidden
              initial={{ scale: 0.4, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.4, opacity: 0 }}
              transition={{ type: "spring", stiffness: 500, damping: 22 }}>
              <motion.path d="M5 12.5l4.5 4.5L19 7.5" initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 0.35, delay: 0.05 }} />
            </motion.svg>
          ) : (
            <motion.svg key="copy" viewBox="0 0 24 24" className="absolute inset-0" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden
              initial={{ scale: 0.4, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.4, opacity: 0 }}>
              <rect x="8" y="8" width="13" height="13" rx="2.5" />
              <path d="M16 8V5.5A2.5 2.5 0 0 0 13.5 3h-8A2.5 2.5 0 0 0 3 5.5v8A2.5 2.5 0 0 0 5.5 16H8" />
            </motion.svg>
          )}
        </AnimatePresence>
      </span>
      {label}
    </motion.button>
  );
}
