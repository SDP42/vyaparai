"use client";

import { useLayoutEffect, useRef } from "react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger);

const STEPS = [
  {
    n: "01",
    title: "Data enters",
    body: "Drop in a CSV or Excel export from your billing software. We inspect every column before anything is saved.",
    visual: <RowsVisual />,
  },
  {
    n: "02",
    title: "It gets organised",
    body: "Columns are mapped, bad rows are flagged rather than silently dropped, and every rupee lands in a clean ledger.",
    visual: <MapVisual />,
  },
  {
    n: "03",
    title: "Insight appears",
    body: "Sales explained by volume, price, mix and discount. Forecasts that know about Diwali. Figures come from SQL, not from an AI's guess.",
    visual: <ChartVisual />,
  },
  {
    n: "04",
    title: "You approve the action",
    body: "Recommendations come with evidence and assumptions. Nothing is ordered or sent until you say so.",
    visual: <ApproveVisual />,
  },
];

export function Story() {
  const root = useRef<HTMLElement>(null);
  const track = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    const el = root.current;
    const tr = track.current;
    if (!el || !tr) return;
    const mm = gsap.matchMedia();
    mm.add("(min-width: 900px) and (prefers-reduced-motion: no-preference)", () => {
      const distance = () => tr.scrollWidth - window.innerWidth;
      const tween = gsap.to(tr, {
        x: () => -distance(),
        ease: "none",
        scrollTrigger: {
          trigger: el,
          start: "top top",
          end: () => `+=${distance()}`,
          pin: true,
          scrub: 0.6,
          invalidateOnRefresh: true,
        },
      });
      gsap.utils.toArray<HTMLElement>("[data-step]").forEach((step) => {
        gsap.from(step.querySelectorAll("[data-reveal]"), {
          opacity: 0,
          y: 50,
          stagger: 0.08,
          ease: "power3.out",
          scrollTrigger: { trigger: step, containerAnimation: tween, start: "left 75%", toggleActions: "play none none reverse" },
        });
      });
    });
    mm.add("(max-width: 899px), (prefers-reduced-motion: reduce)", () => {
      gsap.utils.toArray<HTMLElement>("[data-step]").forEach((step) => {
        gsap.from(step, { opacity: 0, y: 40, duration: 0.8, ease: "power3.out", scrollTrigger: { trigger: step, start: "top 85%" } });
      });
    });
    return () => mm.revert();
  }, []);

  return (
    <section ref={root} id="story" className="relative overflow-hidden bg-ink" aria-labelledby="story-title">
      <div ref={track} className="flex flex-col gap-6 px-5 py-24 min-[900px]:h-dvh min-[900px]:w-max min-[900px]:flex-row min-[900px]:items-center min-[900px]:gap-0 min-[900px]:px-0 min-[900px]:py-0">
        <div className="flex shrink-0 flex-col justify-center min-[900px]:w-[42vw] min-[900px]:pl-16 min-[900px]:pr-10">
          <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-haldi">From ledger to decision</p>
          <h2 id="story-title" className="mt-5 text-5xl font-bold leading-[0.95] tracking-tight sm:text-7xl">
            Four steps.
            <br />
            <span className="font-serif font-normal italic text-paper/70">No black boxes.</span>
          </h2>
        </div>
        {STEPS.map((s) => (
          <article
            key={s.n}
            data-step
            className="relative flex shrink-0 flex-col overflow-hidden rounded-3xl border border-line bg-ink-2 p-6 min-[900px]:mr-8 min-[900px]:h-[72vh] min-[900px]:w-[min(560px,40vw)] min-[900px]:p-9"
          >
            <div className="flex items-baseline justify-between">
              <span data-reveal className="font-mono text-sm text-sindoor">{s.n}</span>
              <span data-reveal className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted">step</span>
            </div>
            <div data-reveal className="my-6 flex flex-1 items-center justify-center min-h-48">{s.visual}</div>
            <h3 data-reveal className="text-3xl font-bold tracking-tight">{s.title}</h3>
            <p data-reveal className="mt-3 max-w-md text-paper/65 leading-relaxed">{s.body}</p>
          </article>
        ))}
        <div className="hidden w-[10vw] shrink-0 min-[900px]:block" />
      </div>
    </section>
  );
}

