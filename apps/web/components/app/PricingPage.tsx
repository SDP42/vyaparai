"use client";

import { useState } from "react";
import { useApi } from "@/lib/analytics";
import { formatINR } from "@/lib/format";
import { useWorkspace } from "./AppContext";
import { EmptyNote, ErrorNote, Skeleton } from "./analytics/parts";

type Disc = { sku: string; name: string; promo_days: number; normal_days: number; avg_discount_pct: number; lift_pct: number; extra_units: number; discount_given: number; profit_known: boolean; profit_effect?: number; profit_effect_low?: number; profit_effect_high?: number; verdict: "paid_off" | "lost_money" | "unclear"; note?: string };
type Discounts = { has_data: boolean; from?: string; to?: string; items: Disc[]; summary: { judged?: number; paid_off?: number; lost_money?: number; unclear?: number; discount_in_losing_promos?: number }; method?: string; limits?: string[] };
type Move = { sku: string; name: string; week: string; old_price: number; new_price: number; price_pct: number; units_pct: number; elasticity: number | null; reliable: boolean };
type Sug = { sku: string; name: string; price: number; suggested_price: number; step_pct: number; margin_pct: number; profit_change_month: { low: number; expected: number; high: number }; measured: boolean; assumption: string | null; why: string };
type Moves = { has_data: boolean; moves: Move[]; suggestions: Sug[]; limits?: string[] };

const V = { paid_off: ["Paid off", "bg-mor/12 text-mor"], lost_money: ["Lost money", "bg-sindoor/10 text-sindoor"], unclear: ["Cannot tell", "bg-haldi/25"] } as const;

