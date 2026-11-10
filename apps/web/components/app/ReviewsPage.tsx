"use client";

import { useRef, useState } from "react";
import { ApiError, api, download } from "@/lib/api";
import { useApi } from "@/lib/analytics";
import { useWorkspace } from "./AppContext";
import { Card, EmptyNote, ErrorNote, Skeleton } from "./analytics/parts";

type Label = "positive" | "neutral" | "negative";
type Theme = { theme: string; polarity: number; snippet: string };
type ThemeRow = { theme: string; label: string; mentions: number; negative: number; negative_pct: number; mean_polarity: number; prior_mentions: number; prior_negative_pct: number | null };
type Summary = {
  total: number; window_days: number; in_window: number;
  labels: Record<Label, number>; mean_sentiment: number | null; mean_rating: number | null;
  languages: Record<string, number>; themes: ThemeRow[];
  weekly: { week: string; reviews: number; mean_sentiment: number }[];
  unscored: number; mismatch: number;
};
type Item = { id: string; review_date: string | null; rating: number | null; text: string; language: string; sentiment: number; label: Label; product: string | null; source: string; themes: Theme[] };
type Feed = { items: Item[]; total: number; limit: number; offset: number };
type ProductRow = { product_id: string; product: string; reviews: number; mean_sentiment: number; negative_pct: number; top_problem: string | null };
type Tried = { language: string; sentiment: number; label: Label; themes: Theme[]; method: string };

const TONE: Record<Label, { bar: string; chip: string; word: string }> = {
  positive: { bar: "bg-mor", chip: "bg-mor/12 text-mor", word: "Positive" },
  neutral: { bar: "bg-line", chip: "bg-surface-2 text-muted", word: "Neutral" },
  negative: { bar: "bg-sindoor", chip: "bg-sindoor/10 text-sindoor", word: "Negative" },
};
const LANG: Record<string, string> = { en: "English", hi: "हिन्दी", hinglish: "Hinglish" };
const THEME_LABEL: Record<string, string> = { delivery: "Delivery", quality: "Quality", price: "Price", packaging: "Packaging", service: "Service", freshness: "Freshness", availability: "Stock" };
const pct = (n: number, d: number) => (d ? Math.round((100 * n) / d) : 0);

