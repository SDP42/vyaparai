"use client";

import { useEffect } from "react";
import { addDays, longDate, useApi } from "@/lib/analytics";
import type { ProductDetail } from "@/lib/forecast";
import { Skeleton, ErrorNote, fmt } from "../analytics/parts";
import { ConfidenceChip, MODEL_LABEL } from "./bits";
import { ForecastChart } from "./ForecastChart";

/** Side panel for one product: its history, forecast, range and how the model did in the past. */
export function ProductDrawer({ base, sku, onClose }: { base: string; sku: string; onClose: () => void }) {
  const { data, error } = useApi<ProductDetail>(`${base}/products/${encodeURIComponent(sku)}`, []);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const series = data && {
    history: data.data.hist.map((v, i) => ({ d: addDays(data.data.hist_start, i), v })),
    forecast: data.data.p50.map((p50, i) => ({ d: addDays(data.data.fc_start, i), p10: data.data.p10[i], p50, p90: data.data.p90[i] })),
    backtest: data.data.backtest.map((b) => ({ d: b.d, p: b.p })),
  };
  const wape = data?.backtest_wape;
  return (
    <div className="fixed inset-0 z-50" role="dialog" aria-modal="true" aria-label={data ? `Forecast for ${data.name}` : "Product forecast"}>
      <button type="button" aria-label="Close" onClick={onClose} className="absolute inset-0 bg-ink/40 backdrop-blur-[2px]" />
      <aside className="absolute inset-y-0 right-0 flex w-full max-w-[560px] animate-[drawer-in_.28s_cubic-bezier(.16,1,.3,1)] flex-col overflow-y-auto border-l border-line bg-canvas p-5 shadow-2xl sm:p-6">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-sindoor">{sku}</p>
            <h2 className="mt-1 text-2xl font-bold tracking-tight">{data?.name ?? "Loading…"}</h2>
            {data && <p className="text-sm text-muted">{data.category ?? "No category"}</p>}
          </div>
          <button type="button" onClick={onClose} className="rounded-full border border-line px-3 py-1.5 text-sm hover:bg-surface-2">
            Close
          </button>
        </div>

        {error && <div className="mt-4"><ErrorNote message={error} /></div>}
        {!data && !error && <Skeleton className="mt-5 h-80" />}
        {data && series && (
          <div className="mt-5 space-y-5">
            <div className="grid grid-cols-3 gap-3">
              <Stat label="Next 14 days" value={fmt("count", Math.round(data.units_next))} hint={`${fmt("count", Math.round(data.units_next_low))} to ${fmt("count", Math.round(data.units_next_high))}`} />
              <Stat label="Last 14 days" value={fmt("count", Math.round(data.units_last))} hint="what sold" />
              <Stat label="Change" value={data.change_pct == null ? "–" : `${data.change_pct > 0 ? "▲" : data.change_pct < 0 ? "▼" : "■"} ${Math.abs(data.change_pct).toFixed(0)}%`} hint="vs last 14 days" />
            </div>
            <div className="rounded-2xl border border-line bg-surface p-4">
              <ForecastChart series={series} height={260} />
            </div>
            <div className="rounded-2xl border border-line bg-surface p-4 text-sm">
              <div className="flex flex-wrap items-center gap-2">
                <ConfidenceChip level={data.confidence} />
                <span className="rounded-full bg-surface-2 px-2 py-0.5 text-[11px]">{MODEL_LABEL[data.model]}</span>
                <span className="rounded-full bg-surface-2 px-2 py-0.5 text-[11px] capitalize">{data.pattern} demand</span>
              </div>
              <p className="mt-3 text-muted">
                {wape == null
                  ? "Not enough past data to measure accuracy for this product."
                  : `In past tests this product's forecast was off by about ${(wape * 100).toFixed(0)}% on average${
                      data.backtest_bias != null && Math.abs(data.backtest_bias) >= 0.05 ? `, and ran ${data.backtest_bias < 0 ? "low" : "high"} by ${(Math.abs(data.backtest_bias) * 100).toFixed(0)}%` : ""
                    }.`}
              </p>
              <p className="mt-2 text-xs text-muted">Forecast period starts {longDate(data.data.fc_start)}. It assumes no new offers or price changes.</p>
            </div>
          </div>
        )}
      </aside>
    </div>
  );
}

function Stat({ label, value, hint }: { label: string; value: string; hint: string }) {
  return (
    <div className="rounded-xl border border-line bg-surface p-3">
      <p className="font-mono text-[10px] uppercase tracking-wider text-muted">{label}</p>
      <p className="mt-1 text-xl font-bold">{value}</p>
      <p className="text-[11px] text-muted">{hint}</p>
    </div>
  );
}
