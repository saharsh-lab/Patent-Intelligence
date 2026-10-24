"use client";

import { AnimatePresence, motion } from "framer-motion";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState, type ReactNode } from "react";
import useSWR from "swr";

import { icons } from "@/components/icons";
import { Wordmark } from "@/components/search/Logo";
import { Spinner } from "@/components/ui";
import { fetcher } from "@/lib/api";
import { auth, initials, useAuth, type User } from "@/lib/auth";
import { applyTheme, currentTheme, type Theme } from "@/lib/theme";
import type { HealthReady, WatchOut } from "@/lib/types";

const AUTH_PAGES = ["/login", "/register"];
const PUBLIC_PAGES = ["/", ...AUTH_PAGES]; // the landing page needs no account

// The floating navigation bar (after the reference site): chat, which is also where you
// search, and the four tools. Research tools (evaluation, research console, system
// status) live in the account menu: they are for the project team, not everyday use.
const NAV = [
  { href: "/chat", label: "Chat", also: ["/search"] },
  { href: "/documents", label: "Library", also: ["/patents", "/compare"] },
  { href: "/invention", label: "Invention", also: [] },
  { href: "/landscape", label: "Landscape", also: [] },
  { href: "/checker", label: "Checker", also: [] },
  { href: "/watches", label: "Watch", also: [] },
];
const RESEARCH = [
  { href: "/evaluation", label: "Evaluation results", icon: icons.chart },
  { href: "/ask", label: "Research console", icon: icons.flask },
  { href: "/settings", label: "System status", icon: icons.gear },
];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { status, isLoading, user, refresh } = useAuth();

  const isPublic = PUBLIC_PAGES.includes(pathname);
  const mustLogin = status?.auth_required && !status.authenticated;

  useEffect(() => {
    if (!isPublic && mustLogin) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    }
  }, [isPublic, mustLogin, pathname, router]);

  // Theme from the profile wins over this browser's last choice
  useEffect(() => {
    const preferred = user?.preferences.theme;
    if (preferred) applyTheme(preferred);
  }, [user?.preferences.theme]);

  const isChat = pathname.startsWith("/chat") || pathname.startsWith("/search");
  // Signed in, or a single-user installation without accounts (only then may it load data)
  const signedIn = !!status && (!status.auth_required || status.authenticated);
  const nav = <TopNav pathname={pathname} user={user} signedIn={signedIn} authRequired={!!status?.auth_required} onLoggedOut={() => refresh()} />;

  if (!isPublic && (isLoading || mustLogin)) {
    return (
      <div className="pi-grid flex min-h-screen items-center justify-center">
        <Spinner label={mustLogin ? "Redirecting to login…" : "Loading…"} />
      </div>
    );
  }
  if (isPublic) {
    return (
      <div className="pi-grid min-h-screen">
        {nav}
        {children}
      </div>
    );
  }
  return (
    <div className="pi-grid flex min-h-screen flex-col">
      {nav}
      {isChat ? (
        // The chat lays out its own columns and fills the window under the bar
        <main className="mx-auto w-full max-w-[1440px] flex-1 px-3 pt-4 pb-3 md:px-6">{children}</main>
      ) : (
        <>
          <main className="mx-auto w-full max-w-7xl flex-1 px-4 pt-8 pb-10 md:px-8">{children}</main>
          <footer className="px-4 pb-6 text-center text-xs text-muted md:px-8">
            Research assistance only: reports technical similarity and evidence from sources. Not legal advice; does
            not assess patent validity or infringement.
          </footer>
        </>
      )}
    </div>
  );
}

