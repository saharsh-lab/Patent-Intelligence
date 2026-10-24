"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import useSWR, { useSWRConfig } from "swr";

import { EvidenceList } from "@/components/ask/EvidenceList";
import { IconTile } from "@/components/chat/ChatSidebar";
import { firstFlagged, type OnFix, useDeveloped, XRayBlocks, XRayPanel, type XRaySelection } from "@/components/chat/XRay";
import { icons } from "@/components/icons";
import { EmptyState, ErrorNotice, Panel, Spinner } from "@/components/ui";
import { api, fetcher } from "@/lib/api";
import { sentenceCount, shortTitle, totals } from "@/lib/checker";
import { scrollToEvidence } from "@/lib/evidence";
import { formatDateTime, formatPercent } from "@/lib/format";
import type { AskResponse, CheckHistoryItem, DocumentOut, PatentOut } from "@/lib/types";
import type { Verification } from "@/lib/verification";
import { answerClaims } from "@/lib/xray";

type Tab = "check" | "history";
const HISTORY = "/checker/history";

/** The Checker: paste any text and check every sentence against your sources, or look
 *  back at what the checker found in your answers. */
export function CheckerWorkspace() {
  const [tab, setTab] = useState<Tab>("check");
  const [run, setRun] = useState<AskResponse | null>(null);
  const [opening, setOpening] = useState<string | null>(null);

  async function open(id: string) {
    setOpening(id);
    try {
      setRun(await api.getRun(id));
      setTab("check");
    } finally {
      setOpening(null);
    }
  }

  // A past check opened from a link: /checker?run=<id>
  useEffect(() => {
    const id = new URLSearchParams(window.location.search).get("run");
    if (!id) return;
    api.getRun(id).then(setRun, () => undefined);
  }, []);

  return (
    <div className="space-y-6">
      <nav aria-label="Checker" className="inline-flex gap-1 rounded-full border border-line bg-surface/60 p-1">
        {(
          [
            ["check", "Check a text"],
            ["history", "Checker record"],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            type="button"
            onClick={() => setTab(key)}
            aria-current={tab === key ? "page" : undefined}
            className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${tab === key ? "bg-brand" : "text-muted hover:text-text"}`}
          >
            {label}
          </button>
        ))}
      </nav>

      {tab === "check" ? (
        run ? (
          <CheckResult key={run.run_id} run={run} onChange={setRun} onReset={() => setRun(null)} />
        ) : (
          <CheckForm onChecked={setRun} />
        )
      ) : (
        <History onOpen={open} opening={opening} />
      )}
    </div>
  );
}

// ------------------------------------------------------------------ check a text

function CheckForm({ onChecked }: { onChecked: (run: AskResponse) => void }) {
  const { mutate } = useSWRConfig();
  const documents = useSWR<DocumentOut[]>("/documents", fetcher);
  const patents = useSWR<PatentOut[]>("/patents", fetcher);
  const [text, setText] = useState("");
  const [chosen, setChosen] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  const ready = (documents.data ?? []).filter((d) => d.status === "ready");
  const sources = [
    ...ready.map((d) => ({ id: d.id, kind: "document" as const, name: d.title || d.filename })),
    ...(patents.data ?? []).map((p) => ({ id: p.id, kind: "patent" as const, name: `${p.publication_number}${p.title ? ` · ${p.title}` : ""}` })),
  ];
  const count = sentenceCount(text);

  function toggle(id: string) {
    setChosen((now) => {
      const next = new Set(now);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      const picked = sources.filter((s) => chosen.has(s.id));
      const documentIds = picked.filter((s) => s.kind === "document").map((s) => s.id);
      const patentIds = picked.filter((s) => s.kind === "patent").map((s) => s.id);
      const run = await api.checkText({
        text,
        document_ids: documentIds.length ? documentIds : null,
        patent_ids: patentIds.length ? patentIds : null,
      });
      mutate(HISTORY);
      onChecked(run);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  const chip = (active: boolean) =>
    `inline-flex max-w-full items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs transition-colors ${
      active ? "border-accent bg-accent-soft font-medium text-accent" : "border-line bg-surface hover:border-line-strong"
    }`;

  return (
    <Panel title="Text to check" aside={<span className="text-xs text-muted">{text.length.toLocaleString()} / 8,000</span>}>
      <div className="space-y-5">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          maxLength={8000}
          rows={8}
          placeholder="Paste an answer from any AI assistant, a draft, or notes. Every sentence is checked against your documents and patents."
          className="w-full resize-y rounded-2xl border border-line-strong bg-surface px-4 py-3 text-[0.95rem] leading-relaxed"
          aria-label="Text to check"
        />

        <div>
          <p className="text-sm font-medium">Check against</p>
          <div className="mt-2 flex max-h-40 flex-wrap gap-2 overflow-y-auto">
            <button type="button" onClick={() => setChosen(new Set())} className={chip(chosen.size === 0)}>
              <icons.layers width={13} height={13} /> All my sources
            </button>
            {sources.map((s) => (
              <button key={s.id} type="button" onClick={() => toggle(s.id)} className={chip(chosen.has(s.id))} title={s.name} aria-pressed={chosen.has(s.id)}>
                {s.kind === "patent" ? <icons.search width={13} height={13} className="shrink-0" /> : <icons.file width={13} height={13} className="shrink-0" />}
                <span className="truncate">{s.name}</span>
              </button>
            ))}
          </div>
          {documents.data && sources.length === 0 && (
            <p className="mt-2 text-xs text-muted">
              Your library is empty. <Link href="/documents" className="text-accent hover:underline">Upload a patent or a draft</Link> to check text against it.
            </p>
          )}
        </div>

        {error ? <ErrorNotice error={error} title="Could not check this text" /> : null}

        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={submit}
            disabled={busy || text.trim().length < 10}
            className="press inline-flex items-center gap-2 rounded-full bg-brand px-5 py-2.5 text-sm font-semibold transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            <icons.shield width={16} height={16} />
            Check every sentence
          </button>
          {busy ? (
            <Spinner label={`Checking ${count || "each"} sentence${count === 1 ? "" : "s"} against your sources…`} />
          ) : (
            <span className="text-xs text-muted">Red: contradicts its source · violet: no source says it · amber: partly backed</span>
          )}
        </div>
      </div>
    </Panel>
  );
}

function CheckResult({ run, onChange, onReset }: { run: AskResponse; onChange: (run: AskResponse) => void; onReset: () => void }) {
  const { mutate } = useSWRConfig();
  const [selected, setSelected] = useState<XRaySelection>(() => firstFlagged(run));
  const [showSources, setShowSources] = useState(false);
  const [copied, setCopied] = useState(false);
  const developed = useDeveloped(true);
  const claims = answerClaims(run.verification as unknown as Verification | null);
  const supported = claims.filter((c) => c.verdict === "supported" && !c.misattributed).length;

  const fix: OnFix = async (action, claim) => {
    const updated = await api.fixSentence(run.run_id, action, claim?.index);
    if (action !== "rewrite") setSelected(null);
    onChange(updated);
    mutate(HISTORY);
  };

  function cite(label: string) {
    setShowSources(true);
    requestAnimationFrame(() => requestAnimationFrame(() => scrollToEvidence(label, "ck-")));
  }

  if (run.status !== "succeeded") {
    return (
      <Panel title="Nothing was checked">
        <p className="text-sm">{run.insufficient_reason ?? run.error_message ?? "This text could not be checked."}</p>
        <button type="button" onClick={onReset} className="mt-4 text-sm text-accent hover:underline">
          ← Check another text
        </button>
      </Panel>
    );
  }

  return (
    <div className="space-y-5">
      <Panel
        title="Every sentence, checked"
        aside={
          <span className="hidden text-xs whitespace-nowrap text-muted sm:inline">
            {formatDateTime(run.created_at)}
            {run.metrics.latency_ms ? ` · ${(run.metrics.latency_ms / 1000).toFixed(1)} s` : ""}
          </span>
        }
      >
        <div className="flex flex-wrap items-end gap-x-6 gap-y-2">
          <p>
            <span className="text-4xl font-bold tracking-tight">{formatPercent(run.grounding_score)}</span>
            <span className="ml-2 text-sm text-muted">grounded</span>
          </p>
          <p className="pb-1 text-sm text-muted">
            {supported} of {claims.length} sentence{claims.length === 1 ? "" : "s"} backed by your sources
          </p>
        </div>

        <div className={`relative mt-5 rounded-2xl border border-line bg-surface/60 px-5 py-4 text-[0.98rem] leading-7 xr-on ${developed ? "xr-developed" : ""}`}>
          <span aria-hidden className="xr-scan" />
          <XRayBlocks text={run.answer ?? ""} claims={claims} selected={selected} onSelect={setSelected} />
        </div>

        <div className="mt-5">
          <XRayPanel run={run} selected={selected} onSelect={setSelected} onCite={cite} onFix={fix} />
        </div>

        <div className="mt-5 flex flex-wrap items-center gap-2 border-t border-line pt-4">
          <button
            type="button"
            onClick={async () => {
              try {
                await navigator.clipboard.writeText(run.answer ?? "");
                setCopied(true);
                setTimeout(() => setCopied(false), 1500);
              } catch {
                /* clipboard blocked */
              }
            }}
            className="press inline-flex items-center gap-1.5 rounded-full border border-line-strong px-4 py-1.5 text-sm font-medium hover:bg-surface-2"
          >
            {copied ? <icons.check width={14} height={14} /> : <icons.copy width={14} height={14} />}
            {copied ? "Copied" : (run.fixes?.length ?? 0) > 0 ? "Copy the corrected text" : "Copy the text"}
          </button>
          <button type="button" onClick={() => setShowSources((v) => !v)} aria-expanded={showSources} className="press inline-flex items-center gap-1.5 rounded-full border border-line-strong px-4 py-1.5 text-sm font-medium hover:bg-surface-2">
            <icons.file width={14} height={14} /> Passages used ({run.evidence.length})
          </button>
          <button type="button" onClick={onReset} className="press ml-auto inline-flex items-center gap-1.5 rounded-full bg-brand px-4 py-1.5 text-sm font-semibold hover:opacity-90">
            <icons.plus width={14} height={14} /> Check another text
          </button>
        </div>
      </Panel>

      {showSources && (
        <div className="pi-in">
          <EvidenceList evidence={run.evidence} idPrefix="ck-" />
        </div>
      )}
    </div>
  );
}

// ------------------------------------------------------------------ the record

const SEGMENTS = [
  ["supported", "bg-ok"],
  ["partly", "bg-warn"],
  ["contradicts", "bg-bad"],
  ["not_found", "bg-miss"],
] as const;

function History({ onOpen, opening }: { onOpen: (id: string) => void; opening: string | null }) {
  const { data, error, isLoading } = useSWR<CheckHistoryItem[]>(HISTORY, fetcher);
  if (isLoading) return <Spinner label="Loading the checker's record…" />;
  if (error) return <ErrorNotice error={error} title="Could not load the record" />;
  if (!data || data.length === 0) {
    return (
      <EmptyState title="Nothing checked yet">
        Ask a question in <Link href="/chat" className="text-accent hover:underline">Chat</Link> or check a text: every checked answer appears here.
      </EmptyState>
    );
  }
  const t = totals(data);
  const stats: [string, string, string][] = [
    ["Checked", `${t.items}`, `${t.sentences} sentences in answers and texts`],
    ["Flagged", `${t.flagged}`, `${t.contradicted} contradicted their source`],
    ["Caught before you saw them", `${t.rewritten}`, `answer${t.rewritten === 1 ? " was" : "s were"} rewritten by the checker`],
    ["Checker tests", t.planted.total ? `${t.planted.caught}/${t.planted.total}` : "—", t.planted.total ? "planted false facts caught" : "plant a false fact from any answer's X-ray"],
  ];
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {stats.map(([label, value, note]) => (
          <div key={label} className="pi-in glass rounded-3xl px-5 py-4">
            <p className="text-xs font-medium text-muted">{label}</p>
            <p className="mt-1 text-3xl font-bold tracking-tight">{value}</p>
            <p className="mt-1 text-xs text-muted">{note}</p>
          </div>
        ))}
      </div>

      <Panel title="Recent" aside={<span className="text-xs text-muted">Last {data.length}</span>}>
        <ul className="-my-2 divide-y divide-line">
          {data.map((item) => (
            <li key={item.run_id}>
              <HistoryRow item={item} onOpen={onOpen} opening={opening === item.run_id} />
            </li>
          ))}
        </ul>
      </Panel>
    </div>
  );
}

function HistoryRow({ item, onOpen, opening }: { item: CheckHistoryItem; onOpen: (id: string) => void; opening: boolean }) {
  const total = item.counts.supported + item.counts.partly + item.counts.contradicts + item.counts.not_found;
  const body = (
    <>
      <IconTile icon={item.kind === "check" ? icons.shield : icons.chat} tone={item.kind === "check" ? "violet" : "blue"} size="sm" />
      <span className="min-w-0 flex-1">
        <span className="line-clamp-2 text-sm font-medium">{shortTitle(item.title, 140)}</span>
        <span className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted">
          <span>{item.kind === "check" ? "Text check" : "Chat answer"}</span>
          <span aria-hidden>·</span>
          <span>{formatDateTime(item.created_at)}</span>
          {item.rewritten && <Tag tone="ok">rewritten by the checker ({item.draft_flagged} flagged)</Tag>}
          {item.planted_caught !== null && item.planted_caught !== undefined && (
            <Tag tone={item.planted_caught ? "ok" : "bad"}>checker test: {item.planted_caught ? "caught" : "missed"}</Tag>
          )}
          {item.fixes > 0 && <Tag tone="neutral">edited by you</Tag>}
          {(item.premise_terms ?? []).length > 0 && <Tag tone="miss">assumed “{item.premise_terms![0]}”</Tag>}
        </span>
      </span>
      <span className="flex w-24 shrink-0 flex-col items-end gap-1.5 sm:w-32">
        <span className="text-sm font-semibold">{opening ? "Opening…" : formatPercent(item.grounding_score)}</span>
        <span className="flex h-1.5 w-full overflow-hidden rounded-full bg-surface-2" aria-label={`${item.counts.supported} of ${total} supported`}>
          {SEGMENTS.map(([key, color]) => (item.counts[key] ? <span key={key} className={color} style={{ width: `${(item.counts[key] / total) * 100}%` }} /> : null))}
        </span>
        <span className="text-[11px] text-muted">
          {item.counts.supported}/{total} backed
        </span>
      </span>
    </>
  );
  const style = "flex w-full items-center gap-3 rounded-2xl px-2 py-3 text-left transition-colors hover:bg-surface-2";
  if (item.kind === "answer" && item.conversation_id) {
    return (
      <Link href={`/chat/${item.conversation_id}`} className={style}>
        {body}
      </Link>
    );
  }
  return (
    <button type="button" onClick={() => onOpen(item.run_id)} className={style}>
      {body}
    </button>
  );
}

const TAG = { ok: "bg-ok-soft text-ok", bad: "bg-bad-soft text-bad", miss: "bg-miss-soft text-miss", neutral: "bg-surface-2 text-muted" } as const;

function Tag({ tone, children }: { tone: keyof typeof TAG; children: React.ReactNode }) {
  return <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${TAG[tone]}`}>{children}</span>;
}
