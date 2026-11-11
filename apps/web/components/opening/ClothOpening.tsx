"use client";

import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger);

/**
 * The shop is closed: a cotton cloth hangs over the front, tied with a red satin ribbon.
 * Tap the bow and it comes undone, the ribbon is pulled away, the cloth drops (peeling down from the middle out)
 * and the page behind it is there to scroll. Once per visit; Esc or "Skip" opens it at once; people who prefer
 * reduced motion never see it.
 */

const STRIPS = 12;

// Woven cotton: warp threads run down, weft across. Drawn once by the browser into a small tile.
const tile = (freq: string, seed: number, alpha: number) =>
  `url("data:image/svg+xml;utf8,${encodeURIComponent(
    `<svg xmlns='http://www.w3.org/2000/svg' width='240' height='240'><filter id='n' x='0' y='0' width='100%' height='100%'><feTurbulence type='fractalNoise' baseFrequency='${freq}' numOctaves='3' seed='${seed}' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 0.25  0 0 0 0 0.14  0 0 0 0 0  0 0 0 ${alpha} 0'/></filter><rect width='100%' height='100%' filter='url(#n)'/></svg>`,
  )}")`;

const CLOTH = [
  tile("0.85 0.04", 3, 0.9), // warp threads
  tile("0.05 0.7", 8, 0.55), // weft threads
  // soft folds: three layers of different widths so the pattern never visibly repeats
  "linear-gradient(90deg, rgba(60,28,0,.30) 0%, rgba(60,28,0,0) 34%, rgba(255,236,170,.20) 62%, rgba(60,28,0,0) 100%) 0 0 / 11.3% 100%",
  "linear-gradient(90deg, rgba(60,28,0,0) 0%, rgba(60,28,0,.22) 41%, rgba(255,236,170,.16) 55%, rgba(60,28,0,0) 100%) 0 0 / 17.9% 100%",
  "linear-gradient(90deg, rgba(255,236,170,.14) 0%, rgba(60,28,0,.16) 48%, rgba(60,28,0,0) 100%) 0 0 / 29.3% 100%",
  // gathered at the top, hangs loose below
  "linear-gradient(180deg, rgba(50,22,0,.55) 0%, rgba(50,22,0,.16) 9%, rgba(50,22,0,0) 24%)",
  "repeating-linear-gradient(90deg, rgba(50,22,0,.30) 0 2px, rgba(50,22,0,0) 2px 2.6%) 0 0 / 100% 20% no-repeat",
  // weight at the hem, and a little light from the upper left
  "linear-gradient(0deg, rgba(50,22,0,.34) 0%, rgba(50,22,0,0) 16%)",
  "radial-gradient(120% 90% at 30% 10%, rgba(255,226,140,.22), rgba(255,226,140,0) 60%)",
  "#d49a22",
].join(", ");

function Hem() {
  return (
    <>
      <div aria-hidden className="absolute inset-x-0 bottom-[5.5%] h-px bg-[rgba(70,34,0,.55)]" />
      <div aria-hidden className="absolute inset-x-0 bottom-[calc(5.5%-6px)] h-0 border-t-2 border-dashed border-[rgba(255,236,170,.55)]" />
    </>
  );
}

function setGate(locked: boolean) {
  document.documentElement.dataset.gate = locked ? "locked" : "open";
  window.dispatchEvent(new CustomEvent("vyapar:gate", { detail: { locked } }));
}

