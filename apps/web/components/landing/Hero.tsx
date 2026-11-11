"use client";

import Link from "next/link";
import { useLayoutEffect, useRef } from "react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { DashboardPreview } from "./DashboardPreview";

gsap.registerPlugin(ScrollTrigger);

const PROMISES = ["Numbers you can check", "Every insight shows its source", "You approve every action"];

/** Simple, human hero: clear words on the left, the real product on the right. */
export function Hero() {
  const root = useRef<HTMLElement>(null);

  useLayoutEffect(() => {
    const el = root.current;
    if (!el) return;
    let cleanup = () => {};
    const mm = gsap.matchMedia();
    mm.add("(prefers-reduced-motion: no-preference)", () => {
      // wait for the cloth to drop before the hero speaks
      const locked = document.documentElement.dataset.gate === "locked";
      const tl = gsap.timeline({ defaults: { ease: "expo.out" }, paused: locked });
      const onGate = (e: Event) => !(e as CustomEvent<{ locked: boolean }>).detail.locked && tl.play();
      window.addEventListener("vyapar:gate", onGate);
      cleanup = () => window.removeEventListener("vyapar:gate", onGate);
      tl.from("[data-hero-word]", { yPercent: 110, rotate: 4, duration: 1.1, stagger: 0.06 }, 0.1)
        .from("[data-hero-fade]", { opacity: 0, y: 24, duration: 0.9, stagger: 0.08 }, 0.5)
        .from("[data-hero-card]", { opacity: 0, y: 80, rotateX: 18, duration: 1.4 }, 0.35);

      // the product card settles upright as you scroll
      gsap.fromTo(
        "[data-hero-card]",
        { rotateX: 14, rotateY: -14, rotateZ: 2 },
        {
          rotateX: 0,
          rotateY: 0,
          rotateZ: 0,
          ease: "none",
          scrollTrigger: { trigger: el, start: "top top", end: "bottom top", scrub: true },
        },
      );
      gsap.to("[data-hero-copy]", {
        yPercent: -12,
        opacity: 0.3,
        ease: "none",
        scrollTrigger: { trigger: el, start: "top top", end: "bottom top", scrub: true },
      });
    });
    return () => {
      cleanup();
      mm.revert();
    };
  }, []);

  const words = ["Your", "business", "deserves", "more", "than"];

  return (
    <section ref={root} id="top" className="relative overflow-hidden" aria-labelledby="hero-title">
      <div aria-hidden className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_80%_30%,#fff7e6_0%,#f6efe2_55%,#efe3cc_100%)]" />
      <div className="relative mx-auto grid min-h-dvh max-w-7xl items-center gap-12 px-5 pb-20 pt-28 sm:px-10 lg:grid-cols-[1fr_1.05fr]">
        <div data-hero-copy>
          <p data-hero-fade className="font-mono text-[11px] uppercase tracking-[0.22em] text-sindoor">
            व्यापार · business intelligence for retailers
          </p>
          <h1 id="hero-title" className="mt-5 text-[clamp(2.8rem,6.5vw,5.6rem)] font-extrabold leading-[0.92] tracking-tight">
            {words.map((w) => (
              <span key={w} className="inline-block overflow-hidden pb-[0.08em] align-top">
                <span data-hero-word className="inline-block">
                  {w}&nbsp;
                </span>
              </span>
            ))}
            <span className="inline-block overflow-hidden pb-[0.12em] align-top">
              <span data-hero-word className="inline-block font-serif font-normal italic text-sindoor">
                guesswork.
              </span>
            </span>
          </h1>
          <p data-hero-fade className="mt-6 max-w-lg text-lg leading-relaxed text-fg/70">
            Upload your sales export. See what happened, why it happened and what to do next, with numbers you
            can check.
          </p>
          <div data-hero-fade className="mt-9 flex flex-wrap gap-3">
            <a
              href="#story"
              className="group inline-flex h-12 items-center gap-2 rounded-full bg-fg px-6 text-sm font-semibold text-canvas transition-colors hover:bg-sindoor"
            >
              See how it works
              <span aria-hidden className="transition-transform group-hover:translate-x-0.5">↓</span>
            </a>
            <Link
              href="/login"
              className="inline-flex h-12 items-center rounded-full border border-fg/20 px-6 text-sm font-semibold transition-colors hover:border-fg/50"
            >
              Try the demo
            </Link>
          </div>
          <ul data-hero-fade className="mt-10 flex flex-wrap gap-x-6 gap-y-2 text-sm text-fg/60">
            {PROMISES.map((p) => (
              <li key={p} className="flex items-center gap-2">
                <span aria-hidden className="h-1.5 w-1.5 rotate-45 bg-haldi" />
                {p}
              </li>
            ))}
          </ul>
        </div>

        <div className="[perspective:1600px]">
          <div
            data-hero-card
            className="overflow-hidden rounded-3xl border border-line bg-surface shadow-[0_50px_100px_-40px_rgba(90,50,20,0.45)] will-change-transform"
          >
            <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
              <div className="flex gap-1.5" aria-hidden>
                <span className="h-2.5 w-2.5 rounded-full bg-sindoor/70" />
                <span className="h-2.5 w-2.5 rounded-full bg-haldi/80" />
                <span className="h-2.5 w-2.5 rounded-full bg-mor/70" />
              </div>
              <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted">Command center · demo data</span>
            </div>
            <DashboardPreview />
          </div>
        </div>
      </div>
    </section>
  );
}
