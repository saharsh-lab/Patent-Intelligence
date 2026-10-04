// Accounts: the current user, login/register/logout. The session itself is an
// httpOnly cookie set by the backend; JavaScript never sees the token.
import useSWR from "swr";

import { ApiError, parseError } from "./api";

export interface User {
  id: string;
  email: string;
  name: string;
  preferences: { theme?: "light" | "dark" | "system"; answer_detail?: "concise" | "detailed"; default_pipeline?: "agentic" | "baseline"; verification?: "balanced" | "strict" };
  created_at: string;
}

export interface AuthStatus {
  authenticated: boolean;
  auth_required: boolean;
  user: User | null;
}

async function post<T>(path: string, body?: unknown, method = "POST"): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError("Cannot reach the server.", 0, "network_error");
  }
  if (!response.ok) throw await parseError(response);
  return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
}

export const auth = {
  login: (email: string, password: string) => post<User>("/auth/login", { email, password }),
  register: (name: string, email: string, password: string) => post<User>("/auth/register", { name, email, password }),
  logout: () => post<void>("/auth/logout"),
  updateProfile: (changes: { name?: string; preferences?: Partial<User["preferences"]> }) =>
    post<User>("/auth/me", changes, "PATCH"),
  changePassword: (current_password: string, new_password: string) =>
    post<void>("/auth/password", { current_password, new_password }),
};

export function useAuth() {
  const { data, error, isLoading, mutate } = useSWR<AuthStatus>("/api/auth/me", (url: string) =>
    fetch(url).then((r) => {
      if (!r.ok) throw new Error("auth status unavailable");
      return r.json();
    }),
  );
  return { status: data, error, isLoading, refresh: mutate, user: data?.user ?? null };
}

/** "Ada Lovelace" → "AL" */
export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  return ((parts[0]?.[0] ?? "?") + (parts.length > 1 ? parts[parts.length - 1][0] : "")).toUpperCase();
}

export function greeting(date = new Date()): string {
  const hour = date.getHours();
  return hour < 5 ? "Good evening" : hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";
}
