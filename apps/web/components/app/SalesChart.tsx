import type { DailyPoint } from "@/lib/demo-data";
import { formatINRCompact } from "@/lib/format";

/** Lightweight SVG line chart: solid actuals, dashed forecast, festival band. */
export function SalesChart({ data, compact = false }: { data: DailyPoint[]; compact?: boolean }) {
  const W = 600;
  const H = compact ? 170 : 240;
  const pad = { l: compact ? 4 : 44, r: 8, t: 10, b: 22 };
  const values = data.flatMap((d) => [d.sales, d.forecast ?? NaN]).filter((v) => !Number.isNaN(v));
  const max = Math.max(...values) * 1.08;
  const x = (i: number) => pad.l + (i / (data.length - 1)) * (W - pad.l - pad.r);
  const y = (v: number) => pad.t + (1 - v / max) * (H - pad.t - pad.b);

  const actual = data.filter((d) => !Number.isNaN(d.sales));
  const lastActual = actual[actual.length - 1];
  const forecast = [lastActual, ...data.filter((d) => d.forecast !== undefined)];
  const line = (pts: { day: number; v: number }[]) => pts.map((p, i) => `${i ? "L" : "M"}${x(p.day)},${y(p.v)}`).join(" ");
  const aPath = line(actual.map((d) => ({ day: d.day, v: d.sales })));
  const fPath = line(forecast.map((d) => ({ day: d.day, v: d.forecast ?? d.sales })));
  const ticks = [0.25, 0.5, 0.75, 1].map((f) => max * f);

  const total = actual.reduce((s, d) => s + d.sales, 0);
  return (
    <figure>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label={`Daily net sales for 30 days totalling ${formatINRCompact(total)}, with a 14-day forecast showing a festival peak.`}>
        <rect x={x(33)} width={x(38) - x(33)} y={pad.t} height={H - pad.t - pad.b} fill="var(--color-haldi)" opacity="0.07" />
        <text x={x(33) + 4} y={pad.t + 12} fill="var(--color-haldi)" fontSize="10" fontFamily="var(--font-mono)">Diwali</text>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={pad.l} x2={W - pad.r} y1={y(t)} y2={y(t)} stroke="var(--color-line)" strokeDasharray="2 5" />
            {!compact && (
              <text x={pad.l - 6} y={y(t) + 3} textAnchor="end" fill="var(--color-muted)" fontSize="10" fontFamily="var(--font-mono)">
                {formatINRCompact(t)}
              </text>
            )}
          </g>
        ))}
        <path d={`${aPath} L${x(lastActual.day)},${H - pad.b} L${x(0)},${H - pad.b} Z`} fill="var(--color-paper)" opacity="0.05" />
        <path d={aPath} fill="none" stroke="var(--color-paper)" strokeWidth="2" strokeLinejoin="round" />
        <path d={fPath} fill="none" stroke="var(--color-haldi)" strokeWidth="2" strokeDasharray="5 5" />
        <line x1={x(lastActual.day)} x2={x(lastActual.day)} y1={pad.t} y2={H - pad.b} stroke="var(--color-line)" />
        <text x={x(lastActual.day) + 4} y={H - 6} fill="var(--color-muted)" fontSize="10" fontFamily="var(--font-mono)">today</text>
      </svg>
    </figure>
  );
}
