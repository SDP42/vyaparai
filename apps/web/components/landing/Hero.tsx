"use client";

import dynamic from "next/dynamic";
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { NODES } from "./nodes";
import { usePrefersReducedMotion } from "@/lib/motion";

gsap.registerPlugin(ScrollTrigger);

const ShatterScene = dynamic(() => import("./ShatterScene"), { ssr: false });

function canUseWebGL() {
  try {
    const c = document.createElement("canvas");
    return !!(c.getContext("webgl2") || c.getContext("webgl"));
  } catch {
    return false;
  }
}

export function Hero() {
  const section = useRef<HTMLElement>(null);
  const progress = useRef(0);
  const labelRefs = useRef<(HTMLDivElement | null)[]>([]);
  const [ready, setReady] = useState(false);
  const [webgl, setWebgl] = useState(true);
  const [active, setActive] = useState(true);
  const reduced = usePrefersReducedMotion();

  // Wait for fonts so the particle word is sampled from the real typeface.
  useEffect(() => {
    setWebgl(canUseWebGL());
    document.fonts.ready.then(() => setReady(true));
  }, []);

  // Pause rendering when the hero is off-screen.
  useEffect(() => {
    const el = section.current;
    if (!el) return;
    const io = new IntersectionObserver(([e]) => setActive(e.isIntersecting), { rootMargin: "100px" });
    io.observe(el);
    return () => io.disconnect();
  }, []);

  useLayoutEffect(() => {
    const el = section.current;
    if (!el) return;
    const ctx = gsap.context(() => {
      if (reduced) {
        progress.current = 1;
        return;
      }
      const tl = gsap.timeline({
        defaults: { ease: "none" },
        scrollTrigger: {
          trigger: el,
          start: "top top",
          end: "bottom bottom",
          scrub: 0.8,
          onUpdate: (self) => {
            progress.current = self.progress;
          },
        },
      });
      tl.to("[data-hero='intro']", { opacity: 0, y: -60, filter: "blur(8px)", duration: 0.12 }, 0.04)
        .fromTo("[data-hero='l1']", { opacity: 0, y: 40 }, { opacity: 1, y: 0, duration: 0.08 }, 0.18)
        .to("[data-hero='l1']", { opacity: 0, y: -40, duration: 0.08 }, 0.36)
        .fromTo("[data-hero='l2']", { opacity: 0, y: 40 }, { opacity: 1, y: 0, duration: 0.08 }, 0.42)
        .to("[data-hero='l2']", { opacity: 0, y: -40, duration: 0.08 }, 0.6)
        .fromTo("[data-hero='l3']", { opacity: 0, y: 40 }, { opacity: 1, y: 0, duration: 0.1 }, 0.8)
        .fromTo("[data-hero='bar']", { scaleX: 0 }, { scaleX: 1, duration: 1 }, 0);
    }, el);
    return () => ctx.revert();
  }, [reduced]);

  return (
    <section ref={section} id="top" className="relative h-[460vh]" aria-label="Introduction">
      <div className="sticky top-0 h-dvh w-full overflow-hidden">
        {/* Warm vignette — subtle, not a neon gradient */}
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_50%_55%,#2a1c16_0%,#14110f_62%)]" />

        <div className="absolute inset-0">
          {ready && webgl ? (
            <ShatterScene progress={progress} labelRefs={labelRefs} active={active} />
          ) : (
            <StaticWord />
          )}
        </div>

        {/* Node labels, positioned each frame from 3D → screen projection */}
        <div className="pointer-events-none absolute inset-0" aria-hidden>
          {NODES.map((n, i) => (
            <div
              key={n.key}
              ref={(el) => {
                labelRefs.current[i] = el;
              }}
              className="absolute left-0 top-0 whitespace-nowrap opacity-0 will-change-transform"
            >
              <div className="rounded-full border border-line/80 bg-ink/70 px-3 py-1.5 backdrop-blur-sm">
                <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted">{n.label}</span>
                <span className="ml-2 font-mono text-xs tabular text-paper">{n.value}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Copy layers — semantic HTML, never inside the canvas */}
        <div className="pointer-events-none relative z-10 flex h-full flex-col justify-between px-5 pb-8 pt-28 sm:px-10">
          <div data-hero="intro" className="max-w-sm">
            <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-haldi">व्यापार · noun · business, trade</p>
          </div>

          <h1 className="sr-only">Vyapar AI — business intelligence for Indian retailers</h1>

          <div className="relative mx-auto w-full max-w-4xl translate-y-[18vh] text-center [text-shadow:0_2px_30px_#14110f,0_0_12px_#14110f]">
            <p data-hero="l1" className="absolute inset-x-0 bottom-0 font-serif text-4xl leading-tight opacity-0 sm:text-6xl">
              Every shop is a story <em className="text-haldi">told in numbers.</em>
            </p>
            <p data-hero="l2" className="absolute inset-x-0 bottom-0 font-serif text-4xl leading-tight opacity-0 sm:text-6xl">
              We take it apart, <em className="text-sindoor">entry by entry.</em>
            </p>
            <div data-hero="l3" className="absolute inset-x-0 bottom-0 opacity-0">
              <p className="font-serif text-4xl leading-tight sm:text-6xl">
                …and rebuild it as <em className="text-haldi">decisions.</em>
              </p>
              <p className="mx-auto mt-4 max-w-md text-sm text-paper/60">
                Sales, customers, stock and forecasts, connected and explained.
              </p>
            </div>
          </div>

          <div data-hero="intro" className="flex items-end justify-between gap-6">
            <p className="max-w-xs text-sm leading-relaxed text-paper/60">
              Decision support for small and mid-sized retailers. Upload your sales and see what happened, why,
              and what to do next.
            </p>
            <div className="flex items-center gap-3 font-mono text-[11px] uppercase tracking-[0.2em] text-paper/50">
              <span className="relative block h-9 w-[1px] overflow-hidden bg-line">
                <span className="absolute inset-x-0 top-0 h-3 animate-[scrollcue_1.6s_ease-in-out_infinite] bg-haldi" />
              </span>
              Scroll to break it
            </div>
          </div>
        </div>

        <div className="absolute inset-x-0 bottom-0 h-[2px] bg-line/40">
          <div data-hero="bar" className="h-full origin-left bg-sindoor" />
        </div>
      </div>
      <style>{`@keyframes scrollcue{0%{transform:translateY(-100%)}100%{transform:translateY(300%)}}`}</style>
    </section>
  );
}

function StaticWord() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-2 select-none" aria-hidden>
      <span className="text-[22vw] font-extrabold leading-none tracking-tight text-paper">VYAPAR</span>
      <span className="font-deva text-[9vw] leading-none text-sindoor">व्यापार</span>
    </div>
  );
}
