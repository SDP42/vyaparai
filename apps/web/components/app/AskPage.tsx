"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { ApiError, streamAnswer } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { useWorkspace } from "./AppContext";

type Answer = {
  intent: string; language: "en" | "hinglish" | "hi"; question: string; answer: string;
  rows: Record<string, string | number | null>[]; link: string | null; note: string | null;
  grounded: boolean; suggestions: string[]; period: { label: string } | null; follow_up?: boolean;
  context?: Record<string, unknown>; evidence: Evidence[]; steps: Step[];
};
type Step = { step: string; detail?: string; tool?: string; ms?: number; empty?: boolean };
type Evidence = { label: string; value: string; source: string };
type Turn = { q: string; a?: Answer; error?: string; steps: Step[]; text?: string; evidence?: Evidence[]; follow?: boolean };
type SR = { start: () => void; stop: () => void; lang: string; interimResults: boolean; onresult: ((e: { results: { 0: { 0: { transcript: string } } } }) => void) | null; onend: (() => void) | null; onerror: (() => void) | null };

const START = ["Sales last week", "Why did sales drop?", "What should I order?", "Any alerts?", "Top 5 products", "Next week forecast"];
const LANGS = { en: "English", hinglish: "Hinglish", hi: "हिन्दी" } as const;
const labelOf = (k: string) => k.replace(/_/g, " ");

