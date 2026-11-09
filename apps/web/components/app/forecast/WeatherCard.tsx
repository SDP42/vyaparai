"use client";

import { useState } from "react";
import { ApiError, api } from "@/lib/api";
import { useApi } from "@/lib/analytics";
import type { Accuracy, City, WeatherSignal, WeatherStatus } from "@/lib/forecast";
import { Card } from "../analytics/parts";

const pct = (v: number | null | undefined) => (v == null ? "–" : `${(v * 100).toFixed(1)}%`);

/** Outside signals: whether weather was tried, whether it helped, and where the shop is. */
export function WeatherCard({ wsId, signal, accuracy, canEdit, onSaved }: { wsId: string; signal?: WeatherSignal; accuracy: Accuracy; canEdit: boolean; onSaved: () => void }) {
  const base = `/workspaces/${wsId}/weather`;
  const status = useApi<WeatherStatus>(`${base}/status`, []);
  const cities = useApi<City[]>(`${base}/cities`, []);
  const [pick, setPick] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const cov = accuracy.covariates;

  const save = async () => {
    if (!pick) return;
    setBusy(true);
    setErr(null);
    try {
      await api(`${base}/location`, { method: "PUT", body: JSON.stringify({ city: pick }) });
      setPick("");
      onSaved();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "Could not save the location");
    } finally {
      setBusy(false);
    }
  };

  let headline = "Weather not used";
  let body = "Add the shop's city to see whether local weather improves the forecast.";
  let tone: "good" | "neutral" | "warn" = "neutral";
  if (signal?.status === "ok" && cov) {
    if (signal.used) {
      headline = "Weather is helping";
      body = `Temperature and rain cut the typical error from ${pct(cov.wape_without)} to ${pct(cov.wape_with)} in past tests, so this forecast uses them.`;
      tone = "good";
    } else {
      headline = "Weather tried, left out";
      body = `We tested weather for ${signal.city ?? "your city"}. It did not improve accuracy enough (${pct(cov.wape_without)} without, ${pct(cov.wape_with)} with), so it is not used. That is common for everyday staples.`;
    }
  } else if (signal?.status === "unavailable") {
    headline = "Weather unavailable";
    body = signal.note ?? "The weather service could not be reached; this forecast does not use it.";
    tone = "warn";
  } else if (signal?.status === "off" || status.data?.enabled === false) {
    headline = "Weather switched off";
    body = status.data?.note ?? signal?.note ?? "Weather is switched off on this server.";
  }

  return (
    <Card title="Outside signals" subtitle="Weather is kept only if it makes the forecast more accurate">
      <div className={`rounded-xl border p-3 text-sm ${tone === "good" ? "border-mor/40 bg-mor/10" : tone === "warn" ? "border-haldi/50 bg-haldi/15" : "border-line bg-canvas"}`}>
        <p className="font-semibold">{headline}</p>
        <p className="mt-1 text-xs text-muted">{body}</p>
      </div>
      {canEdit && status.data?.enabled !== false && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <select aria-label="Shop city" value={pick} onChange={(e) => setPick(e.target.value)} className="min-w-0 flex-1 rounded-lg border border-line bg-surface px-2.5 py-1.5 text-sm">
            <option value="">{status.data?.city ? `City: ${status.data.city}` : "Choose the shop's city"}</option>
            {cities.data?.map((c) => (
              <option key={c.name} value={c.name}>
                {c.name}, {c.state}
              </option>
            ))}
          </select>
          <button type="button" onClick={save} disabled={!pick || busy} className="rounded-full bg-fg px-4 py-1.5 text-xs font-semibold text-canvas hover:bg-sindoor disabled:opacity-50">
            {busy ? "Saving…" : "Save city"}
          </button>
        </div>
      )}
      {pick === "" && status.data?.city && canEdit && <p className="mt-2 text-xs text-muted">Refresh the forecast after changing the city.</p>}
      {err && <p className="mt-2 text-xs text-sindoor">{err}</p>}
      {status.data?.free_tier && status.data.enabled && <p className="mt-2 text-[11px] text-muted">Free weather service: for development and non-commercial use only.</p>}
      <p className="mt-2 text-[11px] text-muted">{signal?.attribution ?? status.data?.attribution}</p>
    </Card>
  );
}
