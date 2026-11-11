"use client";

import { useMemo, useState } from "react";
import { Area, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { num, type TrendPoint } from "@/lib/analytics";
import { formatINR, formatNumber } from "@/lib/format";
import { fmt } from "./parts";

/**
 * Net sales over time with the comparison period overlaid (aligned by position: day 1 against
 * day 1). A "table" toggle gives a text alternative to the chart.
 */
export function TrendChart({ points, compareLabel }: { points: TrendPoint[]; compareLabel: string | null }) {
  const [asTable, setAsTable] = useState(false);
  const data = useMemo(
    () =>
      points.map((p) => ({
        label: p.label,
        net: num(p.net),
        previous: p.previous_net == null ? null : num(p.previous_net),
        previousLabel: p.previous_label,
        orders: p.orders,
        aov: num(p.aov),
      })),
    [points],
  );
  const total = data.reduce((s, d) => s + d.net, 0);
  const summary = `Net sales per ${points.length > 45 ? "bucket" : "day"} totalling ${formatINR(total)} across ${points.length} points.`;

  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-4 text-xs text-muted">
          <span className="flex items-center gap-1.5">
            <span aria-hidden className="h-0.5 w-5 bg-fg" /> This period
          </span>
          {compareLabel && (
            <span className="flex items-center gap-1.5">
              <span aria-hidden className="h-0 w-5 border-t-2 border-dashed border-muted" /> {compareLabel}
            </span>
          )}
        </div>
        <button type="button" onClick={() => setAsTable((t) => !t)} aria-pressed={asTable} className="text-xs text-muted underline underline-offset-4 hover:text-fg">
          {asTable ? "Show chart" : "Show as table"}
        </button>
      </div>

      {asTable ? (
        <div className="max-h-72 overflow-auto rounded-xl border border-line">
          <table className="w-full text-sm">
            <caption className="sr-only">{summary}</caption>
            <thead className="sticky top-0 bg-canvas">
              <tr className="text-left font-mono text-[10px] uppercase tracking-[0.14em] text-muted">
                <th className="px-3 py-2 font-normal">Date</th>
                <th className="px-3 py-2 text-right font-normal">Net sales</th>
                <th className="px-3 py-2 text-right font-normal">Orders</th>
                <th className="px-3 py-2 text-right font-normal">Compared</th>
              </tr>
            </thead>
            <tbody>
              {data.map((d) => (
                <tr key={d.label} className="border-t border-line/70">
                  <td className="px-3 py-1.5">{d.label}</td>
                  <td className="px-3 py-1.5 text-right tabular">{formatINR(d.net)}</td>
                  <td className="px-3 py-1.5 text-right tabular">{formatNumber(d.orders)}</td>
                  <td className="px-3 py-1.5 text-right tabular text-muted">{d.previous == null ? "–" : formatINR(d.previous)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div role="img" aria-label={summary} className="h-64 sm:h-72">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="netFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#f2a71b" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="#f2a71b" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="#dccfb8" strokeDasharray="3 6" vertical={false} />
              <XAxis dataKey="label" tick={{ fill: "#6a5e4e", fontSize: 11 }} tickLine={false} axisLine={false} minTickGap={24} />
              <YAxis
                tick={{ fill: "#6a5e4e", fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                width={58}
                tickFormatter={(v: number) => fmt("inr", v, { compact: true })}
              />
              <Tooltip
                cursor={{ stroke: "#1b1612", strokeOpacity: 0.2 }}
                contentStyle={{ borderRadius: 12, border: "1px solid #dccfb8", background: "#fffaf1", fontSize: 12 }}
                formatter={(v, name) => [formatINR(Number(v)), name === "net" ? "This period" : "Comparison"]}
                labelFormatter={(l, items) => {
                  const prev = (items as { payload?: { previousLabel?: string | null } }[] | undefined)?.[0]?.payload?.previousLabel;
                  return prev ? `${l}  ·  vs ${prev}` : String(l);
                }}
              />
              <Area type="monotone" dataKey="net" stroke="#1b1612" strokeWidth={2} fill="url(#netFill)" activeDot={{ r: 4 }} />
              {compareLabel && <Line type="monotone" dataKey="previous" stroke="#6a5e4e" strokeWidth={1.8} strokeDasharray="5 5" dot={false} connectNulls />}
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
