"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { Logo } from "@/components/landing/Nav";
import { isMuted, setMuted, sfx, unlockAudio } from "@/lib/sfx";

gsap.registerPlugin(ScrollTrigger);

const ShopScene = dynamic(() => import("./ShopScene"), { ssr: false });

type State = "loading" | "idle" | "inserting" | "scroll" | "off";

function setGateLock(locked: boolean) {
  document.documentElement.dataset.gate = locked ? "locked" : "open";
  window.dispatchEvent(new CustomEvent("vyapar:gate", { detail: { locked } }));
}

/** Opacity for a caption that is visible between a and b (with soft edges). */
const windowed = (p: number, a: number, b: number, edge = 0.025) =>
  Math.max(0, Math.min(1, (p - a) / edge, (b - p) / edge));

/** How much of the section's scroll belongs to the 3D sequence (the rest is the hand-off). */
const SCENE_SHARE = 0.82;

/**
 * Page 1: the closed shop at night. Click the key → it enters the lock → scroll to unlock →
 * shutter rises → walk in → hand-off to the landing page. Fully reversible on scroll-back.
 */
export function CinematicOpening() {
  const [state, setState] = useState<State>("loading");
  const [mount, setMount] = useState(false);
  const [sound, setSound] = useState(false);
  const [lowPower, setLowPower] = useState(false);
  const section = useRef<HTMLElement>(null);
  const progress = useRef(0);
  const hint = useRef<HTMLDivElement>(null);
  const ring = useRef<SVGCircleElement>(null);
  const cap1 = useRef<HTMLParagraphElement>(null);
  const cap2 = useRef<HTMLParagraphElement>(null);
  const handoff = useRef<HTMLDivElement>(null);
  const brand = useRef<HTMLDivElement>(null);

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
      setState("off");
      return;
    }
    setLowPower(window.innerWidth < 768 || (navigator.hardwareConcurrency ?? 8) <= 4);
    setMuted(true); // start muted; sound turns on with the click on the key
    window.scrollTo(0, 0);
    setGateLock(true);
    const go = () => setMount(true);
    const t = window.setTimeout(go, 1500);
    document.fonts.ready.then(() => {
      window.clearTimeout(t);
      go();
    });
    return () => {
      window.clearTimeout(t);
      setGateLock(false);
    };
  }, []);

  // Scroll → progress (only meaningful once the key is in the lock).
  useLayoutEffect(() => {
    const el = section.current;
    if (!el || state === "off") return;
    const st = ScrollTrigger.create({
      trigger: el,
      start: "top top",
      end: "bottom bottom",
      onUpdate: (s) => {
        const p = s.progress;
        progress.current = Math.min(1, p / SCENE_SHARE);
        if (hint.current) hint.current.style.opacity = String(state === "scroll" ? Math.max(0, 1 - p / 0.06) : 0);
        if (ring.current) ring.current.style.strokeDashoffset = String(1 - Math.min(1, p / SCENE_SHARE));
        if (cap1.current) cap1.current.style.opacity = String(windowed(p, 0.6, 0.71));
        if (cap2.current) cap2.current.style.opacity = String(windowed(p, 0.71, 0.82));
        const h = Math.max(0, Math.min(1, (p - 0.8) / 0.08));
        if (handoff.current) handoff.current.style.opacity = String(h);
        if (brand.current) {
          const b = Math.max(0, Math.min(1, (p - 0.86) / 0.06));
          brand.current.style.opacity = String(b);
          brand.current.style.transform = `translateY(${(1 - b) * 24}px) scale(${0.96 + b * 0.04})`;
        }
        if (p > 0.84) sfx.ambience(false);
      },
    });
    return () => st.kill();
  }, [state]);

  const onLoaded = useCallback(() => setState((s) => (s === "loading" ? "idle" : s)), []);
  const onKeyClick = useCallback(() => {
    unlockAudio();
    setMuted(false);
    setSound(true);
    setState((s) => (s === "idle" ? "inserting" : s));
  }, []);
  const onInserted = useCallback(() => {
    setState("scroll");
    setGateLock(false);
  }, []);

  const skip = useCallback(() => {
    setGateLock(false);
    sfx.ambience(false);
    requestAnimationFrame(() => {
      const hero = document.getElementById("top");
      if (hero) window.scrollTo({ top: hero.getBoundingClientRect().top + window.scrollY, behavior: "instant" as ScrollBehavior });
    });
  }, []);

  useEffect(() => {
    if (state === "off") return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") skip();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [state, skip]);

  if (state === "off") return null;
  const started = state === "inserting" || state === "scroll";

  return (
    <section ref={section} id="opening" aria-label="Opening: unlock the shop" className="relative h-[700vh] bg-[#07080c]">
      <div className="sticky top-0 h-dvh w-full overflow-hidden bg-[radial-gradient(ellipse_at_62%_40%,#1d1a1c_0%,#0d0f16_60%,#07080c_100%)]">
        <div className="absolute inset-0">
          {mount && (
            <ShopScene
              started={started}
              progress={progress}
              lowPower={lowPower}
              onKeyClick={onKeyClick}
              onInserted={onInserted}
              onLoaded={onLoaded}
            />
          )}
        </div>
        <div aria-hidden className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_50%,rgba(0,0,0,0.45)_100%)]" />

        <header className="absolute inset-x-0 top-0 z-10 flex items-center justify-between px-5 py-5 text-[#f6efe2] sm:px-10">
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
              onClick={skip}
              className="rounded-full border border-white/20 bg-white/5 px-4 py-2 text-xs font-medium text-white/75 backdrop-blur transition-colors hover:text-white"
            >
              Skip intro
            </button>
          </div>
        </header>

        {/* Stage 1 copy */}
        <div
          className={`pointer-events-none absolute inset-x-0 bottom-0 flex flex-col items-center px-5 pb-10 text-center text-[#f6efe2] transition-all duration-700 landscape:inset-y-0 landscape:right-auto landscape:w-[42%] landscape:items-start landscape:justify-center landscape:pb-0 landscape:pl-10 landscape:text-left lg:landscape:pl-20 ${
            started ? "translate-y-6 opacity-0" : "opacity-100"
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
            onClick={onKeyClick}
            disabled={state !== "idle"}
            className="pointer-events-auto mt-8 inline-flex items-center gap-2 rounded-full bg-haldi px-6 py-3 font-mono text-xs font-semibold uppercase tracking-[0.18em] text-ink shadow-[0_14px_40px_-14px_rgba(242,167,27,0.7)] transition-[background,transform] hover:-translate-y-0.5 hover:bg-[#ffc24d] disabled:opacity-50"
          >
            <svg aria-hidden width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="7.5" cy="15.5" r="4.5" />
              <path d="M10.7 12.3 21 2m-4 4 3 3m-6 0 3 3" />
            </svg>
            {state === "loading" ? "Preparing…" : "Click the key to begin"}
          </button>
          <p className="mt-3 text-xs text-white/45">Sound starts when you click · Esc to skip</p>
        </div>

        {/* Stage 3: scroll to unlock */}
        <div
          ref={hint}
          className="pointer-events-none absolute bottom-10 left-1/2 flex -translate-x-1/2 flex-col items-center gap-3 text-[#f6efe2] opacity-0 transition-opacity duration-500"
          style={{ opacity: state === "scroll" ? 1 : 0 }}
          aria-live="polite"
        >
          <svg width="46" height="46" viewBox="0 0 46 46" aria-hidden>
            <circle cx="23" cy="23" r="20" fill="none" stroke="rgba(255,255,255,0.18)" strokeWidth="2" />
            <circle
              ref={ring}
              cx="23"
              cy="23"
              r="20"
              fill="none"
              stroke="#f2a71b"
              strokeWidth="2"
              pathLength={1}
              strokeDasharray="1"
              strokeDashoffset="1"
              transform="rotate(-90 23 23)"
            />
          </svg>
          <p className="font-mono text-xs uppercase tracking-[0.3em]">{state === "scroll" ? "Scroll to unlock" : ""}</p>
        </div>

        {/* Stage 4 captions */}
        <div className="pointer-events-none absolute inset-x-0 bottom-[14%] text-center text-[#f6efe2] [text-shadow:0_2px_24px_rgba(0,0,0,0.6)]">
          <p ref={cap1} className="absolute inset-x-0 text-4xl font-extrabold tracking-tight opacity-0 sm:text-6xl">
            Your business is <span className="font-serif font-normal italic text-haldi">open.</span>
          </p>
          <p ref={cap2} className="absolute inset-x-0 text-4xl font-extrabold tracking-tight opacity-0 sm:text-6xl">
            Now, let&apos;s make it <span className="font-serif font-normal italic text-haldi">intelligent.</span>
          </p>
        </div>

        {/* Stage 5: hand-off into the landing page (same cream as the hero) */}
        <div ref={handoff} className="pointer-events-none absolute inset-0 bg-canvas opacity-0">
          <div aria-hidden className="ledger-rules absolute inset-0 opacity-60" />
        </div>
        <div ref={brand} className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center px-5 text-center opacity-0">
          <p className="font-mono text-[11px] uppercase tracking-[0.3em] text-sindoor">Welcome to</p>
          <p className="mt-3 text-[clamp(3rem,11vw,9rem)] font-extrabold leading-none tracking-tight text-fg">
            VYAPAR<span className="font-serif font-normal italic text-haldi-deep">.ai</span>
          </p>
          <p className="mt-5 max-w-md text-lg text-fg/70">Unlock the intelligence behind your business.</p>
        </div>
      </div>
    </section>
  );
}
