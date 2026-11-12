"use client";

import { useState } from "react";
import { ApiError, api } from "@/lib/api";
import { useApi } from "@/lib/analytics";
import { parseUtc } from "@/lib/format";
import { useWorkspace } from "./AppContext";
import { Card, EmptyNote, ErrorNote, Skeleton } from "./analytics/parts";
import { Tx } from "./Tx";

type Ev = { label: string; value: string; source: string };
type Finding = { kind: "measured" | "context"; title: string; detail: string; weight: number; evidence: Ev[] };
type Step = { position: number; node: string; status: "ok" | "failed" | "skipped"; attempts: number; ms: number; summary: string; error: string | null; input: unknown; output: unknown };
type Run = { id: string; workflow: string; status: string; params: { from?: string; to?: string }; started_at: string; finished_at: string | null; error: string | null; summary: string | null; result?: { summary: string; findings: Finding[]; notes: string[]; caveat: string; facts?: { drafts?: { name: string; phone: string | null; text: string }[]; order_lists?: { supplier: string | null; text: string; share_url: string }[] } }; steps?: Step[] };

const NODE_LABEL: Record<string, string> = {
  sales: "Last day's sales", money_owed: "Who owes money", shelves: "Shelves, expiry and the galla", need: "What needs ordering", cash: "Check cash on hand", lists: "Write order lists", drafts: "Draft reminders", galla: "Check the galla", spend: "Check spending", sort: "Sort by expiry", leaks: "Find margin leaks",
  overview: "Customer overview", reviews_check: "Check reviews", credit_check: "Check credit", stock: "Check stock levels", festival: "Check upcoming festivals", forecast_check: "Check the forecast", refresh: "Read every signal", alerts: "Read alerts", rank: "Rank suggestions",
  scope: "Choose the periods", headline: "Compare net sales", drivers: "Split the change into effects", movers: "Find the products behind it", stock_check: "Check stock",
  cost_check: "Check costs and supplier prices", discount_check: "Check discounts", calendar_check: "Check the festival calendar", review_check: "Check reviews", customers_check: "Orders or basket size?", conclude: "Rank what was found",
};
const ST = { ok: "bg-mor/12 text-mor", failed: "bg-sindoor/10 text-sindoor", skipped: "bg-surface-2 text-muted" } as const;
const iso = (d: Date) => d.toISOString().slice(0, 10);

function Trace({ steps }: { steps: Step[] }) {
  return (
    <ol className="space-y-2" aria-label="Step by step">
      {steps.map((s) => (
        <li key={s.position} className="rounded-xl border border-line bg-canvas">
          <details>
            <summary className="flex cursor-pointer flex-wrap items-center gap-2 px-3 py-2 text-sm">
              <span className="font-mono text-[10px] text-muted">{String(s.position + 1).padStart(2, "0")}</span>
              <b>{NODE_LABEL[s.node] ?? s.node}</b>
              <span className={`rounded-full px-2 py-0.5 text-[11px] ${ST[s.status]}`}>{s.status}{s.attempts > 1 ? ` · ${s.attempts} tries` : ""}</span>
              {s.summary && <span className="text-xs text-muted">{s.summary}</span>}
              <span className="ml-auto font-mono text-[11px] text-muted">{s.ms} ms</span>
            </summary>
            <div className="space-y-2 border-t border-line px-3 py-2 text-xs">
              {s.error && <p className="text-sindoor">{s.error}</p>}
              <p className="font-mono uppercase tracking-wider text-muted">Output</p>
              <pre className="max-h-56 overflow-auto whitespace-pre-wrap break-words rounded-lg bg-surface p-2">{JSON.stringify(s.output, null, 2)}</pre>
            </div>
          </details>
        </li>
      ))}
    </ol>
  );
}

