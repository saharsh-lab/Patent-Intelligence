"use client";

import { AnimatePresence, motion } from "framer-motion";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState, type ReactNode } from "react";
import useSWR from "swr";

import { icons } from "@/components/icons";
import { NEW_SEARCH_EVENT, Wordmark } from "@/components/search/Logo";
import { Spinner } from "@/components/ui";
import { fetcher } from "@/lib/api";
import { auth, initials, useAuth, type User } from "@/lib/auth";
import { chat, groupByRecency, type ConversationSummary } from "@/lib/chat";
import { applyTheme, currentTheme, type Theme } from "@/lib/theme";
import type { HealthReady, WatchOut } from "@/lib/types";

const AUTH_PAGES = ["/login", "/register"];

// Four tools besides chat. Research tools (evaluation, research console, system status)
// live in the user menu: they are for the project team, not everyday use.
const TOOLS = [
  { href: "/search", label: "Search", icon: icons.search, also: [] },
  { href: "/documents", label: "Library", icon: icons.file, also: ["/patents", "/compare"] },
  { href: "/invention", label: "Invention analysis", icon: icons.bulb, also: [] },
  { href: "/watches", label: "Patent watch", icon: icons.bell, also: [] },
];
const RESEARCH = [
  { href: "/evaluation", label: "Evaluation results", icon: icons.chart },
  { href: "/ask", label: "Research console", icon: icons.flask },
  { href: "/settings", label: "System status", icon: icons.gear },
];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { status, error, isLoading, user, refresh } = useAuth();
  // The mobile drawer belongs to the page it was opened on: navigating closes it
  const [drawerFor, setDrawerFor] = useState<string | null>(null);
  const drawer = drawerFor === pathname;
  const setDrawer = (open: boolean) => setDrawerFor(open ? pathname : null);

  const isAuthPage = AUTH_PAGES.includes(pathname);
  const mustLogin = status?.auth_required && !status.authenticated;

  useEffect(() => {
    if (!isAuthPage && mustLogin) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    }
  }, [isAuthPage, mustLogin, pathname, router]);

  // Theme from the profile wins over this browser's last choice
  useEffect(() => {
    const preferred = user?.preferences.theme;
    if (preferred) applyTheme(preferred);
  }, [user?.preferences.theme]);

  if (isAuthPage) {
    return <main className="pi-grid flex min-h-screen items-center justify-center px-4 py-10">{children}</main>;
  }
  if (isLoading || mustLogin) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spinner label={mustLogin ? "Redirecting to login…" : "Loading…"} />
      </div>
    );
  }

  // Chat and search fill the content area themselves (no padded wrapper or footer)
  const isChat = pathname === "/" || pathname.startsWith("/chat") || pathname.startsWith("/search");
  return (
    <div className="flex h-screen overflow-hidden bg-bg">
      {/* Mobile top bar */}
      <div className="fixed inset-x-0 top-0 z-30 flex h-12 items-center gap-2 border-b border-line bg-surface/95 px-3 backdrop-blur md:hidden">
        <button type="button" onClick={() => setDrawer(true)} aria-label="Open menu" className="rounded-lg p-1.5 hover:bg-surface-2">
          <icons.menu />
        </button>
        <Brand compact />
        <Link href="/chat" aria-label="New chat" className="ml-auto rounded-lg p-1.5 text-accent hover:bg-surface-2">
          <icons.plus />
        </Link>
      </div>

      <AnimatePresence>
        {drawer && (
          <motion.div
            className="fixed inset-0 z-40 bg-[#16233a]/30 md:hidden"
            onClick={() => setDrawer(false)}
            aria-hidden
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          />
        )}
      </AnimatePresence>
      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-line bg-sidebar transition-transform duration-300 ease-[cubic-bezier(0.2,0.8,0.2,1)] md:static md:z-auto md:w-64 md:translate-x-0 ${
          drawer ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between px-4 pt-4 pb-3">
          <Brand />
          <button type="button" onClick={() => setDrawer(false)} aria-label="Close menu" className="rounded-lg p-1 hover:bg-surface-2 md:hidden">
            <icons.x />
          </button>
        </div>
        <div className="px-3">
          <Link
            href="/chat"
            className="press flex items-center justify-center gap-2 bg-brand px-3 py-2 text-sm font-medium hover:opacity-90"
          >
            <icons.plus width={16} height={16} /> New chat
          </Link>
        </div>

        <nav className="mt-3 flex-1 space-y-4 overflow-y-auto px-2 pb-3" aria-label="Main">
          <Conversations pathname={pathname} />
          <ToolsNav pathname={pathname} />
        </nav>

        <UserMenu user={user} authRequired={!!status?.auth_required} onLoggedOut={() => refresh()} />
        {error ? <p className="px-4 pb-2 text-xs text-bad">Account service unreachable</p> : null}
      </aside>

      <div className="pi-grid flex min-w-0 flex-1 flex-col overflow-y-auto pt-12 md:pt-0">
        {isChat ? (
          children
        ) : (
          <>
            <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 md:px-8">{children}</main>
            <footer className="border-t border-line px-4 py-3 text-xs text-muted md:px-8">
              Research assistance only: reports technical similarity and evidence from sources. Not legal advice; does
              not assess patent validity or infringement.
            </footer>
          </>
        )}
      </div>
    </div>
  );
}

