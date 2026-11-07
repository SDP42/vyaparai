"use client";

import type { ReactNode } from "react";
import { motion, useReducedMotion } from "motion/react";
import { RFM } from "@/lib/landing-data";
import { EASE, Eyebrow, SplitHeading, SpotlightCard } from "./ui";

type Capability = { name: string; body: string; span: string; art: ReactNode; tag?: string };

const CAPABILITIES: Capability[] = [
  {
    name: "Business Command Center",
    body: "Net sales, profit, orders and AOV, each with its definition, period, filters and data freshness.",
    span: "lg:col-span-6",
    art: <CommandArt />,
  },
  { name: "Sales Intelligence", body: "Explains change by volume, price, mix and discount.", span: "lg:col-span-3", art: <WaterfallArt /> },
  { name: "Customer Intelligence", body: "RFM segments, cohorts and early churn signals.", span: "lg:col-span-3", art: <RfmArt /> },
  { name: "Inventory Intelligence", body: "Stock cover, reorder points and slow movers, with your assumptions visible.", span: "lg:col-span-4", art: <StockArt /> },
  { name: "Predictive Analytics", body: "Baseline-first forecasts with intervals and honest confidence labels.", span: "lg:col-span-4", art: <ForecastArt /> },
  { name: "Review Intelligence", body: "Sentiment and themes such as delivery, quality and price from customer reviews.", span: "lg:col-span-4", art: <ReviewArt /> },
  { name: "Document Intelligence", body: "Ask your policies and supplier contracts. Answers cite page and section.", span: "lg:col-span-4", art: <DocArt /> },
  { name: "Vyapar Copilot", body: "Plain-language questions, with every figure taken from the metric layer.", span: "lg:col-span-4", art: <CopilotArt /> },
  { name: "Agentic Workflows", body: "Bounded, read-only investigations with a full trace of every tool call.", span: "lg:col-span-4", art: <TraceArt /> },
  {
    name: "Decision Support",
    body: "Ranked recommendations with evidence, impact range, confidence and an owner-approved status.",
    span: "lg:col-span-12",
    art: <DecisionArt />,
  },
];

export function IntelligenceSection() {
  const reduce = useReducedMotion();
  return (
    <section id="platform" className="relative py-28 sm:py-36" aria-labelledby="platform-title">
      <div aria-hidden className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-line-strong to-transparent" />
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <div className="max-w-3xl">
          <Eyebrow>The platform</Eyebrow>
          <SplitHeading
            id="platform-title"
            text="One intelligence layer. Your entire business."
            className="mt-4 text-[clamp(2.2rem,5vw,4.2rem)] font-semibold leading-[0.98] tracking-[-0.035em]"
            accent={["intelligence"]}
          />
          <p className="mt-5 max-w-xl text-muted">
            Ten capabilities sharing one source of truth, from the numbers on your dashboard to the answer the
            Copilot gives you.
          </p>
        </div>

        <ul className="mt-14 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-12 [perspective:1400px]">
          {CAPABILITIES.map((c, i) => (
            <motion.li
              key={c.name}
              className={`${c.span} ${i === 0 || i === 9 ? "sm:col-span-2" : ""}`}
              initial={reduce ? false : { opacity: 0, y: 60, rotateX: -14 }}
              whileInView={{ opacity: 1, y: 0, rotateX: 0 }}
              viewport={{ once: true, margin: "-6% 0px" }}
              transition={{ duration: 0.9, ease: EASE, delay: (i % 3) * 0.08 }}
            >
              <SpotlightCard className="h-full p-6 sm:p-7">
                <div className="flex h-full flex-col">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[11px] text-muted">{String(i + 1).padStart(2, "0")}</span>
                  </div>
                  <div className="my-6 flex min-h-32 items-center">{c.art}</div>
                  <h3 className="text-xl font-medium tracking-tight">{c.name}</h3>
                  <p className="mt-1.5 max-w-xl text-sm leading-relaxed text-muted">{c.body}</p>
                </div>
              </SpotlightCard>
            </motion.li>
          ))}
        </ul>
      </div>
    </section>
  );
}

/* ---------------- unique visual compositions ---------------- */

