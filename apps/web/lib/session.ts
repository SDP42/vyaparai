"use client";

import type { PersonaId } from "./personas";

/**
 * What the browser remembers about who is signed in (name and email only, no secrets).
 * The access token lives in memory; the long-lived refresh token is an HttpOnly cookie
 * the page cannot read (see docs/THREAT_MODEL.md, "Sessions").
 */
const KEY = "vyapar.session";

export type Session =
  | { kind: "persona"; personaId: PersonaId }
  | { kind: "account"; email: string; name: string };

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

let accessToken: string | null = null;
let refreshing: Promise<string | null> | null = null;

export function getAccessToken(): string | null {
  return accessToken;
}

/** Ask the API for a fresh access token using the refresh cookie. One call at a time. */
export function refreshAccessToken(): Promise<string | null> {
  refreshing ??= (async () => {
    try {
      const res = await fetch(`${API_URL}/auth/refresh`, {
        method: "POST",
        credentials: "include",
        headers: { "X-Requested-With": "vyapar" },
      });
      if (!res.ok) {
        accessToken = null;
        return null;
      }
      accessToken = ((await res.json()) as { access_token: string }).access_token;
      return accessToken;
    } catch {
      return null;
    } finally {
      refreshing = null;
    }
  })();
  return refreshing;
}

/** A usable access token, refreshing from the cookie when the page was just opened. */
export async function ensureToken(): Promise<string | null> {
  return accessToken ?? refreshAccessToken();
}

/** Sign out: revoke the refresh token on the server, then forget everything here. */
export async function signOut(everywhere = false) {
  try {
    await fetch(`${API_URL}/auth/${everywhere ? "logout-all" : "logout"}`, {
      method: "POST",
      credentials: "include",
      headers: {
        "X-Requested-With": "vyapar",
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      },
    });
  } catch {
    /* offline: the cookie still expires on its own */
  }
  clearSession();
}

export function clearSession() {
  accessToken = null;
  try {
    navigator.serviceWorker?.controller?.postMessage("clear"); // forget saved numbers on this device
    void caches?.delete("vyapar-data-v1");
  } catch {
    /* no cache API */
  }
  try {
    localStorage.removeItem(KEY);
  } catch {
    /* ignore */
  }
}

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export async function loginWithPassword(email: string, password: string): Promise<Session> {
  const body = new URLSearchParams({ username: email, password });
  const res = await fetch(`${API_URL}/auth/login`, { method: "POST", body, credentials: "include" });
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    throw new Error(data?.error?.message ?? "Sign-in failed");
  }
  const { access_token } = (await res.json()) as { access_token: string };
  accessToken = access_token;
  const me = await fetch(`${API_URL}/auth/me`, { headers: { Authorization: `Bearer ${access_token}` } });
  const user = me.ok ? ((await me.json()) as { email: string; full_name: string }) : { email, full_name: email };
  return { kind: "account", email: user.email, name: user.full_name };
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
