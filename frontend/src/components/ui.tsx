// Small shared building blocks. Kept deliberately plain: thin borders, small radii,
// no shadows or gradients.
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
    <header className="mb-6 flex flex-wrap items-end justify-between gap-4 border-b border-line pb-4">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
        {description && <p className="mt-1 max-w-3xl text-sm text-muted">{description}</p>}
      </div>
      {actions}
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
    <section className={`rounded-xl border border-line bg-surface shadow-card ${className}`}>
      {title && (
        <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-2.5">
          <h2 className="text-sm font-semibold">{title}</h2>
          {aside}
        </div>
      )}
      <div className="p-4">{children}</div>
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
      className={`inline-flex items-center rounded-md border px-1.5 py-0.5 text-xs font-medium whitespace-nowrap ${TONES[tone]}`}
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
    <div role="alert" className="rounded-lg border border-bad/30 bg-bad-soft px-4 py-3 text-sm">
      <p className="font-medium text-bad">{title}</p>
      <p className="mt-0.5">{message}</p>
      {requestId && <p className="mt-1 font-mono text-xs text-muted">Request ID: {requestId}</p>}
    </div>
  );
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="rounded-xl border border-dashed border-line-strong px-6 py-10 text-center">
      <p className="text-sm font-medium">{title}</p>
      {children && <div className="mt-1 text-sm text-muted">{children}</div>}
    </div>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-2 text-sm text-muted" role="status">
      <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-line-strong border-t-accent" />
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
    primary: "bg-brand text-white shadow-card hover:brightness-110",
    secondary: "border border-line-strong bg-surface hover:bg-surface-2",
    danger: "border border-line-strong bg-surface text-bad hover:bg-bad-soft",
  }[variant];
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${styles} ${className}`}
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
