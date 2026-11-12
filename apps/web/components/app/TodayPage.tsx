"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import { ApiError, api } from "@/lib/api";
import { useApi } from "@/lib/analytics";
import { formatINR } from "@/lib/format";
import { useWorkspace } from "./AppContext";
import { Card, EmptyNote, ErrorNote, Skeleton } from "./analytics/parts";
import { Tx } from "./Tx";

type Today = {
  day: string;
  shop: string;
  sales: { day: string; net: string | null; bills: number | null; vs_same_day_last_week_pct: string | null } | null;
  udhaar?: { outstanding: string; overdue: string; call_first: { name: string; owed: string; oldest_days: number }[] } | null;
  order?: { count: number; top: { name: string; qty: string }[] };
  expiry?: { expired: number; this_week: number; soonest: { name: string; days_left: number }[] };
  cash?: { yesterday_closed: boolean; yesterday: string; month_expenses: string };
  alerts: number;
};
type Parsed = { understood: boolean; reason?: string; kind?: "credit" | "payment" | "expense"; party?: string; category?: string; amount?: string; text: string };

const money = (v: string | number | null | undefined) => (v == null ? "–" : formatINR(Number(v)));
const longDay = (iso: string) => new Date(iso + "T00:00:00").toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long" });

/** The first screen of the day: a few numbers and a short list of things to do. */
export function TodayPage() {
  const { workspace } = useWorkspace();
  const [version, setVersion] = useState(0);
  const { data, error, loading } = useApi<Today>(`/workspaces/${workspace.id}/daily/today`, [version]);
  const ch = data?.sales?.vs_same_day_last_week_pct != null ? Number(data.sales.vs_same_day_last_week_pct) : null;

  return (
    <div className="space-y-6">
      <header>
        <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-sindoor">{data ? longDay(data.day) : workspace.name}</p>
        <h1 className="mt-1 text-3xl font-bold tracking-tight sm:text-4xl"><Tx k="h.today" /></h1>
        <p className="mt-1 max-w-2xl text-sm text-muted"><Tx k="i.today" /></p>
      </header>
      {error && <ErrorNote message={error} onRetry={() => setVersion((v) => v + 1)} />}
      {loading && !data && <Skeleton className="h-40" />}
      {data && (
        <>
          <section className="grid gap-4 lg:grid-cols-[1.2fr_1fr]">
            <div className="rounded-3xl bg-fg p-6 text-canvas sm:p-8">
              <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-canvas/60">{data.sales ? `Sales on ${longDay(data.sales.day)}` : "Sales"}</p>
              {data.sales?.net != null ? (
                <>
                  <p className="mt-2 text-5xl font-bold tabular-nums tracking-tight sm:text-6xl">{money(data.sales.net)}</p>
                  <p className="mt-2 text-sm text-canvas/75">
                    {data.sales.bills} bills
                    {ch !== null && <span className={ch >= 0 ? "text-[#7fd6c9]" : "text-[#ff9c8f]"}> · {ch >= 0 ? "▲" : "▼"} {Math.abs(ch)}% on the same day last week</span>}
                  </p>
                </>
              ) : (
                <p className="mt-3 text-canvas/75">No sales file yet. <Link href="/app/data" className="underline underline-offset-4">Import one</Link> to see this every morning.</p>
              )}
            </div>
            <QuickEntry wsId={workspace.id} onSaved={() => setVersion((v) => v + 1)} />
          </section>

          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {data.udhaar !== undefined && (
              <Card title="Call for udhaar" subtitle={data.udhaar ? `${money(data.udhaar.outstanding)} owed · ${money(data.udhaar.overdue)} over 30 days` : undefined} action={<Link href="/app/udhaar" className="text-xs underline underline-offset-4">Open</Link>}>
                {data.udhaar?.call_first.length ? (
                  <ol className="space-y-2 text-sm">
                    {data.udhaar.call_first.map((p) => (
                      <li key={p.name} className="flex justify-between gap-2"><span className="truncate font-medium">{p.name}</span><span className="shrink-0 tabular-nums">{money(p.owed)} <span className="text-xs text-muted">{p.oldest_days}d</span></span></li>
                    ))}
                  </ol>
                ) : <p className="text-sm text-muted">Nobody owes you money.</p>}
              </Card>
            )}
            {data.order && (
              <Card title="Order today" subtitle={data.order.count ? `${data.order.count} products` : undefined} action={<Link href="/app/orders" className="text-xs underline underline-offset-4">Lists</Link>}>
                {data.order.count ? (
                  <ul className="space-y-2 text-sm">
                    {data.order.top.map((o) => <li key={o.name} className="flex justify-between gap-2"><span className="truncate">{o.name}</span><span className="shrink-0 font-mono text-xs">× {Number(o.qty)}</span></li>)}
                  </ul>
                ) : <p className="text-sm text-muted">Nothing to order, or no stock counts yet.</p>}
              </Card>
            )}
            {data.expiry && (
              <Card title="Expiring" subtitle={`${data.expiry.expired} expired · ${data.expiry.this_week} this week`} action={<Link href="/app/expiry" className="text-xs underline underline-offset-4">Open</Link>}>
                {data.expiry.soonest.length ? (
                  <ul className="space-y-2 text-sm">
                    {data.expiry.soonest.map((e) => <li key={e.name} className="flex justify-between gap-2"><span className="truncate">{e.name}</span><span className={`shrink-0 text-xs ${e.days_left < 0 ? "text-sindoor" : "text-muted"}`}>{e.days_left < 0 ? `${-e.days_left}d ago` : `${e.days_left}d left`}</span></li>)}
                  </ul>
                ) : <p className="text-sm text-muted">Nothing on the list. Add items you worry about.</p>}
              </Card>
            )}
            {data.cash && (
              <Card title="Galla" subtitle={`Spent this month: ${money(data.cash.month_expenses)}`} action={<Link href="/app/galla" className="text-xs underline underline-offset-4">Open</Link>}>
                <p className="text-sm">{data.cash.yesterday_closed ? "Yesterday was closed." : <><span className="font-medium text-sindoor">Yesterday was not closed.</span> Count the drawer and close it.</>}</p>
              </Card>
            )}
          </section>
          {data.alerts > 0 && (
            <Link href="/app/alerts" className="flex items-center justify-between rounded-2xl border border-sindoor/30 bg-sindoor/5 px-5 py-4 text-sm hover:bg-sindoor/10">
              <span><b>{data.alerts} urgent alerts</b> are open.</span>
              <span aria-hidden>→</span>
            </Link>
          )}
          {!data.sales && !data.udhaar && !data.order?.count && <EmptyNote>Import a sales file and add stock counts to fill this page.</EmptyNote>}
        </>
      )}
    </div>
  );
}

