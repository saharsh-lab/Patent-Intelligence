"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  { href: "/documents", label: "My documents", text: "Upload patents and drafts. Each file is split into sections and claims so answers can cite them precisely." },
  { href: "/patents", label: "Find patents", text: "Search patent databases and add patents to your library. Results show technical relevance only." },
  { href: "/compare", label: "Compare", text: "Put 2–4 documents side by side, aspect by aspect. Every cell cites its own source." },
];

/** One "Library" page with three tabs, instead of three separate menu entries. */
export function LibraryHeader() {
  const pathname = usePathname();
  const current = TABS.find((t) => pathname.startsWith(t.href)) ?? TABS[0];
  return (
    <header className="mb-6">
      <h1 className="text-xl font-semibold tracking-tight">Library</h1>
      <nav aria-label="Library" className="mt-3 flex gap-1 border-b border-line">
        {TABS.map((t) => (
          <Link
            key={t.href}
            href={t.href}
            aria-current={t === current ? "page" : undefined}
            className={`-mb-px border-b-2 px-3 py-2 text-sm ${
              t === current ? "border-accent font-medium text-accent" : "border-transparent text-muted hover:text-text"
            }`}
          >
            {t.label}
          </Link>
        ))}
      </nav>
      <p className="mt-3 max-w-3xl text-sm text-muted">{current.text}</p>
    </header>
  );
}
