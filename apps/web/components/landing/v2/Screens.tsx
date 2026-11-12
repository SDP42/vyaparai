/**
 * Product screens drawn as real UI (not images), with the sample shop's numbers. Used by the landing page.
 * They are illustrations: aria-hidden, with the same information said in the text beside them.
 */

export function PhoneFrame({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`relative mx-auto w-[300px] rounded-[2.6rem] border border-[#2a221b] bg-[#16110d] p-2.5 shadow-[0_40px_80px_-30px_rgba(60,30,5,.55),0_0_0_1px_rgba(255,255,255,.04)_inset] ${className}`} aria-hidden>
      <div className="absolute left-1/2 top-3.5 z-10 h-5 w-24 -translate-x-1/2 rounded-full bg-[#16110d]" />
      <div className="overflow-hidden rounded-[2.1rem] bg-canvas">{children}</div>
    </div>
  );
}

export function TodayScreen() {
  return (
    <div className="px-4 pb-5 pt-10 text-[13px] text-fg">
      <div className="flex items-baseline justify-between">
        <p className="font-semibold">Kulkarni General Store</p>
        <p className="font-mono text-[10px] text-muted">Wed, 12 Nov</p>
      </div>
      <p className="mt-3 font-mono text-[10px] uppercase tracking-[0.16em] text-muted">Kal ki bikri</p>
      <p className="mt-0.5 text-[28px] font-bold leading-none tabular-nums">₹46,820</p>
      <p className="mt-1 text-[11px] text-mor">▲ 6% pichle Tuesday se</p>
      <div className="mt-4 space-y-2">
        <div className="rounded-2xl border border-line bg-surface p-3">
          <p className="text-[11px] text-muted">Udhaar wapas aana hai</p>
          <p className="mt-0.5 font-semibold tabular-nums">₹4,200 · 3 log</p>
          <p className="mt-1 text-[11px] text-fg/70">Ramesh ₹2,100 · 41 din</p>
        </div>
        <div className="rounded-2xl border border-line bg-surface p-3">
          <p className="text-[11px] text-muted">Aaj mangwana hai</p>
          {[
            ["Aashirvaad Atta 5kg", "× 20", true],
            ["Desi Ghee 1L", "× 12", false],
            ["Toor Dal 1kg", "× 15", false],
          ].map(([n, q, done]) => (
            <p key={n as string} className="mt-1.5 flex items-center gap-2">
              <span className={`grid h-4 w-4 place-items-center rounded border text-[9px] ${done ? "border-mor bg-mor text-canvas" : "border-line"}`}>{done ? "✓" : ""}</span>
              <span className={`flex-1 ${done ? "text-muted line-through" : ""}`}>{n}</span>
              <span className="font-mono text-[11px] text-muted">{q}</span>
            </p>
          ))}
        </div>
        <div className="rounded-2xl bg-fg p-3 text-canvas">
          <p className="text-[11px] text-canvas/70">Is hafte ek kaam</p>
          <p className="mt-0.5 leading-snug">Ghee ka daam ₹590 se ₹615 hua, aapka bechne ka daam wahi hai.</p>
        </div>
      </div>
      <div className="mt-4 flex items-center gap-2 rounded-full border border-line bg-surface p-1.5 pl-4">
        <span className="flex-1 text-[12px] text-muted">Poochiye ya boliye…</span>
        <span className="grid h-8 w-8 place-items-center rounded-full bg-sindoor text-canvas">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"><rect x="9" y="3" width="6" height="12" rx="3" /><path d="M5 11a7 7 0 0 0 14 0M12 18v3" /></svg>
        </span>
      </div>
    </div>
  );
}

export function UdhaarScreen() {
  const rows = [
    ["Ramesh Yadav", "₹2,100", "41 din", "high"],
    ["Sunita Patil", "₹1,450", "18 din", "mid"],
    ["Anil Store", "₹650", "6 din", "low"],
  ] as const;
  return (
    <div className="p-5 text-sm">
      <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted">Who to call first</p>
      <ul className="mt-3 divide-y divide-line">
        {rows.map(([n, a, d, lvl]) => (
          <li key={n} className="flex items-center justify-between gap-3 py-2.5">
            <span className="flex items-center gap-2.5">
              <span className={`h-2 w-2 rounded-full ${lvl === "high" ? "bg-sindoor" : lvl === "mid" ? "bg-haldi" : "bg-mor"}`} />
              <span className="font-medium">{n}</span>
            </span>
            <span className="text-right tabular-nums">
              {a} <span className="ml-2 font-mono text-[11px] text-muted">{d}</span>
            </span>
          </li>
        ))}
      </ul>
      <div className="mt-3 rounded-xl bg-surface-2 p-3 text-[13px] leading-relaxed">
        Namaste Ramesh ji, aapka ₹2,100 baaki hai. Jab suvidha ho, de dijiye. Dhanyavaad, Kulkarni Store.
        <p className="mt-2 font-mono text-[10px] uppercase tracking-wider text-muted">Draft · you send it</p>
      </div>
    </div>
  );
}