function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <Link
      href="/search"
      // Already on /search, a link to the same URL would change nothing: ask the
      // search page to return to its start screen, like the logo in its top bar
      onClick={() => window.dispatchEvent(new Event(NEW_SEARCH_EVENT))}
      className="rounded-lg"
    >
      <Wordmark compact={compact} draw />
    </Link>
  );
}

function ToolsNav({ pathname }: { pathname: string }) {
  const watches = useSWR<WatchOut[]>("/watches", fetcher, { shouldRetryOnError: false });
  const unseen = (watches.data ?? []).reduce((n, w) => n + w.unseen, 0);
  return (
    <ul className="stagger space-y-0.5 border-t border-line pt-3">
      {TOOLS.map(({ href, label, icon: Icon, also }) => {
        const active = pathname.startsWith(href) || also.some((p) => pathname.startsWith(p));
        return (
          <li key={href}>
            <Link
              href={href}
              className={`group relative flex items-center gap-2.5 px-2 py-1.5 text-sm ${
                active ? "font-medium text-accent" : "text-text hover:bg-surface-2"
              }`}
            >
              {active && <ActiveMarker />}
              <Icon width={16} height={16} className="relative transition-transform duration-200 group-hover:translate-x-0.5" />
              <span className="relative flex-1">{label}</span>
              {href === "/watches" && unseen > 0 && (
                <span className="pi-cite relative rounded-full bg-stamp px-1.5 text-[11px] font-semibold text-white">{unseen}</span>
              )}
            </Link>
          </li>
        );
      })}
    </ul>
  );
}

