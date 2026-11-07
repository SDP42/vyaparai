# apps/web: Vyapar AI frontend

Next.js (App Router) + TypeScript + Tailwind v4 · React Three Fiber · GSAP ScrollTrigger · Lenis · Motion.

```bash
cp .env.example .env.local
npm install
npm run dev     # http://localhost:3000
```

| Route | What |
|---|---|
| `/` | Landing page: shattering-word 3D hero, scroll story, zoom reveal, features, principles |
| `/login` | Persona chooser (demo) + email sign-in against the API |
| `/app` | Persona-aware dashboard (demo data until Phase F2) |

Design tokens: `app/globals.css`. Design rationale: [docs/DESIGN_SYSTEM.md](../../docs/DESIGN_SYSTEM.md).
