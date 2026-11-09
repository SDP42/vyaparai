"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiError, api, download, type Job } from "@/lib/api";
import { addDays, longDate, useApi } from "@/lib/analytics";
import { hasForecast, type ForecastOverview, type Latest, type ProductForecastPage } from "@/lib/forecast";
import { formatINRCompact, formatNumber } from "@/lib/format";
import { useAnalyticsState, useWorkspace } from "./AppContext";
import { Card, EmptyNote, ErrorNote, Notices, Skeleton } from "./analytics/parts";
import { ConfidenceChip, MODEL_LABEL, RangeBar, Sparkline, useCountUp } from "./forecast/bits";
import { ForecastChart } from "./forecast/ForecastChart";
import { ProductDrawer } from "./forecast/ProductDrawer";
import { WeatherCard } from "./forecast/WeatherCard";

const PAGE = 15;

export function ForecastsPage() {
  const { workspace, canImport } = useWorkspace();
  const { dataVersion } = useAnalyticsState();
  const base = `/workspaces/${workspace.id}/forecasts`;
  const [version, setVersion] = useState(0);
  const latest = useApi<Latest>(`${base}/latest`, [dataVersion, version]);
  const [job, setJob] = useState<Job | null>(null);
  const [runError, setRunError] = useState<string | null>(null);
  const alive = useRef(true);
  useEffect(() => {
    alive.current = true; // set again on mount: React dev mode mounts, unmounts and remounts once
    return () => {
      alive.current = false;
    };
  }, []);

  const running = job !== null && (job.status === "queued" || job.status === "running");
  const run = useCallback(async () => {
    setRunError(null);
    try {
      let j = await api<Job>(`${base}/run`, { method: "POST" });
      setJob(j);
      for (let i = 0; i < 180 && alive.current && (j.status === "queued" || j.status === "running"); i++) {
        await new Promise((r) => setTimeout(r, 900));
        j = await api<Job>(`/workspaces/${workspace.id}/jobs/${j.id}`);
        if (alive.current) setJob(j);
      }
      if (alive.current) setJob(j);
      if (j.status === "failed") setRunError(j.error_message ?? "The forecast could not be built.");
      else if (j.status === "succeeded") setVersion((v) => v + 1);
      else setRunError("The forecast is taking longer than expected. Refresh the page in a moment.");
    } catch (e) {
      setRunError(e instanceof ApiError ? e.message : "Something went wrong");
    }
  }, [base, workspace.id]);

  const d = latest.data;
  const fc = d && hasForecast(d) ? d : null;

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-sindoor">{workspace.name}</p>
          <h1 className="mt-1 text-3xl font-bold tracking-tight sm:text-4xl">Forecasts</h1>
          <p className="mt-1 text-sm text-muted">What to expect over the next two weeks, how sure we are, and why you can trust it.</p>
        </div>
        {canImport && d && (hasForecast(d) || d.can_forecast) && (
          <button
            type="button"
            onClick={run}
            disabled={running}
            className="rounded-full bg-fg px-5 py-2.5 text-sm font-semibold text-canvas transition-colors hover:bg-sindoor disabled:opacity-60"
          >
            {running ? "Building forecast…" : fc ? "Refresh forecast" : "Build my forecast"}
          </button>
        )}
      </header>

      {running && <Progress job={job} />}
      {runError && <ErrorNote message={runError} />}
      {latest.error && <ErrorNote message={latest.error} />}
      {!d && latest.loading && <Skeleton className="h-96" />}

      {d && !hasForecast(d) && !running && <FirstRun can={d.can_forecast} reason={d.reason} days={d.history_days} canRun={canImport} onRun={run} />}
      {fc && <Overview key={fc.run.id} data={fc} base={base} stale={fc.stale} onRefresh={canImport ? run : undefined} running={running} wsId={workspace.id} canEdit={["owner", "admin"].includes(workspace.role)} onLocationSaved={() => setVersion((v) => v + 1)} />}
    </div>
  );
}

