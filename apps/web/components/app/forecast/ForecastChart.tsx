"use client";

import { useMemo, useState, type ReactNode } from "react";
import { Area, CartesianGrid, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { shortDate } from "@/lib/analytics";

type Pt = { d: string; actual?: number; p50?: number; band?: [number, number]; backtest?: number };
export type SeriesInput = {
  history: { d: string; v: number }[];
  forecast: { d: string; p10: number; p50: number; p90: number }[];
  backtest?: { d: string; p: number }[];
};

const RANGES = [30, 60, 120] as const;

/** History, forecast line and the 80 % range as a fan. Past forecasts can be switched on to show how the model did. */
export function ForecastChart({ series, unit = "units", height = 340 }: { series: SeriesInput; unit?: string; height?: number }) {
  const [range, setRange] = useState<(typeof RANGES)[number]>(60);
  const [showBacktest, setShowBacktest] = useState(false);

  const { data, today } = useMemo(() => {
    const hist = series.history.slice(-range);
    const bt = new Map((series.backtest ?? []).map((b) => [b.d, b.p]));
    const pts: Pt[] = hist.map((h) => ({ d: h.d, actual: h.v, backtest: showBacktest ? bt.get(h.d) : undefined }));
    const last = pts[pts.length - 1];
    if (last?.actual !== undefined) {
      last.p50 = last.actual; // joins the actual line to the forecast line
      last.band = [last.actual, last.actual];
    }
    for (const f of series.forecast) pts.push({ d: f.d, p50: f.p50, band: [f.p10, f.p90] });
    return { data: pts, today: last?.d };
  }, [series, range, showBacktest]);

  const hasBacktest = (series.backtest ?? []).length > 0;
  return (
    <div>
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-4 text-xs text-muted">
          <Legend swatch={<span className="h-0.5 w-5 bg-fg" />} label="What sold" />
          <Legend swatch={<span className="h-0.5 w-5 bg-sindoor" />} label="Forecast" />
          <Legend swatch={<span className="h-3 w-5 rounded-sm bg-haldi/40" />} label="Likely range (80%)" />
          {showBacktest && <Legend swatch={<span className="h-0 w-5 border-t-2 border-dashed border-mor" />} label="What the model said before" />}
        </div>
        <div className="flex items-center gap-2">
          {hasBacktest && (
            <button
              type="button"
              aria-pressed={showBacktest}
              onClick={() => setShowBacktest((v) => !v)}
              className={`rounded-full border px-3 py-1 text-xs transition-colors ${showBacktest ? "border-mor bg-mor/10 text-mor" : "border-line text-fg/65 hover:text-fg"}`}
            >
              Show past accuracy
            </button>
          )}
          <div role="group" aria-label="History shown" className="flex gap-1 rounded-full border border-line bg-canvas p-0.5">
            {RANGES.map((r) => (
              <button key={r} type="button" aria-pressed={range === r} onClick={() => setRange(r)} className={`rounded-full px-2.5 py-1 text-xs ${range === r ? "bg-fg text-canvas" : "text-fg/65 hover:text-fg"}`}>
                {r}d
              </button>
            ))}
          </div>
        </div>
      </div>
      <div style={{ height }} role="img" aria-label={`Chart of ${unit} sold and forecast for the next ${series.forecast.length} days with a likely range`}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <defs>
              <linearGradient id="fan" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--color-haldi)" stopOpacity={0.55} />
                <stop offset="100%" stopColor="var(--color-haldi)" stopOpacity={0.18} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="var(--color-line)" strokeDasharray="2 4" vertical={false} />
            <XAxis dataKey="d" tickFormatter={shortDate} tick={{ fontSize: 11, fill: "var(--color-muted)" }} tickLine={false} axisLine={{ stroke: "var(--color-line)" }} minTickGap={28} />
            <YAxis width={44} tick={{ fontSize: 11, fill: "var(--color-muted)" }} tickLine={false} axisLine={false} />
            <Tooltip content={<Tip unit={unit} />} cursor={{ stroke: "var(--color-fg)", strokeOpacity: 0.25 }} />
            {today && <ReferenceLine x={today} stroke="var(--color-fg)" strokeDasharray="3 3" strokeOpacity={0.5} label={{ value: "Today", position: "insideTopLeft", fontSize: 10, fill: "var(--color-muted)" }} />}
            <Area type="monotone" dataKey="band" stroke="none" fill="url(#fan)" isAnimationActive animationDuration={1100} />
            <Line type="monotone" dataKey="actual" stroke="var(--color-fg)" strokeWidth={2} dot={false} isAnimationActive animationDuration={900} />
            <Line type="monotone" dataKey="p50" stroke="var(--color-sindoor)" strokeWidth={2.5} dot={false} isAnimationActive animationBegin={700} animationDuration={900} />
            {showBacktest && <Line type="monotone" dataKey="backtest" stroke="var(--color-mor)" strokeWidth={1.75} strokeDasharray="4 3" dot={false} connectNulls={false} />}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function Legend({ swatch, label }: { swatch: ReactNode; label: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span aria-hidden className="flex items-center">
        {swatch}
      </span>
      {label}
    </span>
  );
}

type TipProps = { active?: boolean; payload?: { payload: Pt }[]; label?: string | number; unit: string };
function Tip({ active, payload, label, unit }: TipProps) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  const n = (v: number) => v.toLocaleString("en-IN", { maximumFractionDigits: 1 });
  return (
    <div className="rounded-xl border border-line bg-surface px-3 py-2 text-xs shadow-lg">
      <p className="font-mono text-[11px] text-muted">{label ? shortDate(String(label)) : ""}</p>
      {p.actual !== undefined ? (
        <p>
          Sold <b>{n(p.actual)}</b> {unit}
        </p>
      ) : p.p50 !== undefined && p.band ? (
        <>
          <p>
            Forecast <b className="text-sindoor">{n(p.p50)}</b> {unit}
          </p>
          <p className="text-muted">
            Likely {n(p.band[0])} to {n(p.band[1])}
          </p>
        </>
      ) : null}
      {p.backtest !== undefined && <p className="text-mor">Model had said {n(p.backtest)}</p>}
    </div>
  );
}
