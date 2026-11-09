"use client";

import Link from "next/link";
import { useState } from "react";
import { ApiError, api } from "@/lib/api";
import { longDate, useApi } from "@/lib/analytics";
import type { AlertItem, AlertList, AlertStatus, Severity } from "@/lib/alerts";
import { formatINR } from "@/lib/format";
import { useWorkspace } from "./AppContext";
import { EmptyNote, ErrorNote, Skeleton } from "./analytics/parts";

const SEV: Record<Severity, { label: string; bar: string; chip: string }> = {
  high: { label: "Needs attention", bar: "bg-sindoor", chip: "bg-sindoor/10 text-sindoor" },
  medium: { label: "Worth a look", bar: "bg-haldi", chip: "bg-haldi/25 text-fg" },
  info: { label: "Good to know", bar: "bg-line", chip: "bg-surface-2 text-muted" },
};
const TABS: { key: AlertStatus; label: string }[] = [
  { key: "open", label: "Open" },
  { key: "dismissed", label: "Dismissed" },
  { key: "resolved", label: "Resolved" },
];
const p = (v: number | null | undefined, d = 1) => (v == null ? "–" : `${v > 0 ? "+" : ""}${v.toFixed(d)}%`);
const r = (v: number | null | undefined) => (v == null ? "–" : formatINR(v));

/** The few numbers behind each alert, so the owner can judge it without trusting a label. */
function chips(a: AlertItem): [string, string][] {
  const e = a.evidence;
  switch (a.rule) {
    case "sales_drop":
    case "sales_spike":
      return [["That day", r(e.actual)], ["Usual", r(e.expected)], ["Change", p(e.change_pct, 0)]];
    case "week_drop":
      return [["Last 7 days", r(e.week)], ["Usual week", r(e.expected)], ["Change", p(e.change_pct, 0)]];
    case "margin_leak":
      return [["Cost", p(e.cost_change_pct)], ["Price", p(e.price_change_pct)], ["Margin", `${e.margin_prev_pct?.toFixed(1)}% → ${e.margin_now_pct?.toFixed(1)}%`], ["Lost", r(e.leak_amount)], ["Suggested price", r(e.suggested_price)]];
    case "discount_creep":
      return [["Now", `${e.now_pct?.toFixed(1)}%`], ["Before", `${e.before_pct?.toFixed(1)}%`]];
    case "product_stopped":
      return [["Selling days before", String(e.selling_days_before)], ["Units before", String(Math.round(e.units_before ?? 0))]];
    case "lapsed_regulars":
      return [["Customers", String(e.customers)]];
    case "no_costs":
      return [["Units with a cost", `${e.coverage_pct?.toFixed(0)}%`]];
    case "data_stale":
      return [["Days old", String(e.days_old)]];
    default:
      return [];
  }
}

export function AlertsPage() {
  const { workspace, canImport } = useWorkspace();
  const base = `/workspaces/${workspace.id}/alerts`;
  const [tab, setTab] = useState<AlertStatus>("open");
  const [version, setVersion] = useState(0);
  const [err, setErr] = useState<string | null>(null);
  const { data, error, loading } = useApi<AlertList>(`${base}?status=${tab}`, [version]);

  const act = async (a: AlertItem, what: "dismiss" | "reopen") => {
    setErr(null);
    try {
      await api(`${base}/${a.id}/${what}`, { method: "POST" });
      setVersion((v) => v + 1);
      window.dispatchEvent(new Event("vyapar:alerts-changed"));
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "Something went wrong");
    }
  };

  const total = (data?.counts.high ?? 0) + (data?.counts.medium ?? 0) + (data?.counts.info ?? 0);
  return (
    <div className="space-y-5">
      <header>
        <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-sindoor">{workspace.name}</p>
        <h1 className="mt-1 text-3xl font-bold tracking-tight sm:text-4xl">Alerts</h1>
        <p className="mt-1 text-sm text-muted">
          What changed that you should know about: sales that fell, costs that rose, discounts that crept up, products that stopped selling.
          {data?.as_of ? ` Checked against sales up to ${longDate(data.as_of)}.` : ""}
        </p>
      </header>

      <div className="grid grid-cols-3 gap-3">
        {(["high", "medium", "info"] as const).map((s) => (
          <div key={s} className={`rounded-2xl border p-4 ${s === "high" && (data?.counts.high ?? 0) > 0 ? "border-sindoor/40 bg-sindoor/5" : "border-line bg-surface"}`}>
            <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted">{SEV[s].label}</p>
            <p className="mt-1 text-3xl font-bold tracking-tight">{data?.counts[s] ?? "–"}</p>
          </div>
        ))}
      </div>

      <div role="tablist" aria-label="Alert status" className="flex gap-1 rounded-full border border-line bg-surface p-1 w-fit">
        {TABS.map((t) => (
          <button key={t.key} role="tab" aria-selected={tab === t.key} onClick={() => setTab(t.key)} className={`rounded-full px-4 py-1.5 text-sm ${tab === t.key ? "bg-fg text-canvas" : "text-fg/65 hover:text-fg"}`}>
            {t.label}
          </button>
        ))}
      </div>

      {(error || err) && <ErrorNote message={(error ?? err) as string} />}
      {!data && loading && <Skeleton className="h-64" />}

      {data && data.items.length === 0 && (
        <EmptyNote>{tab === "open" ? (total === 0 ? "All clear. Nothing needs your attention right now." : "Nothing open.") : `No ${tab} alerts.`}</EmptyNote>
      )}

      <ul className={`space-y-3 transition-opacity ${loading ? "opacity-60" : ""}`}>
        {data?.items.map((a) => (
          <li key={a.id} className="flex overflow-hidden rounded-2xl border border-line bg-surface">
            <span aria-hidden className={`w-1.5 shrink-0 ${SEV[a.severity].bar}`} />
            <div className="min-w-0 flex-1 p-4">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <h2 className="min-w-0 font-semibold leading-snug">{a.title}</h2>
                <span className={`shrink-0 rounded-full px-2 py-0.5 text-[11px] ${SEV[a.severity].chip}`}>{SEV[a.severity].label}</span>
              </div>
              <p className="mt-1 text-sm text-fg/75">{a.detail}</p>
              <dl className="mt-3 flex flex-wrap gap-2">
                {chips(a).map(([k, v]) => (
                  <div key={k} className="rounded-lg bg-canvas px-2.5 py-1">
                    <dt className="font-mono text-[10px] uppercase tracking-wider text-muted">{k}</dt>
                    <dd className="text-sm font-semibold">{v}</dd>
                  </div>
                ))}
              </dl>
              <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
                <Link href={a.link} className="rounded-full bg-fg px-3.5 py-1.5 font-semibold text-canvas hover:bg-sindoor">
                  Look into it
                </Link>
                {canImport && a.status === "open" && (
                  <button type="button" onClick={() => act(a, "dismiss")} className="rounded-full border border-line px-3.5 py-1.5 hover:bg-surface-2">
                    Dismiss
                  </button>
                )}
                {canImport && a.status === "dismissed" && (
                  <button type="button" onClick={() => act(a, "reopen")} className="rounded-full border border-line px-3.5 py-1.5 hover:bg-surface-2">
                    Bring back
                  </button>
                )}
                <span className="text-muted">First seen {longDate(a.first_seen)}</span>
              </div>
            </div>
          </li>
        ))}
      </ul>
      <p className="text-xs text-muted">Alerts come from fixed rules, not guesses: a day is compared with the same weekday over the last 8 weeks, and the numbers above show exactly what was compared. Dismissed alerts stay hidden for as long as the problem lasts.</p>
    </div>
  );
}
