"use client";

import { AnimatePresence, LayoutGroup, MotionConfig, motion, useReducedMotion, type Transition } from "framer-motion";
import Link from "next/link";
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";

import { AnswerPanel } from "@/components/search/AnswerPanel";
import { Background } from "@/components/search/Background";
import { LoadingState } from "@/components/search/LoadingState";
import { LogoMark } from "@/components/search/Logo";
import { SearchBar } from "@/components/search/SearchBar";
import { SourceCard } from "@/components/search/SourceCard";
import { SUGGESTIONS, SearchError, demoResult, describeError, runSearch, type SearchResult } from "@/lib/search";

type Phase = "idle" | "loading" | "done" | "error";
type Active = { id: number; anchor: HTMLElement | null; pinned: boolean } | null;

const EASE = [0.22, 1, 0.36, 1] as const;

export function SearchExperience() {
  const [query, setQuery] = useState("");
  const [submitted, setSubmitted] = useState("");
  const [phase, setPhase] = useState<Phase>("idle");
  const [result, setResult] = useState<SearchResult | null>(null);
  const [error, setError] = useState<SearchError | null>(null);
  const [demoReason, setDemoReason] = useState<string | null>(null);
  const [active, setActive] = useState<Active>(null);
  const controller = useRef<AbortController | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const search = useCallback(async (text: string) => {
    const q = text.trim();
    if (!q) return;
    controller.current?.abort();
    const abort = new AbortController();
    controller.current = abort;
    setQuery(q);
    setSubmitted(q);
    setPhase("loading");
    setResult(null);
    setError(null);
    setDemoReason(null);
    setActive(null);
    try {
      const r = await runSearch(q, abort.signal);
      if (abort.signal.aborted) return;
      setResult(r);
      setPhase("done");
    } catch (e) {
      if (abort.signal.aborted) return;
      const err = e instanceof SearchError ? e : new SearchError("server", String((e as Error)?.message ?? e));
      if (err.kind === "unreachable") {
        // Keep the demo alive: answer from the synthetic demo patents instead
        setDemoReason(describeError(err).title);
        setResult(demoResult(q));
        setPhase("done");
      } else {
        setError(err);
        setPhase("error");
      }
    }
  }, []);

  function cancel() {
    controller.current?.abort();
    setPhase(result ? "done" : "idle");
  }

  function reset() {
    controller.current?.abort();
    setPhase("idle");
    setResult(null);
    setError(null);
    setQuery("");
    setActive(null);
  }

  function showDemo() {
    setDemoReason("Showing a sample answer instead.");
    setResult(demoResult(submitted));
    setError(null);
    setPhase("done");
  }

  useEffect(() => () => controller.current?.abort(), []);

  // Escape clears a pinned citation
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setActive(null);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const started = phase !== "idle";
  return (
    <MotionConfig reducedMotion="user">
      <LayoutGroup>
        <div className="relative isolate min-h-full">
          <Background calm={started} />
          {!started ? (
            <Hero query={query} setQuery={setQuery} onSearch={search} inputRef={inputRef} />
          ) : (
            <>
              <header className="sticky top-0 z-30 border-b border-line/70 bg-bg/80 backdrop-blur-md">
                <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-3 md:px-8">
                  <motion.button
                    type="button"
                    onClick={reset}
                    whileTap={{ scale: 0.92 }}
                    aria-label="New search"
                    title="New search"
                    className="shrink-0 rounded-xl p-1 text-text hover:bg-surface-2"
                  >
                    <LogoMark size={30} />
                  </motion.button>
                  <SearchBar size="compact" value={query} onChange={setQuery} onSubmit={() => search(query)} busy={phase === "loading"} inputRef={inputRef} />
                </div>
              </header>

              <main className="mx-auto max-w-6xl px-4 pt-6 pb-16 md:px-8 md:pt-8">
                <motion.h1
                  key={submitted}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, ease: EASE }}
                  className="mb-5 max-w-4xl text-2xl leading-tight font-medium text-text md:text-[2rem]"
                >
                  {submitted}
                </motion.h1>

                <AnimatePresence>
                  {demoReason && phase === "done" && (
                    <motion.div
                      initial={{ opacity: 0, y: -6 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0 }}
                      role="status"
                      className="mb-5 flex flex-wrap items-center gap-x-3 gap-y-2 rounded-2xl border border-dusty/40 bg-dusty/10 px-4 py-3 text-sm"
                    >
                      <span className="rounded-full bg-dusty/20 px-2 py-0.5 text-xs font-semibold text-text">Demo data</span>
                      <span className="flex-1 text-text/85">
                        {demoReason} This answer comes from the built-in synthetic demo patents, not a live search.
                      </span>
                      <motion.button
                        type="button"
                        whileTap={{ scale: 0.95 }}
                        onClick={() => search(submitted)}
                        className="rounded-full border border-line-strong bg-surface px-3 py-1 text-xs font-medium hover:border-clay/60"
                      >
                        Retry live search
                      </motion.button>
                    </motion.div>
                  )}
                </AnimatePresence>

                <AnimatePresence mode="wait">
                  {phase === "loading" && (
                    <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0, transition: { duration: 0.15 } }}>
                      <LoadingState onCancel={cancel} />
                    </motion.div>
                  )}
                  {phase === "error" && error && (
                    <motion.div key="error" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                      <ErrorPanel error={error} onRetry={() => search(submitted)} onDemo={showDemo} />
                    </motion.div>
                  )}
                  {phase === "done" && result && (
                    <motion.div key={`done-${submitted}`} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                      <Results result={result} active={active} setActive={setActive} />
                    </motion.div>
                  )}
                </AnimatePresence>
              </main>
            </>
          )}
        </div>
      </LayoutGroup>
    </MotionConfig>
  );
}

