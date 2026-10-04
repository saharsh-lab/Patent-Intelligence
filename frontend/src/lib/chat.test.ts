import { describe, expect, it } from "vitest";

import { groupByRecency, type ConversationSummary } from "./chat";

const at = (iso: string) => ({ id: iso, updated_at: iso }) as ConversationSummary;

describe("groupByRecency", () => {
  it("groups conversations by their last activity", () => {
    const now = new Date("2026-10-04T15:00:00");
    const groups = groupByRecency(
      [at("2026-10-04T09:00:00"), at("2026-10-03T20:00:00"), at("2026-09-30T10:00:00"), at("2026-08-01T10:00:00")],
      now,
    );
    expect(groups.map(([label, items]) => [label, items.length])).toEqual([
      ["Today", 1],
      ["Yesterday", 1],
      ["Previous 7 days", 1],
      ["Older", 1],
    ]);
  });
});
