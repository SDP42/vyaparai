"use client";

import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion, useInView, useReducedMotion } from "motion/react";
import { DRIVERS, RECOMMENDATIONS } from "@/lib/landing-data";
import { formatINRCompact } from "@/lib/format";
import { EASE, Eyebrow, SplitHeading } from "./ui";

const QUESTION = "Why did my revenue decline this month?";
const ANSWER =
  "Net sales fell 6.2% to ₹18.46L in October. Most of the drop is volume: 333 fewer orders, concentrated in Staples. Wheat atta 5 kg and Toor dal 1 kg were out of stock for 6–9 days. Average order value rose 3.0%, which offset part of it.";
const TOOLS = [
  { name: "get_sales_summary", args: "period=Oct 2026", ms: 84 },
  { name: "compare_periods", args: "Sep → Oct, by driver", ms: 61 },
  { name: "top_products", args: "sort=delta, limit=5", ms: 43 },
  { name: "inventory_events", args: "type=stock_out", ms: 38 },
];

type Stage = 0 | 1 | 2 | 3 | 4; // 0 idle · 1 question · 2 tools · 3 answer · 4 actions

export function CopilotPreviewSection() {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: "-20% 0px" });
  const reduce = useReducedMotion();
  const [stage, setStage] = useState<Stage>(0);
  const [typed, setTyped] = useState("");
  const [toolsDone, setToolsDone] = useState(0);
  const [answer, setAnswer] = useState("");
  const [decisions, setDecisions] = useState<Record<number, "approved" | "dismissed">>({});
  const [run, setRun] = useState(0);

  useEffect(() => {
    if (!inView) return;
    if (reduce) {
      setTyped(QUESTION);
      setToolsDone(TOOLS.length);
      setAnswer(ANSWER);
      setStage(4);
      return;
    }
    let cancelled = false;
    const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));
    (async () => {
      setStage(1);
      setTyped("");
      setToolsDone(0);
      setAnswer("");
      setDecisions({});
      for (let i = 1; i <= QUESTION.length; i++) {
        if (cancelled) return;
        setTyped(QUESTION.slice(0, i));
        await wait(28);
      }
      await wait(350);
      setStage(2);
      for (let i = 1; i <= TOOLS.length; i++) {
        await wait(420);
        if (cancelled) return;
        setToolsDone(i);
      }
      await wait(300);
      setStage(3);
      const words = ANSWER.split(" ");
      for (let i = 1; i <= words.length; i++) {
        if (cancelled) return;
        setAnswer(words.slice(0, i).join(" "));
        await wait(38);
      }
      await wait(250);
      setStage(4);
    })();
    return () => {
      cancelled = true;
    };
  }, [inView, reduce, run]);

  return (
    <section className="relative py-28 sm:py-36" aria-labelledby="copilot-title">
      <div className="mx-auto grid max-w-7xl gap-12 px-5 sm:px-8 lg:grid-cols-[0.8fr_1.2fr]">
        <div className="lg:sticky lg:top-28 lg:self-start">
          <Eyebrow>Vyapar Copilot</Eyebrow>
          <SplitHeading
            id="copilot-title"
            text="Ask why. Get evidence, not guesses."
            className="mt-4 text-[clamp(2rem,4.4vw,3.6rem)] font-semibold leading-[1] tracking-[-0.03em]"
            accent={["evidence,"]}
          />
          <p className="mt-5 max-w-md text-muted">
            The Copilot routes your question to approved, read-only tools. Figures come from the metric layer, never
            from a language model&apos;s arithmetic. Each answer shows its period, its sources and its caveats.
          </p>
          <ul className="mt-6 space-y-2 text-sm text-muted">
            <li>✓ Numbers from SQL metrics, not LLM math</li>
            <li>✓ Every claim linked to evidence</li>
            <li>✓ Actions stay drafts until you approve</li>
          </ul>
          <p className="mt-6 inline-block rounded-full border border-line bg-surface px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.14em] text-muted">
            Simulated preview · not connected to a live AI
          </p>
        </div>

        <div ref={ref} className="rounded-[28px] border border-line bg-surface p-4 shadow-[0_50px_100px_-60px_rgba(11,16,32,0.45)] sm:p-6" aria-live="polite">
          <div className="flex items-center justify-between border-b border-line pb-3">
            <p className="flex items-center gap-2 text-sm font-medium">
              <span aria-hidden className="grid h-6 w-6 place-items-center rounded-lg bg-gradient-to-br from-violet to-blue text-[11px] text-white">✦</span>
              Vyapar Copilot
            </p>
            <button type="button" onClick={() => setRun((r) => r + 1)} className="rounded-full border border-line px-3 py-1 text-xs text-muted hover:text-fg">
              ↻ Replay
            </button>
          </div>

          <div className="min-h-[520px] space-y-4 pt-5">
            {stage >= 1 && (
              <div className="ml-auto w-fit max-w-[85%] rounded-2xl rounded-br-sm bg-fg px-4 py-2.5 text-sm text-white">
                {typed}
                {stage === 1 && <span aria-hidden className="ml-0.5 inline-block h-4 w-px translate-y-0.5 animate-[caret_1s_step-end_infinite] bg-white" />}
              </div>
            )}

            {stage >= 2 && (
              <motion.ol initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-1.5 rounded-2xl border border-line bg-canvas p-3 font-mono text-[11px]">
                {TOOLS.map((t, i) => (
                  <li key={t.name} className={`flex items-center gap-2 transition-opacity ${i < toolsDone ? "opacity-100" : "opacity-40"}`}>
                    <span className={i < toolsDone ? "text-success" : "text-muted"}>{i < toolsDone ? "✓" : "○"}</span>
                    <span className="text-fg">{t.name}</span>
                    <span className="truncate text-muted">({t.args})</span>
                    {i < toolsDone && <span className="ml-auto text-muted">{t.ms}ms</span>}
                  </li>
                ))}
              </motion.ol>
            )}

            {stage >= 3 && (
              <div className="max-w-[95%] rounded-2xl rounded-bl-sm border border-line bg-canvas p-4 text-sm leading-relaxed">
                <p>{answer}</p>
                <AnimatePresence>
                  {stage >= 4 && (
                    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease: EASE }}>
                      <div className="mt-4 grid grid-cols-3 gap-2">
                        {DRIVERS.map((d) => (
                          <div key={d.label} className="rounded-xl border border-line bg-surface p-2.5">
                            <p className="text-[11px] text-muted">{d.label}</p>
                            <p className={`font-mono text-sm font-medium ${d.value < 0 ? "text-danger" : "text-success"}`}>
                              {d.value < 0 ? "−" : "+"}
                              {formatINRCompact(Math.abs(d.value))}
                            </p>
                          </div>
                        ))}
                      </div>
                      <div className="mt-3 flex flex-wrap gap-1.5 font-mono text-[10px]">
                        {["metric:net_sales v1 · Oct", "drivers: volume/price/mix", "inventory: 2 stock-outs"].map((e, i) => (
                          <span key={e} className="rounded-full border border-line bg-surface px-2 py-0.5 text-blue-soft">
                            [{i + 1}] {e}
                          </span>
                        ))}
                      </div>
                      <p className="mt-3 text-xs text-muted">Caveat: returns data covers 92% of orders; external factors are not measured.</p>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            )}

            <AnimatePresence>
              {stage >= 4 && (
                <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.15, ease: EASE }}>
                  <p className="mb-2 font-mono text-[10px] uppercase tracking-[0.16em] text-muted">Recommended actions</p>
                  <ul className="space-y-2">
                    {RECOMMENDATIONS.map((r, i) => (
                      <li key={r.title} className="rounded-2xl border border-line bg-canvas p-4">
                        <div className="flex flex-wrap items-start justify-between gap-2">
                          <p className="text-sm font-medium">{r.title}</p>
                          <span className="font-mono text-[10px] text-muted">{r.confidence} confidence</span>
                        </div>
                        <p className="mt-1 text-xs text-muted">
                          {r.impact} · {r.evidence.join(" · ")}
                        </p>
                        <div className="mt-3 flex items-center gap-2">
                          {decisions[i] ? (
                            <span role="status" className={`text-xs font-medium ${decisions[i] === "approved" ? "text-success" : "text-muted"}`}>
                              {decisions[i] === "approved" ? "✓ Approved as draft" : "Dismissed"}
                            </span>
                          ) : (
                            <>
                              <button type="button" onClick={() => setDecisions((d) => ({ ...d, [i]: "approved" }))} className="rounded-full bg-fg px-3.5 py-1.5 text-xs font-medium text-white hover:bg-violet">
                                Approve draft
                              </button>
                              <button type="button" onClick={() => setDecisions((d) => ({ ...d, [i]: "dismissed" }))} className="rounded-full border border-line px-3.5 py-1.5 text-xs text-muted hover:text-fg">
                                Dismiss
                              </button>
                            </>
                          )}
                        </div>
                      </li>
                    ))}
                  </ul>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </section>
  );
}
