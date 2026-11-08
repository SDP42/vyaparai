"use client";

import Link from "next/link";
import { motion } from "motion/react";
import { longDate, num, toSearch, useApi, type Insight, type Kpi, type Overview, type ProductRow } from "@/lib/analytics";
import { useAnalyticsState, useWorkspace } from "./AppContext";
import { MixList } from "./analytics/MixList";
import { PeriodBar } from "./analytics/PeriodBar";
import { TrendChart } from "./analytics/TrendChart";
import { Card, DeltaChip, EmptyNote, ErrorNote, MetricInfo, Notices, Skeleton, ToneDot, fmt, signed } from "./analytics/parts";

const EASE = [0.16, 1, 0.3, 1] as const;

export function CommandCenter() {
  const { workspace } = useWorkspace();
  const { query, dataVersion, options } = useAnalyticsState();
  const path = `/workspaces/${workspace.id}/analytics/overview?${toSearch(query)}`;
  const { data, error, loading } = useApi<Overview>(path, [dataVersion]);

  return (
    <div className="space-y-5">
      <header>
        <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-sindoor">{workspace.name}</p>
        <h1 className="mt-1 text-3xl font-bold tracking-tight sm:text-4xl">Command center</h1>
        {data?.meta.freshness.last_order_date && (
          <p className="mt-1 text-sm text-muted">
            Sales through {longDate(data.meta.freshness.last_order_date)}
            {data.meta.freshness.last_import_at && <> · last import {new Date(data.meta.freshness.last_import_at).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}</>}
          </p>
        )}
      </header>

      <PeriodBar />

      {error && <ErrorNote message={error} />}
      {options && !options.has_data && !loading && <NoData />}
      {data && (
        <div className={`space-y-5 transition-opacity ${loading ? "opacity-60" : "opacity-100"}`} aria-busy={loading}>
          <Notices warnings={data.warnings} />
          <KpiGrid items={data.headline} compareLabel={data.meta.compare?.label ?? null} />

          <div className="grid gap-5 xl:grid-cols-[1.7fr_1fr]">
            <Card
              title="Net sales"
              subtitle={`${data.meta.period.days} days · by ${data.meta.granularity}${data.meta.compare ? ` · compared with ${data.meta.compare.label} (${longDate(data.meta.compare.date_from)} → ${longDate(data.meta.compare.date_to)})` : ""}`}
            >
              <TrendChart points={data.trend} compareLabel={data.meta.compare ? "Comparison" : null} />
            </Card>
            <Insights items={data.insights} />
          </div>

          <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
            <Card title="By category" subtitle="Share of net sales and change">
              <MixList rows={data.category_mix} />
            </Card>
            <Card title="By channel">
              <MixList rows={data.channel_mix} emptyText="No channel recorded in your data." />
            </Card>
            <Card title="Busiest weekdays" subtitle="Average net sales per day">
              <Weekdays rows={data.weekday} />
            </Card>
          </div>

          <div className="grid gap-5 xl:grid-cols-[1.5fr_1fr]">
            <Card title="Top products" action={<Link href="/app/sales" className="text-xs text-sindoor underline underline-offset-4">Explore sales →</Link>}>
              <ProductTable rows={data.top_products} compare={!!data.meta.compare} />
            </Card>
            <Card title="Lowest sellers" subtitle="Products with sales in this period">
              <ProductTable rows={data.bottom_products} compare={false} compact />
            </Card>
          </div>

          <SecondaryStrip items={data.secondary} />
        </div>
      )}
      {!data && loading && <LoadingGrid />}
    </div>
  );
}

function NoData() {
  return (
    <div className="rounded-3xl border border-dashed border-line bg-surface p-10 text-center">
      <h2 className="text-xl font-bold">No sales data yet</h2>
      <p className="mx-auto mt-2 max-w-md text-sm text-muted">Import a CSV or Excel export from your billing software and this page fills in. The sample file has 90 days of a general store.</p>
      <Link href="/app/data" className="mt-5 inline-block rounded-full bg-fg px-6 py-3 text-sm font-semibold text-canvas hover:bg-sindoor">
        Import sales data
      </Link>
    </div>
  );
}

function LoadingGrid() {
  return (
    <div className="space-y-5" aria-busy="true" aria-label="Loading">
      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-28" />
        ))}
      </div>
      <Skeleton className="h-80" />
    </div>
  );
}

