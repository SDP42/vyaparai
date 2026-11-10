"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { ApiError, api } from "@/lib/api";
import { useWorkspace } from "./AppContext";

type Answer = {
  intent: string; language: "en" | "hinglish" | "hi"; question: string; answer: string;
  rows: Record<string, string | number | null>[]; link: string | null; note: string | null;
  grounded: boolean; suggestions: string[]; period: { label: string } | null;
};
type Turn = { q: string; a?: Answer; error?: string };
type SR = { start: () => void; stop: () => void; lang: string; interimResults: boolean; onresult: ((e: { results: { 0: { 0: { transcript: string } } } }) => void) | null; onend: (() => void) | null; onerror: (() => void) | null };

const START = ["Sales last week", "Why did sales drop?", "What should I order?", "Any alerts?", "Top 5 products", "Next week forecast"];
const LANGS = { en: "English", hinglish: "Hinglish", hi: "हिन्दी" } as const;
const labelOf = (k: string) => k.replace(/_/g, " ");

export function AskPage() {
  const { workspace } = useWorkspace();
  const [turns, setTurns] = useState<Turn[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [listening, setListening] = useState(false);
  const [voice, setVoice] = useState(false);
  const end = useRef<HTMLDivElement>(null);
  const rec = useRef<SR | null>(null);

  useEffect(() => { // voice input uses the browser's own speech recognition when it exists; nothing is uploaded by us
    const w = window as unknown as { SpeechRecognition?: new () => SR; webkitSpeechRecognition?: new () => SR };
    setVoice(Boolean(w.SpeechRecognition ?? w.webkitSpeechRecognition));
  }, []);
  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [turns]);

  const ask = async (q: string) => {
    const question = q.trim();
    if (!question || busy) return;
    setBusy(true); setText("");
    setTurns((t) => [...t, { q: question }]);
    try {
      const a = await api<Answer>(`/workspaces/${workspace.id}/assistant/ask`, { method: "POST", body: JSON.stringify({ question }) });
      setTurns((t) => t.map((x, i) => (i === t.length - 1 ? { ...x, a } : x)));
    } catch (e) {
      setTurns((t) => t.map((x, i) => (i === t.length - 1 ? { ...x, error: e instanceof ApiError ? e.message : "Could not get an answer" } : x)));
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
    <div className="mx-auto flex max-w-3xl flex-col gap-4 p-4 sm:p-8">
      <header>
        <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">Ask</p>
        <h1 className="font-serif text-3xl tracking-tight sm:text-4xl">Ask your shop</h1>
        <p className="mt-1 text-sm text-fg/70">Ask in English, हिन्दी or Hinglish. Every number comes from your own data, with a link to where you can check it. If it cannot answer, it says so instead of guessing.</p>
      </header>

      <div className="min-h-[40dvh] space-y-4" aria-live="polite">
        {turns.length === 0 && (
          <div className="rounded-2xl border border-dashed border-line p-5">
            <p className="text-sm text-muted">Try one of these:</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {START.map((s) => <button key={s} type="button" onClick={() => ask(s)} className="rounded-full border border-line px-4 py-2 text-sm hover:bg-surface-2">{s}</button>)}
            </div>
          </div>
        )}
        {turns.map((t, i) => (
          <div key={i} className="space-y-2">
            <p className="ml-auto w-fit max-w-[85%] rounded-2xl rounded-br-sm bg-fg px-4 py-2 text-sm text-canvas">{t.q}</p>
            {!t.a && !t.error && <p className="text-sm text-muted">Looking at your numbers…</p>}
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
                <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted">
                  <span className="rounded-full border border-line px-2 py-0.5">{LANGS[t.a.language]}</span>
                  {t.a.period && <span className="rounded-full border border-line px-2 py-0.5">{t.a.period.label}</span>}
                  {t.a.grounded && <span className="rounded-full bg-mor/12 px-2 py-0.5 text-mor">From your data</span>}
                  {t.a.link && <Link href={t.a.link} className="underline underline-offset-4 hover:text-fg">Check it →</Link>}
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

      <form onSubmit={submit} className="sticky bottom-3 flex items-center gap-2 rounded-full border border-line bg-surface p-1.5 shadow-sm">
        <label htmlFor="ask" className="sr-only">Your question</label>
        <input id="ask" value={text} maxLength={300} onChange={(e) => setText(e.target.value)} placeholder="Ask about sales, stock, customers…" className="min-w-0 flex-1 bg-transparent px-4 py-2 text-sm outline-none" autoComplete="off" />
        {voice && (
          <button type="button" onClick={listen} aria-pressed={listening} aria-label={listening ? "Stop listening" : "Ask by voice"} className={`grid h-10 w-10 place-items-center rounded-full border border-line text-lg ${listening ? "animate-pulse bg-sindoor text-canvas" : "hover:bg-surface-2"}`}>🎤</button>
        )}
        <button type="submit" disabled={busy || !text.trim()} className="rounded-full bg-fg px-5 py-2 text-sm font-semibold text-canvas hover:bg-sindoor disabled:opacity-50">Ask</button>
      </form>
    </div>
  );
}