function Progress({ job }: { job: Job | null }) {
  const p = job?.progress ?? 5;
  const step = p < 30 ? "Reading your sales" : p < 85 ? "Training and testing the models" : "Saving results";
  return (
    <div className="rounded-2xl border border-line bg-surface p-4" role="status" aria-live="polite">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium">{step}</span>
        <span className="font-mono text-xs text-muted">{p}%</span>
      </div>
      <div className="mt-2 h-2 overflow-hidden rounded-full bg-surface-2">
        <div className="h-2 rounded-full bg-sindoor transition-[width] duration-700" style={{ width: `${Math.max(5, p)}%` }} />
      </div>
    </div>
  );
}

function FirstRun({ can, reason, days, canRun, onRun }: { can: boolean; reason: string | null; days: number; canRun: boolean; onRun: () => void }) {
  return (
    <div className="grid gap-6 rounded-3xl border border-line bg-surface p-6 sm:p-10 lg:grid-cols-[1.2fr_1fr] lg:items-center">
      <div>
        <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-sindoor">First forecast</p>
        <h2 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">See the next two weeks before they happen.</h2>
        <p className="mt-3 max-w-xl text-muted">
          We learn your weekday pattern, your offers and your busy seasons from {days} days of sales, test ourselves on weeks we already know the answer to, and show you a likely range, never a single false-precise number.
        </p>
        {can ? (
          canRun ? (
            <button type="button" onClick={onRun} className="mt-6 rounded-full bg-fg px-6 py-3 font-semibold text-canvas transition-colors hover:bg-sindoor">
              Build my forecast
            </button>
          ) : (
            <p className="mt-6 text-sm text-muted">Ask an analyst or owner to build the first forecast.</p>
          )
        ) : (
          <p className="mt-6 rounded-xl border border-haldi/40 bg-haldi/10 px-4 py-3 text-sm">{reason}</p>
        )}
      </div>
      <ul className="space-y-3 text-sm">
        {["Learns weekdays, offers and seasons", "Tests itself on past weeks first", "Shows a range, not a guess", "Says how sure it is, product by product"].map((t, i) => (
          <li key={t} className="flex items-center gap-3 rounded-xl border border-line bg-canvas px-4 py-3">
            <span className="grid h-6 w-6 place-items-center rounded-full bg-haldi font-mono text-xs font-bold text-ink">{i + 1}</span>
            {t}
          </li>
        ))}
      </ul>
    </div>
  );
}

