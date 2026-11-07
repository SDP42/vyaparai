/**
 * Deterministic DEMO data for the landing page and persona dashboards.
 * Clearly labelled as demo in the UI; replaced by API data in Phase F2.
 */

function mulberry32(seed: number) {
  return () => {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export type DailyPoint = { day: number; label: string; sales: number; forecast?: number };

/** 30 days actual + 14 days forecast, with a festival bump around day 36. */
export function salesSeries(seed = 7): DailyPoint[] {
  const rnd = mulberry32(seed);
  const out: DailyPoint[] = [];
  for (let d = 0; d < 44; d++) {
    const weekly = [0.92, 0.88, 0.95, 1.0, 1.08, 1.22, 1.18][d % 7];
    const trend = 1 + d * 0.006;
    const festival = d >= 33 && d <= 38 ? 1 + 0.35 * Math.sin(((d - 33) / 5) * Math.PI) : 1;
    const base = 58000 * weekly * trend * festival;
    const label = `D${d + 1}`;
    if (d < 30) out.push({ day: d, label, sales: Math.round(base * (0.9 + rnd() * 0.2)) });
    else out.push({ day: d, label, sales: NaN, forecast: Math.round(base) });
  }
  return out;
}

export const KPIS = [
  { key: "net_sales", label: "Net sales", value: 1846320, delta: 8.4, format: "inr" as const, hint: "Excl. GST, returns & cancellations" },
  { key: "gross_margin", label: "Gross margin", value: 23.8, delta: -1.2, format: "pct" as const, hint: "Net sales − COGS at snapshot cost" },
  { key: "orders", label: "Orders", value: 3412, delta: 5.1, format: "num" as const, hint: "Completed orders only" },
  { key: "aov", label: "Avg order value", value: 541, delta: 3.1, format: "inr" as const, hint: "Net sales ÷ completed orders" },
];

export const TOP_PRODUCTS = [
  { sku: "ATT-5KG", name: "Aashirvaad Atta 5kg", category: "Staples", revenue: 214560, change: 12.4 },
  { sku: "GHE-1L", name: "Desi Ghee 1L", category: "Dairy", revenue: 168320, change: 21.9 },
  { sku: "DRY-500", name: "Dry Fruit Gift Box", category: "Festive", revenue: 151200, change: 64.2 },
  { sku: "BAS-5KG", name: "Basmati Rice 5kg", category: "Staples", revenue: 132880, change: -3.8 },
  { sku: "OIL-5L", name: "Mustard Oil 5L", category: "Staples", revenue: 98450, change: 1.6 },
];

export const RECOMMENDATIONS = [
  {
    id: "r1",
    title: "Reorder Dry Fruit Gift Boxes before Diwali",
    rationale: "Forecast demand over the 9-day lead time is 184 units; 62 on hand.",
    impact: "₹38K–₹52K protected revenue",
    confidence: "Medium",
    evidence: ["forecast:DRY-500@v3", "inventory:snapshot 2026-11-06"],
  },
  {
    id: "r2",
    title: "Review discounting on Basmati Rice 5kg",
    rationale: "Discount rate rose from 4% to 11% while units stayed flat.",
    impact: "≈ ₹9K/month margin",
    confidence: "High",
    evidence: ["metric:discount_rate v1", "metric:units v1"],
  },
];
