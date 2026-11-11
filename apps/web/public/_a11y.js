// A small accessibility audit to paste into the browser console (or run through the browser pane) on any page.
// It checks the basics we can measure without a library: names, labels, alt text, language, headings,
// duplicate ids, positive tabindex, small touch targets and text contrast (WCAG AA, best effort).
// It is not a replacement for a screen-reader test.
(() => {
  const out = [];
  const add = (rule, el, detail) => out.push({ rule, el: sel(el), detail });
  const sel = (e) => (e.id ? `#${e.id}` : `${e.tagName.toLowerCase()}${e.className && typeof e.className === "string" ? "." + e.className.trim().split(/\s+/).slice(0, 2).join(".") : ""}`) + ` "${(e.innerText || e.getAttribute("aria-label") || "").trim().slice(0, 30)}"`;
  const visible = (e) => { const r = e.getBoundingClientRect(); const s = getComputedStyle(e); return r.width > 0 && r.height > 0 && s.visibility !== "hidden" && s.display !== "none" && !e.closest("[aria-hidden=true]"); };
  const name = (e) => (e.getAttribute("aria-label") || e.getAttribute("aria-labelledby") && [...e.getAttribute("aria-labelledby").split(" ")].map((i) => document.getElementById(i)?.innerText).join(" ") || e.innerText || e.getAttribute("title") || e.querySelector("img[alt]")?.alt || "").trim();
  if (!document.documentElement.lang) add("html-lang", document.documentElement, "missing lang");
  document.querySelectorAll("img").forEach((i) => { if (!i.hasAttribute("alt") && visible(i)) add("img-alt", i, "no alt"); });
  document.querySelectorAll("a[href],button,[role=button]").forEach((e) => { if (visible(e) && !name(e)) add("name", e, "link or button without a name"); });
  document.querySelectorAll("input:not([type=hidden]),select,textarea").forEach((e) => {
    if (!visible(e) && e.type !== "checkbox") return;
    const labelled = e.id && document.querySelector(`label[for="${e.id}"]`) || e.closest("label") || e.getAttribute("aria-label") || e.getAttribute("aria-labelledby");
    if (!labelled) add("label", e, "form control without a label");
  });
  const ids = {}; document.querySelectorAll("[id]").forEach((e) => { ids[e.id] = (ids[e.id] || 0) + 1; });
  Object.entries(ids).filter(([, n]) => n > 1).forEach(([id]) => add("dup-id", document.getElementById(id), `id "${id}" used ${ids[id]} times`));
  document.querySelectorAll("[tabindex]").forEach((e) => { if (Number(e.getAttribute("tabindex")) > 0) add("tabindex", e, "positive tabindex"); });
  let last = 0; document.querySelectorAll("h1,h2,h3,h4,h5,h6").forEach((h) => { if (!visible(h)) return; const l = Number(h.tagName[1]); if (last && l > last + 1) add("heading-order", h, `h${last} to h${l}`); last = l; });
  if (document.querySelectorAll("h1").length !== 1) add("h1", document.body, `${document.querySelectorAll("h1").length} h1 elements`);
  if (!document.querySelector("main,[role=main]")) add("landmark", document.body, "no main landmark");
  document.querySelectorAll("a[href],button,select,input,[role=button]").forEach((e) => { if (!visible(e) || e.closest("[class*=sr-only]")) return; const r = e.getBoundingClientRect(); if ((r.width < 24 || r.height < 24) && e.type !== "checkbox" && !e.closest("p")) add("target-size", e, `${Math.round(r.width)}x${Math.round(r.height)}px`); });
  const parse = (c) => { const m = c.match(/rgba?\(([^)]+)\)/); if (!m) return null; const p = m[1].split(/[ ,/]+/).filter(Boolean).map(Number); return { r: p[0], g: p[1], b: p[2], a: p[3] ?? 1 }; };
  const lum = ({ r, g, b }) => { const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; }; return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b); };
  const bg = (e) => { for (let n = e; n; n = n.parentElement) { const c = parse(getComputedStyle(n).backgroundColor); if (c && c.a > 0.5) return c; } return { r: 246, g: 239, b: 226, a: 1 }; };
  const seen = new Set();
  document.querySelectorAll("p,span,a,button,li,label,h1,h2,h3,h4,td,th,dt,dd,small,div").forEach((e) => {
    if (!visible(e) || ![...e.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim())) return;
    const s = getComputedStyle(e); const fg = parse(s.color); if (!fg) return; const b = bg(e);
    const mix = { r: fg.r * fg.a + b.r * (1 - fg.a), g: fg.g * fg.a + b.g * (1 - fg.a), b: fg.b * fg.a + b.b * (1 - fg.a) };
    const L1 = lum(mix), L2 = lum(b); const ratio = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
    const size = parseFloat(s.fontSize); const bold = Number(s.fontWeight) >= 700; const large = size >= 24 || (size >= 18.66 && bold);
    const key = sel(e) + ratio.toFixed(1); if (ratio < (large ? 3 : 4.5) && !seen.has(key)) { seen.add(key); add("contrast", e, `${ratio.toFixed(2)}:1 at ${size}px`); }
  });
  const grouped = {}; out.forEach((o) => { (grouped[o.rule] ||= []).push(o); });
  return Object.fromEntries(Object.entries(grouped).map(([k, v]) => [k, { count: v.length, examples: v.slice(0, 6).map((x) => `${x.el} :: ${x.detail}`) }]));
})();
