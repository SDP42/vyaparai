"use client";

import { useLayoutEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { Wordmark } from "./Navigation";
import { SplitHeading } from "./ui";

gsap.registerPlugin(ScrollTrigger);

export function FinalCta() {
  const root = useRef<HTMLElement>(null);
  const [note, setNote] = useState(false);

  useLayoutEffect(() => {
    const el = root.current;
    if (!el) return;
    const mm = gsap.matchMedia();
    mm.add("(prefers-reduced-motion: no-preference)", () => {
      gsap.fromTo("[data-key-path]", { strokeDashoffset: 1 }, {
        strokeDashoffset: 0,
        ease: "none",
        scrollTrigger: { trigger: el, start: "top 80%", end: "top 20%", scrub: true },
      });
    });
    return () => mm.revert();
  }, []);

  return (
    <section ref={root} id="get-started" className="relative overflow-hidden px-5 pb-10 pt-28 sm:px-8 sm:pt-40" aria-labelledby="cta-title">
      <div className="relative mx-auto max-w-7xl overflow-hidden rounded-[36px] bg-midnight px-6 py-20 text-white sm:px-14 sm:py-28">
        <div aria-hidden className="pointer-events-none absolute -right-40 -top-40 h-[520px] w-[520px] rounded-full bg-[radial-gradient(circle,rgba(115,87,232,0.45),transparent_60%)]" />
        <div aria-hidden className="pointer-events-none absolute -bottom-48 -left-24 h-[480px] w-[480px] rounded-full bg-[radial-gradient(circle,rgba(50,150,245,0.3),transparent_60%)]" />
        {/* a key, drawn as you scroll — the thread back to the opening */}
        <svg aria-hidden viewBox="0 0 600 160" className="pointer-events-none absolute bottom-8 right-6 hidden w-[46%] opacity-70 md:block">
          <path
            data-key-path
            pathLength={1}
            d="M40 80 a44 44 0 1 0 88 0 a44 44 0 1 0 -88 0 M128 80 H560 M500 80 v34 M530 80 v22 M470 80 v26"
            fill="none"
            stroke="#c6a66b"
            strokeWidth="3"
            strokeLinecap="round"
            strokeDasharray="1"
          />
        </svg>

        <div className="relative max-w-3xl">
          <SplitHeading
            id="cta-title"
            text="Your business is ready for its next chapter."
            className="text-[clamp(2.2rem,5.4vw,4.6rem)] font-semibold leading-[0.98] tracking-[-0.035em]"
            accent={["next"]}
          />
          <p className="mt-6 max-w-xl text-lg text-white/70">Unlock the intelligence hidden inside your business with Vyapar.ai.</p>
          <div className="mt-10 flex flex-wrap items-center gap-4">
            <button
              type="button"
              onClick={() => setNote(true)}
              className="group inline-flex h-12 items-center gap-2 rounded-full bg-white px-7 text-sm font-medium text-midnight transition-transform hover:-translate-y-0.5"
            >
              Get Started <span aria-hidden className="transition-transform group-hover:translate-x-0.5">→</span>
            </button>
            <AnimatePresence>
              {note && (
                <motion.p
                  role="status"
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0 }}
                  className="text-sm text-white/70"
                >
                  Early access is opening soon. This page is a product preview.
                </motion.p>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </section>
  );
}

export function Footer() {
  const cols = [
    { h: "Product", l: [["Platform", "#platform"], ["Solutions", "#solutions"], ["How it works", "#how-it-works"]] },
    { h: "Company", l: [["About", "#about"], ["Get started", "#get-started"]] },
  ];
  return (
    <footer className="relative overflow-hidden px-5 pb-10 pt-16 sm:px-8">
      <div className="mx-auto max-w-7xl">
        <div className="grid gap-10 border-b border-line pb-12 md:grid-cols-[1.5fr_1fr_1fr]">
          <div>
            <Wordmark className="text-sm" />
            <p className="mt-4 max-w-sm text-sm text-muted">
              Business intelligence and decision support for small and medium retailers. Trusted metrics, honest
              forecasts, human-approved actions.
            </p>
          </div>
          {cols.map((c) => (
            <nav key={c.h} aria-label={c.h}>
              <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">{c.h}</p>
              <ul className="mt-4 space-y-2 text-sm">
                {c.l.map(([label, href]) => (
                  <li key={label}>
                    <a href={href} className="text-fg/80 transition-colors hover:text-violet">
                      {label}
                    </a>
                  </li>
                ))}
              </ul>
            </nav>
          ))}
        </div>
        <p
          aria-hidden
          className="pointer-events-none mt-10 select-none bg-gradient-to-b from-fg/15 to-transparent bg-clip-text text-center text-[19vw] font-semibold leading-[0.8] tracking-[-0.06em] text-transparent"
        >
          VYAPAR.AI
        </p>
        <div className="mt-6 flex flex-col justify-between gap-2 text-xs text-muted sm:flex-row">
          <p>© {new Date().getFullYear()} Vyapar.ai. All figures shown are illustrative demo data.</p>
          <p>Built as a portfolio-grade engineering case study.</p>
        </div>
      </div>
    </footer>
  );
}
