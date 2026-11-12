"use client";

import { useState } from "react";
import { useApi } from "@/lib/analytics";
import { useT } from "@/lib/i18n";
import { useWorkspace } from "./AppContext";
import { EmptyNote, ErrorNote, Skeleton } from "./analytics/parts";
import { Tx } from "./Tx";

type Group = { supplier: string | null; items: { sku: string; name: string; qty: string; status: string }[]; text: string; share_url: string };
type Lists = { as_of: string | null; groups: Group[]; has_forecast: boolean };

/** What to order, grouped by supplier, as text the owner shares. Nothing is sent from here. */
export function OrdersPage() {
  const { workspace } = useWorkspace();
  const { lang } = useT();
  const [copied, setCopied] = useState<string | null>(null);
  const { data, error, loading } = useApi<Lists>(`/workspaces/${workspace.id}/daily/orders?lang=${lang}`, []);
  const copy = async (g: Group) => {
    try {
      await navigator.clipboard.writeText(g.text);
      setCopied(g.supplier ?? "");
    } catch {
      setCopied(null);
    }
  };
  const share = async (g: Group) => {
    if (navigator.share) {
      try {
        await navigator.share({ text: g.text });
        return;
      } catch {
        /* cancelled: fall back to the link */
      }
    }
    window.open(g.share_url, "_blank", "noopener");
  };

  return (
    <div className="space-y-6">
      <header>
        <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-sindoor">{workspace.name}</p>
        <h1 className="mt-1 text-3xl font-bold tracking-tight sm:text-4xl"><Tx k="h.orders" /></h1>
        <p className="mt-1 max-w-2xl text-sm text-muted"><Tx k="i.orders" /></p>
      </header>
      {error && <ErrorNote message={error} />}
      {loading && !data && <Skeleton className="h-48" />}
      {data && data.groups.length === 0 && <EmptyNote>Nothing to order today, or no stock counts yet. Add stock counts on the Stock page.</EmptyNote>}
      <div className="grid gap-5 lg:grid-cols-2">
        {data?.groups.map((g) => (
          <article key={g.supplier ?? "none"} className="min-w-0 rounded-2xl border border-line bg-surface p-5">
            <div className="flex items-baseline justify-between gap-3">
              <h2 className="text-lg font-semibold">{g.supplier ?? "No supplier yet"}</h2>
              <span className="text-sm text-muted">{g.items.length} items</span>
            </div>
            {!g.supplier && <p className="mt-1 text-xs text-muted">Confirm a bill from this supplier on the Bills page and these items will group under them.</p>}
            <pre className="mt-4 whitespace-pre-wrap rounded-xl bg-surface-2 p-4 font-sans text-sm leading-relaxed">{g.text}</pre>
            <div className="mt-4 flex flex-wrap gap-2">
              <button type="button" onClick={() => share(g)} className="rounded-full bg-fg px-5 py-2.5 text-sm font-semibold text-canvas hover:bg-sindoor">Share…</button>
              <button type="button" onClick={() => copy(g)} className="rounded-full border border-line px-5 py-2.5 text-sm hover:bg-surface-2">{copied === (g.supplier ?? "") ? "Copied" : "Copy text"}</button>
            </div>
          </article>
        ))}
      </div>
      {data && !data.has_forecast && data.groups.length > 0 && <p className="text-xs text-muted">Quantities use recent sales; build a forecast for better amounts.</p>}
    </div>
  );
}
