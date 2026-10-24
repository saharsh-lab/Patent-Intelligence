"use client";

import { useState, type FormEvent } from "react";
import useSWR from "swr";

import { Button, ErrorNotice, PageHeader, Panel } from "@/components/ui";
import { fetcher } from "@/lib/api";
import { auth, initials, useAuth } from "@/lib/auth";
import { formatDateTime } from "@/lib/format";
import { applyTheme, type Theme } from "@/lib/theme";
import type { SystemInfo } from "@/lib/types";

const field = "mt-1 w-full rounded-lg border border-line-strong bg-surface px-3 py-2 text-sm outline-none focus:border-accent focus:ring-2 focus:ring-accent/20";

function Choice<T extends string>({ value, options, onChange, label }: { value: T; options: [T, string][]; onChange: (v: T) => void; label: string }) {
  return (
    <div role="radiogroup" aria-label={label} className="inline-grid auto-cols-fr grid-flow-col gap-1 rounded-lg bg-surface-2 p-1">
      {options.map(([v, text]) => (
        <button key={v} type="button" role="radio" aria-checked={value === v} onClick={() => onChange(v)}
          className={`rounded-md px-3 py-1 text-sm ${value === v ? "bg-surface font-medium shadow-card" : "text-muted hover:text-text"}`}>
          {text}
        </button>
      ))}
    </div>
  );
}

export default function ProfilePage() {
  const { user, status, refresh } = useAuth();
  const info = useSWR<SystemInfo>("/system/info", fetcher);
  const cloud = info.data?.cloud_llm;
  const [edited, setName] = useState<string | null>(null);
  const name = edited ?? user?.name ?? "";
  const [saved, setSaved] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");

  if (!user) {
    return (
      <>
        <PageHeader title="Profile" />
        <p className="text-sm text-muted">
          {status?.auth_required === false
            ? "Accounts are switched off (AUTH_REQUIRED=false): this installation runs as a single local user."
            : "Loading…"}
        </p>
      </>
    );
  }

  async function update(changes: Parameters<typeof auth.updateProfile>[0], message: string) {
    setError(null);
    try {
      await auth.updateProfile(changes);
      await refresh();
      setSaved(message);
    } catch (e) {
      setError(e);
    }
  }

  async function changePassword(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await auth.changePassword(current, next);
      setCurrent("");
      setNext("");
      setSaved("Password changed. Other browsers were logged out.");
    } catch (err) {
      setError(err);
    }
  }

  const prefs = user.preferences;
  return (
    <>
      <PageHeader title="Profile & preferences" description="Your account details and how the app behaves for you." />
      <div className="max-w-2xl space-y-5">
        {error ? <ErrorNotice error={error} /> : null}
        {saved && <p className="rounded-lg bg-ok-soft px-4 py-2 text-sm text-ok" role="status">{saved}</p>}

        <Panel title="Account">
          <div className="flex items-center gap-4">
            <span className="flex h-14 w-14 items-center justify-center rounded-full bg-accent-soft text-lg font-semibold text-accent">
              {initials(user.name)}
            </span>
            <div className="text-sm">
              <p className="font-medium">{user.email}</p>
              <p className="text-muted">Member since {formatDateTime(user.created_at)}</p>
            </div>
          </div>
          <form
            className="mt-4 flex items-end gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              update({ name }, "Name saved.");
            }}
          >
            <label className="flex-1 text-sm font-medium">
              Display name
              <input className={field} value={name} onChange={(e) => setName(e.target.value)} maxLength={80} required />
            </label>
            <Button type="submit" disabled={!name.trim() || name === user.name}>Save</Button>
          </form>
        </Panel>

        <Panel title="Preferences">
          <div className="space-y-4 text-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span>
                <span className="block font-medium">Theme</span>
                <span className="text-xs text-muted">Saved to your account, so it follows you to other browsers.</span>
              </span>
              <Choice<Theme>
                label="Theme"
                value={prefs.theme ?? "dark"}
                options={[["light", "Light"], ["system", "System"], ["dark", "Dark"]]}
                onChange={(t) => {
                  applyTheme(t);
                  update({ preferences: { theme: t } }, "Theme saved.");
                }}
              />
            </div>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span>
                <span className="block font-medium">Chat answers by</span>
                <span className="text-xs text-muted">The agent plans tools and verifies; the baseline is faster.</span>
              </span>
              <Choice
                label="Chat pipeline"
                value={prefs.default_pipeline ?? "agentic"}
                options={[["agentic", "Agent"], ["baseline", "Baseline RAG"]]}
                onChange={(p) => update({ preferences: { default_pipeline: p } }, "Preference saved.")}
              />
            </div>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span>
                <span className="block font-medium">Hallucination checks</span>
                <span className="text-xs text-muted">
                  Balanced asks the language model to re-check flagged sentences (few false alarms). Strict flags
                  more sentences and misses fewer unsupported ones.
                </span>
              </span>
              <Choice
                label="Hallucination checks"
                value={prefs.verification ?? "balanced"}
                options={[["balanced", "Balanced"], ["strict", "Strict"]]}
                onChange={(v) => update({ preferences: { verification: v } }, "Preference saved.")}
              />
            </div>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span>
                <span className="block font-medium">Answer length</span>
                <span className="text-xs text-muted">Detailed answers explain more (up to about 400 words).</span>
              </span>
              <Choice
                label="Answer length"
                value={prefs.answer_detail ?? "concise"}
                options={[["concise", "Concise"], ["detailed", "Detailed"]]}
                onChange={(v) => update({ preferences: { answer_detail: v } }, "Preference saved.")}
              />
            </div>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span>
                <span className="block font-medium">Chat model</span>
                <span className="text-xs text-muted">
                  {cloud?.available
                    ? `Local runs on this computer (private). Cloud (${cloud.model}) answers several times faster; your question and the found passages are sent to the cloud service.`
                    : "Local runs on this computer. A faster cloud model can be enabled by setting CLOUD_LLM_API_KEY in the server's .env file."}
                </span>
              </span>
              <Choice
                label="Chat model"
                value={cloud?.available ? (prefs.model ?? "local") : "local"}
                options={cloud?.available ? [["local", "Local"], ["cloud", "Cloud (fast)"]] : [["local", "Local"]]}
                onChange={(v) => update({ preferences: { model: v } }, "Preference saved.")}
              />
            </div>
          </div>
        </Panel>

        <Panel title="Password">
          <form onSubmit={changePassword} className="grid gap-3 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
            <label className="text-sm font-medium">
              Current password
              <input className={field} type="password" value={current} onChange={(e) => setCurrent(e.target.value)} autoComplete="current-password" required />
            </label>
            <label className="text-sm font-medium">
              New password
              <input className={field} type="password" value={next} onChange={(e) => setNext(e.target.value)} autoComplete="new-password" minLength={8} required />
            </label>
            <Button type="submit">Change</Button>
          </form>
        </Panel>
      </div>
    </>
  );
}
