"use client";

import { useEffect, useRef, useState } from "react";
import {
  longDate,
  num,
  toSearch,
  useApi,
  type Dimension,
  type DriverEffect,
  type Drivers,
  type MixRow,
  type ProductMove,
  type TransactionRow,
  type Transactions,
} from "@/lib/analytics";
import { useAnalyticsState, useWorkspace } from "./AppContext";
import { PeriodBar } from "./analytics/PeriodBar";
import { Card, EmptyNote, ErrorNote, Notices, Skeleton, ToneDot, fmt, signed } from "./analytics/parts";

const DIMENSIONS: { key: Dimension; label: string }[] = [
  { key: "category", label: "Category" },
  { key: "product", label: "Product" },
  { key: "channel", label: "Channel" },
  { key: "region", label: "Region" },
];

export function SalesExplorer() {
  const { workspace } = useWorkspace();
  const { query, dataVersion, setFilter } = useAnalyticsState();
  const [by, setBy] = useState<Dimension>("category");
  const base = `/workspaces/${workspace.id}`;
  const { data, error, loading } = useApi<Drivers>(`${base}/analytics/drivers?${toSearch(query, { by })}`, [dataVersion]);

  // Clicking a row narrows every number on the page to that slice.
  const drill = (row: MixRow) => {
    if (by === "product") setFilter("sku", [row.key]);
    else setFilter(by, [row.key]);
    document.getElementById("transactions")?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <div className="space-y-5">
      <header>
        <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-sindoor">{workspace.name}</p>
        <h1 className="mt-1 text-3xl font-bold tracking-tight sm:text-4xl">Sales</h1>
        <p className="mt-1 text-sm text-muted">What moved net sales, how much each part contributed, and the transactions behind it.</p>
      </header>

      <PeriodBar showFilters />
      {error && <ErrorNote message={error} />}
      {!data && loading && <Skeleton className="h-96" />}

      {data && (
        <div className={`space-y-5 transition-opacity ${loading ? "opacity-60" : "opacity-100"}`} aria-busy={loading}>
          <Notices warnings={data.warnings} />
          <DriversPanel data={data} />

          <div className="grid gap-5 xl:grid-cols-[1.6fr_1fr]">
            <Card
              title="Contribution to the change"
              subtitle="How much each slice added or took away. Click a row to look at only that slice."
              action={
                <div role="tablist" aria-label="Group by" className="flex gap-1 rounded-full border border-line bg-canvas p-0.5">
                  {DIMENSIONS.map((d) => (
                    <button
                      key={d.key}
                      role="tab"
                      aria-selected={by === d.key}
                      onClick={() => setBy(d.key)}
                      className={`rounded-full px-3 py-1 text-xs ${by === d.key ? "bg-fg text-canvas" : "text-fg/65 hover:text-fg"}`}
                    >
                      {d.label}
                    </button>
                  ))}
                </div>
              }
            >
              <Contributions rows={data.contributions} compare={!!data.meta.compare} onPick={drill} />
            </Card>
            <Movers data={data} />
          </div>
        </div>
      )}

      <Transactions />
    </div>
  );
}

/* ------------------------------------------------------------------ drivers */

function DriversPanel({ data }: { data: Drivers }) {
  const [open, setOpen] = useState(false);
  const has = data.net_change != null && data.net_sales_previous != null;
  return (
    <Card
      title="What drove net sales"
      subtitle={
        data.meta.compare
          ? `${longDate(data.meta.compare.date_from)} → ${longDate(data.meta.compare.date_to)} compared with ${longDate(data.meta.period.date_from)} → ${longDate(data.meta.period.date_to)}`
          : "Choose a comparison above to see what changed"
      }
    >
      {!has ? (
        <EmptyNote>There is no comparison period with sales, so there is no change to explain.</EmptyNote>
      ) : (
        <>
          <Waterfall data={data} />
          <button type="button" onClick={() => setOpen((o) => !o)} aria-expanded={open} className="mt-4 text-xs text-muted underline underline-offset-4 hover:text-fg">
            {open ? "Hide" : "How is this calculated?"}
          </button>
          {open && (
            <div className="mt-2 rounded-xl bg-canvas p-3 text-xs leading-relaxed text-muted">
              <p>{data.method}</p>
              <p className="mt-1">
                {data.continuing_products} products were sold in both periods, {data.new_products} are new and {data.discontinued_products} sold only before.
              </p>
              <p className="mt-1 font-medium text-fg/80">{data.caveat}</p>
            </div>
          )}
        </>
      )}
    </Card>
  );
}

