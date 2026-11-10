"use client";

import { useState } from "react";
import { ApiError, api } from "@/lib/api";
import { useApi } from "@/lib/analytics";
import { formatINR } from "@/lib/format";
import { useWorkspace } from "./AppContext";
import { Card, EmptyNote, ErrorNote, Skeleton } from "./analytics/parts";

type Goal = { id: string; name: string; metric: string; label: string; unit: "inr" | "count" | "percent"; kind: string; target: number; direction: string; from: string; to: string; status: string; message?: string; value?: number; progress_pct?: number; pace?: number; elapsed_days?: number; total_days?: number; needed_per_day?: number | null; projection?: { low: number; expected: number; high: number; recent_daily: number }; data_through?: string };
type Metric = { key: string; label: string; unit: string; kind: string; direction: string };
type Bench = { enough: boolean; note: string; label?: string; unit?: string; period?: string; median?: number; best?: number; stretch?: number; periods: { from: string; to: string; value: number }[] };

const ST: Record<string, [string, string]> = {
  achieved: ["Reached", "bg-mor/12 text-mor"], met: ["Met", "bg-mor/12 text-mor"], on_track: ["On track", "bg-mor/12 text-mor"], at_risk: ["At risk", "bg-haldi/25"], behind: ["Behind", "bg-sindoor/10 text-sindoor"],
  missed: ["Missed", "bg-sindoor/10 text-sindoor"], not_started: ["Not started", "bg-surface-2 text-muted"], no_data: ["No data", "bg-surface-2 text-muted"],
};
const show = (unit: string, v: number) => (unit === "inr" ? formatINR(v) : unit === "percent" ? `${v.toFixed(1)}%` : v.toLocaleString("en-IN", { maximumFractionDigits: 0 }));

function Bar({ g }: { g: Goal }) {
  const pct = Math.min(100, g.progress_pct ?? 0);
  const pace = g.elapsed_days && g.total_days ? (100 * g.elapsed_days) / g.total_days : null;
  return (
    <div className="mt-3" role="img" aria-label={`${Math.round(g.progress_pct ?? 0)} percent of the target${pace != null ? `, ${Math.round(pace)} percent of the time gone` : ""}`}>
      <div className="relative h-3 overflow-hidden rounded-full bg-surface-2">
        <div className={`h-full transition-[width] duration-700 ${g.status === "behind" || g.status === "missed" ? "bg-sindoor" : g.status === "at_risk" ? "bg-haldi" : "bg-mor"}`} style={{ width: `${pct}%` }} />
        {pace != null && g.kind === "cumulative" && <span aria-hidden className="absolute inset-y-0 w-0.5 bg-fg" style={{ left: `${Math.min(100, pace)}%` }} />}
      </div>
      {pace != null && g.kind === "cumulative" && <p className="mt-1 text-[11px] text-muted">The dark line is where you should be today ({Math.round(pace)}% of the time has gone).</p>}
    </div>
  );
}

