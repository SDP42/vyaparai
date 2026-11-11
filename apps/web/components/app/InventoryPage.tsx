"use client";

import { Fragment, useRef, useState } from "react";
import { ApiError, api, download } from "@/lib/api";
import { longDate, num, useApi } from "@/lib/analytics";
import type { ImportResult, InventoryItem, InventoryOverview, StockStatus } from "@/lib/inventory";
import { formatINR, formatNumber } from "@/lib/format";
import { useWorkspace } from "./AppContext";
import { Card, EmptyNote, ErrorNote, Skeleton } from "./analytics/parts";
import { Tx } from "./Tx";

const STATUS: Record<StockStatus, { label: string; tone: string }> = {
  urgent: { label: "Order now", tone: "bg-sindoor/10 text-sindoor" },
  reorder: { label: "Order soon", tone: "bg-haldi/25 text-fg" },
  ok: { label: "Fine", tone: "bg-mor/12 text-mor" },
  overstock: { label: "Too much", tone: "bg-surface-2 text-fg" },
  dead: { label: "Not selling", tone: "bg-surface-2 text-muted" },
};
const FILTERS: (StockStatus | "all")[] = ["all", "urgent", "reorder", "overstock", "dead", "ok"];
const SERVICE = [
  { v: 0, label: "Lean", hint: "Cheapest, more risk of running out" },
  { v: 0.5, label: "Balanced", hint: "A sensible middle" },
  { v: 1, label: "Cautious", hint: "Safest, ties up more cash" },
];

