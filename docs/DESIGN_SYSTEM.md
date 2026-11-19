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
| `muted` | `#6A5E4E` | Secondary text (5.5:1 on canvas) |
| `sindoor` / `sindoor-deep` | `#BF2B21` / `#A3241C` | Accent, negative change, hover on dark buttons (4.9:1 on canvas, 4.5:1 on `surface-2`) |
| `haldi` / `haldi-deep` | `#F2A71B` / `#8C5400` | Highlights and fills; `haldi-deep` for small text |
| `mor` | `#0C6F64` | Positive change, success |
| `neel` | `#3346A8` | Rare accent (information) |

The four text colours were darkened on 2026-11-11 to pass WCAG AA at small sizes ([ACCESSIBILITY](ACCESSIBILITY.md)). `haldi` itself is a fill, never text.

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
| Opening | three.js (fallback: GSAP, SVG, CSS) | A simulated cloth tied with a ribbon; draggable scissors; the cloth falls under gravity. No images, models or sounds |
| UI transitions | Motion | 150–300 ms; entrances play on first load only |
| Reduced motion | all | Opening is skipped; scenes become static; marquee and grain stop |

## The marketing site

### 1. The closed shop (`components/opening/ClothOpening.tsx`)
The shop is closed. A woven cotton cloth in turmeric yellow hangs over the front, tied with a red satin ribbon and
bow, and a paper tag reads "vyapar.ai". A pair of scissors rests beside the ribbon with a dotted "cut here" line
across it. **Drag the scissors to the line** (or tap them, or press Enter): the blades snip, the lower length of
ribbon and the scissors fall, the bow and tag slip down, and the cloth lets go in twelve strips from the middle
outward, each slightly out of step, leaving the page to scroll. The hero text starts after the drop.

It is drawn entirely in code. The weave is two generated noise tiles (warp and weft threads) under three layers of
soft folds of different widths so the pattern never visibly repeats; the top is gathered and the hem stitched. The
ribbon is a CSS gradient band split at the cut line; the bow is an SVG with satin gradients and a drop shadow.
Once per visit (`?opening` shows it again), Esc or "Skip" opens it at once, and under reduced motion it is not
shown. On short screens (below 520 px high) the bow is smaller and the caption moves out of the way of the cut line.

### 2. Landing page (`components/landing/`)
Simple hero ("Your business deserves more than *guesswork.*") with the product card (whose layout follows its own
width, so numbers never clip), then a pinned horizontal **story** (data enters → organised → insight → you approve),
a **zoom-through** product reveal, a **feature bento** that describes what the product really does (no roadmap
labels), a **ledger marquee with principles**, and a closing call to action to try the sample shop.

## The product app (`app/app/`)
Same tokens, calmer motion. Tables become stacked summaries on phones; every chart has a text
alternative; every comparison states its own date range.

## References studied
React Bits (split-text, spotlight cards), shadcn/ui (accessible primitives), GSAP and Lenis
documentation, three.js PBR and post-processing examples. Patterns are re-implemented in-repo, not copied.
