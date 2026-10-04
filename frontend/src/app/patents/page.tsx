"use client";

import { StartChatButton } from "@/components/chat/StartChatButton";
import { LibraryHeader } from "@/components/LibraryHeader";
import { useState } from "react";
import useSWR from "swr";

import { Badge, Button, EmptyState, ErrorNotice, Panel, Spinner } from "@/components/ui";
import { ApiError, api, fetcher } from "@/lib/api";
import { formatMs } from "@/lib/format";
import type { DocumentOut, PatentOut, PatentResultOut, PatentSearchResponse, SourceStatusOut } from "@/lib/types";

const inputClass = "rounded border border-line-strong bg-surface px-2.5 py-1.5 text-sm outline-none focus:border-accent";

function SourceBadge({ source }: { source: string }) {
  if (source === "demo") return <Badge tone="warn">Demo · synthetic</Badge>;
  return <Badge tone="accent">{source.toUpperCase()}</Badge>;
}

function ResultRow({
  result,
  onImported,
}: {
  result: PatentResultOut;
  onImported: () => void;
}) {
  const [state, setState] = useState<"idle" | "importing" | "error">("idle");
  const [error, setError] = useState<string>();
  const [expanded, setExpanded] = useState(false);
  const imported = Boolean(result.imported_id);

  async function importIt() {
    setState("importing");
    try {
      await api.importPatent(result.source, result.publication_number);
      setState("idle");
      onImported();
    } catch (e) {
      setState("error");
      setError(e instanceof ApiError ? e.message : "Import failed.");
    }
  }

  return (
    <li className="py-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-sm font-medium">{result.publication_number}</span>
            <SourceBadge source={result.source} />
            {result.publication_date && <span className="text-xs text-muted">published {result.publication_date}</span>}
            {result.similarity != null && (
              <span
                className="rounded-sm bg-accent-soft px-1.5 font-mono text-[11px] text-accent"
                title="Semantic similarity between this patent's title/abstract and your search (or reference invention). Not legal similarity."
              >
                relevance {result.similarity.toFixed(2)}
              </span>
            )}
            {result.full_text_likely ? (
              <Badge tone="ok">full text</Badge>
            ) : (
              <span className="text-[11px] text-muted" title="The patent office supplies only bibliographic data and the abstract for this publication">
                abstract only
              </span>
            )}
          </div>
          <p className="mt-1 font-medium">{result.title ?? "(no title)"}</p>
          <p className="mt-0.5 text-xs text-muted">
            {result.applicants.join("; ") || "Applicant unknown"}
            {result.filing_date && ` · filed ${result.filing_date}`}
          </p>
          {(result.also_published_as?.length ?? 0) > 0 && (
            <p className="mt-0.5 text-xs text-muted">
              Also published as <span className="font-mono">{result.also_published_as?.join(", ")}</span>
            </p>
          )}
          {result.cpc_codes.length > 0 && (
            <div className="mt-1.5 flex flex-wrap gap-1">
              {result.cpc_codes.slice(0, 6).map((c) => (
                <span key={c} className="rounded-sm bg-surface-2 px-1.5 font-mono text-[11px] text-muted">{c}</span>
              ))}
            </div>
          )}
          {result.abstract && (
            <p className={`mt-2 text-sm ${expanded ? "" : "line-clamp-3"}`}>
              {result.abstract}
            </p>
          )}
          {result.abstract && result.abstract.length > 280 && (
            <button type="button" onClick={() => setExpanded(!expanded)} className="mt-1 text-xs text-accent hover:underline">
              {expanded ? "Show less" : "Show full abstract"}
            </button>
          )}
          {state === "error" && <p className="mt-1 text-xs text-bad">{error}</p>}
        </div>
        <div className="flex shrink-0 flex-col items-end gap-2">
          {imported ? (
            <span className="flex items-center gap-2 text-sm text-ok">✓ In your library <StartChatButton patentId={result.imported_id ?? undefined} /></span>
          ) : (
            <Button variant="secondary" disabled={state === "importing"} onClick={importIt}>
              {state === "importing" ? "Importing…" : "Import as evidence"}
            </Button>
          )}
          {result.url && (
            <a href={result.url} target="_blank" rel="noopener noreferrer" className="text-xs text-accent hover:underline">
              View on Espacenet ↗
            </a>
          )}
        </div>
      </div>
    </li>
  );
}