const KIND_LABEL = { credit: "Udhaar given", payment: "Udhaar received", expense: "Expense" } as const;
const REASON: Record<string, string> = {
  no_amount: "I did not find an amount. Try: “Ramesh ko 200 udhaar”.",
  no_name: "Whose udhaar? Try: “Ramesh ko 200 udhaar”.",
  no_kind: "Is it udhaar or an expense? Try: “Ramesh ne 500 diye” or “chai 60 kharcha”.",
};

/** One sentence in, one entry out: the sentence is read back before anything is saved. */
function QuickEntry({ wsId, onSaved }: { wsId: string; onSaved: () => void }) {
  const [text, setText] = useState("");
  const [parsed, setParsed] = useState<Parsed | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const read = async (e: FormEvent) => {
    e.preventDefault();
    if (!text.trim()) return;
    setMsg(null);
    setBusy(true);
    try {
      setParsed(await api<Parsed>(`/workspaces/${wsId}/daily/quick/parse`, { method: "POST", body: JSON.stringify({ text }) }));
    } catch (err) {
      setMsg(err instanceof ApiError ? err.message : "Could not read that");
    } finally {
      setBusy(false);
    }
  };
  const save = async () => {
    if (!parsed?.understood) return;
    setBusy(true);
    try {
      await api(`/workspaces/${wsId}/daily/quick/save`, { method: "POST", body: JSON.stringify({ kind: parsed.kind, amount: Number(parsed.amount), party: parsed.party, category: parsed.category, note: parsed.text }) });
      setMsg(`Saved: ${KIND_LABEL[parsed.kind!]} ${formatINR(Number(parsed.amount))}${parsed.party ? ` · ${parsed.party}` : ""}`);
      setParsed(null);
      setText("");
      onSaved();
    } catch (err) {
      setMsg(err instanceof ApiError ? err.message : "Could not save");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="rounded-3xl border border-line bg-surface p-6">
      <h2 className="font-semibold">Write it in one line</h2>
      <p className="mt-0.5 text-xs text-muted">“Ramesh ko 200 udhaar” · “Sunita ne 500 diye” · “chai 60 kharcha”</p>
      <form onSubmit={read} className="mt-4 flex gap-2">
        <label htmlFor="quick" className="sr-only">One entry</label>
        <input id="quick" value={text} onChange={(e) => { setText(e.target.value); setParsed(null); }} maxLength={200} placeholder="Ramesh ko 200 udhaar" className="min-w-0 flex-1 rounded-full border border-line bg-canvas px-4 py-2.5 text-[15px] outline-none focus:border-haldi" />
        <button type="submit" disabled={busy || !text.trim()} className="rounded-full bg-fg px-5 text-sm font-semibold text-canvas hover:bg-sindoor disabled:opacity-50">Read</button>
      </form>
      {parsed && parsed.understood && (
        <div className="mt-4 rounded-2xl bg-surface-2 p-4" role="status">
          <p className="text-sm">
            <b>{KIND_LABEL[parsed.kind!]}</b> · {formatINR(Number(parsed.amount))}
            {parsed.party && <> · {parsed.party}</>}
            {parsed.category && parsed.kind === "expense" && <> · {parsed.category}</>}
          </p>
          <div className="mt-3 flex gap-2">
            <button type="button" onClick={save} disabled={busy} className="rounded-full bg-fg px-4 py-2 text-sm font-semibold text-canvas hover:bg-sindoor disabled:opacity-50">Yes, save</button>
            <button type="button" onClick={() => setParsed(null)} className="rounded-full border border-line px-4 py-2 text-sm">Change</button>
          </div>
        </div>
      )}
      {parsed && !parsed.understood && <p className="mt-3 text-sm text-sindoor" role="alert">{REASON[parsed.reason ?? ""] ?? "I could not read that."}</p>}
      {msg && <p className="mt-3 text-sm" role="status">{msg}</p>}
    </div>
  );
}
