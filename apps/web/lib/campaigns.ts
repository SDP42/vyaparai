/* Mirrors apps/api/app/schemas/campaigns.py */

export type PlaybookEntry = {
  segment: string;
  help: string;
  kind: string;
  goal: string;
  idea: string;
  customers: number;
  default_max_discount: number;
  assumed_redemption: string;
};
export type OfferRow = {
  sku: string;
  name: string;
  segment_units: string;
  price: string;
  margin_pct: string | null;
  safe_discount_pct: string | null;
  discount_pct: string;
  margin_after_pct: string | null;
  flag: "no_cost" | "no_safe_discount" | null;
};
export type AudienceRow = {
  key: string;
  city: string | null;
  last_order: string;
  recency_days: number;
  orders: number;
  net: string;
  overdue_ratio: string | null;
  reason: string;
  product: string;
  discount_pct: string;
  holdout: boolean;
  consent_status: string;
  message: string;
};
export type CampaignPlan = {
  segment: string;
  kind: string;
  goal: string;
  idea: string;
  as_of: string;
  currency: string;
  audience: { total: number; contact: number; holdout: number };
  params: { max_discount: number; margin_floor: number; holdout_pct: number; language: string; valid_days: number };
  ladder: { step: number; name: string; discount_pct: number; when: string }[];
  offers: OfferRow[];
  projection: { assumed_redemption_pct: string; expected_redeemers: string; avg_order_value: string; expected_sales: string; avg_discount_pct: string; expected_discount_given: string; note: string };
  consent_note: string;
  warnings: string[];
  rows: AudienceRow[];
  total_rows: number;
  limit: number;
  offset: number;
};
