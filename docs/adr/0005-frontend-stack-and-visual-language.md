# 0005 · Frontend stack and "Bahi-Khata" visual language

- **Date:** 2026-11-07 · **Status:** Accepted, amended 2026-11-08 (bright theme, scroll-driven opening)

**Decision.** Next.js App Router + TypeScript + Tailwind v4 tokens. Landing motion uses Lenis +
GSAP ScrollTrigger + React Three Fiber (one shader-driven `Points` mesh); UI transitions use Motion.
The visual language is drawn from the Indian trader's ledger (warm ink, ledger paper, sindoor, haldi)
instead of the generic navy/violet AI aesthetic suggested in the blueprint.

**Consequences.** Distinctive brand. The 3D hero needs reduced-motion and no-WebGL fallbacks (both
implemented) and a performance budget (DPR cap, offscreen pause, ~16k particles desktop / 8k mobile).

**Amendment (2026-11-08).** The palette is bright and warm (cream, ink, sindoor, haldi) rather than the
blueprint's dark navy, and the 3D hero is a photoreal, scroll-driven key-and-lock opening (HDRI + PBR
textures) instead of a particle scene. See [DESIGN_SYSTEM.md](../DESIGN_SYSTEM.md).

## Amendment 2026-11-11

React Three Fiber and three.js were removed: the opening is now a closed shop under a cloth tied with a ribbon (drag the scissors to cut it), drawn in SVG and CSS and animated with GSAP. GSAP and Lenis remain.