function Overview({ data, base, stale, onRefresh, running, wsId, canEdit, onLocationSaved }: { data: ForecastOverview; base: string; stale: boolean; onRefresh?: () => void; running: boolean; wsId: string; canEdit: boolean; onLocationSaved: () => void }) {
  const { kpis, accuracy, totals, model_card: card } = data;
  const series = useMemo(
    () => ({
      history: totals.history.map((h) => ({ d: h.d, v: h.units })),
      forecast: totals.forecast.map((f) => ({ d: f.d, p10: f.p10, p50: f.p50, p90: f.p90 })),
      backtest: totals.backtest.map((b) => ({ d: b.d, p: b.p })),
    }),
    [totals],
  );
  const wape = accuracy.wape;
  const units = useCountUp(kpis.units_next);
  const net = useCountUp(kpis.net_next);

  return (
    <div className="space-y-5">
      {stale && (
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-2xl border border-haldi/50 bg-haldi/15 px-4 py-3 text-sm" role="status">
          <span>
            New sales up to <b>{data.latest_data_date ? longDate(data.latest_data_date) : "today"}</b> arrived after this forecast (it ends at {longDate(data.run.as_of)}).
          </span>
          {onRefresh && (
            <button type="button" onClick={onRefresh} disabled={running} className="rounded-full bg-fg px-4 py-1.5 text-xs font-semibold text-canvas hover:bg-sindoor disabled:opacity-60">
              Refresh forecast
            </button>
          )}
        </div>
      )}
      <Notices warnings={data.warnings} />

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Tile
          tone="hero"
          label={`Next ${data.run.horizon} days`}
          value={`${formatNumber(Math.round(units))} units`}
          hint={`Likely ${formatNumber(Math.round(kpis.units_next_low))} to ${formatNumber(Math.round(kpis.units_next_high))}`}
          delta={kpis.units_change_pct}
        />
        <Tile label="Estimated sales" value={formatINRCompact(net)} hint={`Last ${data.run.horizon} days ≈ ${formatINRCompact(kpis.net_last_est)}`} delta={kpis.net_change_pct} />
        <Tile
          label="How close we usually are"
          value={wape == null ? "–" : `within ${Math.round(wape * 100)}%`}
          hint={accuracy.fva != null ? `${accuracy.fva >= 0 ? `${Math.round(accuracy.fva * 100)}% better` : `${Math.round(-accuracy.fva * 100)}% worse`} than repeating last week` : "Tested on past weeks"}
        />
        <Tile label="Range reliability" value={accuracy.interval_coverage_80 == null ? "–" : `${Math.round(accuracy.interval_coverage_80 * 100)}%`} hint="of past outcomes landed inside the likely range" />
      </div>

      <Card title="Total demand" subtitle={`Forecast for ${longDate(totals.forecast[0].d)} to ${longDate(totals.forecast[totals.forecast.length - 1].d)}`}>
        <ForecastChart series={series} height={360} />
      </Card>

      <div className="grid gap-5 xl:grid-cols-[1.2fr_1fr]">
        <TrustPanel data={data} />
        <div className="space-y-5">
          <Movers title="Rising" tone="mor" items={data.risers} empty="No product is expected to grow by much." />
          <Movers title="Falling" tone="sindoor" items={data.fallers} empty="No product is expected to drop by much." />
          <WeatherCard wsId={wsId} signal={data.signals?.weather} accuracy={data.accuracy} canEdit={canEdit} onSaved={onLocationSaved} />
        </div>
      </div>

      <ProductTable base={base} horizon={data.run.horizon} />

      <p className="text-xs text-muted">
        Built {new Date(data.run.created_at).toLocaleString("en-IN")} in {data.run.seconds}s from {data.run.history_days} days of sales across {data.run.n_series} products. Methods: {Object.entries(card.models).filter(([, n]) => n > 0).map(([m, n]) => `${MODEL_LABEL[m]} (${n})`).join(", ")}.
      </p>
    </div>
  );
}

function Tile({ label, value, hint, delta, tone }: { label: string; value: string; hint: string; delta?: number | null; tone?: "hero" }) {
  const hero = tone === "hero";
  return (
    <div className={`min-w-0 rounded-2xl border p-4 ${hero ? "border-fg bg-fg text-canvas" : "border-line bg-surface"}`}>
      <p className={`font-mono text-[10px] uppercase tracking-[0.16em] ${hero ? "text-canvas/60" : "text-muted"}`}>{label}</p>
      <p className="mt-1 truncate text-2xl font-bold tracking-tight sm:text-3xl">{value}</p>
      <p className={`mt-1 text-xs ${hero ? "text-canvas/70" : "text-muted"}`}>{hint}</p>
      {delta != null && (
        <p className={`mt-2 inline-flex rounded-full px-2 py-0.5 font-mono text-[11px] ${hero ? "bg-canvas/15" : "bg-surface-2"}`}>
          {delta > 0 ? "▲" : delta < 0 ? "▼" : "■"} {Math.abs(delta).toFixed(1)}% vs last period
        </p>
      )}
    </div>
  );
}