export function ClothOpening() {
  const [on, setOn] = useState(true);
  const [opening, setOpening] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const strips = useRef<HTMLDivElement[]>([]);
  const ribbon = useRef<HTMLDivElement>(null);
  const bow = useRef<SVGSVGElement>(null);
  const hint = useRef<HTMLDivElement>(null);

  // Decide before paint whether to show it at all.
  useLayoutEffect(() => {
    let seen = false;
    try {
      seen = sessionStorage.getItem("vyapar.opened") === "1" && !location.search.includes("opening");
    } catch {
      /* storage unavailable: show it */
    }
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (seen || reduced) {
      setOn(false);
      return;
    }
    window.scrollTo(0, 0);
    setGate(true);
    return () => setGate(false);
  }, []);

  // A slow sway so the cloth is not a still picture, and a ring that asks for the tap.
  useEffect(() => {
    if (!on || opening) return;
    const ctx = gsap.context(() => {
      gsap.to("[data-sway]", { skewX: 0.35, duration: 3.2, ease: "sine.inOut", yoyo: true, repeat: -1, stagger: { each: 0.18, from: "center" } });
      gsap.fromTo("[data-ring]", { scale: 0.7, opacity: 0.9 }, { scale: 1.7, opacity: 0, duration: 1.8, ease: "power1.out", repeat: -1 });
      gsap.to("[data-tag]", { rotate: 6, duration: 2.6, ease: "sine.inOut", yoyo: true, repeat: -1, transformOrigin: "50% 0%" });
    }, root);
    return () => ctx.revert();
  }, [on, opening]);

  const finish = useCallback(() => {
    try {
      sessionStorage.setItem("vyapar.opened", "1");
    } catch {
      /* ignore */
    }
    setOn(false);
    setGate(false);
    requestAnimationFrame(() => {
      ScrollTrigger.refresh();
      window.dispatchEvent(new Event("scroll"));
    });
  }, []);

  const open = useCallback(() => {
    if (opening) return;
    setOpening(true);
    gsap.killTweensOf("[data-sway],[data-ring],[data-tag]");
    const s = strips.current.filter(Boolean);
    const mid = (s.length - 1) / 2;
    const tl = gsap.timeline({ onComplete: finish });
    tl.to(hint.current, { opacity: 0, duration: 0.25 }, 0)
      // the knot gives, the loops fall slack and the tails swing
      .to("[data-knot]", { scale: 1.15, duration: 0.18, transformOrigin: "50% 50%", ease: "power2.out" }, 0)
      .to("[data-loop='l']", { rotate: -34, scaleX: 0.55, y: 46, transformOrigin: "100% 50%", duration: 0.55, ease: "power2.in" }, 0.12)
      .to("[data-loop='r']", { rotate: 34, scaleX: 0.55, y: 46, transformOrigin: "0% 50%", duration: 0.55, ease: "power2.in" }, 0.12)
      .to("[data-knot]", { scale: 0, duration: 0.3, transformOrigin: "50% 50%", ease: "back.in(2)" }, 0.3)
      .to("[data-tail='l']", { rotate: 18, transformOrigin: "100% 0%", duration: 0.5, ease: "power2.in" }, 0.15)
      .to("[data-tail='r']", { rotate: -18, transformOrigin: "0% 0%", duration: 0.5, ease: "power2.in" }, 0.15)
      .to("[data-tag]", { y: "120vh", rotate: 20, duration: 0.9, ease: "power2.in" }, 0.2)
      // the ribbon is pulled down and out
      .to(bow.current, { y: "115vh", duration: 0.85, ease: "power2.in" }, 0.45)
      .to(ribbon.current, { y: "115vh", duration: 0.85, ease: "power2.in" }, 0.5)
      // the cloth lets go from the middle outward, each strip a little out of step
      .to(
        s,
        {
          y: () => window.innerHeight * 1.12,
          rotate: (i: number) => (i < mid ? -1 : 1) * (1.2 + Math.abs(i - mid) * 0.5),
          skewY: (i: number) => (i - mid) * 0.5,
          duration: 1.05,
          ease: "power3.in",
          stagger: { each: 0.045, from: "center" },
        },
        0.85,
      )
      .to(root.current, { backgroundColor: "rgba(0,0,0,0)", duration: 0.2 }, 0.85);
  }, [opening, finish]);

  useEffect(() => {
    if (!on) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && finish();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [on, finish]);

  if (!on) return null;

  return (
    <div ref={root} id="opening" className="fixed inset-0 z-[60] overflow-hidden" role="dialog" aria-label="Open the shop">
      {/* the cloth, as vertical strips so it can come away in pieces; each strip shows the same full-width cloth */}
      <div className="absolute inset-0 flex" aria-hidden>
        {Array.from({ length: STRIPS }, (_, i) => (
          <div
            key={i}
            ref={(el) => {
              if (el) strips.current[i] = el;
            }}
            className="relative h-full flex-1 overflow-hidden shadow-[2px_0_8px_-2px_rgba(40,18,0,.55)] will-change-transform"
          >
            <div
              data-sway
              className="absolute inset-y-0 will-change-transform"
              style={{ width: "100vw", left: `calc(${-i} * (100vw / ${STRIPS}))`, background: CLOTH }}
            >
              <Hem />
            </div>
          </div>
        ))}
      </div>

      {/* the ribbon: a satin band down the middle */}
      <div
        ref={ribbon}
        aria-hidden
        className="pointer-events-none absolute inset-y-0 left-1/2 w-[clamp(46px,7.2vw,84px)] -translate-x-1/2 shadow-[0_0_14px_rgba(40,10,0,.45)]"
        style={{
          background:
            "repeating-linear-gradient(90deg, rgba(255,255,255,.05) 0 1px, rgba(0,0,0,0) 1px 3px), linear-gradient(90deg, #8f1d15 0%, #c93428 16%, #e8594a 38%, #f27a68 48%, #d8402f 62%, #b22a20 84%, #86190f 100%)",
        }}
      >
        <div className="absolute inset-y-0 left-[7%] w-px bg-[rgba(255,214,190,.45)]" />
        <div className="absolute inset-y-0 right-[7%] w-px bg-[rgba(255,214,190,.45)]" />
      </div>

      {/* the bow, with the wordmark on a paper tag */}
      <svg
        ref={bow}
        viewBox="0 0 420 520"
        className="pointer-events-none absolute left-1/2 top-1/2 w-[clamp(250px,38vw,420px)] -translate-x-1/2 -translate-y-[52%]"
        aria-hidden
      >
        <defs>
          <linearGradient id="satin" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#f26f5d" />
            <stop offset="0.45" stopColor="#d23b2c" />
            <stop offset="1" stopColor="#97200f" />
          </linearGradient>
          <linearGradient id="satin2" x1="1" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#f26f5d" />
            <stop offset="0.45" stopColor="#d23b2c" />
            <stop offset="1" stopColor="#97200f" />
          </linearGradient>
          <linearGradient id="inner" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#7d150b" />
            <stop offset="1" stopColor="#b02c1f" />
          </linearGradient>
          <filter id="soft" x="-20%" y="-20%" width="140%" height="150%">
            <feDropShadow dx="0" dy="5" stdDeviation="5" floodColor="#2a0e00" floodOpacity="0.45" />
          </filter>
          <linearGradient id="paper" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#f3e3c3" />
            <stop offset="1" stopColor="#dcc79c" />
          </linearGradient>
        </defs>

        <g filter="url(#soft)">
          {/* tails */}
          <g data-tail="l">
            <path d="M188 214 C 170 270, 140 330, 118 396 L 144 384 L 150 420 L 196 232 Z" fill="url(#satin)" />
            <path d="M188 214 C 184 240, 176 262, 170 282" stroke="#ffb3a2" strokeOpacity=".5" strokeWidth="2" fill="none" />
          </g>
          <g data-tail="r">
            <path d="M232 214 C 250 270, 280 330, 302 396 L 276 384 L 270 420 L 224 232 Z" fill="url(#satin2)" />
            <path d="M232 214 C 236 240, 244 262, 250 282" stroke="#ffb3a2" strokeOpacity=".5" strokeWidth="2" fill="none" />
          </g>
          {/* loops */}
          <g data-loop="l">
            <path d="M200 196 C 150 120, 62 104, 40 168 C 24 222, 110 252, 200 222 Z" fill="url(#satin)" />
            <path d="M196 200 C 150 150, 92 142, 78 178 C 68 208, 120 224, 196 216 Z" fill="url(#inner)" opacity=".85" />
            <path d="M60 158 C 90 128, 140 138, 180 176" stroke="#ffc0b0" strokeOpacity=".55" strokeWidth="2.4" fill="none" />
          </g>
          <g data-loop="r">
            <path d="M220 196 C 270 120, 358 104, 380 168 C 396 222, 310 252, 220 222 Z" fill="url(#satin2)" />
            <path d="M224 200 C 270 150, 328 142, 342 178 C 352 208, 300 224, 224 216 Z" fill="url(#inner)" opacity=".85" />
            <path d="M360 158 C 330 128, 280 138, 240 176" stroke="#ffc0b0" strokeOpacity=".55" strokeWidth="2.4" fill="none" />
          </g>
          {/* knot */}
          <g data-knot>
            <rect x="186" y="186" width="48" height="56" rx="14" fill="url(#satin)" />
            <path d="M192 196 C 204 192, 216 192, 228 196" stroke="#ffc0b0" strokeOpacity=".6" strokeWidth="2.4" fill="none" />
            <path d="M190 228 C 204 234, 216 234, 230 228" stroke="#6b1109" strokeOpacity=".5" strokeWidth="2" fill="none" />
          </g>
        </g>

        {/* the tag, tied on with string */}
        <g data-tag filter="url(#soft)" style={{ transformBox: "fill-box" }}>
          <path d="M214 232 C 236 262, 270 270, 296 286" stroke="#6b4a24" strokeWidth="2" fill="none" />
          <g transform="translate(262 282) rotate(8)">
            <path d="M0 14 L 14 0 L 118 0 L 118 74 L 14 74 L 0 60 Z" fill="url(#paper)" stroke="#a98e5c" strokeWidth="1" />
            <circle cx="14" cy="14" r="4" fill="#8a6c3a" opacity=".7" />
            <text x="62" y="40" textAnchor="middle" fontFamily="var(--font-display, sans-serif)" fontWeight="800" fontSize="22" fill="#1b1612">
              vyapar
            </text>
            <text x="62" y="62" textAnchor="middle" fontFamily="var(--font-serif, serif)" fontStyle="italic" fontSize="21" fill="#a3241c">
              .ai
            </text>
          </g>
        </g>
      </svg>

      {/* the tap target and the ring that invites it */}
      <button
        type="button"
        onClick={open}
        disabled={opening}
        aria-label="Open the shop"
        className="absolute left-1/2 top-1/2 h-[clamp(120px,18vw,190px)] w-[clamp(150px,24vw,260px)] -translate-x-1/2 -translate-y-[40%] cursor-pointer rounded-full outline-offset-4 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#fff3c4]"
      >
        <span data-ring aria-hidden className="absolute inset-[18%] rounded-full border-2 border-[#ffe9a8]/80" />
      </button>

      <div ref={hint} className="pointer-events-none absolute inset-x-0 bottom-[11%] text-center text-[#fff7e0] [text-shadow:0_2px_10px_rgba(50,22,0,.7)]">
        <p className="font-serif text-2xl italic sm:text-3xl">The shop is closed.</p>
        <p className="mt-1 font-mono text-[11px] uppercase tracking-[0.24em]">Pull the ribbon to open</p>
      </div>

      <button
        type="button"
        onClick={finish}
        className="absolute right-4 top-4 rounded-full bg-[rgba(40,18,0,.45)] px-4 py-2 font-mono text-[11px] uppercase tracking-wider text-[#fff3d1] backdrop-blur hover:bg-[rgba(40,18,0,.65)]"
      >
        Skip
      </button>
    </div>
  );
}
