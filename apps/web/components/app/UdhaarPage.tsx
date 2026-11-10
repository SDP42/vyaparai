"use client";

import { useRef, useState, type FormEvent } from "react";
import { ApiError, api, download } from "@/lib/api";
import { useApi } from "@/lib/analytics";
import { formatINR } from "@/lib/format";
import { useT } from "@/lib/i18n";
import { useWorkspace } from "./AppContext";
import { Card, EmptyNote, ErrorNote, Skeleton } from "./analytics/parts";

type Summary = { as_of: string; outstanding: string; parties_owing: number; overdue: string; overdue_pct: number; buckets: Record<string, string>; stalled: number; biggest: { name: string; owed: string; oldest_days: number }[]; has_data: boolean };
type Party = { key: string; name: string; phone: string | null; owed: string; oldest_days: number; last_payment: string | null; behaviour: "paying" | "slow" | "stalled" | "settled" };
type Reminder = { key: string; name: string; owed: string; oldest_days: number; behaviour: string; message: string; has_phone: boolean; whatsapp: string | null };
type Ledger = Party & { entries: { date: string; kind: "credit" | "payment"; amount: string; note: string | null }[] };

const n = (s: string) => Number(s);
const BEH = { paying: ["Paying", "bg-mor/12 text-mor"], slow: ["Slow", "bg-haldi/25"], stalled: ["Not paying", "bg-sindoor/10 text-sindoor"], settled: ["Settled", "bg-surface-2 text-muted"] } as const;
const BUCKET_TONE: Record<string, string> = { "0-30": "bg-mor", "31-60": "bg-haldi", "61-90": "bg-sindoor/70", "90+": "bg-sindoor" };
const LANGS = [["hinglish", "Hinglish"], ["en", "English"], ["hi", "हिन्दी"]] as const;

function AddEntry({ base, onDone }: { base: string; onDone: () => void }) {
  const { t } = useT();
  const [party, setParty] = useState("");
  const [kind, setKind] = useState<"credit" | "payment">("credit");
  const [amount, setAmount] = useState("");
  const [phone, setPhone] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true); setErr(null);
    try { await api(`${base}/entries`, { method: "POST", body: JSON.stringify({ party, kind, amount, phone: phone || null }) }); setParty(""); setAmount(""); setPhone(""); onDone(); }
    catch (x) { setErr(x instanceof ApiError ? x.message : "Could not save"); }
    finally { setBusy(false); }
  };
  const f = "mt-1 w-full rounded-lg border border-line bg-canvas px-3 py-2 text-sm";
  return (
    <Card title={t("udhaar.write")}>
      <form onSubmit={submit} className="space-y-3">
        <div role="radiogroup" aria-label="Entry type" className="flex gap-1 rounded-full border border-line p-1 text-sm">
          {(["credit", "payment"] as const).map((k) => <button key={k} type="button" role="radio" aria-checked={kind === k} onClick={() => setKind(k)} className={`flex-1 rounded-full px-3 py-1.5 ${kind === k ? "bg-fg text-canvas" : "text-fg/65"}`}>{k === "credit" ? t("udhaar.gave") : t("udhaar.got")}</button>)}
        </div>
        <label className="block text-xs text-muted">{t("udhaar.name")}<input className={f} value={party} onChange={(e) => setParty(e.target.value)} maxLength={120} required /></label>
        <div className="grid grid-cols-2 gap-3">
          <label className="block text-xs text-muted">{t("udhaar.amount")}<input className={f} inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value)} required /></label>
          <label className="block text-xs text-muted">Phone (optional)<input className={f} inputMode="tel" value={phone} onChange={(e) => setPhone(e.target.value)} /></label>
        </div>
        {err && <p role="alert" className="text-sm text-sindoor">{err}</p>}
        <button type="submit" disabled={busy || !party.trim() || !amount} className="w-full rounded-full bg-fg px-5 py-2.5 text-sm font-semibold text-canvas hover:bg-sindoor disabled:opacity-50">{busy ? "…" : t("udhaar.save")}</button>
      </form>
    </Card>
  );
}

