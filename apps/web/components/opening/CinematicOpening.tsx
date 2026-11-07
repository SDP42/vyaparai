"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useState } from "react";
import { Logo } from "@/components/landing/Nav";
import { isMuted, setMuted, unlockAudio } from "@/lib/sfx";

const ShopScene = dynamic(() => import("./ShopScene"), { ssr: false });

type Phase = "loading" | "idle" | "opening" | "diving" | "done";

function setGateLock(locked: boolean) {
  document.documentElement.dataset.gate = locked ? "locked" : "open";
  window.dispatchEvent(new CustomEvent("vyapar:gate", { detail: { locked } }));
}

/** Page 1: the closed shop at night. Click the key to open it; then the landing page. */
export function CinematicOpening() {
  const [phase, setPhase] = useState<Phase>("loading");
  const [mount, setMount] = useState(false);
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
    setMuted(true); // start muted; sound turns on when the visitor clicks the key
    window.scrollTo(0, 0);
    setGateLock(true);
    // fonts are painted onto the sign texture; don't wait more than 1.5 s for them
    const go = () => setMount(true);
    const t = window.setTimeout(go, 1500);
    document.fonts.ready.then(() => {
      window.clearTimeout(t);
      go();
    });
    return () => window.clearTimeout(t);
  }, []);

  const finish = useCallback(() => {
    setPhase("done");
    setGateLock(false);
    window.scrollTo(0, 0);
  }, []);

  const onLoaded = useCallback(() => setPhase((p) => (p === "loading" ? "idle" : p)), []);
  const open = useCallback(() => {
    unlockAudio();
    setMuted(false);
    setSound(true);
    setPhase((p) => (p === "idle" ? "opening" : p));
  }, []);
  const onDive = useCallback(() => setPhase("diving"), []);

  useEffect(() => {
    if (phase !== "diving") return;
    const t = window.setTimeout(finish, 1600);
    return () => window.clearTimeout(t);
  }, [phase, finish]);

  useEffect(() => {
    if (phase === "done") return;
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
      className={`fixed inset-0 z-[90] overflow-hidden bg-[radial-gradient(ellipse_at_62%_40%,#1d1a1c_0%,#0d0f16_60%,#07080c_100%)] transition-opacity duration-700 ${
        phase === "diving" ? "pointer-events-none opacity-0 delay-700" : "opacity-100"
      }`}
      role="dialog"
      aria-label="Opening: unlock the shop"
      onTransitionEnd={(e) => {
        if (phase === "diving" && e.target === e.currentTarget) finish();
      }}
    >
      <div className="absolute inset-0">
        {mount && <ShopScene opening={busy} onKeyClick={open} onDive={onDive} onLoaded={onLoaded} />}
      </div>
      {/* cinematic vignette */}
      <div aria-hidden className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_45%,rgba(0,0,0,0.55)_100%)]" />

      <header className="absolute inset-x-0 top-0 flex items-center justify-between px-5 py-5 text-[#f6efe2] sm:px-10">
        <Logo />
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => {
              unlockAudio();
              setMuted(!isMuted());
              setSound(!isMuted());
            }}
            aria-pressed={sound}
            className="rounded-full border border-white/20 bg-white/5 px-4 py-2 text-xs font-medium text-white/75 backdrop-blur transition-colors hover:text-white"
          >
            {sound ? "Sound on" : "Sound off"}
          </button>
          <button
            type="button"
            onClick={finish}
            className="rounded-full border border-white/20 bg-white/5 px-4 py-2 text-xs font-medium text-white/75 backdrop-blur transition-colors hover:text-white"
          >
            Skip intro
          </button>
        </div>
      </header>

      <div
        className={`pointer-events-none absolute inset-x-0 bottom-0 flex flex-col items-center px-5 pb-10 text-center text-[#f6efe2] transition-all duration-500 landscape:inset-y-0 landscape:right-auto landscape:w-[42%] landscape:items-start landscape:justify-center landscape:pb-0 landscape:pl-10 landscape:text-left lg:landscape:pl-20 ${
          busy ? "translate-y-6 opacity-0" : "opacity-100"
        }`}
      >
        <h2 className="text-4xl font-extrabold leading-[0.98] tracking-tight sm:text-6xl">
          Every great business
          <br />
          has a <span className="font-serif font-normal italic text-haldi">story.</span>
        </h2>
        <p className="mt-4 max-w-sm text-base text-white/65">Some opportunities are waiting to be unlocked.</p>
        <button
          type="button"
          onClick={open}
          disabled={phase !== "idle"}
          className="pointer-events-auto mt-8 inline-flex items-center gap-2 rounded-full bg-haldi px-6 py-3 font-mono text-xs font-semibold uppercase tracking-[0.18em] text-ink shadow-[0_14px_40px_-14px_rgba(242,167,27,0.7)] transition-[background,transform] hover:-translate-y-0.5 hover:bg-[#ffc24d] disabled:opacity-50"
        >
          <svg aria-hidden width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="7.5" cy="15.5" r="4.5" />
            <path d="M10.7 12.3 21 2m-4 4 3 3m-6 0 3 3" />
          </svg>
          {phase === "loading" ? "Preparing…" : "Click the key to begin"}
        </button>
        <p className="mt-3 text-xs text-white/45">Sound starts when you click · Esc to skip</p>
      </div>
    </div>
  );
}
