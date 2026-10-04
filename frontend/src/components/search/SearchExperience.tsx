"use client";

import { AnimatePresence, LayoutGroup, MotionConfig, motion, useReducedMotion, type Transition } from "framer-motion";
import Link from "next/link";
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { useSWRConfig } from "swr";

import { AnswerPanel } from "@/components/search/AnswerPanel";
import { Background } from "@/components/search/Background";
import { LoadingState } from "@/components/search/LoadingState";
import { LogoMark } from "@/components/search/Logo";
import { SearchBar } from "@/components/search/SearchBar";
import { SourceCard } from "@/components/search/SourceCard";
import { SUGGESTIONS, SearchError, demoResult, describeError, followUpSuggestions, runTurn, type SearchResult } from "@/lib/search";

type Active = { id: number; anchor: HTMLElement | null; pinned: boolean } | null;

/** One question in the thread and what happened to it. */
interface Turn {
  key: number;
  question: string;
  phase: "loading" | "done" | "error";
  result?: SearchResult;
  error?: SearchError;
  /** How the backend read a follow-up ("which is newest?" → full question) */
  interpretedAs?: string | null;
  /** Set when this answer comes from the synthetic demo data */
  demoReason?: string | null;
}

const EASE = [0.22, 1, 0.36, 1] as const;
let turnKey = 0;

export function SearchExperience() {
  const { mutate } = useSWRConfig();
  const reduce = useReducedMotion();
  const [query, setQuery] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const controller = useRef<AbortController | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const followRef = useRef<HTMLInputElement>(null);

  const update = (key: number, patch: Partial<Turn>) =>
    setTurns((all) => all.map((t) => (t.key === key ? { ...t, ...patch } : t)));

  /** Answer `q` as the turn `key`, inside `thread` (null = start a new conversation). */
  const answer = useCallback(
    async (key: number, q: string, thread: string | null, previous: string[]) => {
      controller.current?.abort();
      const abort = new AbortController();
      controller.current = abort;
      try {
        const turn = await runTurn(q, thread, previous, abort.signal);
        if (abort.signal.aborted) return;
        if (turn.conversationId) {
          setConversationId(turn.conversationId);
          mutate("/conversations"); // the thread shows up in the sidebar
        }
        update(key, { phase: "done", result: turn.result, interpretedAs: turn.interpretedAs, error: undefined, demoReason: null });
      } catch (e) {
        if (abort.signal.aborted) return;
        const err = e instanceof SearchError ? e : new SearchError("server", String((e as Error)?.message ?? e));
        if (err.kind === "unreachable") {
          // Keep the demo alive: answer from the synthetic demo patents instead
          update(key, { phase: "done", result: demoResult(q), demoReason: describeError(err).title });
        } else {
          update(key, { phase: "error", error: err });
        }
      }
    },
    [mutate],
  );

  /** A new search from the hero or the top bar: starts a fresh thread. */
  function search(text: string) {
    const q = text.trim();
    if (!q) return;
    const key = ++turnKey;
    setQuery(q);
    setConversationId(null);
    setTurns([{ key, question: q, phase: "loading" }]);
    answer(key, q, null, []);
  }

  /** A follow-up: same thread, so the backend remembers the earlier questions. */
  function followUp(text: string) {
    const q = text.trim();
    if (!q || busy) return;
    const key = ++turnKey;
    const previous = turns.map((t) => t.question);
    setTurns((all) => [...all, { key, question: q, phase: "loading" }]);
    answer(key, q, conversationId, previous);
    // Bring the new question into view once it has rendered
    requestAnimationFrame(() =>
      document.getElementById(`turn-${key}`)?.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" }),
    );
  }

  function retry(turn: Turn) {
    update(turn.key, { phase: "loading", error: undefined });
    const previous = turns.filter((t) => t.key < turn.key).map((t) => t.question);
    answer(turn.key, turn.question, conversationId, previous);
  }

  function cancel(turn: Turn) {
    controller.current?.abort();
    setTurns((all) => all.filter((t) => t.key !== turn.key));
  }

  function reset() {
    controller.current?.abort();
    setTurns([]);
    setQuery("");
    setConversationId(null);
  }

  useEffect(() => () => controller.current?.abort(), []);

  const busy = turns.some((t) => t.phase === "loading");
  const started = turns.length > 0;
  const last = turns.at(-1);
  return (
    <MotionConfig reducedMotion="user">
      <LayoutGroup>
        <div className="relative isolate min-h-full">
          <Background calm={started} />
          {!started ? (
            <Hero query={query} setQuery={setQuery} onSearch={search} inputRef={inputRef} />
          ) : (
            <>
              <header className="sticky top-0 z-30 border-b border-line bg-bg/90 backdrop-blur-md">
                <div className="mx-auto flex max-w-[1080px] items-center gap-3 px-4 py-3.5 md:px-6">
                  <motion.button
                    type="button"
                    onClick={reset}
                    whileTap={{ scale: 0.92 }}
                    aria-label="New search"
                    title="New search"
                    className="hidden shrink-0 items-center gap-2.5 p-1 text-text hover:bg-surface-2 sm:flex"
                  >
                    <LogoMark size={30} />
                    <span className="hidden font-serif text-[1.4rem] leading-none font-medium tracking-tight lg:inline">Patent Intelligence</span>
                  </motion.button>
                  <SearchBar size="compact" value={query} onChange={setQuery} onSubmit={() => search(query)} busy={busy} inputRef={inputRef} />
                </div>
              </header>

              <main className="mx-auto max-w-[1080px] px-4 pt-6 pb-10 md:px-6 md:pt-7">
                {turns.map((turn, i) => (
                  <TurnView
                    key={turn.key}
                    turn={turn}
                    followUp={i > 0}
                    onRetry={() => retry(turn)}
                    onCancel={() => cancel(turn)}
                    onDemo={() => update(turn.key, { phase: "done", result: demoResult(turn.question), demoReason: "Showing a sample answer instead.", error: undefined })}
                  />
                ))}
              </main>

              {last && last.phase !== "loading" && (
                <FollowUpBar
                  inputRef={followRef}
                  onSubmit={followUp}
                  suggestions={last.result && last.result.status === "answered" ? followUpSuggestions(last.result) : []}
                  conversationId={conversationId}
                />
              )}
            </>
          )}
        </div>
      </LayoutGroup>
    </MotionConfig>
  );
}

