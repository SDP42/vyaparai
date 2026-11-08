"use client";

import { useId, useState, type ReactNode } from "react";
import { changeTone, num, type Kpi, type MetricDef, type Unit } from "@/lib/analytics";
import { formatINR, formatNumber } from "@/lib/format";
import { useAnalyticsState } from "../AppContext";

/* ------------------------------------------------------------------ formatting */

export function fmt(unit: Unit, value: string | number | null | undefined, opts: { compact?: boolean } = {}): string {
  const v = typeof value === "number" ? value : num(value);
  if (!Number.isFinite(v)) return "–";
  if (unit === "inr") {
    if (opts.compact && Math.abs(v) >= 1e5) return Math.abs(v) >= 1e7 ? `₹${(v / 1e7).toFixed(2)}Cr` : `₹${(v / 1e5).toFixed(2)}L`;
    return formatINR(v);
  }
  if (unit === "percent") return `${v.toFixed(1)}%`;
  return Number.isInteger(v) ? formatNumber(v) : v.toLocaleString("en-IN", { maximumFractionDigits: 2 });
}

export const signed = (unit: Unit, v: string | number | null, opts: { compact?: boolean } = {}) => {
  const n = typeof v === "number" ? v : num(v);
  if (!Number.isFinite(n)) return "–";
  return `${n > 0 ? "+" : n < 0 ? "−" : ""}${fmt(unit, Math.abs(n), opts)}`;
};

const TONE = {
  good: "bg-mor/12 text-mor",
  bad: "bg-sindoor/10 text-sindoor",
  neutral: "bg-surface-2 text-muted",
} as const;

/** ▲/▼ chip. Colour never carries the meaning alone: the arrow and the sign do too. */
export function DeltaChip({ kpi, label }: { kpi: Pick<Kpi, "change" | "change_pct" | "unit" | "good_direction" | "compare_in_points">; label?: string }) {
  const c = num(kpi.change);
  if (!Number.isFinite(c)) return <span className="font-mono text-[11px] text-muted">no comparison</span>;
  const tone = changeTone(kpi);
  const arrow = c > 0 ? "▲" : c < 0 ? "▼" : "■";
  const pct = num(kpi.change_pct);
  const text = kpi.compare_in_points
    ? `${Math.abs(c).toFixed(1)} pts`
    : Number.isFinite(pct)
      ? `${Math.abs(pct).toFixed(1)}%`
      : signed(kpi.unit, Math.abs(c), { compact: true }).replace(/^[+−]/, "");
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-mono text-[11px] ${TONE[tone]}`}>
      <span aria-hidden>{arrow}</span>
      {text}
      <span className="sr-only">
        {c > 0 ? " increase" : c < 0 ? " decrease" : " no change"}
        {label ? ` ${label}` : ""}
      </span>
    </span>
  );
}

export function ToneDot({ tone }: { tone: "good" | "bad" | "neutral" | "warning" }) {
  const c = { good: "bg-mor", bad: "bg-sindoor", neutral: "bg-muted", warning: "bg-haldi" }[tone];
  return <span aria-hidden className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${c}`} />;
}

/* ------------------------------------------------------------------ layout bits */

export function Card({
  title,
  subtitle,
  action,
  children,
  className = "",
}: {
  title?: string;
  subtitle?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`rounded-2xl border border-line bg-surface p-4 sm:p-5 ${className}`}>
      {(title || action) && (
        <header className="mb-3 flex flex-wrap items-start justify-between gap-2">
          <div>
            {title && <h2 className="font-semibold">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-xs text-muted">{subtitle}</p>}
          </div>
          {action}
        </header>
      )}
      {children}
    </section>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div aria-hidden className={`animate-pulse rounded-xl bg-surface-2 ${className}`} />;
}

export function EmptyNote({ children }: { children: ReactNode }) {
  return <p className="rounded-xl border border-dashed border-line px-4 py-8 text-center text-sm text-muted">{children}</p>;
}

export function ErrorNote({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="rounded-xl border border-sindoor/30 bg-sindoor/5 p-4 text-sm">
      <p className="font-medium text-sindoor">{message}</p>
      {onRetry && (
        <button type="button" onClick={onRetry} className="mt-1 underline underline-offset-4">
          Try again
        </button>
      )}
    </div>
  );
}

export function Notices({ warnings }: { warnings: string[] }) {
  const [open, setOpen] = useState(false);
  if (warnings.length === 0) return null;
  const shown = open ? warnings : warnings.slice(0, 1);
  return (
    <div className="rounded-2xl border border-haldi/40 bg-haldi/10 px-4 py-3 text-sm" role="note" aria-label="Data notices">
      <ul className="space-y-1">
        {shown.map((w) => (
          <li key={w} className="flex gap-2">
            <span aria-hidden>⚠</span>
            <span>{w}</span>
          </li>
        ))}
      </ul>
      {warnings.length > 1 && (
        <button type="button" onClick={() => setOpen((o) => !o)} className="mt-1 text-xs underline underline-offset-4" aria-expanded={open}>
          {open ? "Show less" : `Show ${warnings.length - 1} more`}
        </button>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ "what does this number mean?" */

export function MetricInfo({ metricKey }: { metricKey: string }) {
  const { registry } = useAnalyticsState();
  const [open, setOpen] = useState(false);
  const id = useId();
  const m: MetricDef | undefined = registry?.metrics.find((x) => x.key === metricKey);
  if (!m) return null;
  return (
    <span className="relative inline-block">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-controls={id}
        aria-label={`How ${m.label} is calculated`}
        className="grid h-4 w-4 place-items-center rounded-full border border-line-ish text-[10px] leading-none text-muted hover:text-fg"
        style={{ borderColor: "var(--color-line)" }}
      >
        i
      </button>
      {open && (
        <span
          id={id}
          role="tooltip"
          className="absolute left-0 top-6 z-30 w-64 rounded-xl border border-line bg-surface p-3 text-left text-xs shadow-[0_20px_50px_-20px_rgba(27,22,18,0.4)]"
        >
          <b className="block">{m.label} · v{m.version}</b>
          <span className="mt-1 block text-muted">{m.definition}.</span>
          {m.includes && <span className="mt-1 block text-muted">Includes: {m.includes}.</span>}
          {m.excludes && <span className="mt-1 block text-muted">Excludes: {m.excludes}.</span>}
        </span>
      )}
    </span>
  );
}