function Conversations({ pathname }: { pathname: string }) {
  const router = useRouter();
  const { data, mutate } = useSWR<ConversationSummary[]>("/conversations", fetcher, { shouldRetryOnError: false });
  const [editing, setEditing] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  if (!data || data.length === 0) {
    return (
      <div>
        <p className="px-2 pb-1 text-[11px] font-semibold tracking-wider text-muted uppercase">Chats</p>
        <p className="px-2 text-xs text-muted">{data ? "Your conversations will appear here." : ""}</p>
      </div>
    );
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
          <p className="px-2 pb-1 text-[11px] font-semibold tracking-wider text-muted uppercase">{label}</p>
          <ul className="stagger space-y-0.5">
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
                      className="w-full rounded-lg border border-accent bg-surface px-2 py-1.5 text-sm"
                      aria-label="Conversation title"
                    />
                  ) : (
                    <Link
                      href={`/chat/${c.id}`}
                      className={`relative flex items-center gap-2 py-1.5 pr-14 pl-2 text-sm ${
                        active ? "font-medium text-accent" : "hover:bg-surface-2"
                      }`}
                      title={c.title}
                    >
                      {active && <ActiveMarker />}
                      <icons.chat width={15} height={15} className="relative shrink-0 opacity-60" />
                      <span className="relative truncate">{c.title}</span>
                    </Link>
                  )}
                  {editing !== c.id && (
                    <span className="absolute top-1/2 right-1 hidden -translate-y-1/2 gap-0.5 group-hover:flex group-focus-within:flex">
                      <button
                        type="button"
                        aria-label={`Rename ${c.title}`}
                        className="rounded p-1 text-muted hover:bg-surface hover:text-text"
                        onClick={() => {
                          setEditing(c.id);
                          setTitle(c.title);
                        }}
                      >
                        <icons.pencil width={13} height={13} />
                      </button>
                      <button
                        type="button"
                        aria-label={`Delete ${c.title}`}
                        className="rounded p-1 text-muted hover:bg-surface hover:text-bad"
                        onClick={() => remove(c.id)}
                      >
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

function UserMenu({ user, authRequired, onLoggedOut }: { user: User | null; authRequired: boolean; onLoggedOut: () => void }) {
  const [open, setOpen] = useState(false);
  // Only shown after a click, so reading localStorage lazily is hydration-safe
  const [theme, setTheme] = useState<Theme>(() => (typeof window === "undefined" ? "system" : currentTheme()));
  const ref = useRef<HTMLDivElement>(null);
  const router = useRouter();

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && setOpen(false);
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [open]);

  function chooseTheme(next: Theme) {
    setTheme(next);
    applyTheme(next);
    if (user) auth.updateProfile({ preferences: { theme: next } }).catch(() => undefined);
  }

  async function logout() {
    await auth.logout().catch(() => undefined);
    onLoggedOut();
    router.replace("/login");
  }

  const name = user?.name ?? (authRequired ? "" : "Local user");
  return (
    <div ref={ref} className="relative border-t border-line p-2">
      <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0, y: 8, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 6, scale: 0.98, transition: { duration: 0.12 } }}
          transition={{ type: "spring", stiffness: 420, damping: 32 }}
          style={{ transformOrigin: "bottom center" }}
          className="absolute right-2 bottom-full left-2 mb-2 border border-line bg-surface p-2 shadow-hard"
          role="menu"
        >
          <div className="px-2 pt-1 pb-2">
            <p className="text-sm font-medium">{name}</p>
            {user && <p className="truncate text-xs text-muted">{user.email}</p>}
          </div>
          <p className="px-2 pt-1 text-[11px] font-semibold tracking-wider text-muted uppercase">Theme</p>
          <div className="m-1 grid grid-cols-3 gap-1 rounded-lg bg-surface-2 p-1" role="radiogroup" aria-label="Theme">
            {(["light", "system", "dark"] as Theme[]).map((t) => (
              <button
                key={t}
                type="button"
                role="radio"
                aria-checked={theme === t}
                onClick={() => chooseTheme(t)}
                className={`flex items-center justify-center gap-1 rounded-md py-1 text-xs capitalize ${
                  theme === t ? "bg-surface font-medium shadow-card" : "text-muted hover:text-text"
                }`}
              >
                {t === "light" ? <icons.sun width={13} height={13} /> : t === "dark" ? <icons.moon width={13} height={13} /> : null}
                {t}
              </button>
            ))}
          </div>
          <Link href="/profile" className="mt-1 flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm hover:bg-surface-2" role="menuitem">
            <icons.user width={15} height={15} /> Profile &amp; preferences
          </Link>
          <p className="mt-2 px-2 pt-1 text-[11px] font-semibold tracking-wider text-muted uppercase">Research tools</p>
          {RESEARCH.map(({ href, label, icon: Icon }) => (
            <Link key={href} href={href} className="flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm hover:bg-surface-2" role="menuitem">
              <Icon width={15} height={15} /> {label}
            </Link>
          ))}
          {user && (
            <button type="button" onClick={logout} className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-sm text-bad hover:bg-bad-soft" role="menuitem">
              <icons.logout width={15} height={15} /> Log out
            </button>
          )}
        </motion.div>
      )}
      </AnimatePresence>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-haspopup="menu"
        className="flex w-full items-center gap-2.5 rounded-lg px-2 py-2 text-left hover:bg-surface-2"
      >
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-accent-soft text-xs font-semibold text-accent">
          {user ? initials(user.name) : <icons.user width={15} height={15} />}
        </span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-medium">{name}</span>
          <BackendStatus />
        </span>
      </button>
    </div>
  );
}

function BackendStatus() {
  const { data, error } = useSWR<HealthReady>("/health/ready", fetcher, { refreshInterval: 30_000, shouldRetryOnError: false });
  const ok = data?.status === "ready";
  const label = error ? "Backend unreachable" : !data ? "Checking…" : ok ? "Connected" : "Database down";
  return (
    <span className="flex items-center gap-1.5 text-[11px] text-muted" title={label}>
      <span className={`h-1.5 w-1.5 rounded-full ${error || (data && !ok) ? "bg-bad" : ok ? "bg-ok" : "bg-line-strong"}`} />
      {label}
    </span>
  );
}

/** The highlight behind the current nav item; it slides between items (shared layout). */
function ActiveMarker() {
  return (
    <motion.span
      layoutId="nav-active"
      transition={{ type: "spring", stiffness: 420, damping: 36 }}
      className="absolute inset-0 border-l-[3px] border-cite bg-accent-soft"
      aria-hidden
    />
  );
}
