"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useRef, type ReactNode } from "react";
import { Logo } from "@/components/landing/Nav";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useWorkspace } from "./AppContext";

const NAV = [
  { href: "/app", label: "Command center", icon: "◧", exact: true },
  { href: "/app/ask", label: "Ask", icon: "✦", exact: false },
  { href: "/app/recommendations", label: "Next steps", icon: "✓", exact: false },
  { href: "/app/alerts", label: "Alerts", icon: "!", exact: false },
  { href: "/app/investigate", label: "Investigate", icon: "◇", exact: false },
  { href: "/app/sales", label: "Sales", icon: "◨", exact: false },
  { href: "/app/customers", label: "Customers", icon: "◉", exact: false },
  { href: "/app/products", label: "Products", icon: "◈", exact: false },
  { href: "/app/forecasts", label: "Forecasts", icon: "◬", exact: false },
  { href: "/app/inventory", label: "Stock", icon: "▦", exact: false },
  { href: "/app/festivals", label: "Festivals", icon: "◎", exact: false },
  { href: "/app/bills", label: "Bills", icon: "▥", exact: false },
  { href: "/app/pricing", label: "Pricing", icon: "%", exact: false },
  { href: "/app/costs", label: "Costs", icon: "₹", exact: false },
  { href: "/app/reviews", label: "Reviews", icon: "❝", exact: false },
  { href: "/app/documents", label: "Documents", icon: "❏", exact: false },
  { href: "/app/udhaar", label: "Udhaar", icon: "◐", exact: false },
  { href: "/app/campaigns", label: "Campaigns", icon: "◍", exact: false },
  { href: "/app/digest", label: "Digest", icon: "✉", exact: false },
  { href: "/app/data", label: "Data", icon: "▤", exact: false },
  { href: "/app/reports", label: "Reports", icon: "▣", exact: false },
  { href: "/app/team", label: "Team", icon: "☺", exact: false },
];
const SOON: string[] = [];

/** Open alerts that need a look (high and medium), refreshed when alerts change. */
function useAlertBadge(wsId: string): number {
  const [n, setN] = useState(0);
  useEffect(() => {
    let live = true;
    const load = () => api<Record<string, number>>(`/workspaces/${wsId}/alerts/summary`).then((c) => live && setN((c.high ?? 0) + (c.medium ?? 0))).catch(() => undefined);
    load();
    window.addEventListener("vyapar:alerts-changed", load);
    return () => {
      live = false;
      window.removeEventListener("vyapar:alerts-changed", load);
    };
  }, [wsId]);
  return n;
}

