"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState, type ComponentType, type SVGProps } from "react";
import useSWR from "swr";

import { icons } from "@/components/icons";
import { fetcher } from "@/lib/api";
import { chat, groupByRecency, type ConversationSummary } from "@/lib/chat";

type Icon = ComponentType<SVGProps<SVGSVGElement>>;

// Coloured icon tiles, as on the reference site's action cards
export const TILE = {
  blue: "bg-blue-500/15 text-blue-500",
  violet: "bg-violet-500/15 text-violet-500",
  emerald: "bg-emerald-500/15 text-emerald-500",
  amber: "bg-amber-500/15 text-amber-500",
  rose: "bg-rose-500/15 text-rose-500",
  cyan: "bg-cyan-500/15 text-cyan-500",
} as const;

export function IconTile({ icon: Glyph, tone, size = "md" }: { icon: Icon; tone: keyof typeof TILE; size?: "sm" | "md" }) {
  const box = size === "sm" ? "h-8 w-8 rounded-lg" : "h-12 w-12 rounded-2xl";
  return (
    <span className={`grid shrink-0 place-items-center ${box} ${TILE[tone]}`}>
      <Glyph width={size === "sm" ? 16 : 20} height={size === "sm" ? 16 : 20} />
    </span>
  );
}

function ActionCard({ icon, tone, title, subtitle, href, onClick }: { icon: Icon; tone: keyof typeof TILE; title: string; subtitle: string; href?: string; onClick?: () => void }) {
  const body = (
    <>
      <IconTile icon={icon} tone={tone} />
      <span className="min-w-0">
        <span className="block font-semibold tracking-tight">{title}</span>
        <span className="block truncate text-[0.82rem] text-muted">{subtitle}</span>
      </span>
    </>
  );
  const style = "press glass flex w-full items-center gap-4 rounded-3xl px-5 py-4 text-left transition-colors hover:border-line-strong";
  return href ? (
    <Link href={href} className={style}>
      {body}
    </Link>
  ) : (
    <button type="button" onClick={onClick} className={style}>
      {body}
    </button>
  );
}

const QUICK = [
  { href: "/invention", label: "Check an idea", icon: icons.bulb, tone: "emerald" },
  { href: "/checker", label: "Fact-check a text", icon: icons.shield, tone: "violet" },
  { href: "/landscape", label: "Map a field", icon: icons.map, tone: "amber" },
  { href: "/watches", label: "Follow a topic", icon: icons.bell, tone: "rose" },
  { href: "/documents", label: "Your library", icon: icons.file, tone: "cyan" },
] as const;

/** The chat's left column (after the reference's analysis page): start a chat, talk to a
 *  patent, the tools, and the conversation history. */
export function ChatSidebar({ onAttach }: { onAttach: () => void }) {
  return (
    <div className="flex h-full flex-col gap-4">
      <ActionCard href="/chat" icon={icons.plus} tone="blue" title="New chat" subtitle="Ask about any technology or patent" />
      <ActionCard onClick={onAttach} icon={icons.paperclip} tone="violet" title="Talk to a patent" subtitle="Upload a PDF, DOCX or TXT" />
      <section className="glass overflow-hidden rounded-3xl">
        <p className="border-b border-line px-5 pt-4 pb-3 text-[11px] font-semibold tracking-[0.12em] text-muted uppercase">Quick actions</p>
        <ul>
          {QUICK.map(({ href, label, icon, tone }) => (
            <li key={href} className="border-b border-line last:border-b-0">
              <Link href={href} className="flex items-center gap-3 px-5 py-3 text-sm font-medium transition-colors hover:bg-surface-2">
                <IconTile icon={icon} tone={tone} size="sm" />
                {label}
              </Link>
            </li>
          ))}
        </ul>
      </section>
      <section className="glass flex min-h-48 flex-1 flex-col overflow-hidden rounded-3xl">
        <p className="flex items-center gap-2 border-b border-line px-5 pt-4 pb-3 text-[11px] font-semibold tracking-[0.12em] text-muted uppercase">
          <icons.history width={13} height={13} /> Recent chats
        </p>
        <div className="flex-1 overflow-y-auto px-2 py-2">
          <Conversations />
        </div>
      </section>
    </div>
  );
}

function Conversations() {
  const pathname = usePathname();
  const router = useRouter();
  const { data, mutate } = useSWR<ConversationSummary[]>("/conversations", fetcher, { shouldRetryOnError: false });
  const [editing, setEditing] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  if (!data || data.length === 0) {
    return <p className="px-3 py-2 text-xs text-muted">{data ? "Your conversations will appear here." : ""}</p>;
  }

  async function rename(id: string) {
    if (title.trim()) await chat.rename(id, title.trim());
    setEditing(null);
    mutate();
  }

  async function remove(id: string) {
    if (!window.confirm("Delete this conversation? Its messages are removed; your documents are kept.")) return;
    await chat.remove(id);
    await mutate();
    if (pathname === `/chat/${id}`) router.push("/chat");
  }

  return (
    <div className="space-y-3">
      {groupByRecency(data).map(([label, items]) => (
        <div key={label}>
          <p className="px-3 pb-1 text-[11px] font-medium text-muted">{label}</p>
          <ul className="space-y-0.5">
            {items.map((c) => {
              const active = pathname === `/chat/${c.id}`;
              return (
                <li key={c.id} className="group relative">
                  {editing === c.id ? (
                    <input
                      autoFocus
                      value={title}
                      onChange={(e) => setTitle(e.target.value)}
                      onBlur={() => rename(c.id)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") rename(c.id);
                        if (e.key === "Escape") setEditing(null);
                      }}
                      className="w-full rounded-xl border border-accent bg-surface px-3 py-2 text-sm"
                      aria-label="Conversation title"
                    />
                  ) : (
                    <Link
                      href={`/chat/${c.id}`}
                      aria-current={active ? "page" : undefined}
                      className={`flex items-center gap-2 rounded-xl py-2 pr-14 pl-3 text-sm transition-colors ${
                        active ? "bg-accent-soft font-medium text-accent" : "hover:bg-surface-2"
                      }`}
                      title={c.title}
                    >
                      <icons.chat width={14} height={14} className="shrink-0 opacity-60" />
                      <span className="truncate">{c.title}</span>
                    </Link>
                  )}
                  {editing !== c.id && (
                    <span className="absolute top-1/2 right-1.5 hidden -translate-y-1/2 gap-0.5 group-focus-within:flex group-hover:flex">
                      <button
                        type="button"
                        aria-label={`Rename ${c.title}`}
                        className="rounded-lg p-1 text-muted hover:bg-surface hover:text-text"
                        onClick={() => {
                          setEditing(c.id);
                          setTitle(c.title);
                        }}
                      >
                        <icons.pencil width={13} height={13} />
                      </button>
                      <button type="button" aria-label={`Delete ${c.title}`} className="rounded-lg p-1 text-muted hover:bg-surface hover:text-bad" onClick={() => remove(c.id)}>
                        <icons.trash width={13} height={13} />
                      </button>
                    </span>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </div>
  );
}
