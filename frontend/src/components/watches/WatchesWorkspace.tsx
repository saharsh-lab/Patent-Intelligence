"use client";

import { useState } from "react";
import useSWR from "swr";

import { Badge, Button, EmptyState, ErrorNotice, Panel, Spinner } from "@/components/ui";
import { ApiError, fetcher, parseError } from "@/lib/api";
import { formatDateTime, formatPercent } from "@/lib/format";
import type { DocumentOut, SourceStatusOut, WatchCheckOut, WatchHitOut, WatchOut } from "@/lib/types";

async function send(path: string, init: RequestInit = {}) {
  const response = await fetch(`/api${path}`, {
    ...init,
    headers: init.body ? { "Content-Type": "application/json" } : undefined,
  });
  if (!response.ok) throw await parseError(response);
  return response.status === 204 ? null : response.json();
}

export function WatchesWorkspace() {
  const watches = useSWR<WatchOut[]>("/watches", fetcher);
  const documents = useSWR<DocumentOut[]>("/documents", fetcher);
  const sources = useSWR<SourceStatusOut[]>("/patents/sources", fetcher);
  const [selected, setSelected] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [keywords, setKeywords] = useState("");
  const [cpc, setCpc] = useState("");
  const [reference, setReference] = useState("");

  const live = (sources.data ?? []).filter((s) => s.status === "available");
  const active = selected ?? watches.data?.[0]?.id ?? null;
  const hits = useSWR<WatchHitOut[]>(active ? `/watches/${active}/hits` : null, fetcher);

  async function act(label: string, fn: () => Promise<unknown>) {
    setBusy(label);
    setError(null);
    setMessage(null);
    try {
      await fn();
      await watches.mutate();
      await hits.mutate();
    } catch (e) {
      setError(e instanceof ApiError ? e : new Error("The request failed."));
    } finally {
      setBusy(null);
    }
  }

  const create = () =>
    act("create", async () => {
      const watch: WatchOut = await send("/watches", {
        method: "POST",
        body: JSON.stringify({
          name,
          keywords,
          cpc: cpc.split(",").map((c) => c.trim()).filter(Boolean),
          reference_document_id: reference || null,
        }),
      });
      setSelected(watch.id);
      setName("");
      setKeywords("");
      setCpc("");
    });

  const check = (id: string) =>
    act(`check-${id}`, async () => {
      const outcome: WatchCheckOut = await send(`/watches/${id}/check`, { method: "POST" });
      setMessage(
        outcome.error
          ? `Check failed: ${outcome.error}`
          : `${outcome.new_hits} new publication(s)${outcome.imported.length ? `; imported ${outcome.imported.join(", ")}` : ""}.`,
      );
    });

  return (
    <div className="space-y-6">
      {live.length === 0 && sources.data && (
        <p className="rounded border border-warn/30 bg-warn-soft px-4 py-2 text-sm text-warn">
          No patent database is configured, so checks cannot find anything. Add EPO_OPS_KEY and EPO_OPS_SECRET to .env
          (free at developers.epo.org) and restart the API.
        </p>
      )}

      <Panel title="New watch">
        <div className="grid gap-3 md:grid-cols-[1fr_2fr_1fr_1fr_auto] md:items-end">
          <label className="text-xs text-muted">
            Name
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Battery immersion cooling"
              className="mt-1 w-full rounded border border-line-strong bg-surface px-2 py-1.5 text-sm text-text" />
          </label>
          <label className="text-xs text-muted">
            Keywords
            <input value={keywords} onChange={(e) => setKeywords(e.target.value)} placeholder="battery dielectric immersion cooling"
              className="mt-1 w-full rounded border border-line-strong bg-surface px-2 py-1.5 text-sm text-text" />
          </label>
          <label className="text-xs text-muted">
            CPC (optional)
            <input value={cpc} onChange={(e) => setCpc(e.target.value)} placeholder="H01M10/613"
              className="mt-1 w-full rounded border border-line-strong bg-surface px-2 py-1.5 text-sm text-text" />
          </label>
          <label className="text-xs text-muted">
            Rank against
            <select value={reference} onChange={(e) => setReference(e.target.value)}
              className="mt-1 w-full rounded border border-line-strong bg-surface px-2 py-1.5 text-sm text-text">
              <option value="">— no document —</option>
              {(documents.data ?? []).filter((d) => d.status === "ready").map((d) => (
                <option key={d.id} value={d.id}>{d.title || d.filename}</option>
              ))}
            </select>
          </label>
          <Button disabled={!name.trim() || !(keywords.trim() || cpc.trim()) || busy !== null} onClick={create}>
            Add watch
          </Button>
        </div>
      </Panel>

      {error ? <ErrorNotice error={error} /> : null}
      {message && <p className="text-sm text-muted" role="status">{message}</p>}

      {watches.isLoading ? (
        <Spinner />
      ) : (watches.data ?? []).length === 0 ? (
        <EmptyState title="No watches yet">Add one above to be notified of new publications in a field.</EmptyState>
      ) : (
        <div className="grid gap-6 lg:grid-cols-[20rem_minmax(0,1fr)]">
          <ul className="space-y-2">
            {(watches.data ?? []).map((w) => (
              <li key={w.id}>
                <div
                  className={`rounded border px-3 py-2 text-sm ${w.id === active ? "border-accent bg-accent-soft" : "border-line bg-surface"}`}
                >
                  <button type="button" className="w-full text-left" onClick={() => setSelected(w.id)}>
                    <span className="flex items-center gap-2 font-medium">
                      {w.name}
                      {w.unseen > 0 && <Badge tone="accent">{w.unseen} new</Badge>}
                      {!w.active && <Badge>paused</Badge>}
                    </span>
                    <span className="block truncate text-xs text-muted">
                      {[w.keywords, ...w.cpc].filter(Boolean).join(" · ")}
                    </span>
                    <span className="block text-xs text-muted">
                      {w.last_checked_at ? `checked ${formatDateTime(w.last_checked_at)}` : "never checked"} · {w.hits} found
                    </span>
                    {w.last_error && <span className="block text-xs text-bad">{w.last_error}</span>}
                  </button>
                  <div className="mt-2 flex gap-2">
                    <Button variant="secondary" className="px-2 py-1 text-xs" disabled={busy !== null} onClick={() => check(w.id)}>
                      {busy === `check-${w.id}` ? "Checking…" : "Check now"}
                    </Button>
                    <Button variant="secondary" className="px-2 py-1 text-xs" disabled={busy !== null}
                      onClick={() => act("toggle", () => send(`/watches/${w.id}?active=${!w.active}`, { method: "PATCH" }))}>
                      {w.active ? "Pause" : "Resume"}
                    </Button>
                    <Button variant="danger" className="ml-auto px-2 py-1 text-xs" disabled={busy !== null}
                      onClick={() => act("delete", () => send(`/watches/${w.id}`, { method: "DELETE" }))}>
                      Delete
                    </Button>
                  </div>
                </div>
              </li>
            ))}
          </ul>

          <Panel
            title="Publications found"
            aside={
              active && (hits.data ?? []).some((h) => !h.seen) ? (
                <button type="button" className="text-xs text-accent hover:underline"
                  onClick={() => act("seen", () => send(`/watches/${active}/seen`, { method: "POST" }))}>
                  Mark all as seen
                </button>
              ) : null
            }
          >
            {hits.isLoading ? (
              <Spinner />
            ) : (hits.data ?? []).length === 0 ? (
              <p className="text-sm text-muted">Nothing found yet. Use “Check now”.</p>
            ) : (
              <ul className="-my-2 divide-y divide-line">
                {(hits.data ?? []).map((h) => (
                  <li key={h.id} className="py-2.5 text-sm">
                    <div className="flex flex-wrap items-baseline gap-2">
                      {!h.seen && <span className="h-2 w-2 rounded-full bg-accent" aria-label="new" />}
                      {h.url ? (
                        <a href={h.url} target="_blank" rel="noreferrer" className="font-mono text-xs font-semibold text-accent hover:underline">
                          {h.publication_number}
                        </a>
                      ) : (
                        <span className="font-mono text-xs font-semibold">{h.publication_number}</span>
                      )}
                      <span className="font-medium">{h.title}</span>
                      {h.source === "demo" && <Badge tone="warn">synthetic</Badge>}
                      {h.imported_patent_id && <Badge tone="ok">imported</Badge>}
                      <span className="ml-auto text-xs text-muted tabular-nums">
                        {h.publication_date ?? ""}
                        {h.similarity !== null && ` · similarity ${formatPercent(h.similarity)}`}
                      </span>
                    </div>
                    {h.applicants.length > 0 && <p className="text-xs text-muted">{h.applicants.join(", ")}</p>}
                    {h.abstract && <p className="mt-1 line-clamp-2 text-xs text-muted">{h.abstract}</p>}
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        </div>
      )}
    </div>
  );
}