/** One question with its answer, sources, or loading/error state. */
function TurnView({
  turn,
  followUp,
  onRetry,
  onCancel,
  onDemo,
}: {
  turn: Turn;
  followUp: boolean;
  onRetry: () => void;
  onCancel: () => void;
  onDemo: () => void;
}) {
  const Heading = followUp ? motion.h2 : motion.h1;
  return (
    <section id={`turn-${turn.key}`} className={`scroll-mt-36 md:scroll-mt-24 ${followUp ? "mt-12 border-t border-line pt-10" : ""}`} aria-label={turn.question}>
      {followUp && <p className="pi-in mb-1 text-xs font-bold tracking-wide text-muted uppercase">Follow-up</p>}
      <Heading
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: EASE }}
        className={`mb-2 max-w-4xl leading-tight text-text ${followUp ? "text-xl md:text-[1.6rem]" : "text-2xl md:text-[1.9rem]"}`}
      >
        {turn.question}
      </Heading>
      {turn.interpretedAs && (
        <p className="pi-in mb-4 text-sm text-muted" title="The follow-up was completed using the earlier questions in this thread">
          Understood as: <span className="font-serif text-text italic">{turn.interpretedAs}</span>
        </p>
      )}
      <div className="mt-4">
        <AnimatePresence>
          {turn.demoReason && turn.phase === "done" && (
            <motion.div
              initial={{ opacity: 0, y: -6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              role="status"
              className="mb-5 flex flex-wrap items-center gap-x-3 gap-y-2 border border-line border-l-[3px] border-l-cite bg-surface px-4 py-3 text-sm"
            >
              <span className="font-serif text-[0.95rem] text-stamp italic">Demo data</span>
              <span className="flex-1 text-text/85">
                {turn.demoReason} This answer comes from the built-in synthetic demo patents, not a live search.
              </span>
              <button type="button" onClick={onRetry} className="border border-line bg-surface px-3 py-1 text-xs font-medium hover:border-text">
                Retry live search
              </button>
            </motion.div>
          )}
        </AnimatePresence>

        <AnimatePresence mode="wait">
          {turn.phase === "loading" && (
            <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0, transition: { duration: 0.15 } }}>
              <LoadingState onCancel={onCancel} />
            </motion.div>
          )}
          {turn.phase === "error" && turn.error && (
            <motion.div key="error" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
              <ErrorPanel error={turn.error} onRetry={onRetry} onDemo={onDemo} />
            </motion.div>
          )}
          {turn.phase === "done" && turn.result && (
            <motion.div key="done" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <Results result={turn.result} prefix={`t${turn.key}-`} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </section>
  );
}