function TopNav({
  pathname,
  user,
  signedIn,
  authRequired,
  onLoggedOut,
}: {
  pathname: string;
  user: User | null;
  signedIn: boolean;
  authRequired: boolean;
  onLoggedOut: () => void;
}) {
  const [menuFor, setMenuFor] = useState<string | null>(null); // the phone menu closes on navigation
  const menu = menuFor === pathname;
  // Only when signed in: an unauthorised request sends the browser to the login page
  const watches = useSWR<WatchOut[]>(signedIn ? "/watches" : null, fetcher, { shouldRetryOnError: false });
  const unseen = (watches.data ?? []).reduce((n, w) => n + w.unseen, 0);
  const signedOut = !signedIn;

  const links = NAV.map(({ href, label, also }) => {
    const active = pathname.startsWith(href) || also.some((p) => pathname.startsWith(p));
    return { href, label, active, dot: href === "/watches" && unseen > 0 };
  });

  return (
    <header className="sticky top-0 z-40 px-3 pt-3 md:px-6 md:pt-4">
      <nav
        aria-label="Main"
        className="relative mx-auto flex h-14 max-w-6xl items-center gap-3 rounded-full border border-line bg-nav pr-2 pl-3 shadow-card backdrop-blur-md md:h-16 md:pr-3 md:pl-4"
      >
        <Link href={signedOut ? "/" : "/chat"} className="shrink-0 rounded-lg" aria-label="Patent Intelligence">
          <Wordmark draw />
        </Link>
        <ul className="mx-auto hidden items-center gap-1 lg:flex">
          {links.map(({ href, label, active, dot }) => (
            <li key={href}>
              <Link
                href={href}
                aria-current={active ? "page" : undefined}
                className={`relative rounded-full px-3.5 py-2 text-sm font-medium transition-colors ${active ? "text-accent" : "text-muted hover:text-text"}`}
              >
                {label}
                {dot && <span className="absolute top-1.5 right-1.5 h-1.5 w-1.5 rounded-full bg-stamp" aria-label={`${unseen} new`} />}
              </Link>
            </li>
          ))}
        </ul>
        <div className="ml-auto flex items-center gap-2 lg:ml-0">
          <ThemeMenu user={user} />
          {signedOut ? (
            <Link href="/login" className="press rounded-full bg-brand px-5 py-2 text-sm font-semibold whitespace-nowrap hover:opacity-90">
              Sign in
            </Link>
          ) : (
            <AccountMenu user={user} authRequired={authRequired} onLoggedOut={onLoggedOut} />
          )}
          <button
            type="button"
            onClick={() => setMenuFor(menu ? null : pathname)}
            aria-label={menu ? "Close menu" : "Open menu"}
            aria-expanded={menu}
            className="grid h-10 w-10 place-items-center rounded-full border border-line hover:bg-surface-2 lg:hidden"
          >
            {menu ? <icons.x width={18} height={18} /> : <icons.menu width={18} height={18} />}
          </button>
        </div>

        <AnimatePresence>
          {menu && (
            <motion.ul
              initial={{ opacity: 0, y: -6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6, transition: { duration: 0.12 } }}
              className="absolute inset-x-0 top-full mt-2 space-y-0.5 rounded-3xl border border-line bg-surface p-2 shadow-hard lg:hidden"
            >
              {links.map(({ href, label, active, dot }) => (
                <li key={href}>
                  <Link
                    href={href}
                    className={`flex items-center justify-between rounded-2xl px-4 py-3 text-[0.95rem] font-medium ${active ? "bg-accent-soft text-accent" : "hover:bg-surface-2"}`}
                  >
                    {label}
                    {dot && <span className="h-2 w-2 rounded-full bg-stamp" />}
                  </Link>
                </li>
              ))}
            </motion.ul>
          )}
        </AnimatePresence>
      </nav>
    </header>
  );
}

/** Dismiss a popup menu on an outside click or Escape. */
function useDismiss(open: boolean, close: () => void) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && close();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && close();
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open, close]);
  return ref;
}

const POPUP = "absolute right-0 top-full z-50 mt-3 rounded-2xl border border-line bg-surface p-1.5 shadow-hard";
const pop = {
  initial: { opacity: 0, y: -4, scale: 0.98 },
  animate: { opacity: 1, y: 0, scale: 1 },
  exit: { opacity: 0, y: -4, scale: 0.98, transition: { duration: 0.1 } },
  transition: { type: "spring" as const, stiffness: 460, damping: 32 },
};

