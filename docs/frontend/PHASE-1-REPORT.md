# Phase 1 — Inspection & Visual Direction

**Stage:** Two-page frontend (Cinematic Key-and-Lock Opening → Vyapar.ai Landing Page)
**Status:** Approved with changes. The owner moved the **landing page first**, chose a **bright** theme over dark-first, and asked for no religious motifs. Landing page built 2026-11-07; photoreal opening is next.
**Date:** 2026-11-07

---

## 1. What this phase covers

| Required by master prompt | Where |
|---|---|
| Read the blueprint: product, brand, audience, positioning | §2 |
| Inspect the existing repository | §3 |
| Establish the visual direction | §4–§6 |
| Plan assets, audio, architecture and performance | §7–§10 |
| Risks, open decisions and acceptance criteria | §11–§13 |

---

## 2. Blueprint understanding (what the site must communicate)

**Product.** Vyapar.ai is an *autonomous business-intelligence and decision-support platform*
for small and medium retailers (§02). It converts operational data into **trusted metrics,
predictive insights, explanations and human-approved actions**.

**Primary promise (§02):** *what happened → why it happened → what may happen next → what action is worth considering.*

**Audience (§02).** The owner or operations manager of a small, multi-category retailer.

**Positioning pillars to carry into the copy.** These are the blueprint's own differentiators.

| Pillar | Blueprint source | How the landing page shows it |
|---|---|---|
| Numbers you can trust | §13 canonical metrics, §20 "Copilot must not invent numbers" | Trust section: "Reproducible metrics" |
| Explainability | §14 driver analysis, §23 evidence refs | Copilot preview shows evidence chips |
| Honest prediction | §16 baselines, intervals, low-confidence labels | Forecast mockup with interval band and a confidence label |
| Human in control | §21–§23 agents can't buy or write; approval states | "Human-approved actions" card; Approve/Dismiss in the preview |
| Privacy & tenancy | §10, §24 | Trust section footnote |

**Capabilities we may describe (§03, §14–§23 only).** Command Center, Sales Intelligence,
Customer Intelligence (RFM/churn), Inventory Intelligence (reorder simulation), Predictive
Analytics (forecasting), Review Intelligence (NLP sentiment and aspects), Document Intelligence
(RAG with citations), Vyapar Copilot, Agentic Workflows (read-only, traced), Decision Support
(structured recommendations). **Nothing else will be claimed.** Copy will not say things like
"real-time", "integrates with X" or "AI that runs your shop".

**Design guidance from the blueprint, and how we apply it.**

| Blueprint says | Applied |
|---|---|
| §04 Dark-first: `#0B1020`, `#121A2D`, `#19243A`, violet `#7357E8`, blue `#3296F5`; semantic green/amber/red | Adopted as tokens for the landing page. Brass `#C6A66B` is used only where it connects to the opening. |
| §04 Geist or Inter; tabular numerals for KPIs | **Geist Sans + Geist Mono** (via `next/font`) |
| §04 4/8-pt spacing, one token source | Single `@theme` block |
| §05 3D tells the concept: data core with sales, customer, inventory and forecast nodes; **no essential text in canvas** | Landing hero visual; all copy stays in semantic HTML |
| §05 *"low-poly geometry"* | **Conflict:** the master prompt requires photoreal. The opening follows the master prompt. The landing hero's data visual stays abstract and light, so §05's performance intent is kept there. |
| §06 Motion for components; GSAP ScrollTrigger only for marketing sequences; 150–250 ms UI transitions; reduced motion | Adopted |
| §07 WCAG 2.2 AA; status never by colour alone | Adopted (icons and labels with every colour state) |

---

## 3. Repository inspection

### 3.1 Current state

```
apps/web  (Next.js 15.5, React 19, TS, Tailwind v4)
  app/page.tsx            landing (v1 sections + uncommitted prototypes)
  app/login/page.tsx      persona sign-in        ← outside this stage's scope
  app/app/page.tsx        demo dashboard          ← outside this stage's scope
  components/landing/*    v1 sections + prototypes
  lib/                    demo-data, format (en-IN), motion, personas, session, sfx
apps/api                  FastAPI backend, Phase 0 complete ← untouched in this stage
```

