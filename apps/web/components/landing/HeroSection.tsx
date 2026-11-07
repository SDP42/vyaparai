"use client";

import dynamic from "next/dynamic";
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { motion, useReducedMotion } from "motion/react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { CORE_LEGEND } from "./core-nodes";
import { EASE, MagneticLink } from "./ui";

gsap.registerPlugin(ScrollTrigger);

const DataCore = dynamic(() => import("./DataCore"), { ssr: false });

const HEADLINE = ["Your", "Business", "Deserves", "More", "Than", "Guesswork."];

export function HeroSection() {
  const section = useRef<HTMLElement>(null);
  const labelRefs = useRef<(HTMLElement | null)[]>([]);
  const decisionRef = useRef<HTMLElement | null>(null);
  const scrollProgress = useRef(0);
  const [activeKey, setActiveKey] = useState<string | null>(null);
  const [webgl, setWebgl] = useState(false);
  const [active, setActive] = useState(true);
  const reduce = useReducedMotion();

  useEffect(() => {
    try {
      const c = document.createElement("canvas");
      setWebgl(!!(c.getContext("webgl2") || c.getContext("webgl")));
    } catch {
      setWebgl(false);
    }
    const el = section.current;
    if (!el) return;
    const io = new IntersectionObserver(([e]) => setActive(e.isIntersecting), { rootMargin: "120px" });
    io.observe(el);
    return () => io.disconnect();
  }, []);

  useLayoutEffect(() => {
    const el = section.current;
    if (!el) return;
    const ctx = gsap.context(() => {
      ScrollTrigger.create({
        trigger: el,
        start: "top top",
        end: "bottom top",
        scrub: true,
        onUpdate: (s) => {
          scrollProgress.current = s.progress;
        },
      });
      if (!reduce) {
        gsap.to("[data-hero-copy]", {
          yPercent: -18,
          opacity: 0.2,
          ease: "none",
          scrollTrigger: { trigger: el, start: "top top", end: "bottom top", scrub: true },
        });
      }
    }, el);
    return () => ctx.revert();
  }, [reduce]);

  return (
    <section ref={section} id="top" className="relative min-h-dvh overflow-hidden" aria-labelledby="hero-title">
      {/* atmosphere */}
      <div aria-hidden className="pointer-events-none absolute inset-0">
        <div className="dot-grid absolute inset-0 [mask-image:radial-gradient(ellipse_at_70%_45%,black_10%,transparent_65%)] opacity-60" />
        <div className="absolute right-[-10%] top-[10%] h-[70vmax] w-[70vmax] rounded-full bg-[radial-gradient(circle,rgba(115,87,232,0.16),transparent_60%)]" />
        <div className="absolute bottom-[-30%] left-[-10%] h-[60vmax] w-[60vmax] rounded-full bg-[radial-gradient(circle,rgba(50,150,245,0.12),transparent_60%)]" />
      </div>

      <div className="relative mx-auto grid min-h-dvh max-w-7xl items-center gap-6 px-5 pb-16 pt-28 sm:px-8 lg:grid-cols-[1.05fr_1fr] lg:gap-0">
        <div data-hero-copy className="relative z-10 max-w-2xl lg:max-w-[540px] xl:max-w-[600px]">
          <motion.p
            initial={reduce ? false : { opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: EASE }}
            className="inline-flex items-center gap-2 rounded-full border border-line bg-surface/70 py-1 pl-1 pr-3 text-xs text-muted backdrop-blur"
          >
            <span className="rounded-full bg-violet/20 px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.16em] text-violet-soft">New</span>
            Business intelligence for small and medium retailers
          </motion.p>

          <h1 id="hero-title" className="mt-6 text-[clamp(2.6rem,5.6vw,5rem)] font-semibold leading-[0.95] tracking-[-0.035em]" aria-label={HEADLINE.join(" ")}>
            {HEADLINE.map((w, i) => (
              <span key={i} aria-hidden className="inline-block overflow-hidden pb-[0.1em] align-top">
                <motion.span
                  className={`inline-block ${w === "Guesswork." ? "font-serif font-normal italic tracking-[-0.01em] text-transparent bg-gradient-to-r from-violet-soft via-blue-soft to-violet-soft bg-[length:200%_100%] bg-clip-text animate-[shine_6s_linear_infinite]" : ""}`}
                  initial={reduce ? false : { y: "115%", rotate: 6 }}
                  animate={{ y: "0%", rotate: 0 }}
                  transition={{ duration: 1, ease: EASE, delay: 0.15 + i * 0.07 }}
                >
                  {w}&nbsp;
                </motion.span>
              </span>
            ))}
          </h1>

          <motion.p
            initial={reduce ? false : { opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: EASE, delay: 0.7 }}
            className="mt-6 max-w-xl text-lg leading-relaxed text-muted"
          >
            Transform everyday business data into trusted insights, intelligent predictions and actionable business
            decisions.
          </motion.p>

          <motion.div
            initial={reduce ? false : { opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: EASE, delay: 0.85 }}
            className="mt-9 flex flex-wrap gap-3"
          >
            <MagneticLink href="#platform">Explore Vyapar.ai</MagneticLink>
            <MagneticLink href="#how-it-works" variant="ghost">
              Discover How It Works
            </MagneticLink>
          </motion.div>

          {/* legend doubles as an accessible way to explore the 3D visual */}
          <motion.ul
            initial={reduce ? false : { opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8, delay: 1.1 }}
            className="mt-12 grid max-w-xl grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-2 xl:grid-cols-4"
            aria-label="What Vyapar.ai connects"
          >
            {CORE_LEGEND.map((n) => (
              <li key={n.key}>
                <button
                  type="button"
                  onMouseEnter={() => setActiveKey(n.key)}
                  onMouseLeave={() => setActiveKey(null)}
                  onFocus={() => setActiveKey(n.key)}
                  onBlur={() => setActiveKey(null)}
                  className={`w-full rounded-2xl border px-3 py-2.5 text-left transition-colors ${
                    activeKey === n.key ? "border-line-strong bg-surface-2" : "border-line bg-surface/50"
                  }`}
                >
                  <span className="flex items-center gap-2 text-sm font-medium">
                    <span aria-hidden className="h-2 w-2 rounded-full" style={{ background: n.color }} />
                    {n.label}
                  </span>
                  <span className="mt-0.5 block truncate font-mono text-[10px] text-muted">{n.detail}</span>
                </button>
              </li>
            ))}
          </motion.ul>
        </div>

        <div className="relative h-[52vh] min-h-[360px] lg:absolute lg:inset-y-0 lg:right-0 lg:h-auto lg:w-[50%]">
          {webgl ? (
            <DataCore
              active={active}
              activeKey={activeKey}
              setActiveKey={setActiveKey}
              labelRefs={labelRefs}
              decisionRef={decisionRef}
              scrollProgress={scrollProgress}
            />
          ) : (
            <StaticCore />
          )}
          <div className="pointer-events-none absolute inset-0 hidden sm:block" aria-hidden>
            {CORE_LEGEND.map((n, i) => (
              <div
                key={n.key}
                ref={(el) => {
                  labelRefs.current[i] = el;
                }}
                className={`absolute left-0 top-0 whitespace-nowrap rounded-full border px-3 py-1 text-xs backdrop-blur transition-[border-color,background,opacity] duration-300 will-change-transform ${
                  activeKey === n.key ? "border-line-strong bg-surface-2 opacity-100" : "border-line bg-canvas/60 opacity-80"
                }`}
              >
                <span className="font-medium">{n.label}</span>
                <span className="ml-2 font-mono text-[10px] text-muted">{n.detail}</span>
              </div>
            ))}
            <div
              ref={(el) => {
                decisionRef.current = el;
              }}
              className="absolute left-0 top-0 w-60 rounded-2xl border border-line-strong bg-surface/90 p-3 shadow-[0_20px_60px_-20px_rgba(115,87,232,0.6)] backdrop-blur will-change-transform"
            >
              <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-brass">Decision · awaiting approval</p>
              <p className="mt-1 text-sm font-medium leading-snug">Reorder 120 × Wheat atta 5 kg before stock runs out</p>
              <div className="mt-2 flex gap-1.5">
                <span className="rounded-full bg-fg px-2.5 py-1 text-[11px] font-medium text-canvas">Approve</span>
                <span className="rounded-full border border-line px-2.5 py-1 text-[11px] text-muted">Review evidence</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="pointer-events-none absolute inset-x-0 bottom-6 flex justify-center" aria-hidden>
        <div className="flex h-10 w-6 justify-center rounded-full border border-line-strong pt-2">
          <span className="h-2 w-px animate-[scrolldot_1.8s_ease-in-out_infinite] bg-fg" />
        </div>
      </div>
      <style>{`
        @keyframes shine { to { background-position: -200% 0; } }
        @keyframes scrolldot { 0% { transform: translateY(0); opacity: 1 } 80% { transform: translateY(14px); opacity: 0 } 100% { opacity: 0 } }
      `}</style>
    </section>
  );
}

function StaticCore() {
  return (
    <div className="flex h-full items-center justify-center" aria-hidden>
      <div className="h-56 w-56 rounded-full bg-[radial-gradient(circle_at_35%_35%,#9d8bf2,#3296f5_45%,transparent_70%)] opacity-70 blur-[2px]" />
    </div>
  );
}
