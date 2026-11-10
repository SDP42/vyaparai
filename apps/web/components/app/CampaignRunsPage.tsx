"use client";

import Link from "next/link";
import { useRef, useState } from "react";
import { ApiError, api } from "@/lib/api";
import { useApi } from "@/lib/analytics";
import { formatINR } from "@/lib/format";
import { useWorkspace } from "./AppContext";
import { Card, EmptyNote, ErrorNote, Skeleton } from "./analytics/parts";

type Summary = { customers: number; recorded: number; reachable: number; granted: number; denied: number; unknown: number; opted_out: number; no_phone: number };
type Contact = { customer_key: string; phone: string | null; consent: string; source: string | null; consent_date: string | null; opted_out: boolean };
type Run = { id: string; name: string; segment: string; status: string; started_on: string | null; window_days: number; holdout_pct: number; counts: Record<string, number> };
type OutItem = { id: string; customer_key: string; phone: string | null; message: string; product: string | null; discount_pct: number; whatsapp: string };
type Outbox = { items: OutItem[]; pending: number; sent_today: number; daily_cap: number; can_send_today: number };
type Band = { diff_points?: number; low: number; high: number; verdict?: string; incremental_total?: number; incremental_low?: number; incremental_high?: number; diff_per_customer?: number };
type Group = { customers: number; bought: number; rate: number; revenue_per_customer: number; profit_per_customer: number };
type Results = { ready: boolean; message?: string; final?: boolean; from?: string; to?: string; days_left?: number; not_sent_yet?: number; treated?: Group; holdout?: Group; purchase_rate?: Band; revenue?: Band; profit?: Band; needed_per_group_for_5_points?: number; warnings?: string[]; caveat?: string };

const SEGMENTS = ["At risk", "Hibernating", "Loyal", "Champions", "New"];
const pct = (x: number) => `${(x * 100).toFixed(0)}%`;
const VERDICT = { positive: ["It worked", "bg-mor/12 text-mor"], negative: ["It did worse", "bg-sindoor/10 text-sindoor"], inconclusive: ["Cannot tell yet", "bg-haldi/25"] } as const;

function ResultsView({ base, id }: { base: string; id: string }) {
  const { data, error, loading } = useApi<Results>(`${base}/runs/${id}/results`, []);
  if (error) return <ErrorNote message={error} />;
  if (!data) return loading ? <Skeleton className="h-40" /> : null;
  if (!data.ready) return <EmptyNote>{data.message}</EmptyNote>;
  const t = data.treated!, h = data.holdout!, v = VERDICT[(data.profit?.verdict ?? "inconclusive") as keyof typeof VERDICT];
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className={`rounded-full px-3 py-1 text-sm font-semibold ${v[1]}`}>{v[0]}</span>
        <span className="text-xs text-muted">{data.from} to {data.to}{data.final ? " (finished)" : `, ${data.days_left} days still to run`}</span>
      </div>
      <div className="fluid [--min:14rem]">
        {[["Messaged", t], ["Held back (not messaged)", h]].map(([label, g]) => (
          <div key={label as string} className="rounded-2xl border border-line bg-surface p-4">
            <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted">{label as string}</p>
            <p className="mt-1 text-2xl font-bold">{(g as Group).customers} <span className="text-sm font-normal text-muted">customers</span></p>
            <p className="text-sm">{pct((g as Group).rate)} bought · {formatINR((g as Group).revenue_per_customer)} each · profit {formatINR((g as Group).profit_per_customer)} each</p>
          </div>
        ))}
      </div>
      <dl className="divide-y divide-line rounded-2xl border border-line bg-surface text-sm">
        <div className="flex flex-wrap justify-between gap-2 px-4 py-3"><dt>More customers bought, by</dt><dd className="font-medium">{data.purchase_rate!.diff_points!.toFixed(1)} points <span className="text-muted">(plausibly {data.purchase_rate!.low.toFixed(1)} to {data.purchase_rate!.high.toFixed(1)})</span></dd></div>
        <div className="flex flex-wrap justify-between gap-2 px-4 py-3"><dt>Extra profit from this campaign</dt><dd className="font-medium">{formatINR(data.profit!.incremental_total!)} <span className="text-muted">(plausibly {formatINR(data.profit!.incremental_low!)} to {formatINR(data.profit!.incremental_high!)})</span></dd></div>
        <div className="flex flex-wrap justify-between gap-2 px-4 py-3"><dt>Extra sales</dt><dd className="font-medium">{formatINR(data.revenue!.incremental_total!)} <span className="text-muted">(plausibly {formatINR(data.revenue!.incremental_low!)} to {formatINR(data.revenue!.incremental_high!)})</span></dd></div>
      </dl>
      {data.warnings?.map((w) => <p key={w} role="status" className="rounded-lg bg-haldi/20 px-3 py-2 text-sm">{w}</p>)}
      <p className="text-xs text-muted">{data.caveat} To see a 5-point lift reliably you would need about {data.needed_per_group_for_5_points} customers in each group.</p>
    </div>
  );
}

