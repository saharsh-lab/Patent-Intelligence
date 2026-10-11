"use client";

import { useEffect, useMemo, useState } from "react";
import useSWR from "swr";

import { Badge, Button, ErrorNotice, Panel } from "@/components/ui";
import { ApiError, fetcher, parseError } from "@/lib/api";
import type { DocumentOut, LandscapeOut, LandscapePoint } from "@/lib/types";

const SIZE = 1000;
const PAD = 70;
const colour = (cluster: number | null | undefined) => `var(--map-${((cluster ?? 0) % 6) + 1})`;
const at = (v: number) => PAD + ((v + 1) / 2) * (SIZE - 2 * PAD);

function star(cx: number, cy: number, outer = 26, inner = 11) {
  return Array.from({ length: 10 }, (_, i) => {
    const r = i % 2 ? inner : outer;
    const a = (Math.PI / 5) * i - Math.PI / 2;
    return `${cx + r * Math.cos(a)},${cy + r * Math.sin(a)}`;
  }).join(" ");
}

const EXAMPLES = ["battery immersion cooling", "wireless charging foreign object detection", "solid state battery electrolyte"];

export function LandscapeWorkspace() {
  const documents = useSWR<DocumentOut[]>("/documents", fetcher);
  const ready = (documents.data ?? []).filter((d) => d.status === "ready");

  const [keywords, setKeywords] = useState("");
  const [invention, setInvention] = useState("");
  const [documentId, setDocumentId] = useState("");
  const [includeLibrary, setIncludeLibrary] = useState(true);
  const [limit, setLimit] = useState(60);
  const [pending, setPending] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState<unknown>(null);
  const [map, setMap] = useState<LandscapeOut | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [focusCluster, setFocusCluster] = useState<number | null>(null);

  useEffect(() => {
    if (!pending) return;
    const started = Date.now();
    const timer = setInterval(() => setElapsed(Math.floor((Date.now() - started) / 1000)), 500);
    return () => {
      clearInterval(timer);
      setElapsed(0);
    };
  }, [pending]);

  async function draw(topic = keywords) {
    if (topic.trim().length < 2 || pending) return;
    setKeywords(topic);
    setPending(true);
    setError(null);
    try {
      const response = await fetch("/api/landscape", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          keywords: topic.trim(),
          invention: invention.trim() || null,
          document_id: documentId || null,
          include_library: includeLibrary,
          limit,
        }),
      });
      if (!response.ok) throw await parseError(response);
      const body: LandscapeOut = await response.json();
      setMap(body);
      setFocusCluster(null);
      setSelected(body.points.find((p) => p.closest)?.key ?? null);
    } catch (e) {
      setError(e instanceof ApiError ? e : new Error("The map could not be drawn."));
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="space-y-6">
      <Panel title="What to map">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            draw();
          }}
          className="space-y-3"
        >
          <label className="block text-sm">
            <span className="font-medium">Technology area</span>
            <input
              value={keywords}
              onChange={(e) => setKeywords(e.target.value)}
              placeholder="e.g. battery immersion cooling"
              maxLength={200}
              className="mt-1 w-full rounded border border-line-strong bg-surface px-3 py-2 text-sm"
            />
          </label>
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="text-muted">Try:</span>
            {EXAMPLES.map((e) => (
              <button key={e} type="button" onClick={() => draw(e)} className="text-accent hover:underline" disabled={pending}>
                {e}
              </button>
            ))}
          </div>
          <label className="block text-sm">
            <span className="font-medium">Your invention</span> <span className="text-muted">(optional: drawn as a star, with its five closest patents)</span>
            <textarea
              value={invention}
              onChange={(e) => setInvention(e.target.value)}
              rows={2}
              maxLength={4000}
              placeholder="Describe it in a sentence or two"
              className="mt-1 w-full rounded border border-line-strong bg-surface px-3 py-2 text-sm"
            />
          </label>
          <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-sm">
            <label className="flex items-center gap-1.5">
              <span className="text-muted">or a document:</span>
              <select value={documentId} onChange={(e) => setDocumentId(e.target.value)} className="max-w-56 rounded border border-line-strong bg-surface px-2 py-1 text-xs">
                <option value="">— none —</option>
                {ready.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.title || d.filename}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex items-center gap-1.5">
              <input type="checkbox" checked={includeLibrary} onChange={(e) => setIncludeLibrary(e.target.checked)} />
              Show my library on the map
            </label>
            <label className="flex items-center gap-1.5">
              <span className="text-muted">patents:</span>
              <select value={limit} onChange={(e) => setLimit(Number(e.target.value))} className="rounded border border-line-strong bg-surface px-2 py-1 text-xs">
                {[30, 60, 100].map((n) => (
                  <option key={n}>{n}</option>
                ))}
              </select>
            </label>
            <Button type="submit" className="ml-auto" disabled={pending || keywords.trim().length < 2}>
              {pending ? `Drawing… ${elapsed} s` : "Draw the map"}
            </Button>
          </div>
        </form>
      </Panel>

      {error ? <ErrorNotice error={error} title="Could not draw the map" /> : null}
      {map && <LandscapeView map={map} selected={selected} onSelect={setSelected} focusCluster={focusCluster} onFocusCluster={setFocusCluster} />}
    </div>
  );
}

