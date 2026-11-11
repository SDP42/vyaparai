"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent, type PointerEvent } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { Logo } from "@/components/landing/Nav";
import { demoPersonas, loginDemo, loginWithPassword, registerAccount, saveSession, type DemoPersona } from "@/lib/session";

const EASE = [0.16, 1, 0.3, 1] as const;

/** Look and a line in each person's own words (display only; what they may see is decided by the server). */
const LOOK: Record<string, { accent: string; quote: string; focus: string[]; greeting: string }> = {
  owner: { accent: "var(--color-sindoor)", quote: "I want to know where my profit went this month.", focus: ["Profit and margin", "Who owes me", "Festival prep"], greeting: "Namaste Meera" },
  ops_manager: { accent: "var(--color-haldi)", quote: "Tell me what will run out before it does.", focus: ["Stock-out risk", "What to order", "Dead stock"], greeting: "Namaste Arjun" },
  analyst: { accent: "var(--color-mor)", quote: "Show me the drivers, not just the totals.", focus: ["Why sales moved", "Customers", "Margins"], greeting: "Namaste Zoya" },
  accountant: { accent: "var(--color-neel)", quote: "I need clean numbers that match the books.", focus: ["Sales and margin", "Credit ageing", "Reports"], greeting: "Namaste Kabir" },
  cashier: { accent: "var(--color-sindoor)", quote: "Is it in stock? What is the price?", focus: ["Stock and price", "What sells", "Return rules"], greeting: "Namaste Sunita" },
};
const initials = (n: string) => n.split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase();

