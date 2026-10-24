// Conversations (chat). Backend: app/api/routes/conversations.py.
import { ApiError, parseError } from "./api";
import type { AskResponse, DocumentOut } from "./types";

export interface ConversationDocument {
  id: string;
  kind: "document" | "patent";
  filename: string;
  title: string | null;
  status: string;
}

export interface ConversationSummary {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  documents: ConversationDocument[];
}

export interface ChatMessage {
  run_id: string;
  user_message: string;
  // The standalone question the system answered, when memory rewrote a follow-up
  interpreted_as: string | null;
  created_at: string;
  response: AskResponse;
}

export interface ConversationDetail extends ConversationSummary {
  messages: ChatMessage[];
}

async function call<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, init);
  } catch {
    throw new ApiError("Cannot reach the server.", 0, "network_error");
  }
  if (!response.ok) throw await parseError(response);
  return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
}

const json = (body: unknown): RequestInit => ({
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const chat = {
  create: (title?: string) => call<ConversationDetail>("/conversations", { method: "POST", ...json({ title: title ?? null }) }),
  rename: (id: string, title: string) => call<ConversationSummary>(`/conversations/${id}`, { method: "PATCH", ...json({ title }) }),
  remove: (id: string) => call<void>(`/conversations/${id}`, { method: "DELETE" }),
  send: (id: string, message: string, liveSearch = false, injectFalseFact = false) =>
    call<ChatMessage>(`/conversations/${id}/messages`, {
      method: "POST",
      ...json({ message, live_search: liveSearch, inject_false_fact: injectFalseFact, timezone: timeZone() }),
    }),
  /** The Stop button: the answer stops, keeping what was written so far */
  stop: (id: string) => call<void>(`/conversations/${id}/stop`, { method: "POST" }),
  attach: (id: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return call<{ document: DocumentOut; duplicate: boolean }>(`/conversations/${id}/documents`, { method: "POST", body: form });
  },
  attachSource: (id: string, source: { document_id?: string; patent_id?: string }) =>
    call<ConversationSummary>(`/conversations/${id}/sources`, { method: "POST", ...json(source) }),
  detach: (id: string, documentId: string) => call<void>(`/conversations/${id}/documents/${documentId}`, { method: "DELETE" }),
  /** Follow-up questions for an answer (written once on the server, then kept) */
  suggestions: (id: string, runId: string) =>
    call<{ suggestions: string[] }>(`/conversations/${id}/messages/${runId}/suggestions`, { method: "POST" }),
};

/** The browser's time zone (e.g. "Asia/Kolkata"), for "what day is it?" */
export function timeZone(): string | null {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone ?? null;
  } catch {
    return null;
  }
}

/** An answer as plain text for the clipboard: [E2] becomes [2], and the cited sources are
 *  listed underneath. */
export function copyText(answer: string, evidence: { label: string | null; source_title?: string | null; source_label: string; source_url?: string | null; cited: boolean }[]): string {
  const text = answer.replace(/\[E(\d+)\]/g, "[$1]").replace(/\*\*([^*]+)\*\*/g, "$1").trim();
  const cited = evidence.filter((e) => e.cited && e.label);
  if (!cited.length) return text;
  const lines = cited.map((e) => {
    const name = e.source_title && e.source_title !== e.source_label ? `${e.source_label}: ${e.source_title}` : e.source_label;
    return `[${(e.label as string).replace(/^E/, "")}] ${name}${e.source_url ? ` (${e.source_url})` : ""}`;
  });
  return `${text}\n\nSources:\n${lines.join("\n")}`;
}

/** One-click ways to continue from an answer (sent as ordinary follow-up messages). */
export const QUICK_ACTIONS = [
  { label: "Simpler", message: "Explain that in simpler terms" },
  { label: "Shorter", message: "Summarise that in two sentences" },
  { label: "More detailed", message: "Go deeper into the technical details of that" },
] as const;

/** Group conversations for the sidebar: Today, Yesterday, Previous 7 days, Older. */
export function groupByRecency(items: ConversationSummary[], now = new Date()): [string, ConversationSummary[]][] {
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const day = 86_400_000;
  const groups: Record<string, ConversationSummary[]> = {};
  for (const item of items) {
    const t = new Date(item.updated_at).getTime();
    const label = t >= startOfToday ? "Today" : t >= startOfToday - day ? "Yesterday" : t >= startOfToday - 7 * day ? "Previous 7 days" : "Older";
    (groups[label] ??= []).push(item);
  }
  return ["Today", "Yesterday", "Previous 7 days", "Older"].filter((g) => groups[g]).map((g) => [g, groups[g]]);
}