function Waterfall({ data }: { data: Drivers }) {
  const effects = data.effects;
  const max = Math.max(...effects.map((e) => Math.abs(num(e.amount))), 1);
  const change = num(data.net_change);
  return (
    <div>
      <div className="flex items-baseline justify-between border-b border-line pb-2 text-sm">
        <span className="text-muted">Previous period</span>
        <span className="font-semibold tabular">{fmt("inr", data.net_sales_previous)}</span>
      </div>
      <ul className="divide-y divide-line/60">
        {effects.map((e) => (
          <EffectRow key={e.key} e={e} max={max} />
        ))}
      </ul>
      <div className="flex items-baseline justify-between border-t-2 border-fg/70 pt-2 text-sm">
        <span className="font-medium">
          This period
          <span className={`ml-2 font-mono text-xs ${change > 0 ? "text-mor" : change < 0 ? "text-sindoor" : "text-muted"}`}>
            <span aria-hidden>{change > 0 ? "▲" : change < 0 ? "▼" : ""}</span> {signed("inr", change)}
          </span>
        </span>
        <span className="text-lg font-bold tabular">{fmt("inr", data.net_sales_current)}</span>
      </div>
    </div>
  );
}

function EffectRow({ e, max }: { e: DriverEffect; max: number }) {
  const amount = num(e.amount);
  const width = (Math.abs(amount) / max) * 50;
  return (
    <li className="grid items-center gap-x-4 gap-y-1 py-2.5 sm:grid-cols-[170px_1fr_110px]">
      <div>
        <p className="text-sm font-medium">{e.label}</p>
        <p className="hidden text-[11px] leading-snug text-muted sm:block">{e.explanation}</p>
      </div>
      <div className="relative h-5" aria-hidden>
        <span className="absolute inset-y-0 left-1/2 w-px bg-line" />
        <span
          className={`absolute inset-y-1 rounded-sm ${amount >= 0 ? "left-1/2 bg-mor/80" : "right-1/2 bg-sindoor/80"}`}
          style={{ width: `${Math.max(width, amount === 0 ? 0 : 0.8)}%` }}
        />
      </div>
      <p className={`text-right font-mono text-sm tabular ${amount > 0 ? "text-mor" : amount < 0 ? "text-sindoor" : "text-muted"}`}>
        <span aria-hidden>{amount > 0 ? "▲ " : amount < 0 ? "▼ " : ""}</span>
        {signed("inr", amount)}
        <span className="sr-only">{amount > 0 ? " increase" : amount < 0 ? " decrease" : ""}</span>
      </p>
    </li>
  );
}

/* ------------------------------------------------------------------ contributions & movers */