function RunView({ base, run, onBack }: { base: string; run: Run; onBack: () => void }) {
  const [version, setVersion] = useState(0);
  const [err, setErr] = useState<string | null>(null);
  const [opened, setOpened] = useState<Set<string>>(new Set());
  const out = useApi<Outbox>(`${base}/runs/${run.id}/outbox`, [version]);
  const markSent = async (ids: string[]) => {
    setErr(null);
    try { await api(`${base}/runs/${run.id}/mark-sent`, { method: "POST", body: JSON.stringify({ ids }) }); setVersion((v) => v + 1); }
    catch (e) { setErr(e instanceof ApiError ? e.message : "Could not save"); }
  };
  return (
    <div className="space-y-5">
      <button type="button" onClick={onBack} className="text-sm text-muted hover:text-fg">← All campaigns</button>
      <header><h2 className="font-serif text-2xl">{run.name}</h2><p className="text-sm text-muted">{run.segment} · {run.counts.treatment} to message, {run.counts.holdout} held back as a fair comparison · measured over {run.window_days} days</p></header>
      {err && <ErrorNote message={err} />}
      <Card title="Send" subtitle="Open each message in WhatsApp, press send yourself, then mark it as sent. Nothing is sent automatically.">
        {out.data && <p className="mb-3 text-xs text-muted">{out.data.pending} waiting · {out.data.sent_today} sent today of {out.data.daily_cap} allowed</p>}
        {out.error && <ErrorNote message={out.error} />}
        {out.data?.items.length === 0 && <EmptyNote>Nothing waiting to send.</EmptyNote>}
        <ul className="space-y-3">
          {out.data?.items.map((i) => (
            <li key={i.id} className="rounded-xl border border-line bg-canvas p-3 text-sm">
              <p className="flex flex-wrap justify-between gap-2"><b>{i.customer_key}</b><span className="text-muted">{i.phone}{i.discount_pct > 0 ? ` · ${i.discount_pct}% on ${i.product}` : ""}</span></p>
              <p className="mt-1 whitespace-pre-line break-words text-fg/85">{i.message}</p>
              <div className="mt-2 flex flex-wrap gap-2">
                <a href={i.whatsapp} target="_blank" rel="noopener noreferrer" onClick={() => setOpened((s) => new Set(s).add(i.id))} className="rounded-full bg-fg px-3 py-1 text-xs font-semibold text-canvas hover:bg-sindoor">Open in WhatsApp</a>
                <button type="button" disabled={!opened.has(i.id)} onClick={() => markSent([i.id])} className="rounded-full border border-line px-3 py-1 text-xs hover:bg-surface-2 disabled:opacity-40">I sent it</button>
              </div>
            </li>
          ))}
        </ul>
      </Card>
      <Card title="Did it work?" subtitle="Compared with customers who were chosen the same way but not messaged."><ResultsView base={base} id={run.id} /></Card>
    </div>
  );
}

