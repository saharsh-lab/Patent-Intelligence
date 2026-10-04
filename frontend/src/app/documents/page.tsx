"use client";

import { StartChatButton } from "@/components/chat/StartChatButton";
import Link from "next/link";
import { LibraryHeader } from "@/components/LibraryHeader";
import { useRef, useState } from "react";
import useSWR from "swr";

import { Badge, Button, EmptyState, ErrorNotice, Panel, StatusBadge } from "@/components/ui";
import { ApiError, api, fetcher } from "@/lib/api";
import { formatBytes, formatDateTime, sectionLabel } from "@/lib/format";
import type { DocumentOut, SystemInfo } from "@/lib/types";

type UploadState = { name: string; status: "uploading" | "done" | "duplicate" | "error"; message?: string };

function UploadPanel({ onUploaded }: { onUploaded: () => void }) {
  const info = useSWR<SystemInfo>("/system/info", fetcher);
  const input = useRef<HTMLInputElement>(null);
  const [uploads, setUploads] = useState<UploadState[]>([]);
  const [dragging, setDragging] = useState(false);
  const busy = uploads.some((u) => u.status === "uploading");
  const extensions = info.data?.uploads.allowed_extensions ?? [".pdf", ".docx", ".txt"];
  const maxMb = info.data?.uploads.max_upload_mb ?? 25;

  async function uploadFiles(files: File[]) {
    if (files.length === 0) return;
    setUploads(files.map((f) => ({ name: f.name, status: "uploading" })));
    // One at a time: each upload is processed (extracted + embedded) by the server
    for (const [index, file] of files.entries()) {
      let next: UploadState;
      try {
        const result = await api.uploadDocument(file);
        next = result.duplicate
          ? { name: file.name, status: "duplicate", message: "Already uploaded; existing copy reused." }
          : { name: file.name, status: "done", message: `${result.document.chunk_count} passages indexed` };
      } catch (error) {
        next = { name: file.name, status: "error", message: error instanceof ApiError ? error.message : "Upload failed." };
      }
      setUploads((current) => current.map((u, i) => (i === index ? next : u)));
      onUploaded();
    }
    if (input.current) input.current.value = "";
  }

  return (
    <Panel title="Upload">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          if (!busy) uploadFiles(Array.from(e.dataTransfer.files));
        }}
        className={`flex flex-col items-center justify-center gap-2 rounded border border-dashed px-4 py-8 text-center ${
          dragging ? "border-accent bg-accent-soft" : "border-line-strong"
        }`}
      >
        <p className="text-sm">Drop patent documents here, or</p>
        <Button variant="secondary" disabled={busy} onClick={() => input.current?.click()}>
          Choose files
        </Button>
        <p className="text-xs text-muted">
          {extensions.join(", ").toUpperCase()} · up to {maxMb} MB each · scanned PDFs need OCR (not supported yet)
        </p>
        <input
          ref={input}
          type="file"
          multiple
          accept={extensions.join(",")}
          className="hidden"
          aria-label="Choose files to upload"
          onChange={(e) => uploadFiles(Array.from(e.target.files ?? []))}
        />
      </div>
      {uploads.length > 0 && (
        <ul className="mt-3 divide-y divide-line text-sm">
          {uploads.map((u, i) => (
            <li key={`${u.name}-${i}`} className="flex items-center justify-between gap-3 py-1.5">
              <span className="truncate">{u.name}</span>
              <span className="flex shrink-0 items-center gap-2 text-xs">
                {u.message && <span className={u.status === "error" ? "text-bad" : "text-muted"}>{u.message}</span>}
                {u.status === "uploading" && <Badge>Processing…</Badge>}
                {u.status === "done" && <Badge tone="ok">Indexed</Badge>}
                {u.status === "duplicate" && <Badge tone="accent">Duplicate</Badge>}
                {u.status === "error" && <Badge tone="bad">Rejected</Badge>}
              </span>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}

export default function DocumentsPage() {
  const { data, error, mutate } = useSWR<DocumentOut[]>("/documents", fetcher);
  const [deleting, setDeleting] = useState<string | null>(null);

  async function remove(doc: DocumentOut) {
    if (!window.confirm(`Delete "${doc.filename}" and all of its indexed passages?`)) return;
    setDeleting(doc.id);
    try {
      await api.deleteDocument(doc.id);
      await mutate();
    } finally {
      setDeleting(null);
    }
  }

  return (
    <>
      <LibraryHeader />
      <div className="grid gap-6">
        <UploadPanel onUploaded={() => mutate()} />

        <Panel title={`Your documents${data ? ` (${data.length})` : ""}`}>
          {error && <ErrorNotice error={error} title="Cannot load documents" />}
          {data?.length === 0 && <EmptyState title="No documents yet">Upload a patent PDF, DOCX or TXT to begin.</EmptyState>}
          {data && data.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[720px] text-sm">
                <thead className="text-left text-xs text-muted">
                  <tr>
                    <th className="pb-2 font-medium">Document</th>
                    <th className="pb-2 font-medium">Status</th>
                    <th className="pb-2 font-medium">Sections detected</th>
                    <th className="pb-2 pl-4 text-right font-medium">Pages</th>
                    <th className="pb-2 pl-4 text-right font-medium">Passages</th>
                    <th className="pb-2 pl-4 text-right font-medium">Size</th>
                    <th className="pb-2" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {data.map((doc) => (
                    <tr key={doc.id} className="align-top">
                      <td className="py-2.5 pr-3">
                        <Link href={`/documents/${doc.id}`} className="font-medium hover:text-accent hover:underline">
                          {doc.title || doc.filename}
                        </Link>
                        <p className="text-xs text-muted">
                          {doc.filename} · {formatDateTime(doc.uploaded_at)}
                          {doc.patent_numbers_detected.length > 0 && (
                            <span className="ml-1 font-mono">· {doc.patent_numbers_detected.join(", ")}</span>
                          )}
                        </p>
                        {doc.error_message && <p className="mt-1 text-xs text-bad">{doc.error_message}</p>}
                      </td>
                      <td className="py-2.5 pr-3"><StatusBadge status={doc.status} /></td>
                      <td className="py-2.5 pr-3 text-xs">
                        {doc.section_detection === "none" ? (
                          <span className="text-muted">None found (page-level citations)</span>
                        ) : (
                          <span className="flex flex-wrap gap-1">
                            {doc.sections_found.map((s) => <Badge key={s}>{sectionLabel(s)}</Badge>)}
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 pl-4 text-right font-mono text-xs">{doc.page_count ?? "—"}</td>
                      <td className="py-2.5 pl-4 text-right font-mono text-xs">{doc.chunk_count}</td>
                      <td className="py-2.5 pl-4 text-right font-mono text-xs whitespace-nowrap">{formatBytes(doc.size_bytes)}</td>
                      <td className="py-2.5 pl-3 text-right whitespace-nowrap">
                        {doc.status === "ready" && (
                          <span className="mr-3">
                            <StartChatButton documentId={doc.id} label="Chat" />
                          </span>
                        )}
                        <Button variant="danger" className="px-2 py-1 text-xs" disabled={deleting === doc.id} onClick={() => remove(doc)}>
                          Delete
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Panel>
      </div>
    </>
  );
}
