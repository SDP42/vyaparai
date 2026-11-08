"use client";

import { num, type MixRow } from "@/lib/analytics";
import { fmt } from "./parts";

/**
 * A ranked list with a bar per row: share of net sales, and the change against the comparison.
 * If ``onPick`` is given, each row is a button that drills into that slice.
 */
export function MixList({
  rows,
  limit = 6,
  onPick,
  emptyText = "No sales in this period.",
}: {
  rows: MixRow[];
  limit?: number;
  onPick?: (row: MixRow) => void;
  emptyText?: string;
}) {
  const shown = rows.filter((r) => num(r.net) > 0 || (r.delta != null && num(r.delta) !== 0)).slice(0, limit);
  if (shown.length === 0) return <p className="py-6 text-center text-sm text-muted">{emptyText}</p>;
  const max = Math.max(...shown.map((r) => num(r.net)), 1);

  return (
    <ul className="space-y-2.5">
      {shown.map((r) => {
        const delta = r.delta == null ? null : num(r.delta);
        const Row = (
          <>
            <div className="flex items-baseline justify-between gap-3 text-sm">
              <span className="truncate font-medium">{r.label}</span>
              <span className="shrink-0 tabular">
                {fmt("inr", r.net)}
                {r.share != null && <span className="ml-2 font-mono text-[11px] text-muted">{num(r.share).toFixed(0)}%</span>}
              </span>
            </div>
            <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-surface-2" aria-hidden>
              <div className="h-full rounded-full bg-haldi" style={{ width: `${Math.max((num(r.net) / max) * 100, 1.5)}%` }} />
            </div>
            {delta != null && delta !== 0 && (
              <p className={`mt-0.5 font-mono text-[11px] ${delta > 0 ? "text-mor" : "text-sindoor"}`}>
                <span aria-hidden>{delta > 0 ? "▲" : "▼"}</span> {fmt("inr", Math.abs(delta), { compact: true })}
                <span className="sr-only">{delta > 0 ? " increase" : " decrease"}</span>
                <span className="text-muted"> vs comparison</span>
              </p>
            )}
          </>
        );
        return (
          <li key={r.key}>
            {onPick ? (
              <button type="button" onClick={() => onPick(r)} className="block w-full rounded-lg text-left transition-colors hover:bg-surface-2/60" title={`See ${r.label} transactions`}>
                {Row}
              </button>
            ) : (
              Row
            )}
          </li>
        );
      })}
    </ul>
  );
}