function ImportCard({ base, onDone }: { base: string; onDone: () => void }) {
  const ref = useRef<HTMLInputElement>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const up = async (file: File) => {
    setBusy(true); setErr(null); setMsg(null);
    const fd = new FormData(); fd.append("file", file);
    try { const r = await api<{ added: number; duplicates: number; rejected_count: number }>(`${base}/import`, { method: "POST", body: fd }); setMsg(`${r.added} entries added${r.duplicates ? `, ${r.duplicates} already there` : ""}${r.rejected_count ? `, ${r.rejected_count} rows not understood` : ""}.`); onDone(); }
    catch (e) { setErr(e instanceof ApiError ? e.message : "Could not read the file"); }
    finally { setBusy(false); if (ref.current) ref.current.value = ""; }
  };
  return (
    <Card title="Bring in your khata" subtitle="A CSV from a ledger app or a sheet: Date, Name, Type (Credit or Payment), Amount; or separate Credit and Payment columns. Phone is optional.">
      <input ref={ref} type="file" accept=".csv,text/csv" className="hidden" onChange={(e) => e.target.files?.[0] && up(e.target.files[0])} />
      <div className="flex flex-wrap gap-2">
        <button type="button" disabled={busy} onClick={() => ref.current?.click()} className="rounded-full bg-fg px-4 py-2 text-sm font-semibold text-canvas hover:bg-sindoor disabled:opacity-60">{busy ? "Reading…" : "Upload ledger"}</button>
        <button type="button" onClick={() => download(`${base}/template.csv`, "udhaar-template.csv")} className="rounded-full border border-line px-4 py-2 text-sm hover:bg-surface-2">Download a template</button>
      </div>
      {msg && <p role="status" className="mt-2 text-sm">{msg}</p>}
      {err && <p role="alert" className="mt-2 text-sm text-sindoor">{err}</p>}
    </Card>
  );
}

function Remind({ base, onClose }: { base: string; onClose: () => void }) {
  const [lang, setLang] = useState<"hinglish" | "en" | "hi">("hinglish");
  const { data, error, loading } = useApi<Reminder[]>(`${base}/reminders?lang=${lang}`, []);
  const [copied, setCopied] = useState<string | null>(null);
  const copy = async (r: Reminder) => { try { await navigator.clipboard.writeText(r.message); setCopied(r.key); } catch { /* ignore */ } };
  return (
    <Card title="Reminders to send" subtitle="Drafts for you to read and send yourself. Nothing is sent automatically. The tone gets firmer as dues get older.">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        {LANGS.map(([k, l]) => <button key={k} type="button" aria-pressed={lang === k} onClick={() => setLang(k)} className={`rounded-full px-3 py-1 text-sm ${lang === k ? "bg-fg text-canvas" : "border border-line hover:bg-surface-2"}`}>{l}</button>)}
        <button type="button" onClick={onClose} className="ml-auto rounded-full px-3 py-1 text-sm text-muted hover:text-fg">Close</button>
      </div>
      {error && <ErrorNote message={error} />}
      {loading && !data && <Skeleton className="h-32" />}
      {data?.length === 0 && <EmptyNote>No one needs a reminder yet. Dues under a week old are left alone.</EmptyNote>}
      <ul className="space-y-3">
        {data?.map((r) => (
          <li key={r.key} className="rounded-xl border border-line bg-canvas p-3">
            <p className="flex flex-wrap justify-between gap-2 text-sm"><b>{r.name}</b><span className="text-muted">{formatINR(n(r.owed))} · {r.oldest_days} days</span></p>
            <p className="mt-2 whitespace-pre-line break-words text-sm text-fg/85">{r.message}</p>
            <div className="mt-2 flex flex-wrap gap-2">
              <button type="button" onClick={() => copy(r)} className="rounded-full border border-line px-3 py-1 text-xs hover:bg-surface-2">{copied === r.key ? "Copied" : "Copy"}</button>
              {r.whatsapp ? <a href={r.whatsapp} target="_blank" rel="noopener noreferrer" className="rounded-full bg-fg px-3 py-1 text-xs font-semibold text-canvas hover:bg-sindoor">Open in WhatsApp</a> : <span className="px-1 py-1 text-xs text-muted">No phone saved</span>}
            </div>
          </li>
        ))}
      </ul>
    </Card>
  );
}

function LedgerView({ base, k, onClose }: { base: string; k: string; onClose: () => void }) {
  const { data, error } = useApi<Ledger>(`${base}/parties/${encodeURIComponent(k)}`, []);
  return (
    <Card title={data?.name ?? "Ledger"} subtitle={data ? `${formatINR(n(data.owed))} owed${data.last_payment ? ` · last payment ${data.last_payment}` : " · no payment yet"}` : undefined}>
      {error && <ErrorNote message={error} />}
      <ul className="divide-y divide-line text-sm">
        {data?.entries.map((e, i) => (
          <li key={i} className="flex flex-wrap justify-between gap-2 py-2">
            <span>{e.date} · {e.kind === "credit" ? "Gave udhaar" : "Got payment"}{e.note ? ` · ${e.note}` : ""}</span>
            <b className={e.kind === "credit" ? "text-sindoor" : "text-mor"}>{e.kind === "credit" ? "+" : "−"}{formatINR(n(e.amount))}</b>
          </li>
        ))}
      </ul>
      <button type="button" onClick={onClose} className="mt-3 rounded-full border border-line px-4 py-1.5 text-sm hover:bg-surface-2">Close</button>
    </Card>
  );
}

