"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState } from "react";

// The agent runs these stages in order; the last one is held until the answer
// arrives (a local model can take a minute or more).
const STAGES = ["Searching filings", "Ranking sources", "Writing answer", "Checking every citation"];

export function LoadingState({ onCancel }: { onCancel: () => void }) {
  const [stage, setStage] = useState(0);
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const started = Date.now();
    const timer = setInterval(() => {
      const seconds = (Date.now() - started) / 1000;
      setElapsed(Math.floor(seconds));
      setStage(Math.min(STAGES.length - 1, Math.floor(seconds / 2.2)));
    }, 250);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]" aria-busy>
      <section className="rounded-3xl border border-line bg-surface/85 p-6 shadow-card md:p-8">
        {/* Rotating status line */}
        <div className="flex items-center gap-3" role="status" aria-live="polite">
          <span className="relative flex h-2.5 w-2.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-clay opacity-60" />
            <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-clay" />
          </span>
          <div className="relative h-6 flex-1 overflow-hidden">
            <AnimatePresence mode="popLayout" initial={false}>
              <motion.span
                key={stage}
                initial={{ y: 18, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                exit={{ y: -18, opacity: 0 }}
                transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
                className="absolute inset-0 font-serif text-lg text-text"
              >
                {STAGES[stage]}…
              </motion.span>
            </AnimatePresence>
          </div>
          <span className="font-mono text-xs text-muted tabular-nums">{elapsed}s</span>
        </div>

        {/* Scan line over answer-shaped skeleton lines */}
        <div className="relative mt-6 overflow-hidden rounded-2xl border border-line bg-bg/60 p-5" style={{ ["--scan-distance" as string]: "150px" }}>
          <div className="pi-scanline" aria-hidden />
          <div className="space-y-3">
            {[100, 94, 97, 62].map((w, i) => (
              <div key={i} className="skeleton h-3.5" style={{ width: `${w}%` }} />
            ))}
            <div className="h-2" />
            {[88, 71].map((w, i) => (
              <div key={i} className="skeleton h-3.5" style={{ width: `${w}%` }} />
            ))}
          </div>
        </div>

        <div className="mt-5 flex flex-wrap items-center justify-between gap-3 text-sm text-muted">
          <span>{elapsed >= 8 ? "Still working: answers from the local model can take a minute." : "Every sentence is checked against its source."}</span>
          <motion.button
            type="button"
            whileTap={{ scale: 0.95 }}
            onClick={onCancel}
            className="rounded-full border border-line-strong px-3 py-1 text-xs font-medium text-text hover:border-clay/60 hover:text-accent"
          >
            Cancel
          </motion.button>
        </div>
      </section>

      {/* Source-card skeletons */}
      <div className="space-y-3">
        <div className="skeleton h-4 w-24" />
        {[0, 1, 2].map((i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.08 * i, type: "spring", stiffness: 220, damping: 26 }}
            className="rounded-2xl border border-line bg-surface/85 p-4 shadow-card"
          >
            <div className="flex justify-between">
              <div className="skeleton h-3 w-12" />
              <div className="skeleton h-3 w-24" />
            </div>
            <div className="skeleton mt-3 h-4 w-4/5" />
            <div className="skeleton mt-2 h-3 w-2/5" />
            <div className="skeleton mt-4 h-3 w-full" />
            <div className="skeleton mt-2 h-3 w-11/12" />
            <div className="skeleton mt-4 h-1 w-full" />
          </motion.div>
        ))}
      </div>
    </div>
  );
}
