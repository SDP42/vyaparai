"use client";

import { useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { AnimatePresence, motion } from "motion/react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { EASE, Eyebrow, SplitHeading } from "./ui";

gsap.registerPlugin(ScrollTrigger);

const STEPS: { n: string; title: string; body: string; visual: ReactNode }[] = [
  {
    n: "01",
    title: "Connect Your Data",
    body: "Upload CSV or Excel exports from your billing tool. Every column is inspected and mapped, and bad rows are flagged instead of being silently dropped.",
    visual: <ConnectVisual />,
  },
  {
    n: "02",
    title: "Understand Your Business",
    body: "One metric registry defines net sales, profit, orders and AOV, so the dashboard, the API and the Copilot always agree.",
    visual: <UnderstandVisual />,
  },
  {
    n: "03",
    title: "Discover What's Next",
    body: "Baseline-first forecasts, customer segments and stock-out risk, each with an interval and an honest confidence label.",
    visual: <DiscoverVisual />,
  },
  {
    n: "04",
    title: "Make Better Decisions",
    body: "Ranked recommendations come with evidence and assumptions. Nothing is ordered or changed until you approve it.",
    visual: <DecideVisual />,
  },
];

export function HowItWorksSection() {
  const root = useRef<HTMLElement>(null);
  const fill = useRef<HTMLDivElement>(null);
  const [active, setActive] = useState(0);

  useLayoutEffect(() => {
    const el = root.current;
    if (!el) return;
    const mm = gsap.matchMedia();
    mm.add("(min-width: 1024px) and (prefers-reduced-motion: no-preference)", () => {
      ScrollTrigger.create({
        trigger: el,
        start: "top top",
        end: "+=260%",
        pin: true,
        scrub: true,
        onUpdate: (s) => {
          if (fill.current) fill.current.style.transform = `scaleY(${s.progress})`;
          setActive(Math.min(STEPS.length - 1, Math.floor(s.progress * STEPS.length * 0.999)));
        },
      });
    });
    return () => mm.revert();
  }, []);

  return (
    <section ref={root} id="how-it-works" className="relative py-28 lg:flex lg:min-h-dvh lg:items-center lg:py-0" aria-labelledby="how-title">
      <div className="mx-auto w-full max-w-7xl px-5 sm:px-8">
        <Eyebrow>How Vyapar.ai works</Eyebrow>
        <SplitHeading
            id="how-title"
          text="From raw exports to approved decisions."
          className="mt-4 max-w-3xl text-[clamp(2rem,4.4vw,3.6rem)] font-semibold leading-[1] tracking-[-0.03em]"
          accent={["approved"]}
        />

        {/* Desktop: pinned, scroll-driven */}
        <div className="mt-12 hidden gap-12 lg:grid lg:grid-cols-[0.9fr_1.1fr]">
          <ol className="relative pl-10">
            <div aria-hidden className="absolute bottom-3 left-[15px] top-3 w-px bg-line">
              <div ref={fill} className="h-full w-full origin-top scale-y-0 bg-gradient-to-b from-violet to-blue" />
            </div>
            {STEPS.map((s, i) => (
              <li key={s.n} className="relative pb-9 last:pb-0">
                <span
                  aria-hidden
                  className={`absolute -left-10 top-0.5 grid h-8 w-8 place-items-center rounded-full border font-mono text-[11px] transition-colors duration-500 ${
                    i <= active ? "border-violet bg-violet text-white" : "border-line-strong bg-surface text-muted"
                  }`}
                >
                  {s.n}
                </span>
                <h3 className={`text-2xl font-medium tracking-tight transition-colors duration-500 ${i === active ? "text-fg" : "text-muted/70"}`}>
                  {s.title}
                </h3>
                <motion.p
                  initial={false}
                  animate={{ height: i === active ? "auto" : 0, opacity: i === active ? 1 : 0 }}
                  transition={{ duration: 0.45, ease: EASE }}
                  className="max-w-md overflow-hidden text-muted"
                >
                  <span className="block pt-2">{s.body}</span>
                </motion.p>
              </li>
            ))}
          </ol>
          <div className="relative min-h-[380px] overflow-hidden rounded-[28px] border border-line bg-surface shadow-[0_40px_80px_-50px_rgba(11,16,32,0.35)]">
            <div aria-hidden className="dot-grid absolute inset-0 opacity-50" />
            <AnimatePresence mode="wait">
              <motion.div
                key={active}
                initial={{ opacity: 0, y: 30, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -30, scale: 0.98 }}
                transition={{ duration: 0.5, ease: EASE }}
                className="relative flex h-full items-center justify-center p-8"
              >
                {STEPS[active].visual}
              </motion.div>
            </AnimatePresence>
          </div>
        </div>

        {/* Mobile / tablet / reduced motion: stacked */}
        <ol className="mt-10 space-y-4 lg:hidden">
          {STEPS.map((s) => (
            <li key={s.n} className="rounded-3xl border border-line bg-surface p-6">
              <span className="font-mono text-xs text-violet">{s.n}</span>
              <h3 className="mt-1 text-xl font-medium">{s.title}</h3>
              <p className="mt-2 text-sm text-muted">{s.body}</p>
              <div className="mt-5 flex justify-center overflow-hidden rounded-2xl bg-canvas p-4">{s.visual}</div>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

function ConnectVisual() {
  const map = [
    ["Bill Date", "order_date"],
    ["Item Name", "product"],
    ["Qty", "quantity"],
    ["Rate", "unit_price"],
  ];
  return (
    <div className="w-full max-w-md">
      <div className="mb-4 flex items-center gap-3 rounded-2xl border border-line bg-canvas p-3">
        <span className="grid h-9 w-9 place-items-center rounded-xl bg-success/15 font-mono text-[10px] font-semibold text-success">XLSX</span>
        <div className="text-sm">
          <p className="font-medium">sales_october.xlsx</p>
          <p className="font-mono text-[11px] text-muted">12,408 rows · 14 columns · inspected</p>
        </div>
      </div>
      <div className="space-y-2">
        {map.map(([a, b]) => (
          <div key={a} className="flex items-center gap-3 font-mono text-xs">
            <span className="w-28 rounded-lg border border-line bg-surface px-2.5 py-2">{a}</span>
            <span className="h-px flex-1 bg-gradient-to-r from-line-strong via-violet to-blue" />
            <span className="w-28 rounded-lg bg-violet/10 px-2.5 py-2 text-violet-soft">{b}</span>
          </div>
        ))}
      </div>
      <p className="mt-4 font-mono text-[11px]">
        <span className="text-success">✓ 12,391 accepted</span> · <span className="text-danger">17 rejected (downloadable)</span>
      </p>
    </div>
  );
}

function UnderstandVisual() {
  return (
    <div className="w-full max-w-md space-y-3">
      <div className="rounded-2xl border border-line bg-canvas p-4">
        <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted">metric · net_sales · v1</p>
        <p className="mt-1 text-3xl font-semibold tabular">₹18,46,320</p>
        <p className="mt-1 text-xs text-muted">Completed orders · excl. GST, returns, cancellations · Oct 2026 · fresh 06 Nov 23:40</p>
      </div>
      <div className="grid grid-cols-3 gap-2 text-center text-xs">
        {[
          ["Volume", "−₹1.62L", "text-danger"],
          ["Price", "+₹0.52L", "text-success"],
          ["Mix", "−₹0.12L", "text-danger"],
        ].map(([l, v, c]) => (
          <div key={l} className="rounded-xl border border-line bg-surface p-3">
            <p className="text-muted">{l}</p>
            <p className={`mt-1 font-mono font-medium ${c}`}>{v}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function DiscoverVisual() {
  return (
    <div className="w-full max-w-md rounded-2xl border border-line bg-canvas p-4">
      <div className="flex items-baseline justify-between">
        <p className="text-sm font-medium">Next 14 days · Staples</p>
        <span className="rounded-full bg-warning/15 px-2 py-0.5 font-mono text-[10px] text-warning">medium confidence</span>
      </div>
      <svg viewBox="0 0 300 120" className="mt-3 w-full" aria-hidden>
        <path d="M150 60 C190 48 240 40 300 30 L300 78 C240 82 190 80 150 68 Z" fill="var(--color-violet)" opacity="0.15" />
        <path d="M0 85 C30 70 60 92 90 74 S130 60 150 64" fill="none" stroke="var(--color-fg)" strokeWidth="2.5" />
        <path d="M150 64 C190 58 240 54 300 52" fill="none" stroke="var(--color-violet)" strokeWidth="2.5" strokeDasharray="6 6" />
        <line x1="150" x2="150" y1="10" y2="115" stroke="var(--color-line-strong)" />
      </svg>
      <p className="font-mono text-[11px] text-muted">Seasonal-naive baseline beaten by 11% WAPE in backtests</p>
    </div>
  );
}

function DecideVisual() {
  return (
    <div className="w-full max-w-md rounded-2xl border border-line bg-canvas p-5">
      <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-brass">Recommendation · medium confidence</p>
      <p className="mt-2 text-lg font-medium leading-snug">Draft a reorder: 120 × Wheat atta 5 kg, 80 × Toor dal 1 kg</p>
      <ul className="mt-3 space-y-1 text-xs text-muted">
        <li>• Evidence: 2 stock-outs in Oct · forecast v3</li>
        <li>• Assumes 9-day supplier lead time, 95% service level</li>
        <li>• Impact: ₹38K–₹55K protected revenue</li>
      </ul>
      <div className="mt-4 flex gap-2">
        <span className="rounded-full bg-fg px-4 py-2 text-xs font-medium text-white">Approve draft</span>
        <span className="rounded-full border border-line px-4 py-2 text-xs text-muted">Edit assumptions</span>
      </div>
    </div>
  );
}