function Contributions({ rows, compare, onPick }: { rows: MixRow[]; compare: boolean; onPick: (r: MixRow) => void }) {
  if (rows.length === 0) return <EmptyNote>No sales in this period.</EmptyNote>;
  const shown = rows.slice(0, 12);
  const maxAbs = Math.max(...shown.map((r) => Math.abs(num(r.delta))), 1);
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[520px] text-sm">
        <thead>
          <tr className="text-left font-mono text-[10px] uppercase tracking-[0.14em] text-muted">
            <th className="pb-2 font-normal">Name</th>
            <th className="pb-2 text-right font-normal">Net sales</th>
            {compare && <th className="pb-2 text-right font-normal">Change</th>}
            {compare && <th className="w-32 pb-2 pl-3 font-normal">Share of change</th>}
          </tr>
        </thead>
        <tbody>
          {shown.map((r) => {
            const d = r.delta == null ? null : num(r.delta);
            return (
              <tr key={r.key} className="cursor-pointer border-t border-line/70 hover:bg-surface-2/50" onClick={() => onPick(r)}>
                <td className="py-2 pr-2">
                  <button type="button" className="text-left font-medium underline-offset-4 hover:underline" onClick={(e) => { e.stopPropagation(); onPick(r); }}>
                    {r.label}
                  </button>
                </td>
                <td className="py-2 text-right tabular">{fmt("inr", r.net)}</td>
                {compare && (
                  <td className={`py-2 text-right font-mono text-xs ${d == null || d === 0 ? "text-muted" : d > 0 ? "text-mor" : "text-sindoor"}`}>
                    <span aria-hidden>{d != null && d > 0 ? "▲ " : d != null && d < 0 ? "▼ " : ""}</span>
                    {d == null ? "–" : signed("inr", d, { compact: true })}
                  </td>
                )}
                {compare && (
                  <td className="py-2 pl-3" aria-hidden>
                    <div className="relative h-3">
                      <span className="absolute inset-y-0 left-1/2 w-px bg-line" />
                      {d != null && (
                        <span
                          className={`absolute inset-y-0.5 rounded-sm ${d >= 0 ? "left-1/2 bg-mor/70" : "right-1/2 bg-sindoor/70"}`}
                          style={{ width: `${(Math.abs(d) / maxAbs) * 50}%` }}
                        />
                      )}
                    </div>
                  </td>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function Movers({ data }: { data: Drivers }) {
  const list = (items: ProductMove[]) =>
    items.map((m) => (
      <li key={m.sku} className="flex items-start justify-between gap-3 py-2 text-sm">
        <span className="min-w-0">
          <span className="block truncate font-medium">{m.name}</span>
          <span className="font-mono text-[10px] text-muted">
            {m.sku} · units {num(m.units_prev).toLocaleString("en-IN")} → {num(m.units_cur).toLocaleString("en-IN")}
          </span>
        </span>
        <span className={`shrink-0 font-mono text-xs ${num(m.delta) >= 0 ? "text-mor" : "text-sindoor"}`}>
          <span aria-hidden>{num(m.delta) >= 0 ? "▲ " : "▼ "}</span>
          {signed("inr", m.delta, { compact: true })}
        </span>
      </li>
    ));
  return (
    <Card title="Biggest movers" subtitle="Products with the largest change in net sales">
      {data.biggest_decliners.length + data.biggest_gainers.length === 0 ? (
        <EmptyNote>No product moved against the comparison.</EmptyNote>
      ) : (
        <div className="space-y-3">
          {data.biggest_decliners.length > 0 && (
            <div>
              <p className="mb-1 flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.14em] text-muted">
                <ToneDot tone="bad" /> Down
              </p>
              <ul className="divide-y divide-line/60">{list(data.biggest_decliners)}</ul>
            </div>
          )}
          {data.biggest_gainers.length > 0 && (
            <div>
              <p className="mb-1 flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.14em] text-muted">
                <ToneDot tone="good" /> Up
              </p>
              <ul className="divide-y divide-line/60">{list(data.biggest_gainers)}</ul>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

/* ------------------------------------------------------------------ drill-through */

const PAGE = 25;

function Transactions() {
  const { workspace } = useWorkspace();
  const { query, dataVersion } = useAnalyticsState();
  const [search, setSearch] = useState("");
  const [debounced, setDebounced] = useState("");
  const [offset, setOffset] = useState(0);
  const first = useRef(true);

  useEffect(() => {
    const t = setTimeout(() => {
      setDebounced(search);
      setOffset(0);
    }, 250);
    return () => clearTimeout(t);
  }, [search]);
  const key = toSearch(query);
  useEffect(() => {
    if (first.current) first.current = false;
    else setOffset(0);
  }, [key]);

  const path = `/workspaces/${workspace.id}/analytics/transactions?${toSearch(query, { limit: PAGE, offset, search: debounced })}`;
  const { data, error, loading } = useApi<Transactions>(path, [dataVersion]);

  return (
    <Card
      title="Transactions"
      subtitle={
        data ? (
          <>
            {data.total_lines.toLocaleString("en-IN")} order lines · net {fmt("inr", data.total_net)}. This total matches the Net sales figures above for the same period and filters.
          </>
        ) : undefined
      }
      action={
        <label className="flex items-center gap-2 text-xs text-muted">
          <span className="sr-only">Search transactions</span>
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search bill, SKU or product"
            className="w-56 rounded-lg border border-line bg-canvas px-3 py-1.5 text-sm text-fg"
          />
        </label>
      }
      className="scroll-mt-20"
    >
      <div id="transactions" className="-mt-2" />
      {error && <ErrorNote message={error} />}
      {!data && loading && <Skeleton className="h-64" />}
      {data && (
        <div className={loading ? "opacity-60" : ""}>
          {data.items.length === 0 ? (
            <EmptyNote>No transactions match these filters.</EmptyNote>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[760px] text-sm">
                  <thead>
                    <tr className="text-left font-mono text-[10px] uppercase tracking-[0.14em] text-muted">
                      <th className="pb-2 font-normal">Date</th>
                      <th className="pb-2 font-normal">Bill</th>
                      <th className="pb-2 font-normal">Product</th>
                      <th className="pb-2 text-right font-normal">Qty</th>
                      <th className="pb-2 text-right font-normal">Rate</th>
                      <th className="pb-2 text-right font-normal">Discount</th>
                      <th className="pb-2 text-right font-normal">Net</th>
                      <th className="pb-2 pl-3 font-normal">Customer</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.items.map((t, i) => (
                      <TxRow key={`${t.order_id}-${t.sku}-${i}`} t={t} />
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="mt-3 flex items-center justify-between text-xs text-muted">
                <span>
                  {offset + 1}–{Math.min(offset + PAGE, data.total_lines)} of {data.total_lines.toLocaleString("en-IN")}
                </span>
                <span className="flex gap-2">
                  <button type="button" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE))} className="rounded-full border border-line px-3 py-1 disabled:opacity-40">
                    ← Newer
                  </button>
                  <button type="button" disabled={offset + PAGE >= data.total_lines} onClick={() => setOffset(offset + PAGE)} className="rounded-full border border-line px-3 py-1 disabled:opacity-40">
                    Older →
                  </button>
                </span>
              </div>
            </>
          )}
        </div>
      )}
    </Card>
  );
}

function TxRow({ t }: { t: TransactionRow }) {
  return (
    <tr className="border-t border-line/70">
      <td className="py-2 pr-2 font-mono text-xs">{t.date}</td>
      <td className="py-2 pr-2 font-mono text-xs">{t.order_id}</td>
      <td className="py-2 pr-2">
        {t.product}
        <span className="ml-2 font-mono text-[10px] text-muted">{t.sku}</span>
      </td>
      <td className="py-2 text-right tabular">{fmt("count", t.quantity)}</td>
      <td className="py-2 text-right tabular">{fmt("inr", t.unit_price)}</td>
      <td className="py-2 text-right tabular text-muted">{num(t.discount) ? fmt("inr", t.discount) : "–"}</td>
      <td className="py-2 text-right font-medium tabular">{fmt("inr", t.net)}</td>
      <td className="py-2 pl-3 font-mono text-xs text-muted">{t.customer ?? "walk-in"}</td>
    </tr>
  );
}
