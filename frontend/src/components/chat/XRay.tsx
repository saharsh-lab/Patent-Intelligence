"use client";

import { type KeyboardEvent, type ReactNode, useEffect, useState } from "react";

import { parseAnswer, parseInline, stripInterpretation } from "@/lib/citations";
import { formatPercent, locationLabel } from "@/lib/format";
import type { AskResponse, EvidenceOut } from "@/lib/types";
import { type ClaimResult, splitByClaims, type Verification, type VerificationAttempt } from "@/lib/verification";
import {
  answerClaims,
  checkedAgainst,
  countTones,
  type DemoInjection,
  draftHistory,
  highlightShared,
  plantedClaim,
  type Tone,
  TONE_LABEL,
  toneOf,
} from "@/lib/xray";

/** Which sentence is open in the inspector, and whether it came from the first draft. */
export type XRaySelection = { claim: ClaimResult; from: "final" | "draft" } | null;

const METHOD: Record<string, string> = {
  nli: "an NLI entailment model",
  nli_lexical: "an NLI model with a key-word check",
  nli_llm: "an NLI model, then the LLM re-checks flagged sentences",
  llm_judge: "an LLM judge",
  lexical: "word overlap (baseline)",
};

const DOT: Record<Tone, string> = { ok: "bg-ok", warn: "bg-warn", bad: "bg-bad" };
const TEXT: Record<Tone, string> = { ok: "text-ok", warn: "text-warn", bad: "text-bad" };

/** Answer text without clickable chips: in X-ray mode a click selects the sentence. */
function plain(raw: string): ReactNode[] {
  return parseInline(raw).map((part, i) =>
    part.kind === "citation" ? (
      <sup key={i} className="ml-[1px] font-sans text-[0.68em] font-semibold text-cite">
        {part.label.replace(/^E/, "")}
      </sup>
    ) : part.kind === "invalid-citation" ? (
      <span key={i} className="mx-0.5 rounded-sm bg-bad-soft px-1 font-mono text-[11px] text-bad">unverified</span>
    ) : part.kind === "bold" ? (
      <strong key={i}>{part.text}</strong>
    ) : (
      <span key={i}>{part.text}</span>
    ),
  );
}

/** One line of answer text with every checked sentence coloured and clickable. */
export function XRayText({
  raw,
  claims,
  selected,
  onSelect,
  from = "final",
  removed = [],
  planted,
}: {
  raw: string;
  claims: ClaimResult[];
  selected: XRaySelection;
  onSelect: (s: XRaySelection) => void;
  from?: "final" | "draft";
  removed?: ClaimResult[];
  /** The sentence the checker test planted (demo mode) */
  planted?: ClaimResult;
}) {
  return (
    <>
      {splitByClaims(raw, claims).map((segment, i) => {
        const claim = segment.claim;
        if (!claim) return <span key={i}>{plain(segment.text)}</span>;
        const tone = toneOf(claim);
        const active = selected?.claim === claim;
        const choose = () => onSelect(active ? null : { claim, from });
        const key = (e: KeyboardEvent) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            choose();
          }
        };
        return (
          <span
            key={i}
            role="button"
            tabIndex={0}
            aria-pressed={active}
            aria-label={`${TONE_LABEL[tone]}: ${claim.text}`}
            onClick={choose}
            onKeyDown={key}
            className={`xr-sentence xr-${tone} ${active ? "xr-selected" : ""} ${removed.includes(claim) ? "line-through decoration-bad" : ""}`}
            style={{ transitionDelay: `${Math.min(claim.index, 12) * 70}ms` }}
          >
            {plain(segment.text)}
            {claim === planted && (
              <span className="ml-1 rounded-sm bg-stamp px-1 align-[0.15em] font-sans text-[0.62rem] font-semibold tracking-wide text-white uppercase no-underline">
                planted
              </span>
            )}
          </span>
        );
      })}
    </>
  );
}

/** Answer blocks (paragraphs, lists) in X-ray colours. */
function XRayBlocks({ text, ...rest }: { text: string } & Omit<Parameters<typeof XRayText>[0], "raw">) {
  return (
    <div className="space-y-2">
      {parseAnswer(stripInterpretation(text)).map((block, i) =>
        block.kind === "list" ? (
          <ul key={i} className="list-disc space-y-1 pl-5 marker:text-cite">
            {block.raws.map((raw, j) => (
              <li key={j}>
                <XRayText raw={raw} {...rest} />
              </li>
            ))}
          </ul>
        ) : (
          <p key={i}>
            <XRayText raw={block.raw} {...rest} />
          </p>
        ),
      )}
    </div>
  );
}

