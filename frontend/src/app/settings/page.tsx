"use client";

import useSWR from "swr";

import { Badge, ErrorNotice, KeyValue, PageHeader, Panel } from "@/components/ui";
import { fetcher } from "@/lib/api";
import type { SystemInfo } from "@/lib/types";

const mono = (value: string | number | null) => (
  <span className="font-mono text-xs">{value ?? "—"}</span>
);

export default function SettingsPage() {
  const { data, error } = useSWR<SystemInfo>("/system/info", fetcher);
  return (
    <>
      <PageHeader
        title="Settings"
        description={
          <>
            Read-only view of the active configuration. Change values in the backend <code className="font-mono">.env</code> file and restart the API. API keys are never shown here.
          </>
        }
      />
      {error && <ErrorNotice error={error} title="Cannot load settings" />}
      {data && (
        <div className="grid gap-6 lg:grid-cols-2">
          <Panel title="Language model">
            <KeyValue items={[
              ["Provider", mono(data.llm.provider)],
              ["Model", mono(data.llm.model)],
              ["Temperature", mono(data.llm.temperature)],
              ["Max output tokens", mono(data.llm.max_tokens)],
              ["Reasoning effort", mono(data.llm.reasoning_effort ?? "not sent")],
              ["Prompt version", mono(data.llm.prompt_version)],
            ]} />
          </Panel>
          <Panel title="Retrieval">
            <KeyValue items={[
              ["Mode", mono(data.retrieval.mode)],
              ["Passages to LLM (top-k)", mono(data.retrieval.top_k)],
              ["Candidates per method", mono(data.retrieval.candidate_k)],
              ["Min. similarity", mono(data.retrieval.min_similarity)],
              ["Context budget (tokens)", mono(data.retrieval.max_context_tokens)],
              ["Reranker", data.retrieval.reranker_enabled ? mono(data.retrieval.reranker_model) : <Badge key="r">Off</Badge>],
            ]} />
          </Panel>
          <Panel title="Embeddings & chunking">
            <KeyValue items={[
              ["Embedding provider", mono(data.embeddings.provider)],
              ["Embedding model", mono(data.embeddings.model)],
              ["Dimensions", mono(data.embeddings.dimensions)],
              ["Chunking strategy", mono(data.chunking.strategy)],
              ["Chunk size / overlap", mono(`${data.chunking.max_tokens} / ${data.chunking.overlap_tokens} tokens`)],
            ]} />
          </Panel>
          <Panel title="Data sources & uploads">
            <KeyValue items={[
              ["Uploaded documents", <Badge key="u" tone="ok">Enabled</Badge>],
              ["Patent APIs", data.patent_sources.length
                ? <span key="p" className="flex gap-1">{data.patent_sources.map((s) => <Badge key={s} tone="ok">{s.toUpperCase()}</Badge>)}</span>
                : <span key="p" className="text-muted">None configured (Phase 5)</span>],
              ["Allowed file types", mono(data.uploads.allowed_extensions.join(", "))],
              ["Max upload size", mono(`${data.uploads.max_upload_mb} MB`)],
              ["Environment", mono(data.app_env)],
            ]} />
          </Panel>
        </div>
      )}
    </>
  );
}