function ImportedPatents() {
  const { data, error, mutate } = useSWR<PatentOut[]>("/patents", fetcher);
  if (error) return <ErrorNotice error={error} title="Cannot load imported patents" />;
  if (!data) return <p className="text-sm text-muted">Loading…</p>;
  if (data.length === 0) {
    return <EmptyState title="No patents imported yet">Search above and choose “Import as evidence”.</EmptyState>;
  }
  return (
    <ul className="divide-y divide-line">
      {data.map((p) => (
        <li key={p.id} className="flex flex-wrap items-center justify-between gap-3 py-2.5">
          <div className="min-w-0">
            <p className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-sm">{p.publication_number}</span>
              <SourceBadge source={p.source} />
            </p>
            <p className="truncate text-sm">{p.title}</p>
            <p className="text-xs text-muted">
              {p.chunk_count} passages · claims {p.has_claims ? "✓" : "not available"} · description{" "}
              {p.has_description ? "✓" : "not available"}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <StartChatButton patentId={p.id} />
            <Button
              variant="danger"
              className="px-2 py-1 text-xs"
              onClick={async () => {
                if (!window.confirm(`Remove ${p.publication_number} and its indexed passages?`)) return;
                await api.deletePatent(p.id);
                mutate();
              }}
            >
              Remove
            </Button>
          </div>
        </li>
      ))}
    </ul>
  );
}

