// The "Patent Intelligence" mark: a square sheet with a P drawn as one stroke. With
// `draw`, both strokes draw themselves in once (CSS, so reduced motion shows it finished).
export function LogoMark({ size = 32, draw = false, className = "" }: { size?: number; draw?: boolean; className?: string }) {
  const stroke = draw ? "pi-draw" : "";
  return (
    <svg viewBox="0 0 40 40" width={size} height={size} aria-hidden className={className} fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="4" y="4" width="32" height="32" rx="2" pathLength={140} className={stroke} />
      <path d="M12 28V12h9a5 5 0 0 1 0 10h-9" pathLength={140} className={stroke} style={draw ? { animationDelay: "0.4s" } : undefined} />
    </svg>
  );
}

export function Wordmark({ draw = false }: { draw?: boolean }) {
  return (
    <span className="flex items-center gap-2.5">
      <LogoMark size={34} draw={draw} className="shrink-0 text-text" />
      {/* Phones: the mark alone, so the bar's buttons fit */}
      <span className="hidden text-[1.05rem] leading-none font-bold tracking-tight whitespace-nowrap min-[420px]:inline">
        Patent Intelligence
      </span>
    </span>
  );
}
