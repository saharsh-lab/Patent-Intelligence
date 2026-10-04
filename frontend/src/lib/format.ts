export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatMs(ms: number | null | undefined): string {
  if (ms === null || ms === undefined) return "—";
  return ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(1)} s`;
}

export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `${Math.round(value * 100)}%`;
}

export function formatScore(value: number | null | undefined, digits = 2): string {
  return value === null || value === undefined ? "—" : value.toFixed(digits);
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const SECTION_LABELS: Record<string, string> = {
  front_matter: "Front matter",
  title: "Title",
  abstract: "Abstract",
  technical_field: "Technical field",
  background: "Background",
  summary: "Summary",
  drawings: "Drawings",
  description: "Description",
  claims: "Claims",
};

export function sectionLabel(section: string | null | undefined): string {
  if (!section) return "Unsectioned";
  return SECTION_LABELS[section] ?? section.replace(/_/g, " ");
}

/** "battery.pdf · Claim 3 · p. 4" */
export function locationLabel(parts: {
  source_label?: string;
  section?: string | null;
  claim_number?: number | null;
  page_number?: number | null;
}): string {
  const out: string[] = [];
  if (parts.source_label) out.push(parts.source_label);
  if (parts.claim_number) out.push(`Claim ${parts.claim_number}`);
  else if (parts.section) out.push(sectionLabel(parts.section));
  if (parts.page_number) out.push(`p. ${parts.page_number}`);
  return out.join(" · ");
}
