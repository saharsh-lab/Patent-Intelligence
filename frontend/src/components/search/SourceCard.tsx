"use client";

import { AnimatePresence, motion, useMotionValue, useReducedMotion, useSpring } from "framer-motion";
import { useState, type PointerEvent } from "react";

import type { Source } from "@/lib/search";

const PREVIEW = 200;

/** Cut at a word boundary near `limit` characters. */
function preview(text: string, limit = PREVIEW) {
  if (text.length <= limit + 40) return { head: text, rest: "" };
  const cut = text.lastIndexOf(" ", limit);
  const at = cut > limit * 0.6 ? cut : limit;
  return { head: text.slice(0, at), rest: text.slice(at) };
}

// Look from the reference: white sheet, thin border, "Fig. n" stamp, serif title,
// 3px score bar. Active (hovered or cited): blue border, blue left rule, shifted left.
export function SourceCard({
  source,
  idPrefix = "",
  index,
  active,
  onActivate,
  onDeactivate,
  registerRef,
}: {
  source: Source;
  idPrefix?: string;
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
    ry.set(((e.clientX - r.left) / r.width - 0.5) * 5);
    rx.set(-((e.clientY - r.top) / r.height - 0.5) * 5);
  }

  const meta = [source.assignee, source.year].filter(Boolean).join(", ");
  const score = source.score;

  return (
    <motion.article
      ref={registerRef}
      id={`${idPrefix}source-${source.id}`}
      layout="position"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0, x: active ? -4 : 0 }}
      transition={{ type: "spring", stiffness: 240, damping: 24, delay: active ? 0 : 0.09 * index }}
      style={{ rotateX: rx, rotateY: ry, transformPerspective: 900 }}
      onPointerMove={tilt}
      onPointerEnter={onActivate}
      onPointerLeave={() => {
        rx.set(0);
        ry.set(0);
        onDeactivate();
      }}
      className={`relative scroll-mt-28 border bg-surface px-[18px] py-4 transition-colors duration-200 ${active ? "border-cite" : "border-line"}`}
    >
      <span
        aria-hidden
        className="pointer-events-none absolute -top-px -bottom-px -left-px w-[3px] origin-center bg-cite transition-transform duration-200"
        style={{ transform: `scaleY(${active ? 1 : 0})` }}
      />

      <div className="flex items-baseline justify-between gap-3 text-[0.8rem] text-muted">
        <span className="font-serif text-[0.95rem] text-stamp italic">Fig. {source.id}</span>
        <span className="flex min-w-0 items-baseline gap-2">
          {source.location && <span className="shrink-0 border border-line px-1.5 text-[11px]">{source.location}</span>}
          {source.patent_number && source.patent_number !== source.title && <span className="truncate">{source.patent_number}</span>}
        </span>
      </div>

      <h3 className="mt-1.5 font-serif text-[1.05rem] leading-[1.3] font-medium text-text">
        {source.url ? (
          <a href={source.url} target="_blank" rel="noopener noreferrer" className="decoration-cite underline-offset-4 hover:underline">
            {source.title}
          </a>
        ) : (
          source.title
        )}
      </h3>
      {(meta || source.synthetic) && (
        <p className="mt-0.5 mb-2 flex flex-wrap items-center gap-2 text-[0.82rem] text-muted">
          {meta}
          {source.synthetic && <span className="border border-sage/60 px-1.5 text-[11px] text-ok">Synthetic demo record</span>}
        </p>
      )}

      <div className="text-[0.88rem] leading-normal whitespace-pre-line text-text/85">
        {head}
        {rest && !expanded && "…"}
        <AnimatePresence initial={false}>
          {expanded && rest && (
            <motion.span key="rest" initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.3 }}>
              {rest}
            </motion.span>
          )}
        </AnimatePresence>
      </div>

      <div className="mt-3 flex items-center gap-3">
        {score != null ? (
          <div className="flex flex-1 items-center gap-2.5" title="Relevance: similarity between your question and this passage">
            <div className="h-[3px] flex-1 bg-bg">
              {/* Fills on reveal: scaleX from the left (transform only) */}
              <div className="pi-grow h-full bg-text" style={{ width: `${Math.round(score * 100)}%`, animationDelay: `${0.3 + 0.09 * index}s` }} />
            </div>
            <span className="font-mono text-[11px] text-muted tabular-nums">{Math.round(score * 100)}%</span>
          </div>
        ) : (
          <span className="flex-1" />
        )}
        {rest && (
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            aria-expanded={expanded}
            className="flex items-center gap-1 text-xs font-medium text-accent hover:underline"
          >
            {expanded ? "Less" : "Full passage"}
            <motion.svg animate={{ rotate: expanded ? 180 : 0 }} width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" aria-hidden>
              <path d="m6 9 6 6 6-6" />
            </motion.svg>
          </button>
        )}
      </div>
    </motion.article>
  );
}
