"use client";

import Link from "next/link";
import { useState } from "react";
import { ApiError, api } from "@/lib/api";
import { longDate, num, useApi } from "@/lib/analytics";
import type { EffectRow, EventItem, RegionInfo, UpcomingEvent } from "@/lib/events";
import { useWorkspace } from "./AppContext";
import { Card, EmptyNote, ErrorNote, Skeleton } from "./analytics/parts";
import { Tx } from "./Tx";

const DEMAND: Record<string, string> = {
  sweets_dryfruits: "Sweets and dry fruits",
  gifting: "Gifting",
  apparel: "Clothes",
  jewellery: "Jewellery",
  staples: "Staples",
  oil_ghee_sugar: "Oil, ghee, sugar",
  dairy: "Dairy",
  fruits_flowers: "Fruit and flowers",
  fasting_foods: "Fasting foods",
  non_veg_dip: "Non-veg dips",
  firecrackers: "Firecrackers",
  cleaning_household: "Cleaning and household",
  beverages_snacks: "Snacks and drinks",
  electronics: "Electronics",
  travel: "Travel",
  personal_care: "Personal care",
};
const TIER: Record<number, string> = { 1: "Big peak", 2: "Regional peak", 3: "Smaller effect" };
const STATUS: Record<UpcomingEvent["status"], { label: string; tone: string }> = {
  ahead: { label: "Coming", tone: "bg-surface-2 text-muted" },
  ramping: { label: "Demand building", tone: "bg-haldi/25 text-fg" },
  on: { label: "On now", tone: "bg-sindoor/10 text-sindoor" },
  fading: { label: "Winding down", tone: "bg-surface-2 text-muted" },
};
const WINDOWS = [30, 60, 90, 180, 365];

function when(e: EventItem) {
  return e.start === e.end ? longDate(e.start) : `${longDate(e.start)} to ${longDate(e.end)}`;
}
function away(u: UpcomingEvent) {
  const d = u.days_until;
  return d > 1 ? `in ${d} days` : d === 1 ? "tomorrow" : d === 0 ? "today" : u.status === "on" ? "on now" : "just ended";
}

