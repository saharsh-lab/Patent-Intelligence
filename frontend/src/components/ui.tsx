// Small shared building blocks in the reference site's style: translucent rounded
// cards with thin borders, pill buttons and pill badges. Each one carries an entrance
// animation (see globals.css), so every page that uses them comes alive.
import type { ReactNode } from "react";

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <header className="mb-8 flex flex-wrap items-end justify-between gap-4">
      <div>
        {/* The title slides up from behind a mask, the description fades in after it */}
        <h1 className="pi-line text-3xl tracking-tight md:text-[2.6rem] md:leading-[1.1]">
          <span>{title}</span>
        </h1>
        {description && (
          <p className="pi-in mt-2 max-w-3xl text-[0.95rem] text-muted" style={{ animationDelay: "0.15s" }}>
            {description}
          </p>
        )}
      </div>
      {actions && (
        <div className="pi-in" style={{ animationDelay: "0.2s" }}>
          {actions}
        </div>
      )}
    </header>
  );
}

export function Panel({
  title,
  aside,
  children,
  className = "",
}: {
  title?: ReactNode;
  aside?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`pi-in glass overflow-hidden rounded-3xl ${className}`}>
      {title && (
        <div className="flex items-center justify-between gap-3 border-b border-line px-5 py-3.5">
          <h2 className="text-[0.95rem] font-semibold tracking-tight">{title}</h2>
          {aside}
        </div>
      )}
      <div className="p-5">{children}</div>
    </section>
  );
}

type Tone = "neutral" | "accent" | "ok" | "warn" | "bad";

const TONES: Record<Tone, string> = {
  neutral: "bg-surface-2 text-muted border-line",
  accent: "bg-accent-soft text-accent border-transparent",
  ok: "bg-ok-soft text-ok border-transparent",
  warn: "bg-warn-soft text-warn border-transparent",
  bad: "bg-bad-soft text-bad border-transparent",
};

export function Badge({ tone = "neutral", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium whitespace-nowrap ${TONES[tone]}`}
    >
      {children}
    </span>
  );
}

const STATUS: Record<string, { tone: Tone; label: string }> = {
  ready: { tone: "ok", label: "Ready" },
  processing: { tone: "warn", label: "Processing" },
  pending: { tone: "neutral", label: "Pending" },
  failed: { tone: "bad", label: "Failed" },
  succeeded: { tone: "ok", label: "Answered" },
  insufficient_evidence: { tone: "warn", label: "Insufficient evidence" },
  running: { tone: "neutral", label: "Running" },
};

export function StatusBadge({ status }: { status: string }) {
  const { tone, label } = STATUS[status] ?? { tone: "neutral" as Tone, label: status };
  return <Badge tone={tone}>{label}</Badge>;
}

export function ErrorNotice({ error, title = "Something went wrong" }: { error: unknown; title?: string }) {
  const message = error instanceof Error ? error.message : String(error);
  const requestId = (error as { requestId?: string })?.requestId;
  return (
    <div role="alert" className="pi-in rounded-2xl border border-bad/30 bg-bad-soft px-4 py-3 text-sm">
      <p className="font-medium text-bad">{title}</p>
      <p className="mt-0.5">{message}</p>
      {requestId && <p className="mt-1 font-mono text-xs text-muted">Request ID: {requestId}</p>}
    </div>
  );
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="pi-in rounded-3xl border border-dashed border-line-strong bg-surface/40 px-6 py-12 text-center">
      <p className="text-sm font-medium">{title}</p>
      {children && <div className="mt-1 text-sm text-muted">{children}</div>}
    </div>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-2 text-sm text-muted" role="status">
      <span className="pi-busy" aria-hidden />
      {label}
    </span>
  );
}

export function Button({
  variant = "primary",
  className = "",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "danger" }) {
  const styles = {
    primary: "bg-brand shadow-card hover:opacity-90",
    secondary: "border border-line-strong bg-transparent hover:bg-surface-2",
    danger: "border border-bad/40 bg-transparent text-bad hover:bg-bad-soft",
  }[variant];
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-full px-4 py-2 text-sm font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${styles} ${className}`}
      {...props}
    />
  );
}

export function KeyValue({ items }: { items: [string, ReactNode][] }) {
  return (
    <dl className="grid grid-cols-[max-content_1fr] gap-x-6 gap-y-1.5 text-sm">
      {items.map(([key, value]) => (
        <div key={key} className="contents">
          <dt className="text-muted">{key}</dt>
          <dd className="min-w-0 break-words">{value}</dd>
        </div>
      ))}
    </dl>
  );
}
