"use client";

import { useLayoutEffect, useRef } from "react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger);

const ENTRIES = [
  "₹18,46,320 net sales ▲ 8.4%",
  "3,412 orders",
  "AOV ₹541",
  "17 SKUs at stock-out risk",
  "Diwali forecast +12%",
  "1,284 active customers",
  "GST ₹2,21,558",
  "UPI 64% · Cash 29% · Card 7%",
];

const PRINCIPLES = [
  { k: "01", t: "Numbers come from SQL, not from a language model.", d: "One metric registry powers the dashboards, the API and the Copilot." },
  { k: "02", t: "Every insight shows its working.", d: "Period, filters, definition version and data freshness travel with each figure." },
  { k: "03", t: "Humans approve every action.", d: "Agents can read and suggest. They cannot buy anything, change permissions or write to the database." },
  { k: "04", t: "Your shop's data stays your shop's data.", d: "Each workspace is isolated and checked on the server. Every sensitive action is written to an audit log." },
];

export function Principles() {
  const root = useRef<HTMLElement>(null);

  useLayoutEffect(() => {
    const ctx = gsap.context(() => {
      gsap.utils.toArray<HTMLElement>("[data-principle]").forEach((row) => {
        gsap.fromTo(
          row.querySelector("[data-strike]"),
          { scaleX: 0 },
          { scaleX: 1, ease: "none", scrollTrigger: { trigger: row, start: "top 80%", end: "top 45%", scrub: true } },
        );
        gsap.from(row.querySelectorAll("[data-fade]"), {
          opacity: 0,
          y: 30,
          stagger: 0.1,
          duration: 0.9,
          ease: "expo.out",
          scrollTrigger: { trigger: row, start: "top 82%" },
        });
      });
    }, root);
    return () => ctx.revert();
  }, []);

  return (
    <section ref={root} id="principles" className="relative py-28" aria-labelledby="principles-title">
      <div className="space-y-3 overflow-hidden border-y border-line py-5 font-mono text-sm" aria-hidden>
        <div className="flex w-max marquee">
          {[...ENTRIES, ...ENTRIES].map((e, i) => (
            <span key={i} className="mx-6 whitespace-nowrap text-fg/70">
              <span className="mr-6 text-sindoor">◆</span>
              {e}
            </span>
          ))}
        </div>
        <div className="flex w-max marquee-reverse">
          {[...ENTRIES, ...ENTRIES].reverse().map((e, i) => (
            <span key={i} className="mx-6 whitespace-nowrap text-muted">
              <span className="mr-6 text-haldi-deep">◇</span>
              {e}
            </span>
          ))}
        </div>
      </div>

      <div className="ledger-rules mx-auto mt-24 max-w-6xl px-5 sm:px-10">
        <h2 id="principles-title" className="pl-16 text-5xl font-bold tracking-tight sm:text-6xl">
          Our <span className="font-serif font-normal italic text-haldi-deep">rules</span> of the ledger
        </h2>
        <ol className="mt-12">
          {PRINCIPLES.map((p) => (
            <li key={p.k} data-principle className="relative grid gap-3 border-b border-line py-9 pl-16 md:grid-cols-[1.4fr_1fr] md:gap-10">
              <span data-fade className="absolute left-0 top-10 font-mono text-sm text-sindoor">{p.k}</span>
              <h3 data-fade className="relative text-2xl font-semibold leading-snug sm:text-3xl">
                {p.t}
                <span data-strike aria-hidden className="absolute -bottom-2 left-0 h-[2px] w-full origin-left bg-sindoor/70" />
              </h3>
              <p data-fade className="text-fg/60 md:pt-1">{p.d}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