function LandscapeView({
  map,
  selected,
  onSelect,
  focusCluster,
  onFocusCluster,
}: {
  map: LandscapeOut;
  selected: string | null;
  onSelect: (key: string | null) => void;
  focusCluster: number | null;
  onFocusCluster: (c: number | null) => void;
}) {
  const point = map.points.find((p) => p.key === selected) ?? null;
  const closest = useMemo(
    () => map.points.filter((p) => p.closest).sort((a, b) => (b.similarity ?? 0) - (a.similarity ?? 0)),
    [map.points],
  );
  const patents = map.points.filter((p) => p.kind === "patent").length;
  const dim = (p: LandscapePoint) => focusCluster !== null && p.cluster !== focusCluster;
  const sx = map.invention ? at(map.invention.x) : 0;
  const sy = map.invention ? at(-map.invention.y) : 0;

  return (
    <div className="grid grid-cols-[minmax(0,1fr)] gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
      <figure className="min-w-0">
        <div className="border border-line bg-surface">
          <svg viewBox={`0 0 ${SIZE} ${SIZE}`} className="block h-auto w-full" role="img" aria-label={`Map of ${map.points.length} documents in ${map.clusters.length} groups`}>
            {map.invention &&
              closest.map((p) => (
                <line key={`l-${p.key}`} x1={sx} y1={sy} x2={at(p.x)} y2={at(-p.y)} stroke="var(--text)" strokeOpacity={0.35} strokeWidth={2} strokeDasharray="6 7" className="lm-line" />
              ))}
            {map.points.map((p, i) => {
              const x = at(p.x);
              const y = at(-p.y);
              const active = p.key === selected;
              const common = {
                onClick: () => onSelect(active ? null : p.key),
                className: "lm-dot cursor-pointer",
                style: { animationDelay: `${Math.min(i, 60) * 12}ms`, opacity: dim(p) ? 0.15 : 1 },
              };
              return (
                <g key={p.key} {...common}>
                  <title>{`${p.label}: ${p.title}`}</title>
                  {p.closest && <circle cx={x} cy={y} r={20} fill="none" stroke={colour(p.cluster)} strokeWidth={3} strokeOpacity={0.55} />}
                  {p.kind === "patent" ? (
                    <circle cx={x} cy={y} r={active ? 14 : 10} fill={colour(p.cluster)} stroke={active ? "var(--text)" : "var(--surface)"} strokeWidth={active ? 4 : 2} />
                  ) : (
                    <rect x={x - 11} y={y - 11} width={22} height={22} fill="var(--surface)" stroke={colour(p.cluster)} strokeWidth={active ? 6 : 4} />
                  )}
                </g>
              );
            })}
            {map.invention && (
              <g className="lm-star">
                <polygon points={star(sx, sy)} fill="var(--stamp)" stroke="var(--surface)" strokeWidth={3} />
                <text x={sx} y={sy - 36} textAnchor="middle" fontSize={26} fontWeight={600} fill="var(--text)" paintOrder="stroke" stroke="var(--surface)" strokeWidth={6}>
                  {map.invention.label}
                </text>
              </g>
            )}
          </svg>
        </div>
        <figcaption className="mt-2 text-xs text-muted">
          {patents} patents found for “{map.query}” (from {map.found} returned by the patent office)
          {map.points.length > patents ? `, plus ${map.points.length - patents} from your library (squares)` : ""}. Nearby dots describe similar
          technology: positions come from the meaning of each title and abstract, drawn in two dimensions with {map.method}, so distances are
          approximate. Technical similarity only, not a legal assessment.
          {map.notes.length > 0 && ` ${map.notes.join(" ")}`}
        </figcaption>
      </figure>

      <aside className="space-y-4">
        <Panel title="Groups">
          <ul className="space-y-1.5 text-sm">
            {map.clusters.map((c) => (
              <li key={c.id}>
                <button
                  type="button"
                  onClick={() => onFocusCluster(focusCluster === c.id ? null : c.id)}
                  aria-pressed={focusCluster === c.id}
                  className={`flex w-full items-center gap-2 rounded px-1.5 py-1 text-left hover:bg-surface-2 ${focusCluster === c.id ? "bg-surface-2" : ""}`}
                >
                  <span className="h-3 w-3 shrink-0 rounded-full" style={{ background: colour(c.id) }} aria-hidden />
                  <span className="min-w-0 flex-1 leading-snug">{c.name}</span>
                  <span className="font-mono text-xs text-muted">{c.size}</span>
                </button>
              </li>
            ))}
          </ul>
          <p className="mt-2 text-[11px] text-muted">Named by the words most typical of each group. Click to highlight.</p>
        </Panel>

        {point ? <PointCard point={point} hasInvention={!!map.invention} /> : <p className="text-sm text-muted">Click a dot to see the patent.</p>}

        {closest.length > 0 && (
          <Panel title="Closest to your invention">
            <ol className="space-y-1.5 text-sm">
              {closest.map((p) => (
                <li key={p.key}>
                  <button type="button" onClick={() => onSelect(p.key)} className="flex w-full items-baseline gap-2 text-left hover:underline">
                    <span className="font-mono text-xs text-muted">{p.similarity?.toFixed(2)}</span>
                    <span className="min-w-0 flex-1 truncate">{p.title}</span>
                  </button>
                </li>
              ))}
            </ol>
          </Panel>
        )}
      </aside>

      <section className="lg:col-span-2">
        <h3 className="mb-2 font-serif text-lg">Everything on the map</h3>
        <div className="grid gap-4 md:grid-cols-2">
          {map.clusters.map((c) => (
            <div key={c.id} className="border border-line bg-surface px-3 py-2.5">
              <p className="mb-1.5 flex items-center gap-2 text-sm font-medium">
                <span className="h-3 w-3 rounded-full" style={{ background: colour(c.id) }} aria-hidden />
                {c.name}
              </p>
              <ul className="space-y-1 text-sm">
                {map.points
                  .filter((p) => p.cluster === c.id)
                  .map((p) => (
                    <li key={p.key}>
                      <button type="button" onClick={() => onSelect(p.key)} className={`w-full truncate text-left hover:underline ${p.key === selected ? "font-semibold" : ""}`}>
                        <span className="font-mono text-xs text-muted">{p.label}</span> {p.title}
                      </button>
                    </li>
                  ))}
              </ul>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function PointCard({ point, hasInvention }: { point: LandscapePoint; hasInvention: boolean }) {
  return (
    <div className="pi-in border border-line bg-surface px-4 py-3 text-sm">
      <p className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-xs">{point.label}</span>
        {point.kind !== "patent" && <Badge tone="accent">in your library</Badge>}
        {point.kind === "patent" && point.in_library && <Badge tone="accent">imported</Badge>}
        {point.kind === "patent" && <Badge>{point.full_text_likely ? "full text" : "abstract only"}</Badge>}
      </p>
      <p className="mt-1.5 font-serif text-[1.02rem] leading-snug">{point.title}</p>
      <p className="mt-1 text-xs text-muted">
        {[point.applicants.join(", "), point.date && `published ${point.date}`].filter(Boolean).join(" · ")}
      </p>
      {hasInvention && point.similarity != null && (
        <p className="mt-1 text-xs">
          Similarity to your invention: <span className="font-mono">{point.similarity.toFixed(2)}</span>
          {point.closest && <span className="text-stamp"> · one of the five closest</span>}
        </p>
      )}
      {point.abstract && <p className="mt-2 line-clamp-6 text-xs leading-relaxed">{point.abstract}</p>}
      {point.url && (
        <a href={point.url} target="_blank" rel="noopener noreferrer" className="mt-2 inline-block text-xs text-accent hover:underline">
          Espacenet ↗
        </a>
      )}
    </div>
  );
}
