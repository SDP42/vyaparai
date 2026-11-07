/**
 * Illustrative demo data for the marketing site. One consistent story across sections:
 * October net sales fell 6.2% vs September, driven by fewer orders (stock-outs in Staples),
 * partly offset by a higher average order value. Clearly labelled as demo in the UI.
 */

export const PERIOD = { current: "Oct 2026", previous: "Sep 2026" };

export const KPIS = [
  { key: "net_sales", label: "Net sales", value: 1846320, prev: 1968400, format: "inr" as const },
  { key: "gross_profit", label: "Gross profit", value: 439400, prev: 453500, format: "inr" as const },
  { key: "orders", label: "Orders", value: 3412, prev: 3745, format: "num" as const },
  { key: "aov", label: "Avg order value", value: 541, prev: 525, format: "inr" as const },
];

export const pctChange = (v: number, p: number) => ((v - p) / p) * 100;

function rng(seed: number) {
  return () => {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export type RevenuePoint = {
  day: string;
  actual?: number;
  forecast?: number;
  band?: [number, number];
};

/** 31 days of October actuals (with a stock-out dip in days 9–17) + 14-day forecast with interval. */
export function revenueSeries(): RevenuePoint[] {
  const r = rng(42);
  const out: RevenuePoint[] = [];
  for (let d = 1; d <= 45; d++) {
    const weekly = [0.9, 0.86, 0.93, 0.98, 1.06, 1.22, 1.16][d % 7];
    const dip = d >= 9 && d <= 17 ? 0.82 : 1;
    const base = 59000 * weekly * dip;
    if (d <= 31) {
      out.push({ day: `${d} Oct`, actual: Math.round(base * (0.94 + r() * 0.12)) });
    } else {
      const f = Math.round(61000 * weekly * (1 + (d - 31) * 0.004));
      const w = 0.08 + (d - 31) * 0.008;
      out.push({ day: `${d - 31} Nov`, forecast: f, band: [Math.round(f * (1 - w)), Math.round(f * (1 + w))] });
    }
  }
  // connect the forecast to the last actual
  const last = out[30];
  out[30] = { ...last, forecast: last.actual, band: [last.actual!, last.actual!] };
  return out;
}

export const CATEGORIES = [
  { name: "Staples", share: 42, color: "#7357e8" },
  { name: "Dairy", share: 18, color: "#3296f5" },
  { name: "Snacks", share: 14, color: "#9d8bf2" },
  { name: "Personal care", share: 12, color: "#7cbcf9" },
  { name: "Household", share: 9, color: "#c6a66b" },
  { name: "Beverages", share: 5, color: "#4b5878" },
];

export const TOP_PRODUCTS = [
  { sku: "ATT-5KG", name: "Wheat atta 5 kg", category: "Staples", revenue: 214560, change: -18.4, note: "stock-out 6 days" },
  { sku: "GHE-1L", name: "Desi ghee 1 L", category: "Dairy", revenue: 168320, change: 4.2 },
  { sku: "TUR-1KG", name: "Toor dal 1 kg", category: "Staples", revenue: 151200, change: -22.7, note: "stock-out 9 days" },
  { sku: "BAS-5KG", name: "Basmati rice 5 kg", category: "Staples", revenue: 132880, change: -3.8 },
  { sku: "OIL-5L", name: "Mustard oil 5 L", category: "Staples", revenue: 98450, change: 1.6 },
];

export const DRIVERS = [
  { label: "Volume", value: -162000, note: "333 fewer orders" },
  { label: "Price", value: 52000, note: "AOV +3.0%" },
  { label: "Mix", value: -12000, note: "shift to snacks" },
];

export const INSIGHTS = [
  { tone: "danger" as const, title: "Staples drove 64% of the decline", body: "Two top SKUs were out of stock for 6–9 days." },
  { tone: "success" as const, title: "Basket size is growing", body: "AOV rose 3.0% to ₹541 with steady discount rates." },
  { tone: "warning" as const, title: "142 regulars have lapsed", body: "No purchase in 45 days; 61% bought Staples last." },
];

export const RECOMMENDATIONS = [
  {
    title: "Draft a reorder for Wheat atta 5 kg and Toor dal 1 kg",
    impact: "₹38K–₹55K protected next month",
    confidence: "Medium",
    evidence: ["inventory: 2 stock-outs in Oct", "forecast: demand +4% (v3)"],
  },
  {
    title: "Win back 142 lapsed Staples customers",
    impact: "≈ ₹21K if 15% return",
    confidence: "Low",
    evidence: ["RFM segment: lapsed-45d", "metric: repeat_customers v1"],
  },
];

export const RFM = Array.from({ length: 25 }, (_, i) => {
  const r = Math.floor(i / 5);
  const f = i % 5;
  return Math.max(0.08, 1 - Math.abs(r - f) * 0.22 - (4 - r) * 0.06);
});
