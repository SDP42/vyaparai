"use client";

import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { EASE } from "./ui";

const LINKS = [
  { href: "#platform", label: "Platform" },
  { href: "#solutions", label: "Solutions" },
  { href: "#how-it-works", label: "How It Works" },
  { href: "#about", label: "About" },
];

export function Wordmark({ className = "" }: { className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2 font-semibold tracking-[0.12em] ${className}`}>
      <svg aria-hidden width="22" height="22" viewBox="0 0 24 24" className="shrink-0">
        <defs>
          <linearGradient id="vg" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#9d8bf2" />
            <stop offset="1" stopColor="#3296f5" />
          </linearGradient>
        </defs>
        <path d="M3 4h4.2L12 15.5 16.8 4H21l-7.4 16h-3.2z" fill="url(#vg)" />
        <circle cx="12" cy="6.2" r="1.6" fill="#c6a66b" />
      </svg>
      <span>
        VYAPAR<span className="text-muted">.AI</span>
      </span>
    </span>
  );
}

export function Navigation() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    document.documentElement.style.overflow = open ? "hidden" : "";
  }, [open]);

  return (
    <header className="fixed inset-x-0 top-0 z-50">
      <div
        className={`mx-auto mt-3 flex h-14 max-w-6xl items-center justify-between rounded-full px-4 transition-[background,border-color,box-shadow,margin] duration-500 sm:px-5 ${
          scrolled
            ? "mx-3 border border-line bg-white/80 shadow-[0_20px_60px_-30px_rgba(11,16,32,0.35)] backdrop-blur-xl sm:mx-auto"
            : "border border-transparent"
        }`}
      >
        <a href="#top" aria-label="Vyapar.ai home" className="text-sm">
          <Wordmark />
        </a>
        <nav aria-label="Main" className="hidden md:block">
          <ul className="flex items-center gap-1">
            {LINKS.map((l) => (
              <li key={l.href}>
                <a href={l.href} className="rounded-full px-4 py-2 text-sm text-muted transition-colors hover:bg-fg/5 hover:text-fg">
                  {l.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>
        <div className="flex items-center gap-2">
          <a
            href="#get-started"
            className="hidden h-9 items-center rounded-full bg-fg px-4 text-sm font-medium text-white transition-colors hover:bg-violet sm:inline-flex"
          >
            Get Started
          </a>
          <button
            type="button"
            className="grid h-9 w-9 place-items-center rounded-full border border-line md:hidden"
            aria-label={open ? "Close menu" : "Open menu"}
            aria-expanded={open}
            onClick={() => setOpen((v) => !v)}
          >
            <span className="relative block h-3 w-4" aria-hidden>
              <span className={`absolute left-0 top-0 h-px w-4 bg-fg transition-transform ${open ? "translate-y-1.5 rotate-45" : ""}`} />
              <span className={`absolute bottom-0 left-0 h-px w-4 bg-fg transition-transform ${open ? "-translate-y-1.5 -rotate-45" : ""}`} />
            </span>
          </button>
        </div>
      </div>

      <AnimatePresence>
        {open && (
          <motion.nav
            aria-label="Mobile"
            className="fixed inset-0 -z-10 flex flex-col justify-center bg-canvas/95 px-8 backdrop-blur-xl md:hidden"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25 }}
          >
            <ul className="space-y-2">
              {[...LINKS, { href: "#get-started", label: "Get Started" }].map((l, i) => (
                <motion.li
                  key={l.href}
                  initial={{ opacity: 0, y: 24 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.05 + i * 0.05, duration: 0.5, ease: EASE }}
                >
                  <a href={l.href} onClick={() => setOpen(false)} className="block py-2 text-4xl font-semibold tracking-tight">
                    {l.label}
                  </a>
                </motion.li>
              ))}
            </ul>
          </motion.nav>
        )}
      </AnimatePresence>
    </header>
  );
}
