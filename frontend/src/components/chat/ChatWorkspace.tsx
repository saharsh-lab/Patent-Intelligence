"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, useSyncExternalStore, type DragEvent, type KeyboardEvent, type RefObject } from "react";
import useSWR, { useSWRConfig } from "swr";

import { AssistantAvatar, ChatMessageView, UserBubble } from "@/components/chat/ChatMessageView";
import { icons } from "@/components/icons";
import { Background } from "@/components/search/Background";
import { LiveTrace } from "@/components/chat/AgentTrace";
import { LogoMark } from "@/components/search/Logo";
import { ErrorNotice, Spinner } from "@/components/ui";
import { fetcher } from "@/lib/api";
import { greeting, useAuth } from "@/lib/auth";
import { chat, type ConversationDetail, type ConversationDocument } from "@/lib/chat";
import { SUGGESTIONS } from "@/lib/search";

const DOCUMENT_SUGGESTIONS = [
  "Summarise this patent in plain language",
  "What does claim 1 require?",
  "What problem does it solve?",
];
const COMPARE_SUGGESTIONS = [
  "Compare these documents",
  "What do they have in common?",
  "How do their claims differ?",
];
const START_SUGGESTIONS = [...SUGGESTIONS.slice(0, 2), "What is a patent claim?", "Latest patents on battery immersion cooling"];
const PENDING_STAGES = ["Searching your library and the web", "Ranking passages", "Writing the answer", "Checking every sentence"];
const LIVE_STAGES = ["Searching the patent offices and the web", "Reading abstracts and pages", "Writing the answer", "Checking every sentence"];
const TEST_STAGES = ["Searching the sources again", "Writing a first draft", "Planting a false sentence", "Checking every sentence (not told which)"];
const ACCEPT = ".pdf,.docx,.txt";
const CHIP = "border border-line bg-surface px-3.5 py-2 text-[0.9rem] text-text transition-colors hover:border-text";

/**
 * The one page for asking: a new chat opens on the search-style start screen (big box,
 * suggestions, tools); once a question is asked it becomes a conversation with the box
 * docked at the bottom. Attachments, follow-ups and the patent-database switch work in both.
 */
