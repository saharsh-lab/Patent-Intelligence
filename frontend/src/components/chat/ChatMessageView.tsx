"use client";

import { useState } from "react";

import { icons } from "@/components/icons";

import { AgentTrace, traceSummary } from "@/components/chat/AgentTrace";
import { FollowUps } from "@/components/chat/FollowUps";
import { LiveAnswer } from "@/components/chat/LiveAnswer";
import { LogoMark } from "@/components/search/Logo";

import { RunSummary } from "@/components/ask/AnswerView";
import { EvidenceList } from "@/components/ask/EvidenceList";
import { VerificationPanel } from "@/components/ask/VerificationPanel";
import { WorkflowPanel } from "@/components/ask/WorkflowPanel";
import { ChatAnswer, trustSummary } from "@/components/chat/ChatAnswer";
import { firstFlagged, type OnFix, type XRaySelection, XRayPanel } from "@/components/chat/XRay";
import { ComparisonTable, type Comparison } from "@/components/compare/ComparisonTable";
import { api } from "@/lib/api";
import { initials } from "@/lib/auth";
import { type ChatMessage, copyText } from "@/lib/chat";
import { scrollToEvidence } from "@/lib/evidence";
import type { Verification, VerificationAttempt } from "@/lib/verification";
import { answerClaims, type DemoInjection, injectionOutcome, plantedClaim } from "@/lib/xray";

export function UserBubble({
  text,
  name,
  instant = false,
  onEdit,
}: {
  text: string;
  name?: string;
  instant?: boolean;
  /** Put the question back in the box to change and send again */
  onEdit?: (text: string) => void;
}) {
  return (
    <div className={`${instant ? "" : "pi-in"} group flex items-start justify-end gap-2`}>
      {onEdit && (
        <button
          type="button"
          onClick={() => onEdit(text)}
          aria-label="Edit this question"
          title="Edit and ask again"
          className="mt-1.5 p-1 text-muted opacity-0 transition-opacity group-hover:opacity-100 hover:text-text focus-visible:opacity-100"
        >
          <icons.pencil width={15} height={15} />
        </button>
      )}
      <div className="max-w-[85%] rounded-2xl rounded-tr-md border border-line bg-surface-2 px-4 py-2.5 text-[0.95rem] whitespace-pre-wrap">
        {text}
      </div>
      <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-accent text-xs font-bold text-white">
        {name ? initials(name) : "You"}
      </span>
    </div>
  );
}

export function AssistantAvatar({ draw = false }: { draw?: boolean }) {
  return <LogoMark size={32} draw={draw} className="mt-0.5 shrink-0 text-text" />;
}

type Open = "xray" | "sources" | "steps" | "details" | null;

const TONE = { ok: "text-ok", warn: "text-warn", bad: "text-bad" } as const;

/** One question and its answer. Sources, checks and technical details stay folded away
 *  until asked for, so the conversation reads like a conversation. */
