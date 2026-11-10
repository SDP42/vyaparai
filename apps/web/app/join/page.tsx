"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Logo } from "@/components/landing/Nav";
import { ApiError, api } from "@/lib/api";
import { loadSession } from "@/lib/session";

const KEY = "vyapar.invite";
type State = "checking" | "signin" | "joining" | "done" | "failed";

/** Opened from an invitation link: /join#<token>. The token never leaves the browser until the user is signed in. */
export default function JoinPage() {
  const [state, setState] = useState<State>("checking");
  const [name, setName] = useState("");
  const [msg, setMsg] = useState("");

  useEffect(() => {
    let token = window.location.hash.slice(1);
    try {
      if (token) sessionStorage.setItem(KEY, token);
      else token = sessionStorage.getItem(KEY) ?? "";
    } catch {
      /* storage blocked: the link in the address bar still works */
    }
    window.history.replaceState(null, "", "/join"); // keep the token out of history and screenshots
    if (!token) {
      setMsg("This link is incomplete. Ask for a new invitation.");
      return setState("failed");
    }
    if (loadSession()?.kind !== "account") return setState("signin");
    setState("joining");
    api<{ name: string }>("/invitations/accept", { method: "POST", body: JSON.stringify({ token }) })
      .then((ws) => {
        setName(ws.name);
        try {
          sessionStorage.removeItem(KEY);
        } catch {
          /* ignore */
        }
        setState("done");
      })
      .catch((e: unknown) => {
        setMsg(e instanceof ApiError ? e.message : "Something went wrong");
        setState("failed");
      });
  }, []);

  return (
    <main className="grid min-h-dvh place-items-center bg-canvas p-6">
      <div className="w-full max-w-md rounded-3xl border border-line bg-surface p-8 text-center">
        <Link href="/" className="inline-block"><Logo /></Link>
        <h1 className="mt-6 font-serif text-3xl">Join a workspace</h1>
        <div className="mt-4 text-sm text-fg/75" aria-live="polite">
          {state === "checking" && <p>Checking your invitation…</p>}
          {state === "joining" && <p>Adding you to the team…</p>}
          {state === "signin" && (
            <>
              <p>Sign in to accept the invitation. New here? Create an account on the same page first.</p>
              <Link href="/login?mode=account" className="mt-5 inline-block rounded-full bg-fg px-6 py-2.5 font-semibold text-canvas hover:bg-sindoor">Sign in</Link>
            </>
          )}
          {state === "done" && (
            <>
              <p>You are now part of <strong>{name}</strong>.</p>
              <Link href="/app" className="mt-5 inline-block rounded-full bg-fg px-6 py-2.5 font-semibold text-canvas hover:bg-sindoor">Open the workspace</Link>
            </>
          )}
          {state === "failed" && <p role="alert" className="text-sindoor">{msg}</p>}
        </div>
      </div>
    </main>
  );
}
