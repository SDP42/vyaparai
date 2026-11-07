"use client";

import { useState, type ReactNode } from "react";
import { AnimatePresence, motion } from "motion/react";
import { DRIVERS, RFM } from "@/lib/landing-data";
import { formatINRCompact } from "@/lib/format";
import { EASE, Eyebrow, SplitHeading } from "./ui";

const TABS: { key: string; label: string; title: string; body: string; mock: ReactNode }[] = [
  {
    key: "sales",
    label: "Sales",
    title: "See why revenue moved, not just that it moved.",
    body: "Period comparisons broken into volume, price, mix and discount effects, with drill-through to the transactions behind every bar.",
    mock: <SalesMock />,
  },
  {
    key: "customers",
    label: "Customers",
    title: "Know your regulars, and who quietly stopped coming.",
    body: "Interpretable RFM segments and cohort retention, with rules you can read and lists you can export.",
    mock: <CustomersMock />,
  },
  {
    key: "inventory",
    label: "Inventory",
    title: "Stock that keeps up with demand.",
    body: "Stock cover, reorder points and slow movers, with lead time, safety stock and service level shown as editable assumptions.",
    mock: <InventoryMock />,
  },
  {
    key: "forecasting",
    label: "Forecasting",
    title: "Forecasts that admit what they don't know.",
    body: "Baselines first, rolling backtests, prediction intervals and low-confidence labels for products with thin history.",
    mock: <ForecastMock />,
  },
  {
    key: "copilot",
    label: "Copilot",
    title: "Ask in plain words. Get cited answers.",
    body: "Every figure comes from the metric layer, and every document answer points to its page and section.",
    mock: <CopilotMock />,
  },
];

export function ShowcaseSection() {
  const [tab, setTab] = useState(TABS[0].key);
  const current = TABS.find((t) => t.key === tab)!;

  return (
    <section className="relative py-28 sm:py-36" aria-labelledby="showcase-title">
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <div className="max-w-3xl">
          <Eyebrow>Intelligence showcase</Eyebrow>
          <SplitHeading
            id="showcase-title"
            text="Five lenses on the same truth."
            className="mt-4 text-[clamp(2rem,4.4vw,3.6rem)] font-semibold leading-[1] tracking-[-0.03em]"
            accent={["truth"]}
          />
        </div>

        <div role="tablist" aria-label="Intelligence modules" className="mt-10 flex gap-1 overflow-x-auto rounded-full border border-line bg-surface p-1 [scrollbar-width:none] sm:w-fit">
          {TABS.map((t) => (
            <button
              key={t.key}
              role="tab"
              id={`tab-${t.key}`}
              aria-selected={tab === t.key}
              aria-controls={`panel-${t.key}`}
              onClick={() => setTab(t.key)}
              className={`relative shrink-0 rounded-full px-5 py-2.5 text-sm transition-colors ${tab === t.key ? "text-white" : "text-muted hover:text-fg"}`}
            >
              {tab === t.key && (
                <motion.span layoutId="tab-pill" className="absolute inset-0 rounded-full bg-fg" transition={{ type: "spring", stiffness: 380, damping: 32 }} />
              )}
              <span className="relative">{t.label}</span>
            </button>
          ))}
        </div>

        <div className="mt-8 grid gap-8 lg:grid-cols-[0.8fr_1.2fr] lg:items-center">
          <AnimatePresence mode="wait">
            <motion.div
              key={current.key + "-copy"}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              transition={{ duration: 0.4, ease: EASE }}
            >
              <h3 className="text-3xl font-medium leading-tight tracking-tight">{current.title}</h3>
              <p className="mt-4 max-w-md text-muted">{current.body}</p>
            </motion.div>
          </AnimatePresence>
          <div
            id={`panel-${current.key}`}
            role="tabpanel"
            aria-labelledby={`tab-${current.key}`}
            className="relative min-h-[340px] overflow-hidden rounded-[28px] border border-line bg-surface p-5 shadow-[0_40px_80px_-50px_rgba(11,16,32,0.35)] sm:p-8"
          >
            <AnimatePresence mode="wait">
              <motion.div
                key={current.key}
                initial={{ opacity: 0, y: 24, filter: "blur(6px)" }}
                animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                exit={{ opacity: 0, y: -24, filter: "blur(6px)" }}
                transition={{ duration: 0.45, ease: EASE }}
              >
                {current.mock}
              </motion.div>
            </AnimatePresence>
          </div>
        </div>
      </div>
    </section>
  );
}

function SalesMock() {
  const max = 170000;
  return (
    <div>
      <p className="text-sm font-medium">Why net sales fell ₹1.22L (Sep → Oct)</p>
      <div className="mt-6 space-y-4">
        {DRIVERS.map((d, i) => (
          <div key={d.label}>
            <div className="mb-1.5 flex justify-between text-sm">
              <span>{d.label}</span>
              <span className={`font-mono ${d.value < 0 ? "text-danger" : "text-success"}`}>
                {d.value < 0 ? "−" : "+"}
                {formatINRCompact(Math.abs(d.value))} <span className="text-muted">· {d.note}</span>
              </span>
            </div>
            <div className="relative h-3 rounded-full bg-surface-2">
              <motion.div
                className={`absolute top-0 h-full rounded-full ${d.value < 0 ? "right-1/2 bg-danger" : "left-1/2 bg-success"}`}
                initial={{ width: 0 }}
                animate={{ width: `${(Math.abs(d.value) / max) * 50}%` }}
                transition={{ duration: 0.9, ease: EASE, delay: 0.1 + i * 0.1 }}
              />
              <span aria-hidden className="absolute left-1/2 top-[-4px] h-5 w-px bg-line-strong" />
            </div>
          </div>
        ))}
      </div>
      <p className="mt-6 font-mono text-[11px] text-muted">Attribution, not causation · metric:net_sales v1</p>
    </div>
  );
}

