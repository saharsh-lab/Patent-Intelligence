"use client";

import { AnimatePresence, motion, useMotionValue, useReducedMotion, useSpring } from "framer-motion";
import { useState, type PointerEvent } from "react";

import type { Source } from "@/lib/search";

const PREVIEW = 220;

/** Cut at a word boundary near `limit` characters. */
function preview(text: string, limit = PREVIEW) {
  if (text.length <= limit + 40) return { head: text, rest: "" };
  const cut = text.lastIndexOf(" ", limit);
  const at = cut > limit * 0.6 ? cut : limit;
  return { head: text.slice(0, at), rest: text.slice(at) };
}

export function SourceCard({
  source,
  index,
  active,
  onActivate,
  onDeactivate,
  registerRef,
}: {
  source: Source;
  index: number;
  active: boolean;
  onActivate: () => void;
  onDeactivate: () => void;
  registerRef: (el: HTMLElement | null) => void;
}) {
  const reduce = useReducedMotion();
  const [expanded, setExpanded] = useState(false);
  const { head, rest } = preview(source.snippet);

  // Subtle 3D tilt that follows the pointer (mouse/pen only), sprung back on leave
  const rx = useSpring(useMotionValue(0), { stiffness: 220, damping: 22 });
  const ry = useSpring(useMotionValue(0), { stiffness: 220, damping: 22 });
  function tilt(e: PointerEvent<HTMLElement>) {
    if (reduce || e.pointerType === "touch") return;
    const r = e.currentTarget.getBoundingClientRect();
    ry.set(((e.clientX - r.left) / r.width - 0.5) * 6);
    rx.set(-((e.clientY - r.top) / r.height - 0.5) * 6);
  }
  function untilt() {
    rx.set(0);
    ry.set(0);
  }

  const meta = [source.assignee, source.year].filter(Boolean).join(", ");
  const score = source.score;

  return (
    <motion.article
      ref={registerRef}
      id={`source-${source.id}`}
      layout="position"
      initial={{ opacity: 0, y: 18, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1, x: active ? -4 : 0 }}
      transition={{ type: "spring", stiffness: 240, damping: 24, delay: active ? 0 : 0.09 * index }}
      style={{ rotateX: rx, rotateY: ry, transformPerspective: 900 }}
      onPointerMove={tilt}
      onPointerEnter={onActivate}
      onPointerLeave={() => {
        untilt();
        onDeactivate();
      }}
      className="group relative scroll-mt-28 rounded-2xl border border-line bg-surface/90 p-4 shadow-card md:p-5"
    >
      {/* Active state: clay glow + left rule (opacity only) */}
      <span
        aria-hidden
        className="pointer-events-none absolute -inset-px rounded-[inherit] border border-clay/70 transition-opacity duration-300"
        style={{ opacity: active ? 1 : 0, boxShadow: "0 0 0 4px rgb(217 119 87 / 0.12), 0 14px 36px -10px rgb(217 119 87 / 0.45)" }}
      />
      <span
        aria-hidden
        className="pointer-events-none absolute top-3 bottom-3 -left-px w-[3px] origin-center rounded-full bg-clay transition-transform duration-300"
        style={{ transform: `scaleY(${active ? 1 : 0})` }}
      />

      <div className="flex items-center justify-between gap-3 text-xs text-muted">
        <span className="font-serif text-[13px] text-accent italic">Fig. {source.id}</span>
        <span className="flex items-center gap-2 truncate">
          {source.location && <span className="rounded-full bg-surface-2 px-2 py-0.5 text-[11px] text-text/80">{source.location}</span>}
          {source.patent_number && source.patent_number !== source.title && <span className="truncate font-mono text-[11px]">{source.patent_number}</span>}
        </span>
      </div>

      <h3 className="mt-2 font-serif text-[17px] leading-snug font-medium text-text">
        {source.url ? (
          <a href={source.url} target="_blank" rel="noopener noreferrer" className="decoration-clay/50 underline-offset-4 hover:underline">
            {source.title}
          </a>
        ) : (
          source.title
        )}
      </h3>
      {(meta || source.synthetic) && (
        <p className="mt-1 flex flex-wrap items-center gap-2 text-[13px] text-muted">
          {meta}
          {source.synthetic && (
            <span className="rounded-full bg-sage/25 px-2 py-0.5 text-[11px] font-medium text-ok">Synthetic demo record</span>
          )}
        </p>
      )}

      <div className="mt-3 text-sm leading-relaxed whitespace-pre-line text-text/85">
        {head}
        {rest && !expanded && "…"}
        <AnimatePresence initial={false}>
          {expanded && rest && (
            <motion.span
              key="rest"
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3 }}
            >
              {rest}
            </motion.span>
          )}
        </AnimatePresence>
      </div>

      <div className="mt-4 flex items-center gap-3">
        {score != null ? (
          <div className="flex flex-1 items-center gap-2.5" title="Similarity between your question and this passage">
            <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-surface-2">
              {/* Fills on reveal: scaleX from the left (transform only) */}
              <div className="pi-grow h-full origin-left rounded-full" style={{ width: `${Math.round(score * 100)}%`, background: "linear-gradient(90deg, var(--sage), var(--clay))", animationDelay: `${0.3 + 0.09 * index}s` }} />
            </div>
            <span className="font-mono text-[11px] text-muted tabular-nums">{Math.round(score * 100)}%</span>
          </div>
        ) : (
          <span className="flex-1" />
        )}
        {rest && (
          <motion.button
            type="button"
            whileTap={{ scale: 0.94 }}
            onClick={() => setExpanded((v) => !v)}
            aria-expanded={expanded}
            className="flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium text-accent hover:bg-accent-soft"
          >
            {expanded ? "Less" : "Full passage"}
            <motion.svg animate={{ rotate: expanded ? 180 : 0 }} width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" aria-hidden>
              <path d="m6 9 6 6 6-6" />
            </motion.svg>
          </motion.button>
        )}
      </div>
    </motion.article>
  );
}