export function AppShell({ name, onSignOut, children }: { name: string; onSignOut: () => void; children: ReactNode }) {
  const path = usePathname();
  const { workspace, workspaces, switchTo } = useWorkspace();
  const alertCount = useAlertBadge(workspace.id);
  const badge = (href: string) =>
    href === "/app/alerts" && alertCount > 0 ? (
      <span aria-label={`${alertCount} open alerts`} className="ml-auto grid h-5 min-w-5 place-items-center rounded-full bg-sindoor px-1 font-mono text-[10px] font-bold text-canvas">
        {alertCount}
      </span>
    ) : null;
  const active = (n: (typeof NAV)[number]) => (n.exact ? path === n.href : path.startsWith(n.href));
  const strip = useRef<HTMLElement>(null);
  // Keep the current page's chip visible when the phone nav is scrolled.
  useEffect(() => {
    strip.current?.querySelector<HTMLElement>('[aria-current="page"]')?.scrollIntoView({ inline: "center", block: "nearest" });
  }, [path]);

  return (
    <div className="min-h-dvh bg-canvas md:grid md:grid-cols-[232px_1fr]">
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-50 focus:rounded-full focus:bg-fg focus:px-4 focus:py-2 focus:text-sm focus:text-canvas">
        Skip to content
      </a>
      <aside className="sticky top-0 hidden h-dvh flex-col border-r border-line bg-surface p-5 md:flex">
        <Link href="/" aria-label="Vyapar AI home">
          <Logo />
        </Link>
        <div className="mt-7 rounded-xl border border-line bg-canvas p-3">
          <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted">Workspace</p>
          {workspaces.length > 1 ? (
            <select aria-label="Switch workspace" value={workspace.id} onChange={(e) => switchTo(e.target.value)} className="mt-1 w-full truncate rounded-md border border-line bg-surface px-1.5 py-1 text-sm font-semibold">
              {workspaces.map((w) => (
                <option key={w.id} value={w.id}>
                  {w.name}
                </option>
              ))}
            </select>
          ) : (
            <p className="mt-1 truncate text-sm font-semibold">{workspace.name}</p>
          )}
          <p className="font-mono text-[10px] text-muted">
            {workspace.role} · {workspace.currency}
          </p>
        </div>
        <nav className="mt-6 flex flex-col gap-1" aria-label="App">
          {NAV.map((n) => (
            <Link
              key={n.href}
              href={n.href}
              aria-current={active(n) ? "page" : undefined}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
                active(n) ? "bg-surface-2 font-medium text-fg" : "text-fg/60 hover:bg-surface-2/60 hover:text-fg"
              }`}
            >
              <span aria-hidden className="text-muted">
                {n.icon}
              </span>
              {n.label}
              {badge(n.href)}
            </Link>
          ))}
          <p className="mt-5 px-3 font-mono text-[10px] uppercase tracking-[0.18em] text-muted">Coming</p>
          {SOON.map((label) => (
            <span key={label} aria-disabled className="flex items-center justify-between rounded-lg px-3 py-1.5 text-sm text-fg/35">
              {label}
              <span className="font-mono text-[9px] uppercase tracking-wider">Soon</span>
            </span>
          ))}
        </nav>
        <div className="mt-auto flex items-center gap-3 border-t border-line pt-4">
          <span className="grid h-9 w-9 place-items-center rounded-xl bg-fg font-mono text-xs font-bold text-canvas" aria-hidden>
            {name.slice(0, 2).toUpperCase()}
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium">{name}</p>
          </div>
          <button type="button" onClick={onSignOut} className="text-xs text-muted hover:text-fg">
            Sign out
          </button>
        </div>
      </aside>

      <div className="min-w-0">
        <header className="sticky top-0 z-20 border-b border-line bg-canvas/85 backdrop-blur md:hidden">
          <div className="flex h-14 items-center justify-between px-4">
            <Link href="/" aria-label="Vyapar AI home">
              <Logo />
            </Link>
            {workspaces.length > 1 && (
              <select aria-label="Switch workspace" value={workspace.id} onChange={(e) => switchTo(e.target.value)} className="mx-2 min-w-0 max-w-[40%] truncate rounded-full border border-line bg-surface px-2 py-1 text-xs font-semibold">
                {workspaces.map((w) => (
                  <option key={w.id} value={w.id}>{w.name}</option>
                ))}
              </select>
            )}
            <button type="button" onClick={onSignOut} className="rounded-full border border-line px-3 py-1 text-xs text-muted">
              Sign out
            </button>
          </div>
          <nav ref={strip} aria-label="App" className="flex snap-x gap-2 overflow-x-auto px-4 pb-2 [mask-image:linear-gradient(to_right,#000_92%,transparent)] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
            {NAV.map((n) => (
              <Link
                key={n.href}
                href={n.href}
                aria-current={active(n) ? "page" : undefined}
                className={`inline-flex shrink-0 snap-start items-center gap-1.5 whitespace-nowrap rounded-full border px-3 py-1.5 text-xs ${
                  active(n) ? "border-fg bg-fg text-canvas" : "border-line text-fg/60"
                }`}
              >
                {n.label}
                {badge(n.href)}
              </Link>
            ))}
          </nav>
        </header>
        <main id="main" tabIndex={-1} className="mx-auto max-w-[1200px] px-4 py-6 outline-none sm:px-8 sm:py-8">{children}</main>
      </div>
    </div>
  );
}
