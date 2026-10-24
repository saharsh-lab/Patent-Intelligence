// The answer as it happens (backend: app/agents/live.py, polled from /conversations/{id}/progress).
// Pure helpers; components/chat/LiveAnswer.tsx draws them.

import type { ProgressOut } from "@/lib/types";
import type { ClaimResult } from "@/lib/verification";

export type Live = NonNullable<ProgressOut["live"]>;
export type LiveSource = Live["sources"][number];

export const STAGES = ["Understand", "Search", "Write", "Check"] as const;

/** Which stage the agent is in (0–3), from its live answer and trace rows. */
export function stageOf(progress: Pick<ProgressOut, "steps" | "live"> | undefined): number {
  const phase = progress?.live?.phase;
  if (phase === "checking" || phase === "checked") return 3;
  if (phase === "writing" || phase === "rewriting") return 2;
  if (progress?.live?.sources.length || progress?.steps.some((s) => s.kind === "tool")) return 1;
  return 0;
}

/** One line on what is happening now. */
export function headline(progress: Pick<ProgressOut, "steps" | "live"> | undefined): string {
  const live = progress?.live;
  if (live?.general && live.phase === "writing") return "No source had it: answering from general knowledge";
  switch (live?.phase) {
    case "writing":
      return live.attempt > 1
        ? "Rewriting with more evidence"
        : `Writing from ${live.evidence.length} passage${live.evidence.length === 1 ? "" : "s"}`;
    case "checking":
      return "Checking each sentence against its source";
    case "checked": {
      const s = checkSummary(live.claims as unknown as ClaimResult[]);
      return s ? `${s.supported} of ${s.total} sentences supported${s.flagged ? ` · ${s.flagged} flagged` : ""}` : "Checked";
    }
    case "rewriting":
      return "Some sentences were not supported: rewriting";
  }
  const found = live?.sources.length ?? 0;
  if (stageOf(progress) === 1) return found ? `Reading ${found} source${found === 1 ? "" : "s"}` : "Searching";
  return "Understanding the question";
}

export function checkSummary(claims: ClaimResult[]) {
  const answer = claims.filter((c) => c.location === "answer");
  if (!answer.length) return null;
  const supported = answer.filter((c) => c.verdict === "supported" && !c.misattributed).length;
  return { supported, total: answer.length, flagged: answer.length - supported };
}

/** The first `count` characters of a draft, without a half-written citation or bold
 *  marker at the end ("… pump [E" would flash as text before becoming a chip). */
export function visibleDraft(text: string, count: number): string {
  return text.slice(0, count).replace(/\[(?:E\d*)?$|\*{1,2}$/, "");
}

/** Typewriter step: catch up with the text received so far, faster the further behind. */
export function nextCount(shown: number, total: number): number {
  if (shown >= total) return total;
  return Math.min(total, shown + Math.max(1, Math.ceil((total - shown) / 10)));
}

/** A draft continues the previous one (keep typing) or replaces it (start again). */
export function continues(previous: string, next: string): boolean {
  return next.startsWith(previous.slice(0, Math.max(0, previous.length - 8)));
}

/** Citation sentences flagged before a rewrite, shown without their [E#] labels. */
export function plainSentence(text: string): string {
  return text.replace(/\s*\[(?:E\d+|\?)\]/g, "").trim();
}
