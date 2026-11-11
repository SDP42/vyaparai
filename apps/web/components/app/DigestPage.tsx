"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ApiError, api } from "@/lib/api";
import { longDate, num, useApi } from "@/lib/analytics";
import type { DigestKind, DigestPreview, DigestRow, DigestSettings } from "@/lib/digest";
import { useWorkspace } from "./AppContext";
import { Card, ErrorNote, Skeleton } from "./analytics/parts";
import { Tx } from "./Tx";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const STATUS: Record<string, string> = {
  sent: "bg-mor/12 text-mor",
  stored: "bg-surface-2 text-muted",
  not_configured: "bg-haldi/25 text-fg",
  failed: "bg-sindoor/10 text-sindoor",
};
const STATUS_LABEL: Record<string, string> = { sent: "Emailed", stored: "Saved", not_configured: "Email not set up", failed: "Failed" };

export function DigestPage() {
  const { workspace, canImport } = useWorkspace();
  const base = `/workspaces/${workspace.id}/digests`;
  const canEdit = ["owner", "admin"].includes(workspace.role);
  const [kind, setKind] = useState<DigestKind>("daily");
  const [version, setVersion] = useState(0);
  const preview = useApi<DigestPreview>(`${base}/preview?kind=${kind}`, []);
  const settings = useApi<DigestSettings>(`${base}/settings`, [version]);
  const history = useApi<DigestRow[]>(`${base}/history`, [version]);
  const p = preview.data;

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-sindoor">{workspace.name}</p>
          <h1 className="mt-1 text-3xl font-bold tracking-tight sm:text-4xl"><Tx k="h.digest" /></h1>
          <p className="mt-1 text-sm text-muted"><Tx k="i.digest" /></p>
        </div>
        <div role="group" aria-label="Summary type" className="flex gap-1 rounded-full border border-line bg-surface p-1">
          {(["daily", "weekly"] as const).map((k) => (
            <button key={k} type="button" aria-pressed={kind === k} onClick={() => setKind(k)} className={`rounded-full px-4 py-1.5 text-sm ${kind === k ? "bg-fg text-canvas" : "text-fg/65 hover:text-fg"}`}>
              {k === "daily" ? "Daily" : "Weekly"}
            </button>
          ))}
        </div>
      </header>

      {preview.error && <ErrorNote message={preview.error} />}
      {!p && preview.loading && <Skeleton className="h-96" />}

      {p && (
        <div className="grid gap-5 xl:grid-cols-[1.25fr_1fr]">
          <div className="space-y-5">
            <section className="rounded-3xl border border-line bg-surface p-5 sm:p-7" aria-label="Summary preview">
              <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">
                {kind === "daily" ? "Daily" : "Weekly"} · {p.label}
              </p>
              <div className="mt-4 grid gap-3 sm:grid-cols-3">
                {p.headline.map((h) => (
                  <HeadlineTile key={h.key} h={h} versus={p.versus} />
                ))}
              </div>
              <div className="mt-5 rounded-2xl border border-haldi/50 bg-haldi/15 p-4">
                <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-haldi-deep">Do this</p>
                <p className="mt-1 text-lg font-bold leading-snug">{p.action.title}</p>
                <p className="mt-1 text-sm text-fg/75">{p.action.detail}</p>
                <Link href={p.action.link} className="mt-3 inline-block rounded-full bg-fg px-4 py-1.5 text-sm font-semibold text-canvas hover:bg-sindoor">
                  Open
                </Link>
              </div>
              {p.more_actions.length > 0 && (
                <p className="mt-3 text-sm text-muted">
                  <b className="text-fg">Also:</b> {p.more_actions.map((a) => a.title).join("; ")}
                </p>
              )}
              {p.watch && <p className="mt-3 text-sm">{p.watch}</p>}
              {p.notes.map((n) => (
                <p key={n} className="mt-2 rounded-lg bg-surface-2 px-3 py-2 text-xs text-muted">
                  {n}
                </p>
              ))}
            </section>
            <MessageCard text={p.text} />
          </div>

          <div className="space-y-5">
            <Delivery base={base} settings={settings.data} kind={kind} canEdit={canEdit} canSend={canImport} onChanged={() => setVersion((v) => v + 1)} />
          </div>
        </div>
      )}

      <Card title="Sent and saved" subtitle="Every summary that was generated for your shop">
        {history.data && history.data.length === 0 && <p className="text-sm text-muted">Nothing yet. Turn on delivery or press “Send now”.</p>}
        <ul className="divide-y divide-line">
          {history.data?.map((h) => (
            <li key={h.id}>
              <details className="py-2.5">
                <summary className="flex cursor-pointer flex-wrap items-center justify-between gap-2 text-sm">
                  <span className="min-w-0 truncate">{h.subject}</span>
                  <span className="flex items-center gap-2">
                    <span className="font-mono text-[11px] text-muted">{longDate(h.period_end)}</span>
                    <span className={`rounded-full px-2 py-0.5 text-[11px] ${STATUS[h.status] ?? ""}`}>{STATUS_LABEL[h.status] ?? h.status}</span>
                  </span>
                </summary>
                <pre className="mt-2 whitespace-pre-wrap rounded-xl bg-canvas p-3 font-sans text-xs text-fg/80">{h.text}</pre>
                {h.error && <p className="mt-1 text-xs text-sindoor">{h.error}</p>}
              </details>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}

function HeadlineTile({ h, versus }: { h: DigestPreview["headline"][number]; versus: string }) {
  const c = h.change == null ? null : num(h.change);
  const up = c != null && c > 0;
  const down = c != null && c < 0;
  return (
    <div className="min-w-0 rounded-2xl border border-line bg-canvas p-4">
      <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted">{h.label}</p>
      <p className="mt-1 truncate text-3xl font-bold tracking-tight">{h.value}</p>
      <p className={`mt-1 text-xs ${up ? "text-mor" : down ? "text-sindoor" : "text-muted"}`}>
        {c == null ? "no comparison" : `${up ? "▲" : down ? "▼" : "■"} ${Math.abs(c)}${h.unit === "pct" ? "%" : " pts"} ${versus}`}
      </p>
    </div>
  );
}

/** The plain text a phone message would carry, with a copy button. */
function MessageCard({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard blocked: the text stays selectable */
    }
  };
  return (
    <Card
      title="As a message"
      subtitle="Paste it into WhatsApp or SMS yourself, or let us email it"
      action={
        <button type="button" onClick={copy} className="rounded-full border border-line px-3 py-1.5 text-xs hover:bg-surface-2">
          {copied ? "Copied" : "Copy text"}
        </button>
      }
    >
      <pre className="whitespace-pre-wrap rounded-2xl rounded-tl-sm bg-mor/10 p-4 font-sans text-sm leading-relaxed">{text}</pre>
    </Card>
  );
}

function Delivery({ base, settings, kind, canEdit, canSend, onChanged }: { base: string; settings: DigestSettings | null; kind: DigestKind; canEdit: boolean; canSend: boolean; onChanged: () => void }) {
  const [form, setForm] = useState<DigestSettings | null>(null);
  const [recips, setRecips] = useState("");
  const [msg, setMsg] = useState<{ tone: "ok" | "err"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (settings) {
      setForm(settings);
      setRecips(settings.recipients.join(", "));
    }
  }, [settings]);
  if (!form) return <Skeleton className="h-72" />;
  const input = "rounded-lg border border-line bg-surface px-2.5 py-1.5 text-sm disabled:opacity-60";
  const parsed = recips.split(/[,\s;]+/).map((s) => s.trim()).filter(Boolean);

  const save = async () => {
    setBusy(true);
    setMsg(null);
    try {
      await api(`${base}/settings`, { method: "PUT", body: JSON.stringify({ enabled: form.enabled, frequency: form.frequency, send_hour: form.send_hour, weekday: form.weekday, recipients: parsed }) });
      setMsg({ tone: "ok", text: "Saved." });
      onChanged();
    } catch (e) {
      setMsg({ tone: "err", text: e instanceof ApiError ? (e.status === 422 ? "Check the email addresses (up to 5) and the time." : e.message) : "Could not save" });
    } finally {
      setBusy(false);
    }
  };
  const sendNow = async () => {
    setBusy(true);
    setMsg(null);
    try {
      const r = await api<DigestRow>(`${base}/send-now?kind=${kind}`, { method: "POST" });
      setMsg(r.status === "sent" ? { tone: "ok", text: `Emailed to ${r.sent_to.join(", ")}.` } : { tone: "err", text: r.status === "not_configured" ? "Saved, but email is not set up on this server. Copy the text instead." : (r.error ?? "It could not be sent.") });
      onChanged();
    } catch (e) {
      setMsg({ tone: "err", text: e instanceof ApiError ? e.message : "Could not send" });
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card title="Delivery" subtitle={`Times are in ${form.timezone}`}>
      {!form.email_configured && <p className="mb-3 rounded-xl border border-haldi/40 bg-haldi/10 px-3 py-2 text-xs">Email sending is not set up on this server yet, so summaries are saved and can be copied. An admin sets the mail server in the API settings.</p>}
      <div className="space-y-3 text-sm">
        <label className="flex items-center justify-between gap-3">
          <span>Send me this automatically</span>
          <input type="checkbox" checked={form.enabled} disabled={!canEdit} onChange={(e) => setForm({ ...form, enabled: e.target.checked })} className="h-5 w-5 accent-[var(--color-sindoor)]" />
        </label>
        <div className="grid grid-cols-2 gap-3">
          <label className="block text-xs text-muted">
            How often
            <select className={`${input} mt-1 w-full`} disabled={!canEdit} value={form.frequency} onChange={(e) => setForm({ ...form, frequency: e.target.value as DigestSettings["frequency"] })}>
              <option value="daily">Every day</option>
              <option value="weekly">Every week</option>
              <option value="both">Daily and weekly</option>
            </select>
          </label>
          <label className="block text-xs text-muted">
            At
            <select className={`${input} mt-1 w-full`} disabled={!canEdit} value={form.send_hour} onChange={(e) => setForm({ ...form, send_hour: Number(e.target.value) })}>
              {Array.from({ length: 24 }, (_, h) => (
                <option key={h} value={h}>
                  {String(h).padStart(2, "0")}:00
                </option>
              ))}
            </select>
          </label>
        </div>
        {form.frequency !== "daily" && (
          <label className="block text-xs text-muted">
            Weekly summary goes out on
            <select className={`${input} mt-1 w-full`} disabled={!canEdit} value={form.weekday} onChange={(e) => setForm({ ...form, weekday: Number(e.target.value) })}>
              {DAYS.map((d, i) => (
                <option key={d} value={i}>
                  {d}
                </option>
              ))}
            </select>
          </label>
        )}
        <label className="block text-xs text-muted">
          Email to (up to 5, separated by commas)
          <input className={`${input} mt-1 w-full`} disabled={!canEdit} value={recips} onChange={(e) => setRecips(e.target.value)} placeholder="owner@yourshop.in" />
        </label>
        <p className="text-[11px] text-muted">Summaries contain totals and product names only, never customer names or numbers.</p>
        {canEdit ? (
          <div className="flex flex-wrap gap-2 pt-1">
            <button type="button" onClick={save} disabled={busy} className="rounded-full bg-fg px-4 py-2 text-sm font-semibold text-canvas hover:bg-sindoor disabled:opacity-60">
              Save
            </button>
            <button type="button" onClick={sendNow} disabled={busy || parsed.length === 0 || !canSend} className="rounded-full border border-line px-4 py-2 text-sm hover:bg-surface-2 disabled:opacity-50">
              Send {kind} now
            </button>
          </div>
        ) : (
          <p className="text-xs text-muted">Only owners and admins can change delivery.</p>
        )}
        {msg && (
          <p role="status" className={`text-xs ${msg.tone === "ok" ? "text-mor" : "text-sindoor"}`}>
            {msg.text}
          </p>
        )}
      </div>
    </Card>
  );
}
