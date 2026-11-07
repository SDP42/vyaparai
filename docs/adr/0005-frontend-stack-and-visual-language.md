# 0005 · Frontend stack and "Bahi-Khata" visual language

- **Date:** 2026-11-07 · **Status:** Accepted

**Decision.** Next.js App Router + TypeScript + Tailwind v4 tokens. Landing motion uses Lenis +
GSAP ScrollTrigger + React Three Fiber (one shader-driven `Points` mesh); UI transitions use Motion.
The visual language is drawn from the Indian trader's ledger (warm ink, ledger paper, sindoor, haldi)
instead of the generic navy/violet AI aesthetic suggested in the blueprint.

**Consequences.** Distinctive brand. The 3D hero needs reduced-motion and no-WebGL fallbacks (both
implemented) and a performance budget (DPR cap, offscreen pause, ~16k particles desktop / 8k mobile).
