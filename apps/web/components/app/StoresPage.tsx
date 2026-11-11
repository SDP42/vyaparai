"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { ApiError, api } from "@/lib/api";
import { useApi } from "@/lib/analytics";
import { formatINR } from "@/lib/format";
import { useWorkspace } from "./AppContext";
import { Card, EmptyNote, ErrorNote, Skeleton } from "./analytics/parts";
import { Tx } from "./Tx";

type Store = { id: string; name: string; city?: string | null; role: string; has_data: boolean; from?: string; to?: string; latest_sale?: string; net_sales?: number; growth_pct?: number | null; orders?: number; aov?: number; margin_pct?: number | null; discount_rate?: number | null; urgent_stock?: number | null; udhaar_overdue?: number | null; high_alerts?: number; flags: string[] };
type Overview = { stores: Store[]; totals: { stores: number; net_sales: number; needs_attention: number; average_margin_pct: number | null }; notes: string[]; method: string };

const sign = (x: number | null | undefined, d = 1) => (x == null ? "–" : `${x >= 0 ? "+" : ""}${x.toFixed(d)}%`);

export function StoresPage() {
  const router = useRouter();
  const { workspace, switchTo, reload } = useWorkspace();
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [version, setVersion] = useState(0);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const q = from && to ? `?from=${from}&to=${to}` : "";
  const { data, error, loading } = useApi<Overview>(`/stores/overview${q}`, [version, from, to]);

  const add = async () => {
    setBusy(true); setErr(null);
    try { const ws = await api<{ id: string }>("/workspaces", { method: "POST", body: JSON.stringify({ name }) }); setName(""); await reload(); switchTo(ws.id); setVersion((v) => v + 1); router.push("/app/data"); }
    catch (e) { setErr(e instanceof ApiError ? e.message : "Could not add the store"); }
    finally { setBusy(false); }
  };
  const open = (id: string) => { switchTo(id); router.push("/app"); };
  const f = "mt-1 block rounded-lg border border-line bg-canvas px-3 py-2 text-sm";

  return (
    <div className="space-y-6">
      <header>
        <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">Stores</p>
        <h1 className="font-serif text-3xl tracking-tight sm:text-4xl"><Tx k="h.stores" /></h1>
        <p className="mt-1 max-w-2xl text-sm text-fg/70"><Tx k="i.stores" /></p>
      </header>
      {(error || err) && <ErrorNote message={(error ?? err) as string} />}
      {!data && loading && <Skeleton className="h-48" />}

      {data && (
        <>
          <section className="fluid [--min:11rem]" aria-label="Totals">
            {[["Shops", String(data.totals.stores)], ["Net sales, all shops", formatINR(data.totals.net_sales)], ["Need attention", String(data.totals.needs_attention)], ["Average margin", data.totals.average_margin_pct == null ? "–" : `${data.totals.average_margin_pct.toFixed(1)}%`]].map(([l, v]) => (
              <div key={l} className="rounded-2xl border border-line bg-surface p-4"><p className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted">{l}</p><p className="mt-1 text-2xl font-bold">{v}</p></div>
            ))}
          </section>
          <div className="flex flex-wrap items-end gap-3">
            <label className="text-xs text-muted">Same period for all: from<input type="date" className={f} value={from} onChange={(e) => setFrom(e.target.value)} /></label>
            <label className="text-xs text-muted">to<input type="date" className={f} value={to} onChange={(e) => setTo(e.target.value)} /></label>
            {(from || to) && <button type="button" onClick={() => { setFrom(""); setTo(""); }} className="rounded-full px-3 py-2 text-sm text-muted hover:text-fg">Reset</button>}
          </div>
          {data.notes.map((n) => <p key={n} role="status" className="rounded-lg bg-haldi/20 px-3 py-2 text-sm">{n}</p>)}
          <ul className="space-y-3">
            {data.stores.map((s) => (
              <li key={s.id} className={`rounded-2xl border bg-surface p-5 ${s.flags.length ? "border-sindoor/40" : "border-line"}`}>
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div><h2 className="text-lg font-semibold">{s.name}{s.id === workspace.id && <span className="ml-2 rounded-full bg-surface-2 px-2 py-0.5 text-[11px] font-normal text-muted">current</span>}</h2><p className="text-xs text-muted">{s.city ? `${s.city} · ` : ""}you are {s.role}{s.has_data ? ` · ${s.from} to ${s.to}` : ""}</p></div>
                  <button type="button" onClick={() => open(s.id)} className="rounded-full border border-line px-4 py-1.5 text-sm hover:bg-surface-2">Open →</button>
                </div>
                {s.has_data && (
                  <dl className="fluid mt-4 [--min:8rem]">
                    {[["Net sales", formatINR(s.net_sales ?? 0)], ["Growth", sign(s.growth_pct)], ["Orders", String(s.orders ?? 0)], ["Order value", formatINR(s.aov ?? 0)], ["Margin", s.margin_pct == null ? "–" : `${s.margin_pct.toFixed(1)}%`], ["Discount rate", s.discount_rate == null ? "–" : `${s.discount_rate.toFixed(1)}%`]].map(([l, v]) => (
                      <div key={l} className="rounded-xl bg-canvas px-3 py-2"><dt className="font-mono text-[10px] uppercase tracking-wider text-muted">{l}</dt><dd className={`text-base font-semibold ${l === "Growth" && (s.growth_pct ?? 0) < 0 ? "text-sindoor" : ""}`}>{v}</dd></div>
                    ))}
                  </dl>
                )}
                {s.flags.length > 0 && <ul className="mt-3 space-y-1 text-sm">{s.flags.map((f) => <li key={f} className="flex gap-2"><span aria-hidden className="text-sindoor">▲</span>{f}</li>)}</ul>}
              </li>
            ))}
          </ul>
          <p className="rounded-xl bg-surface-2 p-4 text-xs text-muted">{data.method}</p>
        </>
      )}

      {data && data.stores.length === 0 && <EmptyNote>No shops yet.</EmptyNote>}
      <Card title="Add a shop" subtitle="It gets its own data, team and settings. Import its sales on the Data page.">
        <div className="flex flex-wrap items-end gap-3">
          <label className="min-w-0 flex-1 text-xs text-muted">Shop name<input className={`${f} w-full`} value={name} maxLength={120} onChange={(e) => setName(e.target.value)} /></label>
          <button type="button" disabled={busy || name.trim().length < 2} onClick={add} className="rounded-full bg-fg px-5 py-2.5 text-sm font-semibold text-canvas hover:bg-sindoor disabled:opacity-50">{busy ? "Adding…" : "Add shop"}</button>
        </div>
      </Card>
    </div>
  );
}