export default function LoginPage() {
  const router = useRouter();
  const reduce = useReducedMotion();
  const [people, setPeople] = useState<DemoPersona[] | null>(null);
  const [chosen, setChosen] = useState<DemoPersona | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    demoPersonas().then((p) => {
      setPeople(p);
      if (p.length === 0) setShowForm(true); // no sample accounts here: the account form is the only way in
    });
    // "/login?mode=account" opens the account form straight away.
    if (new URLSearchParams(window.location.search).get("mode") === "account") setShowForm(true);
  }, []);

  const choose = async (p: DemoPersona) => {
    if (chosen) return;
    setError(null);
    setChosen(p);
    try {
      saveSession(await loginDemo(p.key));
      router.prefetch("/app");
      window.setTimeout(() => router.push("/app"), reduce ? 50 : 900);
    } catch (e) {
      setChosen(null);
      setError(e instanceof Error && e.message !== "Failed to fetch" ? e.message : "Could not reach the API. Is it running on port 8000?");
    }
  };

  return (
    <div className="grain relative min-h-dvh overflow-hidden bg-canvas">
      <div className="grid min-h-dvh lg:grid-cols-[0.9fr_1.1fr]">
        <aside className="relative hidden flex-col justify-between overflow-hidden border-r border-line bg-surface p-10 lg:flex">
          <Link href="/" aria-label="Back to home">
            <Logo />
          </Link>
          <div className="ledger-rules -mx-10 px-10 py-10">
            <motion.p initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 1, ease: EASE }} className="pl-16 font-deva text-[8rem] leading-[0.9] text-sindoor" aria-hidden>
              स्वागत
            </motion.p>
            <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3, duration: 1 }} className="mt-6 max-w-sm pl-16 font-serif text-3xl italic leading-tight text-fg/80">
              Welcome back. Choose a seat at the counter.
            </motion.p>
          </div>
          <p className="max-w-xs text-sm text-fg/40">
            Each person sees only what their job needs, and the assistant answers only their kind of questions. The sample shop uses synthetic data.
          </p>
        </aside>

        <main className="relative flex flex-col justify-center px-5 py-16 sm:px-12">
          <div className="mb-10 flex items-center justify-between lg:hidden">
            <Link href="/" aria-label="Back to home">
              <Logo />
            </Link>
          </div>
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7, ease: EASE }}>
            <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-haldi-deep">{people && people.length ? "Sign in · sample shop" : "Sign in"}</p>
            <h1 className="mt-3 text-4xl font-bold tracking-tight sm:text-5xl">{people && people.length ? "Who is at the counter today?" : "Welcome back"}</h1>
            {people && people.length > 0 && <p className="mt-3 max-w-lg text-fg/60">Pick a person to open the shop as them. No password for the sample shop.</p>}
          </motion.div>

          {error && (
            <p role="alert" className="mt-6 text-sm text-sindoor">
              {error}
            </p>
          )}

          {people && people.length > 0 && (
            <ul className="mt-10 grid gap-4 sm:grid-cols-2" role="list">
              {people.map((p, i) => (
                <motion.li key={p.key} initial={{ opacity: 0, y: 40 }} animate={{ opacity: chosen && chosen.key !== p.key ? 0.25 : 1, y: 0 }} transition={{ delay: 0.15 + i * 0.07, duration: 0.7, ease: EASE }}>
                  <PersonaCard person={p} onChoose={choose} active={chosen?.key === p.key} />
                </motion.li>
              ))}
            </ul>
          )}

          <div className="mt-10 max-w-md">
            {people && people.length > 0 && (
              <button type="button" onClick={() => setShowForm((v) => !v)} className="text-sm text-fg/60 underline decoration-line underline-offset-4 transition-colors hover:text-fg" aria-expanded={showForm}>
                {showForm ? "Hide email sign-in" : "Use your own data: sign in or create an account"}
              </button>
            )}
            <AnimatePresence initial={false}>{showForm && <EmailForm onDone={() => router.push(sessionStorage.getItem("vyapar.invite") ? "/join" : "/app")} />}</AnimatePresence>
          </div>
        </main>
      </div>

      <AnimatePresence>
        {chosen && (
          <motion.div
            key="flood"
            className="fixed inset-0 z-[80] flex items-center justify-center"
            style={{ background: LOOK[chosen.key]?.accent ?? "var(--color-haldi)" }}
            initial={{ clipPath: "circle(0% at 50% 50%)" }}
            animate={{ clipPath: "circle(150% at 50% 50%)" }}
            transition={{ duration: reduce ? 0 : 0.85, ease: [0.65, 0, 0.35, 1] }}
            aria-live="polite"
          >
            <motion.p initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.35, duration: 0.5 }} className="text-center text-ink">
              <span className="block font-serif text-5xl italic sm:text-7xl">{LOOK[chosen.key]?.greeting ?? "Namaste"}</span>
              <span className="mt-3 block font-mono text-xs uppercase tracking-[0.2em]">Opening your ledger…</span>
            </motion.p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function PersonaCard({ person: p, onChoose, active }: { person: DemoPersona; onChoose: (p: DemoPersona) => void; active: boolean }) {
  const [tilt, setTilt] = useState({ x: 0, y: 0 });
  const reduce = useReducedMotion();
  const look = LOOK[p.key] ?? LOOK.owner;
  const onMove = (e: PointerEvent<HTMLButtonElement>) => {
    if (reduce) return;
    const r = e.currentTarget.getBoundingClientRect();
    setTilt({ x: ((e.clientY - r.top) / r.height - 0.5) * -8, y: ((e.clientX - r.left) / r.width - 0.5) * 10 });
  };

  return (
    <motion.button
      type="button"
      onClick={() => onChoose(p)}
      onPointerMove={onMove}
      onPointerLeave={() => setTilt({ x: 0, y: 0 })}
      animate={{ rotateX: tilt.x, rotateY: tilt.y, scale: active ? 1.03 : 1 }}
      transition={{ type: "spring", stiffness: 220, damping: 20 }}
      whileTap={{ scale: 0.98 }}
      style={{ transformPerspective: 900, ["--accent" as string]: look.accent }}
      className="group relative flex h-full w-full flex-col overflow-hidden rounded-3xl border border-line bg-surface p-6 text-left transition-colors duration-300 hover:border-[var(--accent)]"
      aria-label={`Continue as ${p.name}, ${p.label.en}`}
    >
      <span aria-hidden className="absolute -right-10 -top-10 h-32 w-32 rounded-full opacity-15 blur-2xl transition-opacity duration-500 group-hover:opacity-40" style={{ background: look.accent }} />
      <div className="flex items-center gap-4">
        <span className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl font-mono text-sm font-bold text-ink" style={{ background: look.accent }} aria-hidden>
          {initials(p.name)}
        </span>
        <div className="min-w-0">
          <p className="font-semibold leading-tight">{p.name}</p>
          <p className="mt-0.5 text-xs text-fg/50">
            {p.label.en} · <span lang="hi">{p.label.hi}</span>
          </p>
        </div>
      </div>
      <p className="mt-5 font-serif text-xl italic leading-snug text-fg/85">“{look.quote}”</p>
      <p className="mt-2 text-xs text-fg/45">{p.about.en}</p>
      <ul className="mt-5 flex flex-wrap gap-1.5">
        {look.focus.map((f) => (
          <li key={f} className="rounded-full bg-surface-2 px-2.5 py-1 text-[11px] text-fg/70">
            {f}
          </li>
        ))}
      </ul>
      <span className="mt-6 inline-flex items-center gap-2 text-sm font-semibold" style={{ color: look.accent }}>
        Enter the shop
        <span aria-hidden className="transition-transform duration-300 group-hover:translate-x-1">→</span>
      </span>
    </motion.button>
  );
}

