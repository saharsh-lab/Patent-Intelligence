"use client";

import { StartChatButton } from "@/components/chat/StartChatButton";
import Link from "next/link";
import { use, useState } from "react";
import useSWR from "swr";

import { Badge, EmptyState, ErrorNotice, KeyValue, PageHeader, Panel, StatusBadge } from "@/components/ui";
import { fetcher } from "@/lib/api";
import { formatBytes, formatDateTime, sectionLabel } from "@/lib/format";
import type { ChunkOut, DocumentOut } from "@/lib/types";

export default function DocumentDetailPage({ params }: PageProps<"/documents/[id]">) {
  const { id } = use(params);
  const [section, setSection] = useState<string>("");
  const doc = useSWR<DocumentOut>(`/documents/${id}`, fetcher);
  const chunks = useSWR<ChunkOut[]>(
    `/documents/${id}/chunks?limit=200${section ? `&section=${section}` : ""}`,
    fetcher,
  );

  if (doc.error) return <ErrorNotice error={doc.error} title="Cannot load document" />;
  if (!doc.data) return <p className="text-sm text-muted">Loading…</p>;
  const d = doc.data;

  return (
    <>
      <p className="mb-2 text-sm">
        <Link href="/documents" className="text-accent hover:underline">← Documents</Link>
      </p>
      <PageHeader
        title={d.title || d.filename}
        actions={
          <StartChatButton documentId={d.id} label="Chat about this document" />
        }
      />
      <div className="grid gap-6 lg:grid-cols-[1fr_2fr]">
        <Panel title="Details">
          <KeyValue
            items={[
              ["Status", <StatusBadge key="s" status={d.status} />],
              ["File", d.filename],
              ["Type", d.mime_type],
              ["Size", formatBytes(d.size_bytes)],
              ["Pages", d.page_count ?? "—"],
              ["Passages", d.chunk_count],
              ["Uploaded", formatDateTime(d.uploaded_at)],
              ["Patent numbers", d.patent_numbers_detected.length ? <span key="n" className="font-mono text-xs">{d.patent_numbers_detected.join(", ")}</span> : "None detected"],
              ["Section detection", d.section_detection === "headings" ? "From headings" : "Not found (page-level)"],
            ]}
          />
          {d.error_message && <p className="mt-3 text-sm text-bad">{d.error_message}</p>}
        </Panel>

        <Panel
          title="Indexed passages"
          aside={
            <select
              aria-label="Filter by section"
              value={section}
              onChange={(e) => setSection(e.target.value)}
              className="rounded border border-line-strong bg-surface px-2 py-1 text-xs"
            >
              <option value="">All sections</option>
              {d.sections_found.map((s) => (
                <option key={s} value={s}>{sectionLabel(s)}</option>
              ))}
            </select>
          }
        >
          {chunks.error && <ErrorNotice error={chunks.error} />}
          {chunks.data?.length === 0 && <EmptyState title="No passages in this section" />}
          <ol className="space-y-3">
            {chunks.data?.map((c) => (
              <li key={c.id} className="rounded border border-line px-3 py-2">
                <div className="mb-1 flex flex-wrap items-center gap-2 text-xs text-muted">
                  <span className="font-mono">#{c.chunk_index}</span>
                  <Badge>{sectionLabel(c.section)}</Badge>
                  {typeof c.meta.claim_number === "number" && <Badge tone="accent">Claim {c.meta.claim_number}</Badge>}
                  {c.page_number && <span>p. {c.page_number}</span>}
                  <span className="ml-auto font-mono">{c.token_count} tokens</span>
                </div>
                <p className="text-sm whitespace-pre-line">{c.text}</p>
              </li>
            ))}
          </ol>
        </Panel>
      </div>
    </>
  );
}
