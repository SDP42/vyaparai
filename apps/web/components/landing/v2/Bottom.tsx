"use client";

import Link from "next/link";
import { useLayoutEffect, useRef } from "react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { Logo } from "../Nav";
import { AlertScreen, BillScreen, ForecastScreen, OrderScreen, UdhaarScreen } from "./Screens";

gsap.registerPlugin(ScrollTrigger);

const motionOk = "(prefers-reduced-motion: no-preference)";

/* ------------------------------------------------------------------ features: real screens, revealed as they arrive */

const SHOTS = [
  {
    title: "Udhaar, in the order to chase it",
    body: "Payments settle the oldest entry first, so ages are honest. A polite reminder is drafted in Hinglish; you send it.",
    screen: <UdhaarScreen />,
    span: "lg:col-span-7",
  },
  {
    title: "What to order before it runs out",
    body: "Days of stock left at the forecast rate, and the cash sitting in stock that stopped moving.",
    screen: <OrderScreen />,
    span: "lg:col-span-5",
  },
  {
    title: "A bill photo becomes your costs",
    body: "Each line is read, you check it, and a supplier's quiet price rise shows up the same day.",
    screen: <BillScreen />,
    span: "lg:col-span-5",
  },
  {
    title: "Forecasts that admit a range",
    body: "Festival weeks included. The page tells you how far off the model was last month.",
    screen: <ForecastScreen />,
    span: "lg:col-span-7",
  },
  {
    title: "Told when something changes",
    body: "A fall in sales, a cost that rose while your price did not, regulars who went quiet.",
    screen: <AlertScreen />,
    span: "lg:col-span-12 lg:grid lg:grid-cols-2 lg:items-center",
  },
];

