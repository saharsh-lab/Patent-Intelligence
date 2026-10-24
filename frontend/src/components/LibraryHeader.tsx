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
    <header className="mb-8">
      <h1 className="pi-line text-3xl tracking-tight md:text-[2.6rem] md:leading-[1.1]">
        <span>Library</span>
      </h1>
      <p className="mt-2 max-w-3xl text-[0.95rem] text-muted">{current.text}</p>
      <nav aria-label="Library" className="mt-5 inline-flex gap-1 rounded-full border border-line bg-surface/60 p-1">
        {TABS.map((t) => (
          <Link
            key={t.href}
            href={t.href}
            aria-current={t === current ? "page" : undefined}
            className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
              t === current ? "bg-brand" : "text-muted hover:text-text"
            }`}
          >
            {t.label}
          </Link>
        ))}
      </nav>
    </header>
  );
}
