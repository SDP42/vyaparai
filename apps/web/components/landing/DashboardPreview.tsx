import { KPIS, TOP_PRODUCTS, salesSeries } from "@/lib/demo-data";
import { formatINR, formatINRCompact, formatNumber, formatPct } from "@/lib/format";
import { SalesChart } from "@/components/app/SalesChart";

export function KpiValue({ value, format }: { value: number; format: "inr" | "pct" | "num" }) {
  if (format === "inr") return <>{value > 99999 ? formatINRCompact(value) : formatINR(value)}</>;
  if (format === "pct") return <>{value.toFixed(1)}%</>;
  return <>{formatNumber(value)}</>;
}

/** Static product preview used on the landing page (no interactivity, aria-hidden chart). */
export function DashboardPreview() {
  const series = salesSeries();
  return (
    <div className="@container">
    <div className="grid gap-4 p-4 @2xl:grid-cols-[170px_1fr] @2xl:p-6">
      <aside className="hidden flex-col gap-1 border-r border-line pr-4 @2xl:flex">
        {["Overview", "Sales", "Customers", "Inventory", "Forecasts", "Copilot"].map((x, i) => (
          <span key={x} className={`rounded-lg px-3 py-2 text-sm ${i === 0 ? "bg-surface-2 text-fg" : "text-fg/50"}`}>
            {x}
          </span>
        ))}
      </aside>
      <div className="min-w-0 space-y-4">
        <div className="grid grid-cols-2 gap-3 @4xl:grid-cols-4">
          {KPIS.map((k) => (
            <div key={k.key} className="min-w-0 rounded-xl border border-line bg-canvas p-3 @lg:p-4">
              <p className="truncate text-xs text-muted">{k.label}</p>
              <p className="mt-1 whitespace-nowrap text-xl font-bold tabular @lg:text-2xl">
                <KpiValue value={k.value} format={k.format} />
              </p>
              <p className={`mt-1 truncate font-mono text-[11px] ${k.delta >= 0 ? "text-mor" : "text-sindoor"}`}>
                {k.delta >= 0 ? "▲" : "▼"} {formatPct(k.delta)} <span className="text-muted">vs prev. 30d</span>
              </p>
            </div>
          ))}
        </div>
        <div className="grid gap-3 @3xl:grid-cols-[1.6fr_1fr]">
          <div className="rounded-xl border border-line bg-canvas p-4">
            <div className="mb-2 flex items-baseline justify-between">
              <p className="text-sm font-semibold">Daily net sales</p>
              <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted">actual · forecast</p>
            </div>
            <SalesChart data={series} compact />
          </div>
          <div className="rounded-xl border border-line bg-canvas p-4">
            <p className="mb-2 text-sm font-semibold">Top products</p>
            <ul className="divide-y divide-line/70">
              {TOP_PRODUCTS.slice(0, 4).map((p) => (
                <li key={p.sku} className="flex items-center justify-between py-2 text-sm">
                  <span className="truncate pr-2 text-fg/80">{p.name}</span>
                  <span className="shrink-0 tabular">{formatINRCompact(p.revenue)}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
    </div>
  );
}
