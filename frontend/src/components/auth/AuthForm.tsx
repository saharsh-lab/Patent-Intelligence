"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState, type FormEvent } from "react";
import { useSWRConfig } from "swr";

import { IconTile } from "@/components/chat/ChatSidebar";
import { icons } from "@/components/icons";
import { LogoMark } from "@/components/search/Logo";
import { ErrorNotice } from "@/components/ui";
import { auth } from "@/lib/auth";

/** Only internal paths: "/chat/1" yes; "//evil.com" or "https://…" no (open redirect). */
export function safeNext(next: string | null): string {
  return next && next.startsWith("/") && !next.startsWith("//") && !next.startsWith("/login") ? next : "/chat";
}

export function AuthForm({ mode }: { mode: "login" | "register" }) {
  const router = useRouter();
  const params = useSearchParams();
  const { mutate } = useSWRConfig();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const isRegister = mode === "register";

  async function submit(e: FormEvent) {
    e.preventDefault();
    setPending(true);
    setError(null);
    try {
      if (isRegister) await auth.register(name, email, password);
      else await auth.login(email, password);
      await mutate("/api/auth/me");
      router.replace(safeNext(params.get("next")));
    } catch (err) {
      setError(err);
      setPending(false);
    }
  }

  const input =
    "mt-1.5 w-full rounded-xl border border-line bg-surface-2/60 px-3.5 py-2.5 text-sm outline-none transition-colors focus:border-cite focus:ring-4 focus:ring-cite/15";
  return (
    <div className="relative isolate flex min-h-[calc(100vh-5rem)] flex-col items-center overflow-hidden px-4 pt-[6vh] pb-10">
      <Waves />
      <LogoMark size={52} draw className="mb-5 text-text" />
      <h1 className="pi-line text-center text-[clamp(2.4rem,7.5vw,5.6rem)] leading-[1.02] font-bold tracking-[-0.045em]">
        <span>
          Welcome to <span className="whitespace-nowrap">Patent Intelligence</span>
        </span>
      </h1>

      <div className="pi-in relative mt-10 w-full max-w-md" style={{ animationDelay: "0.2s" }}>
        <div aria-hidden className="absolute -inset-10 -z-10 rounded-full bg-[radial-gradient(closest-side,var(--glow),transparent)]" />
        <div className="glass rounded-[28px] p-6 shadow-hard sm:p-7">
          <h2 className="text-center text-[1.75rem] leading-tight">{isRegister ? "Create your account" : "Welcome back"}</h2>
          <p className="mt-1 text-center text-sm text-muted">
            {isRegister ? "Your documents and conversations stay private to your account." : "Log in to continue your research."}
          </p>

          <form onSubmit={submit} className="mt-6 space-y-4">
            {isRegister && (
              <label className="block text-sm font-medium">
                Name
                <input className={input} value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" required maxLength={80} />
              </label>
            )}
            <label className="block text-sm font-medium">
              Email
              <input className={input} type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" required />
            </label>
            <label className="block text-sm font-medium">
              Password
              <input
                className={input}
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete={isRegister ? "new-password" : "current-password"}
                required
                minLength={isRegister ? 8 : undefined}
              />
              {isRegister && <span className="mt-1 block text-xs font-normal text-muted">At least 8 characters, letters and numbers.</span>}
            </label>
            {error ? <ErrorNotice error={error} title={isRegister ? "Could not create the account" : "Could not log in"} /> : null}
            <button type="submit" disabled={pending} className="press w-full rounded-xl bg-brand px-3 py-3 text-sm font-semibold hover:opacity-90 disabled:opacity-60">
              {pending ? "Please wait…" : isRegister ? "Create account" : "Log in"}
            </button>
          </form>

          <div className="mt-6 rounded-2xl border border-line bg-surface-2/40 p-4">
            <p className="flex items-center gap-2 text-sm font-semibold">
              <icons.shield width={16} height={16} className="text-accent" /> Why an account?
            </p>
            <ul className="mt-3 space-y-3">
              {REASONS.map(({ icon, tone, title, text }) => (
                <li key={title} className="flex gap-3">
                  <IconTile icon={icon} tone={tone} size="sm" />
                  <span>
                    <span className="block text-sm font-medium">{title}</span>
                    <span className="block text-xs text-muted">{text}</span>
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <p className="mt-5 text-center text-sm text-muted">
          {isRegister ? "Already have an account? " : "New here? "}
          <Link
            href={`${isRegister ? "/login" : "/register"}${params.get("next") ? `?next=${encodeURIComponent(params.get("next")!)}` : ""}`}
            className="font-semibold text-accent hover:underline"
          >
            {isRegister ? "Log in" : "Create an account"}
          </Link>
        </p>
        <p className="mt-2 text-center text-xs text-muted">Research assistance only, not legal advice.</p>
      </div>
    </div>
  );
}

const REASONS = [
  { icon: icons.file, tone: "violet", title: "Your private library", text: "Uploaded documents and chats are visible only to you" },
  { icon: icons.shield, tone: "emerald", title: "Checked answers", text: "Every sentence is linked to its source and verified" },
  { icon: icons.map, tone: "blue", title: "Patent tools", text: "Landscape maps, watches and invention checks" },
] as const;

/** Flowing lines behind the page, as on the reference's sign-in page (pure SVG). */
function Waves() {
  const lines = Array.from({ length: 34 }, (_, i) => i);
  return (
    <svg
      aria-hidden
      viewBox="0 0 1440 900"
      preserveAspectRatio="xMidYMid slice"
      className="pointer-events-none absolute inset-0 -z-20 h-full w-full text-text [mask-image:radial-gradient(ellipse_at_center,black_30%,transparent_75%)]"
    >
      {lines.map((i) => (
        <path
          key={i}
          d={`M -120 ${250 + i * 9} C 360 ${120 + i * 14}, 760 ${760 - i * 6}, 1560 ${430 + i * 13}`}
          fill="none"
          stroke="currentColor"
          strokeOpacity={0.05 + (i % 6) * 0.025}
          strokeWidth={i % 5 === 0 ? 1.4 : 0.8}
        />
      ))}
    </svg>
  );
}
