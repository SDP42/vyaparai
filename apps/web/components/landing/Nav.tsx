"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

export function Logo({ className = "" }: { className?: string }) {
  return (
    <span className={`inline-flex items-baseline gap-1.5 font-display text-lg font-bold tracking-tight ${className}`}>
      <span aria-hidden className="relative top-[1px] inline-block h-3 w-3 rotate-45 bg-sindoor" />
      vyapar<span className="font-serif text-xl font-normal italic text-haldi-deep">ai</span>
    </span>
  );
}

const LINKS = [
  { href: "#story", label: "How it works" },
  { href: "#product", label: "Product" },
  { href: "#principles", label: "Principles" },
];

export function Nav() {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={`fixed inset-x-0 top-0 z-50 transition-[background,border-color,backdrop-filter] duration-300 ${
        scrolled ? "border-b border-line/60 bg-canvas/70 backdrop-blur-md" : "border-b border-transparent"
      }`}
    >
      <nav className="mx-auto flex h-16 max-w-7xl items-center justify-between px-5 sm:px-10" aria-label="Main">
        <Link href="/" aria-label="Vyapar AI home">
          <Logo />
        </Link>
        <ul className="hidden items-center gap-8 md:flex">
          {LINKS.map((l) => (
            <li key={l.href}>
              <a href={l.href} className="group relative text-sm text-fg/70 transition-colors hover:text-fg">
                {l.label}
                <span className="absolute -bottom-1 left-0 h-px w-full origin-right scale-x-0 bg-haldi transition-transform duration-300 group-hover:origin-left group-hover:scale-x-100" />
              </a>
            </li>
          ))}
        </ul>
        <Link
          href="/login"
          className="group inline-flex items-center gap-2 rounded-full bg-fg px-4 py-2 text-sm font-semibold text-canvas transition-colors hover:bg-sindoor"
        >
          Sign in
          <span aria-hidden className="transition-transform duration-300 group-hover:translate-x-0.5">→</span>
        </Link>
      </nav>
    </header>
  );
}