export function ChatWorkspace({ conversationId }: { conversationId?: string }) {
  const router = useRouter();
  const { mutate: mutateGlobal } = useSWRConfig();
  const { user } = useAuth();
  const key = conversationId ? `/conversations/${conversationId}` : null;
  // An answer still being written shows as "running" (e.g. after the page moved from
  // /chat to /chat/<id> mid-question, or after a reload): check again until it is done.
  const conversation = useSWR<ConversationDetail>(key, fetcher, {
    refreshInterval: (data) => (data?.messages.some((m) => m.response.status === "running") ? 3000 : 0),
  });

  const [draft, setDraft] = useState("");
  const [pending, setPending] = useState<string | null>(null); // message being answered
  const [testing, setTesting] = useState(false); // the pending message is a checker test
  const [uploading, setUploading] = useState<string[]>([]);
  const [error, setError] = useState<unknown>(null);
  const [dragging, setDragging] = useState(false);
  const [liveSearch, setLiveSearch] = useState(false); // also search the patent offices
  const fileInput = useRef<HTMLInputElement>(null);
  const bottom = useRef<HTMLDivElement>(null);
  const textarea = useRef<HTMLTextAreaElement>(null);

  const messages = conversation.data?.messages ?? [];
  const documents = conversation.data?.documents ?? [];
  const running = messages.some((m) => m.response.status === "running");

  // When a running answer finishes, the sidebar title (set with the answer) changes too
  const wasRunning = useRef(false);
  useEffect(() => {
    if (wasRunning.current && !running) mutateGlobal("/conversations");
    wasRunning.current = running;
  }, [running, mutateGlobal]);

  useEffect(() => {
    if (messages.length || pending) bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, pending]);

  /** The conversation to work in, created on first use (a new chat has none yet). */
  async function ensureConversation(): Promise<string> {
    if (conversationId) return conversationId;
    const created = await chat.create();
    await mutateGlobal("/conversations");
    router.replace(`/chat/${created.id}`, { scroll: false });
    return created.id;
  }

  async function send(text = draft, { test = false } = {}) {
    const message = text.trim();
    if (!message || pending || running) return;
    setError(null);
    if (!test) setDraft("");
    setPending(message);
    setTesting(test);
    let id: string | null = null;
    try {
      id = await ensureConversation();
      await chat.send(id, message, liveSearch, test);
      await Promise.all([mutateGlobal(`/conversations/${id}`), mutateGlobal("/conversations")]);
    } catch (e) {
      // A slow answer can outlast the connection although the server finished it:
      // look before reporting a failure.
      const latest = id ? await mutateGlobal<ConversationDetail>(`/conversations/${id}`) : undefined;
      if (latest?.messages.at(-1)?.user_message === message) {
        mutateGlobal("/conversations");
      } else {
        setError(e);
        if (!test) setDraft(message); // keep what the user typed
      }
    } finally {
      setPending(null);
      textarea.current?.focus();
    }
  }

  async function attach(files: FileList | File[]) {
    const list = Array.from(files).filter((f) => /\.(pdf|docx|txt)$/i.test(f.name));
    if (!list.length) {
      setError(new Error("Attach PDF, DOCX or TXT files."));
      return;
    }
    setError(null);
    try {
      const id = await ensureConversation();
      for (const file of list) {
        setUploading((u) => [...u, file.name]);
        try {
          await chat.attach(id, file);
        } finally {
          setUploading((u) => u.filter((n) => n !== file.name));
        }
        await mutateGlobal(`/conversations/${id}`);
      }
      await mutateGlobal("/conversations");
    } catch (e) {
      setError(e);
    }
  }

  async function detach(documentId: string) {
    if (!conversationId) return;
    await chat.detach(conversationId, documentId).catch(setError);
    await conversation.mutate();
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setDragging(false);
    if (e.dataTransfer.files.length) attach(e.dataTransfer.files);
  }

  const empty = messages.length === 0 && !pending && !conversation.isLoading;
  const scope = documents.length
    ? `Answers use ${documents.length === 1 ? "this document" : "these documents"}`
    : liveSearch
      ? "Answers search your library, the patent offices and the web"
      : "Answers search your library and the web (patent offices for patent questions)";
  const composer = (variant: "hero" | "dock") => (
    <Composer
      variant={variant}
      draft={draft}
      setDraft={setDraft}
      onSend={() => send()}
      onAttach={() => fileInput.current?.click()}
      liveSearch={liveSearch}
      toggleLive={() => setLiveSearch((v) => !v)}
      pending={!!pending || running}
      hasDocuments={documents.length > 0}
      textarea={textarea}
    />
  );

  return (
    <div
      className="relative isolate flex h-full min-h-[calc(100vh-3rem)] flex-col md:min-h-screen"
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={(e) => {
        if (e.currentTarget === e.target) setDragging(false);
      }}
      onDrop={onDrop}
    >
      <Background calm={!empty} />
      <input ref={fileInput} type="file" accept={ACCEPT} multiple hidden onChange={(e) => e.target.files && attach(e.target.files)} />
      {dragging && (
        <div className="pointer-events-none absolute inset-3 z-20 flex items-center justify-center border-2 border-dashed border-cite bg-surface/85 text-sm font-medium text-text">
          Drop PDF, DOCX or TXT files to attach them to this chat
        </div>
      )}

      {empty ? (
        // ------------------------------------------------------------- start screen
        <div className="mx-auto flex w-full max-w-[1080px] flex-1 flex-col items-center px-4 pt-[12vh] pb-16 text-center md:px-6 md:pt-[16vh]">
          <LogoMark size={44} draw className="text-text" />
          <h1 className="pi-line mt-[0.3em] mb-[0.2em] text-[clamp(2rem,5vw,3.2rem)] leading-[1.1] text-text">
            <span>
              {greeting()}
              {user ? (
                <>
                  , <span className="text-stamp italic">{user.name.split(" ")[0]}</span>
                </>
              ) : null}
            </span>
          </h1>
          <p className="pi-in mx-auto mb-7 max-w-[62ch] leading-[1.55] text-muted" style={{ animationDelay: "0.2s" }}>
            Ask about any technology or patent. Answers come from your documents, patent filings and the web, with every
            sentence linked to its source and checked.
          </p>

          <DocumentChips documents={documents} uploading={uploading} onDetach={detach} className="mb-3 justify-center" />
          <div className="w-full max-w-[720px] text-left">{composer("hero")}</div>

          <div className="stagger mt-[22px] flex max-w-[720px] flex-wrap justify-center gap-2" aria-label="Suggested questions">
            {(documents.length > 1 ? COMPARE_SUGGESTIONS : documents.length ? DOCUMENT_SUGGESTIONS : START_SUGGESTIONS).map((s) => (
              <button key={s} type="button" onClick={() => send(s)} className={CHIP}>
                {s}
              </button>
            ))}
          </div>

          {documents.length === 0 && (
            <nav aria-label="Tools" className="pi-in mt-10 flex flex-wrap justify-center gap-x-6 gap-y-2 text-sm" style={{ animationDelay: "0.5s" }}>
              <button type="button" onClick={() => fileInput.current?.click()} className="flex items-center gap-1.5 text-muted hover:text-text">
                <icons.paperclip width={15} height={15} /> Talk to a patent
              </button>
              <Link href="/invention" className="flex items-center gap-1.5 text-muted hover:text-text">
                <icons.bulb width={15} height={15} /> Check an idea
              </Link>
              <Link href="/landscape" className="flex items-center gap-1.5 text-muted hover:text-text">
                <icons.map width={15} height={15} /> Map a field
              </Link>
              <Link href="/watches" className="flex items-center gap-1.5 text-muted hover:text-text">
                <icons.bell width={15} height={15} /> Follow a topic
              </Link>
            </nav>
          )}
          {error ? (
            <div className="mt-6 w-full max-w-[720px] text-left">
              <ErrorNotice error={error} />
            </div>
          ) : null}
        </div>
      ) : (
        // ------------------------------------------------------------- conversation
        <>
          <header className="sticky top-0 z-10 border-b border-line bg-surface/90 px-4 py-2.5 backdrop-blur md:px-8">
            <div className="mx-auto flex max-w-3xl flex-wrap items-center gap-2">
              <h1 className="mr-2 truncate text-sm font-semibold">{conversation.data?.title ?? "New chat"}</h1>
              <DocumentChips documents={documents} uploading={uploading} onDetach={detach} />
              <span className="ml-auto text-xs text-muted">{scope}</span>
            </div>
          </header>

          <div className="flex-1 px-4 py-6 md:px-8">
            <div className="mx-auto max-w-3xl space-y-8">
              {conversation.isLoading && <Spinner label="Loading conversation…" />}
              {conversation.error && <ErrorNotice error={conversation.error} title="Could not load this conversation" />}
              {messages.map((m, i) => (
                <ChatMessageView
                  key={m.run_id}
                  message={m}
                  index={i}
                  userName={user?.name}
                  busy={!!pending || running}
                  onTestChecker={(question) => send(question, { test: true })}
                />
              ))}
              {pending && (
                <div className="space-y-4">
                  <UserBubble text={pending} name={user?.name} />
                  <div className="flex gap-3">
                    <AssistantAvatar />
                    <LiveTrace
                      conversationId={conversationId ?? null}
                      stages={testing ? TEST_STAGES : liveSearch ? LIVE_STAGES : PENDING_STAGES}
                    />
                  </div>
                </div>
              )}
              {error ? <ErrorNotice error={error} /> : null}
              <div ref={bottom} />
            </div>
          </div>

          <div className="sticky bottom-0 border-t border-line bg-bg/95 px-4 py-3 backdrop-blur md:px-8">
            <div className="mx-auto max-w-3xl">{composer("dock")}</div>
            <p className="mx-auto mt-1.5 max-w-3xl text-center text-[11px] text-muted">
              Enter to send · Shift+Enter for a new line · Technical information only, not legal advice.
            </p>
          </div>
        </>
      )}
    </div>
  );
}

