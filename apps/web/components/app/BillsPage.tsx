"use client";

import { useRef, useState } from "react";
import { ApiError, api } from "@/lib/api";
import { useApi } from "@/lib/analytics";
import { formatINR } from "@/lib/format";
import { useWorkspace } from "./AppContext";
import { Card, EmptyNote, ErrorNote, Skeleton } from "./analytics/parts";

type Line = { description: string; quantity: string; unit_price: string; amount: string; unit: string | null; confidence: "high" | "medium" | "low"; product_id: string | null };
type Bill = { id: string; status: "draft" | "confirmed"; supplier: string | null; gstin: string | null; bill_no: string | null; bill_date: string | null; total: string | null; engine: string; warnings: string[]; line_count: number; created_at: string; lines?: Line[] };
type Choice = { id: string; sku: string; name: string };
type Move = { product_id: string; sku: string; name: string; supplier: string | null; previous: string; latest: string; change_pct: number; previous_date: string; latest_date: string; list_price: string | null };
type Confirmed = { changes: { description: string; price: string; previous: string | null; change_pct: string | null }[]; unmatched: number };

const CONF = { high: "", medium: "bg-haldi/15", low: "bg-sindoor/10" } as const;
const n = (s: string) => Number(s.replace(/,/g, ""));

function Review({ id, base, onClose }: { id: string; base: string; onClose: () => void }) {
  const { data, error, loading } = useApi<Bill>(`${base}/${id}`, []);
  const choices = useApi<Choice[]>(`${base}/products`, []);
  const [edit, setEdit] = useState<Partial<Bill> | null>(null);
  const [lines, setLines] = useState<Line[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [done, setDone] = useState<Confirmed | null>(null);
  if (!data) return loading ? <Skeleton className="h-64" /> : error ? <ErrorNote message={error} /> : null;
  const b = { ...data, ...edit };
  const ls = lines ?? data.lines ?? [];
  const sum = ls.reduce((a, l) => a + n(l.amount), 0);
  const total = b.total ? n(b.total) : null;
  const setLine = (i: number, patch: Partial<Line>) => setLines(ls.map((l, j) => (j === i ? { ...l, ...patch, confidence: "high" } : l)));

  const save = async () => {
    await api(`${base}/${id}`, {
      method: "PUT",
      body: JSON.stringify({
        supplier: b.supplier, bill_no: b.bill_no, bill_date: b.bill_date || null, total: b.total || null,
        lines: ls.map((l) => ({ description: l.description, quantity: n(l.quantity), unit_price: n(l.unit_price), amount: n(l.amount), unit: l.unit, product_id: l.product_id })),
      }),
    });
  };
  const confirm = async () => {
    setBusy(true); setErr(null);
    try { await save(); setDone(await api<Confirmed>(`${base}/${id}/confirm`, { method: "POST" })); }
    catch (e) { setErr(e instanceof ApiError ? e.message : "Could not confirm"); }
    finally { setBusy(false); }
  };
  const discard = async () => {
    if (!window.confirm("Discard this draft?")) return;
    try { await api(`${base}/${id}`, { method: "DELETE" }); onClose(); } catch (e) { setErr(e instanceof ApiError ? e.message : "Could not discard"); }
  };

  if (done)
    return (
      <Card title="Bill confirmed" subtitle="Costs are updated for matched products.">
        <ul className="space-y-1.5 text-sm">
          {done.changes.map((c) => (
            <li key={c.description} className="flex flex-wrap justify-between gap-2">
              <span>{c.description}</span>
              <span className="text-muted">{formatINR(n(c.price))}{c.previous && <> (was {formatINR(n(c.previous))})</>}
                {c.change_pct && <b className={`ml-2 ${n(c.change_pct) > 0 ? "text-sindoor" : "text-mor"}`}>{n(c.change_pct) > 0 ? "▲" : "▼"} {Math.abs(n(c.change_pct))}%</b>}
              </span>
            </li>
          ))}
        </ul>
        {done.unmatched > 0 && <p className="mt-3 text-sm text-muted">{done.unmatched} lines were not matched to a product, so they changed no costs.</p>}
        <button type="button" onClick={onClose} className="mt-4 rounded-full bg-fg px-5 py-2 text-sm font-semibold text-canvas hover:bg-sindoor">Done</button>
      </Card>
    );

  const field = "mt-1 w-full rounded-lg border border-line bg-canvas px-3 py-2 text-sm";
  return (
    <Card title="Check what was read" subtitle={`Read with ${b.engine}. Fix anything wrong, match each line to a product, then confirm. Nothing changes until you confirm.`}>
      {b.warnings.map((w) => <p key={w} role="status" className="mb-2 rounded-lg bg-haldi/20 px-3 py-2 text-sm">{w}</p>)}
      {err && <ErrorNote message={err} />}
      <div className="grid gap-3 sm:grid-cols-4">
        <label className="text-xs text-muted sm:col-span-2">Supplier<input className={field} value={b.supplier ?? ""} onChange={(e) => setEdit({ ...edit, supplier: e.target.value })} /></label>
        <label className="text-xs text-muted">Bill no.<input className={field} value={b.bill_no ?? ""} onChange={(e) => setEdit({ ...edit, bill_no: e.target.value })} /></label>
        <label className="text-xs text-muted">Date<input type="date" className={field} value={b.bill_date ?? ""} onChange={(e) => setEdit({ ...edit, bill_date: e.target.value })} /></label>
      </div>
      <ul className="mt-4 space-y-3">
        {ls.map((l, i) => (
          <li key={i} className={`rounded-xl border border-line p-3 ${CONF[l.confidence]}`}>
            <div className="grid gap-2 sm:grid-cols-[2fr_1fr_1fr_1fr_auto]">
              <label className="text-xs text-muted">Item<input className={field} value={l.description} onChange={(e) => setLine(i, { description: e.target.value })} /></label>
              <label className="text-xs text-muted">Qty<input inputMode="decimal" className={field} value={l.quantity} onChange={(e) => setLine(i, { quantity: e.target.value, amount: String((n(e.target.value) * n(l.unit_price)).toFixed(2)) })} /></label>
              <label className="text-xs text-muted">Rate paid<input inputMode="decimal" className={field} value={l.unit_price} onChange={(e) => setLine(i, { unit_price: e.target.value, amount: String((n(l.quantity) * n(e.target.value)).toFixed(2)) })} /></label>
              <label className="text-xs text-muted">Amount<input inputMode="decimal" className={field} value={l.amount} onChange={(e) => setLine(i, { amount: e.target.value })} /></label>
              <button type="button" aria-label={`Remove ${l.description}`} onClick={() => setLines(ls.filter((_, j) => j !== i))} className="self-end rounded-lg px-3 py-2 text-sm text-sindoor hover:bg-sindoor/10">Remove</button>
            </div>
            <label className="mt-2 block text-xs text-muted">Product in your shop
              <select className={field} value={l.product_id ?? ""} onChange={(e) => setLine(i, { product_id: e.target.value || null })}>
                <option value="">Not matched (will not change any cost)</option>
                {choices.data?.map((c) => <option key={c.id} value={c.id}>{c.name} ({c.sku})</option>)}
              </select>
            </label>
            {l.confidence !== "high" && <p className="mt-1 text-xs text-muted">{l.confidence === "low" ? "The rate or quantity was guessed. Please check." : "Please check this line."}</p>}
          </li>
        ))}
      </ul>
      <button type="button" onClick={() => setLines([...ls, { description: "", quantity: "1", unit_price: "0", amount: "0", unit: null, confidence: "high", product_id: null }])} className="mt-3 rounded-full border border-line px-4 py-1.5 text-sm hover:bg-surface-2">+ Add a line</button>
      <p className="mt-4 text-sm">Lines add up to <b>{formatINR(sum)}</b>{total != null && <> · bill total <b>{formatINR(total)}</b>{Math.abs(sum - total) > Math.max(1, total * 0.05) && <span className="ml-2 text-sindoor">differs: a line may be missing</span>}</>}</p>
      <div className="mt-4 flex flex-wrap gap-2">
        <button type="button" disabled={busy || ls.length === 0} onClick={confirm} className="rounded-full bg-fg px-5 py-2 text-sm font-semibold text-canvas hover:bg-sindoor disabled:opacity-60">{busy ? "Saving…" : "Confirm bill"}</button>
        <button type="button" onClick={discard} className="rounded-full border border-line px-5 py-2 text-sm hover:bg-surface-2">Discard</button>
        <button type="button" onClick={onClose} className="rounded-full px-4 py-2 text-sm text-muted hover:text-fg">Close</button>
      </div>
    </Card>
  );
}

export function BillsPage() {
  const { workspace, canImport } = useWorkspace();
  const base = `/workspaces/${workspace.id}/bills`;
  const ref = useRef<HTMLInputElement>(null);
  const [version, setVersion] = useState(0);
  const [open, setOpen] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const list = useApi<Bill[]>(base, [version]);
  const moves = useApi<Move[]>(`${base}/prices/moves`, [version]);
  const engines = useApi<{ engines: string[] }>(`${base}/engines`, []);

  const upload = async (file: File) => {
    setBusy(true); setErr(null);
    const fd = new FormData(); fd.append("file", file);
    try { const b = await api<Bill>(base, { method: "POST", body: fd }); setVersion((v) => v + 1); setOpen(b.id); }
    catch (e) {
      setErr(e instanceof ApiError ? e.message : "Could not read the bill");
      if (e instanceof ApiError && e.status === 409) setVersion((v) => v + 1);
    } finally { setBusy(false); if (ref.current) ref.current.value = ""; }
  };

  return (
    <div className="space-y-6">
      <header>
        <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">Purchase bills</p>
        <h1 className="font-serif text-3xl tracking-tight sm:text-4xl">What you paid your suppliers</h1>
        <p className="mt-1 max-w-2xl text-sm text-fg/70">Take a photo of a bill or upload a PDF. We read the items and rates, you check them, and your costs and supplier price changes stay current without typing.</p>
      </header>

      {canImport && !open && (
        <Card title="Add a bill" subtitle="JPG, PNG, WebP or PDF, up to 10 MB. On a phone this opens the camera.">
          <input ref={ref} type="file" accept="image/*,application/pdf" className="hidden" onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])} />
          <button type="button" disabled={busy} onClick={() => ref.current?.click()} className="rounded-full bg-fg px-5 py-2.5 text-sm font-semibold text-canvas hover:bg-sindoor disabled:opacity-60">{busy ? "Reading the bill…" : "Photograph or upload a bill"}</button>
          {engines.data && engines.data.engines.length === 0 && <p className="mt-2 text-sm text-sindoor">No text reader is installed on this server, so only PDFs that contain text will work.</p>}
          {err && <p role="alert" className="mt-2 text-sm text-sindoor">{err}</p>}
        </Card>
      )}

      {open && <Review id={open} base={base} onClose={() => { setOpen(null); setVersion((v) => v + 1); }} />}

      {(moves.data?.length ?? 0) > 0 && (
        <section aria-label="Price changes" className="rounded-2xl border border-line bg-surface">
          <h2 className="border-b border-line px-5 py-3 font-semibold">Suppliers changed their price</h2>
          <ul className="divide-y divide-line">
            {moves.data?.map((m) => (
              <li key={m.product_id} className="flex flex-wrap items-center justify-between gap-2 px-5 py-3 text-sm">
                <span><b>{m.name}</b>{m.supplier && <span className="text-muted"> · {m.supplier}</span>}</span>
                <span>{formatINR(n(m.previous))} → <b>{formatINR(n(m.latest))}</b>
                  <b className={`ml-2 ${m.change_pct > 0 ? "text-sindoor" : "text-mor"}`}>{m.change_pct > 0 ? "▲" : "▼"} {Math.abs(m.change_pct)}%</b>
                  {m.list_price && m.change_pct > 0 && <span className="ml-2 text-xs text-muted">you sell at {formatINR(n(m.list_price))}</span>}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section aria-label="Bills" className="space-y-2">
        <h2 className="font-semibold">Your bills</h2>
        {list.error && <ErrorNote message={list.error} />}
        {!list.data && list.loading && <Skeleton className="h-24" />}
        {list.data?.length === 0 && <EmptyNote>No bills yet. Add one above.</EmptyNote>}
        <ul className="space-y-2">
          {list.data?.map((b) => (
            <li key={b.id} className="flex flex-wrap items-center justify-between gap-2 rounded-2xl border border-line bg-surface px-4 py-3 text-sm">
              <div className="min-w-0">
                <p className="truncate font-medium">{b.supplier ?? "Unknown supplier"} {b.bill_no && <span className="text-muted">#{b.bill_no}</span>}</p>
                <p className="text-xs text-muted">{b.bill_date ?? "no date"} · {b.line_count} lines{b.total && <> · {formatINR(n(b.total))}</>}</p>
              </div>
              <div className="flex items-center gap-2">
                <span className={`rounded-full px-2.5 py-0.5 text-xs ${b.status === "confirmed" ? "bg-mor/12 text-mor" : "bg-haldi/25"}`}>{b.status === "confirmed" ? "Confirmed" : "Needs checking"}</span>
                {b.status === "draft" && canImport && <button type="button" onClick={() => setOpen(b.id)} className="rounded-full border border-line px-3 py-1 text-xs hover:bg-surface-2">Review</button>}
              </div>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
