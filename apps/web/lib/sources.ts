/* Mirrors apps/api/app/schemas/source.py */

export type Schedule = "manual" | "hourly" | "daily";
export type SourceStatus = "never" | "running" | "ok" | "unchanged" | "failed";
export type ImportSource = {
  id: string;
  name: string;
  url: string;
  schedule: Schedule;
  enabled: boolean;
  last_run_at: string | null;
  last_status: SourceStatus;
  last_message: string | null;
  last_new_orders: number;
  failures: number;
  created_at: string;
};