/** The question box: big on the start screen, docked under the conversation. */
function Composer({
  variant,
  draft,
  setDraft,
  onSend,
  onAttach,
  liveSearch,
  toggleLive,
  pending,
  hasDocuments,
  textarea,
}: {
  variant: "hero" | "dock";
  draft: string;
  setDraft: (text: string) => void;
  onSend: () => void;
  onAttach: () => void;
  liveSearch: boolean;
  toggleLive: () => void;
  pending: boolean;
  hasDocuments: boolean;
  textarea: RefObject<HTMLTextAreaElement | null>;
}) {
  const hero = variant === "hero";
  const narrow = useNarrowScreen();
  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      onSend();
    }
  }
  const lines = Math.max(0, draft.split("\n").length - 1);
  // One row: tools, text and button share the same height and are centred together.
  // Several lines of text: everything sits at the bottom, next to the line being typed.
  const tool = `flex shrink-0 items-center justify-center gap-1.5 text-muted transition-colors hover:bg-surface-2 hover:text-text ${hero ? "h-11" : "h-9"}`;
  return (
    <form
      // Reference search-bar look: ink border and hard shadow, both turn blue on focus
      className={`flex gap-1 border-[1.5px] border-text bg-surface p-1.5 shadow-hard transition-[border-color,box-shadow] duration-200 focus-within:border-cite focus-within:[box-shadow:var(--shadow-hard-focus)] ${lines ? "items-end" : "items-center"}`}
      onSubmit={(e) => {
        e.preventDefault();
        onSend();
      }}
    >
      <button type="button" onClick={onAttach} aria-label="Attach documents" title="Attach PDF, DOCX or TXT"
        className={`${tool} ${hero ? "w-11" : "w-9"}`}>
        <icons.paperclip width={18} height={18} />
      </button>
      <button
        type="button"
        onClick={toggleLive}
        aria-pressed={liveSearch}
        aria-label="Search patent databases"
        title={liveSearch
          ? "On: every question also searches the patent offices (EPO) and uses the best abstracts"
          : "Off: the patent offices are searched for patent questions, or when your library has no answer"}
        className={`${tool} px-2.5 text-[13px] leading-none font-medium ${liveSearch ? "bg-accent-soft text-accent hover:bg-accent-soft hover:text-accent" : ""}`}
      >
        <icons.globe width={18} height={18} />
        <span className="hidden sm:inline">Patent DBs</span>
      </button>
      {/* Follows the tools: centred on one row, beside the last line when there are several */}
      <span aria-hidden className={`mx-1 w-px shrink-0 bg-line ${hero ? "h-6" : "h-5"} ${lines ? (hero ? "mb-2.5" : "mb-2") : ""}`} />
      <textarea
        ref={textarea}
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={onKeyDown}
        rows={1}
        maxLength={2000}
        autoFocus={hero}
        placeholder={hasDocuments ? (narrow ? "Ask about them…" : "Ask about the attached documents…") : narrow ? "Ask a question…" : "Describe a technology or ask a question"}
        aria-label="Message"
        className={`max-h-40 min-w-0 flex-1 resize-none bg-transparent px-1 outline-none placeholder:text-muted ${hero ? "py-[11px] text-[1.05rem] leading-[22px]" : "py-2 text-sm leading-5"}`}
        style={{ height: `${Math.min(160, (hero ? 44 : 36) + lines * (hero ? 22 : 20))}px` }}
      />
      <button type="submit" disabled={!draft.trim() || pending} aria-label="Send"
        className={`flex shrink-0 items-center justify-center bg-brand font-medium hover:opacity-90 disabled:opacity-40 ${hero ? "h-11 px-[22px]" : "h-9 w-10"}`}>
        {hero ? "Ask" : <icons.send width={18} height={18} />}
      </button>
    </form>
  );
}

