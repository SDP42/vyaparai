"use client";

import { toSearch, useApi } from "@/lib/analytics";
import { useAnalyticsState, useWorkspace } from "./AppContext";
import { PeriodBar } from "./analytics/PeriodBar";
import { Card, EmptyNote, ErrorNote, Skeleton, fmt } from "./analytics/parts";
import { Tx } from "./Tx";

type Row = {
  staff: string;
  orders: number;
  units: string;
  net: string;
  avg_bill: string | null;
  items_per_bill: string | null;
  discount_rate: string | null;
  margin_pct: string | null;
  share: string | null;
};
type Staff = { has_staff: boolean; rows: Row[]; own_only: boolean; needs_link: boolean; note: string | null };

/** Sales by the person on the bill. Counter staff see only their own row. */
export function StaffPage() {
  const { workspace } = useWorkspace();
  const { query, dataVersion } = useAnalyticsState();
  const { data, loading, error } = useApi<Staff>(
    `/workspaces/${workspace.id}/analytics/staff?${toSearch({ ...query, compare: "none" })}`,
    [dataVersion],
  );
  const showMargin = data?.rows.some((r) => r.margin_pct !== null) ?? false;
  const top = Math.max(1, ...(data?.rows ?? []).map((r) => Number(r.net)));

  return (
    <div className="space-y-5">
      <header>
        <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-sindoor">{workspace.name}</p>
        <h1 className="mt-1 text-3xl font-bold tracking-tight sm:text-4xl"><Tx k="h.staff" /></h1>
        <p className="mt-1 max-w-2xl text-sm text-muted"><Tx k="i.staff" /></p>
      </header>
      <PeriodBar />
      {error && <ErrorNote message={error} />}
      {loading && !data && <Skeleton className="h-48" />}
      {data?.needs_link && <EmptyNote>{data.note}</EmptyNote>}
      {data && !data.needs_link && !data.has_staff && <EmptyNote>{data.note}</EmptyNote>}
      {data && data.rows.length > 0 && (data.has_staff || data.own_only) && (
        <Card title={data.own_only ? "Your bills" : "By person"}>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[560px] text-sm">
              <caption className="sr-only">Sales by person on the bill</caption>
              <thead>
                <tr className="border-b border-line text-left font-mono text-[10px] uppercase tracking-[0.14em] text-muted">
                  <th scope="col" className="py-2 pr-3 font-normal">Person</th>
                  <th scope="col" className="px-3 py-2 text-right font-normal">Bills</th>
                  <th scope="col" className="px-3 py-2 text-right font-normal">Net sales</th>
                  <th scope="col" className="px-3 py-2 text-right font-normal">Average bill</th>
                  <th scope="col" className="px-3 py-2 text-right font-normal">Items per bill</th>
                  <th scope="col" className="px-3 py-2 text-right font-normal">Discount</th>
                  {showMargin && <th scope="col" className="px-3 py-2 text-right font-normal">Margin</th>}
                </tr>
              </thead>
              <tbody>
                {data.rows.map((r) => (
                  <tr key={r.staff} className="border-b border-line/70 last:border-0">
                    <th scope="row" className="py-2.5 pr-3 text-left font-medium">
                      {r.staff === "Unspecified" ? <span className="text-muted">No name on the bill</span> : r.staff}
                      <span aria-hidden className="mt-1 block h-1 rounded-full bg-surface-2"><span className="block h-full rounded-full bg-fg/50" style={{ width: `${(Number(r.net) / top) * 100}%` }} /></span>
                    </th>
                    <td className="px-3 py-2.5 text-right tabular">{fmt("count", r.orders)}</td>
                    <td className="px-3 py-2.5 text-right tabular">{fmt("inr", r.net)}{r.share !== null && !data.own_only && <span className="block text-[11px] text-muted">{Number(r.share).toFixed(0)}%</span>}</td>
                    <td className="px-3 py-2.5 text-right tabular">{fmt("inr", r.avg_bill)}</td>
                    <td className="px-3 py-2.5 text-right tabular">{r.items_per_bill !== null ? Number(r.items_per_bill).toFixed(1) : "–"}</td>
                    <td className="px-3 py-2.5 text-right tabular">{fmt("percent", r.discount_rate)}</td>
                    {showMargin && <td className="px-3 py-2.5 text-right tabular">{fmt("percent", r.margin_pct)}</td>}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-xs text-muted">The name is whatever the billing software wrote. Compare people on average bill and items per bill, not only on total sales, since shifts and counters differ.</p>
        </Card>
      )}
    </div>
  );
}
