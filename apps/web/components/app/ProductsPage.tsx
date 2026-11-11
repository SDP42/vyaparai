"use client";

import { useState } from "react";
import { download } from "@/lib/api";
import { num, toSearch, useApi } from "@/lib/analytics";
import type { BasketResponse, ProductItem, ProductsResponse } from "@/lib/intelligence";
import { useAnalyticsState, useWorkspace } from "./AppContext";
import { PeriodBar } from "./analytics/PeriodBar";
import { Card, EmptyNote, ErrorNote, Notices, Skeleton, fmt } from "./analytics/parts";
import { Tx } from "./Tx";

const QUAD_TONE: Record<string, string> = {
  Star: "bg-mor/12 text-mor",
  Workhorse: "bg-haldi/25 text-fg",
  Puzzle: "bg-surface-2 text-fg",
  Dog: "bg-sindoor/10 text-sindoor",
  Unknown: "bg-surface-2 text-muted",
};
const FLAG_LABEL: Record<string, string> = {
  discount_heavy: "Heavy discounts",
  declining: "Declining",
  rising: "Rising",
  no_cost: "No cost",
};
const PAGE = 15;

export function ProductsPage() {
  const { workspace } = useWorkspace();
  const { query, dataVersion } = useAnalyticsState();
  const base = `/workspaces/${workspace.id}/analytics`;
  const [quadrant, setQuadrant] = useState("");
  const [abc, setAbc] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);

  const products = useApi<ProductsResponse>(`${base}/products?${toSearch(query)}`, [dataVersion]);
  const basket = useApi<BasketResponse>(`${base}/basket?${toSearch({ ...query, compare: "none" })}`, [dataVersion]);
  const d = products.data;

  const rows = (d?.items ?? []).filter(
    (i) =>
      (!quadrant || i.quadrant === quadrant) &&
      (!abc || i.abc === abc) &&
      (!search.trim() || `${i.name} ${i.key}`.toLowerCase().includes(search.trim().toLowerCase())),
  );
  const shown = rows.slice(page * PAGE, (page + 1) * PAGE);
  const pick = (fn: () => void) => {
    fn();
    setPage(0);
  };
  const input = "rounded-lg border border-line bg-surface px-2.5 py-1.5 text-sm";

  return (
    <div className="space-y-5">
      <header>
        <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-sindoor">{workspace.name}</p>
        <h1 className="mt-1 text-3xl font-bold tracking-tight sm:text-4xl"><Tx k="h.products" /></h1>
        <p className="mt-1 text-sm text-muted"><Tx k="i.products" /></p>
      </header>

      <PeriodBar showFilters />
      {products.error && <ErrorNote message={products.error} />}
      {!d && products.loading && <Skeleton className="h-96" />}

      {d && (
        <div className={`space-y-5 transition-opacity ${products.loading ? "opacity-60" : ""}`} aria-busy={products.loading}>
          <Notices warnings={d.warnings} />

          <div className="grid gap-5 xl:grid-cols-[1.4fr_1fr]">
            <Card title="Portfolio" subtitle="Popular = units at or above the median product. Profitable = margin at or above the overall margin.">
              <div className="grid grid-cols-2 gap-3">
                {d.portfolio.quadrants
                  .filter((q) => q.quadrant !== "Unknown" || q.products > 0)
                  .map((q) => (
                    <button
                      key={q.quadrant}
                      type="button"
                      aria-pressed={quadrant === q.quadrant}
                      onClick={() => pick(() => setQuadrant(quadrant === q.quadrant ? "" : q.quadrant))}
                      className={`rounded-xl border p-3 text-left transition-colors ${quadrant === q.quadrant ? "border-fg" : "border-line hover:border-fg/40"}`}
                    >
                      <span className={`rounded-full px-2 py-0.5 text-[11px] ${QUAD_TONE[q.quadrant]}`}>{q.quadrant}</span>
                      <p className="mt-2 text-2xl font-bold">{q.products}</p>
                      <p className="font-mono text-xs text-muted">{fmt("inr", q.net, { compact: true })}</p>
                      <p className="mt-1 text-xs text-muted">{q.help}</p>
                    </button>
                  ))}
              </div>
            </Card>

            <div className="space-y-5">
              <Card title="ABC classes" subtitle="A = products making the first 80% of sales, B = next 15%, C = the long tail.">
                <div className="flex gap-2">
                  {(["A", "B", "C"] as const).map((c) => (
                    <button
                      key={c}
                      type="button"
                      aria-pressed={abc === c}
                      onClick={() => pick(() => setAbc(abc === c ? "" : c))}
                      className={`flex-1 rounded-xl border p-3 text-center ${abc === c ? "border-fg" : "border-line hover:border-fg/40"}`}
                    >
                      <p className="font-mono text-xs text-muted">Class {c}</p>
                      <p className="text-2xl font-bold">{d.portfolio.abc[c] ?? 0}</p>
                    </button>
                  ))}
                </div>
              </Card>
              <Card title="Watch list">
                <ul className="space-y-1.5 text-sm">
                  <li>
                    <b>{d.portfolio.discount_heavy}</b> products rely on heavy discounts
                    <span className="text-muted"> (overall {fmt("percent", d.overall_discount_rate)})</span>
                  </li>
                  <li>
                    <b>{d.portfolio.declining}</b> products fell 20% or more vs the comparison period
                  </li>
                  <li>
                    <b>{d.portfolio.rising}</b> products grew 20% or more
                  </li>
                  <li className="text-muted">Overall gross margin {fmt("percent", d.overall_margin_pct)}</li>
                </ul>
              </Card>
            </div>
          </div>

          <Card title="Categories" subtitle="Sales, margin and discount depth by category.">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[34rem] text-sm">
                <thead>
                  <tr className="text-left font-mono text-[10px] uppercase tracking-wider text-muted">
                    <th className="py-2 pr-3">Category</th>
                    <th className="px-2 text-right">Products</th>
                    <th className="px-2 text-right">Net sales</th>
                    <th className="px-2 text-right">Share</th>
                    <th className="px-2 text-right">Margin</th>
                    <th className="px-2 text-right">Discount</th>
                    <th className="pl-2 text-right">Change</th>
                  </tr>
                </thead>
                <tbody>
                  {d.categories.map((c) => (
                    <tr key={c.category} className="border-t border-line">
                      <td className="py-2 pr-3 font-medium">{c.category}</td>
                      <td className="px-2 text-right font-mono">{c.products}</td>
                      <td className="px-2 text-right font-mono">{fmt("inr", c.net, { compact: true })}</td>
                      <td className="px-2 text-right font-mono">{fmt("percent", c.share)}</td>
                      <td className="px-2 text-right font-mono">{c.margin_pct ? fmt("percent", c.margin_pct) : "no cost"}</td>
                      <td className="px-2 text-right font-mono">{fmt("percent", c.discount_rate)}</td>
                      <td className="pl-2 text-right font-mono">{Change(c.change_pct)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          <Card
            title="All products"
            subtitle={`${rows.length} shown`}
            action={
              <button
                type="button"
                onClick={() => download(`${base}/products/export.csv?${toSearch(query)}`, "products.csv")}
                className="rounded-full border border-line px-3 py-1.5 text-xs hover:bg-surface-2"
              >
                Export CSV
              </button>
            }
          >
            <div className="mb-3 flex flex-wrap gap-2">
              <input value={search} onChange={(e) => pick(() => setSearch(e.target.value))} placeholder="Search product or SKU" aria-label="Search products" className={`${input} min-w-0 flex-1 sm:flex-none`} />
              {(quadrant || abc) && (
                <button type="button" onClick={() => pick(() => (setQuadrant(""), setAbc("")))} className="rounded-full border border-line px-3 text-xs">
                  Clear {[quadrant, abc && `class ${abc}`].filter(Boolean).join(" + ")} ✕
                </button>
              )}
            </div>
            {rows.length === 0 ? (
              <EmptyNote>No products match.</EmptyNote>
            ) : (
              <>
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[52rem] text-sm">
                    <thead>
                      <tr className="text-left font-mono text-[10px] uppercase tracking-wider text-muted">
                        <th className="py-2 pr-3">Product</th>
                        <th className="px-2">Class</th>
                        <th className="px-2 text-right">Units</th>
                        <th className="px-2 text-right">Net sales</th>
                        <th className="px-2 text-right">Margin</th>
                        <th className="px-2 text-right">Discount</th>
                        <th className="px-2 text-right">Change</th>
                        <th className="pl-2">Flags</th>
                      </tr>
                    </thead>
                    <tbody>
                      {shown.map((p) => (
                        <ProductRowView key={p.key} p={p} />
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="mt-3 flex items-center justify-between text-xs text-muted">
                  <span>
                    {page * PAGE + 1}–{Math.min((page + 1) * PAGE, rows.length)} of {rows.length}
                  </span>
                  <div className="flex gap-2">
                    <button type="button" disabled={page === 0} onClick={() => setPage(page - 1)} className="rounded-full border border-line px-3 py-1 disabled:opacity-40">
                      Previous
                    </button>
                    <button type="button" disabled={(page + 1) * PAGE >= rows.length} onClick={() => setPage(page + 1)} className="rounded-full border border-line px-3 py-1 disabled:opacity-40">
                      Next
                    </button>
                  </div>
                </div>
              </>
            )}
          </Card>

          <Card title="Bought together" subtitle="Pairs found in the same order. Lift above 1 means they appear together more often than chance.">
            {basket.error && <ErrorNote message={basket.error} />}
            {basket.data && basket.data.pairs.length === 0 && (
              <EmptyNote>No pair appears in at least {basket.data.min_orders} orders in this period.</EmptyNote>
            )}
            {basket.data && basket.data.pairs.length > 0 && (
              <>
                <p className="mb-2 text-xs text-muted">
                  {fmt("percent", basket.data.multi_item_share)} of {basket.data.orders} orders hold two or more products.
                </p>
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[34rem] text-sm">
                    <thead>
                      <tr className="text-left font-mono text-[10px] uppercase tracking-wider text-muted">
                        <th className="py-2 pr-3">Pair</th>
                        <th className="px-2 text-right">Orders</th>
                        <th className="px-2 text-right">Support</th>
                        <th className="px-2 text-right">A→B</th>
                        <th className="px-2 text-right">B→A</th>
                        <th className="pl-2 text-right">Lift</th>
                      </tr>
                    </thead>
                    <tbody>
                      {basket.data.pairs.map((x) => (
                        <tr key={`${x.a}-${x.b}`} className="border-t border-line">
                          <td className="py-2 pr-3">
                            {x.a_name} <span className="text-muted">+</span> {x.b_name}
                          </td>
                          <td className="px-2 text-right font-mono">{x.orders}</td>
                          <td className="px-2 text-right font-mono">{fmt("percent", x.support)}</td>
                          <td className="px-2 text-right font-mono">{fmt("percent", x.confidence_a_to_b)}</td>
                          <td className="px-2 text-right font-mono">{fmt("percent", x.confidence_b_to_a)}</td>
                          <td className="pl-2 text-right font-mono">{num(x.lift).toFixed(2)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p className="mt-3 text-xs text-muted">{basket.data.note}</p>
              </>
            )}
          </Card>
        </div>
      )}
    </div>
  );
}

function Change(v: string | null) {
  const n = num(v);
  if (!Number.isFinite(n)) return "–";
  return `${n > 0 ? "▲" : n < 0 ? "▼" : "■"} ${Math.abs(n).toFixed(1)}%`;
}

function ProductRowView({ p }: { p: ProductItem }) {
  return (
    <tr className="border-t border-line">
      <td className="py-2 pr-3">
        <span className="font-medium">{p.name}</span>
        <span className="block font-mono text-[11px] text-muted">
          {p.key}
          {p.category ? ` · ${p.category}` : ""}
        </span>
      </td>
      <td className="px-2">
        <span className={`rounded-full px-2 py-0.5 text-[11px] ${QUAD_TONE[p.quadrant]}`}>{p.quadrant}</span>
        <span className="ml-1 font-mono text-[11px] text-muted">{p.abc}</span>
      </td>
      <td className="px-2 text-right font-mono">{fmt("count", p.units)}</td>
      <td className="px-2 text-right font-mono">{fmt("inr", p.net, { compact: true })}</td>
      <td className="px-2 text-right font-mono">{p.margin_pct ? fmt("percent", p.margin_pct) : "–"}</td>
      <td className="px-2 text-right font-mono">{fmt("percent", p.discount_rate)}</td>
      <td className="px-2 text-right font-mono">{Change(p.change_pct)}</td>
      <td className="pl-2 text-xs">{p.flags.map((f) => FLAG_LABEL[f] ?? f).join(", ")}</td>
    </tr>
  );
}