function DocumentChips({
  documents,
  uploading,
  onDetach,
  className = "",
}: {
  documents: ConversationDocument[];
  uploading: string[];
  onDetach: (id: string) => void;
  className?: string;
}) {
  if (!documents.length && !uploading.length) return null;
  return (
    <div className={`flex flex-wrap items-center gap-2 ${className}`}>
      {documents.map((d) => (
        <span key={d.id} className="inline-flex items-center gap-1 border border-line bg-surface-2 py-0.5 pr-1 pl-2.5 text-xs">
          {d.kind === "patent" ? <icons.search width={12} height={12} className="text-muted" /> : <icons.file width={12} height={12} className="text-muted" />}
          <span className="max-w-40 truncate" title={d.title ?? d.filename}>{d.title || d.filename}</span>
          <button type="button" onClick={() => onDetach(d.id)} aria-label={`Remove ${d.filename} from this chat`} className="p-0.5 text-muted hover:bg-surface hover:text-bad">
            <icons.x width={11} height={11} />
          </button>
        </span>
      ))}
      {uploading.map((name) => (
        <span key={name} className="inline-flex items-center gap-1.5 border border-dashed border-cite/60 px-2.5 py-0.5 text-xs text-text">
          <Spinner /> {name}
        </span>
      ))}
    </div>
  );
}

/** True on phone-width screens, where the long placeholder would wrap and be cut off. */
function useNarrowScreen(): boolean {
  return useSyncExternalStore(
    (onChange) => {
      const query = window.matchMedia("(max-width: 639px)");
      query.addEventListener("change", onChange);
      return () => query.removeEventListener("change", onChange);
    },
    () => window.matchMedia("(max-width: 639px)").matches,
    () => false, // server render: the wide placeholder
  );
}