export function UdhaarPage() {
  const { workspace, canImport } = useWorkspace();
  const { t } = useT();
  const base = `/workspaces/${workspace.id}/udhaar`;
  const [version, setVersion] = useState(0);
  const [panel, setPanel] = useState<"remind" | string | null>(null);
  const sum = useApi<Summary>(`${base}/summary`, [version]);
  const parties = useApi<Party[]>(`${base}/parties`, [version]);
  const s = sum.data;
  const total = s ? n(s.outstanding) : 0;

  return (
    <div className="space-y-6">
      <header>
        <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">Udhaar</p>
        <h1 className="font-serif text-3xl tracking-tight sm:text-4xl">{t("udhaar.title")}</h1>
        <p className="mt-1 max-w-2xl text-sm text-fg/70">{t("udhaar.intro")}</p>
      </header>

      {sum.error && <ErrorNote message={sum.error} />}
      {!s && sum.loading && <Skeleton className="h-40" />}

      {s && s.has_data && (
        <>
          <section aria-label="Totals" className="fluid [--min:11rem]">
            {[[t("udhaar.total"), formatINR(total), `${s.parties_owing}`], [t("udhaar.old"), formatINR(n(s.overdue)), `${s.overdue_pct.toFixed(0)}%`], [t("udhaar.notPaying"), String(s.stalled), "60+"]].map(([l, v, sub]) => (
              <div key={l} className="rounded-2xl border border-line bg-surface p-4"><p className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted">{l}</p><p className="mt-1 text-3xl font-bold tracking-tight">{v}</p><p className="text-xs text-muted">{sub}</p></div>
            ))}
          </section>

          <section aria-label="Age of dues" className="rounded-2xl border border-line bg-surface p-5">
            <h2 className="font-semibold">How old is it?</h2>
            <div className="mt-3 flex h-4 overflow-hidden rounded-full bg-surface-2" role="img" aria-label={Object.entries(s.buckets).map(([k, v]) => `${k} days: ${formatINR(n(v))}`).join(", ")}>
              {Object.entries(s.buckets).map(([k, v]) => <div key={k} className={`${BUCKET_TONE[k]} transition-[width] duration-700`} style={{ width: `${total ? (100 * n(v)) / total : 0}%` }} />)}
            </div>
            <div className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted">{Object.entries(s.buckets).map(([k, v]) => <span key={k} className="inline-flex items-center gap-1.5"><i className={`h-2.5 w-2.5 rounded-sm ${BUCKET_TONE[k]}`} />{k} days <b className="text-fg">{formatINR(n(v))}</b></span>)}</div>
          </section>
        </>
      )}

      <div className="grid items-start gap-6 lg:grid-cols-[1.4fr_1fr]">
        <div className="space-y-6">
          {panel === "remind" && <Remind base={base} onClose={() => setPanel(null)} />}
          {panel && panel !== "remind" && <LedgerView base={base} k={panel} onClose={() => setPanel(null)} />}
          <section aria-label="People" className="rounded-2xl border border-line bg-surface">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-5 py-3">
              <h2 className="font-semibold">{t("udhaar.first")}</h2>
              {canImport && s?.has_data && <button type="button" onClick={() => setPanel("remind")} className="rounded-full bg-fg px-4 py-1.5 text-xs font-semibold text-canvas hover:bg-sindoor">{t("udhaar.draft")}</button>}
            </div>
            {parties.loading && !parties.data && <Skeleton className="m-4 h-24" />}
            {s && !s.has_data && <div className="p-4"><EmptyNote>No udhaar recorded yet. Write an entry or bring in your khata.</EmptyNote></div>}
            {s?.has_data && parties.data?.length === 0 && <div className="p-4"><EmptyNote>Nobody owes you anything. </EmptyNote></div>}
            <ul className="divide-y divide-line">
              {parties.data?.map((p) => (
                <li key={p.key}>
                  <button type="button" onClick={() => setPanel(p.key)} className="flex w-full flex-wrap items-center justify-between gap-2 px-5 py-3 text-left text-sm hover:bg-surface-2/60">
                    <span className="min-w-0"><span className="block truncate font-medium">{p.name}</span><span className="text-xs text-muted">{p.oldest_days} days old{p.last_payment ? ` · paid ${p.last_payment}` : " · never paid"}</span></span>
                    <span className="flex items-center gap-2"><span className={`rounded-full px-2.5 py-0.5 text-xs ${BEH[p.behaviour][1]}`}>{BEH[p.behaviour][0]}</span><b className="tabular-nums">{formatINR(n(p.owed))}</b></span>
                  </button>
                </li>
              ))}
            </ul>
          </section>
        </div>
        <div className="space-y-6">
          {canImport && <AddEntry base={base} onDone={() => setVersion((v) => v + 1)} />}
          {canImport && <ImportCard base={base} onDone={() => setVersion((v) => v + 1)} />}
        </div>
      </div>
    </div>
  );
}
