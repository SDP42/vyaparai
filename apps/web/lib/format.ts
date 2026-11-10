/** Indian number formatting: ₹12,34,567 and compact ₹4.2L / ₹1.3Cr. */
const inr = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });
const num = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });

export const formatINR = (v: number) => inr.format(v);
export const formatNumber = (v: number) => num.format(v);

export function formatINRCompact(v: number): string {
  const abs = Math.abs(v);
  if (abs >= 1e7) return `₹${(v / 1e7).toFixed(2)}Cr`;
  if (abs >= 1e5) return `₹${(v / 1e5).toFixed(1)}L`;
  if (abs >= 1e3) return `₹${(v / 1e3).toFixed(1)}K`;
  return formatINR(v);
}

export const formatPct = (v: number, digits = 1) => `${v > 0 ? "+" : ""}${v.toFixed(digits)}%`;

/** The API sends UTC times without a timezone marker (SQLite drops it); read them as UTC, not local. */
export function parseUtc(iso: string): Date {
  return new Date(/[zZ]$|[+-]\d\d:?\d\d$/.test(iso) ? iso : `${iso}Z`);
}