export function InventoryPage() {
  const { workspace, canImport } = useWorkspace();
  const base = `/workspaces/${workspace.id}/inventory`;
  const [service, setService] = useState(0.5);
  const [review, setReview] = useState(7);
  const [version, setVersion] = useState(0);
  const [filter, setFilter] = useState<StockStatus | "all">("all");
  const [open, setOpen] = useState<string | null>(null);
  const { data, error, loading } = useApi<InventoryOverview>(`${base}/overview?service=${service}&review_days=${review}`, [version]);
  const items = (data?.items ?? []).filter((i) => filter === "all" || i.status === filter);
  const s = data?.summary;
  const refresh = () => setVersion((v) => v + 1);
  const qs = `service=${service}&review_days=${review}`;

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-sindoor">{workspace.name}</p>
          <h1 className="mt-1 text-3xl font-bold tracking-tight sm:text-4xl"><Tx k="h.stock" /></h1>
          <p className="mt-1 max-w-2xl text-sm text-muted"><Tx k="i.stock" /></p>
        </div>
        {canImport && s && s.tracked > 0 && (
          <button type="button" onClick={() => download(`${base}/order-list.csv?${qs}`, "order-list.csv")} className="rounded-full bg-fg px-5 py-2.5 text-sm font-semibold text-canvas hover:bg-sindoor">
            Download order list
          </button>
        )}
      </header>

      {error && <ErrorNote message={error} />}
      {canImport && <ImportCard base={base} onDone={refresh} />}
      {!data && loading && <Skeleton className="h-72" />}

      {s && s.tracked === 0 && !loading && <EmptyNote>No stock recorded yet. Upload a stock file above, or set stock for a product by hand once it appears here.</EmptyNote>}

      {data && s && s.tracked > 0 && (
        <>
          {!data.has_forecast && <p className="rounded-2xl border border-haldi/40 bg-haldi/10 px-4 py-3 text-sm">No forecast yet, so cover uses each product&apos;s sales over the last 4 weeks. Build a forecast on the Forecasts page for better advice.</p>}
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Tile hero label="Order now" value={String(s.urgent)} hint={`${s.reorder} more soon`} />
            <Tile label="Order bill (est.)" value={formatINR(num(s.order_cost))} hint="for the suggested quantities" />
            <Tile label="Cash on the shelf" value={formatINR(num(s.cash_tied))} hint={`${formatINR(num(s.excess_cash))} is more than needed`} />
            <Tile label="Not selling" value={formatINR(num(s.dead_cash))} hint={`${s.dead} products, nothing sold in 30 days`} />
          </div>
          {s.missing_stock > 0 && <p className="text-xs text-muted">{s.missing_stock} products that sold in the last 4 weeks have no stock recorded, so they are not planned here.</p>}

          <Card
            title="Products"
            subtitle={data.as_of ? `Stock today = last count minus sales since. Sales known to ${longDate(data.as_of)}.` : undefined}
            action={
              <div className="flex flex-wrap items-center gap-2 text-xs">
                <div role="group" aria-label="Safety level" className="flex gap-1 rounded-full border border-line bg-canvas p-0.5">
                  {SERVICE.map((o) => (
                    <button key={o.v} type="button" title={o.hint} aria-pressed={service === o.v} onClick={() => setService(o.v)} className={`rounded-full px-3 py-1 ${service === o.v ? "bg-fg text-canvas" : "text-fg/65 hover:text-fg"}`}>
                      {o.label}
                    </button>
                  ))}
                </div>
                <label className="flex items-center gap-1.5 text-muted">
                  Order every
                  <select value={review} onChange={(e) => setReview(Number(e.target.value))} className="rounded-lg border border-line bg-surface px-2 py-1 text-fg">
                    {[3, 7, 10, 14, 21].map((d) => (
                      <option key={d} value={d}>
                        {d} days
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            }
          >
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
                <table className="w-full min-w-[44rem] text-sm">
                  <thead>
                    <tr className="text-left font-mono text-[10px] uppercase tracking-wider text-muted">
                      <th className="py-2 pr-3">Product</th>
                      <th className="px-2 text-right">On hand</th>
                      <th className="w-40 px-2">Lasts</th>
                      <th className="px-2 text-right">Order</th>
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
                            <span className="block font-mono text-[11px] text-muted">{i.sku} · about {num(i.daily_rate)}/day</span>
                          </td>
                          <td className="px-2 text-right font-mono">
                            {formatNumber(Math.round(num(i.on_hand)))}
                            {num(i.sold_since) > 0 && <span className="block text-[11px] text-muted">counted {formatNumber(Math.round(num(i.snapshot_on_hand)))} on {longDate(i.snapshot_date)}</span>}
                          </td>
                          <td className="px-2">
                            <CoverBar days={i.cover_days == null ? null : num(i.cover_days)} lead={i.lead_time_days} status={i.status} />
                          </td>
                          <td className="px-2 text-right font-mono">{num(i.order_qty) > 0 ? <>{formatNumber(Math.round(num(i.order_qty)))}{i.order_cost && <span className="block text-[11px] text-muted">{formatINR(num(i.order_cost))}</span>}</> : "–"}</td>
                          <td className="pl-2">
                            <span className={`rounded-full px-2 py-0.5 text-[11px] ${STATUS[i.status].tone}`}>{STATUS[i.status].label}</span>
                          </td>
                        </tr>
                        {open === i.sku && (
                          <tr className="bg-canvas">
                            <td colSpan={5} className="p-4">
                              <Editor base={base} item={i} canEdit={canImport} onSaved={refresh} />
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
          <p className="text-xs text-muted">The order quantity covers the delivery time plus the days between orders, at a demand level between the likely and the high forecast (set by the safety level), rounded up to whole packs. These are suggestions: check them against your supplier&apos;s minimums and what is already on its way.</p>
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

/** Days of cover as a bar, with a marker where a new order would arrive. */
function CoverBar({ days, lead, status }: { days: number | null; lead: number; status: StockStatus }) {
  const cap = 30;
  const d = days == null ? cap : Math.min(days, cap);
  const color = status === "urgent" ? "bg-sindoor" : status === "reorder" ? "bg-haldi" : status === "ok" ? "bg-mor" : "bg-line";
  return (
    <div title={days == null ? "No demand expected" : `${days.toFixed(1)} days of stock; delivery takes ${lead} days`}>
      <div className="relative h-2 rounded-full bg-surface-2">
        <div className={`absolute inset-y-0 left-0 rounded-full ${color}`} style={{ width: `${(d / cap) * 100}%` }} />
        <div className="absolute -top-0.5 h-3 w-0.5 bg-fg" style={{ left: `${Math.min(100, (lead / cap) * 100)}%` }} />
      </div>
      <p className="mt-0.5 text-[11px] text-muted">{days == null ? "no demand" : days > 60 ? "60+ days" : `${days.toFixed(0)} days`}</p>
    </div>
  );
}

function Editor({ base, item, canEdit, onSaved }: { base: string; item: InventoryItem; canEdit: boolean; onSaved: () => void }) {
  const [stock, setStock] = useState("");
  const [lead, setLead] = useState(String(item.lead_time_days));
  const [pack, setPack] = useState(String(num(item.pack_size)));
  const [msg, setMsg] = useState<string | null>(null);
  const save = async () => {
    setMsg(null);
    const body: Record<string, number> = { lead_time_days: Number(lead), pack_size: Number(pack) };
    if (stock.trim() !== "") body.on_hand = Number(stock);
    try {
      await api(`${base}/items/${encodeURIComponent(item.sku)}`, { method: "PUT", body: JSON.stringify(body) });
      setStock("");
      onSaved();
      setMsg("Saved.");
    } catch (e) {
      setMsg(e instanceof ApiError ? "Check the numbers (stock 0 or more, lead time 0 to 90 days, pack size above 0)." : "Could not save");
    }
  };
  const input = "w-full rounded-lg border border-line bg-surface px-2.5 py-1.5 text-sm disabled:opacity-60";
  return (
    <div className="grid gap-4 md:grid-cols-[1.2fr_1fr]">
      <div className="text-sm">
        <p>{item.reason}</p>
        {item.run_out_date && <p className="mt-1 text-xs text-muted">Expected to run out around {longDate(item.run_out_date)}.</p>}
        {!item.forecast_based && <p className="mt-1 text-xs text-muted">Based on recent sales: no forecast for this product yet.</p>}
        {item.cash_tied && <p className="mt-1 text-xs text-muted">About {formatINR(num(item.cash_tied))} of stock at cost on the shelf.</p>}
      </div>
      <div className="grid grid-cols-3 gap-2 text-xs text-muted">
        <label>
          Count today
          <input className={`${input} mt-1`} disabled={!canEdit} inputMode="decimal" value={stock} onChange={(e) => setStock(e.target.value)} placeholder="units" />
        </label>
        <label>
          Delivery days
          <input className={`${input} mt-1`} disabled={!canEdit} inputMode="numeric" value={lead} onChange={(e) => setLead(e.target.value)} />
        </label>
        <label>
          Pack size
          <input className={`${input} mt-1`} disabled={!canEdit} inputMode="decimal" value={pack} onChange={(e) => setPack(e.target.value)} />
        </label>
        {canEdit && (
          <div className="col-span-3 flex items-center gap-3">
            <button type="button" onClick={save} className="rounded-full bg-fg px-4 py-1.5 text-xs font-semibold text-canvas hover:bg-sindoor">
              Save
            </button>
            {msg && <span className="text-xs">{msg}</span>}
          </div>
        )}
      </div>
    </div>
  );
}

function ImportCard({ base, onDone }: { base: string; onDone: () => void }) {
  const ref = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [res, setRes] = useState<ImportResult | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const upload = async (file: File) => {
    setBusy(true);
    setErr(null);
    setRes(null);
    const fd = new FormData();
    fd.append("file", file);
    try {
      setRes(await api<ImportResult>(`${base}/import`, { method: "POST", body: fd }));
      onDone();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "Could not read the file");
    } finally {
      setBusy(false);
      if (ref.current) ref.current.value = "";
    }
  };
  return (
    <Card title="Update your stock" subtitle="A CSV with a product code (SKU) and the stock you counted. Optional columns: Date, Lead time days, Pack size.">
      <div className="flex flex-wrap items-center gap-2">
        <input ref={ref} type="file" accept=".csv,text/csv" className="hidden" onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])} />
        <button type="button" disabled={busy} onClick={() => ref.current?.click()} className="rounded-full bg-fg px-4 py-2 text-sm font-semibold text-canvas hover:bg-sindoor disabled:opacity-60">
          {busy ? "Reading…" : "Upload stock file"}
        </button>
        <button type="button" onClick={() => download(`${base}/template.csv`, "stock-template.csv")} className="rounded-full border border-line px-4 py-2 text-sm hover:bg-surface-2">
          Download a template with your products
        </button>
      </div>
      {err && <p className="mt-2 text-sm text-sindoor">{err}</p>}
      {res && (
        <div className="mt-3 text-sm" role="status">
          <p>
            <b>{res.imported}</b> products updated.
            {res.unmatched > 0 && <> {res.unmatched} codes did not match a product ({res.unmatched_skus.slice(0, 5).join(", ")}{res.unmatched > 5 ? ", …" : ""}).</>}
            {res.rejected_count > 0 && <> {res.rejected_count} rows were skipped: {res.rejected.slice(0, 2).map((r) => `row ${r.row} ${r.reason.toLowerCase()}`).join("; ")}.</>}
          </p>
        </div>
      )}
    </Card>
  );
}