export function AskPage() {
  const { workspace } = useWorkspace();
  const { t: tr } = useT();
  const [turns, setTurns] = useState<Turn[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [listening, setListening] = useState(false);
  const [voice, setVoice] = useState(false);
  const end = useRef<HTMLDivElement>(null);
  const ctxRef = useRef<Record<string, unknown> | null>(null);
  const rec = useRef<SR | null>(null);

  useEffect(() => { // voice input uses the browser's own speech recognition when it exists; nothing is uploaded by us
    const w = window as unknown as { SpeechRecognition?: new () => SR; webkitSpeechRecognition?: new () => SR };
    setVoice(Boolean(w.SpeechRecognition ?? w.webkitSpeechRecognition));
  }, []);
  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [turns]);

  const patch = (fn: (t: Turn) => Turn) => setTurns((ts) => ts.map((x, i) => (i === ts.length - 1 ? fn(x) : x)));
  const ask = async (q: string) => {
    const question = q.trim();
    if (!question || busy) return;
    setBusy(true); setText("");
    setTurns((t) => [...t, { q: question, steps: [] }]);
    try {
      await streamAnswer(`/workspaces/${workspace.id}/assistant/stream`, { question, context: ctxRef.current }, (event, data) => {
        if (event === "step") patch((t) => ({ ...t, steps: [...t.steps, data as Step] }));
        else if (event === "answer") patch((t) => ({ ...t, text: (data as { text: string }).text }));
        else if (event === "evidence") patch((t) => ({ ...t, evidence: data as Evidence[] }));
        else if (event === "done") { const a = data as Answer; ctxRef.current = a.context ?? null; patch((t) => ({ ...t, a, follow: a.follow_up })); }
      });
    } catch (e) {
      patch((t) => ({ ...t, error: e instanceof ApiError ? e.message : "Could not get an answer" }));
    } finally { setBusy(false); }
  };
  const submit = (e: FormEvent) => { e.preventDefault(); void ask(text); };

  const listen = () => {
    const w = window as unknown as { SpeechRecognition?: new () => SR; webkitSpeechRecognition?: new () => SR };
    const Ctor = w.SpeechRecognition ?? w.webkitSpeechRecognition;
    if (!Ctor) return;
    if (listening) { rec.current?.stop(); return; }
    const r = new Ctor();
    r.lang = "hi-IN"; // understands Hindi and Hinglish speech reasonably; English words pass through
    r.interimResults = false;
    r.onresult = (e) => { const t = e.results[0][0].transcript; setText(t); void ask(t); };
    r.onend = () => setListening(false);
    r.onerror = () => setListening(false);
    rec.current = r; setListening(true); r.start();
  };

  const last = turns.at(-1)?.a;
  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-4">
      <header>
        <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">Ask</p>
        <h1 className="font-serif text-3xl tracking-tight sm:text-4xl">{tr("ask.title")}</h1>
        <p className="mt-1 text-sm text-fg/70">{tr("ask.intro")}</p>
      </header>

      <div className="min-h-[40dvh] space-y-4" aria-live="polite">
        {turns.length === 0 && (
          <div className="rounded-2xl border border-dashed border-line p-5">
            <p className="text-sm text-muted">{tr("ask.try")}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {START.map((s) => <button key={s} type="button" onClick={() => ask(s)} className="rounded-full border border-line px-4 py-2 text-sm hover:bg-surface-2">{s}</button>)}
            </div>
          </div>
        )}
        {turns.map((t, i) => (
          <div key={i} className="space-y-2">
            <p className="ml-auto w-fit max-w-[85%] rounded-2xl rounded-br-sm bg-fg px-4 py-2 text-sm text-canvas">{t.q}</p>
            {!t.a && !t.error && <p className="text-sm text-muted">{tr("ask.looking")}</p>}
            {t.steps.length > 0 && (
              <ol aria-label="What the assistant did" className="flex flex-wrap items-center gap-x-1.5 gap-y-1 font-mono text-[10px] uppercase tracking-wider text-muted">
                {t.steps.map((s, k) => <li key={k} className="inline-flex items-center gap-1.5"><span className="rounded-full border border-line px-2 py-0.5">{s.step === "tool" ? `ran ${s.tool}${s.ms != null ? ` · ${s.ms} ms` : ""}` : s.step === "done" ? `done · ${s.ms} ms` : `understood · ${s.detail}`}</span>{k < t.steps.length - 1 && <span aria-hidden>→</span>}</li>)}
              </ol>
            )}
            {t.error && <p role="alert" className="rounded-2xl border border-sindoor/30 bg-sindoor/5 px-4 py-3 text-sm text-sindoor">{t.error}</p>}
            {t.a && (
              <div className="max-w-[92%] rounded-2xl rounded-bl-sm border border-line bg-surface px-4 py-3">
                <p className="text-[15px] leading-relaxed">{t.a.answer}</p>
                {t.a.note && <p className="mt-2 rounded-lg bg-haldi/20 px-3 py-2 text-sm">{t.a.note}</p>}
                {t.a.rows.length > 0 && (
                  <ul className="mt-3 divide-y divide-line rounded-xl border border-line bg-canvas text-sm">
                    {t.a.rows.map((r, j) => (
                      <li key={j} className="flex flex-wrap justify-between gap-x-4 gap-y-0.5 px-3 py-2">
                        {Object.entries(r).map(([k, v], c) => <span key={k} className={c === 0 ? "font-medium" : "text-muted"}>{c === 0 ? String(v) : `${labelOf(k)}: ${v ?? "–"}`}</span>)}
                      </li>
                    ))}
                  </ul>
                )}
                {t.a.evidence.length > 0 && (
                  <details className="mt-3 rounded-xl border border-line bg-canvas text-sm">
                    <summary className="cursor-pointer px-3 py-2 font-medium">{tr("ask.evidence")}</summary>
                    <dl className="divide-y divide-line border-t border-line">
                      {t.a.evidence.map((e, j) => (
                        <div key={j} className="grid gap-x-3 px-3 py-1.5 sm:grid-cols-[1fr_auto_1fr]">
                          <dt className="text-muted">{e.label}</dt><dd className="font-medium tabular-nums">{e.value}</dd><dd className="font-mono text-[11px] text-muted sm:text-right">{e.source}</dd>
                        </div>
                      ))}
                    </dl>
                  </details>
                )}
                <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted">
                  {t.follow && <span className="rounded-full border border-line px-2 py-0.5">{tr("ask.follow")}</span>}
                  <span className="rounded-full border border-line px-2 py-0.5">{LANGS[t.a.language]}</span>
                  {t.a.period && <span className="rounded-full border border-line px-2 py-0.5">{t.a.period.label}</span>}
                  {t.a.grounded && <span className="rounded-full bg-mor/12 px-2 py-0.5 text-mor">{tr("ask.fromData")}</span>}
                  {t.a.link && <Link href={t.a.link} className="underline underline-offset-4 hover:text-fg">{tr("ask.check")}</Link>}
                </div>
              </div>
            )}
          </div>
        ))}
        <div ref={end} />
      </div>

      {last && (
        <div className="flex flex-wrap gap-2">
          {last.suggestions.map((s) => <button key={s} type="button" disabled={busy} onClick={() => ask(s)} className="rounded-full border border-line px-3 py-1.5 text-xs hover:bg-surface-2 disabled:opacity-50">{s}</button>)}
        </div>
      )}

      <form onSubmit={submit} className="sticky bottom-20 flex md:bottom-3 items-center gap-2 rounded-full border border-line bg-surface p-1.5 shadow-sm">
        <label htmlFor="ask" className="sr-only">Your question</label>
        <input id="ask" value={text} maxLength={300} onChange={(e) => setText(e.target.value)} placeholder={tr("ask.placeholder")} className="min-w-0 flex-1 bg-transparent px-4 py-2 text-sm outline-none" autoComplete="off" />
        {voice && (
          <button type="button" onClick={listen} aria-pressed={listening} aria-label={listening ? "Stop listening" : "Ask by voice"} className={`grid h-10 w-10 place-items-center rounded-full border border-line text-lg ${listening ? "animate-pulse bg-sindoor text-canvas" : "hover:bg-surface-2"}`}>🎤</button>
        )}
        <button type="submit" disabled={busy || !text.trim()} className="rounded-full bg-fg px-5 py-2 text-sm font-semibold text-canvas hover:bg-sindoor disabled:opacity-50">{tr("ask.send")}</button>
      </form>
    </div>
  );
}
