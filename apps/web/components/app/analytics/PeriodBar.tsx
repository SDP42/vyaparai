"use client";

import { useState } from "react";
import { longDate, type Compare } from "@/lib/analytics";
import { PRESETS, useAnalyticsState } from "../AppContext";

const COMPARE: { key: Compare; label: string }[] = [
  { key: "previous_period", label: "Previous period" },
  { key: "previous_year", label: "Same weekdays last year" },
  { key: "none", label: "No comparison" },
];

/** Period, comparison and dimension filters shared by the command center and the sales explorer. */
export function PeriodBar({ showFilters = false }: { showFilters?: boolean }) {
  const { query, preset, options, setPreset, setRange, setCompare, clearFilters, setFilter } = useAnalyticsState();
  const [custom, setCustom] = useState(false);
  const active = query.category.length + query.channel.length + query.region.length + query.sku.length;

  const input = "rounded-lg border border-line bg-surface px-2.5 py-1.5 text-sm";
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <div role="group" aria-label="Period" className="flex flex-wrap gap-1 rounded-full border border-line bg-surface p-1">
          {PRESETS.map((p) => (
            <button
              key={p.key}
              type="button"
              aria-pressed={preset === p.key}
              onClick={() => {
                setCustom(false);
                setPreset(p.key);
              }}
              className={`rounded-full px-3 py-1.5 text-xs transition-colors ${
                preset === p.key ? "bg-fg text-canvas" : "text-fg/65 hover:text-fg"
              }`}
            >
              {p.label}
            </button>
          ))}
          <button
            type="button"
            aria-pressed={preset === "custom" || custom}
            onClick={() => setCustom((c) => !c)}
            className={`rounded-full px-3 py-1.5 text-xs transition-colors ${
              preset === "custom" ? "bg-fg text-canvas" : "text-fg/65 hover:text-fg"
            }`}
          >
            Custom
          </button>
        </div>

        <label className="flex items-center gap-2 text-xs text-muted">
          <span>Compare with</span>
          <select value={query.compare} onChange={(e) => setCompare(e.target.value as Compare)} className={input}>
            {COMPARE.map((c) => (
              <option key={c.key} value={c.key}>
                {c.label}
              </option>
            ))}
          </select>
        </label>
        <p className="font-mono text-[11px] text-muted">
          {longDate(query.from)} → {longDate(query.to)}
        </p>
      </div>

      {(custom || preset === "custom") && (
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <label className="flex items-center gap-2">
            <span className="text-xs text-muted">From</span>
            <input type="date" value={query.from} max={query.to} onChange={(e) => e.target.value && setRange(e.target.value, query.to)} className={input} />
          </label>
          <label className="flex items-center gap-2">
            <span className="text-xs text-muted">To</span>
            <input type="date" value={query.to} min={query.from} onChange={(e) => e.target.value && setRange(query.from, e.target.value)} className={input} />
          </label>
        </div>
      )}

      {showFilters && options && (
        <div className="flex flex-wrap items-center gap-2">
          <FilterMenu label="Category" values={options.categories} selected={query.category} onChange={(v) => setFilter("category", v)} />
          <FilterMenu label="Channel" values={options.channels} selected={query.channel} onChange={(v) => setFilter("channel", v)} />
          <FilterMenu label="Region" values={[...options.regions, "Unspecified"]} selected={query.region} onChange={(v) => setFilter("region", v)} />
          {query.sku.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => setFilter("sku", query.sku.filter((x) => x !== s))}
              className="rounded-full border border-haldi/50 bg-haldi/15 px-3 py-1 text-xs"
              aria-label={`Remove product filter ${s}`}
            >
              Product {s} ✕
            </button>
          ))}
          {active > 0 && (
            <button type="button" onClick={clearFilters} className="text-xs text-muted underline underline-offset-4 hover:text-fg">
              Clear filters
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function FilterMenu({
  label,
  values,
  selected,
  onChange,
}: {
  label: string;
  values: string[];
  selected: string[];
  onChange: (v: string[]) => void;
}) {
  const [open, setOpen] = useState(false);
  if (values.length === 0) return null;
  return (
    <div className="relative">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className={`rounded-full border px-3 py-1.5 text-xs ${selected.length ? "border-fg bg-fg text-canvas" : "border-line bg-surface text-fg/70 hover:text-fg"}`}
      >
        {label}
        {selected.length > 0 && ` · ${selected.length}`} ▾
      </button>
      {open && (
        <div className="absolute left-0 top-9 z-30 max-h-64 w-52 overflow-auto rounded-xl border border-line bg-surface p-2 shadow-[0_20px_50px_-20px_rgba(27,22,18,0.4)]">
          {values.map((v) => (
            <label key={v} className="flex cursor-pointer items-center gap-2 rounded-lg px-2 py-1.5 text-sm hover:bg-surface-2">
              <input
                type="checkbox"
                checked={selected.includes(v)}
                onChange={() => onChange(selected.includes(v) ? selected.filter((x) => x !== v) : [...selected, v])}
              />
              {v}
            </label>
          ))}
          <button type="button" onClick={() => setOpen(false)} className="mt-1 w-full rounded-lg py-1.5 text-xs text-muted hover:text-fg">
            Done
          </button>
        </div>
      )}
    </div>
  );
}