function CommandArt() {
  const k = [
    ["Net sales", "₹18.46L", "▼ 6.2%", "text-danger"],
    ["Gross profit", "₹4.39L", "▼ 3.1%", "text-danger"],
    ["Orders", "3,412", "▼ 8.9%", "text-danger"],
    ["AOV", "₹541", "▲ 3.0%", "text-success"],
  ];
  return (
    <div className="grid w-full grid-cols-2 gap-2 sm:grid-cols-4" aria-hidden>
      {k.map(([l, v, d, c]) => (
        <div key={l} className="rounded-2xl border border-line bg-canvas/60 p-3">
          <p className="text-[11px] text-muted">{l}</p>
          <p className="mt-1 text-lg font-semibold tabular">{v}</p>
          <p className={`font-mono text-[10px] ${c}`}>{d}</p>
          <svg viewBox="0 0 60 16" className="mt-2 h-4 w-full">
            <path d="M0 10 L10 8 L20 11 L30 6 L40 9 L50 4 L60 7" fill="none" stroke="var(--color-violet-soft)" strokeWidth="1.5" className="[stroke-dasharray:120] [stroke-dashoffset:120] group-hover:[stroke-dashoffset:0] transition-[stroke-dashoffset] duration-1000" />
          </svg>
        </div>
      ))}
    </div>
  );
}

function WaterfallArt() {
  const bars = [
    { h: 80, y: 0, c: "bg-line-strong", l: "Sep" },
    { h: 30, y: 50, c: "bg-danger/80", l: "Vol" },
    { h: 12, y: 38, c: "bg-success/80", l: "Price" },
    { h: 4, y: 46, c: "bg-danger/80", l: "Mix" },
    { h: 50, y: 30, c: "bg-violet", l: "Oct" },
  ];
  return (
    <div className="flex h-28 w-full items-end gap-2" aria-hidden>
      {bars.map((b) => (
        <div key={b.l} className="relative flex h-full flex-1 flex-col justify-end">
          <div className={`w-full rounded-md ${b.c} transition-transform duration-700 group-hover:scale-y-105`} style={{ height: `${b.h}%`, marginBottom: `${b.y}%`, transformOrigin: "bottom" }} />
          <span className="mt-1 text-center font-mono text-[9px] text-muted">{b.l}</span>
        </div>
      ))}
    </div>
  );
}

function RfmArt() {
  return (
    <div className="grid w-full grid-cols-5 gap-1" aria-hidden>
      {RFM.map((v, i) => (
        <span
          key={i}
          className="aspect-square rounded-[5px] transition-transform duration-500 group-hover:scale-95"
          style={{ background: `color-mix(in oklab, var(--color-blue) ${Math.round(v * 100)}%, var(--color-surface-2))`, transitionDelay: `${i * 12}ms` }}
        />
      ))}
    </div>
  );
}

function StockArt() {
  const rows = [
    ["Wheat atta 5 kg", 12, "text-danger", "bg-danger"],
    ["Desi ghee 1 L", 48, "text-warning", "bg-warning"],
    ["Basmati 5 kg", 86, "text-success", "bg-success"],
  ] as const;
  return (
    <div className="w-full space-y-3" aria-hidden>
      {rows.map(([n, v, t, b]) => (
        <div key={n}>
          <div className="mb-1 flex justify-between text-xs">
            <span className="text-muted">{n}</span>
            <span className={`font-mono ${t}`}>{v}% cover</span>
          </div>
          <div className="h-1.5 rounded-full bg-surface-2">
            <div className={`h-full rounded-full ${b} transition-[width] duration-700`} style={{ width: `${v}%` }} />
          </div>
        </div>
      ))}
    </div>
  );
}

function ForecastArt() {
  return (
    <svg viewBox="0 0 240 100" className="w-full" aria-hidden>
      <path d="M140 52 C165 40 190 30 240 22 L240 62 C190 66 165 66 140 58 Z" fill="var(--color-violet)" opacity="0.18" />
      <path d="M0 70 C20 60 40 75 60 62 S100 50 120 56 S135 54 140 55" fill="none" stroke="var(--color-fg)" strokeWidth="2" />
      <path d="M140 55 C165 50 190 46 240 42" fill="none" stroke="var(--color-violet-soft)" strokeWidth="2" strokeDasharray="5 5" />
      <line x1="140" x2="140" y1="10" y2="95" stroke="var(--color-line-strong)" />
      <text x="146" y="92" fill="var(--color-muted)" fontSize="9" fontFamily="var(--font-mono)">
        80% interval · medium confidence
      </text>
    </svg>
  );
}

