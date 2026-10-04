// Friendly names for the types generated from the backend's OpenAPI schema
// (src/types/api.d.ts — regenerate with `npm run gen:api` after backend changes).
import type { components } from "@/types/api";

type Schemas = components["schemas"];

export type DocumentOut = Schemas["DocumentOut"];
export type UploadResponse = Schemas["UploadResponse"];
export type ChunkOut = Schemas["ChunkOut"];
export type AskRequest = Schemas["AskRequest"];
export type AskResponse = Schemas["AskResponse"];
export type EvidenceOut = Schemas["EvidenceOut"];
export type RunListItem = Schemas["RunListItem"];
export type PatentSearchRequest = Schemas["PatentSearchRequest"];
export type PatentSearchResponse = Schemas["PatentSearchResponse"];
export type PatentResultOut = Schemas["PatentResultOut"];
export type PatentOut = Schemas["PatentOut"];
export type PatentImportResponse = Schemas["PatentImportResponse"];
export type SourceStatusOut = Schemas["SourceStatusOut"];
export type InventionRequest = Schemas["InventionRequest"];
export type InventionAnalysisOut = Schemas["InventionAnalysisOut"];
export type InventionListItem = Schemas["InventionListItem"];
export type WatchOut = Schemas["WatchOut"];
export type WatchHitOut = Schemas["WatchHitOut"];
export type WatchCheckOut = Schemas["WatchCheckOut"];

export type RetrievalMode = NonNullable<AskRequest["retrieval_mode"]>;

// /system/info returns a plain dict on the backend, so it is typed by hand here
export interface SystemInfo {
  app_env: string;
  llm: {
    provider: string;
    model: string;
    temperature: number;
    max_tokens: number;
    reasoning_effort: string | null;
    prompt_version: string;
  };
  embeddings: { provider: string; model: string; dimensions: number };
  retrieval: {
    mode: RetrievalMode;
    top_k: number;
    candidate_k: number;
    min_similarity: number;
    max_context_tokens: number;
    reranker_enabled: boolean;
    reranker_model: string | null;
  };
  chunking: { strategy: string; max_tokens: number; overlap_tokens: number };
  uploads: { max_upload_mb: number; allowed_extensions: string[] };
  patent_sources: string[];
  counts: { documents: number; chunks: number; runs: number };
}

export interface HealthReady {
  status: "ready" | "not_ready";
  checks: {
    database: { status: "ok" | "error"; postgres?: string; pgvector?: string; detail?: string };
    llm_provider: string;
    embedding_provider: string;
    patent_sources: string[];
  };
}
