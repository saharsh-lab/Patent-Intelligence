"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import useSWR from "swr";

import { AnswerView, RunSummary } from "@/components/ask/AnswerView";
import { EvidenceList } from "@/components/ask/EvidenceList";
import { VerificationPanel } from "@/components/ask/VerificationPanel";
import { WorkflowPanel } from "@/components/ask/WorkflowPanel";
import { Button, ErrorNotice, Panel, Spinner, StatusBadge } from "@/components/ui";
import { ComparisonTable, type Comparison } from "@/components/compare/ComparisonTable";
import { api, fetcher } from "@/lib/api";
import { scrollToEvidence } from "@/lib/evidence";
import type { Verification } from "@/lib/verification";
import { formatDateTime } from "@/lib/format";
import type { AskResponse, DocumentOut, PatentOut, RetrievalMode, RunListItem, SystemInfo } from "@/lib/types";

const EXAMPLES = [
  "What does claim 1 cover?",
  "How does the invention solve the problem described in the background?",
  "What components are described, and how do they interact?",
];

function useElapsed(running: boolean) {
  const [seconds, setSeconds] = useState(0);
  useEffect(() => {
    if (!running) return;
    const started = Date.now();
    const timer = setInterval(() => setSeconds(Math.floor((Date.now() - started) / 1000)), 500);
    return () => {
      clearInterval(timer);
      setSeconds(0);
    };
  }, [running]);
  return seconds;
}