export default function PatentSearchPage() {
  const sources = useSWR<SourceStatusOut[]>("/patents/sources", fetcher);
  const available = sources.data?.filter((s) => s.status === "available") ?? [];
  const [keywords, setKeywords] = useState("");
  const [cpc, setCpc] = useState("");
  const [applicant, setApplicant] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [dedup, setDedup] = useState(true);
  const [fullTextOnly, setFullTextOnly] = useState(false);
  const [rankAgainst, setRankAgainst] = useState("");
  const documents = useSWR<DocumentOut[]>("/documents", fetcher);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [response, setResponse] = useState<PatentSearchResponse | null>(null);
  const [lastBody, setLastBody] = useState<Parameters<typeof api.searchPatents>[0] | null>(null);
  const imported = useSWR<PatentOut[]>("/patents", fetcher);

  async function run(body = lastBody) {
    if (!body) return;
    setPending(true);
    setError(null);
    try {
      setResponse(await api.searchPatents(body));
      setLastBody(body);
    } catch (e) {
      setError(e);
    } finally {
      setPending(false);
    }
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    run({
      keywords,
      cpc: cpc.split(/[,;]/).map((c) => c.trim()).filter(Boolean),
      applicant: applicant || null,
      date_from: dateFrom || null,
      date_to: dateTo || null,
      limit: 25,
      sources: selected.length ? selected : null,
      dedup,
      full_text_only: fullTextOnly,
      rank_by_relevance: true,
      rank_against_document_id: rankAgainst.startsWith("d:") ? rankAgainst.slice(2) : null,
      rank_against_patent_id: rankAgainst.startsWith("p:") ? rankAgainst.slice(2) : null,
    });
  }

  return (
    <>
      <LibraryHeader />

      {sources.data && available.length === 0 && (
        <div className="mb-6 rounded border border-warn/40 bg-warn-soft px-4 py-3 text-sm">
          <p className="font-medium text-warn">No patent source is configured.</p>
          <p className="mt-1">
            Register for free at developers.epo.org and set <code className="font-mono">EPO_OPS_KEY</code> and{" "}
            <code className="font-mono">EPO_OPS_SECRET</code> in <code className="font-mono">.env</code>. To try this page
            without keys, set <code className="font-mono">PATENT_DEMO_SOURCE=true</code> (synthetic records).
          </p>
        </div>
      )}

      <div className="grid gap-6">
        <Panel>
          <form onSubmit={submit} className="grid gap-3 md:grid-cols-6">
            <label className="flex flex-col gap-1 md:col-span-6">
              <span className="text-xs text-muted">Keywords (title and abstract must contain all words)</span>
              <input value={keywords} onChange={(e) => setKeywords(e.target.value)} placeholder="e.g. battery thermal runaway sensor" className={inputClass} />
            </label>
            <label className="flex flex-col gap-1 md:col-span-2">
              <span className="text-xs text-muted">CPC codes (comma-separated)</span>
              <input value={cpc} onChange={(e) => setCpc(e.target.value)} placeholder="H01M10/48" className={`${inputClass} font-mono`} />
            </label>
            <label className="flex flex-col gap-1 md:col-span-2">
              <span className="text-xs text-muted">Applicant</span>
              <input value={applicant} onChange={(e) => setApplicant(e.target.value)} className={inputClass} />
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-xs text-muted">Published from</span>
              <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className={inputClass} />
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-xs text-muted">Published to</span>
              <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className={inputClass} />
            </label>
            <label className="flex flex-col gap-1 md:col-span-4">
              <span className="text-xs text-muted">Rank results by semantic similarity to (optional)</span>
              <select value={rankAgainst} onChange={(e) => setRankAgainst(e.target.value)} className={inputClass}>
                <option value="">Don&apos;t rank (source order)</option>
                {(documents.data ?? []).filter((d) => d.status === "ready").map((d) => (
                  <option key={d.id} value={`d:${d.id}`}>{d.title || d.filename}</option>
                ))}
                {(imported.data ?? []).map((p) => (
                  <option key={p.id} value={`p:${p.id}`}>{p.publication_number} — {p.title}</option>
                ))}
              </select>
            </label>
            <label className="flex items-end gap-2 pb-2 text-sm md:col-span-2">
              <input type="checkbox" checked={dedup} onChange={(e) => setDedup(e.target.checked)} />
              Merge patent families (A1/B1, EP/US/WO)
            </label>
            <label className="flex items-end gap-2 pb-2 text-sm md:col-span-2" title="EP and WO publications come with claims and description, so you can chat about them in detail">
              <input type="checkbox" checked={fullTextOnly} onChange={(e) => setFullTextOnly(e.target.checked)} />
              Only patents with full text (EP, WO)
            </label>
            <div className="flex flex-wrap items-center gap-3 md:col-span-6">
              <Button type="submit" disabled={pending || available.length === 0 || !(keywords.trim() || cpc.trim() || applicant.trim())}>
                Search
              </Button>
              {available.map((s) => (
                <label key={s.name} className="flex items-center gap-1.5 text-sm">
                  <input
                    type="checkbox"
                    checked={selected.length === 0 || selected.includes(s.name)}
                    onChange={(e) =>
                      setSelected((cur) => {
                        const base = cur.length ? cur : available.map((a) => a.name);
                        return e.target.checked ? [...new Set([...base, s.name])] : base.filter((n) => n !== s.name);
                      })
                    }
                  />
                  {s.label}
                </label>
              ))}
              {sources.data
                ?.filter((s) => s.status !== "available")
                .map((s) => (
                  <span key={s.name} className="text-xs text-muted" title={s.note}>
                    {s.label}: {s.status === "planned" ? "planned" : "not configured"}
                  </span>
                ))}
              {pending && <Spinner label="Searching…" />}
            </div>
          </form>
        </Panel>

        {error != null && <ErrorNotice error={error} title="Search failed" />}

        {response && (
          <Panel
            title={`Results (${response.results.length})`}
            aside={
              <span className="text-xs text-muted">
                {response.reference_label ? `Ranked by ${response.reference_label.startsWith("relevance") ? "" : "similarity to "}${response.reference_label}` : "Sorted as returned by each source"}
                {response.deduplicated ? ` · ${response.deduplicated} family duplicate(s) merged` : ""}
              </span>
            }
          >
            <ul className="mb-3 space-y-1 text-xs">
              {response.sources.map((s) => (
                <li key={s.source} className="flex flex-wrap items-center gap-x-3 gap-y-1">
                  <SourceBadge source={s.source} />
                  {s.error ? (
                    <span className="text-bad">{s.error}</span>
                  ) : (
                    <span className="text-muted">
                      {s.returned} of {s.total.toLocaleString()} hits · {s.cached ? "from cache" : formatMs(s.latency_ms)}
                    </span>
                  )}
                  {s.query_string && <code className="font-mono text-muted">{s.query_string}</code>}
                </li>
              ))}
            </ul>
            {response.results.length === 0 ? (
              <EmptyState title="No patents matched">Try fewer or broader keywords, or remove filters.</EmptyState>
            ) : (
              <ul className="divide-y divide-line border-t border-line">
                {response.results.map((r) => (
                  <ResultRow
                    key={`${r.source}-${r.publication_number}`}
                    result={r}
                    onImported={() => {
                      run();
                      imported.mutate();
                    }}
                  />
                ))}
              </ul>
            )}
          </Panel>
        )}

        <Panel title={`Imported patents${imported.data ? ` (${imported.data.length})` : ""}`}>
          <ImportedPatents />
        </Panel>
      </div>
    </>
  );
}
