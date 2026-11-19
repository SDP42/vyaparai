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
| `/` | Cinematic key-and-lock opening (pinned, scroll-driven) → landing page |
| `/login` | Persona demo, or sign in / create an account against the API |
| `/app` | Account: command center · Persona: illustrative demo dashboard |
| `/app/sales` | Sales explorer: drivers, contributions, drill-through (Phase 2) |
| `/app/data` | Imports: upload → map → review → import |

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
