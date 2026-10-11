"use client";

import { useState } from "react";

import { AgentTrace, LiveTrace, traceSummary } from "@/components/chat/AgentTrace";
import { LogoMark } from "@/components/search/Logo";

import { RunSummary } from "@/components/ask/AnswerView";
import { EvidenceList } from "@/components/ask/EvidenceList";
import { VerificationPanel } from "@/components/ask/VerificationPanel";
import { WorkflowPanel } from "@/components/ask/WorkflowPanel";
import { ChatAnswer, trustSummary } from "@/components/chat/ChatAnswer";
import { firstFlagged, type XRaySelection, XRayPanel } from "@/components/chat/XRay";
import { ComparisonTable, type Comparison } from "@/components/compare/ComparisonTable";
import { initials } from "@/lib/auth";
import type { ChatMessage } from "@/lib/chat";
import { scrollToEvidence } from "@/lib/evidence";
import type { Verification, VerificationAttempt } from "@/lib/verification";
import { answerClaims, type DemoInjection, injectionOutcome, plantedClaim } from "@/lib/xray";

export function UserBubble({ text, name }: { text: string; name?: string }) {
  return (
    <div className="pi-in flex justify-end gap-3">
      <div className="max-w-[85%] bg-brand px-4 py-2.5 text-sm whitespace-pre-wrap">
        {text}
      </div>
      <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-accent-soft text-xs font-semibold text-accent">
        {name ? initials(name) : "You"}
      </span>
    </div>
  );
}

export function AssistantAvatar() {
  return (
    <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center border border-line bg-surface text-text">
      <LogoMark size={24} />
    </span>
  );
}

type Open = "xray" | "sources" | "steps" | "details" | null;

const RUNNING_STAGES = ["Searching your library, the web and patent filings", "Ranking passages", "Writing the answer", "Checking every sentence"];

const TONE = { ok: "text-ok", warn: "text-warn", bad: "text-bad" } as const;

/** One question and its answer. Sources, checks and technical details stay folded away
 *  until asked for, so the conversation reads like a conversation. */
export function ChatMessageView({
  message,
  index,
  userName,
  onTestChecker,
  busy = false,
}: {
  message: ChatMessage;
  index: number;
  userName?: string;
  /** Ask the same question again with a false sentence planted (demo mode) */
  onTestChecker?: (question: string) => void;
  busy?: boolean;
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
          <LiveTrace conversationId={run.conversation_id ?? null} since={Date.parse(run.created_at)} stages={RUNNING_STAGES} />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <UserBubble text={message.user_message} name={userName} />
      <div className="pi-in flex gap-3" style={{ animationDelay: "0.1s" }}>
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
          <ChatAnswer
            run={run}
            onCite={cite}
            xray={open === "xray" ? { selected, onSelect: setSelected, planted: plantedClaim(answerClaims(verification), injection) } : null}
          />

          {run.status === "succeeded" && run.intent !== "small_talk" && (
            <div className="flex flex-wrap items-center gap-x-1 gap-y-1 text-xs text-muted">
              {trust ? (
                <span className={`mr-1 font-medium ${TONE[trust.tone]}`}>
                  {trust.tone === "ok" ? "✓ " : ""}
                  {trust.supported} of {trust.total} statements verified against the sources
                </span>
              ) : (
                <span className="mr-1">{cited} source{cited === 1 ? "" : "s"} cited</span>
              )}
              <span aria-hidden>·</span>
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
              />
            </div>
          )}
          {open === "sources" && (
            <div className="pi-in">
              <EvidenceList evidence={run.evidence} idPrefix={prefix} />
            </div>
          )}
          {open === "steps" && (
            <div className="pi-in border border-line bg-surface px-4 py-3">
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
        </div>
      </div>
    </div>
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

const OUTCOME = { ok: "border-ok text-ok", warn: "border-warn text-warn", bad: "border-bad text-bad" } as const;

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
