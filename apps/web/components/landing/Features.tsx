"use client";

import { useLayoutEffect, useRef, type PointerEvent } from "react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger);

const FEATURES = [
  {
    tag: "P0",
    title: "Command center",
    body: "Net sales, margin, orders and AOV, each with its definition, period, filters and data freshness.",
    span: "sm:col-span-2 lg:col-span-4",
    art: <BarsArt />,
  },
  {
    tag: "P0",
    title: "Festival-aware forecasts",
    body: "Baselines first, honest intervals, and Diwali and wedding season built in.",
    span: "lg:col-span-2",
    art: <WaveArt />,
  },
  {
    tag: "P0",
    title: "Customer RFM",
    body: "New, repeat and lapsed customers using rules you can read.",
    span: "lg:col-span-2",
    art: <DotsArt />,
  },
  {
    tag: "P1",
    title: "Reorder simulator",
    body: "Lead time, safety stock and demand sliders. Purchase orders stay drafts until you approve them.",
    span: "lg:col-span-2",
    art: <StockArt />,
  },
  {
    tag: "P1",
    title: "Hinglish reviews",
    body: "“delivery late tha but quality ekdum mast” becomes delivery −, quality +.",
    span: "lg:col-span-2",
    art: <QuoteArt />,
  },
  {
    tag: "P1",
    title: "Copilot with citations",
    body: "Ask in plain words. Numbers come from the metric layer and every claim links to its source.",
    span: "sm:col-span-2 lg:col-span-6",
    art: <CopilotArt />,
  },
];