function CustomersMock() {
  return (
    <div className="grid gap-6 sm:grid-cols-[1fr_1fr]">
      <div>
        <p className="text-sm font-medium">RFM matrix</p>
        <div className="mt-3 grid grid-cols-5 gap-1.5">
          {RFM.map((v, i) => (
            <motion.span
              key={i}
              className="aspect-square rounded-md"
              initial={{ scale: 0.4, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: i * 0.015, duration: 0.4 }}
              style={{ background: `color-mix(in oklab, var(--color-violet) ${Math.round(v * 100)}%, var(--color-surface-2))` }}
            />
          ))}
        </div>
        <p className="mt-2 font-mono text-[10px] text-muted">recency → · frequency ↑</p>
      </div>
      <ul className="space-y-2 text-sm">
        {[
          ["Champions", "214", "bg-violet"],
          ["Loyal", "388", "bg-blue"],
          ["Needs attention", "540", "bg-warning"],
          ["Lapsed (45d)", "142", "bg-danger"],
        ].map(([n, c, b]) => (
          <li key={n} className="flex items-center justify-between rounded-xl border border-line bg-canvas px-3 py-2.5">
            <span className="flex items-center gap-2">
              <span aria-hidden className={`h-2 w-2 rounded-full ${b}`} />
              {n}
            </span>
            <span className="font-mono">{c}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function InventoryMock() {
  const rows = [
    ["Wheat atta 5 kg", 4, 9, "Reorder now", "text-danger"],
    ["Toor dal 1 kg", 6, 9, "Reorder now", "text-danger"],
    ["Desi ghee 1 L", 14, 7, "Watch", "text-warning"],
    ["Diya set (12)", 96, 12, "Excess stock", "text-muted"],
  ] as const;
  return (
    <div>
      <div className="flex flex-wrap gap-2 text-xs">
        {["Lead time 9 d", "Safety stock 3 d", "Service level 95%"].map((a) => (
          <span key={a} className="rounded-full border border-line bg-canvas px-3 py-1.5 font-mono">
            {a} ✎
          </span>
        ))}
      </div>
      <table className="mt-5 w-full text-sm">
        <thead>
          <tr className="text-left font-mono text-[10px] uppercase tracking-[0.14em] text-muted">
            <th className="pb-2 font-normal">SKU</th>
            <th className="pb-2 text-right font-normal">Days cover</th>
            <th className="pb-2 text-right font-normal">Status</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([n, cover, , s, c]) => (
            <tr key={n} className="border-t border-line">
              <td className="py-2.5">{n}</td>
              <td className="py-2.5 text-right font-mono">{cover}</td>
              <td className={`py-2.5 text-right text-xs font-medium ${c}`}>{s}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ForecastMock() {
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <p className="text-sm font-medium">Desi ghee 1 L · daily units</p>
        <span className="rounded-full bg-success/10 px-2 py-0.5 font-mono text-[10px] text-success">high confidence</span>
      </div>
      <svg viewBox="0 0 400 170" className="mt-4 w-full" aria-hidden>
        {[30, 70, 110, 150].map((y) => (
          <line key={y} x1="0" x2="400" y1={y} y2={y} stroke="var(--color-line)" strokeDasharray="3 6" />
        ))}
        <path d="M220 80 C260 62 320 52 400 40 L400 112 C320 118 260 112 220 96 Z" fill="var(--color-blue)" opacity="0.14" />
        <motion.path
          d="M0 120 C25 100 50 128 75 104 S125 84 150 96 S200 86 220 88"
          fill="none"
          stroke="var(--color-fg)"
          strokeWidth="2.5"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 1.1, ease: EASE }}
        />
        <motion.path
          d="M220 88 C260 80 320 74 400 72"
          fill="none"
          stroke="var(--color-blue)"
          strokeWidth="2.5"
          strokeDasharray="6 6"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 0.8, delay: 1, ease: EASE }}
        />
        <line x1="220" x2="220" y1="10" y2="165" stroke="var(--color-line-strong)" />
      </svg>
      <div className="mt-3 grid grid-cols-3 gap-2 text-center text-xs">
        {[
          ["WAPE", "11.8%"],
          ["vs baseline", "−23%"],
          ["Horizon", "14 d"],
        ].map(([k, v]) => (
          <div key={k} className="rounded-xl border border-line bg-canvas p-2.5">
            <p className="text-muted">{k}</p>
            <p className="font-mono font-medium">{v}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function CopilotMock() {
  return (
    <div className="space-y-3 text-sm">
      <div className="ml-auto w-fit max-w-[80%] rounded-2xl rounded-br-sm bg-fg px-4 py-2.5 text-white">What does our return policy say about damaged goods?</div>
      <div className="max-w-[92%] rounded-2xl rounded-bl-sm border border-line bg-canvas px-4 py-3">
        Damaged goods can be returned within <b>7 days</b> with the original invoice; the supplier credits the cost on the next order.
        <div className="mt-2 flex flex-wrap gap-1.5 font-mono text-[10px]">
          <span className="rounded-full border border-line bg-surface px-2 py-0.5 text-blue-soft">[1] Supplier contract · p.4 §2.1</span>
          <span className="rounded-full border border-line bg-surface px-2 py-0.5 text-blue-soft">[2] Store policy · p.1</span>
        </div>
      </div>
      <p className="font-mono text-[10px] text-muted">Retrieved only from documents you have access to</p>
    </div>
  );
}