**Installed and reusable:** `three 0.170`, `@react-three/fiber 9.8`, `gsap 3.15` (with ScrollTrigger),
`lenis 1.3`, `motion 12` (Framer Motion), `tailwindcss 4.3`.
**Still needed (Phase 2+):** `@react-three/drei`, `@react-three/postprocessing`, `recharts`, Geist font.

### 3.2 Keep / rework / retire

| Item | Verdict | Reason |
|---|---|---|
| `SmoothScroll.tsx` (Lenis + GSAP ticker + gate lock) | **Keep** | Correct pattern; reused for the pinned unlock sequence |
| `lib/format.ts` (₹ en-IN), `lib/demo-data.ts`, `lib/motion.ts` | **Keep** | Consistent demo data for the product preview |
| `SalesChart.tsx` (SVG) | **Replace** with Recharts in the preview | Master prompt prefers Recharts |
| `ShopGate`, `ShopScene` (primitive shop) | **Retire** | Rejected as cartoonish: flat colours, no environment lighting, box geometry |
| `LedgerScene`, `Hero` (ledger), particle hero | **Retire** | Particle effect rejected. The ledger contains religious text (rejected) and is off-brief. |
| `Story`, `ZoomReveal`, `Features`, `Principles`, `Cta` (bright v1) | **Retire** after the new sections land | Replaced by the 10 specified sections. Ideas reused: the pinned timeline and the zoom-reveal preview. |
| `lib/sfx.ts` (synthesized audio) | **Fallback only** | Spec requires realistic recorded audio |
| `/login`, `/app` routes | **Leave untouched, unlinked** | Not to be extended in this stage; "do not destroy working code" |
| Bright tokens in `globals.css` | **Replace** with dark-first tokens (Phase 6) | Master prompt |

### 3.3 Uncommitted work in your tree (yours to keep or discard)

`M globals.css, page.tsx, Hero.tsx, SmoothScroll.tsx` · `D ShatterScene.tsx, nodes.ts` ·
`?? ShopGate.tsx, ShopScene.tsx, LedgerScene.tsx, ledger-labels.ts, lib/sfx.ts`
These are the rejected prototypes. Phase 2 would remove or replace them, with your OK.

---

## 4. Visual direction — Page 1, "The Opening"

**Reference:** your two frames: a weathered brass padlock with a nickel key in warm low light,
and a stone-clad storefront with a corrugated shutter half-raised over a warmly lit interior.

**Tone:** a premium night-time commercial. Late evening on an Indian market street after
closing time. Cool blue ambient street light, one warm sodium/tungsten practical light above the
shop, and the interior glowing amber once the shutter rises. Restrained, quiet, tactile.

**Look rules**
1. **Physically based everything.** HDRI image-based lighting drives every reflection. No unlit or flat-coloured materials.
2. **Real surface detail.** Every surface gets albedo, normal and roughness/AO maps. Brass shows wear and patina; the shutter shows paint scratches and grime streaks.
3. **Cinematic camera.** A 35–50 mm equivalent field of view, shallow depth of field focused on the lock or key, slow eased dolly moves and slight handheld drift. No snappy game-like moves.
4. **Grade.** ACES filmic tone mapping, subtle vignette, fine film grain, gentle bloom on practical lights only.
5. **Authentic, not clichéd, Indian storefront.** Granite or tile-clad pillars, a galvanised rolling shutter painted in faded industrial colour, a backlit acrylic signboard reading **VYAPAR** in clean type with a small Devanagari *व्यापार* line, a tube-light bracket and a ribbed steel step. No religious symbols, no slogans, no stock graphics.

**Colour script**

| Moment | Palette |
|---|---|
| Closed shop | Night navy `#0B1020` sky/ambient · steel greys · brass `#C6A66B` highlight on the lock |
| Unlocking | Same, with a tighter lit pool on the lock |
| Shutter rises | Warm interior amber spills onto the pavement |
| Transition | Amber cools to violet `#7357E8` and blue `#3296F5` as the shop becomes data |
| Landing | Dark-first brand tokens |

---

## 5. Storyboard & timing — Page 1

Scroll segments follow the master prompt exactly and are **fully reversible** (GSAP timeline
scrubbed by a pinned ScrollTrigger; Lenis smooths the wheel but does not hijack it).