function Result({ run }: { run: Run }) {
  const r = run.result;
  if (run.status === "failed") return <ErrorNote message={run.error ?? "The investigation failed"} />;
  if (!r) return null;
  return (
    <div className="space-y-5">
      <Card title="What the numbers show" subtitle={run.params.from ? `${run.params.from} → ${run.params.to ?? ""}` : undefined}>
        <p className="text-[15px] leading-relaxed">{r.summary}</p>
        <p className="mt-3 rounded-lg bg-haldi/15 px-3 py-2 text-xs">{r.caveat}</p>
        {r.notes.length > 0 && <ul className="mt-3 list-disc pl-5 text-xs text-muted">{r.notes.map((n) => <li key={n}>{n}</li>)}</ul>}
      </Card>
      {(r.facts?.drafts?.length || r.facts?.order_lists?.length) ? (
        <Card title={r.facts?.drafts?.length ? "Reminders, ready for you to send" : "Order lists, ready for you to send"}>
          <ul className="grid gap-3 md:grid-cols-2">
            {(r.facts?.drafts ?? []).map((d) => (
              <li key={d.name} className="rounded-xl border border-line bg-canvas p-3 text-sm">
                <p className="font-medium">{d.name}{d.phone ? <span className="ml-2 font-mono text-xs text-muted">{d.phone}</span> : null}</p>
                <p className="mt-1.5 whitespace-pre-wrap leading-relaxed text-fg/80">{d.text}</p>
                <button type="button" onClick={() => navigator.clipboard?.writeText(d.text)} className="mt-2 text-xs underline underline-offset-4">Copy</button>
              </li>
            ))}
            {(r.facts?.order_lists ?? []).map((o) => (
              <li key={o.supplier ?? "none"} className="rounded-xl border border-line bg-canvas p-3 text-sm">
                <p className="font-medium">{o.supplier ?? "No supplier yet"}</p>
                <pre className="mt-1.5 whitespace-pre-wrap font-sans leading-relaxed text-fg/80">{o.text}</pre>
                <a href={o.share_url} target="_blank" rel="noopener noreferrer" className="mt-2 inline-block text-xs underline underline-offset-4">Share</a>
              </li>
            ))}
          </ul>
        </Card>
      ) : null}
      <div className="grid items-start gap-5 lg:grid-cols-[1.2fr_1fr] [&>*]:min-w-0">
        <section aria-label="Findings" className="space-y-3">
          <h2 className="font-semibold">Findings, strongest first</h2>
          {r.findings.map((f, i) => (
            <article key={i} className="rounded-2xl border border-line bg-surface p-4">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <h3 className="font-semibold leading-snug">{f.title}</h3>
                <span className={`shrink-0 rounded-full px-2.5 py-0.5 text-[11px] ${f.kind === "measured" ? "bg-mor/12 text-mor" : "bg-haldi/25"}`}>{f.kind === "measured" ? "Measured" : "Worth checking"}</span>
              </div>
              <p className="mt-1 text-sm text-fg/75">{f.detail}</p>
              <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-surface-2" role="img" aria-label={`Weight ${Math.round(f.weight * 100)} percent`}><div className={`h-full ${f.kind === "measured" ? "bg-mor" : "bg-haldi"}`} style={{ width: `${f.weight * 100}%` }} /></div>
              {f.evidence.length > 0 && (
                <dl className="mt-3 divide-y divide-line rounded-lg border border-line bg-canvas text-xs">
                  {f.evidence.map((e, j) => <div key={j} className="grid gap-x-3 px-3 py-1.5 sm:grid-cols-[1fr_auto_auto]"><dt className="text-muted">{e.label}</dt><dd className="font-medium tabular-nums">{e.value}</dd><dd className="font-mono text-[10px] text-muted">{e.source}</dd></div>)}
                </dl>
              )}
            </article>
          ))}
        </section>
        <section aria-label="Trace" className="space-y-3">
          <h2 className="font-semibold">What it did, step by step</h2>
          <p className="text-xs text-muted">Every step calls an existing calculation and is stored. It only reads your data; it never changes anything.</p>
          {run.steps && <Trace steps={run.steps} />}
        </section>
      </div>
    </div>
  );
}

