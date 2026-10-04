"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import useSWR from "swr";

import { InventionResultView } from "@/components/invention/InventionResultView";
import { Badge, Button, ErrorNotice, Panel, Spinner } from "@/components/ui";
import { ApiError, fetcher, parseError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import type { InventionResult } from "@/lib/invention";
import type { DocumentOut, InventionAnalysisOut, InventionListItem, SourceStatusOut } from "@/lib/types";

const EXAMPLE =
  "A battery pack for an electric vehicle with a temperature sensor on every cell. A controller estimates each cell's core temperature from its surface temperature and charging current, and increases the speed of a coolant pump when any cell gets too hot. Coolant flows through channels between the cells.";

export function InventionWorkspace() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const runId = params.get("run");

  const documents = useSWR<DocumentOut[]>("/documents", fetcher);
  const sources = useSWR<SourceStatusOut[]>("/patents/sources", fetcher);
  const history = useSWR<InventionListItem[]>("/analysis/invention", fetcher);
  const current = useSWR<InventionAnalysisOut>(runId ? `/analysis/invention/${runId}` : null, fetcher);

  const [description, setDescription] = useState("");
  const [documentId, setDocumentId] = useState("");
  const [usePatentSearch, setUsePatentSearch] = useState(true);
  const [maxCandidates, setMaxCandidates] = useState(5);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!pending) return;
    const started = Date.now();
    const timer = setInterval(() => setElapsed(Math.floor((Date.now() - started) / 1000)), 500);
    return () => {
      clearInterval(timer);
      setElapsed(0);
    };
  }, [pending]);

  const liveSources = (sources.data ?? []).filter((s) => s.status === "available");
  const canSearchPatents = liveSources.length > 0;
  const ready = (documents.data ?? []).filter((d) => d.status === "ready");
  const canRun = !pending && (description.trim().split(/\s+/).length >= 8 || documentId !== "");

  async function run() {
    setPending(true);
    setError(null);
    try {
      const response = await fetch("/api/analysis/invention", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          description: description.trim() || null,
          document_id: documentId || null,
          use_patent_search: usePatentSearch && canSearchPatents,
          max_candidates: maxCandidates,
        }),
      });
      if (!response.ok) throw await parseError(response);
      const body: InventionAnalysisOut = await response.json();
      await history.mutate();
      router.replace(`${pathname}?run=${body.run_id}`, { scroll: false });
    } catch (e) {
      setError(e instanceof ApiError ? e : new Error("The analysis failed."));
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_18rem]">
        <Panel title="Your invention">
          <label htmlFor="invention" className="sr-only">
            Invention description
          </label>
          <textarea
            id="invention"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={6}
            maxLength={8000}
            placeholder="Describe what it is, its parts, and how they work together. Pasting a claim (… comprising: a; b; and c) gives the most precise features."
            className="w-full rounded border border-line-strong bg-surface px-3 py-2 text-sm"
          />
          <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
            <button type="button" className="text-xs text-accent hover:underline" onClick={() => setDescription(EXAMPLE)}>
              Use an example
            </button>
            <label className="flex items-center gap-1.5">
              <span className="text-muted">or a document:</span>
              <select
                value={documentId}
                onChange={(e) => setDocumentId(e.target.value)}
                className="max-w-56 rounded border border-line-strong bg-surface px-2 py-1 text-xs"
              >
                <option value="">— none —</option>
                {ready.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.title || d.filename}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex items-center gap-1.5" title={canSearchPatents ? "" : "No patent database configured (add EPO keys in .env)"}>
              <input
                type="checkbox"
                checked={usePatentSearch && canSearchPatents}
                disabled={!canSearchPatents}
                onChange={(e) => setUsePatentSearch(e.target.checked)}
              />
              <span className={canSearchPatents ? "" : "text-muted"}>
                Search patent databases{canSearchPatents ? ` (${liveSources.map((s) => s.name).join(", ")})` : " (not configured)"}
              </span>
            </label>
            <label className="flex items-center gap-1.5">
              <span className="text-muted">documents:</span>
              <select
                value={maxCandidates}
                onChange={(e) => setMaxCandidates(Number(e.target.value))}
                className="rounded border border-line-strong bg-surface px-2 py-1 text-xs"
              >
                {[3, 5, 8].map((n) => (
                  <option key={n}>{n}</option>
                ))}
              </select>
            </label>
            <Button className="ml-auto" disabled={!canRun} onClick={run}>
              {pending ? `Analysing… ${elapsed} s` : "Analyse"}
            </Button>
          </div>
          {documentId && description.trim() && (
            <p className="mt-2 text-xs text-muted">
              The description is analysed; the selected document is excluded from the results (as your own draft).
            </p>
          )}
          {pending && (
            <p className="mt-2 text-xs text-muted">
              Extracting features, searching, then checking every feature against every document. This takes 1–3 minutes
              with local models.
            </p>
          )}
        </Panel>

        <Panel title="Recent analyses">
          {history.isLoading ? (
            <Spinner />
          ) : (history.data ?? []).length === 0 ? (
            <p className="text-sm text-muted">None yet.</p>
          ) : (
            <ul className="-my-1 space-y-1">
              {(history.data ?? []).slice(0, 8).map((h) => (
                <li key={h.run_id}>
                  <button
                    type="button"
                    onClick={() => router.replace(`${pathname}?run=${h.run_id}`, { scroll: false })}
                    className={`w-full rounded px-2 py-1.5 text-left text-xs hover:bg-surface-2 ${h.run_id === runId ? "bg-accent-soft" : ""}`}
                  >
                    <span className="line-clamp-2">{h.description}</span>
                    <span className="mt-0.5 flex items-center gap-1.5 text-muted">
                      {formatDateTime(h.created_at)}
                      {h.status !== "succeeded" && <Badge tone="bad">{h.status}</Badge>}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>

      {error ? <ErrorNotice error={error} title="Analysis failed" /> : null}
      {current.error && <ErrorNotice error={current.error} title="Could not load this analysis" />}
      {current.isLoading && <Spinner label="Loading analysis…" />}
      {current.data?.result && current.data.status === "succeeded" && (
        <InventionResultView runId={current.data.run_id} result={current.data.result as unknown as InventionResult} />
      )}
    </div>
  );
}