| # | Stage | Trigger | Camera / lens | Action | On-screen text | Audio |
|---|---|---|---|---|---|---|
| S1 | Closed shop | Load | Wide 35 mm, eye height, slow drift; DOF on the lock | Key floats in the foreground (soft-focused), catching light | "Every great business has a story." / "Some opportunities are waiting to be unlocked." / **CLICK THE KEY TO BEGIN** | Muted; sound toggle visible |
| S2 | Key travels | **Click** (≈1.6 s, time-based) | Dolly to 50 mm close-up on the lock; focus pulls to the keyhole | Key arcs toward the lock, rolls to orientation, aligns, **inserts** | Fades out | Sound enabled: key jingle/movement, slide-in insertion |
| S3a | Settle | Scroll **0–20 %** | Locked close-up | Key seats fully; tiny recoil | **SCROLL TO UNLOCK** + progress ring | Seat click |
| S3b | Rotate | **20–45 %** | Slow push-in | Key turns 90° clockwise; pins visible through the keyway shadow | — | Ratcheting tumbler clicks |
| S3c | Release | **45–60 %** | Hold | Shackle unlatches: a 2–3 mm lift with spring overshoot | — | Metallic unlock *clack* |
| S3d | Open | **60–75 %** | Pull back slightly | Shackle lifts and swings; lock body drops and swings on the hasp, then is removed from the frame | — | Padlock open, chain/hasp rattle |
| S3e | Shutter | **75–100 %** | Pull back to medium wide | Slats roll individually onto the drum; warm light spills out; pavement reflections | — | Rolling-shutter rattle (scrubbed volume) |
| S4 | Shop open | Continued scroll | Dolly through the doorway at eye height | Interior revealed: shelves, counter, scale, sacks; natural shadows | "Your business is open." → "Now, let's make it intelligent." | Shop ambience (fan hum, distant street) |
| S5 | Transition | Continued scroll | Camera settles centre-aisle | Products emit points; shelves dissolve into a node graph of **Sales · Customers · Inventory · Forecasts**; amber becomes violet/blue | **VYAPAR.AI** · "Unlock the intelligence behind your business." | Soft transition swell |
| → | Landing | Scroll | Canvas hands off to the hero's data visual | Navigation fades in | Hero headline | Ambience fades out |

**Reduced motion:** a static rendered still of the open shop (pre-baked image) with the same
text, plus a "Continue" control. **No WebGL:** the same still. **Mobile:** same story, simplified
(§9).

---

## 6. Visual direction — Page 2, the landing page

**Feel:** a serious international AI product. Calm, spacious, typographic. One accent per
view. Glass only on the navigation bar; no neon.

| Token | Value |
|---|---|
| Background | `#0B1020` |
| Surface / raised | `#121A2D` / `#19243A` |
| Border | `#24304A` (1px) |
| Text / muted | `#E8ECF5` / `#93A0BA` |
| Violet / blue | `#7357E8` / `#3296F5` |
| Brass (sparingly) | `#C6A66B`: the key glyph, thin rules, the "chapter" CTA |
| Semantic | success `#2FBF71` · warning `#F2A93B` · danger `#EF5A5A` (always with icon/label) |
| Type | Geist Sans 400/500/600; display 56–88 px, −2 % tracking; Geist Mono for figures with tabular numerals |
| Grid | 12-col, 1200 px container, 8-pt spacing, 24 px card radius, 1px borders, soft shadows |

**Section concepts (Sections 1–10)**

| § | Section | Visual idea |
|---|---|---|
| 1 | Navigation | Thin bar, blurred on scroll; VYAPAR.AI wordmark with a brass key-notch in the "A"; Platform · Solutions · How It Works · About; **Get Started** |
| 2 | Hero | Headline left; right: a live R3F **data core** of four orbiting node clusters (Sales, Customers, Inventory, Forecasts) joined by flowing edges; hover a node to highlight its card; pointer parallax |
| 3 | Problem | Six "scattered" fragments (receipt, spreadsheet cell, stock tag, review, calendar, chat) drift apart on scroll, then snap into a grid of six problem cards |
| 4 | Ecosystem | 10 capability tiles in a bento layout, each with a **unique mini-composition** (KPI ticker, driver waterfall, RFM matrix, stock cover gauge, interval band, sentiment bars, cited passage, chat bubble, trace graph, decision card) |
| 5 | How it works | Pinned vertical timeline: a line draws between 01→04; each stage swaps a right-hand illustration |
| 6 | Product preview | Full-width dashboard mock in Recharts: 4 KPIs, revenue trend with forecast band, category donut, top products, insights list; **"Demo data"** badge |
| 7 | Intelligence showcase | Tabbed carousel: Sales · Customers · Inventory · Forecasting · Copilot mockups |
| 8 | Copilot | Simulated conversation, "Why did my revenue decline this month?", with streamed answer, evidence chips, a driver chart and recommended actions (Approve / Dismiss). Labelled **"Simulated preview"** |
| 9 | Trust | Four pillars: Reproducible metrics · Traceable evidence · Transparent assumptions · Human-approved actions; a small diagram of the metric registry |
| 10 | Final CTA + footer | "Your business is ready for its next chapter." with a closing brass key motif; footer with section links |