function KpiGrid({ items, compareLabel }: { items: Kpi[]; compareLabel: string | null }) {
  return (
    <section aria-label="Key metrics" className="grid grid-cols-2 gap-3 xl:grid-cols-4">
      {items.map((k, i) => (
        <motion.article
          key={k.key}
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.05, duration: 0.5, ease: EASE }}
          className="rounded-2xl border border-line bg-surface p-4 sm:p-5"
        >
          <p className="flex items-center gap-1.5 text-xs text-muted">
            {k.label} <MetricInfo metricKey={k.key} />
          </p>
          <p className="mt-2 text-2xl font-bold tabular tracking-tight sm:text-3xl">{fmt(k.unit, k.value)}</p>
          <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1">
            <DeltaChip kpi={k} />
            {compareLabel && k.previous != null && <span className="font-mono text-[10px] text-muted">was {fmt(k.unit, k.previous, { compact: true })}</span>}
          </div>
        </motion.article>
      ))}
    </section>
  );
}

function SecondaryStrip({ items }: { items: Kpi[] }) {
  return (
    <section aria-label="More metrics" className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-5">
      {items.map((k) => (
        <div key={k.key} className="rounded-xl border border-line bg-surface px-4 py-3">
          <p className="flex items-center gap-1.5 text-[11px] text-muted">
            {k.label} <MetricInfo metricKey={k.key} />
          </p>
          <p className="mt-1 font-semibold tabular">{fmt(k.unit, k.value)}</p>
          <div className="mt-1">
            <DeltaChip kpi={k} />
          </div>
        </div>
      ))}
    </section>
  );
}

function Insights({ items }: { items: Insight[] }) {
  return (
    <Card title="What changed" subtitle="Rule-based, from your numbers. Attributions, not proven causes.">
      {items.length === 0 ? (
        <EmptyNote>Nothing notable yet.</EmptyNote>
      ) : (
        <ul className="space-y-3">
          {items.map((i) => (
            <li key={i.id} className="flex gap-3">
              <ToneDot tone={i.tone} />
              <div className="min-w-0">
                <p className="text-sm font-semibold leading-snug">{i.title}</p>
                <p className="mt-0.5 text-xs leading-relaxed text-muted">{i.body}</p>
                <p className="mt-1 font-mono text-[10px] text-muted/80">{i.evidence.join(" · ")}</p>
              </div>
            </li>
          ))}
        </ul>
      )}
      <Link href="/app/sales" className="mt-4 inline-block text-xs text-sindoor underline underline-offset-4">
        See the full breakdown →
      </Link>
    </Card>
  );
}

function Weekdays({ rows }: { rows: Overview["weekday"] }) {
  const max = Math.max(...rows.map((r) => num(r.avg_net)), 1);
  return (
    <ul className="space-y-2" aria-label="Average net sales by weekday">
      {rows.map((r) => (
        <li key={r.weekday} className="flex items-center gap-3 text-sm">
          <span className="w-9 font-mono text-xs text-muted">{r.label}</span>
          <div className="h-2 flex-1 overflow-hidden rounded-full bg-surface-2" aria-hidden>
            <div className="h-full rounded-full bg-fg/80" style={{ width: `${(num(r.avg_net) / max) * 100}%` }} />
          </div>
          <span className="w-20 text-right tabular">{fmt("inr", r.avg_net, { compact: true })}</span>
        </li>
      ))}
    </ul>
  );
}

function ProductTable({ rows, compare, compact = false }: { rows: ProductRow[]; compare: boolean; compact?: boolean }) {
  if (rows.length === 0) return <EmptyNote>No products sold in this period.</EmptyNote>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left font-mono text-[10px] uppercase tracking-[0.14em] text-muted">
            <th className="pb-2 font-normal">Product</th>
            {!compact && <th className="pb-2 text-right font-normal">Units</th>}
            <th className="pb-2 text-right font-normal">Net sales</th>
            {compare && <th className="pb-2 text-right font-normal">Change</th>}
          </tr>
        </thead>
        <tbody>
          {rows.map((p) => {
            const d = p.delta == null ? null : num(p.delta);
            return (
              <tr key={p.sku} className="border-t border-line/70">
                <td className="py-2 pr-2">
                  <span className="font-medium">{p.name}</span>
                  <span className="ml-2 font-mono text-[10px] text-muted">{p.sku}</span>
                </td>
                {!compact && <td className="py-2 text-right tabular">{fmt("count", p.units)}</td>}
                <td className="py-2 text-right tabular">{fmt("inr", p.net)}</td>
                {compare && (
                  <td className={`py-2 text-right font-mono text-xs ${d == null || d === 0 ? "text-muted" : d > 0 ? "text-mor" : "text-sindoor"}`}>
                    {d == null ? "–" : (
                      <>
                        <span aria-hidden>{d > 0 ? "▲ " : d < 0 ? "▼ " : ""}</span>
                        {signed("inr", d, { compact: true })}
                      </>
                    )}
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