export function PricingPage() {
  const { workspace } = useWorkspace();
  const base = `/workspaces/${workspace.id}/pricing`;
  const [tab, setTab] = useState<"discounts" | "moves">("discounts");
  const d = useApi<Discounts>(`${base}/discounts`, []);
  const m = useApi<Moves>(`${base}/moves`, []);
  return (
    <div className="space-y-6">
      <header>
        <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">Pricing</p>
        <h1 className="font-serif text-3xl tracking-tight sm:text-4xl">Did your offers pay off?</h1>
        <p className="mt-1 max-w-2xl text-sm text-fg/70">Each product&apos;s discount days are compared with its normal days of the same weekday, in sales and in profit after the discount. Price moves are small trials, never big jumps.</p>
      </header>
      <div role="tablist" aria-label="Section" className="flex w-fit gap-1 rounded-full border border-line bg-surface p-1">
        {([["discounts", "Discounts"], ["moves", "Price moves"]] as const).map(([k, l]) => <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)} className={`rounded-full px-4 py-1.5 text-sm ${tab === k ? "bg-fg text-canvas" : "text-fg/65 hover:text-fg"}`}>{l}</button>)}
      </div>

      {tab === "discounts" && (
        <>
          {d.error && <ErrorNote message={d.error} />}
          {!d.data && d.loading && <Skeleton className="h-40" />}
          {d.data && !d.data.has_data && <EmptyNote>Import some sales first.</EmptyNote>}
          {d.data?.has_data && d.data.items.length === 0 && <EmptyNote>No product has enough discount days yet. A product needs at least 3 discount days and 4 weeks of normal selling to be judged.</EmptyNote>}
          {d.data && d.data.items.length > 0 && (
            <>
              <section className="fluid [--min:11rem]" aria-label="Summary">
                {[["Paid off", d.data.summary.paid_off], ["Lost money", d.data.summary.lost_money], ["Cannot tell", d.data.summary.unclear], ["Given away in losing offers", formatINR(d.data.summary.discount_in_losing_promos ?? 0)]].map(([l, v]) => (
                  <div key={l as string} className="rounded-2xl border border-line bg-surface p-4"><p className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted">{l as string}</p><p className="mt-1 text-2xl font-bold">{v as string | number}</p></div>
                ))}
              </section>
              <ul className="space-y-3">
                {d.data.items.map((i) => (
                  <li key={i.sku} className="rounded-2xl border border-line bg-surface p-4">
                    <div className="flex flex-wrap items-start justify-between gap-2"><h3 className="font-semibold">{i.name}</h3><span className={`rounded-full px-2.5 py-0.5 text-xs ${V[i.verdict][1]}`}>{V[i.verdict][0]}</span></div>
                    <p className="mt-1 text-sm text-fg/75">{i.promo_days} discount days at about {i.avg_discount_pct}% off. Sales {i.lift_pct >= 0 ? "rose" : "fell"} {Math.abs(i.lift_pct).toFixed(0)}% against a normal {i.promo_days === 1 ? "day" : "days"} of the same weekdays ({i.extra_units >= 0 ? "+" : ""}{i.extra_units.toFixed(0)} units).</p>
                    <dl className="mt-3 flex flex-wrap gap-2 text-xs">
                      <div className="rounded-lg bg-canvas px-2.5 py-1"><dt className="font-mono uppercase tracking-wider text-muted">Discount given</dt><dd className="text-sm font-semibold">{formatINR(i.discount_given)}</dd></div>
                      {i.profit_known && i.profit_effect != null && <div className="rounded-lg bg-canvas px-2.5 py-1"><dt className="font-mono uppercase tracking-wider text-muted">Profit effect</dt><dd className={`text-sm font-semibold ${i.profit_effect < 0 ? "text-sindoor" : "text-mor"}`}>{formatINR(i.profit_effect)} <span className="font-normal text-muted">({formatINR(i.profit_effect_low ?? 0)} to {formatINR(i.profit_effect_high ?? 0)})</span></dd></div>}
                    </dl>
                    {i.note && <p className="mt-2 text-xs text-muted">{i.note}</p>}
                  </li>
                ))}
              </ul>
              <p className="rounded-xl bg-surface-2 p-4 text-xs text-muted">{d.data.method} {d.data.limits?.join(" ")}</p>
            </>
          )}
        </>
      )}

      {tab === "moves" && (
        <>
          {m.error && <ErrorNote message={m.error} />}
          {!m.data && m.loading && <Skeleton className="h-40" />}
          {m.data?.suggestions && m.data.suggestions.length > 0 && (
            <section aria-label="Suggestions" className="space-y-3">
              <h2 className="font-semibold">Worth a one-week trial</h2>
              {m.data.suggestions.map((s) => (
                <article key={s.sku} className="rounded-2xl border border-line bg-surface p-4">
                  <div className="flex flex-wrap items-start justify-between gap-2"><h3 className="font-semibold">{s.name}: {formatINR(s.price)} → {formatINR(s.suggested_price)} (+{s.step_pct}%)</h3><span className="text-right text-sm"><b className="text-lg">{formatINR(s.profit_change_month.expected)}</b><span className="block text-[11px] text-muted">a month, between {formatINR(s.profit_change_month.low)} and {formatINR(s.profit_change_month.high)}</span></span></div>
                  <p className="mt-1 text-sm text-fg/75">{s.why} Margin is {s.margin_pct}%.</p>
                  <p className="mt-2 text-xs text-muted">{s.measured ? "Based on how this product's volume reacted to its own earlier price change." : s.assumption}</p>
                </article>
              ))}
            </section>
          )}
          <section aria-label="Past moves" className="rounded-2xl border border-line bg-surface">
            <h2 className="border-b border-line px-5 py-3 font-semibold">Price changes you made and what followed</h2>
            {m.data && m.data.moves.length === 0 && <div className="p-4"><EmptyNote>No lasting price change was found in the last six months.</EmptyNote></div>}
            <ul className="divide-y divide-line text-sm">
              {m.data?.moves.map((x, k) => (
                <li key={k} className="flex flex-wrap items-center justify-between gap-2 px-5 py-3">
                  <span><b>{x.name}</b> <span className="text-muted">week of {x.week}</span><span className="block text-xs text-muted">{formatINR(x.old_price)} → {formatINR(x.new_price)} ({x.price_pct >= 0 ? "+" : ""}{x.price_pct}%), units {x.units_pct >= 0 ? "+" : ""}{x.units_pct}%</span></span>
                  <span className={`rounded-full px-2.5 py-0.5 text-xs ${x.reliable ? "bg-surface-2" : "bg-haldi/25"}`}>{x.elasticity != null ? `response ${x.elasticity}` : "no response"}{x.reliable ? "" : " · few sales"}</span>
                </li>
              ))}
            </ul>
          </section>
          {m.data?.limits && <p className="rounded-xl bg-surface-2 p-4 text-xs text-muted">{m.data.limits.join(" ")}</p>}
        </>
      )}
    </div>
  );
}