/** The follow-up composer pinned to the bottom of the thread. */
function FollowUpBar({
  onSubmit,
  suggestions,
  inputRef,
  conversationId,
}: {
  onSubmit: (q: string) => void;
  suggestions: string[];
  inputRef: React.RefObject<HTMLInputElement | null>;
  conversationId: string | null;
}) {
  const [text, setText] = useState("");
  const send = (q: string) => {
    if (!q.trim()) {
      inputRef.current?.focus();
      return;
    }
    onSubmit(q);
    setText("");
  };
  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 260, damping: 30 }}
      className="sticky bottom-0 z-30 border-t border-line bg-bg/90 backdrop-blur-md"
    >
      <div className="mx-auto max-w-[1080px] px-4 pt-3 pb-4 md:px-6">
        {suggestions.length > 0 && (
          <div className="stagger -mx-4 mb-3 flex gap-2 overflow-x-auto px-4 pb-1 md:mx-0 md:flex-wrap md:overflow-visible md:px-0 md:pb-0" aria-label="Suggested follow-ups">
            {suggestions.map((s) => (
              <button key={s} type="button" onClick={() => send(s)} className="shrink-0 border border-line bg-surface px-3 py-1.5 text-[13px] whitespace-nowrap hover:border-text">
                {s}
              </button>
            ))}
          </div>
        )}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            send(text);
          }}
          className="flex gap-2 border-[1.5px] border-text bg-surface p-1.5 shadow-hard transition-[border-color,box-shadow] duration-200 focus-within:border-cite focus-within:[box-shadow:var(--shadow-hard-focus)]"
        >
          <input
            ref={inputRef}
            value={text}
            onChange={(e) => setText(e.target.value)}
            maxLength={2000}
            placeholder="Ask a follow-up question…"
            aria-label="Ask a follow-up question"
            className="min-w-0 flex-1 bg-transparent px-3 py-2 text-[15px] outline-none placeholder:text-muted focus-visible:outline-none"
          />
          <button type="submit" className="shrink-0 bg-brand px-4 text-sm font-medium">
            Ask
          </button>
        </form>
        <p className="mt-2 flex flex-wrap justify-between gap-2 text-[11px] text-muted">
          <span>Follow-ups remember this thread. The top bar starts a new search.</span>
          {conversationId && (
            <Link href={`/chat/${conversationId}`} className="text-accent hover:underline">
              Continue in chat, with attachments →
            </Link>
          )}
        </p>
      </div>
    </motion.div>
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
  // With reduced motion, show everything at once (no staggered delays)
  const reduce = useReducedMotion();
  const t = (transition: Transition): Transition => (reduce ? { duration: 0 } : transition);
  return (
    // Layout from the reference: content starts ~18% down the page, centred
    <div className="mx-auto flex min-h-[calc(100vh-3rem)] max-w-[1080px] flex-col items-center px-4 pt-[12vh] pb-16 text-center md:min-h-screen md:px-6 md:pt-[18vh]">
      <LogoMark size={44} draw className="text-text" />
      {/* Headline and lede reveal line by line from behind a mask */}
      <h1 className="mt-[0.3em] mb-[0.2em] text-[clamp(2rem,5vw,3.2rem)] leading-[1.1] text-text">
        <span className="block overflow-hidden pb-[0.08em]">
          <motion.span className="block" initial={{ y: "105%", opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={t({ duration: 0.85, delay: 0.3, ease: EASE })}>
            Patent Intelligence
          </motion.span>
        </span>
      </h1>
      <p className="mx-auto mb-7 max-w-[62ch] leading-[1.55] text-muted">
        {["Ask about any technology. Answers are drawn from patent filings,", "with every claim linked to its source."].map((line, i) => (
          <span key={line} className="block overflow-hidden">
            <motion.span className="block" initial={{ y: "105%", opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={t({ duration: 0.7, delay: 0.55 + i * 0.12, ease: EASE })}>
              {line}
            </motion.span>
          </span>
        ))}
      </p>

      <motion.div
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={t({ duration: 0.7, delay: 0.85, ease: EASE })}
        className="w-full max-w-[720px]"
      >
        <SearchBar size="hero" value={query} onChange={setQuery} onSubmit={() => onSearch(query)} busy={false} inputRef={inputRef} autoFocus />
      </motion.div>

      <div className="mt-[22px] flex max-w-[720px] flex-wrap justify-center gap-2" aria-label="Suggested questions">
        {SUGGESTIONS.map((s, i) => (
          <motion.button
            key={s}
            type="button"
            onClick={() => onSearch(s)}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={t({ delay: 1.0 + i * 0.07, type: "spring", stiffness: 260, damping: 24 })}
            whileHover={{ y: -2 }}
            whileTap={{ scale: 0.96 }}
            className="border border-line bg-surface px-3.5 py-2 text-[0.9rem] text-text transition-colors hover:border-text"
          >
            {s}
          </motion.button>
        ))}
      </div>

      <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t({ delay: 1.4 })} className="mt-10 text-xs text-muted">
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
    <div role="alert" className="max-w-2xl border-l-[3px] border-stamp bg-surface p-5 leading-normal md:p-6">
      <div className="flex items-start gap-3">
        <span className="pi-cite mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-bad-soft text-bad" aria-hidden>
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
          <Link href="/login?next=/search" className="press bg-brand px-4 py-2 text-sm font-medium">
            Sign in
          </Link>
        ) : (
          <motion.button type="button" whileTap={{ scale: 0.95 }} onClick={onRetry} className="bg-brand px-4 py-2 text-sm font-medium">
            Try again
          </motion.button>
        )}
        <motion.button type="button" whileTap={{ scale: 0.95 }} onClick={onDemo} className="border border-line bg-surface px-4 py-2 text-sm font-medium hover:border-text">
          Show a demo answer
        </motion.button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------

function Results({ result, prefix }: { result: SearchResult; prefix: string }) {
  const [active, setActive] = useState<Active>(null);
  // Escape clears a pinned citation
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setActive(null);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
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
      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1.25fr)_minmax(0,1fr)]">
        <AnswerPanel result={result} activeId={active?.id ?? null} onHover={hover} onLeave={leave} onCite={cite} />

        <aside aria-label="Sources" className="lg:sticky lg:top-24">
          <h2 className="mb-3 font-sans text-[0.95rem] font-bold tracking-normal">
            Sources <span className="ml-1 font-normal text-muted">{result.sources.length}</span>
          </h2>
          {result.sources.length === 0 ? (
            <p className="text-sm text-muted">No passages were retrieved.</p>
          ) : (
            <div className="flex flex-col gap-3 lg:max-h-[calc(100vh-17rem)] lg:overflow-y-auto lg:py-1 lg:pr-2 lg:pl-2" data-sources-scroll>
              {result.sources.map((s, i) => (
                <SourceCard
                  key={s.id}
                  idPrefix={prefix}
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
              stroke="var(--cite)"
              strokeWidth={1.6}
              strokeLinecap="round"
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ duration: 0.55, ease: EASE }}
            />
            <circle cx={path.x1} cy={path.y1} r={3} fill="var(--cite)" />
            <motion.circle cx={path.x2} cy={path.y2} r={3.5} fill="var(--cite)" initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ delay: 0.45, type: "spring", stiffness: 500, damping: 20 }} />
          </motion.g>
        )}
      </AnimatePresence>
    </svg>
  );
}
