# apps/web: Vyapar AI frontend

Next.js 15 (App Router) · TypeScript · Tailwind v4 · three.js (the cloth opening) · GSAP ScrollTrigger · Lenis · Motion.

```bash
cp .env.example .env.local
npm install
npm run dev        # http://localhost:3000
npm run lint       # tsc --noEmit
npm test           # service worker and audio tests (node --test)
npm run gen:api    # regenerate lib/api-types.ts from ../api/openapi.json
npm run build      # never while the dev server runs: it shares .next
```

| Route | What |
|---|---|
| `/` | Closed-shop opening (simulated cloth, ribbon, draggable scissors) → landing page |
| `/login` | Sign in or create an account; in development, one-tap sample accounts for each job |
| `/join` | Accept a team invite |
| `/app` | Command center |
| `/app/today`, `galla`, `orders`, `expiry` | The daily routine ([DAILY](../../docs/DAILY.md)) |
| `/app/ask` | The assistant, typed or spoken |
| `/app/investigate` | Agent workflows: run now or every day |
| `/app/sales`, `customers`, `products`, `staff`, `forecasts`, `inventory`, `udhaar`, … | One page per area; the navigation shows only what the signed-in job may use |
| `/app/data` | Imports: upload → map → review → import |
| `/offline` | Shown by the service worker when there is no network |

```
app/                 routes
components/
  opening/           3D opening (ShopScene, CinematicOpening)
  landing/           landing sections
  app/               product UI (import wizard, dashboards, charts)
lib/                 api client, session, sound effects, formatting (en-IN), demo data
public/assets/       CC0 HDRI + PBR textures (see LICENSES.md), sample CSV
```

Design tokens: `app/globals.css`. Rationale: [docs/DESIGN_SYSTEM.md](../../docs/DESIGN_SYSTEM.md).
The API base URL comes from `NEXT_PUBLIC_API_URL` (default `http://localhost:8000/api/v1`).
