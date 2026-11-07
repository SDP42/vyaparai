# Design system

## Direction: "Bahi-Khata"

Most AI dashboards look alike: midnight navy, violet-to-blue gradients, glass cards. Vyapar
deliberately avoids that. Its visual language comes from the **bahi-khata**, the red cloth-bound
ledger Indian traders open on Diwali with *शुभ लाभ* ("auspicious profit") written on the first page.

| Token | Hex | Use |
|---|---|---|
| `ink` / `ink-2` / `ink-3` | `#14110F` / `#1C1815` / `#27211D` | Warm near-black surfaces (not blue-black) |
| `line` | `#3A322B` | Borders, rules |
| `paper` / `paper-2` | `#F3ECE0` / `#E7DCCB` | Primary text, light surfaces: ledger paper |
| `muted` | `#9A8F80` | Secondary text |
| `sindoor` | `#D9362B` | Brand, negative change, primary CTA (the ledger's red cloth) |
| `haldi` | `#E9A426` | Highlights, forecasts, focus ring (turmeric) |
| `mor` | `#1F8A7F` | Positive change, success (peacock teal) |
| `neel` | `#3C4FB8` | Rare accent (indigo dye) |

Status is never shown by colour alone: deltas also carry ▲/▼ and screen-reader text.

## Type

| Role | Font | Why |
|---|---|---|
| Display / UI | **Bricolage Grotesque** | Characterful grotesque with optical sizes; not the default Inter look |
| Editorial accent | **Instrument Serif** (italic) | Hand-written ledger feel for emphasis words |
| Numbers / labels | **JetBrains Mono** + `tabular-nums` | Aligned columns of figures |
| Devanagari | **Tiro Devanagari Hindi** | व्यापार, स्वागत, शुभ लाभ |

## Texture

- A subtle animated **film grain** overlay (disabled for reduced motion) adds a printed feel.
- **Ledger rules** (horizontal lines plus a red margin line) appear behind the principles section and the login panel.

## Motion

| Where | Tool | Rule |
|---|---|---|
| Smooth scroll | Lenis | Landing page only; app pages use native scroll |
| Scroll scenes | GSAP ScrollTrigger | Scrubbed, pinned sections; short and never trapping |
| 3D hero | React Three Fiber, custom shader | One draw call; DPR capped at 1.75; paused off-screen |
| UI transitions | Motion | 150–250 ms for UI; staggered entrance on first load only |
| Reduced motion | all | Hero renders the final state statically; horizontal story becomes vertical; marquee/grain stop |

## Landing page narrative

1. **Hero (460vh, sticky):** "VYAPAR / व्यापार" is drawn as ~16k particles sampled from the real
   fonts. On scroll it **shatters** (staggered, with a mid-flight burst in haldi) and **re-forms**
   into a 3D data core: a red core sphere, four domain nodes (Sales, Customers, Inventory, Forecast),
   connecting filaments and an orbit ring. The camera **zooms** in as it assembles, and HTML labels
   track the nodes via 3D→screen projection. Copy: *"Every shop is a story told in numbers. / We take
   it apart, entry by entry. / …and rebuild it as decisions."*
2. **Story (pinned horizontal scroll):** Data enters → gets organised → insight → you approve the action.
3. **Zoom-through:** "Every rupee, explained." scales past the camera while the product dashboard
   scales up from a tilted card to full frame.
4. **Bento features** with cursor spotlight and micro-visuals.
5. **Ledger marquee + principles**, with strike-lines drawn on scroll.
6. **CTA:** *शुभ लाभ* with a magnetic "Choose a persona" button.

## References studied

React Bits (split-text, particles, spotlight cards), shadcn/ui (accessible primitives),
Aceternity/Magic UI scroll patterns, three.js particle morph techniques. Patterns are
re-implemented in-repo, not copied.
