"use client";

import Link from "next/link";
import { useLayoutEffect, useRef } from "react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { AlertScreen, OrderScreen, PhoneFrame, TodayScreen } from "./Screens";

gsap.registerPlugin(ScrollTrigger);

const motionOk = "(prefers-reduced-motion: no-preference)";

/* ------------------------------------------------------------------ hero */

export function Hero() {
  const root = useRef<HTMLElement>(null);
  useLayoutEffect(() => {
    let cleanup = () => {};
    const mm = gsap.matchMedia();
    mm.add(motionOk, () => {
      const locked = document.documentElement.dataset.gate === "locked";
      const tl = gsap.timeline({ defaults: { ease: "expo.out" }, paused: locked });
      tl.from("[data-word]", { yPercent: 115, duration: 1.15, stagger: 0.07 }, 0.05)
        .from("[data-fade]", { opacity: 0, y: 18, duration: 0.9, stagger: 0.08 }, 0.45)
        .from("[data-phone]", { y: 120, rotate: 4, opacity: 0, duration: 1.4 }, 0.25)
        .from("[data-chip]", { opacity: 0, scale: 0.85, y: 14, duration: 0.8, stagger: 0.12 }, 0.9);
      const onGate = (e: Event) => !(e as CustomEvent<{ locked: boolean }>).detail.locked && tl.play();
      window.addEventListener("vyapar:gate", onGate);
      cleanup = () => window.removeEventListener("vyapar:gate", onGate);
      // the phone lifts away a little as the page scrolls on
      gsap.to("[data-phone]", { yPercent: -8, ease: "none", scrollTrigger: { trigger: root.current, start: "top top", end: "bottom top", scrub: true } });
    });
    return () => {
      cleanup();
      mm.revert();
    };
  }, []);

  const words = ["Open", "the", "shutter", "knowing", "three", "things."];
  return (
    <section ref={root} id="top" aria-labelledby="hero-title" className="relative overflow-hidden">
      <div aria-hidden className="pointer-events-none absolute inset-0 bg-[radial-gradient(60%_70%_at_78%_38%,#fff5dc_0%,rgba(246,239,226,0)_70%)]" />
      <div className="relative mx-auto grid min-h-dvh max-w-[1240px] items-center gap-14 px-5 pb-20 pt-28 sm:px-10 lg:grid-cols-[1.15fr_0.85fr]">
        <div>
          <p data-fade className="text-sm font-medium text-fg/70">For kirana, garment, medical and general stores</p>
          <h1 id="hero-title" className="mt-5 text-[clamp(2.9rem,6.6vw,5.9rem)] font-extrabold leading-[0.95] tracking-[-0.035em]">
            {words.map((w) => (
              <span key={w} className="mr-[0.22em] inline-block overflow-hidden pb-[0.06em] align-top">
                <span data-word className="inline-block">{w}</span>
              </span>
            ))}
          </h1>
          <p data-fade className="mt-7 max-w-xl text-lg leading-relaxed text-fg/75">
            Yesterday&apos;s sales, who owes you money, and what to order today. Vyapar AI reads the sales file your billing app
            already makes, and answers in Hindi, Hinglish or English, typed or spoken.
          </p>
          <div data-fade className="mt-9 flex flex-wrap items-center gap-3">
            <Link href="/login" className="inline-flex h-12 items-center rounded-full bg-fg px-6 text-[15px] font-semibold text-canvas transition-colors hover:bg-sindoor">
              Try the sample shop
            </Link>
            <a href="#how" className="inline-flex h-12 items-center rounded-full px-5 text-[15px] font-semibold text-fg/80 underline decoration-line underline-offset-[6px] hover:text-fg">
              How it works
            </a>
          </div>
          <p data-fade className="mt-5 text-sm text-muted">No sign-up for the sample. Nothing is sent or ordered without you.</p>
        </div>
        <div className="relative">
          <div data-phone>
            <PhoneFrame>
              <TodayScreen />
            </PhoneFrame>
          </div>
          <span data-chip className="absolute left-[-10%] top-[52%] hidden rounded-2xl border border-line bg-surface px-3.5 py-2 text-[13px] shadow-[0_18px_40px_-20px_rgba(60,30,5,.45)] sm:block">
            <span className="block font-mono text-[10px] uppercase tracking-wider text-muted">From your sales file</span>
            Every figure links to its bills
          </span>
          <span data-chip className="absolute bottom-[14%] right-[-4%] hidden rounded-2xl border border-line bg-surface px-3.5 py-2 text-[13px] shadow-[0_18px_40px_-20px_rgba(60,30,5,.45)] sm:block">
            <span className="block font-mono text-[10px] uppercase tracking-wider text-muted">Bol kar poochho</span>
            <span className="font-deva">आज कितना बेचा?</span>
          </span>
        </div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ proof: only things you can check */

const FACTS = [
  ["Runs on free, open software", "No per-message or per-user AI bill. The code and models are permissively licensed."],
  ["Your data stays with you", "Voice is turned into words on your own server and thrown away. Nothing goes to a third party."],
  ["Hindi, Hinglish, English", "Ask in the words you use at the counter. Speak if you would rather not type."],
  ["It shows its working", "Every number links back to the bills behind it. If it cannot answer, it says so."],
];

export function Proof() {
  return (
    <section aria-label="What you can check" className="border-y border-line bg-surface/60">
      <dl className="mx-auto grid max-w-[1240px] gap-x-10 gap-y-8 px-5 py-14 sm:grid-cols-2 sm:px-10 lg:grid-cols-4">
        {FACTS.map(([t, d]) => (
          <div key={t}>
            <dt className="font-semibold">{t}</dt>
            <dd className="mt-1.5 text-[15px] leading-relaxed text-fg/70">{d}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

/* ------------------------------------------------------------------ how it works: the one pinned scene */

const STEPS = [
  {
    k: "Bring what you have",
    t: "Your billing app's sales file, a photo of a supplier bill, your udhaar book.",
    d: "Columns are matched for you. Bad rows are shown, not hidden. The same file twice is never counted twice.",
  },
  {
    k: "See three numbers",
    t: "What you sold, what is running out, and who owes you.",
    d: "Each figure has a definition and the bills behind it, so you can check it against your galla.",
  },
  {
    k: "Approve one action",
    t: "Order 20 bags of atta. Call Ramesh about ₹2,100. Raise ghee by ₹10.",
    d: "Suggestions come with a reason and a range. Nothing is ordered, sent or changed until you say so.",
  },
];

function FileRows() {
  const rows = [
    ["INV-2041", "12/11/2026", "Atta 5kg", "2", "590"],
    ["INV-2042", "12/11/2026", "Ghee 1L", "1", "615"],
    ["INV-2043", "12/11/2026", "Rice 5kg", "?", "–"],
    ["INV-2044", "12/11/2026", "Oil 5L", "3", "1,140"],
    ["INV-2045", "12/11/2026", "Sugar 1kg", "4", "172"],
  ];
  return (
    <div className="p-5 font-mono text-[12px]">
      <p className="mb-3 text-[10px] uppercase tracking-[0.16em] text-muted">sales_nov.csv · 12,408 rows</p>
      <table className="w-full">
        <tbody>
          {rows.map((r) => (
            <tr key={r[0]} className={`border-b border-line/70 ${r[3] === "?" ? "bg-sindoor/10 text-sindoor" : ""}`}>
              {r.map((c, i) => (
                <td key={i} className="py-1.5 pr-3">{c}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-3 text-[11px] text-sindoor">1 row needs a look: quantity missing</p>
    </div>
  );
}

function ApproveCard() {
  return (
    <div className="p-5">
      <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted">Next step · worth about ₹2,400 a week</p>
      <p className="mt-2 text-lg font-semibold leading-snug">Order 20 bags of Aashirvaad Atta 5kg before Friday.</p>
      <p className="mt-1.5 text-sm text-fg/70">3 days of stock left at the usual rate; the supplier needs 2 days.</p>
      <div className="mt-4 flex gap-2">
        <span className="rounded-full bg-fg px-4 py-2 text-sm font-semibold text-canvas">I will do this</span>
        <span className="rounded-full border border-line px-4 py-2 text-sm">Not now</span>
      </div>
    </div>
  );
}

export function HowItWorks() {
  const root = useRef<HTMLElement>(null);
  useLayoutEffect(() => {
    const mm = gsap.matchMedia();
    mm.add(`${motionOk} and (min-width: 1024px)`, () => {
      const panes = gsap.utils.toArray<HTMLElement>("[data-pane]");
      const texts = gsap.utils.toArray<HTMLElement>("[data-step]");
      gsap.set(panes.slice(1), { clipPath: "inset(100% 0% 0% 0% round 24px)" });
      gsap.set(texts.slice(1), { opacity: 0.25 });
      const tl = gsap.timeline({
        scrollTrigger: { trigger: root.current, start: "top top", end: "+=220%", pin: true, scrub: 0.6 },
      });
      panes.slice(1).forEach((p, i) => {
        tl.to(p, { clipPath: "inset(0% 0% 0% 0% round 24px)", duration: 1, ease: "power2.inOut" }, i * 1.2)
          .to(panes[i], { scale: 0.94, opacity: 0, duration: 0.8 }, i * 1.2 + 0.2)
          .to(texts[i], { opacity: 0.25, duration: 0.4 }, i * 1.2 + 0.3)
          .to(texts[i + 1], { opacity: 1, duration: 0.4 }, i * 1.2 + 0.3)
          .to("[data-progress]", { scaleY: (i + 2) / 3, duration: 1 }, i * 1.2);
      });
    });
    return () => mm.revert();
  }, []);

  return (
    <section ref={root} id="how" aria-labelledby="how-title" className="relative bg-canvas">
      <div className="mx-auto grid max-w-[1240px] gap-12 px-5 py-24 sm:px-10 lg:min-h-dvh lg:grid-cols-[0.9fr_1.1fr] lg:items-center lg:py-0">
        <div>
          <h2 id="how-title" className="text-[clamp(2.2rem,4.2vw,3.6rem)] font-bold leading-[1] tracking-[-0.03em]">
            From the file you already have to one thing worth doing.
          </h2>
          <div className="relative mt-10 pl-6">
            <span aria-hidden className="absolute bottom-0 left-0 top-0 w-px bg-line" />
            <span aria-hidden data-progress className="absolute left-0 top-0 h-full w-px origin-top scale-y-[0.34] bg-sindoor max-lg:hidden" />
            <ol className="space-y-8">
              {STEPS.map((s) => (
                <li key={s.k} data-step>
                  <p className="text-sm font-semibold text-sindoor">{s.k}</p>
                  <p className="mt-1 text-xl font-semibold leading-snug">{s.t}</p>
                  <p className="mt-1.5 max-w-md text-[15px] leading-relaxed text-fg/70">{s.d}</p>
                </li>
              ))}
            </ol>
          </div>
        </div>
        <div className="relative lg:h-[480px]" aria-hidden>
          {[<FileRows key="f" />, <OrderScreen key="o" />, <ApproveCard key="a" />].map((pane, i) => (
            <div
              key={i}
              data-pane
              className="mb-5 overflow-hidden rounded-3xl border border-line bg-surface shadow-[0_30px_70px_-35px_rgba(60,30,5,.5)] lg:absolute lg:inset-x-0 lg:top-1/2 lg:mb-0 lg:flex lg:h-[340px] lg:-translate-y-1/2 lg:flex-col lg:justify-center"
              style={{ zIndex: i + 1 }}
            >
              {pane}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export { AlertScreen };
