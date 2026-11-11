"use client";

import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger);

/**
 * The shop is closed: a cotton cloth hangs over the front, tied with a red satin ribbon, and a pair of scissors
 * rests beside it. Drag the scissors to the dotted line on the ribbon and let go (or just tap them, or press Enter):
 * the ribbon is snipped, the bow and tag fall, and the cloth drops (peeling down from the middle out), leaving the
 * page behind it to scroll. Once per visit; Esc or "Skip" opens it at once; people who prefer reduced motion never
 * see it.
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
  const ribbonTop = useRef<HTMLDivElement>(null);
  const ribbonBottom = useRef<HTMLDivElement>(null);
  const bow = useRef<SVGSVGElement>(null);
  const hint = useRef<HTMLDivElement>(null);
  const scissors = useRef<HTMLButtonElement>(null);
  const target = useRef<HTMLDivElement>(null);
  const drag = useRef<{ px: number; py: number; x: number; y: number; moved: number } | null>(null);
  const [near, setNear] = useState(false);

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
      gsap.to("[data-tag]", { rotate: 6, duration: 2.6, ease: "sine.inOut", yoyo: true, repeat: -1, transformOrigin: "50% 0%" });
      gsap.to("[data-blade='a']", { rotate: -9, duration: 0.5, ease: "power1.inOut", yoyo: true, repeat: -1, repeatDelay: 1.6, transformOrigin: "42% 50%" });
      gsap.to("[data-blade='b']", { rotate: 9, duration: 0.5, ease: "power1.inOut", yoyo: true, repeat: -1, repeatDelay: 1.6, transformOrigin: "42% 50%" });
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

  const cut = useCallback(() => {
    if (opening) return;
    setOpening(true);
    setNear(false);
    drag.current = null;
    gsap.killTweensOf("[data-sway],[data-ring],[data-tag],[data-blade]");
    const s = strips.current.filter(Boolean);
    const mid = (s.length - 1) / 2;
    const el = scissors.current;
    const t = target.current?.getBoundingClientRect();
    const here = el?.getBoundingClientRect();
    const tl = gsap.timeline({ onComplete: finish });
    // the scissors go to the dotted line (if they are not already there) and snip across the ribbon
    if (el && t && here) {
      tl.to(
        el,
        {
          x: `+=${t.left + t.width / 2 - (here.left + here.width * 0.8)}`,
          y: `+=${t.top + t.height / 2 - (here.top + here.height / 2)}`,
          rotate: 0,
          duration: 0.45,
          ease: "power2.inOut",
        },
        0,
      );
    }
    tl.to(hint.current, { opacity: 0, duration: 0.25 }, 0)
      .to("[data-blade='a']", { rotate: 16, duration: 0.14, repeat: 3, yoyo: true, ease: "power1.inOut", transformOrigin: "42% 50%" }, 0.45)
      .to("[data-blade='b']", { rotate: -16, duration: 0.14, repeat: 3, yoyo: true, ease: "power1.inOut", transformOrigin: "42% 50%" }, 0.45)
      .to("[data-cutline]", { opacity: 0, duration: 0.2 }, 0.75)
      // snipped: the lower length of ribbon and the scissors fall away
      .to([ribbonBottom.current, el], { y: "+=" + Math.round(window.innerHeight * 0.9), rotate: (i: number) => (i === 0 ? 5 : 24), duration: 0.8, ease: "power2.in" }, 0.85)
      // nothing holds the bow now: it slips, swings and drops with the upper length and the tag
      .to("[data-knot]", { scale: 1.1, duration: 0.15, transformOrigin: "50% 50%" }, 0.9)
      .to("[data-loop='l']", { rotate: -14, y: 14, transformOrigin: "100% 50%", duration: 0.5, ease: "power1.in" }, 0.95)
      .to("[data-loop='r']", { rotate: 14, y: 14, transformOrigin: "0% 50%", duration: 0.5, ease: "power1.in" }, 0.95)
      .to("[data-tail='l']", { rotate: 10, transformOrigin: "100% 0%", duration: 0.5, ease: "power1.in" }, 0.95)
      .to("[data-tail='r']", { rotate: -10, transformOrigin: "0% 0%", duration: 0.5, ease: "power1.in" }, 0.95)
      .to([ribbonTop.current, bow.current], { y: "115vh", rotate: (i: number) => (i === 0 ? -2 : 4), duration: 0.9, ease: "power2.in", transformOrigin: "50% 0%" }, 1.15)
      .to("[data-tag]", { y: "120vh", rotate: 22, duration: 0.9, ease: "power2.in" }, 1.05)
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
        1.55,
      );
  }, [opening, finish]);

  const onDown = (e: React.PointerEvent<HTMLButtonElement>) => {
    if (opening) return;
    e.currentTarget.setPointerCapture(e.pointerId);
    drag.current = { px: e.clientX, py: e.clientY, x: Number(gsap.getProperty(e.currentTarget, "x")), y: Number(gsap.getProperty(e.currentTarget, "y")), moved: 0 };
    gsap.killTweensOf("[data-blade]");
  };
  const onMove = (e: React.PointerEvent<HTMLButtonElement>) => {
    const d = drag.current;
    if (!d || opening) return;
    const dx = e.clientX - d.px;
    const dy = e.clientY - d.py;
    d.moved = Math.max(d.moved, Math.hypot(dx, dy));
    gsap.set(e.currentTarget, { x: d.x + dx, y: d.y + dy, rotate: Math.max(-14, Math.min(14, dx / 14)) });
    const dist = tipDistance(e.currentTarget);
    setNear(dist < 90);
    if (dist < 50) cut(); // the blades are on the line
  };
  /** How far the blade tips are from the dotted line, wherever the scissors were grabbed. */
  const tipDistance = (el: HTMLElement) => {
    const t = target.current?.getBoundingClientRect();
    if (!t) return Infinity;
    const r = el.getBoundingClientRect();
    return Math.hypot(r.left + r.width * 0.9 - (t.left + t.width / 2), r.top + r.height * 0.5 - (t.top + t.height / 2));
  };
  const onUp = (e: React.PointerEvent<HTMLButtonElement>) => {
    const d = drag.current;
    drag.current = null;
    if (d && (d.moved < 6 || tipDistance(e.currentTarget) < 110)) cut(); // a tap, or let go close to the line
  };

  useEffect(() => {
    if (!on) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && finish();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [on, finish]);

  if (!on) return null;

  return (
    <div ref={root} id="opening" className="fixed inset-0 z-[60] overflow-hidden" role="dialog" aria-label="Cut the ribbon to open the shop">
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

      {/* the ribbon: a satin band down the middle, in two lengths either side of the dotted cut line */}
      {(["top", "bottom"] as const).map((part) => (
        <div
          key={part}
          ref={part === "top" ? ribbonTop : ribbonBottom}
          aria-hidden
          className="pointer-events-none absolute left-1/2 w-[clamp(46px,7.2vw,84px)] -translate-x-1/2 shadow-[0_0_14px_rgba(40,10,0,.45)]"
          style={{
            top: part === "top" ? 0 : "72%",
            bottom: part === "top" ? "28%" : 0,
            clipPath: part === "top" ? "polygon(0 0,100% 0,100% 100%,0 calc(100% - 7px))" : "polygon(0 7px,100% 0,100% 100%,0 100%)",
            background:
              "repeating-linear-gradient(90deg, rgba(255,255,255,.05) 0 1px, rgba(0,0,0,0) 1px 3px), linear-gradient(90deg, #8f1d15 0%, #c93428 16%, #e8594a 38%, #f27a68 48%, #d8402f 62%, #b22a20 84%, #86190f 100%)",
          }}
        >
          <div className="absolute inset-y-0 left-[7%] w-px bg-[rgba(255,214,190,.45)]" />
          <div className="absolute inset-y-0 right-[7%] w-px bg-[rgba(255,214,190,.45)]" />
        </div>
      ))}

      {/* where to cut */}
      <div data-cutline className="pointer-events-none absolute left-1/2 top-[72%] -translate-x-1/2 -translate-y-1/2" aria-hidden>
        <div ref={target} className="mx-auto h-10 w-[clamp(110px,16vw,170px)]">
          <div className={`absolute inset-x-0 top-1/2 border-t-2 border-dashed transition-colors ${near ? "border-[#fff3c4]" : "border-[rgba(255,243,196,.8)]"}`} />
        </div>
        <p className={`mt-1 text-center font-serif text-base italic transition-opacity ${near ? "opacity-100" : "opacity-80"} text-[#fff3d1] [text-shadow:0_1px_6px_rgba(50,22,0,.8)]`}>cut here</p>
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

      {/* the scissors: drag them to the dotted line, or tap / press Enter */}
      <button
        ref={scissors}
        type="button"
        onPointerDown={onDown}
        onPointerMove={onMove}
        onPointerUp={onUp}
        onPointerCancel={() => (drag.current = null)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            cut();
          }
        }}
                aria-label="Scissors: drag them to the dotted line on the ribbon, or press Enter, to cut the ribbon and open the shop"
        className="absolute left-[calc(50%-clamp(150px,22vw,250px))] top-[60%] z-10 h-[clamp(74px,11vw,120px)] w-[clamp(74px,11vw,120px)] cursor-grab touch-none select-none outline-offset-6 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#fff3c4] active:cursor-grabbing"
        style={{ filter: "drop-shadow(0 8px 6px rgba(40,18,0,.55))" }}
      >
        <svg viewBox="0 0 120 120" className="h-full w-full" aria-hidden>
          <defs>
            <linearGradient id="steel" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0" stopColor="#f4f6f8" />
              <stop offset="0.5" stopColor="#b9c0c8" />
              <stop offset="1" stopColor="#7d858e" />
            </linearGradient>
            <linearGradient id="grip" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0" stopColor="#2a2623" />
              <stop offset="1" stopColor="#0f0d0c" />
            </linearGradient>
          </defs>
          <g data-blade="a">
            <path d="M44 61 L112 46 L112 52 L50 66 Z" fill="url(#steel)" stroke="#6b737b" strokeWidth=".6" />
            <path d="M44 62 C 30 66, 22 76, 22 88" stroke="url(#grip)" strokeWidth="6" fill="none" strokeLinecap="round" />
            <ellipse cx="17" cy="95" rx="13" ry="16" fill="none" stroke="url(#grip)" strokeWidth="6" transform="rotate(-22 17 95)" />
          </g>
          <g data-blade="b">
            <path d="M44 59 L112 74 L112 68 L50 54 Z" fill="url(#steel)" stroke="#6b737b" strokeWidth=".6" />
            <path d="M44 58 C 30 54, 22 44, 22 32" stroke="url(#grip)" strokeWidth="6" fill="none" strokeLinecap="round" />
            <ellipse cx="17" cy="25" rx="13" ry="16" fill="none" stroke="url(#grip)" strokeWidth="6" transform="rotate(22 17 25)" />
          </g>
          <circle cx="47" cy="60" r="4.2" fill="#8a929a" stroke="#3b4147" strokeWidth="1" />
        </svg>
      </button>

      <div ref={hint} className="pointer-events-none absolute inset-x-0 bottom-[11%] text-center text-[#fff7e0] [text-shadow:0_2px_10px_rgba(50,22,0,.7)]">
        <p className="font-serif text-2xl italic sm:text-3xl">The shop is closed.</p>
        <p className="mt-1 font-mono text-[11px] uppercase tracking-[0.24em]">Drag the scissors to the ribbon and cut</p>
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
