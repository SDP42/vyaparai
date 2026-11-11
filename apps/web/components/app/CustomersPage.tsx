"use client";

import { useState } from "react";
import { download } from "@/lib/api";
import { longDate, num, useApi } from "@/lib/analytics";
import type { Cohorts, CustomerList, CustomersSummary } from "@/lib/intelligence";
import { useAnalyticsState, useWorkspace } from "./AppContext";
import { Card, EmptyNote, ErrorNote, Notices, Skeleton, fmt } from "./analytics/parts";
import { Tx } from "./Tx";

const STATUS_TONE: Record<string, string> = {
  Active: "bg-mor/12 text-mor",
  Cooling: "bg-haldi/25 text-fg",
  Lapsed: "bg-sindoor/10 text-sindoor",
};
const PAGE = 20;

function Tile({ label, value, hint }: { label: string; value: string; hint: string }) {
  return (
    <div className="min-w-0 rounded-2xl border border-line bg-surface p-4">
      <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted">{label}</p>
      <p className="mt-1 truncate text-2xl font-bold tracking-tight">{value}</p>
      <p className="mt-1 text-xs text-muted">{hint}</p>
    </div>
  );
}

export function CustomersPage() {
  const { workspace } = useWorkspace();
  const { dataVersion } = useAnalyticsState();
  const base = `/workspaces/${workspace.id}/analytics/customers`;
  const [segment, setSegment] = useState("");
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState("net");
  const [page, setPage] = useState(0);

  const summary = useApi<CustomersSummary>(`${base}/summary`, [dataVersion]);
  const cohorts = useApi<Cohorts>(`${base}/cohorts`, [dataVersion]);
  const qs = new URLSearchParams({ sort, limit: String(PAGE), offset: String(page * PAGE) });
  if (segment) qs.set("segment", segment);
  if (status) qs.set("status", status);
  if (search.trim()) qs.set("search", search.trim());
  const list = useApi<CustomerList>(`${base}/list?${qs}`, [dataVersion]);

  const s = summary.data;
  const exportQs = new URLSearchParams();
  if (segment) exportQs.set("segment", segment);
  if (status) exportQs.set("status", status);
  if (search.trim()) exportQs.set("search", search.trim());

  const pick = (fn: () => void) => {
    fn();
    setPage(0);
  };
  const input = "rounded-lg border border-line bg-surface px-2.5 py-1.5 text-sm";

  return (
    <div className="space-y-5">
      <header>
        <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-sindoor">{workspace.name}</p>
        <h1 className="mt-1 text-3xl font-bold tracking-tight sm:text-4xl"><Tx k="h.customers" /></h1>
        <p className="mt-1 text-sm text-muted">
          Who buys, how often, and who is drifting away
          {s ? ` · as of ${longDate(s.params.as_of)}, last ${s.params.lookback_days} days` : ""}.
        </p>
      </header>

      {summary.error && <ErrorNote message={summary.error} />}
      {!s && summary.loading && <Skeleton className="h-96" />}

      {s && (
        <div className="space-y-5">
          <Notices warnings={s.warnings} />
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Tile label="Customers" value={fmt("count", s.customers)} hint={`${s.repeat_customers} bought more than once`} />
            <Tile label="Repeat rate" value={fmt("percent", s.repeat_rate)} hint="Customers with 2+ orders" />
            <Tile label="Revenue per customer" value={fmt("inr", s.revenue_per_customer, { compact: true })} hint={`${s.avg_orders_per_customer ?? "–"} orders on average`} />
            <Tile label="Top 10% share" value={fmt("percent", s.top_decile_share)} hint="Of sales from the best tenth" />
          </div>

          <div className="grid gap-5 xl:grid-cols-[1.5fr_1fr]">
            <Card title="Segments" subtitle="Each customer sits in exactly one segment, scored on recency, frequency and spend (R, F, M from 1 to 5).">
              <div className="overflow-x-auto">
                <table className="w-full min-w-[34rem] text-sm">
                  <thead>
                    <tr className="text-left font-mono text-[10px] uppercase tracking-wider text-muted">
                      <th className="py-2 pr-3">Segment</th>
                      <th className="px-2 text-right">Customers</th>
                      <th className="px-2 text-right">Sales share</th>
                      <th className="px-2 text-right">Orders each</th>
                      <th className="pl-2 text-right">Days quiet</th>
                    </tr>
                  </thead>
                  <tbody>
                    {s.segments.map((r) => (
                      <tr key={r.segment} className="border-t border-line align-top">
                        <td className="py-2 pr-3">
                          <button
                            type="button"
                            onClick={() => pick(() => setSegment(segment === r.segment ? "" : r.segment))}
                            aria-pressed={segment === r.segment}
                            className="text-left font-medium underline-offset-4 hover:underline"
                          >
                            {r.segment}
                          </button>
                          <p className="text-xs text-muted">{r.help}</p>
                        </td>
                        <td className="px-2 text-right font-mono">{r.customers}</td>
                        <td className="px-2 text-right font-mono">{fmt("percent", r.net_share)}</td>
                        <td className="px-2 text-right font-mono">{r.avg_orders ?? "–"}</td>
                        <td className="pl-2 text-right font-mono">{r.avg_recency_days ?? "–"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>

            <div className="space-y-5">
              <Card title="Activity" subtitle={`Active: bought within ${s.params.active_days} days · Lapsed: ${s.params.lapse_days}+ days ago`}>
                <div className="space-y-2">
                  {["Active", "Cooling", "Lapsed"].map((k) => {
                    const n = s.status_counts[k] ?? 0;
                    const w = s.customers ? (n / s.customers) * 100 : 0;
                    return (
                      <div key={k}>
                        <div className="flex justify-between text-sm">
                          <span>{k}</span>
                          <span className="font-mono">{n}</span>
                        </div>
                        <div className="mt-1 h-2 rounded-full bg-surface-2">
                          <div className={`h-2 rounded-full ${k === "Active" ? "bg-mor" : k === "Cooling" ? "bg-haldi" : "bg-sindoor"}`} style={{ width: `${w}%` }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
                <p className="mt-3 text-xs text-muted">{s.lapsed_regulars} regular customers (2+ orders) have gone quiet. They are the easiest to win back.</p>
              </Card>
              <RfmGrid grid={s.rfm_grid} />
            </div>
          </div>

          <CohortCard state={cohorts} />

          <Card
            title="All customers"
            subtitle={list.data ? `${list.data.total} match` : undefined}
            action={
              <button
                type="button"
                onClick={() => download(`${base}/export.csv?${exportQs}`, "customers.csv")}
                className="rounded-full border border-line px-3 py-1.5 text-xs hover:bg-surface-2"
              >
                Export CSV
              </button>
            }
          >
            <div className="mb-3 flex flex-wrap gap-2">
              <input
                value={search}
                onChange={(e) => pick(() => setSearch(e.target.value))}
                placeholder="Search ID or city"
                aria-label="Search customers"
                className={`${input} min-w-0 flex-1 sm:flex-none`}
              />
              <select aria-label="Segment" value={segment} onChange={(e) => pick(() => setSegment(e.target.value))} className={input}>
                <option value="">All segments</option>
                {s.segments.map((r) => (
                  <option key={r.segment}>{r.segment}</option>
                ))}
              </select>
              <select aria-label="Activity" value={status} onChange={(e) => pick(() => setStatus(e.target.value))} className={input}>
                <option value="">Any activity</option>
                {["Active", "Cooling", "Lapsed"].map((k) => (
                  <option key={k}>{k}</option>
                ))}
              </select>
              <select aria-label="Sort by" value={sort} onChange={(e) => pick(() => setSort(e.target.value))} className={input}>
                <option value="net">Highest spend</option>
                <option value="orders">Most orders</option>
                <option value="recency">Quietest first</option>
                <option value="last_order">Latest order</option>
              </select>
            </div>
            {list.error && <ErrorNote message={list.error} />}
            {list.data && list.data.items.length === 0 && <EmptyNote>No customers match these filters.</EmptyNote>}
            {list.data && list.data.items.length > 0 && (
              <>
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[44rem] text-sm">
                    <thead>
                      <tr className="text-left font-mono text-[10px] uppercase tracking-wider text-muted">
                        <th className="py-2 pr-3">Customer</th>
                        <th className="px-2">Segment</th>
                        <th className="px-2">Activity</th>
                        <th className="px-2 text-right">Orders</th>
                        <th className="px-2 text-right">Spend</th>
                        <th className="px-2 text-right">Last order</th>
                        <th className="pl-2 text-center">R·F·M</th>
                      </tr>
                    </thead>
                    <tbody>
                      {list.data.items.map((c) => (
                        <tr key={c.key} className="border-t border-line">
                          <td className="py-2 pr-3">
                            <span className="font-mono text-xs">{c.key}</span>
                            <span className="block text-xs text-muted">{[c.city, c.region].filter(Boolean).join(", ") || "–"}</span>
                          </td>
                          <td className="px-2">{c.segment}</td>
                          <td className="px-2">
                            <span className={`rounded-full px-2 py-0.5 text-[11px] ${STATUS_TONE[c.status] ?? ""}`}>{c.status}</span>
                          </td>
                          <td className="px-2 text-right font-mono">{c.orders}</td>
                          <td className="px-2 text-right font-mono">{fmt("inr", c.net)}</td>
                          <td className="px-2 text-right font-mono text-xs">
                            {longDate(c.last_order)}
                            <span className="block text-muted">{c.recency_days}d ago</span>
                          </td>
                          <td className="pl-2 text-center font-mono text-xs">
                            {c.r}·{c.f}·{c.m}
                          </td>
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
                    <button type="button" disabled={page === 0} onClick={() => setPage(page - 1)} className="rounded-full border border-line px-3 py-1 disabled:opacity-40">
                      Previous
                    </button>
                    <button
                      type="button"
                      disabled={(page + 1) * PAGE >= list.data.total}
                      onClick={() => setPage(page + 1)}
                      className="rounded-full border border-line px-3 py-1 disabled:opacity-40"
                    >
                      Next
                    </button>
                  </div>
                </div>
              </>
            )}
          </Card>
        </div>
      )}
    </div>
  );
}

function RfmGrid({ grid }: { grid: number[][] }) {
  const max = Math.max(1, ...grid.flat());
  return (
    <Card title="Recency × frequency" subtitle="Customers by R (rows, 5 = most recent) and F (columns, 5 = most frequent).">
      <div role="table" aria-label="R by F grid" className="grid grid-cols-[auto_repeat(5,1fr)] gap-1 text-center text-xs">
        <span />
        {[1, 2, 3, 4, 5].map((f) => (
          <span key={f} className="font-mono text-[10px] text-muted">
            F{f}
          </span>
        ))}
        {[5, 4, 3, 2, 1].map((r) => (
          <FragmentRow key={r} r={r} cells={grid[r - 1] ?? []} max={max} />
        ))}
      </div>
    </Card>
  );
}

function FragmentRow({ r, cells, max }: { r: number; cells: number[]; max: number }) {
  return (
    <>
      <span className="self-center pr-1 font-mono text-[10px] text-muted">R{r}</span>
      {[0, 1, 2, 3, 4].map((i) => {
        const n = cells[i] ?? 0;
        return (
          <span
            key={i}
            title={`R${r} F${i + 1}: ${n} customers`}
            className="grid h-9 place-items-center rounded-md font-mono"
            style={{ background: n ? `color-mix(in srgb, var(--color-haldi) ${Math.round(18 + (n / max) * 72)}%, transparent)` : "var(--color-surface-2)" }}
          >
            {n || ""}
          </span>
        );
      })}
    </>
  );
}

function CohortCard({ state }: { state: { data: Cohorts | null; error: string | null; loading: boolean } }) {
  const d = state.data;
  return (
    <Card title="Retention by first-order month" subtitle="Of the customers who first bought in a month, the share who bought again in each later month.">
      {state.error && <ErrorNote message={state.error} />}
      {!d && state.loading && <Skeleton className="h-32" />}
      {d && d.cohorts.length === 0 && <EmptyNote>No customer history yet.</EmptyNote>}
      {d && d.cohorts.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="font-mono text-[10px] uppercase tracking-wider text-muted">
                <th className="py-2 pr-3 text-left">Cohort</th>
                <th className="px-2 text-right">Size</th>
                {d.cohorts[0].retention.map((_, i) => (
                  <th key={i} className="px-2 text-center">
                    M{i}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {d.cohorts.map((c) => (
                <tr key={c.cohort} className="border-t border-line">
                  <td className="py-1.5 pr-3 font-mono text-xs">{c.cohort}</td>
                  <td className="px-2 text-right font-mono">{c.size}</td>
                  {c.retention.map((v, i) => {
                    const p = num(v);
                    return (
                      <td key={i} className="p-0.5 text-center">
                        {Number.isFinite(p) ? (
                          <span
                            className="block rounded-md px-1 py-1.5 font-mono text-xs"
                            style={{ background: `color-mix(in srgb, var(--color-mor) ${Math.round(8 + p * 0.6)}%, transparent)` }}
                            title={`${c.counts[i]} customers`}
                          >
                            {p.toFixed(0)}%
                          </span>
                        ) : (
                          <span className="text-muted">·</span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {d?.warnings.map((w) => (
        <p key={w} className="mt-2 text-xs text-muted">
          {w}
        </p>
      ))}
    </Card>
  );
}