/** The reference's round theme button with a Light / Dark / System menu. */
function ThemeMenu({ user }: { user: User | null }) {
  const [open, setOpen] = useState(false);
  // Read lazily on the first click: hydration-safe (the server cannot know it)
  const [theme, setTheme] = useState<Theme | null>(null);
  const ref = useDismiss(open, () => setOpen(false));
  const shown = theme ?? "dark";

  function choose(next: Theme) {
    setTheme(next);
    applyTheme(next);
    setOpen(false);
    if (user) auth.updateProfile({ preferences: { theme: next } }).catch(() => undefined);
  }

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        aria-label="Theme"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => {
          if (theme === null) setTheme(currentTheme());
          setOpen((o) => !o);
        }}
        className="grid h-10 w-10 place-items-center rounded-full border border-line-strong bg-bg text-text hover:bg-surface-2"
      >
        <icons.moon width={17} height={17} className="theme-dark-only" />
        <icons.sun width={17} height={17} className="theme-light-only" />
      </button>
      <AnimatePresence>
        {open && (
          <motion.div {...pop} className={`${POPUP} w-40`} role="menu" style={{ transformOrigin: "top right" }}>
            {(
              [
                ["light", "Light", icons.sun],
                ["dark", "Dark", icons.moon],
                ["system", "System", icons.monitor],
              ] as const
            ).map(([value, label, Icon]) => (
              <button
                key={value}
                type="button"
                role="menuitemradio"
                aria-checked={shown === value}
                onClick={() => choose(value)}
                className="flex w-full items-center gap-2.5 rounded-xl px-3 py-2 text-left text-sm hover:bg-surface-2"
              >
                <Icon width={15} height={15} className="text-muted" />
                <span className="flex-1">{label}</span>
                {shown === value && <icons.check width={14} height={14} />}
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function AccountMenu({ user, authRequired, onLoggedOut }: { user: User | null; authRequired: boolean; onLoggedOut: () => void }) {
  const [open, setOpen] = useState(false);
  const ref = useDismiss(open, () => setOpen(false));
  const router = useRouter();

  async function logout() {
    await auth.logout().catch(() => undefined);
    onLoggedOut();
    router.replace("/login");
  }

  const name = user?.name ?? (authRequired ? "" : "Local user");
  const item = "flex w-full items-center gap-2.5 rounded-xl px-3 py-2 text-left text-sm hover:bg-surface-2";
  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-haspopup="menu"
        aria-label="Account"
        className="flex h-10 items-center gap-2 rounded-full bg-brand py-1 pr-4 pl-1 text-sm font-semibold hover:opacity-90"
      >
        <span className="grid h-8 w-8 place-items-center rounded-full bg-accent text-xs font-bold text-white">
          {user ? initials(user.name) : <icons.user width={15} height={15} />}
        </span>
        <span className="hidden max-w-28 truncate sm:inline">{name.split(" ")[0] || "Account"}</span>
      </button>
      <AnimatePresence>
        {open && (
          <motion.div {...pop} className={`${POPUP} w-64`} role="menu" style={{ transformOrigin: "top right" }}>
            <div className="px-3 pt-2 pb-2.5">
              <p className="text-sm font-semibold">{name}</p>
              {user && <p className="truncate text-xs text-muted">{user.email}</p>}
              <BackendStatus />
            </div>
            <div className="border-t border-line pt-1.5">
              <Link href="/profile" className={item} role="menuitem" onClick={() => setOpen(false)}>
                <icons.user width={15} height={15} className="text-muted" /> Profile &amp; preferences
              </Link>
            </div>
            <p className="px-3 pt-2.5 pb-1 text-[11px] font-semibold tracking-wider text-muted uppercase">Research tools</p>
            {RESEARCH.map(({ href, label, icon: Icon }) => (
              <Link key={href} href={href} className={item} role="menuitem" onClick={() => setOpen(false)}>
                <Icon width={15} height={15} className="text-muted" /> {label}
              </Link>
            ))}
            {user && (
              <div className="mt-1.5 border-t border-line pt-1.5">
                <button type="button" onClick={logout} className={`${item} text-bad hover:bg-bad-soft`} role="menuitem">
                  <icons.logout width={15} height={15} /> Log out
                </button>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function BackendStatus() {
  const { data, error } = useSWR<HealthReady>("/health/ready", fetcher, { refreshInterval: 30_000, shouldRetryOnError: false });
  const ok = data?.status === "ready";
  const label = error ? "Backend unreachable" : !data ? "Checking…" : ok ? "Connected" : "Database down";
  return (
    <span className="mt-1.5 flex items-center gap-1.5 text-[11px] text-muted" title={label}>
      <span className={`h-1.5 w-1.5 rounded-full ${error || (data && !ok) ? "bg-bad" : ok ? "bg-ok" : "bg-line-strong"}`} />
      {label}
    </span>
  );
}
