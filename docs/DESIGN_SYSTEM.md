# Design system

## Direction: "Bahi-Khata"

Most AI dashboards look alike: dark navy, violet-to-blue gradients, glass cards. Vyapar deliberately
avoids that. The look is a **warm, bright ledger**: cream paper, near-black ink, a sindoor-red accent
and haldi (turmeric) yellow highlights, with a teal for good news. No religious symbols or phrases.

> The blueprint (§04) suggested dark navy + violet. The owner chose the bright warm direction instead
> (2026-11-07); this document supersedes §04 for colour.

| Token | Hex | Use |
|---|---|---|
| `canvas` | `#F6EFE2` | Page background (ledger paper) |
| `surface` / `surface-2` | `#FFFAF1` / `#EFE4D0` | Cards, raised areas |
| `line` | `#DCCFB8` | Borders and rules |
| `fg` / `ink` | `#1B1612` | Text and dark buttons |
| `muted` | `#776A59` | Secondary text |
| `sindoor` / `sindoor-deep` | `#D9362B` / `#A3241C` | Accent, negative change, hover on dark buttons |
| `haldi` / `haldi-deep` | `#F2A71B` / `#9C5D00` | Highlights, warnings, focus colour |
| `mor` | `#0F7A6F` | Positive change, success |
| `neel` | `#3346A8` | Rare accent (information) |

Status is never shown by colour alone: deltas always carry ▲/▼ and screen-reader text.
All tokens live in `apps/web/app/globals.css` (`@theme`); components never hard-code colours.

## Type

| Role | Font |
|---|---|
| Display and UI | **Bricolage Grotesque** |
| Editorial accent (italic emphasis words) | **Instrument Serif** |
| Figures, labels, code | **JetBrains Mono** with tabular numerals |
| Devanagari ("व्यापार") | **Tiro Devanagari Hindi** |

Indian number formatting everywhere: ₹12,34,567 and compact ₹4.2L / ₹1.3Cr (`lib/format.ts`).

## Motion

| Where | Tool | Rule |
|---|---|---|
| Smooth scroll | Lenis | Marketing page only; the app uses native scroll |
| Scroll scenes | GSAP ScrollTrigger | Scrubbed, pinned, reversible; never trap scrolling |
| 3D opening | React Three Fiber | PBR + HDRI, depth of field, bloom; low-power tier drops post-effects |
| UI transitions | Motion | 150–300 ms; entrances play on first load only |
| Reduced motion | all | Opening is skipped; scenes become static; marquee and grain stop |

## The marketing site

### 1. Cinematic opening (`components/opening/`)
A closed Indian shopfront at night. Click the key and it flies into the brass padlock. Then **scroll
drives a paused GSAP timeline**: settle (0–20 %) → turn clockwise (20–45 %) → release (45–60 %) →
padlock opens and falls (60–75 %) → shutter rises slat by slat (75–100 %) → the camera walks in.
Everything is reversible. Realism comes from a CC0 night-street HDRI, CC0 PBR textures (painted steel,
plaster, concrete), physically-based brass/nickel/steel, soft shadows, auto-focus depth of field,
bloom on the practical lights, vignette and grain. Sounds are synthesized and fire on scroll
thresholds; a shop ambience loops inside. Captions: "Your business is open." → "Now, let's make it
intelligent." → fade to cream → **VYAPAR.ai** → hero. Assets and licences: `public/assets/opening/`.

### 2. Landing page (`components/landing/`)
Simple hero ("Your business deserves more than *guesswork.*") with the product card, then a pinned
horizontal **story** (data enters → organised → insight → you approve), a **zoom-through** product
reveal, a **feature bento**, a **ledger marquee with principles**, and a closing call to action.

## The product app (`app/app/`)
Same tokens, calmer motion. Tables become stacked summaries on phones; every chart has a text
alternative; every comparison states its own date range.

## References studied
React Bits (split-text, spotlight cards), shadcn/ui (accessible primitives), GSAP and Lenis
documentation, three.js PBR and post-processing examples. Patterns are re-implemented in-repo, not copied.
