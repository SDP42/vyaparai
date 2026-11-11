"use client";

import { useRef, useState, type FormEvent } from "react";
import { ApiError, api } from "@/lib/api";
import { useApi } from "@/lib/analytics";
import { parseUtc } from "@/lib/format";
import { useWorkspace } from "./AppContext";
import { Card, EmptyNote, ErrorNote, Skeleton } from "./analytics/parts";
import { Tx } from "./Tx";

type Doc = { id: string; title: string; filename: string; kind: string; pages: number | null; chunks: number; min_role: string; created_at: string };
type Hit = { document_id: string; title: string; page: number | null; section: string | null; text: string; score: number };
type Found = { query: string; answer: string | null; confidence: "high" | "possible" | "none"; results: Hit[] };

const ROLES = [
  { key: "viewer", label: "Everyone in the team" },
  { key: "analyst", label: "Analysts and above" },
  { key: "admin", label: "Admins and owners" },
  { key: "owner", label: "Owners only" },
];
const ROLE_RANK: Record<string, number> = { viewer: 1, analyst: 2, admin: 3, owner: 4 };

export function DocumentsPage() {
  const { workspace, canImport } = useWorkspace();
  const base = `/workspaces/${workspace.id}/documents`;
  const mine = ROLE_RANK[workspace.role] ?? 1;
  const ref = useRef<HTMLInputElement>(null);
  const [version, setVersion] = useState(0);
  const [level, setLevel] = useState("viewer");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [found, setFound] = useState<Found | null>(null);
  const [searching, setSearching] = useState(false);
  const docs = useApi<Doc[]>(base, [version]);

  const upload = async (file: File) => {
    setBusy(true); setErr(null);
    const fd = new FormData(); fd.append("file", file); fd.append("min_role", level);
    try { await api(base, { method: "POST", body: fd }); setVersion((v) => v + 1); }
    catch (e) { setErr(e instanceof ApiError ? e.message : "Could not add the file"); }
    finally { setBusy(false); if (ref.current) ref.current.value = ""; }
  };
  const search = async (e: FormEvent) => {
    e.preventDefault();
    if (q.trim().length < 2) return;
    setSearching(true); setErr(null);
    try { setFound(await api<Found>(`${base}/search`, { method: "POST", body: JSON.stringify({ query: q.trim(), k: 4 }) })); }
    catch (e2) { setErr(e2 instanceof ApiError ? e2.message : "Search failed"); }
    finally { setSearching(false); }
  };
  const remove = async (d: Doc) => {
    if (!window.confirm(`Remove “${d.title}” and its search index?`)) return;
    try { await api(`${base}/${d.id}`, { method: "DELETE" }); setVersion((v) => v + 1); setFound(null); }
    catch (e) { setErr(e instanceof ApiError ? e.message : "Could not remove it"); }
  };

  return (
    <div className="space-y-6">
      <header>
        <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">Documents</p>
        <h1 className="font-serif text-3xl tracking-tight sm:text-4xl"><Tx k="h.documents" /></h1>
        <p className="mt-1 max-w-2xl text-sm text-fg/70"><Tx k="i.documents" /></p>
      </header>

      {err && <ErrorNote message={err} />}

      <div className="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
        <section aria-label="Search" className="space-y-4">
          <form onSubmit={search} className="flex items-center gap-2 rounded-full border border-line bg-surface p-1.5">
            <label htmlFor="docq" className="sr-only">Search your documents</label>
            <input id="docq" value={q} onChange={(e) => setQ(e.target.value)} maxLength={300} placeholder="e.g. how many days to pay the supplier?" className="min-w-0 flex-1 bg-transparent px-4 py-2 text-sm outline-none" autoComplete="off" />
            <button type="submit" disabled={searching || q.trim().length < 2} className="rounded-full bg-fg px-5 py-2 text-sm font-semibold text-canvas hover:bg-sindoor disabled:opacity-50">{searching ? "Searching…" : "Search"}</button>
          </form>

          {found && found.confidence === "none" && <EmptyNote>Nothing in your documents answers that. Try other words, or add the document that covers it.</EmptyNote>}
          {found && found.answer && (
            <div className="rounded-2xl border border-line bg-surface p-5">
              <div className="flex flex-wrap items-center gap-2 text-xs">
                <span className={`rounded-full px-2.5 py-0.5 ${found.confidence === "high" ? "bg-mor/12 text-mor" : "bg-haldi/25"}`}>{found.confidence === "high" ? "Found in your documents" : "Possible match, please check"}</span>
              </div>
              <p className="mt-3 text-[15px] leading-relaxed">{found.answer}</p>
              <p className="mt-2 text-xs text-muted">Quoted from {found.results[0].title}{found.results[0].page ? `, page ${found.results[0].page}` : ""}{found.results[0].section ? `, ${found.results[0].section}` : ""}. Nothing here is written by the search; it is copied from your file.</p>
              <h2 className="mt-5 font-mono text-[10px] uppercase tracking-[0.16em] text-muted">Passages</h2>
              <ul className="mt-2 space-y-2">
                {found.results.map((r, i) => (
                  <li key={i} className="rounded-xl border border-line bg-canvas p-3">
                    <p className="text-xs text-muted"><b className="text-fg">{r.title}</b>{r.page ? ` · page ${r.page}` : ""}{r.section ? ` · ${r.section}` : ""}</p>
                    <p className="mt-1 whitespace-pre-line break-words text-sm text-fg/85">{r.text}</p>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {!found && <EmptyNote>Ask a question above to search every document you can read.</EmptyNote>}
        </section>

        <aside className="space-y-4" aria-label="Files">
          {canImport && (
            <Card title="Add a document" subtitle="PDF, DOCX, TXT or Markdown, up to 15 MB. Scanned pages need typing or a photo on the Bills page.">
              <label htmlFor="lvl" className="block text-xs text-muted">Who can read it</label>
              <select id="lvl" value={level} onChange={(e) => setLevel(e.target.value)} className="mt-1 w-full rounded-lg border border-line bg-canvas px-3 py-2 text-sm">
                {ROLES.filter((r) => ROLE_RANK[r.key] <= mine).map((r) => <option key={r.key} value={r.key}>{r.label}</option>)}
              </select>
              <input ref={ref} type="file" accept=".pdf,.docx,.txt,.md,application/pdf" className="hidden" onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])} />
              <button type="button" disabled={busy} onClick={() => ref.current?.click()} className="mt-3 w-full rounded-full bg-fg px-5 py-2.5 text-sm font-semibold text-canvas hover:bg-sindoor disabled:opacity-60">{busy ? "Reading and indexing…" : "Choose a file"}</button>
            </Card>
          )}
          <section className="rounded-2xl border border-line bg-surface">
            <h2 className="border-b border-line px-5 py-3 font-semibold">Your documents</h2>
            {docs.loading && !docs.data && <Skeleton className="m-4 h-20" />}
            {docs.data?.length === 0 && <div className="p-4"><EmptyNote>No documents yet.</EmptyNote></div>}
            <ul className="divide-y divide-line">
              {docs.data?.map((d) => (
                <li key={d.id} className="flex items-start justify-between gap-3 px-5 py-3 text-sm">
                  <div className="min-w-0">
                    <p className="truncate font-medium">{d.title}</p>
                    <p className="text-xs text-muted">{d.kind.toUpperCase()} · {d.chunks} passages{d.pages ? ` · ${d.pages} pages` : ""} · {parseUtc(d.created_at).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}{d.min_role !== "viewer" && <> · {ROLES.find((r) => r.key === d.min_role)?.label}</>}</p>
                  </div>
                  {["owner", "admin"].includes(workspace.role) && <button type="button" onClick={() => remove(d)} className="shrink-0 rounded-lg px-2.5 py-1 text-xs text-sindoor hover:bg-sindoor/10">Remove</button>}
                </li>
              ))}
            </ul>
          </section>
        </aside>
      </div>
    </div>
  );
}
