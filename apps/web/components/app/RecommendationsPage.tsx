"use client";

import Link from "next/link";
import { useState } from "react";
import { ApiError, api } from "@/lib/api";
import { useApi } from "@/lib/analytics";
import { formatINR } from "@/lib/format";
import { useWorkspace } from "./AppContext";
import { EmptyNote, ErrorNote, Skeleton } from "./analytics/parts";

type Ev = { label: string; value: string; source: string };
type Impact = { low: number | null; expected: number | null; high: number | null; basis: string; assumptions: string[]; measured: boolean };
type Outcome = { verdict: string; metric?: string; before?: number; after?: number; change_pct?: number | null; days?: number; money?: boolean; caveat?: string; note?: string };
type Rec = { done_at?: string | null; outcome?: Outcome | null; id: string; kind: string; title: string; why: string; evidence: Ev[]; impact: Impact; effort: "S" | "M" | "L"; confidence: "high" | "medium" | "low"; score: number; link: string; status: string; note: string | null; last_seen: string };
type Summary = { counts: Record<string, number>; proposed_impact: { low: number; expected: number; high: number; unestimated: number } };

const TABS = [["proposed", "To decide"], ["approved", "To do"], ["done", "Done"], ["dismissed", "Dismissed"], ["stale", "No longer needed"]] as const;
const EFFORT = { S: "A few minutes", M: "An afternoon", L: "Several days" } as const;
const CONF = { high: "bg-mor/12 text-mor", medium: "bg-haldi/25", low: "bg-surface-2 text-muted" } as const;

function Card({ r, onAct, canAct, busy }: { r: Rec; onAct: (a: string, id: string) => void; canAct: boolean; busy: boolean }) {
  const i = r.impact;
  return (
    <article className="rounded-2xl border border-line bg-surface p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <h3 className="max-w-3xl font-semibold leading-snug">{r.title}</h3>
        <div className="text-right">
          {i.expected != null ? (
            <>
              <p className="text-xl font-bold tabular-nums">{formatINR(i.expected)}</p>
              <p className="text-[11px] text-muted">likely, between {formatINR(i.low ?? 0)} and {formatINR(i.high ?? 0)}</p>
            </>
          ) : <p className="text-sm text-muted">Impact not estimated</p>}
        </div>
      </div>
      <p className="mt-2 text-sm text-fg/75">{r.why}</p>
      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
        <span className={`rounded-full px-2.5 py-0.5 ${CONF[r.confidence]}`}>{r.confidence} confidence</span>
        <span className="rounded-full border border-line px-2.5 py-0.5">{EFFORT[r.effort]}</span>
        {i.expected != null && <span className={`rounded-full px-2.5 py-0.5 ${i.measured ? "bg-mor/12 text-mor" : "bg-haldi/25"}`}>{i.measured ? "From your numbers" : "Includes an assumption"}</span>}
      </div>
      <details className="mt-3 rounded-xl border border-line bg-canvas text-sm">
        <summary className="cursor-pointer px-3 py-2 font-medium">Why, and how the figure was worked out</summary>
        <div className="space-y-2 border-t border-line px-3 py-2">
          {i.basis && <p className="text-xs"><b>Basis:</b> {i.basis}</p>}
          {i.assumptions.length > 0 && <ul className="list-disc pl-5 text-xs text-muted">{i.assumptions.map((a) => <li key={a}>{a}</li>)}</ul>}
          <dl className="divide-y divide-line rounded-lg border border-line text-xs">
            {r.evidence.map((e, k) => <div key={k} className="grid gap-x-3 px-3 py-1.5 sm:grid-cols-[1.2fr_1fr_auto]"><dt>{e.label}</dt><dd className="font-medium tabular-nums">{e.value}</dd><dd className="font-mono text-[10px] text-muted">{e.source}</dd></div>)}
          </dl>
        </div>
      </details>
      {r.note && <p className="mt-2 text-xs text-muted">Note: {r.note}</p>}
      {r.status === "done" && (
        <div className="mt-3 rounded-xl border border-line bg-canvas p-3 text-sm">
          {!r.outcome && <p className="text-muted">Done {r.done_at}. The result is read two weeks later.</p>}
          {r.outcome && r.outcome.verdict === "not_measurable" && <p className="text-muted">{r.outcome.note}</p>}
          {r.outcome && r.outcome.verdict !== "not_measurable" && (
            <>
              <p><b className={r.outcome.verdict === "improved" ? "text-mor" : r.outcome.verdict === "worse" ? "text-sindoor" : ""}>{r.outcome.verdict === "improved" ? "Improved" : r.outcome.verdict === "worse" ? "Got worse" : "No change"}</b>: {r.outcome.metric} went from {r.outcome.money ? formatINR(r.outcome.before ?? 0) : r.outcome.before} to {r.outcome.money ? formatINR(r.outcome.after ?? 0) : r.outcome.after} in {r.outcome.days} days.</p>
              <p className="mt-1 text-xs text-muted">{r.outcome.caveat}</p>
            </>
          )}
        </div>
      )}
      <div className="mt-4 flex flex-wrap gap-2">
        <Link href={r.link} className="rounded-full border border-line px-4 py-1.5 text-sm hover:bg-surface-2">Open the page →</Link>
        {canAct && r.status === "proposed" && <><button type="button" disabled={busy} onClick={() => onAct("approve", r.id)} className="rounded-full bg-fg px-4 py-1.5 text-sm font-semibold text-canvas hover:bg-sindoor disabled:opacity-50">I will do this</button><button type="button" disabled={busy} onClick={() => onAct("dismiss", r.id)} className="rounded-full px-4 py-1.5 text-sm text-muted hover:text-fg">Not now</button></>}
        {canAct && r.status === "approved" && <><button type="button" disabled={busy} onClick={() => onAct("done", r.id)} className="rounded-full bg-mor px-4 py-1.5 text-sm font-semibold text-canvas disabled:opacity-50">Mark done</button><button type="button" disabled={busy} onClick={() => onAct("dismiss", r.id)} className="rounded-full px-4 py-1.5 text-sm text-muted hover:text-fg">Drop it</button></>}
        {canAct && ["done", "dismissed"].includes(r.status) && <button type="button" disabled={busy} onClick={() => onAct("reopen", r.id)} className="rounded-full border border-line px-4 py-1.5 text-sm hover:bg-surface-2">Reopen</button>}
      </div>
    </article>
  );
}

