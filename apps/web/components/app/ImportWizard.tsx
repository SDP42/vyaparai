"use client";

import { useCallback, useEffect, useMemo, useRef, useState, type DragEvent } from "react";
import { AnimatePresence, motion } from "motion/react";
import {
  ApiError,
  api,
  download,
  type DataSummary,
  type Dataset,
  type Job,
  type ValidationSummary,
} from "@/lib/api";
import { formatINR, formatNumber } from "@/lib/format";

type Step = "upload" | "map" | "review" | "import";
const STEPS: { key: Step; label: string }[] = [
  { key: "upload", label: "Upload" },
  { key: "map", label: "Map columns" },
  { key: "review", label: "Review" },
  { key: "import", label: "Import" },
];
const EASE = [0.16, 1, 0.3, 1] as const;

function stepFor(d: Dataset): Step {
  if (d.status === "validated") return "review";
  if (d.status === "imported" || d.status === "failed") return "import";
  return "map";
}

export function ImportWizard({
  workspaceId,
  initial,
  onChanged,
  onClose,
}: {
  workspaceId: string;
  initial?: Dataset | null;
  onChanged: () => void;
  onClose: () => void;
}) {
  const [dataset, setDataset] = useState<Dataset | null>(initial ?? null);
  const [step, setStep] = useState<Step>(initial ? stepFor(initial) : "upload");
  const base = `/workspaces/${workspaceId}`;

  // Make sure we have the full detail (inspection + validation) when resuming.
  useEffect(() => {
    if (initial && !initial.inspection) {
      api<Dataset>(`${base}/datasets/${initial.id}`).then(setDataset).catch(() => {});
    }
  }, [initial, base]);

  return (
    <section aria-label="Import data" className="rounded-3xl border border-line bg-surface">
      <header className="flex flex-wrap items-center justify-between gap-4 border-b border-line px-5 py-4 sm:px-6">
        <ol className="flex flex-wrap items-center gap-2 text-sm" aria-label="Steps">
          {STEPS.map((s, i) => {
            const idx = STEPS.findIndex((x) => x.key === step);
            const state = i < idx ? "done" : i === idx ? "current" : "todo";
            return (
              <li key={s.key} className="flex items-center gap-2" aria-current={state === "current" ? "step" : undefined}>
                <span
                  className={`grid h-6 w-6 place-items-center rounded-full font-mono text-[11px] ${
                    state === "done" ? "bg-mor text-canvas" : state === "current" ? "bg-fg text-canvas" : "border border-line text-muted"
                  }`}
                >
                  {state === "done" ? "✓" : i + 1}
                </span>
                <span className={state === "todo" ? "text-muted" : "font-medium"}>{s.label}</span>
                {i < STEPS.length - 1 && <span aria-hidden className="mx-1 h-px w-6 bg-line" />}
              </li>
            );
          })}
        </ol>
        <button type="button" onClick={onClose} className="text-sm text-muted hover:text-fg">
          Close
        </button>
      </header>

      <div className="p-5 sm:p-6">
        <AnimatePresence mode="wait">
          <motion.div
            key={step}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -16 }}
            transition={{ duration: 0.3, ease: EASE }}
          >
            {step === "upload" && (
              <UploadStep
                base={base}
                onUploaded={(d) => {
                  setDataset(d);
                  setStep("map");
                  onChanged();
                }}
                onOpenExisting={(d) => {
                  setDataset(d);
                  setStep(stepFor(d));
                }}
              />
            )}
            {step === "map" && dataset && (
              <MapStep
                base={base}
                dataset={dataset}
                onValidated={(d) => {
                  setDataset(d);
                  setStep("review");
                  onChanged();
                }}
              />
            )}
            {step === "review" && dataset?.validation && (
              <ReviewStep base={base} dataset={dataset} onBack={() => setStep("map")} onImport={() => setStep("import")} />
            )}
            {step === "import" && dataset && <ImportStep base={base} dataset={dataset} onDone={onChanged} />}
          </motion.div>
        </AnimatePresence>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ step 1 */

