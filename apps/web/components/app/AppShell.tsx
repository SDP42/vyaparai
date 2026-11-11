"use client";

import {
  Bell, Boxes, CalendarDays, ChartNoAxesColumn, CheckCheck, ClipboardList, Database, FileText, Gauge, Goal, HandCoins, Home, LineChart, Megaphone, MessageCircleQuestion,
  MessagesSquare, Microscope, Newspaper, Package, ReceiptText, Store, Tag, Target, TrendingUp, Users, UsersRound, UserRound, Wallet, X, Ellipsis, LogOut, type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { Logo } from "@/components/landing/Nav";
import { api } from "@/lib/api";
import { LANGS, useT, type Key } from "@/lib/i18n";
import { useWorkspace } from "./AppContext";
import { allowedPath, usePersona } from "./PersonaContext";

type Item = { href: string; key: Key; icon: LucideIcon; exact?: boolean };
type Group = { key: Key; items: Item[] };

const GROUPS: Group[] = [
  { key: "group.overview", items: [
    { href: "/app", key: "nav.command", icon: Gauge, exact: true },
    { href: "/app/ask", key: "nav.ask", icon: MessageCircleQuestion },
    { href: "/app/recommendations", key: "nav.steps", icon: CheckCheck },
    { href: "/app/goals", key: "nav.goals", icon: Target },
    { href: "/app/alerts", key: "nav.alerts", icon: Bell },
  ] },
  { key: "group.sales", items: [
    { href: "/app/sales", key: "nav.sales", icon: ChartNoAxesColumn },
    { href: "/app/customers", key: "nav.customers", icon: Users },
    { href: "/app/staff", key: "nav.staff", icon: UserRound },
    { href: "/app/products", key: "nav.products", icon: Package },
    { href: "/app/pricing", key: "nav.pricing", icon: Tag },
    { href: "/app/reviews", key: "nav.reviews", icon: MessagesSquare },
    { href: "/app/campaigns", key: "nav.campaigns", icon: Megaphone },
  ] },
  { key: "group.ops", items: [
    { href: "/app/inventory", key: "nav.stock", icon: Boxes },
    { href: "/app/forecasts", key: "nav.forecasts", icon: LineChart },
    { href: "/app/festivals", key: "nav.festivals", icon: CalendarDays },
    { href: "/app/bills", key: "nav.bills", icon: ReceiptText },
    { href: "/app/costs", key: "nav.costs", icon: Wallet },
    { href: "/app/udhaar", key: "nav.udhaar", icon: HandCoins },
    { href: "/app/documents", key: "nav.documents", icon: FileText },
  ] },
  { key: "group.more", items: [
    { href: "/app/investigate", key: "nav.investigate", icon: Microscope },
    { href: "/app/digest", key: "nav.digest", icon: Newspaper },
    { href: "/app/reports", key: "nav.reports", icon: ClipboardList },
    { href: "/app/stores", key: "nav.stores", icon: Store },
    { href: "/app/data", key: "nav.data", icon: Database },
    { href: "/app/team", key: "nav.team", icon: UsersRound },
  ] },
];
const ALL = GROUPS.flatMap((g) => g.items);
const TABS: Item[] = [ALL[0], ALL[1], ALL[2], ALL[4]]; // Command center, Ask, Next steps, Alerts; the last tab is "More"

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

function Badge({ n, className = "" }: { n: number; className?: string }) {
  if (n <= 0) return null;
  return <span aria-label={`${n} open alerts`} className={`grid h-[18px] min-w-[18px] place-items-center rounded-full bg-sindoor px-1 font-mono text-[10px] font-bold leading-none text-canvas ${className}`}>{n}</span>;
}

function LanguageSelect({ className = "" }: { className?: string }) {
  const { t, lang, setLang } = useT();
  return (
    <select aria-label={t("shell.language")} value={lang} onChange={(e) => setLang(e.target.value as (typeof LANGS)[number]["key"])} className={className}>
      {LANGS.map((l) => <option key={l.key} value={l.key}>{l.label}</option>)}
    </select>
  );
}

function WorkspaceSelect({ className = "" }: { className?: string }) {
  const { t } = useT();
  const { workspace, workspaces, switchTo } = useWorkspace();
  if (workspaces.length < 2) return <p className={`truncate font-semibold ${className}`}>{workspace.name}</p>;
  return (
    <select aria-label={t("shell.switch")} value={workspace.id} onChange={(e) => switchTo(e.target.value)} className={`truncate ${className}`}>
      {workspaces.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}
    </select>
  );
}

export function AppShell({ name, onSignOut, children }: { name: string; onSignOut: () => void; children: ReactNode }) {
  const path = usePathname();
  const { t } = useT();
  const router = useRouter();
  const { workspace } = useWorkspace();
  const { persona, ready } = usePersona();
  const alerts = useAlertBadge(workspace.id);
  // A persona sees only its own pages; the rest are hidden, and a typed address goes home.
  const groups = GROUPS.map((g) => ({ ...g, items: g.items.filter((n) => allowedPath(persona, n.href)) })).filter((g) => g.items.length);
  const allowed = groups.flatMap((g) => g.items);
  const tabs = [...TABS.filter((n) => allowed.includes(n)), ...allowed.filter((n) => !TABS.includes(n))].slice(0, 4);
  useEffect(() => {
    if (ready && persona && !allowedPath(persona, path)) router.replace(persona.home);
  }, [ready, persona, path, router]);
  const [more, setMore] = useState(false);
  const closeRef = useRef<HTMLButtonElement>(null);
  const navRef = useRef<HTMLElement>(null);
  const active = (n: Item) => (n.exact ? path === n.href : path === n.href || path.startsWith(`${n.href}/`));

  useEffect(() => setMore(false), [path]); // a tap on a link closes the sheet
  useEffect(() => {
    if (!more) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setMore(false);
    window.addEventListener("keydown", onKey);
    return () => { document.body.style.overflow = prev; window.removeEventListener("keydown", onKey); };
  }, [more]);
  // keep the current page's link in view when the long menu is scrolled
  useEffect(() => { navRef.current?.querySelector<HTMLElement>('[aria-current="page"]')?.scrollIntoView({ block: "nearest" }); }, [path]);

  const inMore = !tabs.some(active) && allowed.some(active);
  const initials = name.slice(0, 2).toUpperCase();

  return (
    <div className="min-h-dvh bg-canvas md:flex">
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-50 focus:rounded-full focus:bg-fg focus:px-4 focus:py-2 focus:text-sm focus:text-canvas">{t("shell.skip")}</a>

      {/* ---------------------------------------------------------------- tablet rail and desktop sidebar */}
      <aside className="sticky top-0 hidden h-dvh w-[72px] shrink-0 flex-col border-r border-line bg-surface md:flex lg:w-[248px] 2xl:w-[272px]">
        <div className="shrink-0 px-3 pb-3 pt-5 lg:px-5">
          <Link href="/" aria-label="Vyapar AI home" className="flex justify-center lg:justify-start"><span className="lg:hidden"><Logo compact /></span><span className="hidden lg:block"><Logo /></span></Link>
          <div className="mt-5 hidden rounded-xl border border-line bg-canvas p-3 lg:block">
            <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted">{t("shell.workspace")}</p>
            <WorkspaceSelect className="mt-1 w-full rounded-md border border-line bg-surface px-1.5 py-1 text-sm" />
            <p className="mt-1 font-mono text-[10px] text-muted">{persona ? persona.label : workspace.role} · {workspace.currency}</p>
          </div>
        </div>

        <nav ref={navRef} aria-label="App" className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-2 pb-3 [scrollbar-color:var(--color-line)_transparent] [scrollbar-width:thin] lg:px-3">
          {groups.map((g, gi) => (
            <div key={g.key} className={gi ? "mt-4" : ""}>
              <p className="mb-1 hidden px-3 font-mono text-[10px] uppercase tracking-[0.18em] text-muted lg:block">{t(g.key)}</p>
              {gi > 0 && <div aria-hidden className="mx-3 mb-2 border-t border-line lg:hidden" />}
              <ul className="space-y-0.5">
                {g.items.map((n) => {
                  const on = active(n);
                  const Icon = n.icon;
                  return (
                    <li key={n.href}>
                      <Link href={n.href} aria-current={on ? "page" : undefined} title={t(n.key)} className={`group relative flex h-10 items-center justify-center gap-3 rounded-lg text-sm transition-colors lg:justify-start lg:px-3 ${on ? "bg-surface-2 font-medium text-fg" : "text-fg/65 hover:bg-surface-2/60 hover:text-fg"}`}>
                        {on && <span aria-hidden className="absolute inset-y-2 left-0 w-0.5 rounded-full bg-sindoor" />}
                        <Icon aria-hidden className={`h-[18px] w-[18px] shrink-0 ${on ? "text-sindoor" : "text-muted group-hover:text-fg"}`} strokeWidth={1.9} />
                        <span className="sr-only lg:not-sr-only lg:truncate">{t(n.key)}</span>
                        {n.href === "/app/alerts" && <Badge n={alerts} className="absolute right-2 top-1.5 lg:static lg:ml-auto" />}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </nav>

        <div className="shrink-0 space-y-3 border-t border-line p-3 lg:p-4">
          <label className="hidden text-[11px] text-muted lg:block">{t("shell.language")}<LanguageSelect className="mt-1 w-full rounded-md border border-line bg-canvas px-1.5 py-1 text-sm" /></label>
          <div className="flex items-center justify-center gap-3 lg:justify-start">
            <span aria-hidden className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-fg font-mono text-xs font-bold text-canvas">{initials}</span>
            <p className="hidden min-w-0 flex-1 text-sm font-medium lg:block"><span className="block truncate">{name}</span>{persona && <span className="block truncate text-[11px] font-normal text-muted">{persona.label}</span>}</p>
            <button type="button" onClick={onSignOut} title={t("shell.signOut")} className="hidden items-center gap-1.5 rounded-lg px-2 py-1.5 text-xs text-muted hover:bg-surface-2 hover:text-fg lg:inline-flex"><LogOut aria-hidden className="h-3.5 w-3.5" />{t("shell.signOut")}</button>
          </div>
          <button type="button" onClick={onSignOut} aria-label={t("shell.signOut")} title={t("shell.signOut")} className="mx-auto grid h-9 w-9 place-items-center rounded-lg text-muted hover:bg-surface-2 hover:text-fg md:flex lg:hidden"><LogOut aria-hidden className="h-4 w-4" /></button>
        </div>
      </aside>

      {/* ---------------------------------------------------------------- content */}
      <div className="min-w-0 flex-1">
        <header className="sticky top-0 z-20 flex h-14 items-center gap-3 border-b border-line bg-canvas/90 px-4 backdrop-blur md:hidden">
          <Link href="/" aria-label="Vyapar AI home" className="shrink-0"><Logo /></Link>
          <div className="min-w-0 flex-1"><WorkspaceSelect className="w-full max-w-full rounded-full border border-line bg-surface px-3 py-1.5 text-sm" /></div>
          <LanguageSelect className="shrink-0 rounded-full border border-line bg-surface px-2 py-1.5 text-xs" />
        </header>
        <main id="main" tabIndex={-1} className="mx-auto w-full max-w-[1200px] px-4 pb-28 pt-5 outline-none sm:px-6 md:px-8 md:pb-10 md:pt-8 2xl:max-w-[1440px] 2xl:px-12">{children}</main>
      </div>

      {/* ---------------------------------------------------------------- phone: bottom bar and the full menu */}
      <nav aria-label="Main" className="fixed inset-x-0 bottom-0 z-30 border-t border-line bg-surface/95 pb-[env(safe-area-inset-bottom)] backdrop-blur md:hidden">
        <ul className="mx-auto grid max-w-md" style={{ gridTemplateColumns: `repeat(${tabs.length + 1}, minmax(0, 1fr))` }}>
          {tabs.map((n) => {
            const on = active(n);
            const Icon = n.icon;
            return (
              <li key={n.href}>
                <Link href={n.href} aria-current={on ? "page" : undefined} className={`relative flex h-16 flex-col items-center justify-center gap-1 text-[11px] ${on ? "font-semibold text-fg" : "text-fg/60"}`}>
                  <span className="relative"><Icon aria-hidden className={`h-[22px] w-[22px] ${on ? "text-sindoor" : ""}`} strokeWidth={on ? 2.2 : 1.8} />{n.href === "/app/alerts" && <Badge n={alerts} className="absolute -right-2.5 -top-1.5" />}</span>
                  <span className="max-w-full truncate px-1">{n.href === "/app" ? t("nav.home") : t(n.key)}</span>
                </Link>
              </li>
            );
          })}
          <li>
            <button type="button" onClick={() => setMore(true)} aria-haspopup="dialog" aria-expanded={more} className={`flex h-16 w-full flex-col items-center justify-center gap-1 text-[11px] ${inMore ? "font-semibold text-fg" : "text-fg/60"}`}>
              <Ellipsis aria-hidden className={`h-[22px] w-[22px] ${inMore ? "text-sindoor" : ""}`} strokeWidth={1.8} />
              <span>{t("shell.more")}</span>
            </button>
          </li>
        </ul>
      </nav>

      {more && (
        <div className="fixed inset-0 z-40 md:hidden" role="dialog" aria-modal="true" aria-label={t("shell.more")}>
          <button type="button" aria-label={t("shell.close")} tabIndex={-1} onClick={() => setMore(false)} className="absolute inset-0 bg-fg/40" />
          <div className="absolute inset-x-0 bottom-0 max-h-[88dvh] overflow-y-auto overscroll-contain rounded-t-3xl border-t border-line bg-canvas p-5 pb-[calc(1.25rem+env(safe-area-inset-bottom))] shadow-2xl">
            <div className="mx-auto mb-4 h-1 w-10 rounded-full bg-line" aria-hidden />
            <div className="mb-3 flex items-center justify-between">
              <p className="font-serif text-2xl">{workspace.name}</p>
              <button ref={closeRef} type="button" onClick={() => setMore(false)} aria-label={t("shell.close")} className="grid h-10 w-10 place-items-center rounded-full border border-line"><X aria-hidden className="h-4 w-4" /></button>
            </div>
            {groups.map((g) => (
              <section key={g.key} className="mt-4" aria-label={t(g.key)}>
                <h2 className="mb-2 font-mono text-[10px] uppercase tracking-[0.18em] text-muted">{t(g.key)}</h2>
                <ul className="grid grid-cols-3 gap-2 sm:grid-cols-4">
                  {g.items.map((n) => {
                    const Icon = n.icon;
                    const on = active(n);
                    return (
                      <li key={n.href}>
                        <Link href={n.href} aria-current={on ? "page" : undefined} className={`relative flex h-[84px] flex-col items-center justify-center gap-1.5 rounded-2xl border px-1 text-center text-xs ${on ? "border-fg bg-surface-2 font-semibold" : "border-line bg-surface"}`}>
                          <Icon aria-hidden className={`h-5 w-5 ${on ? "text-sindoor" : "text-muted"}`} strokeWidth={1.8} />
                          <span className="line-clamp-2 leading-tight">{t(n.key)}</span>
                          {n.href === "/app/alerts" && <Badge n={alerts} className="absolute right-2 top-2" />}
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              </section>
            ))}
            <div className="mt-6 flex items-center justify-between gap-3 border-t border-line pt-4">
              <span className="flex min-w-0 items-center gap-2 text-sm"><span aria-hidden className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-fg font-mono text-[11px] font-bold text-canvas">{initials}</span><span className="truncate">{name}</span></span>
              <button type="button" onClick={onSignOut} className="inline-flex items-center gap-1.5 rounded-full border border-line px-4 py-2 text-sm"><LogOut aria-hidden className="h-4 w-4" />{t("shell.signOut")}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
