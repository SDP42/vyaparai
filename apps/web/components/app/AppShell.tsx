"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { Logo } from "@/components/landing/Nav";
import { useWorkspace } from "./AppContext";

const NAV = [
  { href: "/app", label: "Command center", icon: "◧", exact: true },
  { href: "/app/sales", label: "Sales", icon: "◨", exact: false },
  { href: "/app/data", label: "Data", icon: "▤", exact: false },
];
const SOON = [
  ["Customers", "Phase 3"],
  ["Forecasts", "Phase 4"],
  ["Inventory", "Phase 5"],
  ["Copilot", "Phase 8"],
];

export function AppShell({ name, onSignOut, children }: { name: string; onSignOut: () => void; children: ReactNode }) {
  const path = usePathname();
  const { workspace } = useWorkspace();
  const active = (n: (typeof NAV)[number]) => (n.exact ? path === n.href : path.startsWith(n.href));

  return (
    <div className="min-h-dvh bg-canvas md:grid md:grid-cols-[232px_1fr]">
      <aside className="sticky top-0 hidden h-dvh flex-col border-r border-line bg-surface p-5 md:flex">
        <Link href="/" aria-label="Vyapar AI home">
          <Logo />
        </Link>
        <div className="mt-7 rounded-xl border border-line bg-canvas p-3">
          <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted">Workspace</p>
          <p className="mt-1 truncate text-sm font-semibold">{workspace.name}</p>
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
            </Link>
          ))}
          <p className="mt-5 px-3 font-mono text-[10px] uppercase tracking-[0.18em] text-muted">Coming</p>
          {SOON.map(([label, phase]) => (
            <span key={label} aria-disabled className="flex items-center justify-between rounded-lg px-3 py-1.5 text-sm text-fg/35">
              {label}
              <span className="font-mono text-[9px] uppercase tracking-wider">{phase}</span>
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
            <button type="button" onClick={onSignOut} className="rounded-full border border-line px-3 py-1 text-xs text-muted">
              Sign out
            </button>
          </div>
          <nav aria-label="App" className="flex gap-2 overflow-x-auto px-4 pb-2 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
            {NAV.map((n) => (
              <Link
                key={n.href}
                href={n.href}
                aria-current={active(n) ? "page" : undefined}
                className={`whitespace-nowrap rounded-full border px-3 py-1.5 text-xs ${
                  active(n) ? "border-fg bg-fg text-canvas" : "border-line text-fg/60"
                }`}
              >
                {n.label}
              </Link>
            ))}
          </nav>
        </header>
        <main className="mx-auto max-w-[1200px] px-4 py-6 sm:px-8 sm:py-8">{children}</main>
      </div>
    </div>
  );
}