export function EventsPage() {
  const { workspace } = useWorkspace();
  const base = `/workspaces/${workspace.id}/events`;
  const [days, setDays] = useState(90);
  const [cricket, setCricket] = useState(true);
  const [bigOnly, setBigOnly] = useState(false);
  const [version, setVersion] = useState(0);
  const up = useApi<UpcomingEvent[]>(`${base}/upcoming?days=${days}&include_cricket=${cricket}`, [version]);
  const effects = useApi<EffectRow[]>(`${base}/effects`, [version]);
  const region = useApi<RegionInfo>(`${base}/regions`, [version]);
  const rows = (up.data ?? []).filter((u) => !bigOnly || u.event.tier === 1);
  const withEffect = (effects.data ?? []).filter((e) => e.all_products || e.matching_products);

  return (
    <div className="space-y-5">
      <header>
        <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-sindoor">{workspace.name}</p>
        <h1 className="mt-1 text-3xl font-bold tracking-tight sm:text-4xl"><Tx k="h.festivals" /></h1>
        <p className="mt-1 max-w-2xl text-sm text-muted"><Tx k="i.festivals" /></p>
      </header>

      <RegionCard base={base} info={region.data} canEdit={["owner", "admin"].includes(workspace.role)} onSaved={() => setVersion((v) => v + 1)} />

      <div className="flex flex-wrap items-center gap-2 text-xs">
        <div role="group" aria-label="How far ahead" className="flex gap-1 rounded-full border border-line bg-surface p-1">
          {WINDOWS.map((d) => (
            <button key={d} type="button" aria-pressed={days === d} onClick={() => setDays(d)} className={`rounded-full px-3 py-1.5 ${days === d ? "bg-fg text-canvas" : "text-fg/65 hover:text-fg"}`}>
              {d === 365 ? "1 year" : `${d} days`}
            </button>
          ))}
        </div>
        <label className="flex items-center gap-1.5 rounded-full border border-line bg-surface px-3 py-1.5">
          <input type="checkbox" checked={cricket} onChange={(e) => setCricket(e.target.checked)} className="accent-[var(--color-sindoor)]" /> Cricket
        </label>
        <label className="flex items-center gap-1.5 rounded-full border border-line bg-surface px-3 py-1.5">
          <input type="checkbox" checked={bigOnly} onChange={(e) => setBigOnly(e.target.checked)} className="accent-[var(--color-sindoor)]" /> Big peaks only
        </label>
      </div>

      {up.error && <ErrorNote message={up.error} />}
      {!up.data && up.loading && <Skeleton className="h-96" />}
      {up.data && rows.length === 0 && <EmptyNote>Nothing in this window. Try a longer one.</EmptyNote>}

      <ul className="space-y-3">
        {rows.map((u) => (
          <EventCard key={u.event.id} u={u} />
        ))}
      </ul>

      <Card title="What happened before" subtitle="How your sales moved in past events, against the four weeks before each. Only shown when your data had a quiet month before it.">
        {effects.loading && !effects.data ? (
          <Skeleton className="h-24" />
        ) : withEffect.length === 0 ? (
          <p className="text-sm text-muted">Not enough history yet to measure any event. It needs a month of sales before an event and sales during it. As months pass, this fills in and the forecast learns from it.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[30rem] text-sm">
              <thead>
                <tr className="text-left font-mono text-[10px] uppercase tracking-wider text-muted">
                  <th className="py-2 pr-3">Event</th>
                  <th className="px-2 text-right">All products</th>
                  <th className="pl-2 text-right">Products it touches</th>
                </tr>
              </thead>
              <tbody>
                {withEffect.slice(0, 12).map((e) => (
                  <tr key={e.id} className="border-t border-line">
                    <td className="py-2 pr-3">
                      {e.name}
                      <span className="block font-mono text-[11px] text-muted">{longDate(e.start)}</span>
                    </td>
                    <td className="px-2 text-right font-mono">
                      <Ratio v={e.all_products?.ratio} />
                    </td>
                    <td className="pl-2 text-right font-mono">
                      <Ratio v={e.matching_products?.ratio} />
                      {e.matching_count > 0 && <span className="block text-[11px] text-muted">{e.matching_count} products</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      <p className="text-xs text-muted">Dates come from government holiday lists and published almanacs and schedules, each with a confidence level. Lunar dates can shift by a day, and cricket schedules can change. The size of an effect is learned from your own sales; we never assume one.</p>
    </div>
  );
}

function Ratio({ v }: { v: number | undefined }) {
  if (v == null) return <span className="text-muted">–</span>;
  const tone = v >= 1.15 ? "text-mor" : v <= 0.9 ? "text-sindoor" : "text-muted";
  return <span className={tone}>{v.toFixed(2)}×</span>;
}

function EventCard({ u }: { u: UpcomingEvent }) {
  const e = u.event;
  const risky = u.products.filter((p) => p.at_risk);
  return (
    <li className="overflow-hidden rounded-2xl border border-line bg-surface">
      <div className="flex">
        <span aria-hidden className={`w-1.5 shrink-0 ${e.category === "cricket" ? "bg-mor" : e.tier === 1 ? "bg-sindoor" : e.tier === 2 ? "bg-haldi" : "bg-line"}`} />
        <div className="min-w-0 flex-1 p-4">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div className="min-w-0">
              <h2 className="font-semibold leading-snug">{e.name}</h2>
              <p className="font-mono text-[11px] text-muted">{when(e)}</p>
            </div>
            <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
              <span className={`rounded-full px-2 py-0.5 ${STATUS[u.status].tone}`}>{STATUS[u.status].label}</span>
              <span className="rounded-full bg-canvas px-2 py-0.5 font-semibold">{away(u)}</span>
            </div>
          </div>
          <p className="mt-1.5 text-sm text-fg/80">{e.notes}</p>
          <div className="mt-2 flex flex-wrap items-center gap-1.5 text-[11px]">
            <span className="rounded-full bg-canvas px-2 py-0.5">{e.category === "cricket" ? "Cricket" : TIER[e.tier]}</span>
            {e.relevance === "zone" && <span title="Named for other states, but observed in your part of India" className="rounded-full bg-surface-2 px-2 py-0.5 text-muted">Also observed in your zone</span>}
            {e.demand.slice(0, 5).map((d) => (
              <span key={d} className="rounded-full bg-haldi/20 px-2 py-0.5">{DEMAND[d] ?? d}</span>
            ))}
            <span title={`Date basis: ${e.basis}`} className={`rounded-full px-2 py-0.5 ${e.confidence === "high" ? "bg-mor/12 text-mor" : e.confidence === "medium" ? "bg-haldi/25" : "bg-sindoor/10 text-sindoor"}`}>
              date {e.confidence === "high" ? "confirmed" : e.confidence === "medium" ? "likely" : "estimated"}
            </span>
          </div>

          {u.products.length > 0 && (
            <div className="mt-3 rounded-xl bg-canvas p-3">
              <p className="mb-1.5 text-xs text-muted">
                {u.matching_products} of your products fit this event{risky.length > 0 ? `. ${risky.length} may run out before it ends.` : "."}
              </p>
              <ul className="flex flex-wrap gap-1.5">
                {u.products.map((p) => (
                  <li key={p.sku} className={`rounded-lg border px-2 py-1 text-xs ${p.at_risk ? "border-sindoor/40 bg-sindoor/5" : "border-line bg-surface"}`}>
                    <b>{p.name}</b>
                    <span className="ml-1.5 text-muted">
                      {p.cover_days == null ? (p.tracked ? "plenty" : "stock not counted") : `${num(String(p.cover_days)).toFixed(0)}d of stock`}
                    </span>
                    {p.at_risk && <span className="ml-1.5 font-semibold text-sindoor">may run out</span>}
                  </li>
                ))}
              </ul>
              {risky.length > 0 && (
                <Link href="/app/inventory" className="mt-2 inline-block text-xs underline underline-offset-4">
                  See stock and order advice
                </Link>
              )}
            </div>
          )}
          {u.last_time && (u.last_time.matching || u.last_time.all) && (
            <p className="mt-2 text-xs text-muted">
              Last time ({u.last_time.year}): your {u.last_time.matching ? "matching products" : "sales"} ran at <b className="text-fg">{(u.last_time.matching ?? u.last_time.all)!.ratio.toFixed(2)}×</b> the usual level.
            </p>
          )}
        </div>
      </div>
    </li>
  );
}

/** Some festivals belong to certain states or zones, so the shop's state decides what is shown. */
function RegionCard({ base, info, canEdit, onSaved }: { base: string; info: RegionInfo | null; canEdit: boolean; onSaved: () => void }) {
  const [pick, setPick] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  if (!info) return null;
  const save = async () => {
    if (!pick) return;
    setBusy(true);
    setErr(null);
    try {
      await api(`${base}/region`, { method: "PUT", body: JSON.stringify({ state: pick }) });
      setPick("");
      onSaved();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "Could not save");
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className={`rounded-2xl border px-4 py-3 text-sm ${info.state ? "border-line bg-surface" : "border-haldi/40 bg-haldi/10"}`}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p>
          {info.state ? (
            <>
              Showing festivals for <b>{info.state}</b>
              {info.zones.length > 0 && <span className="text-muted"> ({info.zones.join(" and ")} India)</span>}.
            </>
          ) : (
            <>Some festivals are celebrated only in certain states. Tell us your state so we show the right ones.</>
          )}
        </p>
        {canEdit && (
          <div className="flex min-w-0 items-center gap-2">
            <select aria-label="Your state" value={pick} onChange={(e) => setPick(e.target.value)} className="min-w-0 flex-1 rounded-lg border border-line bg-canvas px-2.5 py-1.5 text-sm sm:flex-none">
              <option value="">{info.state ? "Change state" : "Choose your state"}</option>
              {info.states.map((s) => (
                <option key={s.state} value={s.state}>
                  {s.state}
                </option>
              ))}
            </select>
            <button type="button" onClick={save} disabled={!pick || busy} className="shrink-0 rounded-full bg-fg px-4 py-1.5 text-xs font-semibold text-canvas hover:bg-sindoor disabled:opacity-50">
              {busy ? "Saving…" : "Save"}
            </button>
          </div>
        )}
      </div>
      {err && <p className="mt-1 text-xs text-sindoor">{err}</p>}
      {!canEdit && !info.state && <p className="mt-1 text-xs text-muted">Ask an owner or admin to set it.</p>}
    </div>
  );
}