function Spark({ pts }: { pts: number[] }) {
  if (pts.length < 2) return <p className="text-xs text-muted">Not enough dated reviews for a trend yet.</p>;
  const w = 320, h = 64, step = w / (pts.length - 1);
  const y = (v: number) => h / 2 - (v * (h / 2 - 6));
  const d = pts.map((v, i) => `${i ? "L" : "M"}${(i * step).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="h-16 w-full" role="img" aria-label={`Weekly average sentiment, from ${pts[0].toFixed(2)} to ${pts[pts.length - 1].toFixed(2)}`}>
      <line x1="0" x2={w} y1={h / 2} y2={h / 2} className="stroke-line" strokeDasharray="3 4" />
      <path d={d} fill="none" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="stroke-fg" />
      {pts.map((v, i) => <circle key={i} cx={i * step} cy={y(v)} r="3" className={v >= 0 ? "fill-mor" : "fill-sindoor"} />)}
    </svg>
  );
}

function Stars({ n }: { n: number | null }) {
  if (n == null) return null;
  return <span aria-label={`${n} out of 5 stars`} className="font-mono text-xs tracking-tight text-haldi">{"★".repeat(n)}<span className="text-line">{"★".repeat(5 - n)}</span></span>;
}

function ThemeChips({ themes }: { themes: Theme[] }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {themes.map((t) => {
        const l: Label = t.polarity >= 0.15 ? "positive" : t.polarity <= -0.15 ? "negative" : "neutral";
        return (
          <span key={t.theme} title={`“${t.snippet}”`} className={`rounded-full px-2.5 py-0.5 text-[11px] ${TONE[l].chip}`}>
            {l === "positive" ? "▲" : l === "negative" ? "▼" : "■"} {THEME_LABEL[t.theme] ?? t.theme}
          </span>
        );
      })}
    </div>
  );
}

function TryBox({ base }: { base: string }) {
  const [text, setText] = useState("Product accha hai but delivery bahut late aaya");
  const [res, setRes] = useState<Tried | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const run = async () => {
    setBusy(true); setErr(null);
    try { setRes(await api<Tried>(`${base}/try`, { method: "POST", body: JSON.stringify({ text }) })); }
    catch (e) { setErr(e instanceof ApiError ? e.message : "Could not read that"); }
    finally { setBusy(false); }
  };
  return (
    <Card title="See how a review is read" subtitle="Type or paste one, in English, हिन्दी or Hinglish. Nothing is saved.">
      <label htmlFor="try-text" className="sr-only">Review text</label>
      <textarea id="try-text" value={text} maxLength={2000} rows={2} onChange={(e) => setText(e.target.value)} className="w-full rounded-xl border border-line bg-canvas p-3 text-sm" />
      <div className="mt-2 flex flex-wrap items-center gap-3">
        <button type="button" onClick={run} disabled={busy || !text.trim()} className="rounded-full bg-fg px-4 py-2 text-sm font-semibold text-canvas hover:bg-sindoor disabled:opacity-60">{busy ? "Reading…" : "Read it"}</button>
        {err && <span className="text-sm text-sindoor">{err}</span>}
      </div>
      {res && (
        <div className="mt-4 rounded-xl bg-canvas p-4" role="status">
          <div className="flex flex-wrap items-center gap-2">
            <span className={`rounded-full px-3 py-1 text-sm font-semibold ${TONE[res.label].chip}`}>{TONE[res.label].word} {res.sentiment > 0 ? "+" : ""}{res.sentiment.toFixed(2)}</span>
            <span className="rounded-full border border-line px-2.5 py-0.5 text-xs">{LANG[res.language] ?? res.language}</span>
          </div>
          {res.themes.length > 0 ? (
            <ul className="mt-3 space-y-1.5 text-sm">
              {res.themes.map((t) => (
                <li key={t.theme}><b>{THEME_LABEL[t.theme] ?? t.theme}</b> <span className="text-muted">({t.polarity > 0 ? "+" : ""}{t.polarity.toFixed(2)})</span>: “{t.snippet}”</li>
              ))}
            </ul>
          ) : <p className="mt-3 text-sm text-muted">No theme words found in this one.</p>}
          {res.sentiment === 0 && <p className="mt-2 text-xs text-muted">No opinion words were recognised, so this reads as neutral. That is a gap in the word lists, not a verdict.</p>}
        </div>
      )}
    </Card>
  );
}

function ImportCard({ base, onDone }: { base: string; onDone: () => void }) {
  const ref = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [res, setRes] = useState<{ added: number; duplicates: number; empty: number; languages: Record<string, number> } | null>(null);
  const upload = async (file: File) => {
    setBusy(true); setErr(null); setRes(null);
    const fd = new FormData(); fd.append("file", file);
    try { setRes(await api(`${base}/import`, { method: "POST", body: fd })); onDone(); }
    catch (e) { setErr(e instanceof ApiError ? e.message : "Could not read the file"); }
    finally { setBusy(false); if (ref.current) ref.current.value = ""; }
  };
  return (
    <Card title="Add reviews" subtitle="A CSV with a Review column. Optional: Date, Product (SKU or name), Rating (1-5), Source. Export from Google Business, a marketplace, or type them in a sheet.">
      <div className="flex flex-wrap items-center gap-2">
        <input ref={ref} type="file" accept=".csv,text/csv" className="hidden" onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])} />
        <button type="button" disabled={busy} onClick={() => ref.current?.click()} className="rounded-full bg-fg px-4 py-2 text-sm font-semibold text-canvas hover:bg-sindoor disabled:opacity-60">{busy ? "Reading…" : "Upload reviews"}</button>
        <button type="button" onClick={() => download(`${base}/template.csv`, "reviews-template.csv")} className="rounded-full border border-line px-4 py-2 text-sm hover:bg-surface-2">Download a template</button>
      </div>
      {err && <p role="alert" className="mt-2 text-sm text-sindoor">{err}</p>}
      {res && <p role="status" className="mt-3 text-sm"><b>{res.added}</b> new reviews read{res.duplicates ? `, ${res.duplicates} already had` : ""}{res.empty ? `, ${res.empty} blank rows skipped` : ""}.</p>}
    </Card>
  );
}

export function ReviewsPage() {
  const { workspace, canImport } = useWorkspace();
  const base = `/workspaces/${workspace.id}/reviews`;
  const init = typeof window !== "undefined" ? new URLSearchParams(window.location.search) : new URLSearchParams();
  const [version, setVersion] = useState(0);
  const [label, setLabel] = useState<Label | "">((init.get("label") as Label) || "");
  const [theme, setTheme] = useState(init.get("theme") ?? "");
  const [lang, setLang] = useState("");
  const [q, setQ] = useState("");
  const [page, setPage] = useState(0);
  const sum = useApi<Summary>(`${base}/summary?days=90`, [version]);
  const prods = useApi<ProductRow[]>(`${base}/products`, [version]);
  const qs = new URLSearchParams({ limit: "10", offset: String(page * 10) });
  if (label) qs.set("label", label);
  if (theme) qs.set("theme", theme);
  if (lang) qs.set("language", lang);
  if (q.trim()) qs.set("q", q.trim());
  const feed = useApi<Feed>(`${base}?${qs}`, [version]);
  const s = sum.data;
  const empty = s && s.total === 0;
  const reset = (fn: () => void) => { fn(); setPage(0); };

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-4 sm:p-8">
      <header>
        <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">Reviews</p>
        <h1 className="font-serif text-3xl tracking-tight sm:text-4xl">What customers are saying</h1>
        <p className="mt-1 max-w-2xl text-sm text-fg/70">Every review is read for language, mood and what it is about. Each claim shows the words it came from, so you can check it.</p>
      </header>

      {sum.error && <ErrorNote message={sum.error} onRetry={() => setVersion((v) => v + 1)} />}
      {!s && sum.loading && <Skeleton className="h-48" />}

      {canImport && <ImportCard base={base} onDone={() => setVersion((v) => v + 1)} />}

      {empty && <EmptyNote>No reviews yet. Upload a file above, or try a sentence in the box below to see how reading works.</EmptyNote>}

      {s && !empty && (
        <>
          <section aria-label="Overall mood" className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
            <div className="rounded-2xl border border-line bg-surface p-5">
              <div className="flex flex-wrap items-end justify-between gap-2">
                <div>
                  <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted">Last {s.window_days} days · {s.in_window} reviews</p>
                  <p className="mt-1 text-5xl font-bold tracking-tight">{pct(s.labels.positive, s.in_window)}<span className="text-2xl text-muted">% positive</span></p>
                </div>
                {s.mean_rating != null && <p className="text-right text-sm text-muted">Average stars<br /><b className="text-2xl text-fg">{s.mean_rating.toFixed(1)}</b></p>}
              </div>
              <div className="mt-4 flex h-4 overflow-hidden rounded-full bg-surface-2" role="img" aria-label={`${s.labels.positive} positive, ${s.labels.neutral} neutral, ${s.labels.negative} negative`}>
                {(["positive", "neutral", "negative"] as const).map((k) => <div key={k} className={`${TONE[k].bar} transition-[width] duration-700`} style={{ width: `${pct(s.labels[k], s.in_window)}%` }} />)}
              </div>
              <div className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted">
                {(["positive", "neutral", "negative"] as const).map((k) => <span key={k}>{TONE[k].word}: <b className="text-fg">{s.labels[k]}</b></span>)}
                {Object.entries(s.languages).map(([k, v]) => <span key={k}>{LANG[k] ?? k}: <b className="text-fg">{v}</b></span>)}
              </div>
            </div>
            <div className="rounded-2xl border border-line bg-surface p-5">
              <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted">Mood by week</p>
              <Spark pts={s.weekly.map((w) => w.mean_sentiment)} />
              <p className="mt-1 text-xs text-muted">Above the dotted line is positive.</p>
            </div>
          </section>

          <section aria-label="Themes">
            <h2 className="mb-3 font-semibold">What they talk about</h2>
            <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {s.themes.map((t) => {
                const delta = t.prior_negative_pct == null ? null : t.negative_pct - t.prior_negative_pct;
                const on = theme === t.theme;
                return (
                  <li key={t.theme}>
                    <button type="button" aria-pressed={on} onClick={() => reset(() => setTheme(on ? "" : t.theme))} className={`w-full rounded-2xl border p-4 text-left transition hover:-translate-y-0.5 ${on ? "border-fg bg-surface-2" : "border-line bg-surface"}`}>
                      <div className="flex items-baseline justify-between"><span className="font-semibold">{t.label}</span><span className="font-mono text-xs text-muted">{t.mentions} mentions</span></div>
                      <div className="mt-3 h-2 overflow-hidden rounded-full bg-mor/25"><div className="h-full bg-sindoor transition-[width] duration-700" style={{ width: `${t.negative_pct}%` }} /></div>
                      <p className="mt-2 text-sm"><b className={t.negative_pct >= 40 ? "text-sindoor" : ""}>{t.negative_pct.toFixed(0)}%</b> negative
                        {delta != null && Math.abs(delta) >= 5 && <span className={`ml-2 text-xs ${delta > 0 ? "text-sindoor" : "text-mor"}`}>{delta > 0 ? "▲" : "▼"} {Math.abs(delta).toFixed(0)} pts vs before</span>}
                      </p>
                    </button>
                  </li>
                );
              })}
            </ul>
          </section>

          {(prods.data?.length ?? 0) > 0 && (
            <section aria-label="Products" className="rounded-2xl border border-line bg-surface">
              <h2 className="border-b border-line px-5 py-3 font-semibold">Products to look at first</h2>
              <ul className="divide-y divide-line">
                {prods.data?.slice(0, 6).map((p) => (
                  <li key={p.product_id} className="flex flex-wrap items-center justify-between gap-2 px-5 py-3 text-sm">
                    <span className="font-medium">{p.product}</span>
                    <span className="text-muted">{p.reviews} reviews · <b className={p.negative_pct >= 40 ? "text-sindoor" : "text-fg"}>{p.negative_pct.toFixed(0)}% negative</b>{p.top_problem && <> · mostly {THEME_LABEL[p.top_problem] ?? p.top_problem}</>}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <section aria-label="Reviews" className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="mr-2 font-semibold">Reviews</h2>
              {(["", "negative", "neutral", "positive"] as const).map((k) => (
                <button key={k || "all"} type="button" aria-pressed={label === k} onClick={() => reset(() => setLabel(k))} className={`rounded-full px-3 py-1 text-sm ${label === k ? "bg-fg text-canvas" : "border border-line hover:bg-surface-2"}`}>{k ? TONE[k].word : "All"}</button>
              ))}
              <label className="sr-only" htmlFor="lang">Language</label>
              <select id="lang" value={lang} onChange={(e) => reset(() => setLang(e.target.value))} className="rounded-full border border-line bg-canvas px-3 py-1 text-sm">
                <option value="">Any language</option><option value="en">English</option><option value="hinglish">Hinglish</option><option value="hi">हिन्दी</option>
              </select>
              <label className="sr-only" htmlFor="q">Search reviews</label>
              <input id="q" value={q} onChange={(e) => reset(() => setQ(e.target.value))} placeholder="Search words" className="min-w-0 flex-1 rounded-full border border-line bg-canvas px-4 py-1 text-sm sm:max-w-56" />
              {theme && <button type="button" onClick={() => reset(() => setTheme(""))} className="rounded-full bg-haldi/25 px-3 py-1 text-sm">Theme: {THEME_LABEL[theme] ?? theme} ✕</button>}
            </div>
            {feed.error && <ErrorNote message={feed.error} />}
            {feed.data && feed.data.items.length === 0 && <EmptyNote>No reviews match these filters.</EmptyNote>}
            <ul className={`space-y-3 transition-opacity ${feed.loading ? "opacity-60" : ""}`}>
              {feed.data?.items.map((r) => (
                <li key={r.id} className="flex overflow-hidden rounded-2xl border border-line bg-surface">
                  <span aria-hidden className={`w-1.5 shrink-0 ${TONE[r.label].bar}`} />
                  <div className="min-w-0 flex-1 p-4">
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted">
                      <Stars n={r.rating} />
                      <span className={`rounded-full px-2 py-0.5 ${TONE[r.label].chip}`}>{TONE[r.label].word}</span>
                      <span>{LANG[r.language] ?? r.language}</span>
                      {r.product && <span>· {r.product}</span>}
                      {r.review_date && <span>· {r.review_date}</span>}
                      <span>· {r.source}</span>
                    </div>
                    <p className="mt-2 break-words text-sm">{r.text}</p>
                    {r.themes.length > 0 && <div className="mt-2"><ThemeChips themes={r.themes} /></div>}
                  </div>
                </li>
              ))}
            </ul>
            {feed.data && feed.data.total > 10 && (
              <div className="flex items-center justify-between text-sm">
                <button type="button" disabled={page === 0} onClick={() => setPage((p) => p - 1)} className="rounded-full border border-line px-4 py-1.5 disabled:opacity-40">← Newer</button>
                <span className="text-muted">{page * 10 + 1}–{Math.min((page + 1) * 10, feed.data.total)} of {feed.data.total}</span>
                <button type="button" disabled={(page + 1) * 10 >= feed.data.total} onClick={() => setPage((p) => p + 1)} className="rounded-full border border-line px-4 py-1.5 disabled:opacity-40">Older →</button>
              </div>
            )}
          </section>

          <p className="rounded-xl bg-surface-2 p-4 text-xs text-muted">
            How to read this: moods come from word lists written for English, हिन्दी and Hinglish, plus a model that learns from your star ratings once you have 100 or more. Sarcasm and unusual spellings can fool it.
            {s.unscored > 0 && <> {s.unscored} of {s.in_window} reviews had no opinion words it knew, so they show as neutral.</>}
            {s.mismatch > 0 && <> {s.mismatch} reviews have stars that disagree with their words; worth a look.</>}
          </p>
        </>
      )}

      <TryBox base={base} />
    </div>
  );
}