export function InvestigatePage() {
  const { workspace, canImport } = useWorkspace();
  const base = `/workspaces/${workspace.id}/agents`;
  const today = new Date();
  const [from, setFrom] = useState(iso(new Date(today.getTime() - 29 * 86400000)));
  const [to, setTo] = useState(iso(today));
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [run, setRun] = useState<Run | null>(null);
  const [version, setVersion] = useState(0);
  const runs = useApi<Run[]>(`${base}/runs`, [version]);

  const go = async (workflow = "investigate_sales") => {
    setBusy(true); setErr(null);
    try { setRun(await api<Run>(`${base}/runs`, { method: "POST", body: JSON.stringify(workflow === "investigate_sales" ? { workflow, date_from: from, date_to: to } : { workflow }) })); setVersion((v) => v + 1); }
    catch (e) { setErr(e instanceof ApiError ? e.message : "Could not run it"); }
    finally { setBusy(false); }
  };
  const open = async (id: string) => { try { setRun(await api<Run>(`${base}/runs/${id}`)); } catch (e) { setErr(e instanceof ApiError ? e.message : "Could not open it"); } };
  const f = "mt-1 rounded-lg border border-line bg-canvas px-3 py-2 text-sm";

  return (
    <div className="space-y-6">
      <header>
        <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">Investigate</p>
        <h1 className="font-serif text-3xl tracking-tight sm:text-4xl"><Tx k="h.investigate" /></h1>
        <p className="mt-1 max-w-2xl text-sm text-fg/70"><Tx k="i.investigate" /></p>
      </header>

      {err && <ErrorNote message={err} />}
      {canImport ? (
        <Card title="Run an investigation">
          <div className="flex flex-wrap items-end gap-3">
            <label className="text-xs text-muted">From<input type="date" className={`block ${f}`} value={from} onChange={(e) => setFrom(e.target.value)} /></label>
            <label className="text-xs text-muted">To<input type="date" className={`block ${f}`} value={to} onChange={(e) => setTo(e.target.value)} /></label>
            <button type="button" disabled={busy || !from || !to || from > to} onClick={() => go()} className="rounded-full bg-fg px-5 py-2.5 text-sm font-semibold text-canvas hover:bg-sindoor disabled:opacity-50">{busy ? "Working…" : "Investigate"}</button>
            {[["weekly_review", "What should I do this week?"], ["customer_health", "Are my customers healthy?"], ["stock_risk", "Where is stock at risk?"]].map(([k, l]) => <button key={k} type="button" disabled={busy} onClick={() => go(k)} className="rounded-full border border-line px-5 py-2.5 text-sm hover:bg-surface-2 disabled:opacity-50">{l}</button>)}
          </div>
        </Card>
      ) : <EmptyNote>Viewers can read past investigations. Analysts and above can run them.</EmptyNote>}

      <Automations base={base} canRun={canImport} busy={busy} onRun={(k) => go(k)} />

      {run && <Result run={run} />}

      <section aria-label="Past runs" className="rounded-2xl border border-line bg-surface">
        <h2 className="border-b border-line px-5 py-3 font-semibold">Past investigations</h2>
        {runs.loading && !runs.data && <Skeleton className="m-4 h-16" />}
        {runs.data?.length === 0 && <div className="p-4"><EmptyNote>None yet.</EmptyNote></div>}
        <ul className="divide-y divide-line">
          {runs.data?.map((r) => (
            <li key={r.id}>
              <button type="button" onClick={() => open(r.id)} className="flex w-full flex-wrap items-center justify-between gap-2 px-5 py-3 text-left text-sm hover:bg-surface-2/60">
                <span className="min-w-0 flex-1"><span className="block truncate">{r.summary ?? r.error ?? "Running…"}</span><span className="text-xs text-muted">{parseUtc(r.started_at).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}{r.params.from ? ` · ${r.params.from} → ${r.params.to}` : ""}</span></span>
                <span className={`rounded-full px-2.5 py-0.5 text-xs ${r.status === "done" ? ST.ok : ST.failed}`}>{r.status}</span>
              </button>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}


type Auto = { workflow: string; title: string; about: string; enabled: boolean; hour: number; last_run_for: string | null };

/** Automation agents: run one now, or let it run by itself every day at a chosen hour. They only prepare. */
function Automations({ base, canRun, busy, onRun }: { base: string; canRun: boolean; busy: boolean; onRun: (k: string) => void }) {
  const { workspace } = useWorkspace();
  const [version, setVersion] = useState(0);
  const list = useApi<Auto[]>(`${base}/schedule`, [version]);
  const admin = ["owner", "admin"].includes(workspace.role);
  const save = (a: Auto, enabled: boolean, hour: number) =>
    api(`${base}/schedule`, { method: "PUT", body: JSON.stringify({ workflow: a.workflow, enabled, hour }) }).then(() => setVersion((v) => v + 1));
  return (
    <Card title="Daily helpers" subtitle="Each one prepares findings and drafts for you to check. They never send, order or change anything.">
      {list.error && <ErrorNote message={list.error} />}
      <ul className="grid gap-3 md:grid-cols-2">
        {list.data?.map((a) => (
          <li key={a.workflow} className="flex flex-col rounded-2xl border border-line bg-canvas p-4">
            <p className="font-semibold">{a.title}</p>
            <p className="mt-1 flex-1 text-sm text-fg/70">{a.about}</p>
            <div className="mt-3 flex flex-wrap items-center gap-2 text-sm">
              {canRun && <button type="button" disabled={busy} onClick={() => onRun(a.workflow)} className="rounded-full bg-fg px-4 py-1.5 font-semibold text-canvas hover:bg-sindoor disabled:opacity-50">Run now</button>}
              <label className="inline-flex items-center gap-2">
                <input type="checkbox" checked={a.enabled} disabled={!admin} onChange={(e) => save(a, e.target.checked, a.hour)} className="h-4 w-4" />
                Every day at
              </label>
              <label className="sr-only" htmlFor={`h-${a.workflow}`}>Hour for {a.title}</label>
              <select id={`h-${a.workflow}`} value={a.hour} disabled={!admin} onChange={(e) => save(a, a.enabled, Number(e.target.value))} className="rounded-lg border border-line bg-surface px-2 py-1">
                {Array.from({ length: 24 }, (_, h) => <option key={h} value={h}>{String(h).padStart(2, "0")}:00</option>)}
              </select>
              {a.last_run_for && <span className="text-xs text-muted">last ran {a.last_run_for}</span>}
            </div>
          </li>
        ))}
      </ul>
    </Card>
  );
}