function EmailForm({ onDone }: { onDone: () => void }) {
  const [mode, setMode] = useState<"signin" | "register">("signin");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const email = String(fd.get("email") ?? "");
    const password = String(fd.get("password") ?? "");
    setBusy(true);
    setError(null);
    try {
      const session =
        mode === "register"
          ? await registerAccount(String(fd.get("name") ?? ""), email, password)
          : await loginWithPassword(email, password);
      saveSession(session);
      onDone();
    } catch (err) {
      setError(err instanceof Error && err.message !== "Failed to fetch" ? err.message : "Could not reach the API. Is it running on port 8000?");
    } finally {
      setBusy(false);
    }
  };

  const input = "w-full rounded-xl border border-line bg-surface px-4 py-3 text-fg outline-none transition-colors focus:border-haldi";

  return (
    <motion.form
      onSubmit={submit}
      initial={{ height: 0, opacity: 0 }}
      animate={{ height: "auto", opacity: 1 }}
      exit={{ height: 0, opacity: 0 }}
      transition={{ duration: 0.35, ease: EASE }}
      className="overflow-hidden"
      noValidate
    >
      <div className="space-y-3 pt-5">
        <div role="tablist" aria-label="Account" className="flex gap-1 rounded-full border border-line bg-surface p-1 text-sm">
          {(["signin", "register"] as const).map((m) => (
            <button
              key={m}
              type="button"
              role="tab"
              aria-selected={mode === m}
              onClick={() => {
                setMode(m);
                setError(null);
              }}
              className={`flex-1 rounded-full py-1.5 transition-colors ${mode === m ? "bg-fg text-canvas" : "text-fg/60 hover:text-fg"}`}
            >
              {m === "signin" ? "Sign in" : "Create account"}
            </button>
          ))}
        </div>
        {mode === "register" && (
          <label className="block">
            <span className="mb-1.5 block text-xs text-fg/60">Full name</span>
            <input name="name" type="text" required autoComplete="name" className={input} />
          </label>
        )}
        <label className="block">
          <span className="mb-1.5 block text-xs text-fg/60">Email</span>
          <input name="email" type="email" required autoComplete="email" className={input} />
        </label>
        <label className="block">
          <span className="mb-1.5 block text-xs text-fg/60">Password{mode === "register" ? " (10+ characters)" : ""}</span>
          <input
            name="password"
            type="password"
            required
            minLength={mode === "register" ? 10 : undefined}
            autoComplete={mode === "register" ? "new-password" : "current-password"}
            className={input}
          />
        </label>
        {error && (
          <p role="alert" className="text-sm text-sindoor">
            {error}
          </p>
        )}
        <button
          type="submit"
          disabled={busy}
          className="w-full rounded-xl bg-fg py-3 font-semibold text-canvas transition-colors hover:bg-sindoor disabled:opacity-60"
        >
          {busy ? "Please wait…" : mode === "register" ? "Create account" : "Sign in"}
        </button>
      </div>
    </motion.form>
  );
}
