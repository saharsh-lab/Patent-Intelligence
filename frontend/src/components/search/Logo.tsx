// The "Patent Intelligence" mark from the reference component: a square sheet with
// a P drawn as one stroke. With `draw`, both strokes draw themselves in once (CSS,
// so reduced motion shows it finished).
export function LogoMark({ size = 32, draw = false, className = "" }: { size?: number; draw?: boolean; className?: string }) {
  const stroke = draw ? "pi-draw" : "";
  return (
    <svg viewBox="0 0 40 40" width={size} height={size} aria-hidden className={className} fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="4" y="4" width="32" height="32" rx="2" pathLength={140} className={stroke} />
      <path d="M12 28V12h9a5 5 0 0 1 0 10h-9" pathLength={140} className={stroke} style={draw ? { animationDelay: "0.4s" } : undefined} />
    </svg>
  );
}

/** Fired by the sidebar logo; the search page resets to its start screen. */
export const NEW_SEARCH_EVENT = "pi:new-search";

export function Wordmark({ compact = false, draw = false }: { compact?: boolean; draw?: boolean }) {
  return (
    <span className="flex items-center gap-2.5">
      <LogoMark size={compact ? 26 : 30} draw={draw} className="shrink-0 text-text" />
      <span className="leading-tight">
        <span className="block font-serif text-[17px] font-medium tracking-tight">Patent Intelligence</span>
        {!compact && <span className="block text-[11px] text-muted">Evidence-grounded patent AI</span>}
      </span>
    </span>
  );
}
