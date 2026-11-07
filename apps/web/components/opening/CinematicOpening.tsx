"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useState } from "react";
import { Wordmark } from "@/components/landing/Navigation";
import { isMuted, setMuted, unlockAudio } from "@/lib/sfx";

const ShopScene = dynamic(() => import("./ShopScene"), { ssr: false });

type Phase = "loading" | "idle" | "opening" | "diving" | "done";

function setGateLock(locked: boolean) {
  document.documentElement.dataset.gate = locked ? "locked" : "open";
  window.dispatchEvent(new CustomEvent("vyapar:gate", { detail: { locked } }));
}

/**
 * Page 1: the key-and-lock opening, shown before the landing page.
 * INTERIM version: the interaction and sound work; the photoreal storefront,
 * scroll-scrubbed unlock and shop-to-digital transition come in the opening phases.
 */
export function CinematicOpening() {
  const [phase, setPhase] = useState<Phase>("loading");
  const [sound, setSound] = useState(false);

  useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let webgl = false;
    try {
      const c = document.createElement("canvas");
      webgl = !!(c.getContext("webgl2") || c.getContext("webgl"));
    } catch {
      webgl = false;
    }
    if (reduced || !webgl) {
      setPhase("done");
      return;
    }
    setMuted(true); // start muted; enabled when the visitor clicks the key
    window.scrollTo(0, 0);
    setGateLock(true);
    // Wait for fonts (painted onto the shop textures), but never longer than 1.5 s.
    const ready = () => setPhase((p) => (p === "loading" ? "idle" : p));
    const t = window.setTimeout(ready, 1500);
    document.fonts.ready.then(() => {
      window.clearTimeout(t);
      ready();
    });
    return () => window.clearTimeout(t);
  }, []);

  const finish = useCallback(() => {
    setPhase("done");
    setGateLock(false);
    window.scrollTo(0, 0);
  }, []);

  const open = useCallback(() => {
    unlockAudio();
    setMuted(false);
    setSound(true);
    setPhase((p) => (p === "idle" ? "opening" : p));
  }, []);
  const onDive = useCallback(() => setPhase("diving"), []);
  const noop = useCallback(() => {}, []);

  useEffect(() => {
    if (phase !== "diving") return;
    const t = window.setTimeout(finish, 1500);
    return () => window.clearTimeout(t);
  }, [phase, finish]);

  useEffect(() => {
    if (phase !== "idle") return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") finish();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [phase, finish]);

  if (phase === "done") return null;
  const busy = phase === "opening" || phase === "diving";

  return (
    <div
      className={`fixed inset-0 z-[90] overflow-hidden bg-[radial-gradient(ellipse_at_60%_40%,#ffffff_0%,#f6f7fb_50%,#e6e9f3_100%)] transition-opacity duration-700 ${
        phase === "diving" ? "pointer-events-none opacity-0 delay-500" : "opacity-100"
      }`}
      role="dialog"
      aria-label="Opening: unlock the shop"
      onTransitionEnd={(e) => {
        if (phase === "diving" && e.target === e.currentTarget) finish();
      }}
    >
      <div className="absolute inset-0">
        {phase !== "loading" && <ShopScene opening={busy} onKeyClick={open} onDive={onDive} onOpened={noop} />}
      </div>

      <header className="absolute inset-x-0 top-0 flex items-center justify-between px-5 py-5 sm:px-10">
        <Wordmark className="text-sm" />
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => {
              unlockAudio();
              setMuted(!isMuted());
              setSound(!isMuted());
            }}
            aria-pressed={sound}
            className="rounded-full border border-line bg-surface/80 px-4 py-2 text-xs font-medium text-muted backdrop-blur transition-colors hover:text-fg"
          >
            {sound ? "Sound on" : "Sound off"}
          </button>
          <button
            type="button"
            onClick={finish}
            className="rounded-full border border-line bg-surface/80 px-4 py-2 text-xs font-medium text-muted backdrop-blur transition-colors hover:text-fg"
          >
            Skip intro
          </button>
        </div>
      </header>

      <div
        className={`pointer-events-none absolute inset-x-0 bottom-0 flex flex-col items-center px-5 pb-8 text-center transition-all duration-500 sm:pb-12 landscape:inset-y-0 landscape:right-auto landscape:w-[44%] landscape:items-start landscape:justify-center landscape:pb-0 landscape:pl-10 landscape:text-left lg:landscape:pl-20 ${
          busy ? "translate-y-6 opacity-0" : "opacity-100"
        }`}
      >
        <h2 className="text-4xl font-semibold leading-[1] tracking-[-0.03em] sm:text-6xl">
          Every great business
          <br />
          has a <span className="font-serif font-normal italic text-violet">story.</span>
        </h2>
        <p className="mt-4 max-w-sm text-base text-muted">Some opportunities are waiting to be unlocked.</p>
        <button
          type="button"
          onClick={open}
          disabled={phase !== "idle"}
          className="pointer-events-auto mt-7 inline-flex items-center gap-2 rounded-full bg-fg px-6 py-3 font-mono text-xs font-medium uppercase tracking-[0.18em] text-white shadow-[0_14px_40px_-14px_rgba(115,87,232,0.8)] transition-[background,transform] hover:-translate-y-0.5 hover:bg-violet disabled:opacity-50"
        >
          <svg aria-hidden width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="7.5" cy="15.5" r="4.5" />
            <path d="M10.7 12.3 21 2m-4 4 3 3m-6 0 3 3" />
          </svg>
          {phase === "loading" ? "Preparing…" : "Click the key to begin"}
        </button>
        <p className="mt-3 text-xs text-muted">Sound starts when you click · Esc to skip</p>
      </div>
    </div>
  );
}
