"use client";

import { useState } from "react";
import { ApiError, api } from "@/lib/api";
import { useApi } from "@/lib/analytics";
import { parseUtc } from "@/lib/format";
import { signOut } from "@/lib/session";
import { useWorkspace } from "./AppContext";
import { Tx } from "./Tx";
import { EmptyNote, ErrorNote, Skeleton } from "./analytics/parts";

type Member = { user_id: string; email: string; full_name: string; role: string; persona: string | null; staff_name: string | null; joined_at: string };
type Invite = { id: string; role: string; persona: string | null; expires_at: string; status: string };

const RANK: Record<string, number> = { viewer: 0, analyst: 1, admin: 2, owner: 3 };
/** The job in the shop. It narrows what a person sees and may ask; the role still decides what they may change. */
const JOBS = [
  { key: "owner", label: "Store owner", min: "owner" },
  { key: "ops_manager", label: "Operations manager", min: "admin" },
  { key: "analyst", label: "Data analyst", min: "analyst" },
  { key: "accountant", label: "Accountant (view only)", min: "viewer" },
  { key: "cashier", label: "Counter staff", min: "viewer" },
];
/** Same rule as the server: an owner is only the owner persona, and nobody gets more than their role allows. */
const jobsFor = (role: string) => JOBS.filter((j) => (role === "owner" ? j.key === "owner" : j.key !== "owner" && RANK[j.min] <= RANK[role]));

const ROLES = [
  { key: "viewer", label: "Viewer", note: "Sees dashboards and reports" },
  { key: "analyst", label: "Analyst", note: "Also imports data and runs forecasts" },
  { key: "admin", label: "Admin", note: "Also manages people and settings" },
  { key: "owner", label: "Owner", note: "Everything, including other owners" },
];

