/* Mirrors apps/api/app/schemas/costs.py */

export type CostStatus = "margin_leak" | "passed_on" | "cost_down" | "stable" | "no_cost" | "new" | "too_few";
export type CostItem = {
  sku: string;
  name: string;
  category: string | null;
  status: CostStatus;
  cost_prev: string | null;
  cost_now: string | null;
  cost_change_pct: string | null;
  price_prev: string | null;
  price_now: string | null;
  price_change_pct: string | null;
  margin_prev_pct: string | null;
  margin_now_pct: string | null;
  units: string | null;
  leak_amount: string | null;
  suggested_price: string | null;
  suggested_increase_pct: string | null;
};
export type CostOverview = {
  as_of: string | null;
  window_days: number;
  current: { from: string; to: string } | null;
  previous: { from: string; to: string } | null;
  items: CostItem[];
  summary: { margin_leaks: number; leak_amount: string; cost_up: number; cost_down: number; no_cost: number; unit_coverage_pct: string | null };
};
export type CostHistory = { sku: string; weeks: { week_start: string; units: string; cost: string | null; price: string | null }[] };