function UploadStep({
  base,
  onUploaded,
  onOpenExisting,
}: {
  base: string;
  onUploaded: (d: Dataset) => void;
  onOpenExisting: (d: Dataset) => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [drag, setDrag] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const input = useRef<HTMLInputElement>(null);

  const pick = (f: File | undefined | null) => {
    setError(null);
    if (f) setFile(f);
  };

  const send = useCallback(
    async (f: File) => {
      setBusy(true);
      setError(null);
      const fd = new FormData();
      fd.append("file", f);
      try {
        onUploaded(await api<Dataset>(`${base}/datasets`, { method: "POST", body: fd }));
      } catch (e) {
        setError(e instanceof ApiError ? e : new ApiError(0, "unknown", "Upload failed"));
      } finally {
        setBusy(false);
      }
    },
    [base, onUploaded],
  );

  const useSample = async () => {
    const res = await fetch("/samples/vyapar_demo_sales_messy.csv");
    const blob = await res.blob();
    const f = new File([blob], "vyapar_demo_sales_messy.csv", { type: "text/csv" });
    setFile(f);
    await send(f);
  };

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDrag(false);
    pick(e.dataTransfer.files?.[0]);
  };

  const existingId = (error?.details as { dataset_id?: string } | null)?.dataset_id;

  return (
    <div className="grid gap-6 lg:grid-cols-[1.3fr_1fr]">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Upload a sales export</h2>
        <p className="mt-1 text-sm text-muted">
          CSV or Excel (.xlsx), one row per order line, up to 25 MB. Nothing is saved to your books until you review
          and confirm the import.
        </p>
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDrag(true);
          }}
          onDragLeave={() => setDrag(false)}
          onDrop={onDrop}
          className={`mt-5 flex flex-col items-center justify-center rounded-2xl border-2 border-dashed px-6 py-12 text-center transition-colors ${
            drag ? "border-haldi bg-haldi/10" : "border-line bg-canvas"
          }`}
        >
          <svg aria-hidden width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-muted">
            <path d="M12 16V4m0 0-4 4m4-4 4 4M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" />
          </svg>
          {file ? (
            <p className="mt-3 font-medium">
              {file.name} <span className="text-muted">· {(file.size / 1024).toFixed(0)} KB</span>
            </p>
          ) : (
            <p className="mt-3 font-medium">Drag a file here</p>
          )}
          <button type="button" onClick={() => input.current?.click()} className="mt-3 text-sm text-sindoor underline underline-offset-4">
            or choose a file
          </button>
          <input
            ref={input}
            type="file"
            accept=".csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            className="sr-only"
            onChange={(e) => pick(e.target.files?.[0])}
          />
        </div>
        {error && (
          <div role="alert" className="mt-4 rounded-xl border border-sindoor/30 bg-sindoor/5 p-3 text-sm">
            <p className="font-medium text-sindoor">{error.message}</p>
            {existingId && (
              <button
                type="button"
                className="mt-1 underline underline-offset-4"
                onClick={async () => onOpenExisting(await api<Dataset>(`${base}/datasets/${existingId}`))}
              >
                Open the existing upload
              </button>
            )}
          </div>
        )}
        <div className="mt-5 flex flex-wrap gap-3">
          <button
            type="button"
            disabled={!file || busy}
            onClick={() => file && send(file)}
            className="rounded-full bg-fg px-6 py-3 text-sm font-semibold text-canvas transition-colors hover:bg-sindoor disabled:opacity-50"
          >
            {busy ? "Uploading & inspecting…" : "Upload & inspect"}
          </button>
          <button type="button" disabled={busy} onClick={useSample} className="rounded-full border border-line px-6 py-3 text-sm font-semibold hover:border-fg/40">
            Try the sample file
          </button>
        </div>
      </div>
      <aside className="rounded-2xl bg-canvas p-5 text-sm">
        <p className="font-semibold">What we expect</p>
        <ul className="mt-3 space-y-2 text-muted">
          <li>
            <b className="text-fg">Required:</b> order/invoice ID, order date, SKU, product name, quantity, unit price
          </li>
          <li>
            <b className="text-fg">Optional:</b> category, discount, cost, customer, state, city, channel, status, GST
          </li>
          <li>Column names can be anything. You will map them in the next step.</li>
          <li>Dates are read day-first (05/10/2026 is 5 October) unless you choose otherwise.</li>
          <li>₹ symbols and Indian commas (1,23,456) are fine.</li>
        </ul>
      </aside>
    </div>
  );
}

/* ------------------------------------------------------------------ step 2 */

