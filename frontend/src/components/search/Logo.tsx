// Our own mark for "Patent Intelligence": a framed sheet with a P drawn as one
// stroke (from the reference component), plus a small clay seal. With `draw`, the
// strokes draw themselves in once (CSS, so reduced motion shows it finished).
export function LogoMark({ size = 32, draw = false, className = "" }: { size?: number; draw?: boolean; className?: string }) {
  const stroke = draw ? "pi-draw" : "";
  return (
    <svg viewBox="0 0 40 40" width={size} height={size} aria-hidden className={className}>
      <rect x="4" y="4" width="32" height="32" rx="7" fill="none" stroke="currentColor" strokeWidth="2.2" pathLength={140} className={stroke} />
      <path
        d="M14 29V11h8a5.5 5.5 0 0 1 0 11h-8"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
        pathLength={140}
        className={stroke}
        style={draw ? { animationDelay: "0.45s" } : undefined}
      />
      <circle cx="28.5" cy="28.5" r="3.2" fill="var(--clay)" className={draw ? "pi-cite" : ""} style={draw ? { animationDelay: "1.2s" } : undefined} />
    </svg>
  );
}

export function Wordmark({ compact = false }: { compact?: boolean }) {
  return (
    <span className="flex items-center gap-2.5">
      <LogoMark size={compact ? 26 : 30} className="shrink-0 text-text" />
      <span className="leading-tight">
        <span className="block font-serif text-[15px] font-medium tracking-tight">Patent Intelligence</span>
        {!compact && <span className="block text-[11px] text-muted">Evidence-grounded patent AI</span>}
      </span>
    </span>
  );
}