/** The passage with the words it shares with the sentence marked. */
function Passage({ item, sentence }: { item: EvidenceOut; sentence: string }) {
  const [full, setFull] = useState(false);
  const long = item.text.length > 700;
  const text = full || !long ? item.text : `${item.text.slice(0, 700)}…`;
  return (
    <div className="border border-line bg-surface px-3 py-2.5">
      <p className="flex flex-wrap items-baseline gap-x-2 text-xs">
        <span className="font-serif text-[0.95rem] text-stamp italic">Fig. {item.label?.replace(/^E/, "")}</span>
        <span className="font-medium">{locationLabel(item)}</span>
        {item.source_url && (
          <a href={item.source_url} target="_blank" rel="noopener noreferrer" className="ml-auto text-accent hover:underline">
            Open original ↗
          </a>
        )}
      </p>
      <p className="mt-1.5 text-sm leading-relaxed whitespace-pre-line">
        {highlightShared(text, sentence).map((piece, i) =>
          piece.shared ? (
            <mark key={i} className="rounded-sm bg-accent-soft px-[1px] text-text">
              {piece.text}
            </mark>
          ) : (
            <span key={i}>{piece.text}</span>
          ),
        )}
      </p>
      {long && (
        <button type="button" onClick={() => setFull(!full)} className="mt-1 text-xs text-accent hover:underline">
          {full ? "Show less" : "Show the whole passage"}
        </button>
      )}
    </div>
  );
}

function Inspector({
  selection,
  evidence,
  onCite,
  injection,
}: {
  selection: NonNullable<XRaySelection>;
  evidence: EvidenceOut[];
  onCite: (label: string) => void;
  injection?: DemoInjection | null;
}) {
  const { claim, from } = selection;
  const tone = toneOf(claim);
  const labels = checkedAgainst(claim);
  const passages = labels.map((l) => evidence.find((e) => e.label === l)).filter((e): e is EvidenceOut => !!e);
  const cited = claim.cited.filter((l) => /^E\d+$/.test(l));

  return (
    <div className={`pi-in border-l-4 bg-surface-2 px-4 py-3 ${tone === "ok" ? "border-ok" : tone === "warn" ? "border-warn" : "border-bad"}`}>
      <p className="flex flex-wrap items-center gap-2 text-xs">
        <span className={`font-semibold ${TEXT[tone]}`}>{TONE_LABEL[tone]}</span>
        {from === "draft" && <span className="rounded-sm bg-surface px-1.5 py-0.5 text-muted">from the first draft</span>}
        <span className="text-muted" title="How sure the checker was (0–1)">checker score {claim.score.toFixed(2)}</span>
      </p>
      <blockquote className="mt-1.5 font-serif text-[1.02rem] leading-snug">“{claim.text.replace(/\s*\[(?:E\d+|\?)\]/g, "")}”</blockquote>
      {injection && plantedClaim([claim], injection) && (
        <p className="mt-1.5 border-l-2 border-stamp pl-2 text-xs">
          <span className="font-semibold text-stamp">Planted by the checker test</span> ({injection.description}).
          {injection.original ? (
            <>
              {" "}
              The model actually wrote: <span className="italic">“{injection.original.replace(/\s*\[(?:E\d+|\?)\]/g, "")}”</span>
            </>
          ) : (
            " The model never wrote this; it was added to the draft."
          )}
        </p>
      )}
      <p className="mt-1.5 text-xs text-muted">
        <span className="text-text">Why: </span>
        {claim.reason || "—"}
        {cited.length > 0 ? ` · cited ${cited.join(", ")}` : " · cited no source"}
      </p>

      <p className="mt-3 text-[11px] font-semibold tracking-wide text-muted uppercase">
        {claim.supporting.length ? "The passage that supports it" : passages.length ? "The passage it cited (does not support it)" : "Passage"}
      </p>
      {passages.length > 0 ? (
        <div className="mt-1.5 space-y-2">
          {passages.map((p) => (
            <Passage key={p.label} item={p} sentence={claim.text} />
          ))}
        </div>
      ) : (
        <p className="mt-1 text-sm">No passage in the sources says this, and it cited none.</p>
      )}
      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted">
        <span>
          <mark className="rounded-sm bg-accent-soft px-1 text-text">Marked</mark> words also appear in the sentence. That is a reading aid: the
          checker judges meaning, not shared words.
        </span>
        {passages[0]?.label && (
          <button type="button" onClick={() => onCite(passages[0].label!)} className="ml-auto text-accent hover:underline">
            Show in sources →
          </button>
        )}
      </div>
    </div>
  );
}

