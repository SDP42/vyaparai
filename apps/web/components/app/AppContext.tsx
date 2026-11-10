"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type FormEvent, type ReactNode } from "react";
import { ApiError, api, type Workspace } from "@/lib/api";
import { addDays, type Compare, type FilterOptions, type MetricRegistry, type Query } from "@/lib/analytics";

/* ------------------------------------------------------------------ workspace */

type WorkspaceCtx = { workspace: Workspace; workspaces: Workspace[]; canImport: boolean; switchTo: (id: string) => void; reload: () => Promise<void> };
const WorkspaceContext = createContext<WorkspaceCtx | null>(null);

export function useWorkspace(): WorkspaceCtx {
  const v = useContext(WorkspaceContext);
  if (!v) throw new Error("useWorkspace must be used inside <WorkspaceProvider>");
  return v;
}

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [workspaces, setWorkspaces] = useState<Workspace[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [chosen, setChosen] = useState<string | null>(null);
  useEffect(() => {
    try {
      setChosen(localStorage.getItem("vyapar.workspace"));
    } catch {
      /* ignore */
    }
  }, []);

  const load = useCallback(async () => {
    try {
      setWorkspaces(await api<Workspace[]>("/workspaces"));
      setError(null);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not load your workspace");
    }
  }, []);
  useEffect(() => {
    load();
  }, [load]);

  if (error) {
    return (
      <div className="grid min-h-dvh place-items-center bg-canvas p-6">
        <div role="alert" className="max-w-md rounded-2xl border border-sindoor/30 bg-sindoor/5 p-6 text-center">
          <p className="font-semibold text-sindoor">{error}</p>
          <button type="button" onClick={load} className="mt-3 text-sm underline underline-offset-4">
            Try again
          </button>
        </div>
      </div>
    );
  }
  if (workspaces === null) return <div className="min-h-dvh bg-canvas" aria-busy="true" />;
  if (workspaces.length === 0) return <CreateWorkspace onCreated={load} />;

  const workspace = workspaces.find((w) => w.id === chosen) ?? workspaces[0];
  const switchTo = (id: string) => {
    try {
      localStorage.setItem("vyapar.workspace", id);
    } catch {
      /* storage unavailable: the choice lasts for this page only */
    }
    setChosen(id);
  };
  return (
    <WorkspaceContext.Provider value={{ workspace, workspaces, switchTo, reload: load, canImport: ["owner", "admin", "analyst"].includes(workspace.role) }}>
      {children}
    </WorkspaceContext.Provider>
  );
}

