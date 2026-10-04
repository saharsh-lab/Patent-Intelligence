"use client";

import { LibraryHeader } from "@/components/LibraryHeader";
import { useState } from "react";
import useSWR from "swr";

import { RunSummary } from "@/components/ask/AnswerView";
import { EvidenceList } from "@/components/ask/EvidenceList";
import { VerificationPanel } from "@/components/ask/VerificationPanel";
import { ComparisonTable, type Comparison } from "@/components/compare/ComparisonTable";
import { Button, ErrorNotice, Panel, Spinner } from "@/components/ui";
import { ApiError, fetcher, parseError } from "@/lib/api";
import { scrollToEvidence } from "@/lib/evidence";
import type { AskResponse, DocumentOut, PatentOut } from "@/lib/types";
import type { Verification } from "@/lib/verification";

type Choice = { key: string; label: string; ref: Record<string, string> };

export default function ComparePage() {
  const documents = useSWR<DocumentOut[]>("/documents", fetcher);
  const patents = useSWR<PatentOut[]>("/patents", fetcher);
  const [selected, setSelected] = useState<Choice[]>([]);
  const [number, setNumber] = useState("");
  const [question, setQuestion] = useState("");
  const [mode, setMode] = useState<"auto" | "llm" | "extractive">("auto");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [result, setResult] = useState<AskResponse | null>(null);

  const choices: Choice[] = [
    ...(documents.data ?? []).filter((d) => d.status === "ready").map((d) => ({
      key: `d:${d.id}`, label: d.title || d.filename, ref: { document_id: d.id } })),
    ...(patents.data ?? []).map((p) => ({
      key: `p:${p.id}`, label: `${p.publication_number}${p.source === "demo" ? " (demo)" : ""}`, ref: { patent_id: p.id } })),
  ];
  const isSelected = (key: string) => selected.some((s) => s.key === key);
  const toggle = (choice: Choice) =>
    setSelected((cur) => (isSelected(choice.key) ? cur.filter((s) => s.key !== choice.key) : cur.length < 4 ? [...cur, choice] : cur));

  function addNumber() {
    const value = number.trim().toUpperCase();
    if (!value || selected.length >= 4) return;
    setSelected((cur) => [...cur, { key: `n:${value}`, label: `${value} (will be fetched)`, ref: { publication_number: value } }]);
    setNumber("");
  }

  async function run() {
    setPending(true);
    setError(null);
    try {
      const response = await fetch("/api/compare", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sources: selected.map((s) => s.ref), question: question || null, mode }),
      });
      if (!response.ok) throw await parseError(response);
      setResult(await response.json());
      patents.mutate();
    } catch (e) {
      setError(e instanceof ApiError ? e : new Error("Comparison failed."));
    } finally {
      setPending(false);
    }
  }

  const comparison = result?.comparison as unknown as Comparison | undefined;

  return (
    <>
      <LibraryHeader />
      <div className="grid gap-6">
        <Panel title="Sources to compare">
          <p className="mb-2 text-xs text-muted">Select 2–4 ({selected.length} selected, in this order: S1, S2, …)</p>
          <div className="flex flex-wrap gap-1.5">
            {choices.map((c) => (
              <button
                key={c.key}
                type="button"
                onClick={() => toggle(c)}
                className={`rounded border px-2 py-1 text-xs ${isSelected(c.key) ? "border-accent bg-accent-soft text-accent" : "border-line hover:bg-surface-2"}`}
              >
                {isSelected(c.key) && <span className="mr-1 font-mono">S{selected.findIndex((s) => s.key === c.key) + 1}</span>}
                {c.label}
              </button>
            ))}
            {selected.filter((s) => s.key.startsWith("n:")).map((s) => (
              <button key={s.key} type="button" onClick={() => toggle(s)} className="rounded border border-accent bg-accent-soft px-2 py-1 text-xs text-accent">
                <span className="mr-1 font-mono">S{selected.findIndex((x) => x.key === s.key) + 1}</span>{s.label} ×
              </button>
            ))}
          </div>
          <div className="mt-3 grid gap-3 md:grid-cols-[1fr_1fr_auto]">
            <label className="flex flex-col gap-1 text-sm">
              <span className="text-xs text-muted">Add by publication number (fetched from a patent source)</span>
              <span className="flex gap-2">
                <input value={number} onChange={(e) => setNumber(e.target.value)} onKeyDown={(e) => e.key === "Enter" && addNumber()}
                  placeholder="EP1234567A1" className="w-full rounded border border-line-strong bg-surface px-2 py-1 font-mono text-sm" />
                <Button type="button" variant="secondary" onClick={addNumber} disabled={!number.trim() || selected.length >= 4}>Add</Button>
              </span>
            </label>
            <label className="flex flex-col gap-1 text-sm">
              <span className="text-xs text-muted">Focus (optional)</span>
              <input value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="e.g. how each one controls coolant flow"
                className="rounded border border-line-strong bg-surface px-2 py-1" />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              <span className="text-xs text-muted">Method</span>
              <select value={mode} onChange={(e) => setMode(e.target.value as typeof mode)} className="rounded border border-line-strong bg-surface px-2 py-1">
                <option value="auto">Auto</option>
                <option value="llm">LLM (written, checked)</option>
                <option value="extractive">Extractive (quotes only)</option>
              </select>
            </label>
          </div>
          <div className="mt-3 flex items-center gap-3">
            <Button onClick={run} disabled={pending || selected.length < 2}>Compare</Button>
            {pending && <Spinner label="Gathering evidence from each source and comparing…" />}
          </div>
        </Panel>

        {error != null && <ErrorNotice error={error} title="Comparison failed" />}

        {result && comparison && (
          <>
            <ComparisonTable
              comparison={comparison}
              onCite={scrollToEvidence}
              verification={result.verification as unknown as Verification | null}
            />
            <VerificationPanel run={result} onCite={scrollToEvidence} />
            <RunSummary run={result} />
            <Panel title={`Evidence (${result.evidence.length} passages)`}>
              <EvidenceList evidence={result.evidence} />
            </Panel>
          </>
        )}
      </div>
    </>
  );
}