function Contacts({ base, canEdit }: { base: string; canEdit: boolean }) {
  const [version, setVersion] = useState(0);
  const ref = useRef<HTMLInputElement>(null);
  const [err, setErr] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [form, setForm] = useState({ customer_key: "", phone: "", source: "" });
  const sum = useApi<Summary>(`${base}/contacts/summary`, [version]);
  const list = useApi<Contact[]>(canEdit ? `${base}/contacts` : null, [version]);
  const act = async (fn: () => Promise<unknown>, ok?: string) => { setErr(null); setMsg(null); try { await fn(); if (ok) setMsg(ok); setVersion((v) => v + 1); } catch (e) { setErr(e instanceof ApiError ? e.message : "Could not save"); } };
  const s = sum.data;
  const f = "mt-1 w-full rounded-lg border border-line bg-canvas px-3 py-2 text-sm";
  return (
    <div className="space-y-5">
      {err && <ErrorNote message={err} />}
      {s && (
        <section className="fluid [--min:9rem]" aria-label="Consent">
          {[["Can be messaged", s.reachable], ["Agreed", s.granted], ["Said no", s.denied], ["Not asked", s.unknown], ["Opted out", s.opted_out], ["No phone", s.no_phone]].map(([l, v]) => (
            <div key={l as string} className="rounded-2xl border border-line bg-surface p-4"><p className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted">{l as string}</p><p className="mt-1 text-2xl font-bold">{v as number}</p></div>
          ))}
        </section>
      )}
      <p className="text-sm text-fg/70">Only customers who agreed to hear from you, with a phone number and no opt-out, can be messaged. Record how and when they agreed. A STOP is final until they agree again.</p>
      {canEdit && (
        <div className="grid items-start gap-5 lg:grid-cols-2">
          <Card title="Record consent" subtitle="Use the same customer key as in your sales file.">
            <div className="space-y-3">
              <label className="block text-xs text-muted">Customer key<input className={f} value={form.customer_key} onChange={(e) => setForm({ ...form, customer_key: e.target.value })} /></label>
              <div className="grid grid-cols-2 gap-3"><label className="block text-xs text-muted">Phone<input className={f} inputMode="tel" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></label><label className="block text-xs text-muted">How they agreed<input className={f} value={form.source} placeholder="asked at the counter" onChange={(e) => setForm({ ...form, source: e.target.value })} /></label></div>
              <div className="flex flex-wrap gap-2">
                <button type="button" disabled={!form.customer_key || !form.source} onClick={() => act(() => api(`${base}/contacts`, { method: "PUT", body: JSON.stringify({ customer_key: form.customer_key, phone: form.phone || null, consent: "granted", source: form.source }) }), "Saved.")} className="rounded-full bg-fg px-4 py-2 text-sm font-semibold text-canvas hover:bg-sindoor disabled:opacity-50">They agreed</button>
                <button type="button" disabled={!form.customer_key} onClick={() => act(() => api(`${base}/contacts/opt-out`, { method: "POST", body: JSON.stringify({ customer_key: form.customer_key }) }), "Opt-out recorded.")} className="rounded-full border border-line px-4 py-2 text-sm text-sindoor hover:bg-sindoor/10 disabled:opacity-50">Record a STOP</button>
              </div>
              {msg && <p role="status" className="text-sm">{msg}</p>}
            </div>
          </Card>
          <Card title="Bring in a list" subtitle="CSV with Customer, Phone, Consent (yes or no) and Source.">
            <input ref={ref} type="file" accept=".csv,text/csv" className="hidden" onChange={(e) => { const file = e.target.files?.[0]; if (!file) return; const fd = new FormData(); fd.append("file", file); void act(async () => { const r = await api<{ saved: number; skipped: number }>(`${base}/contacts/import`, { method: "POST", body: fd }); setMsg(`${r.saved} saved${r.skipped ? `, ${r.skipped} skipped` : ""}.`); }); if (ref.current) ref.current.value = ""; }} />
            <button type="button" onClick={() => ref.current?.click()} className="rounded-full bg-fg px-4 py-2 text-sm font-semibold text-canvas hover:bg-sindoor">Upload list</button>
          </Card>
        </div>
      )}
      {list.data && list.data.length > 0 && (
        <section className="rounded-2xl border border-line bg-surface" aria-label="Contacts">
          <h2 className="border-b border-line px-5 py-3 font-semibold">Recently recorded</h2>
          <ul className="divide-y divide-line text-sm">
            {list.data.map((c) => <li key={c.customer_key} className="flex flex-wrap justify-between gap-2 px-5 py-2.5"><span><b>{c.customer_key}</b> <span className="text-muted">{c.phone ?? "no phone"}{c.source ? ` · ${c.source}` : ""}</span></span><span className={`rounded-full px-2.5 py-0.5 text-xs ${c.opted_out ? "bg-sindoor/10 text-sindoor" : c.consent === "granted" ? "bg-mor/12 text-mor" : "bg-surface-2 text-muted"}`}>{c.opted_out ? "opted out" : c.consent}</span></li>)}
          </ul>
        </section>
      )}
    </div>
  );
}

