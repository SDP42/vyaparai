/* Mirrors apps/api/app/schemas/inventory.py */

export type StockStatus = "urgent" | "reorder" | "ok" | "overstock" | "dead";
export type InventoryItem = {
  sku: string;
  name: string;
  category: string | null;
  snapshot_date: string;
  snapshot_on_hand: string;
  sold_since: string;
  on_hand: string;
  daily_rate: string;
  cover_days: string | null;
  run_out_date: string | null;
  lead_time_days: number;
  pack_size: string;
  status: StockStatus;
  reason: string;
  order_qty: string;
  unit_cost: string | null;
  order_cost: string | null;
  cash_tied: string | null;
  excess_cash: string | null;
  forecast_based: boolean;
};
export type InventoryOverview = {
  as_of: string | null;
  items: InventoryItem[];
  summary: { tracked: number; urgent: number; reorder: number; overstock: number; dead: number; missing_stock: number; cash_tied: string; excess_cash: string; dead_cash: string; order_cost: string };
  has_forecast: boolean;
};
export type ImportResult = { imported: number; unmatched: number; unmatched_skus: string[]; rejected_count: number; rejected: { row: number; sku?: string; reason: string }[] };