function RowsVisual() {
  const rows = [
    ["INV-2041", "Atta 5kg", "2", "₹590"],
    ["INV-2042", "Ghee 1L", "1", "₹645"],
    ["INV-2043", "Rice 5kg", "?", "₹—"],
    ["INV-2044", "Oil 5L", "3", "₹1,140"],
  ];
  return (
    <div className="w-full max-w-sm rounded-xl border border-line bg-ink p-3 font-mono text-xs">
      <div className="mb-2 flex items-center gap-2 text-muted">
        <span className="h-2 w-2 rounded-full bg-mor" /> sales_oct.csv · 12,408 rows
      </div>
      {rows.map((r, i) => (
        <div key={r[0]} className={`grid grid-cols-4 gap-2 border-t border-line/60 py-2 ${i === 2 ? "text-sindoor" : "text-paper/80"}`}>
          {r.map((c, j) => (
            <span key={j} className="truncate">{c}</span>
          ))}
        </div>
      ))}
    </div>
  );
}

function MapVisual() {
  const map = [
    ["Bill Date", "order_date"],
    ["Item", "product"],
    ["Qty", "quantity"],
    ["Rate", "unit_price"],
  ];
  return (
    <div className="w-full max-w-sm space-y-2.5">
      {map.map(([a, b]) => (
        <div key={a} className="flex items-center gap-3 font-mono text-xs">
          <span className="w-28 rounded-md border border-line bg-ink px-2.5 py-2 text-paper/80">{a}</span>
          <span className="h-px flex-1 bg-gradient-to-r from-line via-haldi to-line" />
          <span className="w-28 rounded-md border border-haldi/40 bg-haldi/10 px-2.5 py-2 text-haldi">{b}</span>
        </div>
      ))}
      <p className="pt-2 font-mono text-[11px] text-muted">
        <span className="text-mor">12,391 accepted</span> · <span className="text-sindoor">17 rejected</span> (downloadable)
      </p>
    </div>
  );
}

function ChartVisual() {
  const pts = [30, 34, 31, 38, 42, 40, 47, 45, 52, 58, 55, 63, 70, 66];
  const max = 75;
  const path = pts.map((v, i) => `${i === 0 ? "M" : "L"}${(i / (pts.length - 1)) * 300},${120 - (v / max) * 110}`).join(" ");
  return (
    <svg viewBox="0 0 300 130" className="w-full max-w-sm" role="img" aria-label="Sales trend rising over two weeks">
      {[0, 1, 2, 3].map((i) => (
        <line key={i} x1="0" x2="300" y1={10 + i * 37} y2={10 + i * 37} stroke="var(--color-line)" strokeDasharray="2 4" />
      ))}
      <path d={`${path} L300,130 L0,130 Z`} fill="var(--color-haldi)" opacity="0.08" />
      <path d={path} fill="none" stroke="var(--color-haldi)" strokeWidth="2.5" strokeLinecap="round" />
      <circle cx="300" cy={120 - (66 / max) * 110} r="4" fill="var(--color-sindoor)" />
      <text x="0" y="128" fill="var(--color-muted)" fontSize="9" fontFamily="var(--font-mono)">price +2% · volume +9% · mix +1%</text>
    </svg>
  );
}

function ApproveVisual() {
  return (
    <div className="w-full max-w-sm rounded-xl border border-line bg-ink p-4">
      <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-haldi">Recommendation · medium confidence</p>
      <p className="mt-2 font-semibold">Reorder 120 gift boxes before Diwali</p>
      <p className="mt-1 text-xs text-paper/55">Evidence: forecast v3 · stock snapshot 06 Nov · lead time 9 days</p>
      <div className="mt-4 flex gap-2">
        <span className="rounded-full bg-mor px-3 py-1.5 text-xs font-semibold text-ink">Approve draft</span>
        <span className="rounded-full border border-line px-3 py-1.5 text-xs text-paper/70">Dismiss</span>
      </div>
    </div>
  );
}
