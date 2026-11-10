# Installable app and Hinglish/Hindi

## Install and offline

- The web app is a **progressive web app**: a manifest (name, standalone display, start page `/app`, icons including a maskable one, shortcuts to Ask, Alerts and Udhaar) lets Chrome and Android install it, and an "Install the app" button appears when the browser offers it. On iPhone use Share, then Add to Home Screen.
- A **service worker** (`public/sw.js`, production builds only) caches the app's own scripts, styles, fonts and icons as they are used, so the app opens without a connection, and shows an offline page for new pages.
- **Offline reading**: a fixed list of read-only pages keeps its last good answer (sales overview, customers summary, alerts, today's digest preview, stock overview, udhaar summary and list, recommendations, latest forecast, pricing, review summary, reports list). Offline, the app serves that saved answer and a banner says "these are the numbers saved on this phone".
- **Never saved or touched**: sign-in and session calls, anything that is not a GET, uploads and imports, exports, downloads, PDFs, streamed answers, document search and questions to the assistant, bills, and any response marked `no-store`.
- **Sign-out erases the saved numbers** on the device, so a shared phone keeps nothing.
- Writing while offline is not supported: nothing is queued, and the app says it needs a connection.

## Language

A language switch (English, Hinglish, हिन्दी) sits in the sidebar and the phone header and is remembered on the device. Covered: the navigation, the app shell, and the Ask, Next steps and Udhaar pages (headings, tabs, buttons, labels). Everything else stays English. A missing word falls back to English; the compiler checks that all three languages define every key, and a test checks the Hindi dictionary is really Devanagari.

## Limits

- **The Hinglish and Hindi wording has not been reviewed by a native speaker.** Treat it as a good first draft.
- Other pages (Sales, Customers, Forecasts, Stock, Pricing and so on) are English only; only the assistant and the reminder drafts speak all three languages today.
- The service worker could not be registered inside the build environment's embedded browser, so its behaviour is verified by running its real code in a simulated worker (`apps/web/tests/sw.test.mjs`: live fetch and save, offline serving, exclusions, no-store, clearing, offline page), not on a physical phone. Install it on a real phone once and check the offline banner.
- Offline reading shows the last data seen, which may be old; the banner says so but not how old.
- Voice input on the Ask page uses the browser's own speech recognition where it exists, set to Hindi-India.
