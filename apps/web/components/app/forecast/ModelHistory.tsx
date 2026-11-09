"use client";

import { useState } from "react";
import { ApiError, api } from "@/lib/api";
import { longDate, useApi } from "@/lib/analytics";
import type { RunVersion } from "@/lib/forecast";
import { Card } from "../analytics/parts";
import { MODEL_LABEL } from "./bits";

const STATUS: Record<RunVersion["status"], { label: string; tone: string }> = {
  active: { label: "In use", tone: "bg-mor/12 text-mor" },
  superseded: { label: "Older", tone: "bg-surface-2 text-muted" },
  rejected: { label: "Not used", tone: "bg-sindoor/10 text-sindoor" },
};
const pct = (v: number | null | undefined) => (v == null ? "–" : `${(v * 100).toFixed(1)}%`);

/** Every forecast version with its test results, and a way to go back to an earlier one. */
export function ModelHistory({ wsId, canEdit, version, onChanged }: { wsId: string; canEdit: boolean; version: number; onChanged: () => void }) {
  const base = `/workspaces/${wsId}/forecasts`;
  const runs = useApi<RunVersion[]>(`${base}/runs`, [version]);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const use = async (r: RunVersion) => {
    setBusy(r.id);
    setErr(null);
    try {
      await api(`${base}/runs/${r.id}/activate`, { method: "POST" });
      onChanged();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "Could not switch version");
    } finally {
      setBusy(null);
    }
  };

  return (
    <Card title="Forecast versions" subtitle="Each refresh is kept with its test results. A version that does worse than “repeat last week” is not put in use.">
      {err && <p className="mb-2 text-xs text-sindoor">{err}</p>}
      <ul className="divide-y divide-line">
        {runs.data?.map((r) => (
          <li key={r.id} className="py-3 text-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="flex items-center gap-2">
                <b>Version {r.version}</b>
                <span className={`rounded-full px-2 py-0.5 text-[11px] ${STATUS[r.status].tone}`}>{STATUS[r.status].label}</span>
              </span>
              <span className="font-mono text-[11px] text-muted">{longDate(r.created_at.slice(0, 10))} · sales to {longDate(r.as_of)}</span>
            </div>
            <p className="mt-1 text-xs text-muted">
              Typically off by {pct(r.wape)}
              {r.fva != null ? ` · ${r.fva >= 0 ? `${Math.round(r.fva * 100)}% better` : `${Math.round(-r.fva * 100)}% worse`} than repeating last week` : ""}
              {" · "}
              {Object.entries(r.models)
                .filter(([, n]) => n > 0)
                .map(([m, n]) => `${MODEL_LABEL[m] ?? m} ${n}`)
                .join(", ")}
              {r.options.peak_uplift_pct ? ` · festive +${r.options.peak_uplift_pct}%` : ""}
              {r.tuning ? ` · tuning ${r.tuning.used ? "improved it" : "found nothing better"}` : ""}
            </p>
            {r.note && <p className="mt-1 text-xs text-fg/70">{r.note}</p>}
            {canEdit && r.status !== "active" && (
              <button type="button" disabled={busy === r.id} onClick={() => use(r)} className="mt-2 rounded-full border border-line px-3 py-1 text-xs hover:bg-surface-2 disabled:opacity-60">
                {busy === r.id ? "Switching…" : "Use this version"}
              </button>
            )}
          </li>
        ))}
      </ul>
    </Card>
  );
}
