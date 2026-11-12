"use client";

import { useState, type FormEvent } from "react";
import { ApiError, api } from "@/lib/api";
import { useApi } from "@/lib/analytics";
import { formatINR } from "@/lib/format";
import { useWorkspace } from "./AppContext";
import { Card, EmptyNote, ErrorNote, Skeleton } from "./analytics/parts";
import { Tx } from "./Tx";

type Saved = { opening_cash: string; cash_sales: string; upi_sales: string; card_sales: string; taken_out: string; counted_cash: string; typed_sales: string; expected_cash: string; difference: string; status: "matches" | "short" | "extra"; file_gap: string | null; rough_profit: string | null; margin_used_pct: string | null; note: string | null };
type View = { day: string; file_sales: string | null; suggested_opening: string | null; cash_expenses: string; udhaar_given: string; udhaar_received: string; saved: Saved | null };
type Expenses = { total: string; by_category: { category: string; amount: string }[]; items: { id: string; spent_on: string; category: string; amount: string; paid_by: string; note: string | null }[] };
type Cat = { key: string; en: string };

const inr = (v: string | number | null | undefined) => (v == null ? "–" : formatINR(Number(v)));
const iso = (d: Date) => d.toISOString().slice(0, 10);

/** Close the day: what should be in the drawer, against what is. And the day's expenses. */
export function GallaPage() {
  const { workspace } = useWorkspace();
  const base = `/workspaces/${workspace.id}/daily`;
  const [day, setDay] = useState(() => iso(new Date()));
  const [version, setVersion] = useState(0);
  const view = useApi<View>(`${base}/close?day=${day}`, [version]);
  const history = useApi<{ day: string; typed_sales: string; difference: string; status: string }[]>(`${base}/close/history?days=14`, [version]);
  const month = useApi<Expenses>(`${base}/expenses`, [version]);
  const cats = useApi<Cat[]>(`${base}/expense-categories`, []);
  const canWrite = ["owner", "admin"].includes(workspace.role);
  const label = (k: string) => cats.data?.find((c) => c.key === k)?.en ?? k;
  const refresh = () => setVersion((v) => v + 1);

  return (
    <div className="space-y-6">
      <header>
        <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-sindoor">{workspace.name}</p>
        <h1 className="mt-1 text-3xl font-bold tracking-tight sm:text-4xl"><Tx k="h.galla" /></h1>
        <p className="mt-1 max-w-2xl text-sm text-muted"><Tx k="i.galla" /></p>
      </header>
      <div className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr] [&>*]:min-w-0">
        <Card title="Close the day" action={<input type="date" value={day} max={iso(new Date())} onChange={(e) => setDay(e.target.value)} aria-label="Day" className="rounded-lg border border-line bg-canvas px-2 py-1 text-sm" />}>
          {view.error && <ErrorNote message={view.error} />}
          {view.loading && !view.data && <Skeleton className="h-60" />}
          {view.data && <CloseForm key={`${day}-${version}`} base={base} v={view.data} canWrite={canWrite} onSaved={refresh} />}
        </Card>
        <div className="space-y-6">
          <Card title="Expenses this month" subtitle={month.data ? `Total ${inr(month.data.total)}` : undefined}>
            {canWrite && <ExpenseForm base={base} cats={cats.data ?? []} onSaved={refresh} />}
            {month.data && month.data.items.length === 0 && <p className="mt-3 text-sm text-muted">No expenses written this month.</p>}
            {month.data && month.data.by_category.length > 0 && (
              <ul className="mt-4 space-y-1.5 text-sm">
                {month.data.by_category.map((c) => (
                  <li key={c.category} className="flex justify-between"><span>{label(c.category)}</span><span className="tabular-nums">{inr(c.amount)}</span></li>
                ))}
              </ul>
            )}
            {month.data && month.data.items.length > 0 && (
              <details className="mt-3 text-sm">
                <summary className="cursor-pointer text-muted">Every entry ({month.data.items.length})</summary>
                <ul className="mt-2 divide-y divide-line">
                  {month.data.items.map((x) => (
                    <li key={x.id} className="flex items-center justify-between gap-2 py-1.5">
                      <span className="min-w-0 truncate">{x.spent_on.slice(5)} · {label(x.category)}{x.note ? ` · ${x.note}` : ""} <span className="text-xs text-muted">({x.paid_by})</span></span>
                      <span className="flex shrink-0 items-center gap-2 tabular-nums">{inr(x.amount)}{canWrite && <button type="button" aria-label="Delete expense" onClick={() => api(`${base}/expenses/${x.id}`, { method: "DELETE" }).then(refresh)} className="text-xs text-sindoor hover:underline">✕</button>}</span>
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </Card>
          <Card title="Last two weeks">
            {history.data && history.data.length === 0 && <EmptyNote>No days closed yet.</EmptyNote>}
            <ul className="space-y-1.5 text-sm">
              {history.data?.map((h) => (
                <li key={h.day} className="flex justify-between gap-2">
                  <button type="button" onClick={() => setDay(h.day)} className="underline decoration-line underline-offset-4">{h.day}</button>
                  <span className="tabular-nums">{inr(h.typed_sales)} <span className={`ml-2 text-xs ${h.status === "matches" ? "text-mor" : "text-sindoor"}`}>{h.status === "matches" ? "matched" : `${h.status} ${inr(Math.abs(Number(h.difference)))}`}</span></span>
                </li>
              ))}
            </ul>
          </Card>
        </div>
      </div>
    </div>
  );
}

function CloseForm({ base, v, canWrite, onSaved }: { base: string; v: View; canWrite: boolean; onSaved: () => void }) {
  const s = v.saved;
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const submit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const n = (k: string) => Number(f.get(k) || 0);
    setBusy(true);
    setErr(null);
    try {
      await api(`${base}/close`, { method: "PUT", body: JSON.stringify({ day: v.day, opening_cash: n("opening"), cash_sales: n("cash"), upi_sales: n("upi"), card_sales: n("card"), taken_out: n("out"), counted_cash: n("counted"), note: String(f.get("note") || "") || null }) });
      onSaved();
    } catch (x) {
      setErr(x instanceof ApiError ? x.message : "Could not save");
    } finally {
      setBusy(false);
    }
  };
  const field = (name: string, label: string, value: string | null | undefined, hint?: string) => (
    <label className="block">
      <span className="text-xs text-muted">{label}</span>
      <input name={name} type="number" inputMode="decimal" min={0} step="0.01" defaultValue={value == null ? "" : Number(value)} disabled={!canWrite} className="mt-1 w-full rounded-xl border border-line bg-canvas px-3 py-2.5 text-lg tabular-nums outline-none focus:border-haldi disabled:opacity-60" />
      {hint && <span className="mt-0.5 block text-[11px] text-muted">{hint}</span>}
    </label>
  );
  return (
    <form onSubmit={submit} className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-2">
        {field("opening", "Cash in the drawer this morning", s?.opening_cash ?? v.suggested_opening, v.suggested_opening != null && !s ? "From the last close" : undefined)}
        {field("cash", "Sales in cash", s?.cash_sales)}
        {field("upi", "Sales by UPI", s?.upi_sales)}
        {field("card", "Sales by card", s?.card_sales)}
        {field("out", "Taken out (banked or home)", s?.taken_out)}
        {field("counted", "Cash counted now", s?.counted_cash)}
      </div>
      <dl className="grid gap-x-6 gap-y-1 rounded-2xl bg-surface-2 p-4 text-sm sm:grid-cols-2">
        <div className="flex justify-between"><dt className="text-muted">Cash expenses today</dt><dd className="tabular-nums">{inr(v.cash_expenses)}</dd></div>
        <div className="flex justify-between"><dt className="text-muted">Udhaar paid back today</dt><dd className="tabular-nums">{inr(v.udhaar_received)}</dd></div>
        <div className="flex justify-between"><dt className="text-muted">Udhaar given today</dt><dd className="tabular-nums">{inr(v.udhaar_given)}</dd></div>
        <div className="flex justify-between"><dt className="text-muted">Sales in the sales file</dt><dd className="tabular-nums">{v.file_sales == null ? "not in file" : inr(v.file_sales)}</dd></div>
      </dl>
      {s && (
        <div className={`rounded-2xl p-5 ${s.status === "matches" ? "bg-mor/10" : "bg-sindoor/10"}`} role="status">
          <p className="text-lg font-semibold">{s.status === "matches" ? "The drawer matches." : s.status === "short" ? `The drawer is short by ${inr(Math.abs(Number(s.difference)))}.` : `The drawer has ${inr(Number(s.difference))} extra.`}</p>
          <p className="mt-1 text-sm text-fg/75">Expected {inr(s.expected_cash)} = morning cash + cash sales + udhaar paid back − cash expenses − taken out. Counted {inr(s.counted_cash)}.</p>
          {s.file_gap != null && Math.abs(Number(s.file_gap)) >= 1 && <p className="mt-1 text-sm text-fg/75">Typed sales differ from the sales file by {inr(Math.abs(Number(s.file_gap)))}.</p>}
          {s.rough_profit != null && <p className="mt-1 text-sm text-fg/75">Rough profit today: {inr(s.rough_profit)} (sales × the last 30 days&apos; margin of {s.margin_used_pct}%, minus today&apos;s expenses).</p>}
        </div>
      )}
      <label className="block"><span className="text-xs text-muted">Note</span><input name="note" maxLength={200} defaultValue={s?.note ?? ""} disabled={!canWrite} className="mt-1 w-full rounded-xl border border-line bg-canvas px-3 py-2 text-sm outline-none focus:border-haldi" /></label>
      {err && <p role="alert" className="text-sm text-sindoor">{err}</p>}
      {canWrite ? <button type="submit" disabled={busy} className="rounded-full bg-fg px-6 py-3 text-sm font-semibold text-canvas hover:bg-sindoor disabled:opacity-50">{s ? "Update the close" : "Close the day"}</button> : <p className="text-sm text-muted">View only.</p>}
    </form>
  );
}

function ExpenseForm({ base, cats, onSaved }: { base: string; cats: Cat[]; onSaved: () => void }) {
  const [err, setErr] = useState<string | null>(null);
  const submit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = e.currentTarget;
    const f = new FormData(form);
    setErr(null);
    try {
      await api(`${base}/expenses`, { method: "POST", body: JSON.stringify({ category: f.get("category"), amount: Number(f.get("amount")), paid_by: f.get("paid_by"), note: String(f.get("note") || "") || null }) });
      form.reset();
      onSaved();
    } catch (x) {
      setErr(x instanceof ApiError ? x.message : "Could not save");
    }
  };
  const input = "rounded-xl border border-line bg-canvas px-3 py-2 text-sm outline-none focus:border-haldi";
  return (
    <form onSubmit={submit} className="grid gap-2 sm:grid-cols-[1fr_7rem]">
      <label className="sr-only" htmlFor="exp-cat">Category</label>
      <select id="exp-cat" name="category" className={input} defaultValue="tea">{cats.map((c) => <option key={c.key} value={c.key}>{c.en}</option>)}</select>
      <label className="sr-only" htmlFor="exp-amt">Amount</label>
      <input id="exp-amt" name="amount" type="number" min={1} step="0.01" required placeholder="₹" className={`${input} tabular-nums`} />
      <label className="sr-only" htmlFor="exp-note">Note</label>
      <input id="exp-note" name="note" maxLength={200} placeholder="Note (optional)" className={input} />
      <label className="sr-only" htmlFor="exp-by">Paid by</label>
      <select id="exp-by" name="paid_by" className={input} defaultValue="cash"><option value="cash">Cash</option><option value="upi">UPI</option><option value="card">Card</option><option value="bank">Bank</option></select>
      <button type="submit" className="rounded-full bg-fg px-4 py-2 text-sm font-semibold text-canvas hover:bg-sindoor sm:col-span-2">Add expense</button>
      {err && <p role="alert" className="text-sm text-sindoor sm:col-span-2">{err}</p>}
    </form>
  );
}
