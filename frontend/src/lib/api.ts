// Thin, typed client for the FastAPI backend. All calls go to /api/*, which
// Next.js forwards to the backend (see next.config.ts).
import type {
  AskRequest,
  AskResponse,
  ChunkOut,
  DocumentOut,
  HealthReady,
  PatentImportResponse,
  PatentOut,
  PatentSearchRequest,
  PatentSearchResponse,
  RunListItem,
  SourceStatusOut,
  SystemInfo,
  UploadResponse,
} from "./types";

const BASE = "/api";

/** An error response from the backend, in its standard {"error": {...}} shape. */
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public code: string,
    public requestId?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function parseError(response: Response): Promise<ApiError> {
  try {
    const body = await response.json();
    const error = body?.error;
    if (error?.message) {
      return new ApiError(error.message, response.status, error.code ?? "error", error.request_id);
    }
  } catch {
    // not JSON (e.g. proxy error page) — fall through
  }
  const message =
    response.status === 500 || response.status === 502 || response.status === 504
      ? "The server is unavailable. Is the backend running?"
      : `Request failed (${response.status}).`;
  return new ApiError(message, response.status, "http_error");
}

/** Session expired or missing: go to the login page and come back afterwards. */
export function redirectToLogin() {
  if (typeof window === "undefined" || window.location.pathname.startsWith("/login")) return;
  const next = encodeURIComponent(window.location.pathname + window.location.search);
  // A full reload on purpose: it drops every cached response of the expired session
  // eslint-disable-next-line @next/next/no-location-assign-relative-destination
  window.location.assign(`/login?next=${next}`);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, init);
  } catch {
    throw new ApiError("Cannot reach the server.", 0, "network_error");
  }
  if (response.status === 401 && !path.startsWith("/auth/")) redirectToLogin();
  if (!response.ok) throw await parseError(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

/** SWR fetcher: `useSWR("/documents", fetcher)`. */
export const fetcher = <T>(path: string) => request<T>(path);

export const api = {
  health: () => request<HealthReady>("/health/ready"),
  systemInfo: () => request<SystemInfo>("/system/info"),

  listDocuments: () => request<DocumentOut[]>("/documents"),
  getDocument: (id: string) => request<DocumentOut>(`/documents/${id}`),
  listChunks: (id: string, section?: string) =>
    request<ChunkOut[]>(
      `/documents/${id}/chunks?limit=200${section ? `&section=${encodeURIComponent(section)}` : ""}`,
    ),
  uploadDocument: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<UploadResponse>("/documents", { method: "POST", body: form });
  },
  deleteDocument: (id: string) => request<void>(`/documents/${id}`, { method: "DELETE" }),

  ask: (body: AskRequest) =>
    request<AskResponse>("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  listRuns: (limit = 30) => request<RunListItem[]>(`/runs?limit=${limit}`),
  getRun: (id: string) => request<AskResponse>(`/runs/${id}`),

  patentSources: () => request<SourceStatusOut[]>("/patents/sources"),
  searchPatents: (body: PatentSearchRequest) =>
    request<PatentSearchResponse>("/patents/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  importPatent: (source: string, publication_number: string) =>
    request<PatentImportResponse>("/patents/import", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source, publication_number }),
    }),
  listPatents: () => request<PatentOut[]>("/patents"),
  deletePatent: (id: string) => request<void>(`/patents/${id}`, { method: "DELETE" }),
};
