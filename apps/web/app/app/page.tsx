"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { motion } from "motion/react";
import { Logo } from "@/components/landing/Nav";
import { SalesChart } from "@/components/app/SalesChart";
import { KpiValue } from "@/components/landing/DashboardPreview";
import { KPIS, RECOMMENDATIONS, TOP_PRODUCTS, salesSeries } from "@/lib/demo-data";
import { formatINR, formatPct } from "@/lib/format";
import { getPersona, type Persona } from "@/lib/personas";
import { clearSession, loadSession, type Session } from "@/lib/session";

const NAV = [
  { label: "Overview", phase: null },
  { label: "Sales", phase: "Phase 2" },
  { label: "Customers", phase: "Phase 3" },
  { label: "Forecasts", phase: "Phase 4" },
  { label: "Inventory", phase: "Phase 5" },
  { label: "Knowledge", phase: "Phase 7" },
  { label: "Copilot", phase: "Phase 8" },
];

const EASE = [0.16, 1, 0.3, 1] as const;

export default function AppHome() {
  const router = useRouter();
  const [session, setSession] = useState<Session | null | undefined>(undefined);

  useEffect(() => {
    const s = loadSession();
    if (!s) router.replace("/login");
    setSession(s);
  }, [router]);

  if (!session) return <div className="min-h-dvh bg-ink" aria-busy="true" />;

  const persona = session.kind === "persona" ? getPersona(session.personaId) : null;
  const name = persona?.name ?? (session.kind === "account" ? session.name : "You");
  const signOut = () => {
    clearSession();
    router.push("/login");
  };

  return (
    <div className="min-h-dvh bg-ink md:grid md:grid-cols-[240px_1fr]">
      <aside className="sticky top-0 hidden h-dvh flex-col border-r border-line bg-ink-2 p-5 md:flex">
        <Link href="/" aria-label="Vyapar AI home">
          <Logo />
        </Link>
        <div className="mt-8 rounded-xl border border-line bg-ink p-3">
          <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted">Workspace</p>
          <p className="mt-1 truncate text-sm font-semibold">{persona?.business.split(" · ")[0] ?? "My workspace"}</p>
        </div>
        <nav className="mt-6 flex flex-col gap-1" aria-label="App">
          {NAV.map((n, i) => (
            <span
              key={n.label}
              aria-current={i === 0 ? "page" : undefined}
              aria-disabled={n.phase ? true : undefined}
              className={`flex items-center justify-between rounded-lg px-3 py-2 text-sm ${
                i === 0 ? "bg-ink-3 text-paper" : "text-paper/40"
              }`}
            >
              {n.label}
              {n.phase && <span className="font-mono text-[9px] uppercase tracking-wider text-muted">{n.phase}</span>}
            </span>
          ))}
        </nav>
        <div className="mt-auto flex items-center gap-3 border-t border-line pt-4">
          <span
            className="grid h-9 w-9 place-items-center rounded-xl font-mono text-xs font-bold text-ink"
            style={{ background: persona?.accent ?? "var(--color-paper)" }}
            aria-hidden
          >
            {persona?.initials ?? name.slice(0, 2).toUpperCase()}
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium">{name}</p>
            <p className="truncate text-xs text-muted">{persona?.role ?? "member"}</p>
          </div>
          <button onClick={signOut} className="text-xs text-paper/50 hover:text-paper" type="button">
            Sign out
          </button>
        </div>
      </aside>

      <main className="min-w-0 px-5 py-6 sm:px-8 sm:py-8">
        <header className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3 md:hidden">
            <Logo />
          </div>
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, ease: EASE }}>
            <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
              {persona?.greeting ?? `Welcome, ${name}`}
              <span className="font-serif font-normal italic text-paper/60"> — here&apos;s your shop.</span>
            </h1>
            <p className="mt-1 text-sm text-paper/50">Last 30 days · INR · data refreshed 06 Nov 2026, 23:40 IST</p>
          </motion.div>
          <div className="flex items-center gap-2">
            <span
              className="grid h-8 w-8 place-items-center rounded-lg font-mono text-[10px] font-bold text-ink md:hidden"
              style={{ background: persona?.accent ?? "var(--color-paper)" }}
              title={name}
              aria-hidden
            >
              {persona?.initials ?? name.slice(0, 2).toUpperCase()}
            </span>
            <span className="rounded-full border border-haldi/40 bg-haldi/10 px-3 py-1 font-mono text-[10px] uppercase tracking-[0.18em] text-haldi">
              Demo data
            </span>
            <button onClick={signOut} className="rounded-full border border-line px-3 py-1 text-xs text-paper/60 md:hidden" type="button">
              Sign out
            </button>
          </div>
        </header>

        {/* Mobile: section nav replaces the sidebar */}
        <nav aria-label="App sections" className="-mx-5 mt-5 overflow-x-auto px-5 [scrollbar-width:none] md:hidden [&::-webkit-scrollbar]:hidden">
          <ul className="flex w-max gap-2">
            {NAV.map((n, i) => (
              <li key={n.label}>
                <span
                  aria-current={i === 0 ? "page" : undefined}
                  aria-disabled={n.phase ? true : undefined}
                  className={`flex items-center gap-1.5 whitespace-nowrap rounded-full border px-3 py-1.5 text-xs ${
                    i === 0 ? "border-paper bg-paper text-ink" : "border-line text-paper/45"
                  }`}
                >
                  {n.label}
                  {n.phase && <span className="font-mono text-[9px] text-muted">{n.phase.replace("Phase ", "P")}</span>}
                </span>
              </li>
            ))}
          </ul>
        </nav>

        {persona && <FocusStrip persona={persona} />}

        <section aria-label="Key metrics" className="mt-6 grid grid-cols-2 gap-3 xl:grid-cols-4">
          {KPIS.map((k, i) => (
            <motion.article
              key={k.key}
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 + i * 0.06, duration: 0.6, ease: EASE }}
              className="rounded-2xl border border-line bg-ink-2 p-4 sm:p-5"
            >
              <p className="text-xs text-muted">{k.label}</p>
              <p className="mt-2 text-2xl font-bold tabular sm:text-3xl">
                <KpiValue value={k.value} format={k.format} />
              </p>
              <p className={`mt-1 font-mono text-[11px] ${k.delta >= 0 ? "text-mor" : "text-sindoor"}`}>
                <span aria-hidden>{k.delta >= 0 ? "▲" : "▼"}</span> {formatPct(k.delta)}
                <span className="sr-only">{k.delta >= 0 ? " increase" : " decrease"}</span> vs prev. 30d
              </p>
              <p className="mt-3 border-t border-line pt-2 text-[11px] leading-snug text-paper/40">{k.hint}</p>
            </motion.article>
          ))}
        </section>

        <div className="mt-4 grid gap-4 xl:grid-cols-[1.6fr_1fr]">
          <motion.section
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.35, duration: 0.6, ease: EASE }}
            className="rounded-2xl border border-line bg-ink-2 p-5"
            aria-labelledby="trend-title"
          >
            <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
              <h2 id="trend-title" className="font-semibold">Daily net sales & 14-day forecast</h2>
              <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted">seasonal-naive baseline · demo</p>
            </div>
            <SalesChart data={salesSeries()} />
          </motion.section>

          <Recommendations canApprove={persona ? persona.role === "owner" || persona.role === "admin" : true} />
        </div>

        <motion.section
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5, duration: 0.6, ease: EASE }}
          className="mt-4 overflow-hidden rounded-2xl border border-line bg-ink-2"
          aria-labelledby="top-title"
        >
          <h2 id="top-title" className="px-5 pt-5 font-semibold">Top products</h2>
          {/* Phones: stacked summaries instead of a wide table */}
          <ul className="mt-3 divide-y divide-line/60 sm:hidden">
            {TOP_PRODUCTS.map((p) => (
              <li key={p.sku} className="flex items-center justify-between gap-3 px-5 py-3">
                <div className="min-w-0">
                  <p className="truncate text-sm">{p.name}</p>
                  <p className="font-mono text-[10px] text-muted">
                    {p.sku} · {p.category}
                  </p>
                </div>
                <div className="shrink-0 text-right">
                  <p className="text-sm tabular">{formatINR(p.revenue)}</p>
                  <p className={`font-mono text-[11px] ${p.change >= 0 ? "text-mor" : "text-sindoor"}`}>{formatPct(p.change)}</p>
                </div>
              </li>
            ))}
          </ul>
          <div className="hidden overflow-x-auto sm:block">
            <table className="mt-3 w-full min-w-[520px] text-sm">
              <thead>
                <tr className="border-y border-line text-left font-mono text-[10px] uppercase tracking-[0.14em] text-muted">
                  <th className="px-5 py-2 font-normal">Product</th>
                  <th className="px-5 py-2 font-normal">Category</th>
                  <th className="px-5 py-2 text-right font-normal">Net sales</th>
                  <th className="px-5 py-2 text-right font-normal">vs prev.</th>
                </tr>
              </thead>
              <tbody>
                {TOP_PRODUCTS.map((p) => (
                  <tr key={p.sku} className="border-b border-line/60 last:border-0 hover:bg-ink-3/50">
                    <td className="px-5 py-3">
                      {p.name}
                      <span className="ml-2 font-mono text-[10px] text-muted">{p.sku}</span>
                    </td>
                    <td className="px-5 py-3 text-paper/60">{p.category}</td>
                    <td className="px-5 py-3 text-right tabular">{formatINR(p.revenue)}</td>
                    <td className={`px-5 py-3 text-right font-mono text-xs ${p.change >= 0 ? "text-mor" : "text-sindoor"}`}>
                      {formatPct(p.change)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.section>
      </main>
    </div>
  );
}

function FocusStrip({ persona }: { persona: Persona }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: 0.2, duration: 0.6 }}
      className="mt-5 flex flex-wrap items-center gap-2 rounded-2xl border border-line bg-ink-2 px-4 py-3"
    >
      <span className="mr-1 font-mono text-[10px] uppercase tracking-[0.18em] text-muted">Your focus</span>
      {persona.focus.map((f) => (
        <span key={f} className="rounded-full px-3 py-1 text-xs font-medium text-ink" style={{ background: persona.accent }}>
          {f}
        </span>
      ))}
      <span className="ml-auto hidden font-serif text-sm italic text-paper/50 sm:inline">“{persona.quote}”</span>
    </motion.div>
  );
}

