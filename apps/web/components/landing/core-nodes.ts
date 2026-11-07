/** Node metadata for the hero data core (kept separate so three.js stays lazy-loaded). */
export const CORE_LEGEND = [
  { key: "sales", label: "Sales", detail: "₹18.5L net · ▼6.2%", color: "#7357e8" },
  { key: "customers", label: "Customers", detail: "1,284 active · 142 lapsed", color: "#3296f5" },
  { key: "inventory", label: "Inventory", detail: "17 SKUs at risk", color: "#c6a66b" },
  { key: "forecasts", label: "Forecasts", detail: "+4% next 14 days", color: "#9d8bf2" },
] as const;
