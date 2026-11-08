"use client";

import { API_URL, clearSession, loadSession } from "./session";

/** Error shape returned by the API: {"error": {code, message, details, request_id}}. */
export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details: unknown = null,
    public requestId: string | null = null,
  ) {
    super(message);
  }
}

function token(): string | null {
  const s = loadSession();
  return s && s.kind === "account" ? s.token : null;
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const t = token();
  if (t) headers.set("Authorization", `Bearer ${t}`);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, "network", "Could not reach the Vyapar API. Is it running on port 8000?");
  }
  if (res.status === 401) {
    clearSession();
    if (typeof window !== "undefined") window.location.href = "/login";
    throw new ApiError(401, "unauthenticated", "Your session has expired. Please sign in again.");
  }
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    const e = body?.error;
    throw new ApiError(res.status, e?.code ?? "http_error", e?.message ?? `Request failed (${res.status})`, e?.details ?? null, e?.request_id ?? null);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

/** Download an authenticated file (e.g. the validation error CSV). */
export async function download(path: string, filename: string) {
  const res = await fetch(`${API_URL}${path}`, { headers: { Authorization: `Bearer ${token() ?? ""}` } });
  if (!res.ok) throw new ApiError(res.status, "download_failed", "Could not download the file");
  const url = URL.createObjectURL(await res.blob());
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

// ---------- types mirrored from the API (apps/api/app/schemas) ----------

export type Workspace = { id: string; name: string; slug: string; currency: string; timezone: string; role: string };

export type FieldSpec = { key: string; label: string; required: boolean; kind: string };
export type ColumnInfo = { name: string; inferred_type: string; empty_pct: number; samples: string[] };
export type Inspection = {
  row_count: number;
  headers: string[];
  columns: ColumnInfo[];
  sample_rows: string[][];
  suggested_mapping: Record<string, string>;
  fields: FieldSpec[];
};
export type ValidationSummary = {
  rows_total: number;
  rows_valid: number;
  rows_invalid: number;
  error_count: number;
  errors_by_field: Record<string, number>;
  sample_errors: { row: number; field: string; column: string; message: string; value: string }[];
  warnings: string[];
  preview: {
    orders: number;
    products: number;
    customers: number;
    date_from: string | null;
    date_to: string | null;
    net_sales_completed: string;
  };
};
export type DatasetStatus = "uploaded" | "mapped" | "validated" | "imported" | "failed";
export type Dataset = {
  id: string;
  name: string;
  source_filename: string;
  file_type: string | null;
  file_size_bytes: number | null;
  row_count: number | null;
  status: DatasetStatus;
  column_mapping: { fields: Record<string, string>; date_order?: "dmy" | "mdy" | "ymd" } | null;
  created_at: string;
  inspection?: Inspection | null;
  validation?: ValidationSummary | null;
};
export type Job = {
  id: string;
  status: "queued" | "running" | "succeeded" | "failed" | "cancelled";
  progress: number;
  rows_accepted: number | null;
  rows_rejected: number | null;
  error_message: string | null;
  result: Record<string, number> | null;
};
export type DataSummary = {
  orders: number;
  order_items: number;
  products: number;
  customers: number;
  date_from: string | null;
  date_to: string | null;
  net_sales_completed: string;
};
export type Page<T> = { items: T[]; total: number; limit: number; offset: number };
