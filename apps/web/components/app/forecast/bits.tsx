"use client";

import { useEffect, useState } from "react";

/** Counts a number up once, easing out; jumps straight to the value when motion is reduced. */
export function useCountUp(target: number, ms = 900): number {
  const [v, setV] = useState(0);
  useEffect(() => {
    if (!Number.isFinite(target)) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setV(target);
      return;
    }
    let raf = 0;
    const t0 = performance.now();
    const tick = (t: number) => {
      const p = Math.min(1, (t - t0) / ms);
      setV(target * (1 - Math.pow(1 - p, 3)));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, ms]);
  return v;
}

/** Last 28 days solid, forecast dashed. */
export function Sparkline({ values, split = 28, w = 120, h = 34 }: { values: number[]; split?: number; w?: number; h?: number }) {
  if (values.length < 2) return <span className="text-muted">–</span>;
  const max = Math.max(...values, 1);
  const x = (i: number) => (i / (values.length - 1)) * (w - 2) + 1;
  const y = (v: number) => h - 2 - (v / max) * (h - 4);
  const pts = (from: number, to: number) => values.slice(from, to).map((v, i) => `${x(from + i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  const cut = Math.min(split, values.length - 1);
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} aria-hidden className="overflow-visible">
      <polyline points={pts(0, cut + 1)} fill="none" stroke="var(--color-fg)" strokeWidth={1.5} strokeLinejoin="round" />
      <polyline points={pts(cut, values.length)} fill="none" stroke="var(--color-sindoor)" strokeWidth={1.75} strokeDasharray="3 2" strokeLinejoin="round" />
    </svg>
  );
}

/** Where the forecast sits inside its likely range. */
export function RangeBar({ low, mid, high, max }: { low: number; mid: number; high: number; max: number }) {
  const pct = (v: number) => `${Math.min(100, Math.max(0, (v / Math.max(max, 1)) * 100))}%`;
  return (
    <div className="relative h-2 w-full rounded-full bg-surface-2" aria-hidden>
      <div className="absolute inset-y-0 rounded-full bg-haldi/60" style={{ left: pct(low), width: `calc(${pct(high)} - ${pct(low)})` }} />
      <div className="absolute top-1/2 h-3.5 w-1 -translate-y-1/2 rounded-full bg-sindoor" style={{ left: pct(mid) }} />
    </div>
  );
}

const CONF = {
  high: "bg-mor/12 text-mor",
  medium: "bg-haldi/25 text-fg",
  low: "bg-sindoor/10 text-sindoor",
} as const;
export function ConfidenceChip({ level }: { level: "high" | "medium" | "low" }) {
  return <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${CONF[level]}`}>{level === "high" ? "Reliable" : level === "medium" ? "Fair" : "Rough guide"}</span>;
}

export const MODEL_LABEL: Record<string, string> = { lightgbm: "Machine learning", seasonal_average: "Recent average" };