function MapStep({ base, dataset, onValidated }: { base: string; dataset: Dataset; onValidated: (d: Dataset) => void }) {
  const insp = dataset.inspection;
  const [fields, setFields] = useState<Record<string, string>>(dataset.column_mapping?.fields ?? {});
  const [order, setOrder] = useState<"dmy" | "mdy" | "ymd">(dataset.column_mapping?.date_order ?? "dmy");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (dataset.column_mapping?.fields) setFields(dataset.column_mapping.fields);
  }, [dataset.column_mapping]);

  const columns = useMemo(() => Object.fromEntries((insp?.columns ?? []).map((c) => [c.name, c])), [insp]);
  if (!insp) return <p className="text-sm text-muted">Loading file details…</p>;

  const missing = insp.fields.filter((f) => f.required && !fields[f.key]);
  const used = new Set(Object.values(fields));

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      await api(`${base}/datasets/${dataset.id}/mapping`, {
        method: "PUT",
        body: JSON.stringify({ fields, date_order: order }),
      });
      await api<ValidationSummary>(`${base}/datasets/${dataset.id}/validate`, { method: "POST" });
      onValidated(await api<Dataset>(`${base}/datasets/${dataset.id}`));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Match your columns</h2>
          <p className="mt-1 text-sm text-muted">
            {dataset.source_filename} · {formatNumber(insp.row_count)} rows · {insp.headers.length} columns. We guessed the
            matches; check them before validating.
          </p>
        </div>
        <label className="text-sm">
          <span className="mr-2 text-muted">Dates are written</span>
          <select value={order} onChange={(e) => setOrder(e.target.value as typeof order)} className="rounded-lg border border-line bg-canvas px-3 py-2">
            <option value="dmy">Day / Month / Year</option>
            <option value="mdy">Month / Day / Year</option>
            <option value="ymd">Year / Month / Day</option>
          </select>
        </label>
      </div>

      <div className="mt-5 overflow-x-auto rounded-2xl border border-line">
        <table className="w-full min-w-[640px] text-sm">
          <thead>
            <tr className="border-b border-line bg-canvas text-left font-mono text-[10px] uppercase tracking-[0.14em] text-muted">
              <th className="px-4 py-2.5 font-normal">Vyapar field</th>
              <th className="px-4 py-2.5 font-normal">Your column</th>
              <th className="px-4 py-2.5 font-normal">Sample values</th>
            </tr>
          </thead>
          <tbody>
            {insp.fields.map((f) => {
              const col = fields[f.key];
              const info = col ? columns[col] : undefined;
              return (
                <tr key={f.key} className="border-b border-line/70 last:border-0">
                  <td className="px-4 py-2.5">
                    <span className="font-medium">{f.label}</span>
                    {f.required && <span className="ml-1.5 rounded-full bg-sindoor/10 px-1.5 py-0.5 text-[10px] text-sindoor">required</span>}
                  </td>
                  <td className="px-4 py-2.5">
                    <select
                      aria-label={`Column for ${f.label}`}
                      value={col ?? ""}
                      onChange={(e) => setFields((m) => ({ ...m, [f.key]: e.target.value }))}
                      className={`w-full rounded-lg border bg-canvas px-3 py-2 ${f.required && !col ? "border-sindoor/50" : "border-line"}`}
                    >
                      <option value="">— not in my file —</option>
                      {insp.headers.map((h) => (
                        <option key={h} value={h} disabled={used.has(h) && col !== h}>
                          {h}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="max-w-[260px] truncate px-4 py-2.5 font-mono text-xs text-muted">
                    {info ? info.samples.slice(0, 3).join(" · ") || "(empty)" : ""}
                    {info && info.empty_pct > 0 && <span className="ml-2 text-haldi-deep">{info.empty_pct}% empty</span>}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {error && (
        <p role="alert" className="mt-4 text-sm text-sindoor">
          {error}
        </p>
      )}
      <div className="mt-5 flex flex-wrap items-center gap-4">
        <button
          type="button"
          disabled={busy || missing.length > 0}
          onClick={submit}
          className="rounded-full bg-fg px-6 py-3 text-sm font-semibold text-canvas transition-colors hover:bg-sindoor disabled:opacity-50"
        >
          {busy ? "Checking every row…" : "Save & validate"}
        </button>
        {missing.length > 0 && <p className="text-sm text-muted">Still needed: {missing.map((m) => m.label).join(", ")}</p>}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ step 3 */

function ReviewStep({ base, dataset, onBack, onImport }: { base: string; dataset: Dataset; onBack: () => void; onImport: () => void }) {
  const v = dataset.validation!;
  const okPct = v.rows_total ? Math.round((v.rows_valid / v.rows_total) * 100) : 0;
  return (
    <div>
      <h2 className="text-2xl font-bold tracking-tight">Review before importing</h2>
      <p className="mt-1 text-sm text-muted">Rows with problems are left out. Nothing is changed until you confirm.</p>

      <div className="mt-5 grid gap-3 sm:grid-cols-3">
        <Stat label="Rows checked" value={formatNumber(v.rows_total)} />
        <Stat label="Ready to import" value={formatNumber(v.rows_valid)} tone="good" sub={`${okPct}%`} />
        <Stat label="Need attention" value={formatNumber(v.rows_invalid)} tone={v.rows_invalid ? "bad" : undefined} />
      </div>

      <div className="mt-3 grid gap-3 sm:grid-cols-4">
        <Stat label="Orders" value={formatNumber(v.preview.orders)} small />
        <Stat label="Products" value={formatNumber(v.preview.products)} small />
        <Stat label="Customers" value={formatNumber(v.preview.customers)} small />
        <Stat label="Net sales (completed)" value={formatINR(Number(v.preview.net_sales_completed))} small />
      </div>
      {v.preview.date_from && (
        <p className="mt-2 font-mono text-xs text-muted">
          Period: {v.preview.date_from} → {v.preview.date_to}
        </p>
      )}

      {v.rows_invalid > 0 && (
        <div className="mt-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="font-semibold">Problems found</p>
            <div className="flex flex-wrap gap-1.5">
              {Object.entries(v.errors_by_field).map(([f, n]) => (
                <span key={f} className="rounded-full bg-sindoor/10 px-2.5 py-1 font-mono text-[11px] text-sindoor">
                  {f}: {n}
                </span>
              ))}
            </div>
          </div>
          <div className="mt-3 max-h-72 overflow-auto rounded-2xl border border-line">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-canvas">
                <tr className="text-left font-mono text-[10px] uppercase tracking-[0.14em] text-muted">
                  <th className="px-4 py-2 font-normal">Row</th>
                  <th className="px-4 py-2 font-normal">Column</th>
                  <th className="px-4 py-2 font-normal">Problem</th>
                  <th className="px-4 py-2 font-normal">Value</th>
                </tr>
              </thead>
              <tbody>
                {v.sample_errors.map((e, i) => (
                  <tr key={i} className="border-t border-line/70">
                    <td className="px-4 py-2 font-mono text-xs">{e.row}</td>
                    <td className="px-4 py-2">{e.column || e.field}</td>
                    <td className="px-4 py-2 text-sindoor">{e.message}</td>
                    <td className="max-w-[180px] truncate px-4 py-2 font-mono text-xs text-muted">{e.value}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {v.error_count > v.sample_errors.length && (
            <p className="mt-2 text-xs text-muted">Showing the first {v.sample_errors.length} of {formatNumber(v.error_count)} problems.</p>
          )}
        </div>
      )}
      {v.warnings.length > 0 && (
        <ul className="mt-4 space-y-1 text-xs text-haldi-deep">
          {v.warnings.slice(0, 5).map((w) => (
            <li key={w}>⚠ {w}</li>
          ))}
        </ul>
      )}

      <div className="mt-6 flex flex-wrap gap-3">
        <button
          type="button"
          onClick={onImport}
          disabled={v.rows_valid === 0}
          className="rounded-full bg-fg px-6 py-3 text-sm font-semibold text-canvas transition-colors hover:bg-sindoor disabled:opacity-50"
        >
          Import {formatNumber(v.rows_valid)} rows
        </button>
        {v.rows_invalid > 0 && (
          <button
            type="button"
            onClick={() => download(`${base}/datasets/${dataset.id}/errors.csv`, `${dataset.name}_errors.csv`)}
            className="rounded-full border border-line px-6 py-3 text-sm font-semibold hover:border-fg/40"
          >
            Download problem rows (CSV)
          </button>
        )}
        <button type="button" onClick={onBack} className="px-2 text-sm text-muted hover:text-fg">
          ← Change mapping
        </button>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ step 4 */

/** One import request per dataset, even if React mounts the step twice (StrictMode). */
const importStarts = new Map<string, Promise<Job>>();
function startImportOnce(base: string, datasetId: string): Promise<Job> {
  let p = importStarts.get(datasetId);
  if (!p) {
    p = api<Job>(`${base}/datasets/${datasetId}/import`, { method: "POST" });
    importStarts.set(datasetId, p);
    p.catch(() => importStarts.delete(datasetId));
  }
  return p;
}

function ImportStep({ base, dataset, onDone }: { base: string; dataset: Dataset; onDone: () => void }) {
  const [job, setJob] = useState<Job | null>(null);
  const [summary, setSummary] = useState<DataSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Keep the latest callback without restarting the polling effect when the parent re-renders.
  const doneRef = useRef(onDone);
  doneRef.current = onDone;

  useEffect(() => {
    let stop = false;
    (async () => {
      try {
        let j: Job;
        if (dataset.status === "imported") {
          setSummary(await api<DataSummary>(`${base}/data-summary`));
          return;
        }
        j = await startImportOnce(base, dataset.id);
        setJob(j);
        while (!stop && (j.status === "queued" || j.status === "running")) {
          await new Promise((r) => setTimeout(r, 700));
          j = await api<Job>(`${base}/jobs/${j.id}`);
          setJob(j);
        }
        if (j.status === "succeeded") setSummary(await api<DataSummary>(`${base}/data-summary`));
        doneRef.current();
      } catch (e) {
        setError(e instanceof ApiError ? e.message : "Import failed");
      }
    })();
    return () => {
      stop = true;
    };
    // Mount-only: the import is started once per dataset (see startImportOnce).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const running = !job || job.status === "queued" || job.status === "running";
  const failed = job?.status === "failed" || !!error;

  return (
    <div className="mx-auto max-w-2xl text-center">
      {failed ? (
        <>
          <p className="text-4xl" aria-hidden>
            ⚠
          </p>
          <h2 className="mt-2 text-2xl font-bold">The import did not finish</h2>
          <p role="alert" className="mt-2 text-sm text-sindoor">
            {error ?? job?.error_message}
          </p>
          <p className="mt-1 text-xs text-muted">Nothing was saved, because imports happen in a single transaction.</p>
        </>
      ) : running && dataset.status !== "imported" ? (
        <>
          <h2 className="text-2xl font-bold">Importing into your books…</h2>
          <div className="mx-auto mt-6 h-2 max-w-md overflow-hidden rounded-full bg-canvas">
            <motion.div className="h-full rounded-full bg-haldi" animate={{ width: `${Math.max(job?.progress ?? 5, 8)}%` }} transition={{ duration: 0.5 }} />
          </div>
          <p className="mt-3 text-sm text-muted">Creating products, customers, orders and line items.</p>
        </>
      ) : (
        <>
          <motion.div
            initial={{ scale: 0.6, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ type: "spring", stiffness: 260, damping: 18 }}
            className="mx-auto grid h-14 w-14 place-items-center rounded-full bg-mor text-2xl text-canvas"
            aria-hidden
          >
            ✓
          </motion.div>
          <h2 className="mt-4 text-2xl font-bold">Your data is in</h2>
          {job?.result && (
            <p className="mt-2 text-sm text-muted">
              {formatNumber(job.result.orders_created)} orders · {formatNumber(job.result.lines_imported)} line items ·{" "}
              {formatNumber(job.result.products_created)} new products · {formatNumber(job.result.customers_created)} new customers
              {job.result.duplicate_orders_skipped ? ` · ${formatNumber(job.result.duplicate_orders_skipped)} orders already existed and were skipped` : ""}
              {job.rows_rejected ? ` · ${formatNumber(job.rows_rejected)} rows left out` : ""}
            </p>
          )}
          {summary && (
            <div className="mt-6 grid gap-3 text-left sm:grid-cols-2">
              <Stat label="Orders in workspace" value={formatNumber(summary.orders)} small />
              <Stat label="Net sales (completed)" value={formatINR(Number(summary.net_sales_completed))} small />
              <Stat label="Products" value={formatNumber(summary.products)} small />
              <Stat label="Customers" value={formatNumber(summary.customers)} small />
            </div>
          )}
          <div className="mt-6 flex flex-wrap justify-center gap-2">
            {[
              ["/app", "Open the command center"],
              ["/app/sales", "Explore sales"],
              ["/app/customers", "See customers"],
              ["/app/products", "See products"],
            ].map(([href, label]) => (
              <a key={href} href={href} className="rounded-full border border-line px-4 py-2 text-sm font-medium hover:border-fg/40">
                {label}
              </a>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function Stat({ label, value, sub, tone, small }: { label: string; value: string; sub?: string; tone?: "good" | "bad"; small?: boolean }) {
  return (
    <div className="rounded-2xl border border-line bg-canvas p-4">
      <p className="text-xs text-muted">{label}</p>
      <p className={`mt-1 font-bold tabular ${small ? "text-lg" : "text-3xl"} ${tone === "good" ? "text-mor" : tone === "bad" ? "text-sindoor" : ""}`}>
        {value}
        {sub && <span className="ml-2 text-sm font-medium text-muted">{sub}</span>}
      </p>
    </div>
  );
}
