/* Mirrors apps/api/app/schemas/events.py */

export type EventItem = {
  id: string;
  name: string;
  start: string;
  end: string;
  category: "festival" | "holiday" | "observance" | "cricket" | "season";
  tier: 1 | 2 | 3;
  scope: string;
  regions: string[];
  lead: number;
  tail: number;
  demand: string[];
  notes: string;
  basis: string;
  confidence: "high" | "medium" | "low";
  sources: string[];
  relevance: "core" | "zone";
};
export type RegionInfo = { state: string | null; zones: string[]; states: { state: string; zones: string[] }[] };
export type MatchedProduct = { sku: string; name: string; daily_sales: number; cover_days: number | null; tracked: boolean; at_risk: boolean };
export type Lift = { ratio: number; baseline_per_day: number; window_per_day: number };
export type UpcomingEvent = {
  event: EventItem;
  days_until: number;
  status: "ahead" | "ramping" | "on" | "fading";
  matching_products: number;
  products: MatchedProduct[];
  last_time: { year: number; all: Lift | null; matching: Lift | null } | null;
};
export type EffectRow = { id: string; name: string; start: string; end: string; tier: number; all_products: Lift | null; matching_products: Lift | null; matching_count: number };
