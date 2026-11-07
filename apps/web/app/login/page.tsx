"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent, type PointerEvent } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { Logo } from "@/components/landing/Nav";
import { PERSONAS, type Persona } from "@/lib/personas";
import { loginWithPassword, saveSession } from "@/lib/session";

const EASE = [0.16, 1, 0.3, 1] as const;

export default function LoginPage() {
  const router = useRouter();
  const reduce = useReducedMotion();
  const [chosen, setChosen] = useState<Persona | null>(null);
  const [showForm, setShowForm] = useState(false);

  const choose = (p: Persona) => {
    if (chosen) return;
    saveSession({ kind: "persona", personaId: p.id });
    setChosen(p);
    router.prefetch("/app");
    window.setTimeout(() => router.push("/app"), reduce ? 50 : 900);
  };

  return (
    <div className="grain relative min-h-dvh overflow-hidden bg-ink">
      <div className="grid min-h-dvh lg:grid-cols-[0.9fr_1.1fr]">
        {/* Left: brand panel */}
        <aside className="relative hidden flex-col justify-between overflow-hidden border-r border-line bg-ink-2 p-10 lg:flex">
          <Link href="/" aria-label="Back to home">
            <Logo />
          </Link>
          <div className="ledger-rules -mx-10 px-10 py-10">
            <motion.p
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 1, ease: EASE }}
              className="pl-16 font-deva text-[8rem] leading-[0.9] text-sindoor"
              aria-hidden
            >
              स्वागत
            </motion.p>
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.3, duration: 1 }}
              className="mt-6 max-w-sm pl-16 font-serif text-3xl italic leading-tight text-paper/80"
            >
              Welcome back. Choose a seat at the counter.
            </motion.p>
          </div>
          <p className="max-w-xs text-sm text-paper/40">
            Demo personas use synthetic data and map to real workspace roles: owner, admin, analyst and viewer.
          </p>
        </aside>

        {/* Right: persona chooser */}
        <main className="relative flex flex-col justify-center px-5 py-16 sm:px-12">
          <div className="mb-10 flex items-center justify-between lg:hidden">
            <Link href="/" aria-label="Back to home">
              <Logo />
            </Link>
          </div>
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7, ease: EASE }}>
            <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-haldi">Sign in · demo</p>
            <h1 className="mt-3 text-4xl font-bold tracking-tight sm:text-5xl">Who&apos;s minding the shop today?</h1>
            <p className="mt-3 max-w-lg text-paper/60">Pick a persona to open their workspace. No password needed for the demo.</p>
          </motion.div>

          <ul className="mt-10 grid gap-4 sm:grid-cols-2" role="list">
            {PERSONAS.map((p, i) => (
              <motion.li
                key={p.id}
                initial={{ opacity: 0, y: 40 }}
                animate={{ opacity: chosen && chosen.id !== p.id ? 0.25 : 1, y: 0 }}
                transition={{ delay: 0.15 + i * 0.07, duration: 0.7, ease: EASE }}
              >
                <PersonaCard persona={p} onChoose={choose} active={chosen?.id === p.id} />
              </motion.li>
            ))}
          </ul>

          <div className="mt-10 max-w-md">
            <button
              type="button"
              onClick={() => setShowForm((v) => !v)}
              className="text-sm text-paper/60 underline decoration-line underline-offset-4 transition-colors hover:text-paper"
              aria-expanded={showForm}
            >
              {showForm ? "Hide email sign-in" : "Have an account? Sign in with email"}
            </button>
            <AnimatePresence initial={false}>{showForm && <EmailForm onDone={() => router.push("/app")} />}</AnimatePresence>
          </div>
        </main>
      </div>

      {/* Persona transition: the chosen colour floods the screen, then we route */}
      <AnimatePresence>
        {chosen && (
          <motion.div
            key="flood"
            className="fixed inset-0 z-[80] flex items-center justify-center"
            style={{ background: chosen.accent }}
            initial={{ clipPath: "circle(0% at 50% 50%)" }}
            animate={{ clipPath: "circle(150% at 50% 50%)" }}
            transition={{ duration: reduce ? 0 : 0.85, ease: [0.65, 0, 0.35, 1] }}
            aria-live="polite"
          >
            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.35, duration: 0.5 }}
              className="text-center text-ink"
            >
              <span className="block font-serif text-5xl italic sm:text-7xl">{chosen.greeting}</span>
              <span className="mt-3 block font-mono text-xs uppercase tracking-[0.2em]">Opening your ledger…</span>
            </motion.p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function PersonaCard({ persona: p, onChoose, active }: { persona: Persona; onChoose: (p: Persona) => void; active: boolean }) {
  const [tilt, setTilt] = useState({ x: 0, y: 0 });
  const reduce = useReducedMotion();
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
      style={{ transformPerspective: 900, ["--accent" as string]: p.accent }}
      className="group relative flex h-full w-full flex-col overflow-hidden rounded-3xl border border-line bg-ink-2 p-6 text-left transition-colors duration-300 hover:border-[var(--accent)]"
      aria-label={`Continue as ${p.name}, ${p.title}`}
    >
      <span
        aria-hidden
        className="absolute -right-10 -top-10 h-32 w-32 rounded-full opacity-15 blur-2xl transition-opacity duration-500 group-hover:opacity-40"
        style={{ background: p.accent }}
      />
      <div className="flex items-center gap-4">
        <span
          className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl font-mono text-sm font-bold text-ink"
          style={{ background: p.accent }}
          aria-hidden
        >
          {p.initials}
        </span>
        <div className="min-w-0">
          <p className="truncate font-semibold">{p.name}</p>
          <p className="truncate text-xs text-paper/50">{p.title}</p>
        </div>
        <span className="ml-auto rounded-full border border-line px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-muted">
          {p.role}
        </span>
      </div>
      <p className="mt-5 font-serif text-xl italic leading-snug text-paper/85">“{p.quote}”</p>
      <p className="mt-2 text-xs text-paper/45">{p.business}</p>
      <ul className="mt-5 flex flex-wrap gap-1.5">
        {p.focus.map((f) => (
          <li key={f} className="rounded-full bg-ink-3 px-2.5 py-1 text-[11px] text-paper/70">
            {f}
          </li>
        ))}
      </ul>
      <span className="mt-6 inline-flex items-center gap-2 text-sm font-semibold" style={{ color: p.accent }}>
        Enter workspace
        <span aria-hidden className="transition-transform duration-300 group-hover:translate-x-1">→</span>
      </span>
    </motion.button>
  );
}

