"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState, type FormEvent } from "react";
import { useSWRConfig } from "swr";

import { ErrorNotice } from "@/components/ui";
import { auth } from "@/lib/auth";

/** Only internal paths: "/chat/1" yes; "//evil.com" or "https://…" no (open redirect). */
export function safeNext(next: string | null): string {
  return next && next.startsWith("/") && !next.startsWith("//") && !next.startsWith("/login") ? next : "/";
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

  const input = "mt-1 w-full rounded-lg border border-line-strong bg-surface px-3 py-2 text-sm outline-none focus:border-accent focus:ring-2 focus:ring-accent/20";
  return (
    <div className="w-full max-w-sm">
      <div className="mb-6 flex flex-col items-center text-center">
        <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-brand text-lg font-bold text-white shadow-card">
          PI
        </span>
        <h1 className="mt-4 text-xl font-semibold tracking-tight">
          {isRegister ? "Create your account" : "Welcome back"}
        </h1>
        <p className="mt-1 text-sm text-muted">
          {isRegister
            ? "Your documents and conversations stay private to your account."
            : "Log in to continue to Patent Intelligence."}
        </p>
      </div>

      <form onSubmit={submit} className="space-y-4 rounded-2xl border border-line bg-surface p-6 shadow-card">
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
        <button
          type="submit"
          disabled={pending}
          className="w-full rounded-lg bg-brand px-3 py-2.5 text-sm font-medium text-white shadow-card hover:brightness-110 disabled:opacity-60"
        >
          {pending ? "Please wait…" : isRegister ? "Create account" : "Log in"}
        </button>
      </form>

      <p className="mt-4 text-center text-sm text-muted">
        {isRegister ? "Already have an account? " : "New here? "}
        <Link
          href={`${isRegister ? "/login" : "/register"}${params.get("next") ? `?next=${encodeURIComponent(params.get("next")!)}` : ""}`}
          className="font-medium text-accent hover:underline"
        >
          {isRegister ? "Log in" : "Create an account"}
        </Link>
      </p>
    </div>
  );
}
