"use client";

import { useEffect, useState } from "react";
import { download } from "@/lib/api";
import { longDate, num, useApi } from "@/lib/analytics";
import type { CampaignPlan, PlaybookEntry } from "@/lib/campaigns";
import { formatINR, formatNumber } from "@/lib/format";
import { useAnalyticsState, useWorkspace } from "./AppContext";
import { Card, EmptyNote, ErrorNote, Skeleton } from "./analytics/parts";

const KIND_TONE: Record<string, string> = {
  reward: "bg-mor/12 text-mor",
  grow: "bg-haldi/25 text-fg",
  welcome: "bg-mor/12 text-mor",
  nudge: "bg-haldi/25 text-fg",
  winback: "bg-sindoor/10 text-sindoor",
};
const PAGE = 15;

function useDebounced<T>(value: T, ms = 350): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return v;
}

export function CampaignsPage() {
  const { workspace, canImport } = useWorkspace();
  const { dataVersion } = useAnalyticsState();
  const base = `/workspaces/${workspace.id}/campaigns`;
  const book = useApi<PlaybookEntry[]>(`${base}/playbook`, [dataVersion]);
  const [segment, setSegment] = useState<string | null>(null);
  const [maxDisc, setMaxDisc] = useState<number | null>(null);
  const [floor, setFloor] = useState(15);
  const [holdout, setHoldout] = useState(10);
  const [lang, setLang] = useState<"en" | "hinglish">("en");
  const [page, setPage] = useState(0);

  const entry = book.data?.find((e) => e.segment === segment);
  const dMax = useDebounced(maxDisc);
  const dFloor = useDebounced(floor);
  const dHold = useDebounced(holdout);
  const qs = new URLSearchParams({ segment: segment ?? "", margin_floor: String(dFloor), holdout_pct: String(dHold), language: lang });
  if (dMax !== null) qs.set("max_discount", String(dMax));
  const plan = useApi<CampaignPlan>(segment ? `${base}/plan?${qs}&limit=${PAGE}&offset=${page * PAGE}` : null, [dataVersion]);
  const p = plan.data;

  const pick = (s: string) => {
    setSegment(s);
    setMaxDisc(null);
    setPage(0);
  };
  const shownMax = maxDisc ?? entry?.default_max_discount ?? 0;

  return (
    <div className="space-y-5">
      <header>
        <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-sindoor">{workspace.name}</p>
        <h1 className="mt-1 text-3xl font-bold tracking-tight sm:text-4xl">Campaigns</h1>
        <p className="mt-1 text-sm text-muted">Pick a customer group, get a safe offer and ready-to-send messages. Nothing is sent from here: you review, then send it yourself.</p>
      </header>

      <div className="rounded-2xl border border-haldi/50 bg-haldi/15 px-4 py-3 text-sm" role="note">
        <b>Consent first.</b> Only message customers who agreed to hear from you on that channel, and honour every STOP reply. We do not record consent yet, so every customer shows “consent not recorded”.
      </div>

      {book.error && <ErrorNote message={book.error} />}
      {!book.data && book.loading && <Skeleton className="h-64" />}

      {book.data && (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {book.data.map((e) => (
            <button
              key={e.segment}
              type="button"
              aria-pressed={segment === e.segment}
              onClick={() => pick(e.segment)}
              className={`min-w-0 rounded-2xl border p-4 text-left transition-all ${segment === e.segment ? "border-fg bg-fg text-canvas shadow-lg" : "border-line bg-surface hover:-translate-y-0.5 hover:border-fg/40"}`}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="truncate font-semibold">{e.segment}</span>
                <span className={`rounded-full px-2 py-0.5 text-[10px] uppercase ${segment === e.segment ? "bg-canvas/15" : KIND_TONE[e.kind]}`}>{e.kind}</span>
              </div>
              <p className="mt-2 text-3xl font-bold tracking-tight">{formatNumber(e.customers)}</p>
              <p className={`mt-1 text-xs ${segment === e.segment ? "text-canvas/70" : "text-muted"}`}>{e.goal}</p>
            </button>
          ))}
        </div>
      )}

      {!segment && book.data && <EmptyNote>Choose a group above to see who to contact and what to offer.</EmptyNote>}
      {segment && plan.error && <ErrorNote message={plan.error} />}
      {segment && !p && plan.loading && <Skeleton className="h-96" />}

      {segment && p && (
        <div className={`space-y-5 transition-opacity ${plan.loading ? "opacity-60" : ""}`} aria-busy={plan.loading}>
          <Card title={`${p.segment}: ${p.goal}`} subtitle={p.idea}>
            <div className="grid gap-4 lg:grid-cols-4">
              <Slider label="Biggest discount" value={shownMax} min={0} max={30} unit="%" onChange={(v) => { setMaxDisc(v); setPage(0); }} hint="A ceiling, not a target" />
              <Slider label="Keep at least this margin" value={floor} min={0} max={60} unit="%" onChange={(v) => { setFloor(v); setPage(0); }} hint="Offers never go below it" />
              <Slider label="Hold back to measure" value={holdout} min={0} max={30} unit="%" onChange={(v) => { setHoldout(v); setPage(0); }} hint="Not contacted, so we can see the real effect" />
              <div>
                <p className="text-xs text-muted">Language</p>
                <div role="group" aria-label="Message language" className="mt-1.5 flex gap-1 rounded-full border border-line bg-canvas p-0.5">
                  {(["en", "hinglish"] as const).map((l) => (
                    <button key={l} type="button" aria-pressed={lang === l} onClick={() => setLang(l)} className={`flex-1 rounded-full px-3 py-1.5 text-xs ${lang === l ? "bg-fg text-canvas" : "text-fg/65 hover:text-fg"}`}>
                      {l === "en" ? "English" : "Hinglish"}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </Card>

          {p.warnings.length > 0 && (
            <ul className="space-y-1 rounded-2xl border border-haldi/40 bg-haldi/10 px-4 py-3 text-sm" role="note">
              {p.warnings.map((w) => (
                <li key={w}>⚠ {w}</li>
              ))}
            </ul>
          )}

          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <Tile label="Customers in group" value={formatNumber(p.audience.total)} hint={`${formatNumber(p.audience.contact)} to contact · ${formatNumber(p.audience.holdout)} held back`} hero />
            <Tile label="Might buy (assumed)" value={`${num(p.projection.expected_redeemers).toFixed(1)}`} hint={`${num(p.projection.assumed_redemption_pct)}% of those contacted: an assumption`} />
            <Tile label="Sales if they do" value={formatINR(num(p.projection.expected_sales))} hint={`${formatINR(num(p.projection.avg_order_value))} per order`} />
            <Tile label="Discount given" value={formatINR(num(p.projection.expected_discount_given))} hint={`about ${num(p.projection.avg_discount_pct).toFixed(1)}% on average`} />
          </div>
          <p className="text-xs text-muted">{p.projection.note}</p>

          <div className="grid gap-5 xl:grid-cols-[1.4fr_1fr]">
            <Card title="Safe offers" subtitle="Which products can be discounted without dropping below your margin floor">
              {p.offers.length === 0 ? (
                <EmptyNote>No purchases to base an offer on.</EmptyNote>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[34rem] text-sm">
                    <thead>
                      <tr className="text-left font-mono text-[10px] uppercase tracking-wider text-muted">
                        <th className="py-2 pr-3">Product</th>
                        <th className="px-2 text-right">Margin now</th>
                        <th className="px-2 text-right">Offer</th>
                        <th className="w-36 px-2">Margin after</th>
                      </tr>
                    </thead>
                    <tbody>
                      {p.offers.map((o) => (
                        <tr key={o.sku} className="border-t border-line align-middle">
                          <td className="py-2 pr-3">
                            <span className="font-medium">{o.name}</span>
                            <span className="block font-mono text-[11px] text-muted">{o.sku} · {formatINR(num(o.price))}</span>
                          </td>
                          <td className="px-2 text-right font-mono">{o.margin_pct ? `${num(o.margin_pct).toFixed(1)}%` : "no cost"}</td>
                          <td className="px-2 text-right font-mono">
                            {num(o.discount_pct) > 0 ? `${num(o.discount_pct)}% off` : <span className="text-muted">{o.flag === "no_cost" ? "value only" : "no discount"}</span>}
                          </td>
                          <td className="px-2">
                            {o.margin_after_pct ? <MarginBar after={num(o.margin_after_pct)} now={num(o.margin_pct)} floor={p.params.margin_floor} /> : <span className="text-xs text-muted">–</span>}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>

            <Card title="Step by step" subtitle="Start gentle, escalate only if there is no reply">
              <ol className="space-y-2">
                {p.ladder.map((s) => (
                  <li key={s.step} className="flex items-center gap-3 rounded-xl border border-line bg-canvas px-3 py-2.5 text-sm">
                    <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-haldi font-mono text-xs font-bold text-ink">{s.step}</span>
                    <span className="min-w-0 flex-1">
                      <b>{s.name}</b>
                      <span className="block text-xs text-muted">{s.when}</span>
                    </span>
                    <span className="font-mono text-xs">{s.discount_pct > 0 ? `${s.discount_pct}% off` : "no discount"}</span>
                  </li>
                ))}
              </ol>
            </Card>
          </div>

          <Card
            title="Message preview"
            subtitle={`${p.params.valid_days}-day offer · every message ends with an opt-out line`}
          >
            {p.rows.filter((r) => !r.holdout).length === 0 ? (
              <EmptyNote>No customers to message in this group.</EmptyNote>
            ) : (
              <div className="grid gap-3 lg:grid-cols-2">
                {p.rows.filter((r) => !r.holdout).slice(0, 4).map((r) => (
                  <MessageCard key={r.key} text={r.message} who={r.key} why={r.reason} />
                ))}
              </div>
            )}
          </Card>

          <Card
            title="Who to contact"
            subtitle={`${formatNumber(p.total_rows)} customers · timing follows each person's own buying rhythm`}
            action={
              canImport && (
                <button
                  type="button"
                  onClick={() => download(`${base}/export.csv?${qs}`, `campaign-${p.segment.toLowerCase().replace(/[^a-z]+/g, "-")}.csv`)}
                  className="rounded-full bg-fg px-4 py-1.5 text-xs font-semibold text-canvas hover:bg-sindoor"
                >
                  Export contact list (CSV)
                </button>
              )
            }
          >
            <div className="overflow-x-auto">
              <table className="w-full min-w-[40rem] text-sm">
                <thead>
                  <tr className="text-left font-mono text-[10px] uppercase tracking-wider text-muted">
                    <th className="py-2 pr-3">Customer</th>
                    <th className="px-2">Why now</th>
                    <th className="px-2">Product</th>
                    <th className="px-2 text-right">Offer</th>
                    <th className="pl-2">Group</th>
                  </tr>
                </thead>
                <tbody>
                  {p.rows.map((r) => (
                    <tr key={r.key} className="border-t border-line">
                      <td className="py-2 pr-3">
                        <span className="font-mono text-xs">{r.key}</span>
                        <span className="block text-[11px] text-muted">{r.city ?? "–"} · last {longDate(r.last_order)}</span>
                      </td>
                      <td className="px-2 text-xs">{r.reason}</td>
                      <td className="px-2 text-xs">{r.product}</td>
                      <td className="px-2 text-right font-mono text-xs">{num(r.discount_pct) > 0 ? `${num(r.discount_pct)}%` : "–"}</td>
                      <td className="pl-2">
                        <span className={`rounded-full px-2 py-0.5 text-[11px] ${r.holdout ? "bg-surface-2 text-muted" : "bg-mor/12 text-mor"}`}>{r.holdout ? "held back" : "contact"}</span>
                        <span className="ml-1 text-[10px] text-muted">consent not recorded</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="mt-3 flex items-center justify-between text-xs text-muted">
              <span>
                {p.total_rows === 0 ? 0 : page * PAGE + 1}–{Math.min((page + 1) * PAGE, p.total_rows)} of {p.total_rows}
              </span>
              <div className="flex gap-2">
                <button type="button" disabled={page === 0} onClick={() => setPage(page - 1)} className="rounded-full border border-line px-3 py-1 disabled:opacity-40">Previous</button>
                <button type="button" disabled={(page + 1) * PAGE >= p.total_rows} onClick={() => setPage(page + 1)} className="rounded-full border border-line px-3 py-1 disabled:opacity-40">Next</button>
              </div>
            </div>
            <p className="mt-3 text-xs text-muted">{p.consent_note}</p>
          </Card>
        </div>
      )}
    </div>
  );
}

function Tile({ label, value, hint, hero }: { label: string; value: string; hint: string; hero?: boolean }) {
  return (
    <div className={`min-w-0 rounded-2xl border p-4 ${hero ? "border-fg bg-fg text-canvas" : "border-line bg-surface"}`}>
      <p className={`font-mono text-[10px] uppercase tracking-[0.16em] ${hero ? "text-canvas/60" : "text-muted"}`}>{label}</p>
      <p className="mt-1 truncate text-2xl font-bold tracking-tight sm:text-3xl">{value}</p>
      <p className={`mt-1 text-xs ${hero ? "text-canvas/70" : "text-muted"}`}>{hint}</p>
    </div>
  );
}

function Slider({ label, value, min, max, unit, hint, onChange }: { label: string; value: number; min: number; max: number; unit: string; hint: string; onChange: (v: number) => void }) {
  return (
    <label className="block">
      <span className="flex items-baseline justify-between text-xs text-muted">
        {label}
        <b className="font-mono text-sm text-fg">
          {value}
          {unit}
        </b>
      </span>
      <input type="range" min={min} max={max} value={value} onChange={(e) => onChange(Number(e.target.value))} className="mt-2 w-full accent-[var(--color-sindoor)]" />
      <span className="text-[11px] text-muted">{hint}</span>
    </label>
  );
}

/** Margin before and after the offer, against the floor line. */
function MarginBar({ now, after, floor }: { now: number; after: number; floor: number }) {
  const top = Math.max(60, now);
  const pct = (v: number) => `${Math.min(100, Math.max(0, (v / top) * 100))}%`;
  const ok = after >= floor;
  return (
    <div title={`${now.toFixed(1)}% now, ${after.toFixed(1)}% after, floor ${floor}%`}>
      <div className="relative h-2 rounded-full bg-surface-2">
        <div className={`absolute inset-y-0 left-0 rounded-full ${ok ? "bg-mor" : "bg-sindoor"}`} style={{ width: pct(after) }} />
        <div className="absolute -top-0.5 h-3 w-0.5 bg-fg" style={{ left: pct(floor) }} />
      </div>
      <p className={`mt-0.5 text-[11px] ${ok ? "text-mor" : "text-sindoor"}`}>{after.toFixed(1)}%</p>
    </div>
  );
}

function MessageCard({ text, who, why }: { text: string; who: string; why: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard blocked: the text is still selectable */
    }
  };
  return (
    <figure className="rounded-2xl border border-line bg-canvas p-4">
      <div className="rounded-2xl rounded-tl-sm bg-mor/10 px-4 py-3 text-sm leading-relaxed">{text}</div>
      <figcaption className="mt-2 flex items-center justify-between gap-2 text-[11px] text-muted">
        <span className="min-w-0 truncate">
          {who} · {why}
        </span>
        <button type="button" onClick={copy} className="shrink-0 rounded-full border border-line px-3 py-1 text-xs text-fg hover:bg-surface-2">
          {copied ? "Copied" : "Copy"}
        </button>
      </figcaption>
    </figure>
  );
}