/** Draft vs final, when the checker sent the first answer back to be rewritten. */
function DraftCompare({
  attempts,
  selected,
  onSelect,
  injection,
}: {
  attempts: VerificationAttempt[];
  selected: XRaySelection;
  onSelect: (s: XRaySelection) => void;
  injection?: DemoInjection | null;
}) {
  const history = draftHistory(attempts);
  if (!history) return null;
  const { draft, final, removed } = history;
  const flagged = (draft.claims ?? []).filter((c) => toneOf(c) !== "ok").length;
  return (
    <section className="space-y-2">
      <h4 className="font-serif text-[1.05rem]">Caught before you saw it</h4>
      <p className="text-sm text-muted">
        {draft.attempt < final.attempt ? (
          <>
            The first draft had {flagged} sentence{flagged === 1 ? "" : "s"} the checker could not fully back with the sources, so the answer was
            rewritten with that feedback. Grounding went from {formatPercent(draft.grounding_score)} to {formatPercent(final.grounding_score)}.
          </>
        ) : (
          <>
            A rewrite was tried but scored lower ({formatPercent(draft.grounding_score)} vs {formatPercent(final.grounding_score)}), so the first
            answer was kept.
          </>
        )}
      </p>
      <div className="grid gap-3 md:grid-cols-2">
        {[
          {
            a: draft,
            title:
              draft.attempt < final.attempt
                ? injection
                  ? "First draft, with the planted sentence (rejected)"
                  : "First draft (rejected)"
                : "Rewrite (discarded)",
            from: "draft" as const,
          },
          { a: final, title: "Answer shown", from: "final" as const },
        ].map(({ a, title, from }) => (
          <div key={title} className="border border-line bg-surface px-3 py-2.5 text-[0.95rem] leading-relaxed">
            <p className="mb-1.5 flex items-center justify-between text-xs text-muted">
              <span className="font-semibold">{title}</span>
              <span>grounding {formatPercent(a.grounding_score)}</span>
            </p>
            <XRayBlocks
              text={a.answer_text}
              claims={(a.claims ?? []).filter((c) => c.location === "answer")}
              selected={selected}
              onSelect={onSelect}
              from={from}
              removed={from === "draft" ? removed : []}
              planted={plantedClaim(a.claims ?? [], injection)}
            />
          </div>
        ))}
      </div>
    </section>
  );
}

/** Everything under the answer in X-ray mode: tally, legend, inspector, draft history. */
export function XRayPanel({
  run,
  selected,
  onSelect,
  onCite,
  onTestChecker,
  busy = false,
}: {
  run: AskResponse;
  selected: XRaySelection;
  onSelect: (s: XRaySelection) => void;
  onCite: (label: string) => void;
  /** Ask this question again with a false sentence planted in the draft (demo mode) */
  onTestChecker?: () => void;
  busy?: boolean;
}) {
  const verification = run.verification as unknown as Verification | null | undefined;
  const injection = run.demo_injection as unknown as DemoInjection | null | undefined;
  const claims = answerClaims(verification);
  const counts = countTones(claims);
  const attempts = (run.verification_attempts ?? []) as unknown as VerificationAttempt[];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs">
        {(["ok", "warn", "bad"] as const).map((tone) => (
          <span key={tone} className="flex items-center gap-1.5">
            <span className={`h-2.5 w-2.5 rounded-full ${DOT[tone]}`} aria-hidden />
            <span className="font-semibold">{counts[tone]}</span>
            <span className="text-muted">{TONE_LABEL[tone].toLowerCase()}</span>
          </span>
        ))}
        {verification && <span className="text-muted sm:ml-auto">Checked by {METHOD[verification.method] ?? verification.method}</span>}
      </div>

      {selected ? (
        <Inspector selection={selected} evidence={run.evidence} onCite={onCite} injection={injection} />
      ) : (
        <p className="text-sm text-muted">Click any sentence to see the passage it was checked against.</p>
      )}

      <DraftCompare attempts={attempts} selected={selected} onSelect={onSelect} injection={injection} />

      {onTestChecker && !injection && (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border border-dashed border-line-strong px-4 py-3">
          <p className="min-w-0 flex-1 text-sm">
            <span className="font-semibold">Test the checker.</span>{" "}
            <span className="text-muted">
              Ask this again with one false sentence planted in the first draft, and see whether the checker catches it.
            </span>
          </p>
          <button
            type="button"
            onClick={onTestChecker}
            disabled={busy}
            className="border-[1.5px] border-text bg-surface px-3 py-1.5 text-sm font-medium shadow-[3px_3px_0_var(--text)] transition-transform hover:-translate-y-px disabled:opacity-50"
          >
            Plant a false fact
          </button>
        </div>
      )}

      <p className="text-xs text-muted">
        The checker can be wrong in both directions: treat colours as a guide to what to double-check, not a final judgement.
      </p>
    </div>
  );
}

/** Sentence that is most worth opening first: the first one the checker flagged. */
export function firstFlagged(run: AskResponse): XRaySelection {
  const claims = answerClaims(run.verification as unknown as Verification | null | undefined);
  const claim = claims.find((c) => toneOf(c) !== "ok");
  return claim ? { claim, from: "final" } : null;
}

/** Turns on after first paint so the colours "develop" one sentence after another. */
export function useDeveloped(active: boolean) {
  const [developed, setDeveloped] = useState(false);
  useEffect(() => {
    if (!active) return;
    const frame = requestAnimationFrame(() => setDeveloped(true));
    return () => {
      cancelAnimationFrame(frame);
      setDeveloped(false);
    };
  }, [active]);
  return developed;
}