export function OrderScreen() {
  const rows = [
    ["Aashirvaad Atta 5kg", 3, 20],
    ["Desi Ghee 1L", 5, 12],
    ["Basmati Rice 5kg", 9, 0],
  ] as const;
  return (
    <div className="p-5 text-sm">
      <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted">Days of stock left</p>
      <ul className="mt-3 space-y-3">
        {rows.map(([n, days, qty]) => (
          <li key={n}>
            <div className="flex justify-between">
              <span>{n}</span>
              <span className="font-mono text-[11px]">{qty ? `order ${qty}` : "fine"}</span>
            </div>
            <div className="mt-1 h-1.5 rounded-full bg-line">
              <div className={`h-full rounded-full ${days < 4 ? "bg-sindoor" : days < 7 ? "bg-haldi" : "bg-mor"}`} style={{ width: `${Math.min(100, days * 10)}%` }} />
            </div>
            <p className="mt-0.5 font-mono text-[10px] text-muted">{days} days at the forecast rate</p>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function BillScreen() {
  return (
    <div className="grid grid-cols-[1fr_1.3fr] gap-3 p-5 text-[12px]">
      <div className="rotate-[-2deg] rounded-md bg-[#fbf6ea] p-3 font-mono text-[10px] leading-relaxed text-fg/80 shadow-md">
        <p className="text-center font-bold">SHREE TRADERS</p>
        <p className="text-center text-[9px]">GSTIN 27AB…</p>
        <p className="mt-2">Atta 5kg 20 × 258</p>
        <p>Sugar 1kg 40 × 43</p>
        <p className="bg-haldi/40">Ghee 1L 12 × 615</p>
        <p className="mt-1 border-t border-dashed border-fg/30 pt-1">Total 14,600</p>
      </div>
      <div className="space-y-1.5">
        {[
          ["Atta 5kg", "₹258", "same"],
          ["Sugar 1kg", "₹43", "same"],
          ["Ghee 1L", "₹615", "+₹25"],
        ].map(([n, r, ch]) => (
          <div key={n} className={`flex justify-between rounded-lg px-2.5 py-1.5 ${ch !== "same" ? "bg-sindoor/10" : "bg-surface"}`}>
            <span>{n}</span>
            <span className="tabular-nums">
              {r} <span className={`ml-1 font-mono text-[10px] ${ch !== "same" ? "text-sindoor" : "text-muted"}`}>{ch}</span>
            </span>
          </div>
        ))}
        <p className="pt-1 font-mono text-[10px] text-muted">Read from the photo · checked by you</p>
      </div>
    </div>
  );
}

export function ForecastScreen() {
  const pts = [38, 41, 36, 44, 48, 52, 47, 50, 55, 53, 58, 66, 74, 70];
  const w = 300;
  const h = 110;
  const x = (i: number) => (i / (pts.length - 1)) * w;
  const y = (v: number) => h - (v / 80) * h;
  const split = 9;
  const line = (a: number, b: number) => pts.slice(a, b + 1).map((v, i) => `${i ? "L" : "M"}${x(a + i)},${y(v)}`).join(" ");
  const band = pts.slice(split).map((v, i) => `${x(split + i)},${y(v + 6 + i * 1.5)}`).join(" ") + " " + pts.slice(split).map((v, i) => `${x(split + i)},${y(v - 6 - i * 1.5)}`).reverse().join(" ");
  return (
    <div className="p-5">
      <div className="flex items-baseline justify-between text-sm">
        <p className="font-semibold">Next 2 weeks</p>
        <p className="font-mono text-[10px] text-muted">Diwali week ahead</p>
      </div>
      <svg viewBox={`0 0 ${w} ${h + 6}`} className="mt-3 w-full">
        <polygon points={band} fill="var(--color-haldi)" fillOpacity=".22" />
        <path d={line(0, split)} fill="none" stroke="var(--color-fg)" strokeWidth="2" />
        <path d={line(split, pts.length - 1)} fill="none" stroke="var(--color-haldi-deep)" strokeWidth="2" strokeDasharray="5 4" />
        <line x1={x(split)} x2={x(split)} y1="0" y2={h} stroke="var(--color-line)" />
      </svg>
      <p className="mt-2 text-[12px] text-fg/70">Likely ₹6.1L to ₹7.4L. Last month this model was off by 9% on average.</p>
    </div>
  );
}

export function AlertScreen() {
  return (
    <div className="space-y-2 p-5 text-[13px]">
      {[
        ["high", "Sales down 18% on Tuesdays", "Mostly fewer bills in Staples"],
        ["mid", "Ghee cost up, price not", "Margin fell from 14% to 10%"],
        ["low", "5 regulars quiet for 30 days", "₹9,800 a month between them"],
      ].map(([lvl, t, d]) => (
        <div key={t} className="flex gap-3 rounded-xl border border-line bg-surface p-3">
          <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${lvl === "high" ? "bg-sindoor" : lvl === "mid" ? "bg-haldi" : "bg-mor"}`} />
          <span>
            <span className="block font-medium">{t}</span>
            <span className="text-[12px] text-muted">{d}</span>
          </span>
        </div>
      ))}
    </div>
  );
}
