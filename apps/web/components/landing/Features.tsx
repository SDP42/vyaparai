"use client";

import { useLayoutEffect, useRef, type PointerEvent } from "react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger);

const FEATURES = [
  {
    tag: "Numbers",
    title: "Command center",
    body: "Net sales, margin, orders and average bill, each with its definition, period and when the data was last updated.",
    span: "sm:col-span-2 lg:col-span-4",
    art: <BarsArt />,
  },
  {
    tag: "Forecast",
    title: "Festival-aware forecasts",
    body: "Starts from last week's pattern, adds Diwali and wedding season only when it helps, and shows how wrong it has been.",
    span: "lg:col-span-2",
    art: <WaveArt />,
  },
  {
    tag: "Udhaar",
    title: "Who owes you, and since when",
    body: "Payments settle the oldest udhaar first. You see whom to call first, with a reminder you send yourself.",
    span: "lg:col-span-2",
    art: <UdhaarArt />,
  },
  {
    tag: "Stock",
    title: "What to order before it runs out",
    body: "Days of cover from the forecast, and the cash sitting in stock that has stopped moving.",
    span: "lg:col-span-2",
    art: <StockArt />,
  },
  {
    tag: "Reviews",
    title: "Hinglish reviews, read properly",
    body: "“delivery late tha but quality ekdum mast” becomes delivery −, quality +, with the phrase behind each.",
    span: "lg:col-span-2",
    art: <QuoteArt />,
  },
  {
    tag: "Voice",
    title: "Ask by speaking",
    body: "Say it in Hindi, Hinglish or English. You check the words, then the answer comes back, and can be read out loud.",
    span: "sm:col-span-2 lg:col-span-3",
    art: <VoiceArt />,
  },
  {
    tag: "Your team",
    title: "Everyone sees their own shop",
    body: "The counter does not see profit and the accountant cannot change anything. The assistant answers only the questions of the job.",
    span: "sm:col-span-2 lg:col-span-3",
    art: <JobsArt />,
  },
  {
    tag: "Bills",
    title: "Supplier bills, read from a photo",
    body: "A person checks every line before it counts. Then you see when a supplier quietly raised a price.",
    span: "lg:col-span-2",
    art: <BillArt />,
  },
  {
    tag: "Ask",
    title: "Answers that show their working",
    body: "Every number comes from your own data and links back to where you can check it. If it cannot answer, it says so.",
    span: "sm:col-span-2 lg:col-span-4",
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
        <p className="max-w-sm text-fg/60">
          Every figure shows the numbers behind it, and every page says what it does not know.
        </p>
      </div>
      <div className="grid gap-4 [perspective:1200px] sm:grid-cols-2 lg:grid-cols-6">
        {FEATURES.map((f) => (
          <article
            key={f.title}
            data-card
            onPointerMove={onMove}
            className={`group relative overflow-hidden rounded-3xl border border-line bg-surface p-7 transition-colors duration-500 hover:border-haldi/40 ${f.span}`}
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
              <div className="my-8 flex min-h-28 flex-1 items-center">{f.art}</div>
              <h3 className="text-2xl font-bold tracking-tight">{f.title}</h3>
              <p className="mt-2 max-w-xl text-fg/60">{f.body}</p>
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
          className="flex-1 origin-bottom rounded-t-sm bg-fg/15 transition-all duration-500 group-hover:bg-sindoor/80"
          style={{ height: `${v}%`, transitionDelay: `${i * 25}ms` }}
        />
      ))}
    </div>
  );
}

function WaveArt() {
  return (
    <svg viewBox="0 0 200 80" className="w-full" aria-hidden>
      <path d="M0,60 C30,55 45,50 70,48 S110,15 125,12 S160,45 200,40" fill="none" stroke="var(--color-fg)" strokeOpacity=".3" strokeWidth="2" />
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
            i % 7 === 0 ? "bg-sindoor" : i % 3 === 0 ? "bg-mor" : "bg-fg/20"
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
        ["Ghee 1L", 68, "text-haldi-deep"],
        ["Atta 5kg", 91, "text-mor"],
      ].map(([n, v, c]) => (
        <div key={n as string}>
          <div className="mb-1 flex justify-between text-fg/60">
            <span>{n}</span>
            <span className={c as string}>{v}% cover</span>
          </div>
          <div className="h-1.5 rounded-full bg-line">
            <div className="h-full rounded-full bg-fg/50 transition-all duration-700 group-hover:bg-sindoor" style={{ width: `${v}%` }} />
          </div>
        </div>
      ))}
    </div>
  );
}

