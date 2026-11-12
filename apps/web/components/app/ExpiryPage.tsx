"use client";

import { useState, type FormEvent } from "react";
import { ApiError, api } from "@/lib/api";
import { useApi } from "@/lib/analytics";
import { useWorkspace } from "./AppContext";
import { Card, EmptyNote, ErrorNote, Skeleton } from "./analytics/parts";
import { Tx } from "./Tx";

type Item = { id: string; name: string; batch: string | null; expires_on: string; days_left: number; bucket: "expired" | "this_week" | "this_month" | "later"; quantity: string | null; note: string | null };
type List = { counts: Record<Item["bucket"], number>; items: Item[] };

const GROUPS: { key: Item["bucket"]; title: string; tone: string }[] = [
  { key: "expired", title: "Expired: take off the shelf", tone: "border-sindoor/40 bg-sindoor/5" },
  { key: "this_week", title: "This week: sell these first", tone: "border-haldi/50 bg-haldi/10" },
  { key: "this_month", title: "This month", tone: "border-line bg-surface" },
  { key: "later", title: "Later", tone: "border-line bg-surface" },
];

/** A short list of stock the shop worries about, sorted by how soon it expires. Not a pharmacy register. */
export function ExpiryPage() {
  const { workspace } = useWorkspace();
  const base = `/workspaces/${workspace.id}/daily/expiry`;
  const [version, setVersion] = useState(0);
  const [err, setErr] = useState<string | null>(null);
  const { data, error, loading } = useApi<List>(base, [version]);
  const refresh = () => setVersion((v) => v + 1);

  const add = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = e.currentTarget;
    const f = new FormData(form);
    setErr(null);
    try {
      await api(base, { method: "POST", body: JSON.stringify({ name: f.get("name"), expires_on: f.get("expires_on"), quantity: f.get("quantity") ? Number(f.get("quantity")) : null, batch: f.get("batch") || null }) });
      form.reset();
      refresh();
    } catch (x) {
      setErr(x instanceof ApiError ? x.message : "Could not add");
    }
  };
  const clear = (id: string, how: string) => api(`${base}/${id}/clear`, { method: "POST", body: JSON.stringify({ how }) }).then(refresh).catch(() => setErr("Could not update"));
  const input = "rounded-xl border border-line bg-canvas px-3 py-2.5 text-sm outline-none focus:border-haldi";

  return (
    <div className="space-y-6">
      <header>
        <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-sindoor">{workspace.name}</p>
        <h1 className="mt-1 text-3xl font-bold tracking-tight sm:text-4xl"><Tx k="h.expiry" /></h1>
        <p className="mt-1 max-w-2xl text-sm text-muted"><Tx k="i.expiry" /></p>
      </header>
      <Card title="Add an item">
        <form onSubmit={add} className="grid gap-2 sm:grid-cols-[2fr_1fr_0.7fr_0.8fr_auto]">
          <label className="sr-only" htmlFor="ex-name">Item</label>
          <input id="ex-name" name="name" required maxLength={160} placeholder="Item, e.g. Amul Dahi 400g" className={input} />
          <label className="sr-only" htmlFor="ex-date">Expires on</label>
          <input id="ex-date" name="expires_on" type="date" required className={input} />
          <label className="sr-only" htmlFor="ex-qty">Quantity</label>
          <input id="ex-qty" name="quantity" type="number" min={0} step="1" placeholder="Qty" className={input} />
          <label className="sr-only" htmlFor="ex-batch">Batch</label>
          <input id="ex-batch" name="batch" maxLength={40} placeholder="Batch" className={input} />
          <button type="submit" className="rounded-full bg-fg px-5 py-2.5 text-sm font-semibold text-canvas hover:bg-sindoor">Add</button>
        </form>
        {err && <p role="alert" className="mt-2 text-sm text-sindoor">{err}</p>}
      </Card>
      {error && <ErrorNote message={error} />}
      {loading && !data && <Skeleton className="h-40" />}
      {data && data.items.length === 0 && <EmptyNote>Nothing on the list. Add the 20 to 50 items you worry about most: dairy, bread, medicines, baby food.</EmptyNote>}
      {data &&
        GROUPS.filter((g) => data.counts[g.key] > 0).map((g) => (
          <section key={g.key} className={`rounded-2xl border p-4 sm:p-5 ${g.tone}`} aria-labelledby={`g-${g.key}`}>
            <h2 id={`g-${g.key}`} className="font-semibold">{g.title} <span className="font-normal text-muted">({data.counts[g.key]})</span></h2>
            <ul className="mt-3 divide-y divide-line/70">
              {data.items.filter((i) => i.bucket === g.key).map((i) => (
                <li key={i.id} className="flex flex-wrap items-center justify-between gap-3 py-2.5">
                  <span className="min-w-0">
                    <span className="block font-medium">{i.name}{i.quantity ? <span className="font-normal text-muted"> × {Number(i.quantity)}</span> : null}</span>
                    <span className="text-xs text-muted">{i.expires_on}{i.batch ? ` · batch ${i.batch}` : ""} · {i.days_left < 0 ? `${-i.days_left} days ago` : i.days_left === 0 ? "today" : `${i.days_left} days left`}</span>
                  </span>
                  <span className="flex flex-wrap gap-1.5 text-xs">
                    {(["sold", "discounted", "returned", "thrown"] as const).map((how) => (
                      <button key={how} type="button" onClick={() => clear(i.id, how)} className="rounded-full border border-line bg-canvas px-3 py-1.5 hover:bg-surface-2">{how === "thrown" ? "Thrown away" : how[0].toUpperCase() + how.slice(1)}</button>
                    ))}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        ))}
    </div>
  );
}