function TrustPanel({ data }: { data: ForecastOverview }) {
  const { accuracy: a, model_card: m, confidence_counts: c } = data;
  const total = c.high + c.medium + c.low || 1;
  const models = Object.entries(m.models).filter(([, n]) => n > 0);
  return (
    <Card title="Why you can trust this" subtitle={`Tested on ${a.windows} past ${a.windows === 1 ? "window" : "windows"} of ${m.horizon_days} days the model had not seen`}>
      <div className="space-y-4 text-sm">
        <div>
          <p className="mb-1.5 flex justify-between text-xs text-muted">
            <span>How sure we are, by product</span>
            <span>{total} products</span>
          </p>
          <div className="flex h-3 overflow-hidden rounded-full bg-surface-2" role="img" aria-label={`${c.high} reliable, ${c.medium} fair, ${c.low} rough guide`}>
            <div className="bg-mor" style={{ width: `${(c.high / total) * 100}%` }} />
            <div className="bg-haldi" style={{ width: `${(c.medium / total) * 100}%` }} />
            <div className="bg-sindoor" style={{ width: `${(c.low / total) * 100}%` }} />
          </div>
          <p className="mt-1.5 flex flex-wrap gap-x-4 text-xs">
            <span className="text-mor">● {c.high} reliable</span>
            <span className="text-haldi-deep">● {c.medium} fair</span>
            <span className="text-sindoor">● {c.low} rough guide</span>
          </p>
        </div>
        <ul className="space-y-1.5">
          <li>
            {a.gate_passed ? "✓" : "!"} Beat “repeat last week” by <b>{a.fva != null ? `${Math.round(a.fva * 100)}%` : "–"}</b>
            {a.series_beating_naive != null && <span className="text-muted"> · on {Math.round(a.series_beating_naive * 100)}% of products</span>}
          </li>
          <li>
            ✓ The “likely range” held <b>{a.interval_coverage_80 != null ? `${Math.round(a.interval_coverage_80 * 100)}%` : "–"}</b> of the time{a.interval_scale && a.interval_scale > 1 ? <span className="text-muted"> (widened {Math.round((a.interval_scale - 1) * 100)}% after testing)</span> : null}
          </li>
          {a.bias != null && (
            <li>
              {Math.abs(a.bias) < 0.05 ? "✓" : "!"} Leans {a.bias < 0 ? "low" : "high"} by <b>{Math.abs(a.bias * 100).toFixed(1)}%</b> on average
            </li>
          )}
        </ul>
        <details className="rounded-xl border border-line bg-canvas p-3">
          <summary className="cursor-pointer text-sm font-medium">How it works and what it assumes</summary>
          <div className="mt-2 space-y-2 text-xs text-muted">
            <p>
              Methods used: {models.map(([k, n]) => `${MODEL_LABEL[k]} for ${n} products`).join(", ")}. The method for each product is picked by how it did on past weeks.
            </p>
            <p>It looks at: {m.features.join("; ")}.</p>
            <p className="font-medium text-fg">Assumes</p>
            <ul className="list-disc pl-4">{m.assumptions.map((x) => <li key={x}>{x}</li>)}</ul>
            <p className="font-medium text-fg">Limits</p>
            <ul className="list-disc pl-4">{m.limits.map((x) => <li key={x}>{x}</li>)}</ul>
          </div>
        </details>
      </div>
    </Card>
  );
}

