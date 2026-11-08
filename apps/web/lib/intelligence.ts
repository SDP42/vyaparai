import type { Meta } from "./analytics";

/* Mirrors apps/api/app/schemas/intelligence.py */

export type CustomerParams = { as_of: string; lookback_days: number; new_days: number; active_days: number; lapse_days: number };
export type SegmentRow = {
  segment: string;
  help: string;
  customers: number;
  share: string | null;
  net: string;
  net_share: string | null;
  avg_orders: string | null;
  avg_recency_days: string | null;
};
export type CustomersSummary = {
  params: CustomerParams;
  currency: string;
  customers: number;
  net: string;
  repeat_customers: number;
  repeat_rate: string | null;
  revenue_per_customer: string | null;
  avg_orders_per_customer: string | null;
  top_decile_share: string | null;
  lapsed_regulars: number;
  walk_in_share: string | null;
  status_counts: Record<string, number>;
  segments: SegmentRow[];
  rfm_grid: number[][];
  warnings: string[];
};
export type CustomerOut = {
  key: string;
  region: string | null;
  city: string | null;
  first_order: string;
  last_order: string;
  orders: number;
  net: string;
  aov: string;
  recency_days: number;
  r: number;
  f: number;
  m: number;
  segment: string;
  status: string;
};
export type CustomerList = { params: CustomerParams; total: number; limit: number; offset: number; items: CustomerOut[] };
export type CohortRow = { cohort: string; size: number; counts: number[]; retention: (string | null)[] };
export type Cohorts = { as_of: string; months: number; cohorts: CohortRow[]; warnings: string[] };

export type ProductItem = {
  key: string;
  name: string;
  category: string | null;
  units: string;
  net: string;
  gross: string;
  discount: string;
  discount_rate: string | null;
  discounted_line_share: string | null;
  margin_amount: string | null;
  margin_pct: string | null;
  cost_coverage_pct: string | null;
  share: string | null;
  cumulative_share: string;
  abc: "A" | "B" | "C";
  quadrant: "Star" | "Workhorse" | "Puzzle" | "Dog" | "Unknown";
  previous_net: string | null;
  change_pct: string | null;
  flags: string[];
};
export type CategoryPerf = {
  category: string;
  products: number;
  units: string;
  net: string;
  share: string | null;
  discount_rate: string | null;
  margin_amount: string | null;
  margin_pct: string | null;
  cost_coverage_pct: string | null;
  previous_net: string | null;
  change_pct: string | null;
};
export type QuadrantRow = { quadrant: string; help: string; products: number; net: string };
export type Portfolio = { quadrants: QuadrantRow[]; abc: Record<string, number>; discount_heavy: number; declining: number; rising: number };
export type ProductsResponse = {
  meta: Meta;
  overall_margin_pct: string | null;
  overall_discount_rate: string | null;
  items: ProductItem[];
  categories: CategoryPerf[];
  portfolio: Portfolio;
  warnings: string[];
};
export type BasketPair = {
  a: string;
  a_name: string;
  b: string;
  b_name: string;
  orders: number;
  support: string;
  confidence_a_to_b: string;
  confidence_b_to_a: string;
  lift: string;
};
export type BasketResponse = {
  meta: Meta;
  orders: number;
  multi_item_orders: number;
  multi_item_share: string | null;
  avg_items_per_order: string | null;
  pairs: BasketPair[];
  pairs_found: number;
  min_orders: number;
  note: string;
};
