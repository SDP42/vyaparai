"use client";

import { Fragment, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { num, shortDate, useApi } from "@/lib/analytics";
import type { CostHistory, CostItem, CostOverview, CostStatus } from "@/lib/costs";
import { formatINR } from "@/lib/format";
import { useAnalyticsState, useWorkspace } from "./AppContext";
import { Card, EmptyNote, ErrorNote, Skeleton } from "./analytics/parts";
import { Tx } from "./Tx";

const STATUS: Record<CostStatus, { label: string; tone: string; help: string }> = {
  margin_leak: { label: "Margin leak", tone: "bg-sindoor/10 text-sindoor", help: "Cost rose and the price did not keep up" },
  passed_on: { label: "Passed on", tone: "bg-mor/12 text-mor", help: "Cost rose and the price followed" },
  cost_down: { label: "Cost down", tone: "bg-mor/12 text-mor", help: "Cost fell: room to cut price or earn more" },
  stable: { label: "Steady", tone: "bg-surface-2 text-muted", help: "Cost moved less than 3%" },
  no_cost: { label: "No cost", tone: "bg-haldi/25 text-fg", help: "Sold without a recorded cost" },
  new: { label: "New", tone: "bg-surface-2 text-muted", help: "Not sold in the earlier period" },
  too_few: { label: "Too few sales", tone: "bg-surface-2 text-muted", help: "Too few units to compare" },
};
const FILTERS: (CostStatus | "all")[] = ["all", "margin_leak", "passed_on", "cost_down", "no_cost"];

const pct = (v: string | null, digits = 1) => (v == null ? "–" : `${num(v) > 0 ? "+" : ""}${num(v).toFixed(digits)}%`);

export function CostsPage() {
  const { workspace } = useWorkspace();
  const { dataVersion } = useAnalyticsState();
  const base = `/workspaces/${workspace.id}/costs`;
  const { data, error, loading } = useApi<CostOverview>(`${base}/overview`, [dataVersion]);
  const [filter, setFilter] = useState<CostStatus | "all">("all");
  const [open, setOpen] = useState<string | null>(null);
  const items = (data?.items ?? []).filter((i) => filter === "all" || i.status === filter);

  return (
    <div className="space-y-5">
      <header>
        <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-sindoor">{workspace.name}</p>
        <h1 className="mt-1 text-3xl font-bold tracking-tight sm:text-4xl"><Tx k="h.costs" /></h1>
        <p className="mt-1 text-sm text-muted">
          Supplier prices change. We read the cost on every sale to show where a cost went up and your price did not follow.
          {data?.current ? ` Comparing the last ${data.window_days} days with the ${data.window_days} before.` : ""}
        </p>
      </header>

      {error && <ErrorNote message={error} />}
      {!data && loading && <Skeleton className="h-96" />}

      {data && (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Tile hero label="Margin leaks" value={String(data.summary.margin_leaks)} hint="products to reprice" />
            <Tile label="Margin lost" value={formatINR(num(data.summary.leak_amount))} hint={`in the last ${data.window_days} days`} />
            <Tile label="Costs that rose" value={String(data.summary.cost_up)} hint={`${data.summary.cost_down} fell`} />
            <Tile label="Sales with a cost" value={data.summary.unit_coverage_pct == null ? "–" : `${num(data.summary.unit_coverage_pct)}%`} hint={`${data.summary.no_cost} products have none`} />
          </div>

          <Card title="Products" subtitle="Biggest margin leaks first. Click a row for the history and a suggested price.">
            <div className="mb-3 flex flex-wrap gap-1.5" role="group" aria-label="Filter by status">
              {FILTERS.map((f) => (
                <button key={f} type="button" aria-pressed={filter === f} onClick={() => setFilter(f)} className={`rounded-full border px-3 py-1 text-xs ${filter === f ? "border-fg bg-fg text-canvas" : "border-line text-fg/70 hover:text-fg"}`}>
                  {f === "all" ? "All" : STATUS[f].label}
                </button>
              ))}
            </div>
            {items.length === 0 ? (
              <EmptyNote>Nothing matches.</EmptyNote>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[46rem] text-sm">
                  <thead>
                    <tr className="text-left font-mono text-[10px] uppercase tracking-wider text-muted">
                      <th className="py-2 pr-3">Product</th>
                      <th className="px-2 text-right">Cost</th>
                      <th className="px-2 text-right">Price</th>
                      <th className="px-2 text-right">Margin</th>
                      <th className="px-2 text-right">Lost</th>
                      <th className="pl-2">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map((i) => (
                      <Fragment key={i.sku}>
                        <tr className="cursor-pointer border-t border-line hover:bg-surface-2/50" onClick={() => setOpen(open === i.sku ? null : i.sku)}>
                          <td className="py-2 pr-3">
                            <button type="button" aria-expanded={open === i.sku} className="text-left font-medium underline-offset-4 hover:underline">
                              {i.name}
                            </button>
                            <span className="block font-mono text-[11px] text-muted">{i.sku}</span>
                          </td>
                          <td className="px-2 text-right font-mono text-xs">{i.cost_now ? <>{formatINR(num(i.cost_now))}<span className={`block ${num(i.cost_change_pct) > 0 ? "text-sindoor" : num(i.cost_change_pct) < 0 ? "text-mor" : "text-muted"}`}>{pct(i.cost_change_pct)}</span></> : "–"}</td>
                          <td className="px-2 text-right font-mono text-xs">{i.price_now ? <>{formatINR(num(i.price_now))}<span className="block text-muted">{pct(i.price_change_pct)}</span></> : "–"}</td>
                          <td className="px-2 text-right font-mono text-xs">{i.margin_now_pct ? <>{num(i.margin_now_pct).toFixed(1)}%<span className="block text-muted">was {num(i.margin_prev_pct).toFixed(1)}%</span></> : "–"}</td>
                          <td className="px-2 text-right font-mono text-xs">{i.status === "margin_leak" ? formatINR(num(i.leak_amount)) : "–"}</td>
                          <td className="pl-2">
                            <span title={STATUS[i.status].help} className={`rounded-full px-2 py-0.5 text-[11px] ${STATUS[i.status].tone}`}>{STATUS[i.status].label}</span>
                          </td>
                        </tr>
                        {open === i.sku && (
                          <tr className="bg-canvas">
                            <td colSpan={6} className="p-4">
                              <Detail base={base} item={i} />
                            </td>
                          </tr>
                        )}
                      </Fragment>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
          <p className="text-xs text-muted">Cost and price are averages per unit over sales that have a cost recorded, so the two are compared fairly. A leak means the margin fell by more than one point after the cost rose by 3% or more. Add costs on the Data page to cover more products.</p>
        </>
      )}
    </div>
  );
}

function Tile({ label, value, hint, hero }: { label: string; value: string; hint: string; hero?: boolean }) {
  return (
    <div className={`min-w-0 rounded-2xl border p-4 ${hero ? "border-fg bg-fg text-canvas" : "border-line bg-surface"}`}>
      <p className={`font-mono text-[10px] uppercase tracking-[0.16em] ${hero ? "text-canvas/60" : "text-muted"}`}>{label}</p>
      <p className="mt-1 truncate text-2xl font-bold tracking-tight sm:text-3xl">{value}</p>
      <p className={`mt-1 text-xs ${hero ? "text-canvas/70" : "text-muted"}`}>{hint}</p>
    </div>
  );
}

function Detail({ base, item }: { base: string; item: CostItem }) {
  const h = useApi<CostHistory>(`${base}/${encodeURIComponent(item.sku)}/history`, []);
  const data = (h.data?.weeks ?? []).map((w) => ({ d: w.week_start, cost: w.cost == null ? null : num(w.cost), price: w.price == null ? null : num(w.price) }));
  return (
    <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
      <div>
        <p className="mb-1 flex gap-4 text-xs text-muted">
          <span className="flex items-center gap-1.5"><span className="h-0.5 w-5 bg-sindoor" /> Cost per unit</span>
          <span className="flex items-center gap-1.5"><span className="h-0.5 w-5 bg-fg" /> Price per unit</span>
        </p>
        <div style={{ height: 180 }} role="img" aria-label={`Weekly cost and price per unit for ${item.name}`}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 6, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid stroke="var(--color-line)" strokeDasharray="2 4" vertical={false} />
              <XAxis dataKey="d" tickFormatter={shortDate} tick={{ fontSize: 10, fill: "var(--color-muted)" }} tickLine={false} minTickGap={24} />
              <YAxis width={40} tick={{ fontSize: 10, fill: "var(--color-muted)" }} tickLine={false} axisLine={false} domain={["auto", "auto"]} />
              <Tooltip formatter={(v) => formatINR(Number(v))} labelFormatter={(l) => `Week of ${shortDate(String(l))}`} />
              <Line type="stepAfter" dataKey="price" stroke="var(--color-fg)" strokeWidth={2} dot={false} connectNulls />
              <Line type="stepAfter" dataKey="cost" stroke="var(--color-sindoor)" strokeWidth={2} dot={false} connectNulls />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
      <div className="text-sm">
        {item.status === "margin_leak" && item.suggested_price ? (
          <div className="rounded-2xl border border-haldi/50 bg-haldi/15 p-4">
            <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-haldi-deep">Suggested</p>
            <p className="mt-1 text-lg font-bold">Raise the price to {formatINR(num(item.suggested_price))}</p>
            <p className="mt-1 text-xs text-fg/75">
              That is {pct(item.suggested_increase_pct)} on today&apos;s {formatINR(num(item.price_now))} and brings the margin back to {num(item.margin_prev_pct).toFixed(1)}%. Without it you give up about {formatINR(num(item.leak_amount))} every {num(item.units) > 0 ? "28 days" : "period"}.
            </p>
          </div>
        ) : (
          <p className="text-muted">{STATUS[item.status].help}.</p>
        )}
        <p className="mt-3 text-[11px] text-muted">A suggestion, not a rule: check what customers will bear and what nearby shops charge.</p>
      </div>
    </div>
  );
}
