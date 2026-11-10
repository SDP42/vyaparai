"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError, api } from "@/lib/api";
import { parseUtc } from "@/lib/format";
import type { ImportSource, Schedule, SourceStatus } from "@/lib/sources";

const STATUS: Record<SourceStatus, { label: string; tone: string }> = {
  never: { label: "Not checked yet", tone: "bg-surface-2 text-muted" },
  running: { label: "Checking…", tone: "bg-haldi/25 text-fg" },
  ok: { label: "Up to date", tone: "bg-mor/12 text-mor" },
  unchanged: { label: "Up to date", tone: "bg-mor/12 text-mor" },
  failed: { label: "Problem", tone: "bg-sindoor/10 text-sindoor" },
};
const SCHEDULE: Record<Schedule, string> = { daily: "Every day", hourly: "Every hour", manual: "Only when I press Check now" };

function ago(iso: string | null): string {
  if (!iso) return "never";
  const mins = Math.round((Date.now() - parseUtc(iso).getTime()) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min ago`;
  if (mins < 60 * 24) return `${Math.round(mins / 60)} h ago`;
  return `${Math.round(mins / 1440)} days ago`;
}
const host = (u: string) => {
  try {
    return new URL(u).hostname;
  } catch {
    return u;
  }
};

/** Keep your numbers fresh by connecting a published sheet or shared file; new sales arrive by themselves. */
export function ConnectionsCard({ base, canEdit, onNewData }: { base: string; canEdit: boolean; onNewData: () => void }) {
  const [items, setItems] = useState<ImportSource[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: "", url: "", schedule: "daily" as Schedule });
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setItems(await api<ImportSource[]>(`${base}/sources`));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not load your links");
    }
  }, [base]);
  useEffect(() => {
    load();
  }, [load]);

  // While a check is running, look again every second; when it finishes with new sales, refresh the page.
  const running = items?.some((s) => s.last_status === "running") ?? false;
  useEffect(() => {
    if (!running) return;
    const t = setInterval(async () => {
      const next = await api<ImportSource[]>(`${base}/sources`).catch(() => null);
      if (!next) return;
      setItems((prev) => {
        if (prev && next.some((n) => n.last_status === "ok" && prev.find((p) => p.id === n.id)?.last_status === "running")) onNewData();
        return next;
      });
    }, 1200);
    return () => clearInterval(t);
  }, [running, base, onNewData]);

  const act = async (fn: () => Promise<unknown>) => {
    setError(null);
    try {
      await fn();
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Something went wrong");
    }
  };
  const add = async () => {
    setBusy(true);
    await act(async () => {
      const s = await api<ImportSource>(`${base}/sources`, { method: "POST", body: JSON.stringify(form) });
      setForm({ name: "", url: "", schedule: "daily" });
      setOpen(false);
      await api(`${base}/sources/${s.id}/run`, { method: "POST" });
    });
    setBusy(false);
  };
  const input = "w-full rounded-lg border border-line bg-surface px-2.5 py-1.5 text-sm";

  return (
    <section aria-labelledby="conn-title" className="rounded-3xl border border-line bg-surface p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 id="conn-title" className="font-semibold">
            Connected links
          </h2>
          <p className="mt-0.5 max-w-xl text-xs text-muted">Connect a Google Sheet or shared file that your billing software updates, and new sales come in by themselves. No more uploading by hand.</p>
        </div>
        {canEdit && !open && (
          <button type="button" onClick={() => setOpen(true)} className="rounded-full border border-line px-4 py-1.5 text-sm hover:bg-surface-2">
            + Connect a link
          </button>
        )}
      </div>

      {error && (
        <p role="alert" className="mt-3 text-sm text-sindoor">
          {error}
        </p>
      )}

      {open && (
        <div className="mt-4 space-y-3 rounded-2xl border border-line bg-canvas p-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block text-xs text-muted">
              Name
              <input className={`${input} mt-1`} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Daily sales sheet" maxLength={120} />
            </label>
            <label className="block text-xs text-muted">
              How often to check
              <select className={`${input} mt-1`} value={form.schedule} onChange={(e) => setForm({ ...form, schedule: e.target.value as Schedule })}>
                {(Object.keys(SCHEDULE) as Schedule[]).map((s) => (
                  <option key={s} value={s}>
                    {SCHEDULE[s]}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <label className="block text-xs text-muted">
            Link
            <input className={`${input} mt-1`} value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} placeholder="https://docs.google.com/spreadsheets/d/…" inputMode="url" />
          </label>
          <details className="text-xs text-muted">
            <summary className="cursor-pointer text-fg">How do I get the link?</summary>
            <ol className="mt-2 list-decimal space-y-1 pl-5">
              <li>Open your sales sheet in Google Sheets.</li>
              <li>Choose <b>File → Share → Publish to web</b>, pick the sheet tab and <b>CSV</b>, then publish. Copy the link. (Or share it with “Anyone with the link can view”.)</li>
              <li>Paste it here. Dropbox shared links and Google Drive files work too.</li>
            </ol>
            <p className="mt-2 rounded-lg bg-haldi/10 p-2 text-fg">Anyone who has the link can read the sheet, so keep customer names and phone numbers out of it. Only totals and product lines are needed.</p>
            <p className="mt-2">The first time, we match your columns once, then remember them. If we cannot match them we will tell you, and you can upload the file by hand once to confirm.</p>
          </details>
          <div className="flex gap-2">
            <button type="button" disabled={busy || !form.name.trim() || !form.url.trim()} onClick={add} className="rounded-full bg-fg px-4 py-1.5 text-sm font-semibold text-canvas hover:bg-sindoor disabled:opacity-50">
              {busy ? "Connecting…" : "Connect and check now"}
            </button>
            <button type="button" onClick={() => setOpen(false)} className="rounded-full border border-line px-4 py-1.5 text-sm">
              Cancel
            </button>
          </div>
        </div>
      )}

      {items && items.length === 0 && !open && <p className="mt-4 text-sm text-muted">No links yet.</p>}
      <ul className="mt-4 divide-y divide-line">
        {items?.map((s) => (
          <li key={s.id} className="py-3 text-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="min-w-0">
                <p className="font-medium">
                  {s.name}
                  {!s.enabled && <span className="ml-2 rounded-full bg-surface-2 px-2 py-0.5 text-[11px] text-muted">Paused</span>}
                </p>
                <p className="font-mono text-[11px] text-muted">
                  {host(s.url)} · {SCHEDULE[s.schedule]}
                </p>
              </div>
              <span className={`rounded-full px-2 py-0.5 text-[11px] ${STATUS[s.last_status].tone}`}>{STATUS[s.last_status].label}</span>
            </div>
            <p className={`mt-1 text-xs ${s.last_status === "failed" ? "text-sindoor" : "text-muted"}`}>
              {s.last_message ? `${s.last_message} ` : ""}Checked {ago(s.last_run_at)}.
            </p>
            {canEdit && (
              <div className="mt-2 flex flex-wrap gap-2 text-xs">
                <button type="button" disabled={s.last_status === "running"} onClick={() => act(() => api(`${base}/sources/${s.id}/run`, { method: "POST" }))} className="rounded-full border border-line px-3 py-1 hover:bg-surface-2 disabled:opacity-50">
                  Check now
                </button>
                <button type="button" onClick={() => act(() => api(`${base}/sources/${s.id}`, { method: "PATCH", body: JSON.stringify({ enabled: !s.enabled }) }))} className="rounded-full border border-line px-3 py-1 hover:bg-surface-2">
                  {s.enabled ? "Pause" : "Resume"}
                </button>
                <button
                  type="button"
                  onClick={() => confirm(`Remove "${s.name}"? Data already imported stays.`) && act(() => api(`${base}/sources/${s.id}`, { method: "DELETE" }))}
                  className="rounded-full border border-line px-3 py-1 text-sindoor hover:bg-sindoor/5"
                >
                  Remove
                </button>
              </div>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
