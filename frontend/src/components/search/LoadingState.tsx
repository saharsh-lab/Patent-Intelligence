"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState } from "react";

// The agent runs these stages in order; the last one is held until the answer
// arrives (a local model can take a minute or more).
const STAGES = ["Searching filings", "Ranking sources", "Writing answer", "Checking every citation"];

/** The reference's scan box (a blue line sweeping a white sheet) with a rotating status line. */
export function ScanStatus({ height = 120, stages = STAGES, className = "" }: { height?: number; stages?: string[]; className?: string }) {
  const [stage, setStage] = useState(0);
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const started = Date.now();
    const timer = setInterval(() => {
      const seconds = (Date.now() - started) / 1000;
      setElapsed(Math.floor(seconds));
      setStage(Math.min(stages.length - 1, Math.floor(seconds / 2.2)));
    }, 250);
    return () => clearInterval(timer);
  }, [stages.length]);

  return (
    <div
      className={`relative grid place-items-center overflow-hidden border border-line bg-surface text-muted ${className}`}
      style={{ height, ["--scan-distance" as string]: `${height * 0.84}px` }}
      role="status"
      aria-live="polite"
    >
      <div className="pi-scanline" aria-hidden />
      <div className="relative h-6 w-full overflow-hidden text-center">
        <AnimatePresence mode="popLayout" initial={false}>
          <motion.span
            key={stage}
            initial={{ y: 18, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: -18, opacity: 0 }}
            transition={{ duration: 0.35, ease: [0.2, 0.8, 0.2, 1] }}
            className="absolute inset-0"
          >
            {stages[stage]}
          </motion.span>
        </AnimatePresence>
      </div>
      <span className="absolute right-3 bottom-2 font-mono text-[11px] tabular-nums">{elapsed}s</span>
    </div>
  );
}

export function LoadingState({ onCancel }: { onCancel: () => void }) {
  const [slow, setSlow] = useState(false);
  useEffect(() => {
    const timer = setTimeout(() => setSlow(true), 8000);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="grid items-start gap-6 lg:grid-cols-[1.25fr_1fr]" aria-busy>
      <div>
        <ScanStatus />
        {/* Answer-shaped skeleton */}
        <div className="mt-4 border border-line bg-surface p-6">
          <div className="skeleton mb-4 h-3.5 w-16" />
          <div className="space-y-3">
            {[100, 94, 97, 62].map((w, i) => (
              <div key={i} className="skeleton h-4" style={{ width: `${w}%` }} />
            ))}
          </div>
        </div>
        <div className="mt-3 flex flex-wrap items-center justify-between gap-3 text-sm text-muted">
          <span>{slow ? "Still working: answers from the local model can take a minute." : "Every sentence is checked against its source."}</span>
          <button type="button" onClick={onCancel} className="border border-line bg-surface px-3 py-1 text-xs font-medium text-text hover:border-text">
            Cancel
          </button>
        </div>
      </div>

      {/* Source-card skeletons */}
      <div className="flex flex-col gap-3">
        <div className="skeleton h-4 w-24" />
        {[0, 1, 2].map((i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.09 * i, type: "spring", stiffness: 220, damping: 26 }}
            className="border border-line bg-surface px-[18px] py-4"
          >
            <div className="flex justify-between">
              <div className="skeleton h-3 w-12" />
              <div className="skeleton h-3 w-24" />
            </div>
            <div className="skeleton mt-3 h-4 w-4/5" />
            <div className="skeleton mt-2 h-3 w-2/5" />
            <div className="skeleton mt-4 h-3 w-full" />
            <div className="skeleton mt-2 h-3 w-11/12" />
            <div className="skeleton mt-4 h-[3px] w-full" />
          </motion.div>
        ))}
      </div>
    </div>
  );
}
