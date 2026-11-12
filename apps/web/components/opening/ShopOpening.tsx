"use client";

import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { ClothOpening } from "./ClothOpening";
import type { ClothScene } from "./ClothScene";

gsap.registerPlugin(ScrollTrigger);

/**
 * The opening: a real (simulated) cloth hangs over the closed shop, tied with a satin ribbon. Drag the scissors
 * to the ribbon, or tap them, or press Enter: the ribbon is cut, the rail lets go and the cloth falls away.
 *
 * - once per visit (`?opening` shows it again); Esc or Skip opens at once;
 * - not shown at all under reduced motion;
 * - without WebGL the drawn (CSS and SVG) version is used instead.
 */

const CUT_AT = 0.7; // how far down the screen the dotted line sits

function setGate(locked: boolean) {
  document.documentElement.dataset.gate = locked ? "locked" : "open";
  window.dispatchEvent(new CustomEvent("vyapar:gate", { detail: { locked } }));
}

function hasWebGL() {
  try {
    const c = document.createElement("canvas");
    return Boolean(c.getContext("webgl2") || c.getContext("webgl"));
  } catch {
    return false;
  }
}

export function ShopOpening() {
  const [mode, setMode] = useState<"pending" | "webgl" | "drawn" | "off">("pending");
  const [ready, setReady] = useState(false);
  const [cutting, setCutting] = useState(false);
  const [near, setNear] = useState(false);
  const [line, setLine] = useState<{ x: number; y: number } | null>(null);
  const root = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const scissors = useRef<HTMLButtonElement>(null);
  const scene = useRef<ClothScene | null>(null);
  const row = useRef(0);
  const drag = useRef<{ px: number; py: number; x: number; y: number; moved: number } | null>(null);

  useLayoutEffect(() => {
    let seen = false;
    try {
      seen = sessionStorage.getItem("vyapar.opened") === "1" && !location.search.includes("opening");
    } catch {
      /* storage unavailable: show it */
    }
    if (seen || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setMode("off");
      return;
    }
    if (!hasWebGL()) {
      setMode("drawn"); // the drawn version manages the scroll lock itself
      return;
    }
    window.scrollTo(0, 0);
    setGate(true);
    setMode("webgl");
    return () => setGate(false);
  }, []);

  const finish = useCallback(() => {
    try {
      sessionStorage.setItem("vyapar.opened", "1");
    } catch {
      /* ignore */
    }
    gsap.to(root.current, {
      opacity: 0,
      duration: 0.35,
      onComplete: () => {
        setMode("off");
        setGate(false);
        requestAnimationFrame(() => {
          ScrollTrigger.refresh();
          window.dispatchEvent(new Event("scroll"));
        });
      },
    });
  }, []);

  // build the scene once the canvas exists
  useEffect(() => {
    if (mode !== "webgl" || !canvas.current) return;
    let live = true;
    let stage: ClothScene | null = null;
    const place = () => {
      if (!stage) return;
      const p = stage.ribbonPoint(CUT_AT);
      if (!Number.isFinite(p.x) || !Number.isFinite(p.y)) return;
      row.current = p.row;
      setLine({ x: p.x, y: p.y });
    };
    const lowPower = window.innerWidth < 768 || (navigator.hardwareConcurrency ?? 8) <= 4;
    import("./ClothScene")
      .then(({ ClothScene }) => {
        if (!live || !canvas.current) return;
        stage = new ClothScene(canvas.current, { onDone: finish, lowPower });
        scene.current = stage;
        stage.start();
        place();
        setReady(true);
      })
      .catch(() => {
        setGate(false);
        setMode("drawn"); // a broken GPU driver should not leave the visitor locked out
      });
    const onResize = () => {
      stage?.resize();
      place();
    };
    const tick = window.setInterval(place, 400); // the ribbon sways: keep the dotted line on it
    window.addEventListener("resize", onResize);
    return () => {
      live = false;
      window.clearInterval(tick);
      window.removeEventListener("resize", onResize);
      stage?.dispose();
      scene.current = null;
    };
  }, [mode, finish]);

  // an idle snip so the scissors read as something to pick up
  useEffect(() => {
    if (!ready || cutting) return;
    const ctx = gsap.context(() => {
      gsap.to("[data-blade='a']", { rotate: -9, duration: 0.5, ease: "power1.inOut", yoyo: true, repeat: -1, repeatDelay: 1.7, transformOrigin: "42% 50%" });
      gsap.to("[data-blade='b']", { rotate: 9, duration: 0.5, ease: "power1.inOut", yoyo: true, repeat: -1, repeatDelay: 1.7, transformOrigin: "42% 50%" });
    }, root);
    return () => ctx.revert();
  }, [ready, cutting]);

  const cut = useCallback(() => {
    if (cutting || !scene.current || !line) return;
    setCutting(true);
    setNear(false);
    drag.current = null;
    gsap.killTweensOf("[data-blade]");
    const el = scissors.current;
    const here = el?.getBoundingClientRect();
    const tl = gsap.timeline();
    if (el && here) {
      tl.to(el, { x: `+=${line.x - (here.left + here.width * 0.86)}`, y: `+=${line.y - (here.top + here.height / 2)}`, rotate: 0, duration: 0.4, ease: "power2.inOut" }, 0);
    }
    tl.to("[data-hint]", { opacity: 0, duration: 0.25 }, 0)
      .to("[data-blade='a']", { rotate: 17, duration: 0.13, repeat: 3, yoyo: true, ease: "power1.inOut", transformOrigin: "42% 50%" }, 0.4)
      .to("[data-blade='b']", { rotate: -17, duration: 0.13, repeat: 3, yoyo: true, ease: "power1.inOut", transformOrigin: "42% 50%" }, 0.4)
      .add(() => scene.current?.cut(row.current), 0.72)
      .to("[data-cutline]", { opacity: 0, duration: 0.2 }, 0.72)
      .to(el, { y: "+=" + Math.round(window.innerHeight * 0.8), rotate: 28, opacity: 0, duration: 0.9, ease: "power2.in" }, 0.95);
  }, [cutting, line]);

  const tipDistance = (el: HTMLElement) => {
    if (!line) return Infinity;
    const r = el.getBoundingClientRect();
    return Math.hypot(r.left + r.width * 0.86 - line.x, r.top + r.height * 0.5 - line.y);
  };
  const onDown = (e: React.PointerEvent<HTMLButtonElement>) => {
    if (cutting) return;
    e.currentTarget.setPointerCapture(e.pointerId);
    drag.current = { px: e.clientX, py: e.clientY, x: Number(gsap.getProperty(e.currentTarget, "x")), y: Number(gsap.getProperty(e.currentTarget, "y")), moved: 0 };
    gsap.killTweensOf("[data-blade]");
  };
  const onMove = (e: React.PointerEvent<HTMLButtonElement>) => {
    const d = drag.current;
    if (!d || cutting) return;
    const dx = e.clientX - d.px;
    const dy = e.clientY - d.py;
    d.moved = Math.max(d.moved, Math.hypot(dx, dy));
    gsap.set(e.currentTarget, { x: d.x + dx, y: d.y + dy, rotate: Math.max(-14, Math.min(14, dx / 14)) });
    scene.current?.point(e.clientX, e.clientY);
    const dist = tipDistance(e.currentTarget);
    setNear(dist < 90);
    if (dist < 46) cut();
  };
  const onUp = (e: React.PointerEvent<HTMLButtonElement>) => {
    const d = drag.current;
    drag.current = null;
    if (d && (d.moved < 6 || tipDistance(e.currentTarget) < 110)) cut();
  };

  useEffect(() => {
    if (mode !== "webgl") return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && finish();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [mode, finish]);

  if (mode === "off") return null;
  if (mode === "drawn") return <ClothOpening />;

  return (
    <div
      ref={root}
      id="opening"
      role="dialog"
      aria-label="Cut the ribbon to open the shop"
      className="fixed inset-0 z-[60] overflow-hidden"
      onPointerMove={(e) => !drag.current && scene.current?.point(e.clientX, e.clientY)}
    >
      {/* until the scene is drawn, a plain cloth colour: never a flash of the page behind */}
      <div className={`absolute inset-0 bg-[#c98f1f] transition-opacity duration-500 ${ready ? "opacity-0" : "opacity-100"}`} aria-hidden />
      <canvas ref={canvas} className="absolute inset-0 h-full w-full" aria-hidden />

      {ready && line && (
        <div data-cutline className="pointer-events-none absolute -translate-x-1/2 -translate-y-1/2" style={{ left: line.x, top: line.y }} aria-hidden>
          <div className={`h-0 w-[clamp(110px,15vw,170px)] border-t-2 border-dashed transition-colors ${near ? "border-white" : "border-[rgba(255,246,214,.85)]"}`} />
          <p className="mt-1.5 text-center font-serif text-base italic text-[#fff6d6] [text-shadow:0_1px_8px_rgba(40,18,0,.9)]">cut here</p>
        </div>
      )}

      {ready && (
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
          className="absolute left-[calc(50%-clamp(150px,22vw,260px))] top-[58%] z-10 h-[clamp(78px,11vw,124px)] w-[clamp(78px,11vw,124px)] cursor-grab touch-none select-none outline-offset-8 focus-visible:outline focus-visible:outline-2 focus-visible:outline-white active:cursor-grabbing"
          style={{ filter: "drop-shadow(0 10px 8px rgba(30,12,0,.6))" }}
        >
          <svg viewBox="0 0 120 120" className="h-full w-full" aria-hidden>
            <defs>
              <linearGradient id="so-steel" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0" stopColor="#fbfcfd" />
                <stop offset="0.45" stopColor="#c3c9d0" />
                <stop offset="1" stopColor="#7a828b" />
              </linearGradient>
              <linearGradient id="so-grip" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0" stopColor="#3a3430" />
                <stop offset="1" stopColor="#0f0d0c" />
              </linearGradient>
            </defs>
            <g data-blade="a">
              <path d="M44 61 L113 45 L113 52 L50 66 Z" fill="url(#so-steel)" stroke="#646c74" strokeWidth=".6" />
              <path d="M52 62 L110 49" stroke="#fff" strokeOpacity=".7" strokeWidth=".8" />
              <path d="M44 62 C 30 66, 22 76, 22 88" stroke="url(#so-grip)" strokeWidth="6.5" fill="none" strokeLinecap="round" />
              <ellipse cx="17" cy="95" rx="13" ry="16" fill="none" stroke="url(#so-grip)" strokeWidth="6.5" transform="rotate(-22 17 95)" />
            </g>
            <g data-blade="b">
              <path d="M44 59 L113 75 L113 68 L50 54 Z" fill="url(#so-steel)" stroke="#646c74" strokeWidth=".6" />
              <path d="M44 58 C 30 54, 22 44, 22 32" stroke="url(#so-grip)" strokeWidth="6.5" fill="none" strokeLinecap="round" />
              <ellipse cx="17" cy="25" rx="13" ry="16" fill="none" stroke="url(#so-grip)" strokeWidth="6.5" transform="rotate(22 17 25)" />
            </g>
            <circle cx="47" cy="60" r="4.4" fill="#9aa2aa" stroke="#3b4147" strokeWidth="1" />
            <circle cx="46" cy="59" r="1.4" fill="#fff" fillOpacity=".8" />
          </svg>
        </button>
      )}

      <div data-hint className="pointer-events-none absolute inset-x-0 bottom-[9%] text-center text-[#fff7e0] [text-shadow:0_2px_12px_rgba(40,18,0,.85)] [@media(max-height:520px)]:bottom-1">
        <p className="font-serif text-3xl italic sm:text-4xl [@media(max-height:520px)]:hidden">The shop is closed.</p>
        <p className="mt-2 font-mono text-[11px] uppercase tracking-[0.26em]">{ready ? "Drag the scissors to the ribbon and cut" : "Hanging the cloth…"}</p>
      </div>

      <button
        type="button"
        onClick={finish}
        className="absolute right-4 top-4 rounded-full bg-[rgba(30,14,0,.5)] px-4 py-2 font-mono text-[11px] uppercase tracking-wider text-[#fff3d1] backdrop-blur hover:bg-[rgba(30,14,0,.7)]"
      >
        Skip
      </button>
    </div>
  );
}