function Recommendations({ canApprove }: { canApprove: boolean }) {
  const [status, setStatus] = useState<Record<string, "approved" | "dismissed">>({});
  return (
    <motion.section
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.42, duration: 0.6, ease: EASE }}
      className="rounded-2xl border border-line bg-ink-2 p-5"
      aria-labelledby="rec-title"
    >
      <h2 id="rec-title" className="font-semibold">Suggested actions</h2>
      <p className="mt-1 text-xs text-paper/45">Drafts only — nothing is ordered without approval.</p>
      <ul className="mt-4 space-y-3">
        {RECOMMENDATIONS.map((r) => {
          const s = status[r.id];
          return (
            <li key={r.id} className="rounded-xl border border-line bg-ink p-4">
              <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-haldi">{r.confidence} confidence · {r.impact}</p>
              <p className="mt-1.5 font-semibold leading-snug">{r.title}</p>
              <p className="mt-1 text-xs text-paper/55">{r.rationale}</p>
              <p className="mt-2 font-mono text-[10px] text-muted">Evidence: {r.evidence.join(" · ")}</p>
              <div className="mt-3 flex items-center gap-2">
                {s ? (
                  <span className={`text-xs font-semibold ${s === "approved" ? "text-mor" : "text-paper/50"}`} role="status">
                    {s === "approved" ? "✓ Approved as draft" : "Dismissed"}
                  </span>
                ) : canApprove ? (
                  <>
                    <button type="button" onClick={() => setStatus((x) => ({ ...x, [r.id]: "approved" }))} className="rounded-full bg-mor px-3 py-1.5 text-xs font-semibold text-ink hover:brightness-110">
                      Approve draft
                    </button>
                    <button type="button" onClick={() => setStatus((x) => ({ ...x, [r.id]: "dismissed" }))} className="rounded-full border border-line px-3 py-1.5 text-xs text-paper/70 hover:text-paper">
                      Dismiss
                    </button>
                  </>
                ) : (
                  <span className="text-xs text-paper/45">View only. An owner or admin approves actions.</span>
                )}
              </div>
            </li>
          );
        })}
      </ul>
    </motion.section>
  );
}