---

## 7. Asset plan (verified CC0 sources)

All Poly Haven assets are **CC0** (no attribution required). Sizes were verified via the Poly Haven API.

| Use | Asset | Source | 1k size |
|---|---|---|---|
| Night lighting & reflections | `cobblestone_street_night` (alt: `modern_buildings_night`, `dresden_station_night`) | Poly Haven HDRI | 1.8 MB `.hdr` |
| Shutter slats | `painted_metal_shutter` (weathered, scratched, corrugated) | Poly Haven texture | 2.0 MB |
| Shutter alt / grime | `rusted_shutter` | Poly Haven | 2.9 MB |
| Pillars | `granite_tile` / `granite_wall` | Poly Haven | 2.0–2.7 MB |
| Pavement / step | `concrete_pavement` / `brushed_concrete` | Poly Haven | 2.5–2.9 MB |
| Wall above shop | `grey_plaster` | Poly Haven | 1.4 MB |
| Brass & steel micro-detail | `metal_plate` roughness/normal, tinted as brass `#C6A66B` (metalness 1) | Poly Haven | 2.5 MB |

**Optimisation:** convert to **KTX2/Basis** (or WebP), which is about 60–75 % smaller and GPU-compressed.
Desktop ≈ 6–8 MB total textures; mobile uses 512 px variants ≈ 2–3 MB.

**Models (custom-built in code, no low-poly):**
- **Key:** a flat pin-tumbler key from an extruded bevelled 2D profile with real bitting cuts, a stamped bow with a hole, nickel-silver PBR.
- **Padlock:** a heavy rectangular brass body (rounded, bevelled) with an engraved face (normal-map lettering, no brand names), a keyway cylinder with visible plug and pins, and a hardened-steel shackle (tube along a U-path) with a real latch notch.
- **Shutter:** ~40 **individual instanced slats** with a curved interlocking profile, side guide rails, a bottom bar with handle and hasp, and a drum housing the slats coil into.
- **Storefront:** clad pillars, beam, a backlit signboard (emissive acrylic, extruded letters), a tube-light bracket and a step.
- **Interior:** steel shelving, instanced packaged goods with **generic, unbranded** label textures generated procedurally, a glass-top counter, a weighing scale and grain sacks.

*Option:* if you prefer, a licensed high-detail padlock/key from Sketchfab (CC-BY, attribution in the footer) can replace the custom models. It needs your Sketchfab login to download.

---

## 8. Audio plan

Realistic recordings, not synthesis. They start **muted** and are enabled on the key click. A visible toggle sits in the top-right corner.

| Cue | Sync point | Suggested search terms (Pixabay SFX / Freesound CC0) |
|---|---|---|
| Key movement | S2 start | "keys jingle single key handling" |
| Key insertion | S2 end | "key insert padlock" |
| Lock rotation | 20–45 % (scrubbed) | "key turn lock tumbler click" |
| Metallic unlock | 45–60 % | "padlock unlock click" |
| Padlock opening | 60–75 % | "padlock open shackle" |
| Rolling shutter | 75–100 % (volume follows scroll velocity) | "rolling shutter opening metal" |
| Shop ambience | S4 loop | "small shop ambience fan hum" |
| Transition | S5 | "soft cinematic swell whoosh" |

Implementation: `AudioController` (Web Audio). It decodes about 8 short `.m4a`/`.ogg` files (~600 KB total), plays scroll-scrubbed cues once per direction, uses a looped ambience with a crossfade, and silences everything when the tab is hidden. The synthesized `sfx.ts` stays as a no-download fallback.

