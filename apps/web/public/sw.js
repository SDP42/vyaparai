/* Vyapar AI service worker: installable app shell and read-only offline numbers.
 *
 * - Static files (JS, CSS, fonts, icons) are cached as they are used, so the app opens without a network.
 * - A fixed list of read-only API pages is kept as the last successful answer; offline, those answers are
 *   served marked "x-vyapar-offline" so the app can say they are saved numbers.
 * - Never cached: anything that is not a GET, sign-in and session calls, uploads, downloads, streams.
 * - Everything cached from the API is deleted on sign-out ("clear" message) so a shared phone keeps nothing.
 */
const STATIC = "vyapar-static-v1";
const DATA = "vyapar-data-v1";
const OFFLINE_URL = "/offline";
const READABLE = /\/api\/v1\/workspaces\/[0-9a-f-]+\/(analytics\/(overview|customers\/summary)|alerts(\/summary)?|digests\/preview|inventory\/overview|udhaar\/(summary|parties)|recommendations(\/summary)?|forecasts\/latest|pricing\/(discounts|moves)|reviews\/summary|reports)$/;
const NEVER = /\/(auth|stream|import|export|template|download|pdf|csv)(\/|\.|$)/;

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(STATIC).then((c) => c.addAll([OFFLINE_URL, "/manifest.webmanifest", "/icons/icon-192.png"])).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => ![STATIC, DATA].includes(k)).map((k) => caches.delete(k)))).then(() => self.clients.claim()),
  );
});

self.addEventListener("message", (e) => {
  if (e.data === "clear") e.waitUntil(caches.delete(DATA));
});

function offlineCopy(res) {
  const headers = new Headers(res.headers);
  headers.set("x-vyapar-offline", "1");
  return new Response(res.body, { status: res.status, statusText: res.statusText, headers });
}

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);

  if (READABLE.test(url.pathname) && !NEVER.test(url.pathname)) {
    e.respondWith(
      fetch(req)
        .then(async (res) => {
          if (res.ok && !/no-store/.test(res.headers.get("cache-control") || "")) (await caches.open(DATA)).put(url.pathname + url.search, res.clone());
          return res;
        })
        .catch(async () => {
          const hit = await (await caches.open(DATA)).match(url.pathname + url.search);
          return hit ? offlineCopy(hit) : new Response(JSON.stringify({ error: { code: "offline", message: "You are offline and this has not been saved yet." } }), { status: 503, headers: { "content-type": "application/json" } });
        }),
    );
    return;
  }

  if (url.origin !== self.location.origin) return;

  if (req.mode === "navigate") {
    e.respondWith(fetch(req).catch(() => caches.match(req).then((r) => r || caches.match(OFFLINE_URL))));
    return;
  }

  if (/^\/(_next\/static|icons|assets|fonts)\//.test(url.pathname) || url.pathname === "/manifest.webmanifest") {
    e.respondWith(
      caches.match(req).then(
        (hit) =>
          hit ||
          fetch(req).then((res) => {
            if (res.ok) caches.open(STATIC).then((c) => c.put(req, res.clone()));
            return res;
          }),
      ),
    );
  }
});
