"use client";

import { useLayoutEffect, useMemo, useRef } from "react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { CATEGORIES, INSIGHTS, KPIS, PERIOD, TOP_PRODUCTS, pctChange, revenueSeries } from "@/lib/landing-data";
import { formatINR, formatINRCompact, formatNumber } from "@/lib/format";
import { CountUp, Delta, DemoBadge, Eyebrow, SplitHeading } from "./ui";

gsap.registerPlugin(ScrollTrigger);

const fmt = (format: "inr" | "num") => (v: number) =>
  format === "num" ? formatNumber(Math.round(v)) : v >= 100000 ? formatINRCompact(v) : formatINR(Math.round(v));

export function ProductPreviewSection() {
  const root = useRef<HTMLElement>(null);
  const data = useMemo(() => revenueSeries(), []);

  useLayoutEffect(() => {
    const el = root.current;
    if (!el) return;
    const mm = gsap.matchMedia();
    mm.add("(prefers-reduced-motion: no-preference)", () => {
      gsap.fromTo(
        "[data-preview-frame]",
        { rotateX: 28, scale: 0.84, y: 80, borderRadius: 40 },
        {
          rotateX: 0,
          scale: 1,
          y: 0,
          borderRadius: 28,
          ease: "none",
          scrollTrigger: { trigger: el, start: "top 85%", end: "top 15%", scrub: true },
        },
      );
    });
    return () => mm.revert();
  }, []);

  return (
    <section ref={root} id="solutions" className="relative py-28 sm:py-36" aria-labelledby="preview-title">
      <div aria-hidden className="pointer-events-none absolute inset-x-0 top-1/3 h-[60%] bg-[radial-gradient(ellipse_at_center,rgba(115,87,232,0.14),transparent_65%)]" />
      <div className="relative mx-auto max-w-7xl px-5 sm:px-8">
        <div className="flex flex-col justify-between gap-6 md:flex-row md:items-end">
          <div>
            <Eyebrow>Product preview</Eyebrow>
            <SplitHeading
            id="preview-title"
              text="Your whole shop on one honest screen."
              className="mt-4 max-w-2xl text-[clamp(2rem,4.4vw,3.6rem)] font-semibold leading-[1] tracking-[-0.03em]"
              accent={["honest"]}
            />
          </div>
          <DemoBadge label="Illustrative demo data" />
        </div>

        <div className="mt-12 [perspective:1600px]">
          <div
            data-preview-frame
            className="origin-top overflow-hidden rounded-[28px] border border-line bg-surface shadow-[0_60px_120px_-60px_rgba(11,16,32,0.45)] will-change-transform"
          >
            {/* window chrome */}
            <div className="flex items-center gap-2 border-b border-line px-5 py-3">
              <span className="h-2.5 w-2.5 rounded-full bg-line-strong" />
              <span className="h-2.5 w-2.5 rounded-full bg-line-strong" />
              <span className="h-2.5 w-2.5 rounded-full bg-line-strong" />
              <span className="ml-3 font-mono text-[11px] text-muted">Command center · {PERIOD.current} vs {PERIOD.previous}</span>
            </div>

            <div className="grid gap-4 p-4 sm:p-6">
              <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                {KPIS.map((k) => (
                  <div key={k.key} className="rounded-2xl border border-line bg-canvas p-4">
                    <p className="text-xs text-muted">{k.label}</p>
                    <p className="mt-1 text-2xl font-semibold tracking-tight sm:text-3xl">
                      <CountUp value={k.value} format={fmt(k.format)} />
                    </p>
                    <div className="mt-1 flex items-center gap-2">
                      <Delta v={pctChange(k.value, k.prev)} />
                      <span className="text-[11px] text-muted">vs Sep</span>
                    </div>
                  </div>
                ))}
              </div>

              <div className="grid gap-4 lg:grid-cols-[1.7fr_1fr]">
                <figure className="rounded-2xl border border-line bg-canvas p-4">
                  <figcaption className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
                    <span className="text-sm font-medium">Daily net sales · 14-day forecast</span>
                    <span className="font-mono text-[10px] text-muted">actual · forecast · 80% interval</span>
                  </figcaption>
                  <div className="h-56 sm:h-64" role="img" aria-label="Daily net sales in October with a dip from the 9th to the 17th, followed by a 14-day forecast with an interval band.">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={data} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
                        <defs>
                          <linearGradient id="actualFill" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="#7357e8" stopOpacity={0.28} />
                            <stop offset="100%" stopColor="#7357e8" stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid stroke="#e2e5ee" strokeDasharray="3 6" vertical={false} />
                        <XAxis dataKey="day" tick={{ fill: "#5b6478", fontSize: 10 }} tickLine={false} axisLine={false} interval={6} />
                        <YAxis tick={{ fill: "#5b6478", fontSize: 10 }} tickLine={false} axisLine={false} tickFormatter={(v: number) => formatINRCompact(v)} width={56} />
                        <Tooltip
                          contentStyle={{ borderRadius: 12, border: "1px solid #e2e5ee", fontSize: 12 }}
                          formatter={(v: number | number[], name: string) =>
                            Array.isArray(v) ? [`${formatINRCompact(v[0])}–${formatINRCompact(v[1])}`, "Interval"] : [formatINR(v), name === "actual" ? "Actual" : "Forecast"]
                          }
                        />
                        <Area type="monotone" dataKey="band" stroke="none" fill="#3296f5" fillOpacity={0.14} isAnimationActive />
                        <Area type="monotone" dataKey="actual" stroke="#7357e8" strokeWidth={2.2} fill="url(#actualFill)" isAnimationActive />
                        <Area type="monotone" dataKey="forecast" stroke="#3296f5" strokeWidth={2.2} strokeDasharray="6 5" fill="none" isAnimationActive />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </figure>

                <figure className="rounded-2xl border border-line bg-canvas p-4">
                  <figcaption className="text-sm font-medium">Category contribution</figcaption>
                  <div className="flex items-center gap-4">
                    <div className="h-44 w-44 shrink-0" role="img" aria-label="Category share of net sales: Staples 42%, Dairy 18%, Snacks 14%, Personal care 12%, Household 9%, Beverages 5%.">
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie data={CATEGORIES} dataKey="share" nameKey="name" innerRadius="62%" outerRadius="95%" paddingAngle={2} stroke="none">
                            {CATEGORIES.map((c) => (
                              <Cell key={c.name} fill={c.color} />
                            ))}
                          </Pie>
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                    <ul className="space-y-1.5 text-xs">
                      {CATEGORIES.map((c) => (
                        <li key={c.name} className="flex items-center gap-2">
                          <span aria-hidden className="h-2 w-2 rounded-full" style={{ background: c.color }} />
                          <span className="text-muted">{c.name}</span>
                          <span className="ml-auto font-mono tabular">{c.share}%</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </figure>
              </div>

              <div className="grid gap-4 lg:grid-cols-[1.7fr_1fr]">
                <div className="overflow-hidden rounded-2xl border border-line bg-canvas">
                  <p className="px-4 pt-4 text-sm font-medium">Top products</p>
                  <div className="overflow-x-auto">
                    <table className="mt-2 w-full min-w-[520px] text-sm">
                      <thead>
                        <tr className="border-y border-line text-left font-mono text-[10px] uppercase tracking-[0.14em] text-muted">
                          <th className="px-4 py-2 font-normal">Product</th>
                          <th className="px-4 py-2 font-normal">Category</th>
                          <th className="px-4 py-2 text-right font-normal">Net sales</th>
                          <th className="px-4 py-2 text-right font-normal">vs Sep</th>
                        </tr>
                      </thead>
                      <tbody>
                        {TOP_PRODUCTS.map((p) => (
                          <tr key={p.sku} className="border-b border-line/70 last:border-0">
                            <td className="px-4 py-2.5">
                              {p.name}
                              {p.note && <span className="ml-2 rounded-full bg-danger/10 px-2 py-0.5 text-[10px] text-danger">{p.note}</span>}
                            </td>
                            <td className="px-4 py-2.5 text-muted">{p.category}</td>
                            <td className="px-4 py-2.5 text-right tabular">{formatINR(p.revenue)}</td>
                            <td className="px-4 py-2.5 text-right">
                              <Delta v={p.change} />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
                <div className="rounded-2xl border border-line bg-canvas p-4">
                  <p className="text-sm font-medium">Business insights</p>
                  <ul className="mt-3 space-y-3">
                    {INSIGHTS.map((i) => (
                      <li key={i.title} className="flex gap-3">
                        <span
                          aria-hidden
                          className={`mt-1 h-2 w-2 shrink-0 rounded-full ${i.tone === "danger" ? "bg-danger" : i.tone === "success" ? "bg-success" : "bg-warning"}`}
                        />
                        <div>
                          <p className="text-sm font-medium">{i.title}</p>
                          <p className="text-xs text-muted">{i.body}</p>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