export function Features() {
  const root = useRef<HTMLElement>(null);

  useLayoutEffect(() => {
    const ctx = gsap.context(() => {
      gsap.from("[data-card]", {
        opacity: 0,
        y: 70,
        rotateX: -12,
        stagger: 0.08,
        duration: 1,
        ease: "expo.out",
        scrollTrigger: { trigger: root.current, start: "top 70%" },
      });
    }, root);
    return () => ctx.revert();
  }, []);

  const onMove = (e: PointerEvent<HTMLElement>) => {
    const r = e.currentTarget.getBoundingClientRect();
    e.currentTarget.style.setProperty("--mx", `${e.clientX - r.left}px`);
    e.currentTarget.style.setProperty("--my", `${e.clientY - r.top}px`);
  };

  return (
    <section ref={root} className="relative mx-auto max-w-7xl px-5 py-32 sm:px-10" aria-labelledby="features-title">
      <div className="mb-14 flex flex-col justify-between gap-6 md:flex-row md:items-end">
        <h2 id="features-title" className="max-w-2xl text-5xl font-bold leading-[0.95] tracking-tight sm:text-6xl">
          Built for the <span className="font-serif font-normal italic text-sindoor">dukaan</span>,
          <br /> not the boardroom.
        </h2>
        <p className="max-w-sm text-paper/60">
          Each capability ships only when it is tested, documented and can explain itself. The P0/P1 labels follow
          our public roadmap.
        </p>
      </div>
      <div className="grid gap-4 [perspective:1200px] sm:grid-cols-2 lg:grid-cols-6">
        {FEATURES.map((f) => (
          <article
            key={f.title}
            data-card
            onPointerMove={onMove}
            className={`group relative overflow-hidden rounded-3xl border border-line bg-ink-2 p-7 transition-colors duration-500 hover:border-haldi/40 ${f.span}`}
          >
            <div
              aria-hidden
              className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-500 group-hover:opacity-100"
              style={{
                background:
                  "radial-gradient(420px circle at var(--mx) var(--my), color-mix(in oklab, var(--color-haldi) 13%, transparent), transparent 60%)",
              }}
            />
            <div className="relative flex h-full flex-col">
              <span className="w-fit rounded-full border border-line px-2.5 py-1 font-mono text-[10px] tracking-[0.18em] text-muted">
                {f.tag}
              </span>
              <div className="my-8 flex min-h-28 items-center">{f.art}</div>
              <h3 className="text-2xl font-bold tracking-tight">{f.title}</h3>
              <p className="mt-2 max-w-xl text-paper/60">{f.body}</p>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function BarsArt() {
  const h = [38, 52, 44, 61, 58, 72, 66, 80, 76, 92, 84, 98];
  return (
    <div className="flex h-28 w-full items-end gap-1.5" aria-hidden>
      {h.map((v, i) => (
        <span
          key={i}
          className="flex-1 origin-bottom rounded-t-sm bg-paper/15 transition-all duration-500 group-hover:bg-haldi/80"
          style={{ height: `${v}%`, transitionDelay: `${i * 25}ms` }}
        />
      ))}
    </div>
  );
}

function WaveArt() {
  return (
    <svg viewBox="0 0 200 80" className="w-full" aria-hidden>
      <path d="M0,60 C30,55 45,50 70,48 S110,15 125,12 S160,45 200,40" fill="none" stroke="var(--color-paper)" strokeOpacity=".3" strokeWidth="2" />
      <path d="M0,60 C30,55 45,50 70,48 S110,15 125,12 S160,45 200,40" fill="none" stroke="var(--color-haldi)" strokeWidth="2" strokeDasharray="4 5" className="transition-[stroke-dashoffset] duration-[1.5s] group-hover:[stroke-dashoffset:-60]" />
      <circle cx="125" cy="12" r="4" fill="var(--color-sindoor)" />
    </svg>
  );
}

function DotsArt() {
  return (
    <div className="grid w-full grid-cols-10 gap-1.5" aria-hidden>
      {Array.from({ length: 30 }, (_, i) => (
        <span
          key={i}
          className={`aspect-square rounded-full transition-transform duration-500 group-hover:scale-110 ${
            i % 7 === 0 ? "bg-sindoor" : i % 3 === 0 ? "bg-mor" : "bg-paper/20"
          }`}
        />
      ))}
    </div>
  );
}

function StockArt() {
  return (
    <div className="w-full space-y-2 font-mono text-[11px]" aria-hidden>
      {[
        ["Gift box", 34, "text-sindoor"],
        ["Ghee 1L", 68, "text-haldi"],
        ["Atta 5kg", 91, "text-mor"],
      ].map(([n, v, c]) => (
        <div key={n as string}>
          <div className="mb-1 flex justify-between text-paper/60">
            <span>{n}</span>
            <span className={c as string}>{v}% cover</span>
          </div>
          <div className="h-1.5 rounded-full bg-line">
            <div className="h-full rounded-full bg-paper/50 transition-all duration-700 group-hover:bg-haldi" style={{ width: `${v}%` }} />
          </div>
        </div>
      ))}
    </div>
  );
}

function QuoteArt() {
  return (
    <p className="font-serif text-2xl italic leading-snug text-paper/80" aria-hidden>
      “delivery <span className="text-sindoor underline decoration-wavy underline-offset-4">late tha</span> but quality{" "}
      <span className="text-mor underline decoration-wavy underline-offset-4">ekdum mast</span>”
    </p>
  );
}

function CopilotArt() {
  return (
    <div className="grid w-full gap-3 md:grid-cols-[1fr_1.4fr]" aria-hidden>
      <div className="self-start rounded-2xl rounded-br-sm bg-paper px-4 py-3 text-sm text-ink">
        Why did sales dip last Tuesday?
      </div>
      <div className="rounded-2xl rounded-tl-sm border border-line bg-ink p-4 text-sm text-paper/80">
        Net sales were <b className="text-paper">₹41,200</b> (−18% vs. the previous 4 Tuesdays). 72% of the drop came from{" "}
        <b className="text-paper">Staples</b>, mostly fewer orders rather than lower prices.
        <div className="mt-3 flex flex-wrap gap-2 font-mono text-[10px]">
          <span className="rounded border border-line px-2 py-0.5 text-haldi">[1] metric:net_sales v1</span>
          <span className="rounded border border-line px-2 py-0.5 text-haldi">[2] drivers: volume/price/mix</span>
        </div>
      </div>
    </div>
  );
}
