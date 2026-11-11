"use client";

import { useState } from "react";
import { ApiError, api, download } from "@/lib/api";
import { useApi } from "@/lib/analytics";
import { parseUtc } from "@/lib/format";
import { useWorkspace } from "./AppContext";
import { Card, EmptyNote, ErrorNote, Skeleton } from "./analytics/parts";
import { Tx } from "./Tx";

type Meta = { id: string; title: string; from: string; to: string; created_at: string };
const iso = (d: Date) => d.toISOString().slice(0, 10);

export function ReportsPage() {
  const { workspace, canImport } = useWorkspace();
  const base = `/workspaces/${workspace.id}/reports`;
  const today = new Date();
  const [from, setFrom] = useState(iso(new Date(today.getTime() - 29 * 86400000)));
  const [to, setTo] = useState(iso(today));
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [version, setVersion] = useState(0);
  const list = useApi<Meta[]>(base, [version]);
  const can = ["owner", "admin"].includes(workspace.role);

  const make = async () => {
    setBusy(true); setErr(null);
    try { await api(base, { method: "POST", body: JSON.stringify({ date_from: from, date_to: to }) }); setVersion((v) => v + 1); }
    catch (e) { setErr(e instanceof ApiError ? e.message : "Could not make the report"); }
    finally { setBusy(false); }
  };
  const remove = async (m: Meta) => {
    if (!window.confirm("Delete this saved report?")) return;
    try { await api(`${base}/${m.id}`, { method: "DELETE" }); setVersion((v) => v + 1); } catch (e) { setErr(e instanceof ApiError ? e.message : "Could not delete it"); }
  };
  const f = "mt-1 block rounded-lg border border-line bg-canvas px-3 py-2 text-sm";

  return (
    <div className="space-y-6">
      <header>
        <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">Reports</p>
        <h1 className="font-serif text-3xl tracking-tight sm:text-4xl"><Tx k="h.reports" /></h1>
        <p className="mt-1 max-w-2xl text-sm text-fg/70"><Tx k="i.reports" /></p>
      </header>
      {err && <ErrorNote message={err} />}
      <div className="grid items-start gap-6 lg:grid-cols-[1fr_1.4fr] [&>*]:min-w-0">
        {canImport ? (
          <Card title="Make a report" subtitle="It is compared with the period of the same length before.">
            <div className="flex flex-wrap items-end gap-3">
              <label className="text-xs text-muted">From<input type="date" className={f} value={from} onChange={(e) => setFrom(e.target.value)} /></label>
              <label className="text-xs text-muted">To<input type="date" className={f} value={to} onChange={(e) => setTo(e.target.value)} /></label>
            </div>
            <button type="button" disabled={busy || !from || !to || from > to} onClick={make} className="mt-4 w-full rounded-full bg-fg px-5 py-2.5 text-sm font-semibold text-canvas hover:bg-sindoor disabled:opacity-50">{busy ? "Making it…" : "Make the report"}</button>
            <p className="mt-2 text-xs text-muted">PDFs are in English with amounts as “Rs”.</p>
          </Card>
        ) : <EmptyNote>Analysts and above can make reports.</EmptyNote>}
        <section aria-label="Saved reports" className="rounded-2xl border border-line bg-surface">
          <h2 className="border-b border-line px-5 py-3 font-semibold">Saved reports</h2>
          {list.loading && !list.data && <Skeleton className="m-4 h-20" />}
          {list.data?.length === 0 && <div className="p-4"><EmptyNote>None yet.</EmptyNote></div>}
          <ul className="divide-y divide-line">
            {list.data?.map((m) => (
              <li key={m.id} className="flex flex-wrap items-center justify-between gap-2 px-5 py-3 text-sm">
                <span className="min-w-0"><span className="block truncate font-medium">{m.from} → {m.to}</span><span className="text-xs text-muted">made {parseUtc(m.created_at).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}</span></span>
                <span className="flex flex-wrap gap-2">
                  <button type="button" onClick={() => download(`${base}/${m.id}/pdf`, `business-summary-${m.from}-${m.to}.pdf`)} className="rounded-full bg-fg px-3.5 py-1.5 text-xs font-semibold text-canvas hover:bg-sindoor">PDF</button>
                  <button type="button" onClick={() => download(`${base}/${m.id}/csv`, `business-summary-${m.from}-${m.to}.csv`)} className="rounded-full border border-line px-3.5 py-1.5 text-xs hover:bg-surface-2">CSV</button>
                  {can && <button type="button" onClick={() => remove(m)} className="rounded-full px-2.5 py-1.5 text-xs text-sindoor hover:bg-sindoor/10">Delete</button>}
                </span>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
}
