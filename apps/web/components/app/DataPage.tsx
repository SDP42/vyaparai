"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type DataSummary, type Dataset, type Page } from "@/lib/api";
import { formatINR, formatNumber, parseUtc } from "@/lib/format";
import { useAnalyticsState, useWorkspace } from "./AppContext";
import { ConnectionsCard } from "./ConnectionsCard";
import { ImportWizard } from "./ImportWizard";

const STATUS: Record<Dataset["status"], { label: string; cls: string }> = {
  uploaded: { label: "Needs mapping", cls: "bg-haldi/15 text-haldi-deep" },
  mapped: { label: "Needs validation", cls: "bg-haldi/15 text-haldi-deep" },
  validated: { label: "Ready to import", cls: "bg-neel/10 text-neel" },
  imported: { label: "Imported", cls: "bg-mor/15 text-mor" },
  failed: { label: "Failed", cls: "bg-sindoor/10 text-sindoor" },
};

/** Imports: upload → map → review → import, plus the upload history. */
export function DataPage() {
  const { workspace, canImport } = useWorkspace();
  const { refreshOptions } = useAnalyticsState();
  const base = `/workspaces/${workspace.id}`;
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [summary, setSummary] = useState<DataSummary | null>(null);
  const [wizard, setWizard] = useState<{ open: boolean; dataset: Dataset | null }>({ open: false, dataset: null });

  const refresh = useCallback(async () => {
    const [d, s] = await Promise.all([api<Page<Dataset>>(`${base}/datasets?limit=50`), api<DataSummary>(`${base}/data-summary`)]);
    setDatasets(d.items);
    setSummary(s);
  }, [base]);
  useEffect(() => {
    refresh().catch(() => {});
  }, [refresh]);

  // After an import, the metric layer has new data: refresh the shared analytics state too.
  const onChanged = useCallback(() => {
    refresh().catch(() => {});
    refreshOptions().catch(() => {});
  }, [refresh, refreshOptions]);

  const empty = summary && summary.orders === 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-sindoor">{workspace.name}</p>
          <h1 className="mt-1 text-3xl font-bold tracking-tight sm:text-4xl">Data</h1>
        </div>
        {canImport && !wizard.open && (
          <button type="button" onClick={() => setWizard({ open: true, dataset: null })} className="rounded-full bg-fg px-5 py-2.5 text-sm font-semibold text-canvas hover:bg-sindoor">
            + Import sales data
          </button>
        )}
      </div>

      {summary && (
        <div className="fluid [--min:9rem]">
          <Tile label="Orders" value={formatNumber(summary.orders)} />
          <Tile label="Line items" value={formatNumber(summary.order_items)} />
          <Tile label="Products" value={formatNumber(summary.products)} />
          <Tile label="Customers" value={formatNumber(summary.customers)} />
          <Tile label="Net sales (completed)" value={formatINR(Number(summary.net_sales_completed))} />
        </div>
      )}
      {summary?.date_from && (
        <p className="-mt-3 font-mono text-xs text-muted">
          Data from {summary.date_from} to {summary.date_to}
        </p>
      )}

      <ConnectionsCard base={base} canEdit={canImport} onNewData={onChanged} />

      {wizard.open && <ImportWizard workspaceId={workspace.id} initial={wizard.dataset} onChanged={onChanged} onClose={() => setWizard({ open: false, dataset: null })} />}

      {empty && !wizard.open && (
        <div className="rounded-3xl border border-dashed border-line bg-surface p-10 text-center">
          <h2 className="text-xl font-bold">No sales data yet</h2>
          <p className="mx-auto mt-2 max-w-md text-sm text-muted">
            Import a CSV or Excel export from your billing software. You can also try our sample file: 90 days of a general store with a few deliberate mistakes.
          </p>
          {canImport && (
            <button type="button" onClick={() => setWizard({ open: true, dataset: null })} className="mt-5 rounded-full bg-fg px-6 py-3 text-sm font-semibold text-canvas hover:bg-sindoor">
              Import sales data
            </button>
          )}
        </div>
      )}

      {datasets.length > 0 && (
        <section aria-labelledby="uploads-title" className="overflow-hidden rounded-3xl border border-line bg-surface">
          <h2 id="uploads-title" className="px-5 pt-5 font-semibold">
            Uploads
          </h2>
          <div className="overflow-x-auto">
            <table className="mt-3 w-full min-w-[560px] text-sm">
              <thead>
                <tr className="border-y border-line text-left font-mono text-[10px] uppercase tracking-[0.14em] text-muted">
                  <th className="px-5 py-2 font-normal">File</th>
                  <th className="px-5 py-2 font-normal">Rows</th>
                  <th className="px-5 py-2 font-normal">Status</th>
                  <th className="px-5 py-2 font-normal">Uploaded</th>
                  <th className="px-5 py-2" />
                </tr>
              </thead>
              <tbody>
                {datasets.map((d) => (
                  <tr key={d.id} className="border-b border-line/70 last:border-0">
                    <td className="px-5 py-3">
                      <p className="font-medium">{d.name}</p>
                      <p className="font-mono text-[11px] text-muted">{d.source_filename}</p>
                    </td>
                    <td className="px-5 py-3 tabular">{d.row_count ? formatNumber(d.row_count) : "—"}</td>
                    <td className="px-5 py-3">
                      <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${STATUS[d.status].cls}`}>{STATUS[d.status].label}</span>
                    </td>
                    <td className="px-5 py-3 text-muted">{parseUtc(d.created_at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })}</td>
                    <td className="px-5 py-3 text-right">
                      {canImport && d.status !== "imported" && (
                        <button type="button" onClick={() => setWizard({ open: true, dataset: d })} className="text-sm font-medium text-sindoor underline underline-offset-4">
                          Continue
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}

function Tile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-line bg-surface p-4">
      <p className="text-xs text-muted">{label}</p>
      <p className="mt-1 text-xl font-bold tabular sm:text-2xl">{value}</p>
    </div>
  );
}
