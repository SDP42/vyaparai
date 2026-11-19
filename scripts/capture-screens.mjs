// Take high-resolution screenshots of the running app for docs and posts, through headless Chrome's DevTools
// protocol (no extra packages: Node 22 has WebSocket built in).
//
//   node scripts/capture-screens.mjs            (API on :8000 and web on :3000, DEMO_LOGIN_ENABLED=true)
//
// Images go to docs/linkedin/images. Demo data only.
import { spawn } from "node:child_process";
import { mkdirSync, writeFileSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const WEB = "http://localhost:3000";
const OUT = new URL("../docs/linkedin/images/", import.meta.url).pathname;
const PORT = 9333;
mkdirSync(OUT, { recursive: true });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const chrome = spawn(CHROME, [
  "--headless=new", `--remote-debugging-port=${PORT}`, `--user-data-dir=${mkdtempSync(join(tmpdir(), "vyapar-shots-"))}`,
  "--hide-scrollbars", "--no-first-run", "--no-default-browser-check", "--enable-unsafe-swiftshader", "--use-angle=swiftshader", "about:blank",
], { stdio: "ignore" });

async function target() {
  for (let i = 0; i < 50; i++) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
      const page = list.find((t) => t.type === "page");
      if (page) return page.webSocketDebuggerUrl;
    } catch { /* not up yet */ }
    await sleep(200);
  }
  throw new Error("Chrome did not start");
}

const ws = new WebSocket(await target());
await new Promise((r) => ws.addEventListener("open", r, { once: true }));
let id = 0;
const pending = new Map();
ws.addEventListener("message", (e) => {
  const m = JSON.parse(e.data);
  if (m.id && pending.has(m.id)) {
    pending.get(m.id)(m);
    pending.delete(m.id);
  }
});
const send = (method, params = {}) =>
  new Promise((resolve, reject) => {
    const n = ++id;
    pending.set(n, (m) => (m.error ? reject(new Error(`${method}: ${m.error.message}`)) : resolve(m.result)));
    ws.send(JSON.stringify({ id: n, method, params }));
  });
const evaluate = async (expression) => (await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true })).result?.value;

async function viewport(width, height, mobile = false) {
  await send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 2, mobile });
}
async function go(path, wait = 3500) {
  await send("Page.navigate", { url: WEB + path });
  await sleep(wait);
}
async function shot(name) {
  const { data } = await send("Page.captureScreenshot", { format: "png" });
  writeFileSync(join(OUT, name + ".png"), Buffer.from(data, "base64"));
  console.log("saved", name);
}
async function scrollTo(selector, offset = 0, wait = 2600) {
  await evaluate(`(() => { const el = document.querySelector(${JSON.stringify(selector)}); if (el) window.scrollTo(0, el.getBoundingClientRect().top + window.scrollY + ${offset}); })()`);
  await sleep(wait);
}

await send("Page.enable");
await send("Runtime.enable");
await viewport(1440, 900);

const only = process.argv[2]; // "landing" retakes just the landing sections

if (only !== "landing") {
// 1. the opening: the cloth, then mid-fall after the cut
await go("/?opening=1", 7000);
await shot("01-opening-cloth");
await evaluate(`document.querySelector('button[aria-label^="Scissors"]')?.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }))`);
await sleep(1150);
await shot("02-opening-ribbon-cut");
await sleep(1100);
await shot("03-opening-cloth-falling");
await sleep(3000);
}

// 2. the landing page, with the opening already seen this visit
await go("/", 1500);
await evaluate(`sessionStorage.setItem("vyapar.opened", "1")`);
await go("/", 4500);
await shot("04-landing-hero");
await scrollTo("#how", 700);
await shot("05-landing-how-it-works");
await scrollTo("#features", 0);
await shot("06-landing-features");
await scrollTo("#team", 300);
await shot("07-landing-jobs");
await scrollTo("#voice", 0, 3500);
await shot("08-landing-voice");
await scrollTo("#trust", -40);
await shot("09-landing-trust");

if (only === "landing") {
  ws.close();
  chrome.kill();
  process.exit(0);
}

// 3. sign in as the sample owner
await go("/login", 3500);
await shot("10-sign-in-personas");
await evaluate(`[...document.querySelectorAll('button')].find((b) => /Meera/.test(b.getAttribute('aria-label') || ''))?.click()`);
await sleep(4500);

// 4. the app
for (const [path, name, wait] of [
  ["/app/today", "11-app-today", 4000],
  ["/app", "12-app-command-center", 5000],
  ["/app/sales", "13-app-sales-drivers", 5000],
  ["/app/forecasts", "14-app-forecasts", 5000],
  ["/app/inventory", "15-app-stock", 4500],
  ["/app/udhaar", "16-app-udhaar", 4500],
  ["/app/galla", "17-app-galla", 4000],
  ["/app/orders", "18-app-orders", 4000],
  ["/app/recommendations", "19-app-next-steps", 4500],
  ["/app/team", "20-app-team-personas", 4000],
]) {
  await go(path, wait);
  await shot(name);
}

// the assistant answering a Hinglish question
await go("/app/ask", 3500);
await evaluate(`(async () => { const i = document.querySelector('#ask'); const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set; set.call(i, 'pichle hafte ki bikri kitni thi?'); i.dispatchEvent(new Event('input', { bubbles: true })); await new Promise((r) => setTimeout(r, 200)); i.form.requestSubmit(); })()`);
await sleep(5000);
await shot("21-app-ask-hinglish");

// an automation agent: udhaar collector with drafted reminders
await go("/app/investigate", 4000);
await evaluate(`[...document.querySelectorAll('button')].filter((b) => b.textContent === 'Run now')[2]?.click()`);
await sleep(6000);
await scrollTo("main", 0, 500);
await evaluate(`(() => { const h = [...document.querySelectorAll('h2')].find((x) => /What the numbers show/.test(x.textContent)); if (h) window.scrollTo(0, h.getBoundingClientRect().top + window.scrollY - 90); })()`);
await sleep(1500);
await shot("22-app-agent-udhaar-collector");

// 5. phone size
await viewport(390, 844, true);
for (const [path, name] of [["/app/today", "23-phone-today"], ["/app/ask", "24-phone-ask"]]) {
  await go(path, 4500);
  await shot(name);
}
await go("/", 4000);
await shot("25-phone-landing");

ws.close();
chrome.kill();
console.log("done");
