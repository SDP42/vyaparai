/* Mirrors apps/api/app/schemas/digest.py */

export type DigestKind = "daily" | "weekly";
export type Headline = { key: string; label: string; value: string; change: string | null; unit: "pct" | "pts"; text: string };
export type Action = { kind: string; title: string; detail: string; link: string };
export type DigestPreview = {
  kind: DigestKind;
  as_of: string;
  label: string;
  subject: string;
  versus: string;
  headline: Headline[];
  action: Action;
  more_actions: Action[];
  watch: string | null;
  notes: string[];
  stale_days: number;
  text: string;
};
export type DigestSettings = {
  enabled: boolean;
  frequency: "daily" | "weekly" | "both";
  send_hour: number;
  weekday: number;
  recipients: string[];
  email_configured: boolean;
  timezone: string;
  last_daily_for: string | null;
  last_weekly_for: string | null;
};
export type DigestRow = { id: string; kind: string; period_end: string; subject: string; text: string; status: string; sent_to: string[]; error: string | null; created_at: string };
