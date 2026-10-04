"use client";

import { useState } from "react";

import { LogoMark } from "@/components/search/Logo";

import { RunSummary } from "@/components/ask/AnswerView";
import { EvidenceList } from "@/components/ask/EvidenceList";
import { VerificationPanel } from "@/components/ask/VerificationPanel";
import { WorkflowPanel } from "@/components/ask/WorkflowPanel";
import { ChatAnswer, trustSummary } from "@/components/chat/ChatAnswer";
import { ComparisonTable, type Comparison } from "@/components/compare/ComparisonTable";
import { initials } from "@/lib/auth";
import type { ChatMessage } from "@/lib/chat";
import { scrollToEvidence } from "@/lib/evidence";
import type { Verification } from "@/lib/verification";

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

type Open = "checks" | "sources" | "details" | null;

const TONE = { ok: "text-ok", warn: "text-warn", bad: "text-bad" } as const;

/** One question and its answer. Sources, checks and technical details stay folded away
 *  until asked for, so the conversation reads like a conversation. */
export function ChatMessageView({ message, index, userName }: { message: ChatMessage; index: number; userName?: string }) {
  const run = message.response;
  const prefix = `m${index}-`;
  const [open, setOpen] = useState<Open>(null);
  const verification = run.verification as unknown as Verification | null | undefined;
  const trust = trustSummary(verification);
  const cited = run.evidence.filter((e) => e.cited).length;

  function cite(label: string) {
    setOpen("sources");
    requestAnimationFrame(() => requestAnimationFrame(() => scrollToEvidence(label, prefix)));
  }
  const toggle = (what: Open) => setOpen((o) => (o === what ? null : what));
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
          <ChatAnswer run={run} onCite={cite} showChecks={open === "checks"} />

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
              {trust && tab("checks", open === "checks" ? "Hide checks" : "Show checks")}
              {tab("sources", `Sources (${run.evidence.length})`)}
              {tab("details", "Details")}
            </div>
          )}

          {open === "checks" && trust && trust.supported < trust.total && (
            <p className="text-xs text-muted">
              <span className="rounded-sm bg-warn-soft px-1">dotted</span> = partly supported ·{" "}
              <span className="rounded-sm bg-bad-soft px-1">wavy</span> = not found in the sources · hover a sentence for the
              reason.
            </p>
          )}
          {open === "sources" && (
            <div className="pi-in">
              <EvidenceList evidence={run.evidence} idPrefix={prefix} />
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