// ---------------------------------------------------------------------------

function Hero({
  query,
  setQuery,
  onSearch,
  inputRef,
}: {
  query: string;
  setQuery: (q: string) => void;
  onSearch: (q: string) => void;
  inputRef: React.RefObject<HTMLInputElement | null>;
}) {
  const lines = ["Patent research,", "grounded in evidence."];
  // With reduced motion, show everything at once (no staggered delays)
  const reduce = useReducedMotion();
  const t = (transition: Transition): Transition => (reduce ? { duration: 0 } : transition);
  return (
    <div className="flex min-h-[calc(100vh-3rem)] flex-col items-center justify-center px-4 py-12 text-center md:min-h-screen">
      <div className="text-text">
        <LogoMark size={56} draw />
      </div>
      <h1 className="mt-6 text-[2.4rem] leading-[1.08] font-medium tracking-tight text-text sm:text-5xl md:text-6xl">
        {lines.map((line, i) => (
          <span key={line} className="block overflow-hidden pb-[0.08em]">
            <motion.span
              className={`block ${i === 1 ? "text-accent italic" : ""}`}
              initial={{ y: "105%", opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={t({ duration: 0.9, delay: 0.35 + i * 0.16, ease: EASE })}
            >
              {line}
            </motion.span>
          </span>
        ))}
      </h1>
      <motion.p
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={t({ duration: 0.7, delay: 0.75, ease: EASE })}
        className="mt-5 max-w-[46ch] text-[15px] leading-relaxed text-muted md:text-base"
      >
        Ask about any technology. Answers are drawn from patent filings, with every claim linked to its source.
      </motion.p>

      <motion.div
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={t({ duration: 0.7, delay: 0.9, ease: EASE })}
        className="mt-8 w-full max-w-2xl"
      >
        <SearchBar size="hero" value={query} onChange={setQuery} onSubmit={() => onSearch(query)} busy={false} inputRef={inputRef} autoFocus />
      </motion.div>

      <div className="mt-6 flex max-w-2xl flex-wrap justify-center gap-2" aria-label="Suggested questions">
        {SUGGESTIONS.map((s, i) => (
          <motion.button
            key={s}
            type="button"
            onClick={() => onSearch(s)}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={t({ delay: 1.05 + i * 0.07, type: "spring", stiffness: 260, damping: 24 })}
            whileHover={{ y: -2 }}
            whileTap={{ scale: 0.96 }}
            className="rounded-full border border-line-strong bg-surface/80 px-3.5 py-2 text-[13.5px] text-text/90 shadow-card transition-colors hover:border-clay/60 hover:text-accent"
          >
            {s}
          </motion.button>
        ))}
      </div>

      <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t({ delay: 1.5 })} className="mt-10 text-xs text-muted">
        Prefer a conversation?{" "}
        <Link href="/chat" className="text-accent underline-offset-4 hover:underline">
          Open chat
        </Link>{" "}
        to attach documents and ask follow-ups.
      </motion.p>
    </div>
  );
}

// ---------------------------------------------------------------------------

function ErrorPanel({ error, onRetry, onDemo }: { error: SearchError; onRetry: () => void; onDemo: () => void }) {
  const { title, fix } = describeError(error);
  return (
    <div role="alert" className="max-w-2xl rounded-3xl border border-bad/30 bg-surface/90 p-6 shadow-card">
      <div className="flex items-start gap-3">
        <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-bad-soft text-bad" aria-hidden>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round">
            <path d="M12 8v5M12 16.5v.5" />
          </svg>
        </span>
        <div>
          <p className="font-serif text-lg text-text">{title}</p>
          <p className="mt-1 text-sm text-muted">
            <span className="font-medium text-text">How to fix: </span>
            {fix}
          </p>
          {error.status ? <p className="mt-1 font-mono text-[11px] text-muted">HTTP {error.status}</p> : null}
        </div>
      </div>
      <div className="mt-5 flex flex-wrap gap-2 pl-11">
        {error.kind === "auth" ? (
          <Link href="/login?next=/search" className="rounded-xl bg-brand px-4 py-2 text-sm font-medium text-white">
            Sign in
          </Link>
        ) : (
          <motion.button type="button" whileTap={{ scale: 0.95 }} onClick={onRetry} className="rounded-xl bg-brand px-4 py-2 text-sm font-medium text-white">
            Try again
          </motion.button>
        )}
        <motion.button type="button" whileTap={{ scale: 0.95 }} onClick={onDemo} className="rounded-xl border border-line-strong bg-surface px-4 py-2 text-sm font-medium hover:border-clay/60">
          Show a demo answer
        </motion.button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------

function Results({ result, active, setActive }: { result: SearchResult; active: Active; setActive: (a: Active) => void }) {
  const reduce = useReducedMotion();
  const wrapper = useRef<HTMLDivElement>(null);
  const cards = useRef(new Map<number, HTMLElement>());

  const hover = (id: number, anchor: HTMLElement | null) => {
    if (active?.pinned && active.id !== id) return;
    setActive({ id, anchor, pinned: active?.pinned ?? false });
  };
  const leave = () => {
    if (!active?.pinned) setActive(null);
  };
  const cite = (id: number, anchor: HTMLElement) => {
    if (active?.pinned && active.id === id) {
      setActive(null);
      return;
    }
    setActive({ id, anchor, pinned: true });
    const card = cards.current.get(id);
    const stacked = window.matchMedia("(max-width: 1023px)").matches;
    card?.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: stacked ? "center" : "nearest" });
  };

  return (
    <div ref={wrapper} className="relative">
      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)] lg:gap-10">
        <AnswerPanel result={result} activeId={active?.id ?? null} onHover={hover} onLeave={leave} onCite={cite} />

        <aside aria-label="Sources" className="lg:sticky lg:top-24">
          <h2 className="mb-3 flex items-baseline gap-2 text-[13px] font-semibold tracking-wide text-muted uppercase" style={{ fontFamily: "var(--font-sans)" }}>
            Sources <span className="font-normal normal-case">{result.sources.length}</span>
          </h2>
          {result.sources.length === 0 ? (
            <p className="text-sm text-muted">No passages were retrieved.</p>
          ) : (
            <div className="space-y-3 lg:max-h-[calc(100vh-9rem)] lg:overflow-y-auto lg:p-1.5 lg:pr-2" data-sources-scroll>
              {result.sources.map((s, i) => (
                <SourceCard
                  key={s.id}
                  source={s}
                  index={i}
                  active={active?.id === s.id}
                  onActivate={() => hover(s.id, wrapper.current?.querySelector<HTMLElement>(`[data-cite="${s.id}"]`) ?? null)}
                  onDeactivate={leave}
                  registerRef={(el) => {
                    if (el) cards.current.set(s.id, el);
                    else cards.current.delete(s.id);
                  }}
                />
              ))}
            </div>
          )}
        </aside>
      </div>
      <Connector wrapper={wrapper} active={active} cards={cards} />
    </div>
  );
}