export function Showcase() {
  const root = useRef<HTMLElement>(null);
  useLayoutEffect(() => {
    const mm = gsap.matchMedia();
    mm.add(motionOk, () => {
      gsap.utils.toArray<HTMLElement>("[data-shot]").forEach((el) => {
        gsap.fromTo(
          el.querySelector("[data-reveal]"),
          { clipPath: "inset(18% 10% 18% 10% round 28px)", scale: 1.06 },
          { clipPath: "inset(0% 0% 0% 0% round 20px)", scale: 1, ease: "none", scrollTrigger: { trigger: el, start: "top 88%", end: "top 40%", scrub: 0.5 } },
        );
        gsap.from(el.querySelector("[data-copy]"), { y: 24, opacity: 0, duration: 0.9, ease: "expo.out", scrollTrigger: { trigger: el, start: "top 75%" } });
      });
    }, root);
    return () => mm.revert();
  }, []);
  return (
    <section ref={root} id="features" aria-labelledby="features-title" className="mx-auto max-w-[1240px] px-5 py-28 sm:px-10 lg:py-36">
      <div className="max-w-2xl">
        <h2 id="features-title" className="text-[clamp(2.2rem,4.2vw,3.6rem)] font-bold leading-[1] tracking-[-0.03em]">The jobs a shop does every day, with the numbers already done.</h2>
        <p className="mt-5 text-lg text-fg/70">Screens from the sample shop, Kulkarni General Store, with its demo numbers.</p>
      </div>
      <div className="mt-16 grid gap-6 lg:grid-cols-12">
        {SHOTS.map((s) => (
          <article key={s.title} data-shot className={`rounded-[28px] border border-line bg-surface p-3 ${s.span}`}>
            <div data-reveal className="overflow-hidden rounded-[20px] bg-canvas will-change-transform" aria-hidden>
              {s.screen}
            </div>
            <div data-copy className="px-3 pb-3 pt-5">
              <h3 className="text-xl font-semibold tracking-tight">{s.title}</h3>
              <p className="mt-1.5 max-w-xl text-[15px] leading-relaxed text-fg/70">{s.body}</p>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ jobs: stacking cards */

const JOBS = [
  { who: "Owner", sees: "Everything: sales, profit, stock, credit, staff.", asks: "Is hafte kya karna chahiye?", tone: "bg-fg text-canvas" },
  { who: "Operations manager", sees: "Stock, orders, suppliers, festivals. Not your margins.", asks: "Pehle kya khatam hoga?", tone: "bg-[#2c241d] text-canvas" },
  { who: "Accountant", sees: "Sales, costs, credit ageing, reports. View only.", asks: "Pichle mahine ki bikri?", tone: "bg-surface text-fg" },
  { who: "Analyst", sees: "Why sales moved, customers, margins, prices.", asks: "Kaun se grahak aana band hue?", tone: "bg-surface-2 text-fg" },
  { who: "Counter staff", sees: "Stock and price of an item, their own sales. No profit, no credit book.", asks: "बासमती चावल स्टॉक में है?", tone: "bg-[#c98f1f] text-fg" },
];

export function Jobs() {
  return (
    <section id="team" aria-labelledby="team-title" className="border-t border-line bg-canvas">
      <div className="mx-auto grid max-w-[1240px] gap-12 px-5 py-28 sm:px-10 lg:grid-cols-[0.8fr_1.2fr] lg:py-36">
        <div className="lg:sticky lg:top-28 lg:self-start">
          <h2 id="team-title" className="text-[clamp(2.2rem,4.2vw,3.6rem)] font-bold leading-[1] tracking-[-0.03em]">Everyone at the shop sees their part.</h2>
          <p className="mt-5 max-w-md text-lg leading-relaxed text-fg/70">
            Each person has a job. The assistant answers that job&apos;s questions and politely refuses the rest. Cost and
            margin are removed on the server, not just hidden on the screen.
          </p>
        </div>
        <ol className="space-y-6">
          {JOBS.map((j, i) => (
            <li
              key={j.who}
              className={`rounded-[28px] border border-line p-7 shadow-[0_30px_60px_-40px_rgba(40,20,0,.6)] [@media(min-height:700px)]:sticky ${j.tone}`}
              style={{ top: `calc(6rem + ${i * 22}px)` }}
            >
              <p className="text-2xl font-semibold tracking-tight">{j.who}</p>
              <p className="mt-2 max-w-lg text-[15px] leading-relaxed opacity-80">{j.sees}</p>
              <p className={`mt-6 inline-block rounded-2xl border border-current/20 px-4 py-2 text-[15px] ${/[ऀ-ॿ]/.test(j.asks) ? "font-deva" : ""}`}>“{j.asks}”</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ voice */

export function Voice() {
  const root = useRef<HTMLElement>(null);
  useLayoutEffect(() => {
    const mm = gsap.matchMedia();
    mm.add(motionOk, () => {
      const tl = gsap.timeline({ scrollTrigger: { trigger: root.current, start: "top 65%" } });
      tl.fromTo("[data-wave] rect", { scaleY: 0.08 }, { scaleY: 1, duration: 0.6, stagger: { each: 0.012, from: "start" }, ease: "power2.out", transformOrigin: "50% 50%" })
        .from("[data-heard]", { opacity: 0, y: 16, duration: 0.6 }, "+=0.1")
        .from("[data-answer]", { opacity: 0, y: 16, duration: 0.6 }, "+=0.35");
    }, root);
    return () => mm.revert();
  }, []);
  const bars = Array.from({ length: 56 }, (_, i) => Math.round((0.25 + Math.abs(Math.sin(i * 0.55) * Math.cos(i * 0.21)) * 0.75) * 100) / 100);
  return (
    <section ref={root} id="voice" aria-labelledby="voice-title" className="bg-fg text-canvas">
      <div className="mx-auto grid max-w-[1240px] gap-14 px-5 py-28 sm:px-10 lg:grid-cols-2 lg:items-center lg:py-36">
        <div>
          <h2 id="voice-title" className="text-[clamp(2.2rem,4.2vw,3.6rem)] font-bold leading-[1] tracking-[-0.03em]">Bol kar poochho.</h2>
          <p className="mt-5 max-w-lg text-lg leading-relaxed text-canvas/75">
            Tap once and speak, in Hindi, Hinglish or English. You see the words it heard and fix them if needed. Only then is
            the question asked, and the answer can be read out loud.
          </p>
          <p className="mt-6 max-w-lg text-sm leading-relaxed text-canvas/55">
            Speech is turned into words on your own server with a free model, then the recording is thrown away. Tested so
            far with synthetic voices only; real shop noise will make it work harder.
          </p>
        </div>
        <div className="rounded-[28px] border border-white/10 bg-white/[0.04] p-6" aria-hidden>
          <svg data-wave viewBox="0 0 560 80" className="h-16 w-full">
            {bars.map((h, i) => (
              <rect key={i} x={i * 10} y={(40 - h * 36).toFixed(2)} width="5" height={(h * 72).toFixed(2)} rx="2.5" fill="var(--color-haldi)" opacity={(0.55 + h * 0.45).toFixed(2)} />
            ))}
          </svg>
          <div data-heard className="mt-6 rounded-2xl bg-white/[0.06] p-4">
            <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-canvas/50">I heard</p>
            <p className="mt-1 font-deva text-xl">आज कितना बेचा?</p>
            <div className="mt-3 flex gap-2 text-sm">
              <span className="rounded-full bg-canvas px-4 py-1.5 font-semibold text-fg">Haan, poochho</span>
              <span className="rounded-full border border-white/20 px-4 py-1.5">Phir se boliye</span>
            </div>
          </div>
          <div data-answer className="mt-4 rounded-2xl bg-canvas p-4 text-fg">
            <p className="font-deva text-lg">आज ₹46,820 की बिक्री हुई, कल से 6% ज़्यादा।</p>
            <p className="mt-1 text-xs text-muted">From your sales file · 212 bills</p>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ trust and limits */

export function Trust() {
  const does = [
    "Reads the files you already have: sales exports, bill photos, your udhaar list",
    "Shows every number with the bills behind it",
    "Drafts reminders and orders for you to send",
    "Says how wrong its forecasts have been",
  ];
  const doesNot = [
    "Send messages, place orders or move money on its own",
    "Replace your billing software or file your GST",
    "Promise a forecast: it gives a range, and it can be wrong",
    "Share your data with anyone",
  ];
  return (
    <section id="trust" aria-labelledby="trust-title" className="mx-auto max-w-[1240px] px-5 py-28 sm:px-10 lg:py-36">
      <h2 id="trust-title" className="max-w-3xl text-[clamp(2.2rem,4.2vw,3.6rem)] font-bold leading-[1] tracking-[-0.03em]">It advises. You decide.</h2>
      <div className="mt-14 grid gap-12 md:grid-cols-2">
        {[
          ["It will", does, "text-mor", "✓"],
          ["It will not", doesNot, "text-sindoor", "✕"],
        ].map(([title, items, tone, mark]) => (
          <div key={title as string}>
            <h3 className="text-lg font-semibold">{title as string}</h3>
            <ul className="mt-5 divide-y divide-line border-y border-line">
              {(items as string[]).map((t) => (
                <li key={t} className="flex gap-4 py-4 text-[16px] leading-relaxed">
                  <span aria-hidden className={`font-mono ${tone as string}`}>{mark as string}</span>
                  {t}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ call to action and footer */

export function FinalCta() {
  return (
    <>
      <section aria-labelledby="cta-title" className="relative overflow-hidden bg-[#c98f1f]">
        <div aria-hidden className="absolute inset-0 opacity-[.18] [background:repeating-linear-gradient(90deg,rgba(60,30,0,.5)_0_2px,transparent_2px_9px),repeating-linear-gradient(0deg,rgba(255,240,200,.35)_0_1px,transparent_1px_7px)]" />
        <div className="relative mx-auto flex max-w-[1240px] flex-col items-start gap-8 px-5 py-24 sm:px-10 lg:flex-row lg:items-end lg:justify-between lg:py-32">
          <h2 id="cta-title" className="max-w-2xl text-[clamp(2.4rem,5vw,4.4rem)] font-extrabold leading-[0.98] tracking-[-0.035em] text-fg">
            See it with a sample shop. No sign-up.
          </h2>
          <Link href="/login" className="inline-flex h-14 shrink-0 items-center rounded-full bg-fg px-8 text-base font-semibold text-canvas transition-colors hover:bg-sindoor">
            Open the sample shop
          </Link>
        </div>
      </section>
      <footer className="border-t border-line">
        <div className="mx-auto flex max-w-[1240px] flex-col gap-4 px-5 py-10 text-sm text-muted sm:flex-row sm:items-center sm:justify-between sm:px-10">
          <Logo />
          <p>A work in progress, not yet tested with real shops. All figures on this page are demo data.</p>
          <p>© 2026 Vyapar AI</p>
        </div>
      </footer>
    </>
  );
}