export function AskWorkspace() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const runId = searchParams.get("run");
  const preselectedDoc = searchParams.get("doc");
  const preselectedPatent = searchParams.get("patent");

  const documents = useSWR<DocumentOut[]>("/documents", fetcher);
  const patents = useSWR<PatentOut[]>("/patents", fetcher);
  const info = useSWR<SystemInfo>("/system/info", fetcher);
  const history = useSWR<RunListItem[]>("/runs?limit=30", fetcher);
  const loadedRun = useSWR<AskResponse>(runId ? `/runs/${runId}` : null, fetcher);

  const [question, setQuestion] = useState("");
  const [scope, setScope] = useState<string[]>(preselectedDoc ? [preselectedDoc] : []);
  const [patentScope, setPatentScope] = useState<string[]>(preselectedPatent ? [preselectedPatent] : []);
  const [showOptions, setShowOptions] = useState(false);
  const [topK, setTopK] = useState<string>("");
  const [mode, setMode] = useState<"" | RetrievalMode>("");
  const [rerank, setRerank] = useState<"" | "on" | "off">("");
  const [pipeline, setPipeline] = useState<"agentic" | "baseline">("agentic");
  const [pending, setPending] = useState(false);
  const [askError, setAskError] = useState<unknown>(null);
  const elapsed = useElapsed(pending);
  const textarea = useRef<HTMLTextAreaElement>(null);

  const readyDocs = documents.data?.filter((d) => d.status === "ready") ?? [];
  const run = loadedRun.data;

  async function submit() {
    const text = question.trim();
    if (text.length < 3 || pending) return;
    setPending(true);
    setAskError(null);
    try {
      const result = await api.ask({
        question: text,
        document_ids: scope.length ? scope : null,
        patent_ids: patentScope.length ? patentScope : null,
        top_k: topK ? Number(topK) : null,
        retrieval_mode: mode || null,
        rerank: rerank === "" ? null : rerank === "on",
        pipeline,
      });
      await loadedRun.mutate(result, { revalidate: false });
      router.replace(`${pathname}?run=${result.run_id}`, { scroll: false });
      history.mutate();
      setQuestion("");
    } catch (error) {
      setAskError(error);
    } finally {
      setPending(false);
    }
  }

  const showEvidence = scrollToEvidence;

  const toggle = (id: string) => (current: string[]) =>
    current.includes(id) ? current.filter((x) => x !== id) : [...current, id];
  const scoped = scope.length + patentScope.length;
  const patentList = patents.data ?? [];

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_260px]">
      <div className="min-w-0 space-y-6">
        {/* ---------------- question form ---------------- */}
        <Panel>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              submit();
            }}
          >
            <label htmlFor="question" className="text-sm font-medium">
              Question
            </label>
            <textarea
              id="question"
              ref={textarea}
              rows={3}
              maxLength={2000}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) submit();
              }}
              placeholder="e.g. How does the claimed system estimate the core temperature of a battery cell?"
              className="mt-1.5 w-full resize-y rounded border border-line-strong bg-surface px-3 py-2 text-sm outline-none focus:border-accent"
            />
            {readyDocs.length === 0 && patentList.length === 0 && documents.data && patents.data && (
              <p className="mt-2 text-sm text-warn">
                Nothing is indexed yet. Upload a document or import a patent from Patent Search first.
              </p>
            )}

            <fieldset className="mt-3">
              <legend className="text-xs font-medium text-muted">
                Search in {scoped ? `${scoped} selected source(s)` : "all documents and imported patents"}
              </legend>
              <div className="mt-1.5 flex flex-wrap gap-1.5">
                {readyDocs.map((doc) => (
                  <label
                    key={doc.id}
                    className={`cursor-pointer rounded border px-2 py-1 text-xs ${
                      scope.includes(doc.id) ? "border-accent bg-accent-soft text-accent" : "border-line hover:bg-surface-2"
                    }`}
                  >
                    <input type="checkbox" className="sr-only" checked={scope.includes(doc.id)} onChange={() => setScope(toggle(doc.id))} />
                    {doc.title || doc.filename}
                  </label>
                ))}
                {patentList.map((p) => (
                  <label
                    key={p.id}
                    title={p.title ?? undefined}
                    className={`cursor-pointer rounded border px-2 py-1 text-xs ${
                      patentScope.includes(p.id) ? "border-accent bg-accent-soft text-accent" : "border-line hover:bg-surface-2"
                    }`}
                  >
                    <input type="checkbox" className="sr-only" checked={patentScope.includes(p.id)} onChange={() => setPatentScope(toggle(p.id))} />
                    <span className="font-mono">{p.publication_number}</span>
                    {p.source === "demo" && <span className="ml-1 text-warn">(demo)</span>}
                  </label>
                ))}
              </div>
            </fieldset>

            {showOptions && (
              <div className="mt-3 grid gap-3 rounded border border-line bg-surface-2 p-3 text-sm sm:grid-cols-4">
                <label className="flex flex-col gap-1">
                  <span className="text-xs text-muted">Pipeline</span>
                  <select value={pipeline} onChange={(e) => setPipeline(e.target.value as "agentic" | "baseline")} className="rounded border border-line-strong bg-surface px-2 py-1">
                    <option value="agentic">Agent (chooses tools)</option>
                    <option value="baseline">Baseline RAG (fixed)</option>
                  </select>
                </label>
                <label className="flex flex-col gap-1">
                  <span className="text-xs text-muted">Passages to use (top-k)</span>
                  <input
                    type="number" min={1} max={20} value={topK} onChange={(e) => setTopK(e.target.value)}
                    placeholder={`default ${info.data?.retrieval.top_k ?? ""}`}
                    className="rounded border border-line-strong bg-surface px-2 py-1"
                  />
                </label>
                <label className="flex flex-col gap-1">
                  <span className="text-xs text-muted">Retrieval method</span>
                  <select value={mode} onChange={(e) => setMode(e.target.value as "" | RetrievalMode)} className="rounded border border-line-strong bg-surface px-2 py-1">
                    <option value="">Default ({info.data?.retrieval.mode ?? "hybrid"})</option>
                    <option value="hybrid">Hybrid (vector + keyword)</option>
                    <option value="vector">Vector only</option>
                    <option value="keyword">Keyword only</option>
                  </select>
                </label>
                <label className="flex flex-col gap-1">
                  <span className="text-xs text-muted">Reranking</span>
                  <select value={rerank} onChange={(e) => setRerank(e.target.value as "" | "on" | "off")} className="rounded border border-line-strong bg-surface px-2 py-1">
                    <option value="">Default ({info.data?.retrieval.reranker_enabled ? "on" : "off"})</option>
                    <option value="on">On (cross-encoder)</option>
                    <option value="off">Off</option>
                  </select>
                </label>
              </div>
            )}

            <div className="mt-3 flex flex-wrap items-center gap-3">
              <Button type="submit" disabled={pending || question.trim().length < 3}>
                Ask
              </Button>
              <button type="button" className="text-sm text-accent hover:underline" onClick={() => setShowOptions(!showOptions)}>
                {showOptions ? "Hide options" : "Retrieval options"}
              </button>
              <span className="text-xs text-muted">⌘/Ctrl + Enter to submit</span>
              {pending && (
                <Spinner
                  label={`${pipeline === "agentic" ? "Agent is planning, gathering evidence and answering" : "Retrieving evidence and answering"}… ${elapsed}s`}
                />
              )}
            </div>
            {!run && !pending && (
              <div className="mt-3 flex flex-wrap gap-2">
                {EXAMPLES.map((example) => (
                  <button
                    type="button" key={example}
                    onClick={() => { setQuestion(example); textarea.current?.focus(); }}
                    className="rounded border border-line px-2 py-1 text-xs text-muted hover:bg-surface-2"
                  >
                    {example}
                  </button>
                ))}
              </div>
            )}
          </form>
        </Panel>

        {askError != null && <ErrorNotice error={askError} title="The question could not be answered" />}
        {loadedRun.error && <ErrorNotice error={loadedRun.error} title="Cannot load this run" />}

        {/* ---------------- result ---------------- */}
        {run && (
          <>
            {run.comparison && (
              <ComparisonTable
                comparison={run.comparison as unknown as Comparison}
                onCite={showEvidence}
                verification={run.verification as unknown as Verification | null}
              />
            )}
            <AnswerView run={run} onCite={showEvidence} />
            <VerificationPanel run={run} onCite={showEvidence} />
            <WorkflowPanel run={run} />
            <RunSummary run={run} />
            <Panel title={`Evidence (${run.evidence.length} passages)`} aside={<span className="text-xs text-muted">Click a citation chip to jump to its passage</span>}>
              <EvidenceList evidence={run.evidence} />
            </Panel>
          </>
        )}
      </div>

      {/* ---------------- history ---------------- */}
      <aside className="min-w-0">
        <h2 className="mb-2 text-sm font-semibold">History</h2>
        {history.data?.length === 0 && <p className="text-sm text-muted">No questions yet.</p>}
        <ul className="space-y-1">
          {history.data?.map((item) => (
            <li key={item.run_id}>
              <button
                type="button"
                onClick={() => router.replace(`${pathname}?run=${item.run_id}`, { scroll: false })}
                className={`w-full rounded px-2 py-1.5 text-left text-sm hover:bg-surface-2 ${item.run_id === runId ? "bg-accent-soft" : ""}`}
              >
                <span className="line-clamp-2">{item.question}</span>
                <span className="mt-0.5 flex items-center gap-2 text-[11px] text-muted">
                  <StatusBadge status={item.status} />
                  {formatDateTime(item.created_at)}
                </span>
              </button>
            </li>
          ))}
        </ul>
      </aside>
    </div>
  );
}
