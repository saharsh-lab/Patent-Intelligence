"use client";

import { useState } from "react";

import { Badge } from "@/components/ui";
import { formatScore, locationLabel } from "@/lib/format";
import type { EvidenceOut } from "@/lib/types";

const METHOD_LABEL: Record<string, string> = {
  hybrid: "vector + keyword",
  vector: "vector",
  keyword: "keyword",
  section: "read directly (requested section)",
};

function EvidenceCard({ item, idPrefix }: { item: EvidenceOut; idPrefix: string }) {
  const [expanded, setExpanded] = useState(false);
  const long = item.text.length > 420;
  return (
    <li
      id={item.label ? `${idPrefix}evidence-${item.label}` : undefined}
      className={`pi-card scroll-mt-4 border bg-surface px-[18px] py-3.5 ${item.cited ? "border-line-strong" : "border-line"}`}
    >
      <div className="flex flex-wrap items-center gap-2">
        {item.label ? (
          <span className="font-serif text-[0.95rem] text-stamp italic">Fig. {item.label.replace(/^E/, "")}</span>
        ) : (
          <span className="font-mono text-xs text-muted">#{item.rank}</span>
        )}
        <span className="min-w-0 truncate font-serif text-[1rem] font-medium" title={item.source_title ?? undefined}>
          {locationLabel(item)}
        </span>
        {item.source_type !== "upload" && (
          <Badge tone={item.source_type === "demo" ? "warn" : "neutral"}>
            {item.source_type === "demo" ? "Demo patent" : `${item.source_type.toUpperCase()} patent`}
          </Badge>
        )}
        {item.cited ? <Badge tone="accent">Cited</Badge> : <Badge>Not cited</Badge>}
        {item.source_url && (
          <a href={item.source_url} target="_blank" rel="noopener noreferrer" className="ml-auto text-xs text-accent hover:underline">
            Espacenet ↗
          </a>
        )}
      </div>
      <p className={`mt-2 text-sm whitespace-pre-line ${expanded || !long ? "" : "line-clamp-5"}`}>{item.text}</p>
      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 font-mono text-[11px] text-muted">
        <span>rank {item.rank}</span>
        <span>{METHOD_LABEL[item.method] ?? item.method}</span>
        <span title="Cosine similarity between question and passage embeddings">sim {formatScore(item.vector_similarity)}</span>
        <span title="PostgreSQL full-text rank">kw {formatScore(item.keyword_score, 3)}</span>
        {item.rerank_score != null && <span title="Cross-encoder relevance">rerank {formatScore(item.rerank_score)}</span>}
        {long && (
          <button type="button" className="ml-auto font-sans text-accent hover:underline" onClick={() => setExpanded(!expanded)}>
            {expanded ? "Show less" : "Show full passage"}
          </button>
        )}
      </div>
    </li>
  );
}

export function EvidenceList({ evidence, idPrefix = "" }: { evidence: EvidenceOut[]; idPrefix?: string }) {
  if (evidence.length === 0) {
    return <p className="text-sm text-muted">No passages were retrieved.</p>;
  }
  return (
    <ol className="space-y-2.5">
      {evidence.map((item) => (
        <EvidenceCard idPrefix={idPrefix} key={item.chunk_id} item={item} />
      ))}
    </ol>
  );
}
