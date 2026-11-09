/* Mirrors apps/api/app/schemas/alerts.py */

export type Severity = "high" | "medium" | "info";
export type AlertStatus = "open" | "dismissed" | "resolved";
export type AlertItem = {
  id: string;
  key: string;
  rule: string;
  severity: Severity;
  title: string;
  detail: string;
  evidence: Record<string, number | null>;
  link: string;
  status: AlertStatus;
  first_seen: string;
  last_seen: string;
};
export type AlertList = { as_of: string | null; counts: Record<Severity, number>; items: AlertItem[] };