export function GoalsPage() {
  const { workspace, canImport } = useWorkspace();
  const base = `/workspaces/${workspace.id}/goals`;
  const [version, setVersion] = useState(0);
  const [form, setForm] = useState({ metric: "net_sales", target: "", period: "month", name: "" });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const list = useApi<Goal[]>(base, [version]);
  const metrics = useApi<Metric[]>(`${base}/metrics`, []);
  const kind = metrics.data?.find((m) => m.key === form.metric);
  const bench = useApi<Bench>(kind && kind.kind !== "point" ? `${base}/benchmarks?metric=${form.metric}&period=${form.period === "week" ? "week" : "month"}` : null, [form.metric, form.period]);

  const add = async () => {
    setBusy(true); setErr(null);
    try { await api(base, { method: "POST", body: JSON.stringify({ metric: form.metric, target: Number(form.target), period: form.period, name: form.name }) }); setForm({ ...form, target: "", name: "" }); setVersion((v) => v + 1); }
    catch (e) { setErr(e instanceof ApiError ? e.message : "Could not save the goal"); }
    finally { setBusy(false); }
  };
  const close = async (id: string) => { try { await api(`${base}/${id}`, { method: "DELETE" }); setVersion((v) => v + 1); } catch (e) { setErr(e instanceof ApiError ? e.message : "Could not close it"); } };
  const f = "mt-1 w-full rounded-lg border border-line bg-canvas px-3 py-2 text-sm";

  return (
    <div className="space-y-6">
      <header>
        <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">Goals</p>
        <h1 className="font-serif text-3xl tracking-tight sm:text-4xl">Where you are against where you want to be</h1>
        <p className="mt-1 max-w-2xl text-sm text-fg/70">Set a target for the month or week. You see your pace, the amount needed each remaining day, and a range for where you will likely finish, not a single promise.</p>
      </header>
      {err && <ErrorNote message={err} />}
      <div className="grid items-start gap-6 lg:grid-cols-[1.5fr_1fr]">
        <section aria-label="Goals" className="space-y-3">
          {list.error && <ErrorNote message={list.error} />}
          {!list.data && list.loading && <Skeleton className="h-40" />}
          {list.data?.length === 0 && <EmptyNote>No goals yet. Set one on the right; the suggestions come from your own past months.</EmptyNote>}
          {list.data?.map((g) => (
            <article key={g.id} className="rounded-2xl border border-line bg-surface p-5">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div><h2 className="font-semibold">{g.name}</h2><p className="text-xs text-muted">{g.label} · {g.from} to {g.to} · {g.direction === "at_most" ? "keep under" : "reach"} {show(g.unit, g.target)}</p></div>
                <span className={`rounded-full px-2.5 py-0.5 text-xs ${(ST[g.status] ?? ST.no_data)[1]}`}>{(ST[g.status] ?? ST.no_data)[0]}</span>
              </div>
              {g.message && <p className="mt-2 text-sm text-muted">{g.message}</p>}
              {g.value != null && (
                <>
                  <p className="mt-3 text-3xl font-bold tracking-tight">{show(g.unit, g.value)} <span className="text-base font-normal text-muted">{g.progress_pct != null && `· ${g.progress_pct.toFixed(0)}% of ${show(g.unit, g.target)}`}</span></p>
                  <Bar g={g} />
                  {g.kind === "cumulative" && g.projection && (
                    <dl className="fluid mt-3 [--min:9rem] text-sm">
                      {g.needed_per_day != null && <div className="rounded-xl bg-canvas px-3 py-2"><dt className="font-mono text-[10px] uppercase tracking-wider text-muted">Needed a day</dt><dd className="font-semibold">{show(g.unit, g.needed_per_day)}</dd></div>}
                      <div className="rounded-xl bg-canvas px-3 py-2"><dt className="font-mono text-[10px] uppercase tracking-wider text-muted">Last 4 weeks a day</dt><dd className="font-semibold">{show(g.unit, g.projection.recent_daily)}</dd></div>
                      <div className="rounded-xl bg-canvas px-3 py-2"><dt className="font-mono text-[10px] uppercase tracking-wider text-muted">Likely finish</dt><dd className="font-semibold">{show(g.unit, g.projection.low)} to {show(g.unit, g.projection.high)}</dd></div>
                    </dl>
                  )}
                  <p className="mt-2 text-xs text-muted">Data through {g.data_through}.</p>
                </>
              )}
              {canImport && <button type="button" onClick={() => close(g.id)} className="mt-3 text-xs text-muted underline underline-offset-4 hover:text-fg">Close this goal</button>}
            </article>
          ))}
        </section>
        <div className="space-y-6">
          {canImport && (
            <Card title="Set a goal" subtitle="For this month or this week.">
              <div className="space-y-3">
                <label className="block text-xs text-muted">What<select className={f} value={form.metric} onChange={(e) => setForm({ ...form, metric: e.target.value })}>{metrics.data?.map((m) => <option key={m.key} value={m.key}>{m.label}{m.direction === "at_most" ? " (keep under)" : ""}</option>)}</select></label>
                <div className="grid grid-cols-2 gap-3">
                  <label className="block text-xs text-muted">Target<input className={f} inputMode="decimal" value={form.target} onChange={(e) => setForm({ ...form, target: e.target.value })} /></label>
                  <label className="block text-xs text-muted">For<select className={f} value={form.period} onChange={(e) => setForm({ ...form, period: e.target.value })}><option value="month">This month</option><option value="week">This week</option></select></label>
                </div>
                <label className="block text-xs text-muted">Name (optional)<input className={f} value={form.name} maxLength={120} onChange={(e) => setForm({ ...form, name: e.target.value })} /></label>
                <button type="button" disabled={busy || !Number(form.target)} onClick={add} className="w-full rounded-full bg-fg px-5 py-2.5 text-sm font-semibold text-canvas hover:bg-sindoor disabled:opacity-50">{busy ? "Saving…" : "Set the goal"}</button>
              </div>
            </Card>
          )}
          <Card title="Your own history" subtitle="Benchmarks come from your last months. There is no data from other shops.">
            {bench.data && !bench.data.enough && <p className="text-sm text-muted">{bench.data.note}</p>}
            {bench.data?.enough && bench.data.unit && (
              <div className="space-y-2 text-sm">
                {[["A usual " + (form.period === "week" ? "week" : "month"), bench.data.median, "Steady"], ["Your best", bench.data.best, "Best"], ["A stretch (top quarter)", bench.data.stretch, "Stretch"]].map(([l, v, k]) => (
                  <div key={k as string} className="flex items-center justify-between gap-2 rounded-xl bg-canvas px-3 py-2"><span>{l as string}<b className="ml-2">{show(bench.data!.unit!, v as number)}</b></span>{canImport && form.metric !== "udhaar_overdue" && <button type="button" onClick={() => setForm({ ...form, target: String(Math.round(v as number)) })} className="rounded-full border border-line px-3 py-1 text-xs hover:bg-surface-2">Use</button>}</div>
                ))}
                <p className="text-xs text-muted">{bench.data.note}</p>
              </div>
            )}
            {kind?.kind === "point" && <p className="text-sm text-muted">This measure is a balance today, so it has no monthly history.</p>}
          </Card>
        </div>
      </div>
    </div>
  );
}
