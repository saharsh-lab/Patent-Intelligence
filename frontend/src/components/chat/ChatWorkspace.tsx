"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, useSyncExternalStore, type DragEvent, type KeyboardEvent, type RefObject } from "react";
import useSWR, { useSWRConfig } from "swr";

import { AssistantAvatar, ChatMessageView, UserBubble } from "@/components/chat/ChatMessageView";
import { ChatSidebar } from "@/components/chat/ChatSidebar";
import { LiveAnswer } from "@/components/chat/LiveAnswer";
import { icons } from "@/components/icons";
import { ErrorNotice, Spinner } from "@/components/ui";
import { fetcher } from "@/lib/api";
import { greeting, useAuth } from "@/lib/auth";
import { chat, type ConversationDetail, type ConversationDocument } from "@/lib/chat";
import { setSidebarHidden, useSidebarHidden } from "@/lib/sidebar";
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
const ACCEPT = ".pdf,.docx,.txt";

/**
 * The one page for asking, laid out after the reference site's analysis page: the actions,
 * tools and chat history on the left; on the right one rounded panel with the active
 * context (attached documents, the patent-database switch), the conversation and the
 * question box. A new chat opens on a greeting with suggested questions.
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
  const [sheet, setSheet] = useState(false); // phones: the left column as a sheet
  const sidebarHidden = useSidebarHidden(); // wide screens: the left column hidden
  const fileInput = useRef<HTMLInputElement>(null);
  const bottom = useRef<HTMLDivElement>(null);
  const textarea = useRef<HTMLTextAreaElement>(null);

  const messages = conversation.data?.messages ?? [];
  const documents = conversation.data?.documents ?? [];
  const running = messages.some((m) => m.response.status === "running");
  // The question whose answer was just watched live: it then appears without a fade-in
  // (otherwise the answer the reader was following blinks out and back)
  const [watched, setWatched] = useState<string | null>(null);
  const live = pending ?? messages.find((m) => m.response.status === "running")?.user_message ?? null;
  if (live && live !== watched) setWatched(live);

  // When a running answer finishes, the sidebar title (set with the answer) changes too
  const wasRunning = useRef(false);
  useEffect(() => {
    if (wasRunning.current && !running) mutateGlobal("/conversations");
    wasRunning.current = running;
  }, [running, mutateGlobal]);

  useEffect(() => {
    if (messages.length || pending) bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, pending]);

  // Ctrl/⌘+B hides or shows the left column (as in code editors)
  useEffect(() => {
    const onKey = (e: globalThis.KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && !e.altKey && !e.shiftKey && e.key.toLowerCase() === "b") {
        e.preventDefault();
        setSidebarHidden(!sidebarHidden);
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [sidebarHidden]);

  // The phone sheet closes with Escape too
  useEffect(() => {
    if (!sheet) return;
    const onKey = (e: globalThis.KeyboardEvent) => e.key === "Escape" && setSheet(false);
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [sheet]);

  // "Jump to latest" appears when the end of the conversation is out of view
  const [atBottom, setAtBottom] = useState(true);
  useEffect(() => {
    const end = bottom.current;
    if (!end) return;
    const observer = new IntersectionObserver(([entry]) => setAtBottom(entry.isIntersecting), { rootMargin: "0px 0px 160px 0px" });
    observer.observe(end);
    return () => observer.disconnect();
  }, [messages.length]);

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

  /** The Stop button: the answer stops at its next step, keeping what was written. */
  async function stop() {
    if (conversationId) await chat.stop(conversationId).catch(setError);
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
  const examples = documents.length > 1 ? COMPARE_SUGGESTIONS : documents.length ? DOCUMENT_SUGGESTIONS : START_SUGGESTIONS;
  const scope = documents.length
    ? `Answers use ${documents.length === 1 ? "this document" : "these documents"}`
    : liveSearch
      ? "Every answer also searches the patent offices"
      : "Your library, patent filings and the web";
  const openFiles = () => fileInput.current?.click();

  return (
    <div
      className="relative flex h-[calc(100dvh-6rem)] md:h-[calc(100dvh-7.25rem)]"
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={(e) => {
        if (e.currentTarget === e.target) setDragging(false);
      }}
      onDrop={onDrop}
    >
      <input ref={fileInput} type="file" accept={ACCEPT} multiple hidden onChange={(e) => e.target.files && attach(e.target.files)} />

      {/* Left column (after the reference's analysis page): hideable with the panel button;
          a sheet on phones. Its width animates; the content keeps its width meanwhile. */}
      <aside id="chat-sidebar" className="chat-aside hidden shrink-0 overflow-hidden lg:block" inert={sidebarHidden} aria-hidden={sidebarHidden}>
        <div className="chat-aside-inner h-full overflow-y-auto">
          <ChatSidebar onAttach={openFiles} />
        </div>
      </aside>
      {sheet && (
        <div className="fixed inset-0 z-50 lg:hidden" role="dialog" aria-label="Chats and tools">
          <button type="button" aria-label="Close" className="absolute inset-0 bg-black/60" onClick={() => setSheet(false)} />
          <div className="pi-in absolute inset-y-3 left-3 w-[min(340px,calc(100vw-1.5rem))] overflow-y-auto rounded-3xl bg-bg p-1">
            <div className="flex justify-end pb-2">
              <button type="button" onClick={() => setSheet(false)} aria-label="Close chats and tools" className="grid h-9 w-9 place-items-center rounded-full border border-line bg-surface hover:bg-surface-2">
                <icons.x width={16} height={16} />
              </button>
            </div>
            <ChatSidebar
              onAttach={() => {
                setSheet(false);
                openFiles();
              }}
            />
          </div>
        </div>
      )}

      <section className="glass relative flex min-w-0 flex-1 flex-col overflow-hidden rounded-3xl">
        {dragging && (
          <div className="pointer-events-none absolute inset-3 z-20 flex items-center justify-center rounded-3xl border-2 border-dashed border-cite bg-surface/90 text-sm font-medium">
            Drop PDF, DOCX or TXT files to attach them to this chat
          </div>
        )}
        <div className="flex items-center gap-1 border-b border-line px-3 md:px-5">
          <button type="button" onClick={() => setSheet(true)} aria-label="Chats and tools" className="mr-1 grid h-9 w-9 place-items-center rounded-full text-muted hover:bg-surface-2 hover:text-text lg:hidden">
            <icons.menu width={17} height={17} />
          </button>
          <button
            type="button"
            onClick={() => setSidebarHidden(!sidebarHidden)}
            aria-controls="chat-sidebar"
            aria-expanded={!sidebarHidden}
            aria-label={sidebarHidden ? "Show chats and tools" : "Hide chats and tools"}
            title={`${sidebarHidden ? "Show" : "Hide"} chats and tools (Ctrl/⌘ B)`}
            className="mr-1 hidden h-9 w-9 place-items-center rounded-full text-muted transition-colors hover:bg-surface-2 hover:text-text lg:grid"
          >
            <icons.sidebar width={18} height={18} />
          </button>
          <span className="-mb-px border-b-2 border-accent px-3 py-4 text-sm font-semibold text-accent">Chat assistant</span>
          <Link href="/invention" className="px-3 py-4 text-sm font-medium text-muted transition-colors hover:text-text">
            Invention analysis
          </Link>
          {conversation.data && !empty && (
            <span className="ml-auto hidden max-w-[40%] truncate text-xs text-muted md:block" title={conversation.data.title}>
              {conversation.data.title}
            </span>
          )}
        </div>

        <ContextBar
          documents={documents}
          uploading={uploading}
          onDetach={detach}
          onAttach={openFiles}
          scope={scope}
          liveSearch={liveSearch}
          toggleLive={() => setLiveSearch((v) => !v)}
        />

        <div className="flex-1 overflow-y-auto px-4 py-6 md:px-8">
          <div className="mx-auto max-w-3xl space-y-8">
            {conversation.isLoading && <Spinner label="Loading conversation…" />}
            {conversation.error && <ErrorNotice error={conversation.error} title="Could not load this conversation" />}
            {empty && <Welcome name={user?.name} examples={examples} onAsk={(s) => send(s)} hasDocuments={documents.length > 0} />}
            {messages.map((m, i) => (
              <ChatMessageView
                key={m.run_id}
                message={m}
                index={i}
                userName={user?.name}
                busy={!!pending || running}
                onTestChecker={(question) => send(question, { test: true })}
                onAsk={i === messages.length - 1 && !pending ? (text) => send(text) : undefined}
                onRegenerate={() => send(m.user_message)}
                onFixed={() => conversation.mutate()}
                onEdit={(text) => {
                  setDraft(text);
                  textarea.current?.focus();
                }}
                instant={i === messages.length - 1 && m.user_message === watched}
                examples={examples}
              />
            ))}
            {pending && (
              <div className="space-y-4">
                <UserBubble text={pending} name={user?.name} />
                <div className="flex gap-3">
                  <AssistantAvatar />
                  <LiveAnswer conversationId={conversationId ?? null} testing={testing} />
                </div>
              </div>
            )}
            {error ? <ErrorNotice error={error} /> : null}
            <div ref={bottom} />
          </div>
        </div>

        <div className="relative px-3 pt-2 pb-3 md:px-6 md:pb-4">
          {!atBottom && (messages.length > 0 || !!pending) && (
            <button
              type="button"
              onClick={() => bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" })}
              aria-label="Jump to the latest message"
              className="pi-in absolute -top-11 left-1/2 grid h-9 w-9 -translate-x-1/2 place-items-center rounded-full border border-line bg-surface text-text shadow-card hover:border-line-strong"
            >
              <icons.arrowDown width={16} height={16} />
            </button>
          )}
          <div className="mx-auto max-w-3xl">
            <Composer
              draft={draft}
              setDraft={setDraft}
              onSend={() => send()}
              onAttach={openFiles}
              pending={!!pending || running}
              onStop={stop}
              hasDocuments={documents.length > 0}
              textarea={textarea}
              autoFocus={empty}
            />
            <p className="mt-2 hidden text-center text-[11px] text-muted sm:block">
              Enter to send · Shift+Enter for a new line · Technical information only, not legal advice
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}

/** A new chat: the assistant's greeting and questions to start with. */
function Welcome({ name, examples, onAsk, hasDocuments }: { name?: string; examples: string[]; onAsk: (q: string) => void; hasDocuments: boolean }) {
  return (
    <div className="space-y-5">
      <div className="pi-in flex gap-3">
        <AssistantAvatar draw />
        <div className="rounded-2xl rounded-tl-md border-2 border-text/80 px-5 py-3.5">
          <p className="text-[1.05rem] font-semibold tracking-tight">
            {greeting()}
            {name ? `, ${name.split(" ")[0]}` : ""}. How can I help you?
          </p>
          <p className="mt-0.5 text-sm text-muted">
            {hasDocuments
              ? "Ask about the attached documents: every sentence of the answer is linked to its source and checked."
              : "Ask about any technology or patent. Answers come from your documents, patent filings and the web, with every sentence checked."}
          </p>
        </div>
      </div>
      <div className="stagger grid gap-2.5 pl-11 sm:grid-cols-2" aria-label="Suggested questions">
        {examples.map((q) => (
          <button
            key={q}
            type="button"
            onClick={() => onAsk(q)}
            className="press group flex items-center justify-between gap-3 rounded-2xl border border-line bg-surface/50 px-4 py-3 text-left text-sm transition-colors hover:border-line-strong hover:bg-surface-2"
          >
            <span>{q}</span>
            <icons.arrowRight width={15} height={15} className="shrink-0 text-muted transition-transform group-hover:translate-x-0.5" />
          </button>
        ))}
      </div>
    </div>
  );
}

/** What the answers draw on: the attached documents, or everything (the reference's
 *  "Active context" bar). */
function ContextBar({
  documents,
  uploading,
  onDetach,
  onAttach,
  scope,
  liveSearch,
  toggleLive,
}: {
  documents: ConversationDocument[];
  uploading: string[];
  onDetach: (id: string) => void;
  onAttach: () => void;
  scope: string;
  liveSearch: boolean;
  toggleLive: () => void;
}) {
  const attached = documents.length > 0 || uploading.length > 0;
  return (
    <div className="mx-3 mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 rounded-2xl bg-surface-2/60 px-4 py-3 md:mx-4">
      <span className="hidden h-11 w-11 shrink-0 place-items-center rounded-xl border border-line bg-surface text-accent sm:grid">
        <icons.file width={19} height={19} />
      </span>
      {/* Wide enough for the title; on phones the buttons wrap underneath */}
      <div className="min-w-[13rem] flex-1">
        <p className="text-[11px] font-semibold tracking-[0.12em] text-muted uppercase">Active context</p>
        {attached ? (
          <div className="mt-1 flex flex-wrap items-center gap-1.5">
            {documents.map((d) => (
              <span key={d.id} className="inline-flex items-center gap-1 rounded-full border border-line bg-surface py-0.5 pr-1 pl-2.5 text-xs font-medium">
                {d.kind === "patent" ? <icons.search width={12} height={12} className="text-muted" /> : <icons.file width={12} height={12} className="text-muted" />}
                <span className="max-w-44 truncate" title={d.title ?? d.filename}>
                  {d.title || d.filename}
                </span>
                <button type="button" onClick={() => onDetach(d.id)} aria-label={`Remove ${d.filename} from this chat`} className="rounded-full p-0.5 text-muted hover:bg-surface-2 hover:text-bad">
                  <icons.x width={11} height={11} />
                </button>
              </span>
            ))}
            {uploading.map((name) => (
              <span key={name} className="inline-flex items-center gap-1.5 rounded-full border border-dashed border-cite/60 px-2.5 py-0.5 text-xs">
                <Spinner /> {name}
              </span>
            ))}
          </div>
        ) : (
          <p className="truncate font-semibold tracking-tight">No document attached</p>
        )}
        <p className="truncate text-xs text-muted">{scope}</p>
      </div>
      <div className="-ml-3 flex items-center gap-1 sm:ml-0">
        <button
          type="button"
          onClick={toggleLive}
          aria-pressed={liveSearch}
          title={liveSearch ? "On: every question also searches the patent offices (EPO)" : "Off: the patent offices are searched for patent questions, or when nothing else answers"}
          className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${liveSearch ? "bg-accent-soft text-accent" : "text-muted hover:bg-surface hover:text-text"}`}
        >
          <icons.globe width={14} height={14} /> Patent DBs {liveSearch ? "on" : "off"}
        </button>
        <button type="button" onClick={onAttach} className="flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium text-muted transition-colors hover:bg-surface hover:text-text">
          <icons.paperclip width={14} height={14} /> {attached ? "Add" : "Attach"}
        </button>
      </div>
    </div>
  );
}

/** The question box: a pill, as on the reference. */
function Composer({
  draft,
  setDraft,
  onSend,
  onAttach,
  pending,
  onStop,
  hasDocuments,
  textarea,
  autoFocus,
}: {
  draft: string;
  setDraft: (text: string) => void;
  onSend: () => void;
  onAttach: () => void;
  pending: boolean;
  onStop: () => void;
  hasDocuments: boolean;
  textarea: RefObject<HTMLTextAreaElement | null>;
  autoFocus: boolean;
}) {
  const narrow = useNarrowScreen();
  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      onSend();
    }
  }
  const lines = Math.max(0, draft.split("\n").length - 1);
  const round = "grid h-10 w-10 shrink-0 place-items-center rounded-full";
  return (
    <form
      className={`flex gap-1.5 border border-line bg-pill p-1.5 shadow-card transition-[border-color,box-shadow,border-radius] duration-200 focus-within:border-cite focus-within:[box-shadow:var(--shadow-hard-focus)] ${lines ? "items-end rounded-[22px]" : "items-center rounded-full"}`}
      onSubmit={(e) => {
        e.preventDefault();
        onSend();
      }}
    >
      <button type="button" onClick={onAttach} aria-label="Attach documents" title="Attach PDF, DOCX or TXT" className={`${round} text-muted hover:bg-surface-2 hover:text-text`}>
        <icons.paperclip width={18} height={18} />
      </button>
      <textarea
        ref={textarea}
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={onKeyDown}
        rows={1}
        maxLength={2000}
        autoFocus={autoFocus}
        placeholder={hasDocuments ? (narrow ? "Ask about them…" : "Ask about the attached documents…") : narrow ? "Ask a question…" : "Ask about any technology or patent…"}
        aria-label="Message"
        className="max-h-40 min-w-0 flex-1 resize-none bg-transparent px-1 py-2 text-[0.95rem] leading-6 outline-none placeholder:text-muted"
        style={{ height: `${Math.min(160, 40 + lines * 24)}px` }}
      />
      {pending ? (
        // While an answer is written the button stops it (and keeps what was written)
        <button type="button" onClick={onStop} aria-label="Stop the answer" title="Stop" className={`${round} bg-text text-bg hover:opacity-90`}>
          <icons.stop width={15} height={15} />
        </button>
      ) : (
        <button type="submit" disabled={!draft.trim()} aria-label="Send" className={`${round} bg-brand hover:opacity-90 disabled:opacity-30`}>
          <icons.arrowRight width={18} height={18} />
        </button>
      )}
    </form>
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