export function TeamPage() {
  const { workspace } = useWorkspace();
  const isAdmin = ["owner", "admin"].includes(workspace.role);
  const isOwner = workspace.role === "owner";
  const base = `/workspaces/${workspace.id}`;
  const [version, setVersion] = useState(0);
  const [err, setErr] = useState<string | null>(null);
  const [role, setRole] = useState("viewer");
  const [job, setJob] = useState("");
  const [link, setLink] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const members = useApi<Member[]>(`${base}/members`, [version]);
  const invites = useApi<Invite[]>(isAdmin ? `${base}/invitations` : null, [version]);
  const assignable = ROLES.filter((r) => isOwner || r.key !== "owner");

  const run = async (fn: () => Promise<unknown>) => {
    setErr(null);
    try {
      await fn();
      setVersion((v) => v + 1);
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "Something went wrong");
    }
  };

  const createInvite = () =>
    run(async () => {
      const r = await api<Invite & { token: string }>(`${base}/invitations`, { method: "POST", body: JSON.stringify({ role, persona: job || null }) });
      // The token sits after "#" so it is never sent to a server or written to a log.
      setLink(`${window.location.origin}/join#${r.token}`);
      setCopied(false);
    });

  const copy = async () => {
    if (!link) return;
    try {
      await navigator.clipboard.writeText(link);
      setCopied(true);
    } catch {
      setErr("Could not copy. Select the link and copy it by hand.");
    }
  };

  return (
    <div className="space-y-6">
      <header>
        <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">Team</p>
        <h1 className="font-serif text-3xl tracking-tight sm:text-4xl"><Tx k="h.team" />: {workspace.name}</h1>
        <p className="mt-1 text-sm text-fg/70"><Tx k="i.team" /></p>
      </header>

      {err && <ErrorNote message={err} />}

      <div className="grid items-start gap-6 lg:grid-cols-[1.3fr_1fr] [&>*]:min-w-0">
      <section aria-labelledby="people" className="rounded-2xl border border-line bg-surface">
        <h2 id="people" className="border-b border-line px-5 py-3 font-semibold">People</h2>
        {members.loading && !members.data && <Skeleton className="m-5 h-24" />}
        {members.error && <div className="p-5"><ErrorNote message={members.error} /></div>}
        <ul className="divide-y divide-line">
          {members.data?.map((m) => {
            const locked = !isAdmin || (m.role === "owner" && !isOwner);
            return (
              <li key={m.user_id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-3">
                <div className="min-w-0">
                  <p className="truncate font-medium">{m.full_name}</p>
                  <p className="truncate text-sm text-muted">{m.email}</p>
                </div>
                <div className="flex items-center gap-2">
                  <label className="sr-only" htmlFor={`n-${m.user_id}`}>Name on the bills for {m.full_name}</label>
                  <input
                    id={`n-${m.user_id}`}
                    defaultValue={m.staff_name ?? ""}
                    disabled={locked}
                    maxLength={80}
                    placeholder="Name on bills"
                    onBlur={(e) => e.target.value.trim() !== (m.staff_name ?? "") && run(() => api(`${base}/members/${m.user_id}`, { method: "PATCH", body: JSON.stringify({ role: m.role, staff_name: e.target.value.trim() || null }) }))}
                    className="w-32 rounded-lg border border-line bg-canvas px-2.5 py-1.5 text-sm disabled:opacity-60"
                  />
                  <label className="sr-only" htmlFor={`j-${m.user_id}`}>Job of {m.full_name}</label>
                  <select
                    id={`j-${m.user_id}`}
                    value={m.persona ?? ""}
                    disabled={locked}
                    onChange={(e) => run(() => api(`${base}/members/${m.user_id}`, { method: "PATCH", body: JSON.stringify({ role: m.role, persona: e.target.value || null }) }))}
                    className="rounded-lg border border-line bg-canvas px-2.5 py-1.5 text-sm disabled:opacity-60"
                  >
                    <option value="">Any job (role only)</option>
                    {jobsFor(m.role).map((j) => <option key={j.key} value={j.key}>{j.label}</option>)}
                  </select>
                  <label className="sr-only" htmlFor={`r-${m.user_id}`}>Role of {m.full_name}</label>
                  <select
                    id={`r-${m.user_id}`}
                    value={m.role}
                    disabled={locked}
                    onChange={(e) => run(() => api(`${base}/members/${m.user_id}`, { method: "PATCH", body: JSON.stringify({ role: e.target.value }) }))}
                    className="rounded-lg border border-line bg-canvas px-2.5 py-1.5 text-sm disabled:opacity-60"
                  >
                    {ROLES.map((r) => <option key={r.key} value={r.key} disabled={r.key === "owner" && !isOwner}>{r.label}</option>)}
                  </select>
                  {!locked && (
                    <button
                      onClick={() => window.confirm(`Remove ${m.full_name} from ${workspace.name}?`) && run(() => api(`${base}/members/${m.user_id}`, { method: "DELETE" }))}
                      className="rounded-lg px-2.5 py-1.5 text-sm text-sindoor hover:bg-sindoor/10"
                    >
                      Remove
                    </button>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      </section>

      <div className="space-y-6">
      {isAdmin ? (
        <section aria-labelledby="invite" className="rounded-2xl border border-line bg-surface p-5">
          <h2 id="invite" className="font-semibold">Invite someone</h2>
          <p className="mt-1 text-sm text-fg/70">Create a one-time link, valid for 7 days. Send it only to the person you mean; anyone who opens it while signed in joins with the role below.</p>
          <div className="mt-4 flex flex-wrap items-end gap-3">
            <div>
              <label htmlFor="invite-role" className="block font-mono text-[10px] uppercase tracking-wider text-muted">Role</label>
              <select id="invite-role" value={role} onChange={(e) => { setRole(e.target.value); setJob(""); }} className="mt-1 rounded-lg border border-line bg-canvas px-3 py-2 text-sm">
                {assignable.map((r) => <option key={r.key} value={r.key}>{r.label}: {r.note}</option>)}
              </select>
            </div>
            <div>
              <label htmlFor="invite-job" className="block font-mono text-[10px] uppercase tracking-wider text-muted">Job in the shop</label>
              <select id="invite-job" value={job} onChange={(e) => setJob(e.target.value)} className="mt-1 rounded-lg border border-line bg-canvas px-3 py-2 text-sm">
                <option value="">Any (role only)</option>
                {jobsFor(role).map((j) => <option key={j.key} value={j.key}>{j.label}</option>)}
              </select>
            </div>
            <button onClick={createInvite} className="rounded-full bg-fg px-5 py-2 text-sm font-semibold text-canvas hover:bg-sindoor">Create link</button>
          </div>
          {link && (
            <div className="mt-4 rounded-xl border border-mor/30 bg-mor/5 p-3" role="status">
              <p className="text-sm font-semibold">Shown once. Copy it now.</p>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <input readOnly value={link} onFocus={(e) => e.currentTarget.select()} aria-label="Invitation link" className="min-w-0 flex-1 rounded-lg border border-line bg-canvas px-3 py-2 font-mono text-xs" />
                <button onClick={copy} className="rounded-full border border-line px-4 py-2 text-sm hover:border-fg">{copied ? "Copied" : "Copy"}</button>
              </div>
            </div>
          )}

          <h3 className="mt-6 font-mono text-[11px] uppercase tracking-[0.16em] text-muted">Links so far</h3>
          {invites.data && invites.data.length === 0 && <EmptyNote>No invitations yet.</EmptyNote>}
          <ul className="mt-2 divide-y divide-line">
            {invites.data?.map((i) => (
              <li key={i.id} className="flex flex-wrap items-center justify-between gap-2 py-2 text-sm">
                <span>{ROLES.find((r) => r.key === i.role)?.label} · {i.status === "pending" ? `expires ${parseUtc(i.expires_at).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}` : i.status}</span>
                {i.status === "pending" && (
                  <button onClick={() => run(() => api(`${base}/invitations/${i.id}`, { method: "DELETE" }))} className="text-sindoor hover:underline">Cancel</button>
                )}
              </li>
            ))}
          </ul>
        </section>
      ) : (
        <EmptyNote>Only owners and admins can invite or change roles.</EmptyNote>
      )}

      <section aria-labelledby="security" className="rounded-2xl border border-line bg-surface p-5">
        <h2 id="security" className="font-semibold">Your sign-ins</h2>
        <p className="mt-1 text-sm text-fg/70">Lost a phone or used a shared computer? End every sign-in of your account. You will be asked to sign in again.</p>
        <button onClick={() => void signOut(true).finally(() => { window.location.href = "/login"; })} className="mt-3 rounded-full border border-sindoor/40 px-4 py-2 text-sm text-sindoor hover:bg-sindoor/10">
          Sign out everywhere
        </button>
      </section>
      </div>
      </div>
    </div>
  );
}