/**
 * An animated curve from the citation marker to its source card (wide screens).
 * Positions are re-measured on scroll and resize while a citation is active.
 */
function Connector({
  wrapper,
  active,
  cards,
}: {
  wrapper: React.RefObject<HTMLDivElement | null>;
  active: Active;
  cards: React.RefObject<Map<number, HTMLElement>>;
}) {
  const [measured, setPath] = useState<{ id: number; d: string; x1: number; y1: number; x2: number; y2: number } | null>(null);
  // Only draw the curve measured for the citation that is active right now
  const path = active?.anchor && measured?.id === active.id ? measured : null;

  useLayoutEffect(() => {
    const anchor = active?.anchor;
    const card = active ? cards.current.get(active.id) : undefined;
    if (!active || !anchor || !card || !wrapper.current) return;
    const id = active.id;
    let frame = 0;
    const measure = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        const box = wrapper.current?.getBoundingClientRect();
        if (!box || window.innerWidth < 1024 || !anchor.isConnected) {
          setPath(null);
          return;
        }
        const a = anchor.getBoundingClientRect();
        const c = card.getBoundingClientRect();
        const x1 = a.right - box.left + 3;
        const y1 = a.top + a.height / 2 - box.top;
        const x2 = c.left - box.left - 4;
        // Aim at the card's middle, kept inside the visible part of the card
        const top = Math.max(c.top, 0) - box.top + 24;
        const bottom = Math.min(c.bottom, window.innerHeight) - box.top - 24;
        const y2 = Math.max(top, Math.min(bottom, c.top + c.height / 2 - box.top));
        const dx = Math.max(40, (x2 - x1) * 0.5);
        setPath({ id, d: `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`, x1, y1, x2, y2 });
      });
    };
    measure();
    window.addEventListener("scroll", measure, true);
    window.addEventListener("resize", measure);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("scroll", measure, true);
      window.removeEventListener("resize", measure);
    };
  }, [active, cards, wrapper]);

  return (
    <svg aria-hidden className="pointer-events-none absolute inset-0 z-20 hidden h-full w-full overflow-visible lg:block">
      <AnimatePresence>
        {path && (
          <motion.g key={active?.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0, transition: { duration: 0.2 } }}>
            <motion.path
              d={path.d}
              fill="none"
              stroke="var(--clay)"
              strokeWidth={1.6}
              strokeLinecap="round"
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ duration: 0.55, ease: EASE }}
            />
            <circle cx={path.x1} cy={path.y1} r={3} fill="var(--clay)" />
            <motion.circle cx={path.x2} cy={path.y2} r={3.5} fill="var(--clay)" initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ delay: 0.45, type: "spring", stiffness: 500, damping: 20 }} />
          </motion.g>
        )}
      </AnimatePresence>
    </svg>
  );
}
