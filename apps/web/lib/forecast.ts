import type { Job } from "./api";

/* Mirrors apps/api/app/schemas/forecast.py */

export type RunInfo = { version?: number; status?: string; note?: string | null; id: string; created_at: string; as_of: string; horizon: number; history_days: number; n_series: number; seconds: number };
export type ForecastKpis = {
  units_next: number;
  units_next_low: number;
  units_next_high: number;
  units_last: number;
  units_change_pct: number | null;
  net_next: number;
  net_last_est: number;
  net_change_pct: number | null;
};
export type Mover = { sku: string; name: string; units_last: number; units_next: number; change_pct: number };
export type TotalsHistory = { d: string; units: number };
export type TotalsForecast = { d: string; p10: number; p50: number; p90: number; net: number };
export type TotalsBacktest = { d: string; a: number; p: number };
export type Accuracy = {
  windows: number;
  wape?: number | null;
  bias?: number | null;
  wape_seasonal_naive?: number | null;
  fva?: number | null;
  gate_passed?: boolean;
  series_beating_naive?: number | null;
  interval_coverage_80?: number | null;
  interval_coverage_80_raw?: number | null;
  interval_scale?: number;
  covariates?: { names: string[]; used: boolean; wape_without: number | null; wape_with: number | null; required_gain: number };
  candidates?: Record<string, number | null>;
  tuning?: { trials: number; used: boolean; default_wape: number | null; best_wape: number | null; note?: string };
  engine_version?: string;
};
export type ModelCard = {
  models: Record<string, number>;
  features: string[];
  backtest_windows: number;
  horizon_days: number;
  assumptions: string[];
  limits: string[];
};
export type ForecastOverview = {
  run: RunInfo;
  currency: string;
  stale: boolean;
  latest_data_date: string | null;
  kpis: ForecastKpis;
  totals: { history: TotalsHistory[]; forecast: TotalsForecast[]; backtest: TotalsBacktest[] };
  accuracy: Accuracy;
  model_card: ModelCard;
  risers: Mover[];
  fallers: Mover[];
  confidence_counts: Record<"high" | "medium" | "low", number>;
  warnings: string[];
  signals: { weather?: WeatherSignal };
};
export type WeatherSignal = { status: "ok" | "off" | "no_location" | "unavailable"; city?: string | null; used?: boolean; note?: string | null; attribution?: string; forecast_days?: number };
export type City = { name: string; state: string; latitude: number; longitude: number };
export type WeatherStatus = { enabled: boolean; free_tier: boolean; city: string | null; latitude: number | null; longitude: number | null; attribution: string; note: string | null };
export type NoForecast = { has_forecast: false; can_forecast: boolean; reason: string | null; latest_data_date: string | null; history_days: number };
export type Latest = ForecastOverview | NoForecast;
export const hasForecast = (x: Latest): x is ForecastOverview => !("has_forecast" in x);

export type ProductForecastRow = {
  sku: string;
  name: string;
  category: string | null;
  model: "lightgbm" | "theta" | "seasonal_average";
  pattern: string;
  confidence: "high" | "medium" | "low";
  backtest_wape: number | null;
  backtest_bias: number | null;
  units_last: number;
  units_next: number;
  units_next_low: number;
  units_next_high: number;
  change_pct: number | null;
  spark: number[];
};
export type ProductForecastPage = { run_id: string; horizon: number; total: number; limit: number; offset: number; items: ProductForecastRow[] };
export type ProductDetail = ProductForecastRow & {
  net_per_unit: number | null;
  data: { hist_start: string; hist: number[]; fc_start: string; p10: number[]; p50: number[]; p90: number[]; backtest: { d: string; a: number; p: number }[] };
};
export type { Job };

export type RunVersion = {
  id: string;
  version: number;
  status: "active" | "superseded" | "rejected";
  created_at: string;
  as_of: string;
  history_days: number;
  n_series: number;
  seconds: number;
  wape: number | null;
  fva: number | null;
  gate_passed: boolean | null;
  interval_coverage: number | null;
  models: Record<string, number>;
  options: { tune_trials?: number; peak_uplift_pct?: number };
  tuning: Accuracy["tuning"] | null;
  covariates: Accuracy["covariates"] | null;
  note: string | null;
};