function EmailForm({ onDone }: { onDone: () => void }) {
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    setBusy(true);
    setError(null);
    try {
      saveSession(await loginWithPassword(String(fd.get("email")), String(fd.get("password"))));
      onDone();
    } catch (err) {
      setError(err instanceof Error && err.message !== "Failed to fetch" ? err.message : "Could not reach the API. Is it running on port 8000?");
    } finally {
      setBusy(false);
    }
  };

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
        <label className="block">
          <span className="mb-1.5 block text-xs text-paper/60">Email</span>
          <input name="email" type="email" required autoComplete="email" className="w-full rounded-xl border border-line bg-ink-2 px-4 py-3 text-paper outline-none transition-colors focus:border-haldi" />
        </label>
        <label className="block">
          <span className="mb-1.5 block text-xs text-paper/60">Password</span>
          <input name="password" type="password" required autoComplete="current-password" className="w-full rounded-xl border border-line bg-ink-2 px-4 py-3 text-paper outline-none transition-colors focus:border-haldi" />
        </label>
        {error && (
          <p role="alert" className="text-sm text-sindoor">
            {error}
          </p>
        )}
        <button
          type="submit"
          disabled={busy}
          className="w-full rounded-xl bg-paper py-3 font-semibold text-ink transition-colors hover:bg-haldi disabled:opacity-60"
        >
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </div>
    </motion.form>
  );
}