function CreateWorkspace({ onCreated }: { onCreated: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const submit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    setBusy(true);
    setError(null);
    try {
      await api("/workspaces", { method: "POST", body: JSON.stringify({ name: String(fd.get("name") ?? "") }) });
      onCreated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create the workspace");
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="grid min-h-dvh place-items-center bg-canvas p-6">
      <form onSubmit={submit} className="w-full max-w-md rounded-3xl border border-line bg-surface p-8">
        <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-sindoor">Step 1 of 2</p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight">Name your business</h1>
        <p className="mt-2 text-sm text-muted">A workspace keeps one business&apos;s data private. You can invite your team later.</p>
        <label className="mt-6 block">
          <span className="mb-1.5 block text-xs text-muted">Business name</span>
          <input name="name" required minLength={2} placeholder="e.g. Kulkarni General Stores" className="w-full rounded-xl border border-line bg-canvas px-4 py-3 outline-none focus:border-haldi" />
        </label>
        {error && (
          <p role="alert" className="mt-3 text-sm text-sindoor">
            {error}
          </p>
        )}
        <button type="submit" disabled={busy} className="mt-5 w-full rounded-xl bg-fg py-3 font-semibold text-canvas hover:bg-sindoor disabled:opacity-60">
          {busy ? "Creating…" : "Create workspace"}
        </button>
      </form>
    </div>
  );
}

/* ------------------------------------------------------------------ analytics period & filters */

export type Preset = "7d" | "30d" | "90d" | "mtd" | "all" | "custom";
export const PRESETS: { key: Preset; label: string }[] = [
  { key: "7d", label: "7 days" },
  { key: "30d", label: "30 days" },
  { key: "90d", label: "90 days" },
  { key: "mtd", label: "Month to date" },
  { key: "all", label: "All data" },
];

type AnalyticsCtx = {
  query: Query;
  preset: Preset;
  options: FilterOptions | null;
  registry: MetricRegistry | null;
  setPreset: (p: Preset) => void;
  setRange: (from: string, to: string) => void;
  setCompare: (c: Compare) => void;
  setFilter: (dim: "category" | "channel" | "region" | "sku", values: string[]) => void;
  toggleFilter: (dim: "category" | "channel" | "region" | "sku", value: string) => void;
  clearFilters: () => void;
  refreshOptions: () => Promise<void>;
  /** Bumps whenever data may have changed (e.g. after an import) so views refetch. */
  dataVersion: number;
};
const AnalyticsContext = createContext<AnalyticsCtx | null>(null);

export function useAnalyticsState(): AnalyticsCtx {
  const v = useContext(AnalyticsContext);
  if (!v) throw new Error("useAnalyticsState must be used inside <AnalyticsProvider>");
  return v;
}

function rangeFor(preset: Preset, o: FilterOptions): [string, string] {
  const to = o.last_order_date ?? o.default_to;
  switch (preset) {
    case "7d":
      return [addDays(to, -6), to];
    case "90d":
      return [addDays(to, -89), to];
    case "mtd":
      return [`${to.slice(0, 7)}-01`, to];
    case "all":
      return [o.first_order_date ?? o.default_from, to];
    default:
      return [addDays(to, -29), to];
  }
}

export function AnalyticsProvider({ children }: { children: ReactNode }) {
  const { workspace } = useWorkspace();
  const base = `/workspaces/${workspace.id}`;
  const [options, setOptions] = useState<FilterOptions | null>(null);
  const [registry, setRegistry] = useState<MetricRegistry | null>(null);
  const [preset, setPresetState] = useState<Preset>("30d");
  const [query, setQuery] = useState<Query | null>(null);
  const [dataVersion, setDataVersion] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const refreshOptions = useCallback(async () => {
    const o = await api<FilterOptions>(`${base}/analytics/filters`);
    setOptions(o);
    setDataVersion((v) => v + 1);
    setQuery((q) => {
      if (q) return q;
      const [from, to] = rangeFor("30d", o);
      return { from, to, compare: "previous_period", category: [], channel: [], region: [], sku: [] };
    });
  }, [base]);

  useEffect(() => {
    refreshOptions().catch((e) => setError(e instanceof ApiError ? e.message : "Could not load analytics options"));
    api<MetricRegistry>(`${base}/metrics`).then(setRegistry).catch(() => {});
  }, [base, refreshOptions]);

  const value = useMemo<AnalyticsCtx | null>(() => {
    if (!query) return null;
    const patch = (p: Partial<Query>) => setQuery((q) => (q ? { ...q, ...p } : q));
    return {
      query,
      preset,
      options,
      registry,
      dataVersion,
      setPreset: (p) => {
        setPresetState(p);
        if (p !== "custom" && options) {
          const [from, to] = rangeFor(p, options);
          patch({ from, to });
        }
      },
      setRange: (from, to) => {
        setPresetState("custom");
        patch({ from, to });
      },
      setCompare: (compare) => patch({ compare }),
      setFilter: (dim, values) => patch({ [dim]: values }),
      toggleFilter: (dim, value) =>
        setQuery((q) => (q ? { ...q, [dim]: q[dim].includes(value) ? q[dim].filter((v) => v !== value) : [...q[dim], value] } : q)),
      clearFilters: () => patch({ category: [], channel: [], region: [], sku: [] }),
      refreshOptions,
    };
  }, [query, preset, options, registry, dataVersion, refreshOptions]);

  if (error) {
    return (
      <p role="alert" className="p-8 text-sindoor">
        {error}
      </p>
    );
  }
  if (!value) return <div className="min-h-[50vh]" aria-busy="true" />;
  return <AnalyticsContext.Provider value={value}>{children}</AnalyticsContext.Provider>;
}