function ReviewArt() {
  const a = [
    ["Quality", 78, "bg-success"],
    ["Price", 54, "bg-blue"],
    ["Delivery", 31, "bg-danger"],
    ["Packaging", 62, "bg-violet"],
  ] as const;
  return (
    <div className="w-full space-y-2" aria-hidden>
      {a.map(([n, v, c]) => (
        <div key={n} className="flex items-center gap-3 text-xs">
          <span className="w-16 text-muted">{n}</span>
          <div className="h-2 flex-1 rounded-full bg-surface-2">
            <div className={`h-full rounded-full ${c}`} style={{ width: `${v}%` }} />
          </div>
          <span className="w-8 text-right font-mono text-muted">{v}</span>
        </div>
      ))}
    </div>
  );
}

function DocArt() {
  return (
    <div className="relative w-full rounded-2xl border border-line bg-canvas/60 p-4" aria-hidden>
      <div className="space-y-1.5">
        {[90, 75, 82].map((w, i) => (
          <div key={i} className="h-1.5 rounded bg-line" style={{ width: `${w}%` }} />
        ))}
        <div className="rounded bg-blue/20 px-1 py-0.5 text-[11px] text-blue-soft">Returns accepted within 7 days with invoice…</div>
        {[70, 88].map((w, i) => (
          <div key={i} className="h-1.5 rounded bg-line" style={{ width: `${w}%` }} />
        ))}
      </div>
      <span className="absolute -bottom-3 right-4 rounded-full border border-line-strong bg-surface-2 px-2.5 py-1 font-mono text-[10px] text-fg">
        [1] Supplier contract · p.4 §2.1
      </span>
    </div>
  );
}

function CopilotArt() {
  return (
    <div className="w-full space-y-2 text-xs" aria-hidden>
      <div className="ml-auto w-fit rounded-2xl rounded-br-sm bg-fg px-3 py-2 text-canvas">Top products this week?</div>
      <div className="w-fit max-w-[90%] rounded-2xl rounded-bl-sm border border-line bg-canvas/60 px-3 py-2 text-muted">
        Desi ghee leads at <b className="text-fg">₹42.1K</b>, up 4.2%.
        <span className="ml-1 font-mono text-[10px] text-blue-soft">[metric:net_sales v1]</span>
      </div>
    </div>
  );
}

function TraceArt() {
  const steps = ["plan", "get_sales_summary", "compare_periods", "summarise"];
  return (
    <ol className="w-full space-y-1.5 font-mono text-[11px]" aria-hidden>
      {steps.map((s, i) => (
        <li key={s} className="flex items-center gap-2">
          <span className="grid h-5 w-5 place-items-center rounded-full border border-line-strong text-[9px] text-muted">{i + 1}</span>
          <span className={i === 3 ? "text-fg" : "text-muted"}>{s}()</span>
          <span className="ml-auto text-success">✓ {[12, 84, 61, 9][i]}ms</span>
        </li>
      ))}
    </ol>
  );
}

function DecisionArt() {
  const states = ["Proposed", "Approved", "Completed", "Outcome measured"];
  return (
    <div className="grid w-full gap-4 md:grid-cols-[1.2fr_1fr] md:items-center" aria-hidden>
      <div className="rounded-2xl border border-line bg-canvas/60 p-4">
        <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-brass">Recommendation · medium confidence</p>
        <p className="mt-1.5 font-medium">Draft a reorder for Wheat atta 5 kg and Toor dal 1 kg</p>
        <p className="mt-1 text-xs text-muted">Impact ₹38K–₹55K · Evidence: 2 stock-outs, forecast v3 · Assumes 9-day lead time</p>
      </div>
      <ol className="flex flex-wrap items-center gap-2 text-xs">
        {states.map((s, i) => (
          <li key={s} className="flex items-center gap-2">
            <span className={`rounded-full px-3 py-1 ${i <= 1 ? "bg-violet/20 text-violet-soft" : "border border-line text-muted"}`}>{s}</span>
            {i < states.length - 1 && <span className="text-muted">→</span>}
          </li>
        ))}
      </ol>
    </div>
  );
}
