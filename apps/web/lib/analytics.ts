"use client";

import { useEffect, useRef, useState } from "react";
import { ApiError, api } from "./api";

/* ------------------------------------------------------------------ types (mirror apps/api/app/schemas/analytics.py) */

export type Unit = "inr" | "count" | "percent";
export type Compare = "previous_period" | "previous_year" | "none";
export type Granularity = "day" | "week" | "month";
export type Dimension = "category" | "channel" | "region" | "product";

export type MetricDef = {
  key: string;
  label: string;
  unit: Unit;
  version: number;
  definition: string;
  includes: string;
  excludes: string;
  good_direction: "up_good" | "down_good" | "neutral";
};
export type MetricRegistry = { registry_version: number; eligibility: string; assumptions: string[]; metrics: MetricDef[] };

export type Kpi = {
  key: string;
  label: string;
  unit: Unit;
  version: number;
  value: string | null;
  previous: string | null;
  change: string | null;
  change_pct: string | null;
  good_direction: "up_good" | "down_good" | "neutral";
  compare_in_points: boolean;
};

export type Period = { date_from: string; date_to: string; days: number };
export type Meta = {
  currency: string;
  timezone: string;
  has_data: boolean;
  period: Period;
  compare: (Period & { mode: Exclude<Compare, "none">; label: string }) | null;
  granularity: Granularity;
  filters: { categories: string[]; channels: string[]; regions: string[]; skus: string[] };
  metric_versions: Record<string, number>;
  freshness: { last_order_date: string | null; first_order_date: string | null; last_import_at: string | null };
  coverage: {
    days_in_period: number;
    days_with_data: number;
    compare_days_with_data: number | null;
    cost_coverage_pct: string | null;
    excluded_orders_by_status: Record<string, number>;
    anonymous_order_share: string | null;
  };
};

export type TrendPoint = {
  start: string;
  label: string;
  net: string;
  orders: number;
  units: string;
  aov: string | null;
  previous_net: string | null;
  previous_label: string | null;
};
export type MixRow = {
  key: string;
  label: string;
  net: string;
  previous_net: string | null;
  delta: string | null;
  share: string | null;
  share_of_change: string | null;
  units: string;
  orders: number;
};
export type WeekdayRow = { weekday: number; label: string; avg_net: string; days: number };
export type ProductRow = {
  sku: string;
  name: string;
  category: string | null;
  net: string;
  previous_net: string | null;
  delta: string | null;
  units: string;
  previous_units: string | null;
};
export type Insight = { id: string; tone: "good" | "bad" | "neutral" | "warning"; title: string; body: string; evidence: string[] };

export type Overview = {
  meta: Meta;
  headline: Kpi[];
  secondary: Kpi[];
  trend: TrendPoint[];
  category_mix: MixRow[];
  channel_mix: MixRow[];
  region_mix: MixRow[];
  weekday: WeekdayRow[];
  top_products: ProductRow[];
  bottom_products: ProductRow[];
  insights: Insight[];
  warnings: string[];
};

export type DriverEffect = { key: string; label: string; amount: string; explanation: string };
export type ProductMove = {
  sku: string;
  name: string;
  category: string | null;
  units_prev: string;
  units_cur: string;
  net_prev: string;
  net_cur: string;
  delta: string;
};
export type Drivers = {
  meta: Meta;
  net_sales_current: string;
  net_sales_previous: string | null;
  net_change: string | null;
  effects: DriverEffect[];
  method: string;
  caveat: string;
  contributions: MixRow[];
  contribution_dimension: Dimension;
  biggest_decliners: ProductMove[];
  biggest_gainers: ProductMove[];
  continuing_products: number;
  new_products: number;
  discontinued_products: number;
  insights: Insight[];
  warnings: string[];
};

export type TransactionRow = {
  order_id: string;
  date: string;
  sku: string;
  product: string;
  category: string | null;
  quantity: string;
  unit_price: string;
  discount: string;
  net: string;
  customer: string | null;
  channel: string | null;
};
export type Transactions = { meta: Meta; total_lines: number; total_net: string; limit: number; offset: number; items: TransactionRow[] };

export type FilterOptions = {
  categories: string[];
  channels: string[];
  regions: string[];
  first_order_date: string | null;
  last_order_date: string | null;
  default_from: string;
  default_to: string;
  has_data: boolean;
};

/* ------------------------------------------------------------------ query state */

export type Query = {
  from: string;
  to: string;
  compare: Compare;
  category: string[];
  channel: string[];
  region: string[];
  sku: string[];
};

export function toSearch(q: Query, extra: Record<string, string | number | undefined> = {}): string {
  const p = new URLSearchParams();
  p.set("from", q.from);
  p.set("to", q.to);
  p.set("compare", q.compare);
  for (const k of ["category", "channel", "region", "sku"] as const) for (const v of q[k]) p.append(k, v);
  for (const [k, v] of Object.entries(extra)) if (v !== undefined && v !== "") p.set(k, String(v));
  return p.toString();
}

/* ------------------------------------------------------------------ data hook */

export type Fetched<T> = { data: T | null; error: string | null; loading: boolean };

/** Fetches ``path`` whenever ``deps`` change; ignores stale responses and keeps the previous data while loading. */
export function useApi<T>(path: string | null, deps: unknown[]): Fetched<T> {
  const [state, setState] = useState<Fetched<T>>({ data: null, error: null, loading: path !== null });
  const seq = useRef(0);
  useEffect(() => {
    if (path === null) return;
    const my = ++seq.current;
    setState((s) => ({ ...s, loading: true, error: null }));
    api<T>(path)
      .then((data) => {
        if (my === seq.current) setState({ data, error: null, loading: false });
      })
      .catch((e: unknown) => {
        if (my === seq.current)
          setState((s) => ({ data: s.data, error: e instanceof ApiError ? e.message : "Something went wrong", loading: false }));
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, ...deps]);
  return state;
}

/* ------------------------------------------------------------------ display helpers */

export const num = (x: string | null | undefined): number => (x == null ? NaN : Number(x));

const OPPOSITE_DOWN_GOOD = new Set(["down_good"]);

/** Tone of a change for colouring: good / bad / neutral. */
export function changeTone(kpi: Pick<Kpi, "change" | "good_direction">): "good" | "bad" | "neutral" {
  const c = num(kpi.change);
  if (!Number.isFinite(c) || c === 0 || kpi.good_direction === "neutral") return "neutral";
  const up = c > 0;
  return up === !OPPOSITE_DOWN_GOOD.has(kpi.good_direction) ? "good" : "bad";
}

export function shortDate(iso: string): string {
  const d = new Date(`${iso}T00:00:00`);
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
}
export function longDate(iso: string): string {
  const d = new Date(`${iso}T00:00:00`);
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}
export function addDays(iso: string, n: number): string {
  const d = new Date(`${iso}T00:00:00`);
  d.setDate(d.getDate() + n);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
