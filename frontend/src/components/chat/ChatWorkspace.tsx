"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, type DragEvent, type KeyboardEvent } from "react";
import useSWR, { useSWRConfig } from "swr";

import { AssistantAvatar, ChatMessageView, UserBubble } from "@/components/chat/ChatMessageView";
import { LogoMark } from "@/components/search/Logo";
import { icons } from "@/components/icons";
import { ScanStatus } from "@/components/search/LoadingState";
import { ErrorNotice, Spinner } from "@/components/ui";
import { fetcher } from "@/lib/api";
import { greeting, useAuth } from "@/lib/auth";
import { chat, type ConversationDetail } from "@/lib/chat";

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
// Cards in the reference style: white sheet, thin border, blue left rule on hover
const ACTION = "press pi-card flex flex-col items-center gap-1.5 border border-line bg-surface p-4 text-sm";
const ACTION_ICON = "mb-1 flex h-9 w-9 items-center justify-center border border-line text-text";
const PENDING_STAGES = ["Searching your library", "Ranking passages", "Writing the answer", "Checking every sentence"];
const LIVE_STAGES = ["Searching the patent databases", "Importing the best matches", "Writing the answer", "Checking every sentence"];
const ACCEPT = ".pdf,.docx,.txt";

export function ChatWorkspace({ conversationId }: { conversationId?: string }) {
  const router = useRouter();
  const { mutate: mutateGlobal } = useSWRConfig();
  const { user } = useAuth();
  const key = conversationId ? `/conversations/${conversationId}` : null;
  const conversation = useSWR<ConversationDetail>(key, fetcher);

  const [draft, setDraft] = useState("");
  const [pending, setPending] = useState<string | null>(null); // message being answered
  const [uploading, setUploading] = useState<string[]>([]);
  const [error, setError] = useState<unknown>(null);
  const [dragging, setDragging] = useState(false);
  const [liveSearch, setLiveSearch] = useState(false); // also search the patent databases
  const fileInput = useRef<HTMLInputElement>(null);
  const bottom = useRef<HTMLDivElement>(null);
  const textarea = useRef<HTMLTextAreaElement>(null);

  const messages = conversation.data?.messages ?? [];
  const documents = conversation.data?.documents ?? [];

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, pending]);


  /** The conversation to work in, created on first use (a new chat has none yet). */
  async function ensureConversation(): Promise<string> {
    if (conversationId) return conversationId;
    const created = await chat.create();
    await mutateGlobal("/conversations");
    router.replace(`/chat/${created.id}`, { scroll: false });
    return created.id;
  }

  async function send(text = draft) {
    const message = text.trim();
    if (!message || pending) return;
    setError(null);
    setDraft("");
    setPending(message);
    let id: string | null = null;
    try {
      id = await ensureConversation();
      await chat.send(id, message, liveSearch);
      await Promise.all([mutateGlobal(`/conversations/${id}`), mutateGlobal("/conversations")]);
    } catch (e) {
      // A slow answer can outlast the connection although the server finished it:
      // look before reporting a failure.
      const latest = id ? await mutateGlobal<ConversationDetail>(`/conversations/${id}`) : undefined;
      if (latest?.messages.at(-1)?.user_message === message) {
        mutateGlobal("/conversations");
      } else {
        setError(e);
        setDraft(message); // keep what the user typed
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

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      send();
    }
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setDragging(false);
    if (e.dataTransfer.files.length) attach(e.dataTransfer.files);
  }

  const empty = messages.length === 0 && !pending;
  return (
    <div
      className="relative flex h-full min-h-[calc(100vh-3rem)] flex-col md:min-h-screen"
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={(e) => {
        if (e.currentTarget === e.target) setDragging(false);
      }}
      onDrop={onDrop}
    >
      {dragging && (
        <div className="pointer-events-none absolute inset-3 z-20 flex items-center justify-center rounded-2xl border-2 border-dashed border-accent bg-accent-soft/80 text-sm font-medium text-accent">
          Drop PDF, DOCX or TXT files to attach them to this chat
        </div>
      )}

      {/* Header: title + attached documents */}
      <header className="sticky top-0 z-10 border-b border-line bg-surface/90 px-4 py-2.5 backdrop-blur md:px-8">
        <div className="mx-auto flex max-w-3xl flex-wrap items-center gap-2">
          <h1 className="mr-2 truncate text-sm font-semibold">{conversation.data?.title ?? "New chat"}</h1>
          {documents.map((d) => (
            <span key={d.id} className="inline-flex items-center gap-1 rounded-full border border-line bg-surface-2 py-0.5 pr-1 pl-2.5 text-xs">
              {d.kind === "patent" ? (
                <icons.search width={12} height={12} className="text-muted" />
              ) : (
                <icons.file width={12} height={12} className="text-muted" />
              )}
              <span className="max-w-40 truncate" title={d.title ?? d.filename}>{d.title || d.filename}</span>
              <button type="button" onClick={() => detach(d.id)} aria-label={`Remove ${d.filename} from this chat`} className="rounded-full p-0.5 text-muted hover:bg-surface hover:text-bad">
                <icons.x width={11} height={11} />
              </button>
            </span>
          ))}
          {uploading.map((name) => (
            <span key={name} className="inline-flex items-center gap-1.5 rounded-full border border-dashed border-accent/50 px-2.5 py-0.5 text-xs text-accent">
              <Spinner /> {name}
            </span>
          ))}
          <span className="ml-auto text-xs text-muted">
            {documents.length ? `Answers use ${documents.length === 1 ? "this document" : "these documents"}` : liveSearch ? "Answers search your library and the patent databases" : "Answers search your library (and the patent databases if it has no answer)"}
          </span>
        </div>
      </header>

      {/* Thread */}
      <div className="flex-1 px-4 py-6 md:px-8">
        <div className="mx-auto max-w-3xl space-y-8">
          {conversation.isLoading && <Spinner label="Loading conversation…" />}
          {conversation.error && <ErrorNotice error={conversation.error} title="Could not load this conversation" />}

          {empty && !conversation.isLoading && (
            <div className="-mx-4 flex flex-col items-center px-4 pt-10 pb-4 text-center md:pt-16">
              <LogoMark size={44} draw className="text-text" />
              <h2 className="pi-line mt-3 text-[clamp(1.9rem,4vw,2.6rem)] leading-tight">
                <span>
                  {greeting()}
                  {user ? (
                    <>
                      , <span className="text-stamp italic">{user.name.split(" ")[0]}</span>
                    </>
                  ) : null}
                </span>
              </h2>
              <p className="pi-in mt-2 max-w-md text-sm text-muted" style={{ animationDelay: "0.2s" }}>
                Ask about patents and get answers that cite their sources, with every sentence checked.
              </p>

              {documents.length === 0 ? (
                <div className="stagger mt-8 grid w-full max-w-2xl gap-3 sm:grid-cols-3">
                  <button type="button" onClick={() => fileInput.current?.click()} className={ACTION}>
                    <span className={ACTION_ICON}><icons.paperclip /></span>
                    <span className="font-medium">Talk to a patent</span>
                    <span className="text-xs text-muted">Attach a PDF, Word or text file</span>
                  </button>
                  <Link href="/invention" className={ACTION}>
                    <span className={ACTION_ICON}><icons.bulb /></span>
                    <span className="font-medium">Check an idea</span>
                    <span className="text-xs text-muted">See which patents share its features</span>
                  </Link>
                  <Link href="/watches" className={ACTION}>
                    <span className={ACTION_ICON}><icons.bell /></span>
                    <span className="font-medium">Follow a topic</span>
                    <span className="text-xs text-muted">Get new patents as they are published</span>
                  </Link>
                </div>
              ) : (
                <div className="stagger mt-6 flex max-w-xl flex-wrap justify-center gap-2">
                  {(documents.length > 1 ? COMPARE_SUGGESTIONS : DOCUMENT_SUGGESTIONS).map((s) => (
                    <button key={s} type="button" onClick={() => send(s)}
                      className="border border-line bg-surface px-3.5 py-2 text-sm hover:border-text">
                      {s}
                    </button>
                  ))}
                </div>
              )}
              {documents.length === 0 && (
                <p className="pi-in mt-6 text-xs text-muted" style={{ animationDelay: "0.5s" }}>
                  Or just type a question: it searches your <Link href="/documents" className="text-accent hover:underline">library</Link>,
                  and the patent databases when the library has no answer. Try &ldquo;latest patents on battery immersion cooling&rdquo;.
                </p>
              )}
            </div>
          )}

          {messages.map((m, i) => (
            <ChatMessageView key={m.run_id} message={m} index={i} userName={user?.name} />
          ))}

          {pending && (
            <div className="space-y-4">
              <UserBubble text={pending} name={user?.name} />
              <div className="flex gap-3">
                <AssistantAvatar />
                <ScanStatus height={84} stages={liveSearch ? LIVE_STAGES : PENDING_STAGES} className="pi-in min-w-0 flex-1 text-sm" />
              </div>
            </div>
          )}
          {error ? <ErrorNotice error={error} /> : null}
          <div ref={bottom} />
        </div>
      </div>

      {/* Composer */}
      <div className="sticky bottom-0 border-t border-line bg-bg/95 px-4 py-3 backdrop-blur md:px-8">
        <form
          // Reference search-bar look: ink border and hard shadow, both turn blue on focus
          className="mx-auto flex max-w-3xl items-end gap-2 border-[1.5px] border-text bg-surface p-2 shadow-hard transition-[border-color,box-shadow] duration-200 focus-within:border-cite focus-within:[box-shadow:var(--shadow-hard-focus)]"
          onSubmit={(e) => {
            e.preventDefault();
            send();
          }}
        >
          <input ref={fileInput} type="file" accept={ACCEPT} multiple hidden onChange={(e) => e.target.files && attach(e.target.files)} />
          <button type="button" onClick={() => fileInput.current?.click()} aria-label="Attach documents"
            className="rounded-xl p-2 text-muted hover:bg-surface-2 hover:text-accent" title="Attach PDF, DOCX or TXT">
            <icons.paperclip />
          </button>
          <button
            type="button"
            onClick={() => setLiveSearch((v) => !v)}
            aria-pressed={liveSearch}
            aria-label="Search patent databases"
            title={liveSearch
              ? "On: each question also searches the patent databases (EPO) and imports the most relevant patents"
              : "Off: answers come from your library; the patent databases are searched only when it has no answer"}
            className={`flex items-center gap-1 rounded-xl px-2 py-2 text-xs font-medium ${liveSearch ? "bg-accent-soft text-accent" : "text-muted hover:bg-surface-2 hover:text-accent"}`}
          >
            <icons.globe width={16} height={16} />
            <span className="hidden sm:inline">Patent DBs</span>
          </button>
          <textarea
            ref={textarea}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={onKeyDown}
            rows={1}
            maxLength={2000}
            placeholder={documents.length ? "Ask about the attached documents…" : liveSearch ? "Ask anything: patent databases are searched too…" : "Ask about patents…"}
            aria-label="Message"
            className="max-h-40 min-h-[2.5rem] flex-1 resize-none bg-transparent px-1 py-2 text-sm outline-none"
            style={{ height: `${Math.min(160, 40 + Math.max(0, draft.split("\n").length - 1) * 20)}px` }}
          />
          <button type="submit" disabled={!draft.trim() || !!pending} aria-label="Send"
            className="bg-brand p-2 hover:opacity-90 disabled:opacity-40">
            <icons.send />
          </button>
        </form>
        <p className="mx-auto mt-1.5 max-w-3xl text-center text-[11px] text-muted">
          Enter to send · Shift+Enter for a new line · Technical information only, not legal advice.
        </p>
      </div>
    </div>
  );
}