function QuoteArt() {
  return (
    <p className="font-serif text-2xl italic leading-snug text-fg/80" aria-hidden>
      “delivery <span className="text-sindoor underline decoration-wavy underline-offset-4">late tha</span> but quality{" "}
      <span className="text-mor underline decoration-wavy underline-offset-4">ekdum mast</span>”
    </p>
  );
}

function CopilotArt() {
  return (
    <div className="grid w-full gap-3 md:grid-cols-[1fr_1.4fr]" aria-hidden>
      <div className="self-start rounded-2xl rounded-br-sm bg-fg px-4 py-3 text-sm text-canvas">
        Why did sales dip last Tuesday?
      </div>
      <div className="rounded-2xl rounded-tl-sm border border-line bg-canvas p-4 text-sm text-fg/80">
        Net sales were <b className="text-fg">₹41,200</b> (18% below the last four Tuesdays). Most of the drop came from{" "}
        <b className="text-fg">Staples</b>: fewer bills, not lower prices. That is what the numbers show; they cannot say why customers stayed away.
        <div className="mt-3 flex flex-wrap gap-2 font-mono text-[10px]">
          <span className="rounded border border-line px-2 py-0.5 text-haldi-deep">Net sales · 4 Tuesdays</span>
          <span className="rounded border border-line px-2 py-0.5 text-haldi-deep">Volume, price, mix</span>
        </div>
      </div>
    </div>
  );
}

function UdhaarArt() {
  const rows = [
    ["0–30 days", "₹38,400", 42],
    ["31–60 days", "₹21,900", 24],
    ["Over 60", "₹31,150", 34],
  ] as const;
  return (
    <div className="w-full space-y-2.5 font-mono text-[11px]" aria-hidden>
      {rows.map(([label, amt, w], i) => (
        <div key={label}>
          <div className="mb-1 flex justify-between text-fg/60">
            <span>{label}</span>
            <span className={i === 2 ? "text-sindoor" : "text-fg/80"}>{amt}</span>
          </div>
          <div className="h-1.5 rounded-full bg-line">
            <div className={`h-full rounded-full transition-all duration-700 ${i === 2 ? "bg-sindoor/80" : "bg-fg/40"} group-hover:bg-sindoor`} style={{ width: `${w * 2}%` }} />
          </div>
        </div>
      ))}
    </div>
  );
}

function VoiceArt() {
  return (
    <div className="flex w-full items-center gap-4" aria-hidden>
      <span className="grid h-14 w-14 shrink-0 place-items-center rounded-full bg-fg text-canvas transition-colors group-hover:bg-sindoor">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="9" y="3" width="6" height="12" rx="3" />
          <path d="M5 11a7 7 0 0 0 14 0M12 18v3" />
        </svg>
      </span>
      <div className="min-w-0 space-y-2 text-sm">
        <p className="font-deva text-lg leading-snug">आज की बिक्री कितनी हुई?</p>
        <p className="rounded-xl border border-line bg-canvas px-3 py-2 text-fg/75">Aaj ₹46,820 hui, kal se 6% zyada.</p>
      </div>
    </div>
  );
}

function JobsArt() {
  const jobs = ["Owner", "Operations", "Analyst", "Accountant", "Counter"];
  return (
    <div className="flex flex-wrap gap-2" aria-hidden>
      {jobs.map((j, i) => (
        <span key={j} className={`rounded-full border px-3.5 py-1.5 text-sm ${i === 4 ? "border-sindoor/40 bg-sindoor/10 text-sindoor" : "border-line bg-canvas text-fg/75"}`}>
          {j}
        </span>
      ))}
    </div>
  );
}

function BillArt() {
  return (
    <div className="w-full space-y-1.5 font-mono text-[11px]" aria-hidden>
      {[
        ["Atta 5kg × 20", "₹5,160"],
        ["Sugar 1kg × 40", "₹1,720"],
        ["Ghee 1L × 12", "₹7,080"],
      ].map(([n, v], i) => (
        <div key={n} className={`flex justify-between rounded-md px-2 py-1 ${i === 2 ? "bg-haldi/20 text-fg" : "bg-canvas text-fg/70"}`}>
          <span>{n}</span>
          <span>{v}</span>
        </div>
      ))}
      <p className="pt-1 text-[10px] text-muted">Ghee: ₹590 → ₹615 since March</p>
    </div>
  );
}
