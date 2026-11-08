"use client";

import type { PersonaId } from "./personas";

/**
 * Demo session stored in localStorage (per-browser convenience only).
 * Real sessions will use an HttpOnly cookie issued by the API (Phase F2).
 */
const KEY = "vyapar.session";

export type Session =
  | { kind: "persona"; personaId: PersonaId }
  | { kind: "account"; email: string; name: string; token: string };

export function saveSession(s: Session) {
  try {
    localStorage.setItem(KEY, JSON.stringify(s));
  } catch {
    /* storage unavailable (private mode) — session lasts for this page only */
  }
}

export function loadSession(): Session | null {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as Session) : null;
  } catch {
    return null;
  }
}

export function clearSession() {
  try {
    localStorage.removeItem(KEY);
  } catch {
    /* ignore */
  }
}

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export async function loginWithPassword(email: string, password: string): Promise<Session> {
  const body = new URLSearchParams({ username: email, password });
  const res = await fetch(`${API_URL}/auth/login`, { method: "POST", body });
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    throw new Error(data?.error?.message ?? "Sign-in failed");
  }
  const { access_token } = (await res.json()) as { access_token: string };
  const me = await fetch(`${API_URL}/auth/me`, { headers: { Authorization: `Bearer ${access_token}` } });
  const user = me.ok ? ((await me.json()) as { email: string; full_name: string }) : { email, full_name: email };
  return { kind: "account", email: user.email, name: user.full_name, token: access_token };
}

export async function registerAccount(fullName: string, email: string, password: string): Promise<Session> {
  const res = await fetch(`${API_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, full_name: fullName, password }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    const detail = data?.error?.details?.[0]?.msg as string | undefined;
    throw new Error(detail ? `${data?.error?.message}: ${detail}` : (data?.error?.message ?? "Could not create the account"));
  }
  return loginWithPassword(email, password);
}
