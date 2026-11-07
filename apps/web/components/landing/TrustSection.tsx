"use client";

import { motion, useReducedMotion } from "motion/react";
import { EASE, Eyebrow, SplitHeading } from "./ui";

const PILLARS = [
  {
    title: "Reproducible metrics",
    body: "Every number comes from one versioned metric registry and can be recalculated from the source rows.",
    tag: "metric:net_sales v1",
  },
  {
    title: "Traceable evidence",
    body: "Insights and Copilot answers link to the records, model versions and document passages behind them.",
    tag: "evidence_refs[3]",
  },
  {
    title: "Transparent assumptions",
    body: "Lead times, service levels and confidence intervals are shown and editable, never hidden inside a model.",
    tag: "assumes lead_time=9d",
  },
  {
    title: "Human-approved actions",
    body: "Agents can read and suggest. Purchases, messages and changes stay drafts until a person approves them.",
    tag: "status: proposed → approved",
  },
];

const CHAIN = ["Source rows", "Metric v1", "Figure ₹18.46L", "Evidence", "Assumptions", "Your approval"];

export function TrustSection() {
  const reduce = useReducedMotion();
  return (
    <section id="about" className="relative py-28 sm:py-36" aria-labelledby="trust-title">
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <div className="max-w-3xl">
          <Eyebrow>Trust &amp; explainability</Eyebrow>
          <SplitHeading
            id="trust-title"
            text="Intelligence you can check, question and approve."
            className="mt-4 text-[clamp(2rem,4.4vw,3.6rem)] font-semibold leading-[1] tracking-[-0.03em]"
            accent={["check,"]}
          />
        </div>

        {/* traceability chain with a travelling pulse */}
        <div className="relative mt-12 overflow-hidden rounded-[28px] border border-line bg-surface p-6 sm:p-8">
          <ol className="relative flex flex-wrap items-center gap-3 text-sm">
            {CHAIN.map((c, i) => (
              <li key={c} className="flex items-center gap-3">
                <span className={`rounded-full border px-4 py-2 ${i === CHAIN.length - 1 ? "border-brass/50 bg-brass/10 text-brass" : "border-line bg-canvas"}`}>{c}</span>
                {i < CHAIN.length - 1 && (
                  <span aria-hidden className="relative block h-px w-8 overflow-hidden bg-line-strong sm:w-12">
                    {!reduce && (
                      <motion.span
                        className="absolute inset-y-0 w-3 bg-violet"
                        animate={{ x: [-12, 48] }}
                        transition={{ duration: 1.4, repeat: Infinity, ease: "linear", delay: i * 0.25 }}
                      />
                    )}
                  </span>
                )}
              </li>
            ))}
          </ol>
        </div>

        <ul className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {PILLARS.map((p, i) => (
            <motion.li
              key={p.title}
              initial={reduce ? false : { opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-8% 0px" }}
              transition={{ duration: 0.8, ease: EASE, delay: i * 0.08 }}
              className="flex flex-col rounded-[24px] border border-line bg-surface p-6"
            >
              <span className="font-mono text-xs text-violet">0{i + 1}</span>
              <h3 className="mt-6 text-xl font-medium tracking-tight">{p.title}</h3>
              <p className="mt-2 flex-1 text-sm leading-relaxed text-muted">{p.body}</p>
              <span className="mt-6 w-fit rounded-full bg-surface-2 px-2.5 py-1 font-mono text-[10px] text-muted">{p.tag}</span>
            </motion.li>
          ))}
        </ul>
      </div>
    </section>
  );
}