export function RecommendationsPage() {
  const { workspace, canImport } = useWorkspace();
  const base = `/workspaces/${workspace.id}/recommendations`;
  const [tab, setTab] = useState<(typeof TABS)[number][0]>("proposed");
  const [version, setVersion] = useState(0);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const list = useApi<Rec[]>(`${base}?status=${tab}`, [version]);
  const sum = useApi<Summary>(`${base}/summary`, [version]);

  const act = async (a: string, id: string) => {
    setBusy(true); setErr(null);
    try { await api(`${base}/${id}/${a}`, { method: "POST", body: JSON.stringify({}) }); setVersion((v) => v + 1); }
    catch (e) { setErr(e instanceof ApiError ? e.message : "Could not save that"); }
    finally { setBusy(false); }
  };
  const refresh = async () => {
    setBusy(true); setErr(null);
    try { await api(`${base}/refresh`, { method: "POST" }); setVersion((v) => v + 1); }
    catch (e) { setErr(e instanceof ApiError ? e.message : "Could not refresh"); }
    finally { setBusy(false); }
  };
  const pi = sum.data?.proposed_impact;

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">Recommendations</p>
          <h1 className="font-serif text-3xl tracking-tight sm:text-4xl">What is worth doing next</h1>
          <p className="mt-1 max-w-2xl text-sm text-fg/70">Ranked by likely value, how sure we are, and how much effort it takes. Nothing happens until you choose, and every figure shows how it was worked out.</p>
        </div>
        {canImport && <button type="button" onClick={refresh} disabled={busy} className="rounded-full bg-fg px-5 py-2.5 text-sm font-semibold text-canvas hover:bg-sindoor disabled:opacity-50">{busy ? "Working…" : "Look again"}</button>}
      </header>

      {err && <ErrorNote message={err} />}

      {pi && tab === "proposed" && (pi.expected > 0 || pi.unestimated > 0) && (
        <section aria-label="Total" className="rounded-2xl border border-line bg-surface p-5">
          <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted">If you did everything waiting</p>
          <p className="mt-1 text-3xl font-bold tracking-tight">{formatINR(pi.expected)} <span className="text-base font-normal text-muted">likely, {formatINR(pi.low)} to {formatINR(pi.high)}</span></p>
          <p className="mt-1 text-xs text-muted">An estimate with stated assumptions, not a promise.{pi.unestimated > 0 && ` ${pi.unestimated} item${pi.unestimated > 1 ? "s are" : " is"} not counted because the data cannot support a figure.`}</p>
        </section>
      )}

      <div role="tablist" aria-label="Status" className="flex w-fit max-w-full gap-1 overflow-x-auto rounded-full border border-line bg-surface p-1">
        {TABS.map(([k, l]) => <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)} className={`whitespace-nowrap rounded-full px-4 py-1.5 text-sm ${tab === k ? "bg-fg text-canvas" : "text-fg/65 hover:text-fg"}`}>{l}{sum.data && sum.data.counts[k] ? ` · ${sum.data.counts[k]}` : ""}</button>)}
      </div>

      {list.error && <ErrorNote message={list.error} />}
      {!list.data && list.loading && <Skeleton className="h-48" />}
      {list.data?.length === 0 && <EmptyNote>{tab === "proposed" ? "Nothing waiting. Press “Look again” after you add stock counts, bills or udhaar entries." : "Nothing here."}</EmptyNote>}
      <div className={`space-y-4 transition-opacity ${list.loading ? "opacity-60" : ""}`}>
        {list.data?.map((r) => <Card key={r.id} r={r} onAct={act} canAct={canImport} busy={busy} />)}
      </div>
    </div>
  );
}