function Movers({ title, tone, items, empty }: { title: string; tone: "mor" | "sindoor"; items: ForecastOverview["risers"]; empty: string }) {
  return (
    <Card title={title}>
      {items.length === 0 ? (
        <p className="text-sm text-muted">{empty}</p>
      ) : (
        <ul className="space-y-2">
          {items.map((m) => (
            <li key={m.sku} className="flex items-center justify-between gap-3 text-sm">
              <span className="min-w-0 truncate">{m.name}</span>
              <span className={`shrink-0 font-mono text-xs ${tone === "mor" ? "text-mor" : "text-sindoor"}`}>
                {m.change_pct > 0 ? "▲" : "▼"} {Math.abs(m.change_pct).toFixed(0)}% <span className="text-muted">({Math.round(m.units_last)}→{Math.round(m.units_next)})</span>
              </span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function ProductTable({ base, horizon }: { base: string; horizon: number }) {
  const [search, setSearch] = useState("");
  const [confidence, setConfidence] = useState("");
  const [sort, setSort] = useState("units_next");
  const [page, setPage] = useState(0);
  const [open, setOpen] = useState<string | null>(null);
  const qs = new URLSearchParams({ sort, limit: String(PAGE), offset: String(page * PAGE) });
  if (confidence) qs.set("confidence", confidence);
  if (search.trim()) qs.set("search", search.trim());
  const list = useApi<ProductForecastPage>(`${base}/products?${qs}`, []);
  const max = Math.max(1, ...(list.data?.items.map((i) => i.units_next_high) ?? [1]));
  const input = "rounded-lg border border-line bg-surface px-2.5 py-1.5 text-sm";
  const reset = (fn: () => void) => {
    fn();
    setPage(0);
  };
  return (
    <Card
      title="Every product"
      subtitle={list.data ? `${list.data.total} products · next ${horizon} days · click a row for the full picture` : undefined}
      action={
        <button type="button" onClick={() => download(`${base}/export.csv`, "forecast.csv")} className="rounded-full border border-line px-3 py-1.5 text-xs hover:bg-surface-2">
          Export CSV
        </button>
      }
    >
      <div className="mb-3 flex flex-wrap gap-2">
        <input value={search} onChange={(e) => reset(() => setSearch(e.target.value))} placeholder="Search product or SKU" aria-label="Search products" className={`${input} min-w-0 flex-1 sm:flex-none`} />
        <select aria-label="How sure" value={confidence} onChange={(e) => reset(() => setConfidence(e.target.value))} className={input}>
          <option value="">Any confidence</option>
          <option value="high">Reliable</option>
          <option value="medium">Fair</option>
          <option value="low">Rough guide</option>
        </select>
        <select aria-label="Sort by" value={sort} onChange={(e) => reset(() => setSort(e.target.value))} className={input}>
          <option value="units_next">Biggest forecast</option>
          <option value="change">Biggest growth</option>
          <option value="wape">Least accurate</option>
          <option value="name">Name</option>
        </select>
      </div>
      {list.error && <ErrorNote message={list.error} />}
      {list.data && list.data.items.length === 0 && <EmptyNote>No products match.</EmptyNote>}
      {list.data && list.data.items.length > 0 && (
        <>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[46rem] text-sm">
              <thead>
                <tr className="text-left font-mono text-[10px] uppercase tracking-wider text-muted">
                  <th className="py-2 pr-3">Product</th>
                  <th className="px-2">Trend</th>
                  <th className="px-2 text-right">Next {horizon}d</th>
                  <th className="w-32 px-2">Likely range</th>
                  <th className="px-2 text-right">Change</th>
                  <th className="pl-2">Confidence</th>
                </tr>
              </thead>
              <tbody>
                {list.data.items.map((p) => (
                  <tr key={p.sku} className="cursor-pointer border-t border-line transition-colors hover:bg-surface-2/60" onClick={() => setOpen(p.sku)}>
                    <td className="py-2 pr-3">
                      <button type="button" className="text-left font-medium underline-offset-4 hover:underline" onClick={(e) => { e.stopPropagation(); setOpen(p.sku); }}>
                        {p.name}
                      </button>
                      <span className="block font-mono text-[11px] text-muted">
                        {p.sku} · {MODEL_LABEL[p.model]}
                      </span>
                    </td>
                    <td className="px-2"><Sparkline values={p.spark} /></td>
                    <td className="px-2 text-right font-mono">
                      {formatNumber(Math.round(p.units_next))}
                      <span className="block text-[11px] text-muted">
                        {formatNumber(Math.round(p.units_next_low))}–{formatNumber(Math.round(p.units_next_high))}
                      </span>
                    </td>
                    <td className="px-2"><RangeBar low={p.units_next_low} mid={p.units_next} high={p.units_next_high} max={max} /></td>
                    <td className="px-2 text-right font-mono text-xs">
                      {p.change_pct == null ? "–" : <span className={p.change_pct > 0 ? "text-mor" : p.change_pct < 0 ? "text-sindoor" : ""}>{p.change_pct > 0 ? "▲" : p.change_pct < 0 ? "▼" : "■"} {Math.abs(p.change_pct).toFixed(0)}%</span>}
                    </td>
                    <td className="pl-2"><ConfidenceChip level={p.confidence} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-3 flex items-center justify-between text-xs text-muted">
            <span>
              {page * PAGE + 1}–{Math.min((page + 1) * PAGE, list.data.total)} of {list.data.total}
            </span>
            <div className="flex gap-2">
              <button type="button" disabled={page === 0} onClick={() => setPage(page - 1)} className="rounded-full border border-line px-3 py-1 disabled:opacity-40">Previous</button>
              <button type="button" disabled={(page + 1) * PAGE >= list.data.total} onClick={() => setPage(page + 1)} className="rounded-full border border-line px-3 py-1 disabled:opacity-40">Next</button>
            </div>
          </div>
        </>
      )}
      {open && <ProductDrawer base={base} sku={open} onClose={() => setOpen(null)} />}
    </Card>
  );
}
