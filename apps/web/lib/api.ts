"use client";

import { API_URL, clearSession, ensureToken, loadSession, refreshAccessToken } from "./session";

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

async function token(): Promise<string | null> {
  const s = loadSession();
  return s ? ensureToken() : null;
}

function expired(): never {
  clearSession();
  if (typeof window !== "undefined") window.location.href = "/login";
  throw new ApiError(401, "unauthenticated", "Your session has expired. Please sign in again.");
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  let t = await token();
  if (t) headers.set("Authorization", `Bearer ${t}`);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { ...init, headers });
    if (res.status === 401 && t) {
      // The 15-minute access token ran out: renew it once from the cookie and retry.
      t = await refreshAccessToken();
      if (!t) expired();
      headers.set("Authorization", `Bearer ${t}`);
      res = await fetch(`${API_URL}${path}`, { ...init, headers });
    }
  } catch (e) {
    if (e instanceof ApiError) throw e;
    throw new ApiError(0, "network", "Could not reach the Vyapar API. Is it running on port 8000?");
  }
  if (res.headers.get("x-vyapar-offline") && typeof window !== "undefined") window.dispatchEvent(new Event("vyapar:offline-data"));
  if (res.status === 401) expired();
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
  const res = await fetch(`${API_URL}${path}`, { headers: { Authorization: `Bearer ${(await token()) ?? ""}` } });
  if (!res.ok) throw new ApiError(res.status, "download_failed", "Could not download the file");
  const url = URL.createObjectURL(await res.blob());
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

/** POST and read a server-sent-event stream, calling `on(event, data)` for each event. */
export async function streamAnswer(path: string, body: unknown, on: (event: string, data: unknown) => void): Promise<void> {
  const send = async (token: string | null) =>
    fetch(`${API_URL}${path}`, { method: "POST", headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) }, body: JSON.stringify(body) });
  let res: Response;
  try {
    res = await send(await token());
    if (res.status === 401) {
      const t = await refreshAccessToken();
      if (!t) expired();
      res = await send(t);
    }
  } catch (e) {
    if (e instanceof ApiError) throw e;
    throw new ApiError(0, "network", "Could not reach the Vyapar API. Is it running on port 8000?");
  }
  if (!res.ok || !res.body) {
    const b = await res.json().catch(() => null);
    throw new ApiError(res.status, b?.error?.code ?? "http_error", b?.error?.message ?? `Request failed (${res.status})`);
  }
  const reader = res.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    let i: number;
    while ((i = buf.indexOf("\n\n")) >= 0) {
      const block = buf.slice(0, i); buf = buf.slice(i + 2);
      const ev = /^event: (.*)$/m.exec(block)?.[1]; const data = /^data: (.*)$/m.exec(block)?.[1];
      if (ev && data) on(ev, JSON.parse(data));
    }
  }
}

// ---------- types mirrored from the API (apps/api/app/schemas) ----------

export type Workspace = { id: string; name: string; slug: string; currency: string; timezone: string; role: string; city?: string | null; state?: string | null };

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
  column_mapping: { fields: Record<string, string>; date_order?: "dmy" | "mdy" | "ymd"; remembered?: boolean; profile_name?: string } | null;
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