---

## 9. Responsiveness & performance budget

| Tier | 3D | Textures | Post-FX | Target |
|---|---|---|---|---|
| Desktop | Full scene, shadows, DOF, bloom, SMAA | 1k (2k for hero objects) | DOF + bloom + vignette + grain | 60 fps on Apple M1 / RTX-class |
| Tablet | Full scene, no DOF, fewer instances | 1k | Bloom + vignette | 45–60 fps |
| Mobile | Simplified: fewer slats, baked shadows, fewer interior items | 512 px | Vignette only | 30+ fps mid-range Android; tap = click, swipe = scroll |
| Reduced motion / no WebGL | Static still + text | — | — | — |

- The 3D bundle is lazy-loaded behind a branded loader. Landing-page JS is kept separate from the three.js chunk.
- DPR is capped at 1.5–1.75, and rendering pauses off-screen and on hidden tabs.
- Lighthouse targets for the landing page: Performance ≥ 85 desktop, Accessibility ≥ 95.

---

## 10. Proposed architecture (adapted to the repo)

```
apps/web/
  app/page.tsx                      <CinematicOpening/> then <LandingPage/>
  components/opening/
    CinematicOpening.tsx            pinned section, overlays, sound toggle, a11y fallback
    StorefrontScene.tsx             Canvas, environment, camera rig, post-FX
    KeyModel.tsx · LockModel.tsx · ShutterModel.tsx · Storefront.tsx · ShopInterior.tsx
    DataTransition.tsx              shelves → node graph
    useOpeningTimeline.ts           GSAP timeline + ScrollTrigger mapping (0–20–45–60–75–100)
    AudioController.ts
  components/landing/
    LandingPage.tsx · Navigation.tsx · HeroSection.tsx · DataCore.tsx · ProblemSection.tsx
    IntelligenceSection.tsx · HowItWorksSection.tsx · ProductPreviewSection.tsx
    ShowcaseSection.tsx · CopilotPreviewSection.tsx · TrustSection.tsx · FinalCta.tsx · Footer.tsx
  public/assets/{hdri,textures,audio}/   CC0 assets (+ LICENSES.md)
```

---

## 11. Risks & mitigations

| Risk | Mitigation |
|---|---|
| "Photoreal" in a real-time browser has a ceiling below offline renders | HDRI + PBR + DOF + filmic grade; hero objects get 2k maps; review stills at the end of Phase 2 before any animation |
| Procedural product labels may look fake | Keep labels small, out of focus, under warm light; add a slight motion blur on the camera move |
| Asset weight on mobile | KTX2, 512 px tier, lazy loading, a static fallback |
| Scroll-scrub audio can stutter | Trigger cues at thresholds (direction-aware) instead of scrubbing waveforms; only the shutter volume follows velocity |
| Blueprint "low-poly" vs master prompt "photoreal" | Master prompt wins for the opening; the landing data-core stays light |
| Existing `/login`, `/app` routes conflict with the "two pages only" rule | Left as-is and unlinked; your call (§12) |

---

## 12. Decisions needed before Phase 2

1. **Audio:** (a) you download ~8 CC0 clips using the search terms in §8, or (b) I source Pixabay CC0 clips myself, or (c) use the synthesized fallback for now.
2. **Models:** custom-built key and padlock in code (recommended) **or** you supply a Sketchfab padlock/key file.
3. **Prototype cleanup:** OK to remove `ShopGate`, `ShopScene`, `LedgerScene`, `ledger-labels`, the bright v1 landing sections and the old `Hero` as each replacement lands?
4. **`/login` and `/app`:** leave them untouched and unlinked (recommended), or remove them?
5. **HDRI mood:** `cobblestone_street_night` (warm old street, recommended), `modern_buildings_night` (cooler, urban) or `dresden_station_night`.

---

## 13. Acceptance check for Phase 2 (what you will review)

- Still frames (desktop and mobile) of the **closed shop** at night: the key in the foreground, the lock in focus.
- Close-ups of the **key**, the **padlock** (engraving, keyway, shackle) and the **shutter slats** (individual, weathered).
- No cartoon look: every material is PBR and lit by the HDRI.
- Frame rate and asset sizes measured and reported.
- No interaction or animation yet (that is Phase 3).
