"use client";

import Link from "next/link";
import { useRef, type PointerEvent } from "react";
import { Logo } from "./Nav";

export function Cta() {
  const btn = useRef<HTMLAnchorElement>(null);

  // Magnetic button: follows the pointer a little, springs back on leave.
  const onMove = (e: PointerEvent<HTMLDivElement>) => {
    const b = btn.current;
    if (!b || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const r = b.getBoundingClientRect();
    const dx = e.clientX - (r.left + r.width / 2);
    const dy = e.clientY - (r.top + r.height / 2);
    b.style.transform = `translate(${dx * 0.25}px, ${dy * 0.3}px)`;
  };
  const onLeave = () => {
    if (btn.current) btn.current.style.transform = "";
  };

  return (
    <section className="relative overflow-hidden px-5 pb-10 pt-32 sm:px-10" aria-labelledby="cta-title">
      <div className="mx-auto max-w-7xl">
        <p className="font-deva text-[clamp(4rem,18vw,16rem)] leading-[0.9] text-sindoor/90" aria-hidden>
          शुभ लाभ
        </p>
        <div className="mt-6 flex flex-col items-start justify-between gap-10 md:flex-row md:items-end">
          <h2 id="cta-title" className="max-w-2xl text-5xl font-bold leading-[0.95] tracking-tight sm:text-7xl">
            Open your
            <br />
            <span className="font-serif font-normal italic text-haldi-deep">first page.</span>
          </h2>
          <div onPointerMove={onMove} onPointerLeave={onLeave} className="-m-10 p-10">
            <Link
              ref={btn}
              href="/login"
              className="group relative inline-flex h-40 w-40 items-center justify-center rounded-full bg-sindoor text-center font-semibold text-canvas transition-[transform,background-color] duration-300 ease-out hover:bg-sindoor-deep sm:h-48 sm:w-48"
            >
              <span className="leading-tight">
                Choose a
                <br />
                persona →
              </span>
              <span aria-hidden className="absolute inset-0 rounded-full border border-sindoor/50 transition-transform duration-700 group-hover:scale-125 group-hover:opacity-0" />
            </Link>
          </div>
        </div>
      </div>

      <footer className="mx-auto mt-32 flex max-w-7xl flex-col gap-6 border-t border-line pt-8 text-sm text-fg/50 md:flex-row md:items-center md:justify-between">
        <Logo />
        <p>Built as a portfolio-grade engineering case study. Demo figures are synthetic.</p>
        <p className="font-mono text-xs">© {new Date().getFullYear()} Vyapar AI</p>
      </footer>
    </section>
  );
}