export function ChatMessageView({
  message,
  index,
  userName,
  onTestChecker,
  busy = false,
  onAsk,
  examples,
  instant = false,
  onRegenerate,
  onEdit,
  onFixed,
}: {
  message: ChatMessage;
  index: number;
  userName?: string;
  /** Ask the same question again with a false sentence planted (demo mode) */
  onTestChecker?: (question: string) => void;
  busy?: boolean;
  /** The latest answer: offer follow-up questions, sent with this */
  onAsk?: (message: string) => void;
  /** Example questions to offer after a greeting or a question about the assistant */
  examples?: string[];
  /** The reader just watched this answer being written: show it at once, no fade-in */
  instant?: boolean;
  /** "Try again": ask the same question again */
  onRegenerate?: () => void;
  onEdit?: (text: string) => void;
  /** A sentence was fixed (or the original restored): fetch the conversation again */
  onFixed?: () => Promise<unknown>;
}) {
  const run = message.response;
  const prefix = `m${index}-`;
  const injection = run.demo_injection as unknown as DemoInjection | null | undefined;
  // A checker test opens straight in the X-ray, on the planted sentence
  const [open, setOpen] = useState<Open>(injection ? "xray" : null);
  const [selected, setSelected] = useState<XRaySelection>(() => (injection ? plantedSelection(run, injection) : null));
  const verification = run.verification as unknown as Verification | null | undefined;
  const trust = trustSummary(verification);
  const cited = run.evidence.filter((e) => e.cited).length;
  // An answer built from sources (not general knowledge, the clock or a stopped draft)
  const grounded = run.status === "succeeded" && !run.general && !run.everyday;

  const fix: OnFix | undefined = onFixed
    ? async (action, claim) => {
        await api.fixSentence(message.run_id, action, claim?.index);
        if (action !== "rewrite") setSelected(null);
        await onFixed();
      }
    : undefined;

  function cite(label: string) {
    setOpen("sources");
    requestAnimationFrame(() => requestAnimationFrame(() => scrollToEvidence(label, prefix)));
  }
  const toggle = (what: Open) => {
    // Opening the X-ray starts on the first sentence the checker flagged, if any
    if (what === "xray" && open !== "xray") setSelected(firstFlagged(run));
    setOpen((o) => (o === what ? null : what));
  };
  const tab = (what: Open, label: string) => (
    <button
      type="button"
      onClick={() => toggle(what)}
      aria-expanded={open === what}
      className={`border-b-2 px-2 py-0.5 transition-colors ${open === what ? "border-cite font-medium text-accent" : "border-transparent hover:border-line hover:text-text"}`}
    >
      {label}
    </button>
  );

  if (run.status === "running") {
    // Still being answered (the page was changed or reloaded meanwhile)
    return (
      <div className="space-y-4">
        <UserBubble text={message.user_message} name={userName} />
        <div className="flex gap-3">
          <AssistantAvatar />
          <LiveAnswer conversationId={run.conversation_id ?? null} since={Date.parse(run.created_at)} />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <UserBubble text={message.user_message} name={userName} instant={instant} onEdit={busy ? undefined : onEdit} />
      <div className={`${instant ? "" : "pi-in"} flex gap-3`} style={{ animationDelay: "0.1s" }}>
        <AssistantAvatar />
        <div className="min-w-0 flex-1 space-y-3">
          {message.interpreted_as && message.interpreted_as !== message.user_message && (
            <p className="text-xs text-muted" title="Your question was completed using the conversation so far">
              Understood as: <span className="italic">{message.interpreted_as}</span>
            </p>
          )}
          {run.comparison && (
            <ComparisonTable
              comparison={run.comparison as unknown as Comparison}
              onCite={cite}
              verification={run.verification as unknown as Verification | null}
            />
          )}
          {injection && <InjectionBanner injection={injection} />}
          {/* The answer in a rounded bubble; actions, checks and sources open below it */}
          <div className="space-y-3 rounded-2xl rounded-tl-md border border-line bg-surface/70 px-5 py-4">
            <AnswerKind run={run} />
            <PremiseNote run={run} />
            <ChatAnswer
              run={run}
              instant={instant}
              onCite={cite}
              xray={open === "xray" ? { selected, onSelect: setSelected, planted: plantedClaim(answerClaims(verification), injection) } : null}
            />
            {run.intent !== "small_talk" && run.status !== "failed" && (
              <div className="flex flex-wrap items-center justify-between gap-2">
                {grounded && cited > 0 ? <SourceChips run={run} onCite={cite} /> : <span />}
                <MessageActions run={run} onRegenerate={busy ? undefined : onRegenerate} />
              </div>
            )}
          </div>

          {grounded && (
            <div className="flex flex-wrap items-center gap-x-1 gap-y-1 text-xs text-muted">
              {trust ? (
                <span className={`mr-1 basis-full font-medium sm:basis-auto ${TONE[trust.tone]}`} title={`${trust.supported} of ${trust.total} statements verified against the sources they cite`}>
                  {trust.tone === "ok" ? "✓ " : ""}
                  {trust.supported} of {trust.total} statements verified
                  {(run.fixes?.length ?? 0) > 0 && <span className="font-normal text-muted"> · edited by you</span>}
                </span>
              ) : (
                <span className="mr-1 basis-full sm:basis-auto">{cited} source{cited === 1 ? "" : "s"} cited</span>
              )}
              {/* Phones: the verdict gets its own line, so no separator is left hanging */}
              <span aria-hidden className="hidden sm:inline">·</span>
              {trust && tab("xray", open === "xray" ? "Close X-ray" : "Hallucination X-ray")}
              {tab("sources", `Sources (${run.evidence.length})`)}
              {(run.trace?.length ?? 0) > 0 && tab("steps", "Agent steps")}
              {tab("details", "Details")}
            </div>
          )}

          {open === "xray" && (
            <div className="pi-in">
              <XRayPanel
                run={run}
                selected={selected}
                onSelect={setSelected}
                onCite={cite}
                busy={busy}
                onTestChecker={onTestChecker ? () => onTestChecker(message.interpreted_as ?? message.user_message) : undefined}
                onFix={busy ? undefined : fix}
              />
            </div>
          )}
          {open === "sources" && (
            <div className="pi-in">
              <EvidenceList evidence={run.evidence} idPrefix={prefix} />
            </div>
          )}
          {open === "steps" && (
            <div className="pi-in rounded-2xl border border-line bg-surface px-4 py-3">
              <p className="mb-2.5 flex flex-wrap items-baseline gap-x-2 text-xs text-muted">
                <span className="font-semibold tracking-wide text-text uppercase">How the agent worked</span>
                <span className="ml-auto">{traceSummary(run.trace ?? [])}</span>
              </p>
              <AgentTrace steps={run.trace ?? []} />
            </div>
          )}
          {open === "details" && (
            <div className="stagger space-y-3">
              <VerificationPanel run={run} onCite={cite} />
              <WorkflowPanel run={run} />
              <RunSummary run={run} />
            </div>
          )}
          {onAsk && run.conversation_id && run.status === "succeeded" && !run.everyday && (
            <FollowUps
              conversationId={run.conversation_id}
              runId={message.run_id}
              onAsk={onAsk}
              busy={busy}
              examples={run.intent === "small_talk" ? examples : undefined}
            />
          )}
        </div>
      </div>
    </div>
  );
}

/** The question assumed something no source mentions, and the answer said so. */
function PremiseNote({ run }: { run: ChatMessage["response"] }) {
  const terms = (run.premise as { acknowledged?: string[] } | null | undefined)?.acknowledged ?? [];
  if (terms.length === 0) return null;
  return (
    <p className="inline-flex flex-wrap items-center gap-x-1.5 rounded-full border border-miss/30 bg-miss-soft px-3 py-1 text-xs text-text">
      <span className="font-semibold text-miss">Check the question</span>
      <span className="text-muted">· it assumes something the sources never mention: {terms.map((t) => `“${t}”`).join(", ")}</span>
    </p>
  );
}

/** Where an answer that is not built from sources comes from, said before it is read. */
function AnswerKind({ run }: { run: ChatMessage["response"] }) {
  const general = run.general as { searched?: boolean } | null | undefined;
  if (general) {
    return (
      <p className="inline-flex flex-wrap items-center gap-x-1.5 rounded-full border border-warn/30 bg-warn-soft px-3 py-1 text-xs text-text">
        <span className="font-semibold text-warn">General knowledge</span>
        <span className="text-muted">
          {general.searched ? "· not found in your library, patent filings or the web · " : "· "}
          not from sources, not checked
        </span>
      </p>
    );
  }
  if (run.everyday) {
    return (
      <p className="text-xs text-muted">
        {run.everyday === "clock" ? "From the clock (your time zone)" : "Calculated exactly"}
      </p>
    );
  }
  if (run.status === "stopped") {
    return <p className="text-xs text-muted">You stopped this answer. What was written so far is shown; it was not checked.</p>;
  }
  return null;
}

const KIND_ICON: Record<string, typeof icons.file> = { upload: icons.file, wikipedia: icons.globe, tavily: icons.globe };

/** The cited sources as chips under the answer; a click opens the passage. */
function SourceChips({ run, onCite }: { run: ChatMessage["response"]; onCite: (label: string) => void }) {
  const seen = new Set<string>();
  const sources = run.evidence.filter((e) => {
    if (!e.cited || !e.label || seen.has(e.source_label)) return false;
    seen.add(e.source_label);
    return true;
  });
  const shown = sources.slice(0, 4);
  return (
    <ul className="flex flex-wrap gap-1.5" aria-label="Sources">
      {shown.map((e) => {
        const Icon = KIND_ICON[e.source_type] ?? (e.patent_id || /^[A-Z]{2}\d/.test(e.source_label) ? icons.search : icons.file);
        const name = e.source_type === "wikipedia" || e.source_type === "tavily" ? (e.source_title ?? e.source_label) : e.source_label;
        return (
          <li key={e.source_label}>
            <button
              type="button"
              onClick={() => onCite(e.label as string)}
              title={e.source_title ?? e.source_label}
              className="inline-flex max-w-[15rem] items-center gap-1.5 rounded-full border border-line bg-surface px-2.5 py-1 text-xs transition-colors hover:border-line-strong hover:bg-surface-2"
            >
              <span className="font-mono text-[10px] text-cite">{(e.label as string).replace(/^E/, "")}</span>
              <Icon width={12} height={12} className="shrink-0 text-muted" />
              <span className="truncate">{name}</span>
            </button>
          </li>
        );
      })}
      {sources.length > shown.length && <li className="self-center text-xs text-muted">+{sources.length - shown.length} more</li>}
    </ul>
  );
}

/** Copy the answer (with its sources) and ask again. */
function MessageActions({ run, onRegenerate }: { run: ChatMessage["response"]; onRegenerate?: () => void }) {
  const [copied, setCopied] = useState(false);
  const text = run.answer ?? run.insufficient_reason ?? "";
  const button = "flex items-center gap-1 rounded-sm px-1.5 py-0.5 text-muted transition-colors hover:bg-surface-2 hover:text-text disabled:opacity-40";
  return (
    <span className="ml-auto flex items-center gap-0.5 text-xs">
      {text && (
        <button
          type="button"
          className={button}
          title="Copy the answer with its sources"
          onClick={async () => {
            try {
              await navigator.clipboard.writeText(copyText(text, run.evidence));
              setCopied(true);
              setTimeout(() => setCopied(false), 1500);
            } catch {
              /* clipboard blocked: nothing to do */
            }
          }}
        >
          {copied ? <icons.check width={14} height={14} /> : <icons.copy width={14} height={14} />}
          <span>{copied ? "Copied" : "Copy"}</span>
        </button>
      )}
      {run.everyday !== "clock" && run.everyday !== "calculator" && (
        <button type="button" className={button} onClick={onRegenerate} disabled={!onRegenerate} title="Ask the same question again">
          <icons.refresh width={14} height={14} />
          <span>Try again</span>
        </button>
      )}
    </span>
  );
}

/** The planted sentence as first judged: in the draft if the answer was rewritten. */
function plantedSelection(run: ChatMessage["response"], injection: DemoInjection): XRaySelection {
  const attempts = (run.verification_attempts ?? []) as unknown as VerificationAttempt[];
  const draft = attempts.length > 1 ? attempts[0] : null;
  const inDraft = draft && plantedClaim(draft.claims ?? [], injection);
  if (inDraft) return { claim: inDraft, from: "draft" };
  const inFinal = plantedClaim(answerClaims(run.verification as unknown as Verification | null), injection);
  return inFinal ? { claim: inFinal, from: "final" } : null;
}

const OUTCOME = { ok: "border-ok text-ok", warn: "border-warn text-warn", bad: "border-bad text-bad", miss: "border-miss text-miss" } as const;

function InjectionBanner({ injection }: { injection: DemoInjection }) {
  const outcome = injectionOutcome(injection);
  return (
    <div className={`pi-in border-l-4 bg-surface px-3 py-2 text-sm ${OUTCOME[outcome.tone]}`}>
      <p className="text-text">
        <span className="font-semibold text-stamp">Checker test.</span> One false sentence was planted in the first draft (
        {injection.description}). The checker was not told which.
      </p>
      <p className="mt-0.5 font-medium">{outcome.text}</p>
    </div>
  );
}