export function CampaignRunsPage() {
  const { workspace } = useWorkspace();
  const base = `/workspaces/${workspace.id}/campaigns`;
  const isAdmin = ["owner", "admin"].includes(workspace.role);
  const canEdit = ["owner", "admin", "analyst"].includes(workspace.role);
  const [tab, setTab] = useState<"runs" | "contacts">("runs");
  const [open, setOpen] = useState<Run | null>(null);
  const [version, setVersion] = useState(0);
  const [form, setForm] = useState({ name: "", segment: "At risk", holdout_pct: 10, language: "hinglish" });
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const runs = useApi<Run[]>(`${base}/runs`, [version]);
  const launch = async () => {
    setBusy(true); setErr(null);
    try { const r = await api<Run>(`${base}/runs`, { method: "POST", body: JSON.stringify(form) }); setVersion((v) => v + 1); setOpen(r); }
    catch (e) { setErr(e instanceof ApiError ? e.message : "Could not start it"); }
    finally { setBusy(false); }
  };
  const f = "mt-1 w-full rounded-lg border border-line bg-canvas px-3 py-2 text-sm";
  return (
    <div className="space-y-6">
      <header>
        <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">Campaigns</p>
        <h1 className="font-serif text-3xl tracking-tight sm:text-4xl">Message customers, and find out if it worked</h1>
        <p className="mt-1 max-w-2xl text-sm text-fg/70">Only people who agreed are messaged, each message is one you send yourself, and a few eligible customers are held back so the result is a fair comparison. <Link href="/app/campaigns" className="underline underline-offset-4">Plan a campaign first →</Link></p>
      </header>
      <div role="tablist" aria-label="Section" className="flex w-fit gap-1 rounded-full border border-line bg-surface p-1">
        {([["runs", "Campaigns"], ["contacts", "Consent and contacts"]] as const).map(([k, l]) => <button key={k} role="tab" aria-selected={tab === k} onClick={() => { setTab(k); setOpen(null); }} className={`rounded-full px-4 py-1.5 text-sm ${tab === k ? "bg-fg text-canvas" : "text-fg/65 hover:text-fg"}`}>{l}</button>)}
      </div>
      {tab === "contacts" && <Contacts base={base} canEdit={canEdit} />}
      {tab === "runs" && open && <RunView base={base} run={open} onBack={() => setOpen(null)} />}
      {tab === "runs" && !open && (
        <div className="grid items-start gap-6 lg:grid-cols-[1.4fr_1fr]">
          <section className="rounded-2xl border border-line bg-surface" aria-label="Campaigns">
            <h2 className="border-b border-line px-5 py-3 font-semibold">Your campaigns</h2>
            {runs.loading && !runs.data && <Skeleton className="m-4 h-20" />}
            {runs.data?.length === 0 && <div className="p-4"><EmptyNote>None yet. Record consent, then start one.</EmptyNote></div>}
            <ul className="divide-y divide-line">
              {runs.data?.map((r) => <li key={r.id}><button type="button" onClick={() => setOpen(r)} className="flex w-full flex-wrap items-center justify-between gap-2 px-5 py-3 text-left text-sm hover:bg-surface-2/60"><span><b>{r.name}</b><span className="block text-xs text-muted">{r.segment} · {r.counts.treatment} messaged, {r.counts.holdout} held back{r.started_on ? ` · started ${r.started_on}` : " · not sent yet"}</span></span><span className="rounded-full bg-surface-2 px-2.5 py-0.5 text-xs">{r.status}</span></button></li>)}
            </ul>
          </section>
          {isAdmin ? (
            <Card title="Start a campaign" subtitle="Freezes who is messaged and who is held back.">
              {err && <ErrorNote message={err} />}
              <div className="space-y-3">
                <label className="block text-xs text-muted">Name<input className={f} value={form.name} maxLength={120} onChange={(e) => setForm({ ...form, name: e.target.value })} /></label>
                <label className="block text-xs text-muted">Who<select className={f} value={form.segment} onChange={(e) => setForm({ ...form, segment: e.target.value })}>{SEGMENTS.map((s) => <option key={s}>{s}</option>)}</select></label>
                <div className="grid grid-cols-2 gap-3">
                  <label className="block text-xs text-muted">Held back %<input type="number" min={0} max={50} className={f} value={form.holdout_pct} onChange={(e) => setForm({ ...form, holdout_pct: Number(e.target.value) })} /></label>
                  <label className="block text-xs text-muted">Language<select className={f} value={form.language} onChange={(e) => setForm({ ...form, language: e.target.value })}><option value="hinglish">Hinglish</option><option value="en">English</option></select></label>
                </div>
                <button type="button" disabled={busy || !form.name.trim()} onClick={launch} className="w-full rounded-full bg-fg px-5 py-2.5 text-sm font-semibold text-canvas hover:bg-sindoor disabled:opacity-50">{busy ? "Working…" : "Start"}</button>
              </div>
            </Card>
          ) : <EmptyNote>Owners and admins start campaigns.</EmptyNote>}
        </div>
      )}
    </div>
  );
}
