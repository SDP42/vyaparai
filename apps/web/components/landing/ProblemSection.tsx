"use client";

import { useLayoutEffect, useRef, type ReactNode } from "react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { Eyebrow, SplitHeading } from "./ui";

gsap.registerPlugin(ScrollTrigger);

type Problem = { title: string; body: string; fragment: ReactNode; scatter: [number, number, number] };

const PROBLEMS: Problem[] = [
  {
    title: "Scattered business information",
    body: "Billing exports, spreadsheets and notebooks that never agree with each other.",
    scatter: [-38, -30, -14],
    fragment: (
      <div className="font-mono text-[11px] leading-relaxed text-muted">
        <p className="text-fg">sales_oct_FINAL_v3.xlsx</p>
        <p>sheet2 (copy) · 12,408 rows</p>
        <p className="text-danger">#REF! · 17 cells</p>
      </div>
    ),
  },
  {
    title: "Unclear sales performance",
    body: "Revenue moved, but was it price, volume, mix or discounts? Nobody can say.",
    scatter: [34, -36, 11],
    fragment: (
      <div className="flex h-12 items-end gap-1" aria-hidden>
        {[40, 62, 35, 80, 52, 70, 30].map((h, i) => (
          <span key={i} className="w-3 rounded-sm bg-line-strong" style={{ height: `${h}%` }} />
        ))}
        <span className="ml-1 font-mono text-xs text-muted">?</span>
      </div>
    ),
  },
  {
    title: "Inventory uncertainty",
    body: "Best-sellers run out while slow movers fill the back room.",
    scatter: [-44, 18, 9],
    fragment: (
      <div className="font-mono text-[11px] text-muted">
        <p>
          SKU TUR-1KG · on hand <span className="text-danger">0</span>
        </p>
        <p>
          SKU DIY-12 · on hand <span className="text-warning">418</span>
        </p>
      </div>
    ),
  },
  {
    title: "Customer behaviour is a mystery",
    body: "Who are your regulars? Who quietly stopped coming? The data knows; you don't.",
    scatter: [40, 22, -10],
    fragment: (
      <div className="flex -space-x-2" aria-hidden>
        {["#7357e8", "#3296f5", "#9d8bf2", "#33415f", "#33415f"].map((c, i) => (
          <span key={i} className="h-7 w-7 rounded-full border-2 border-surface" style={{ background: c, opacity: i > 2 ? 0.4 : 1 }} />
        ))}
        <span className="ml-3 self-center font-mono text-[11px] text-muted">142 lapsed?</span>
      </div>
    ),
  },
  {
    title: "Unpredictable demand",
    body: "Festive weeks and month-ends surprise you every single year.",
    scatter: [-20, 44, -7],
    fragment: (
      <svg viewBox="0 0 120 40" className="h-10 w-full" aria-hidden>
        <path d="M0 30 Q15 10 30 26 T60 18 T90 34 T120 6" fill="none" stroke="#33415f" strokeWidth="2" strokeDasharray="3 4" />
      </svg>
    ),
  },
  {
    title: "Delayed decisions",
    body: "By the time the numbers are clear, the moment to act has passed.",
    scatter: [26, 46, 15],
    fragment: (
      <div className="rounded-xl rounded-tl-sm bg-surface-2 px-3 py-2 text-xs text-muted">
        &ldquo;Will check the numbers next week&rdquo; <span className="font-mono text-[10px]">· 11:42 pm ✓✓</span>
      </div>
    ),
  },
];

export function ProblemSection() {
  const root = useRef<HTMLElement>(null);

  useLayoutEffect(() => {
    const el = root.current;
    if (!el) return;
    const mm = gsap.matchMedia();
    mm.add("(min-width: 1024px) and (prefers-reduced-motion: no-preference)", () => {
      const cards = gsap.utils.toArray<HTMLElement>("[data-problem]", el);
      const tl = gsap.timeline({
        scrollTrigger: { trigger: el, start: "top top", end: "+=140%", pin: true, scrub: 0.8 },
      });
      cards.forEach((card, i) => {
        const [x, y, r] = PROBLEMS[i].scatter;
        tl.fromTo(
          card,
          { xPercent: x * 2.2, yPercent: y * 2.4, rotate: r, scale: 0.86, filter: "blur(2px)" },
          { xPercent: 0, yPercent: 0, rotate: 0, scale: 1, filter: "blur(0px)", ease: "power3.inOut", duration: 1 },
          i * 0.06,
        );
        tl.fromTo(card.querySelector("[data-problem-copy]"), { opacity: 0, y: 12 }, { opacity: 1, y: 0, duration: 0.4 }, 0.7 + i * 0.04);
      });
      tl.fromTo("[data-problem-chaos]", { opacity: 1 }, { opacity: 0, duration: 0.4 }, 0.5);
    });
    mm.add("(max-width: 1023px), (prefers-reduced-motion: reduce)", () => {
      gsap.utils.toArray<HTMLElement>("[data-problem]", el).forEach((card) => {
        gsap.from(card, { opacity: 0, y: 40, duration: 0.8, ease: "power3.out", scrollTrigger: { trigger: card, start: "top 88%" } });
      });
    });
    return () => mm.revert();
  }, []);

  return (
    <section ref={root} className="relative overflow-hidden py-24 lg:flex lg:min-h-dvh lg:items-center lg:py-0" aria-labelledby="problem-title">
      <div className="mx-auto w-full max-w-7xl px-5 sm:px-8">
        <div className="mb-10 grid gap-6 lg:mb-12 lg:grid-cols-[1.2fr_1fr] lg:items-end">
          <div>
            <Eyebrow>The problem</Eyebrow>
            <SplitHeading
            id="problem-title"
              text="Running a business shouldn't mean running behind data."
              className="mt-4 text-[clamp(2rem,4.4vw,3.8rem)] font-semibold leading-[1] tracking-[-0.03em]"
              accent={["behind"]}
            />
          </div>
          <p className="max-w-md text-muted lg:justify-self-end">
            Most retailers already have the data. It&apos;s just spread across too many places to tell a clear story,
            or to tell you what to do next.
          </p>
        </div>

        <p data-problem-chaos aria-hidden className="pointer-events-none absolute left-1/2 top-[55%] hidden -translate-x-1/2 font-mono text-xs uppercase tracking-[0.3em] text-muted/60 lg:block">
          scroll to bring order
        </p>

        <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {PROBLEMS.map((p) => (
            <li key={p.title} data-problem className="rounded-3xl border border-line bg-surface p-6 will-change-transform">
              <div className="flex min-h-14 items-center">{p.fragment}</div>
              <div data-problem-copy className="mt-5 border-t border-line pt-5">
                <h3 className="text-lg font-medium tracking-tight">{p.title}</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-muted">{p.body}</p>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
