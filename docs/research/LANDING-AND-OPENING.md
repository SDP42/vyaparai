# The cloth opening and the landing page: techniques and a recommended structure

Research notes, 2026-11-12. **[V]** = read on a fetched page or source file this session. **[U]** = general
knowledge, not verified. **[R]** = my recommendation; numbers are starting points to tune by eye, not measured.
Context: the current opening is GSAP + SVG + CSS (cloth drops in twelve strips), and the site already uses
GSAP ScrollTrigger, Lenis and Motion. three.js is not a dependency today.

## Part A. A realistic cloth, a ribbon, a cut

### A1. How the reference simulations work

- **Classic three.js cloth example** (`webgl_animation_cloth` + `examples/js/Cloth.js`, read at tag r100; the
  example is gone from the current site, its URL returns 404) [V]: a 10 x 10 segment particle grid, rest distance
  25, mass 0.1. Verlet step `new = pos + (pos - prev) * 0.97 + accel * dt^2` (`DAMPING = 0.03`), fixed
  `TIMESTEP = 18 ms`, gravity `981 * 1.4`. Structural constraints only (shear is commented out), each solved by
  moving both ends half the error, **one pass per frame**, which is why it looks stretchy. Pins are top-row
  indices reset after every step; one formation is literally `pins = []; // cut the rope ;)`, so emptying the
  pin list drops the cloth. Wind force per vertex = normal x (normal . wind), varied with sines. Normals are
  recomputed each frame; Lambert material, one directional light, 1024 shadow map.
- **Current official example** (`webgpu_compute_cloth`) [V]: 30 x 30 segments (961 vertices, 3,660 springs with
  both diagonals), stiffness 0.2, dampening 0.99, **360 steps per second**, noise wind, pinned vertices skip the
  compute pass, normals from tangent x bitangent. `MeshPhysicalNodeMaterial` with `sheen 1.0`,
  `sheenRoughness 0.5`, white sheen colour, double-sided, lit only by an HDR environment. **No WebGL fallback**
  (a TODO in the source), so it is not safe as the only path.
- **Tearing** [V, Tuts+ verlet tutorial]: each link has a tear distance; stretched past it, the link is deleted.
  The author uses 3 relaxation passes and re-pins after each. Cutting is the same thing done on purpose.
- **Pre-baked alternative** [V, Lusion's Awwwards case study]: cloth simulated in Houdini and shipped as data
  (about 220 kB gzipped; 4,096 vertices desktop, 1,024 mobile). Looks perfect, but cannot react to where the
  visitor cuts, and Houdini is not free software.

### A2. Recommendation: CPU verlet in three.js, as an enhancement over the existing opening [R]

A three-second effect with ~1,500 particles does not need GPU compute; plain JavaScript runs it wherever
WebGL runs. Keep today's SVG opening as the fallback.

| Setting | Phone | Desktop | Why |
|---|---|---|---|
| Cloth grid | 28 x 20 segments | 48 x 32 | Folds need ~5 particles per fold; more is wasted on a short effect |
| Constraints | structural + shear + bend (skip-one neighbour) | same | Shear stops diamond collapse; bend gives cotton its body |
| Solver passes | 3 | 4-5 | Cotton barely stretches; fewer passes reads as rubber |
| Time step | fixed 1/60 s, max 2 catch-up steps | same | Verlet is unstable with a variable step |
| Damping | 0.02-0.03 per step | same | The official value is 0.03 [V]; less than 0.01 never settles |
| Wind | low-frequency noise along the normal, small | same | A slow breath before the cut; a brief gust as it falls |
| Pixel ratio | min(devicePixelRatio, 1.5) | min(dpr, 2) | Physical materials cost per pixel [V, three.js docs] |
| Shadows | none; a soft gradient under the hem | PCF soft, 1024 map, one light | A shadow map on a phone is the first thing to cut |

- **Hanging.** Pin every third or fourth top-row particle, slightly closer together than rest length, so the
  cloth hangs in scallops. Run ~60 steps before the first painted frame so it is already at rest.
- **The ribbon.** Its own strip (2 x ~40 particles) across the cloth, pinned at both ends, plus a row of *cinch*
  constraints: short links (rest length ~0.6 of normal) between cloth particles at ribbon height, which makes
  the cloth look tied. Build the ribbon mesh as two halves meeting at the cut, so no triangle spans it.
- **The cut.** When the scissors close: (1) delete the ribbon constraints crossing the cut; (2) delete cinch
  constraints outward from the cut over ~200 ms, so the gather relaxes; (3) give the two ribbon ends a small
  opposite impulse, let them swing, then unpin them; (4) after ~300 ms release the top pins from the centre
  outward, 30-60 ms apart; (5) when every particle is below the viewport, stop the loop, dispose geometry,
  materials and renderer, remove the canvas. Deleting a constraint = removing it from the solver's array.
- **Fabric materials** (three.js `MeshPhysicalMaterial`; sheen is documented as "for representing cloth and
  fabric", anisotropy for directional highlights; the docs say to always supply an environment map [V]):

| | Cotton cloth | Satin ribbon |
|---|---|---|
| roughness / metalness | 0.9-1.0 / 0 | 0.3-0.4 / 0 |
| sheen, sheenRoughness | 0.4-0.6, 0.8-0.9 | 1.0, 0.25-0.35 |
| sheenColor | base colour, lightened | pale tint of the red |
| anisotropy | 0 | 0.6-0.8, rotated to run along the ribbon |
| normal map (both DoubleSide) | plain weave, repeat 12-20, scale 0.3-0.5 | fine satin weave or none |

- **Light** [R]: one warm directional key from upper left (the only shadow caster), a dim hemisphere fill, and
  a procedural environment (three.js ships `RoomEnvironment`, so no HDR download [U]); neutral tone mapping.
- **Textures.** Generate the weave normal map on a canvas (no asset, keeps the "drawn in code" rule), or use one
  1K CC0 fabric set and list it in LICENSES.md. Poly Haven: "Our assets are all licensed as CC0", no credit
  needed [V]. ambientCG: "Creative Commons CC0 1.0 Universal License" [V]. **three.js is MIT** [V, LICENSE file].
- **Loading and fallbacks** [R]: import three.js dynamically, only when the opening will show. Fall back to the
  SVG opening when WebGL context creation fails, on `saveData`, on low memory or core counts, or if the first
  30 frames average under ~40 fps. Under `prefers-reduced-motion`: no opening, as now. Skip, Esc, tap and Enter
  keep working; the scissors stay a real focusable button; pause on `visibilitychange`.
- **Not verified:** none of the grid, pass or material numbers were run on a device; three.js bundle cost in
  this app; WebGPU availability on our users' Android phones.

### A3. Cloth done well (to study, not copy)

| What | URL | Note |
|---|---|---|
| three.js WebGPU compute cloth | https://threejs.org/examples/webgpu_compute_cloth.html | Sheen fabric, source read [V] |
| Lusion (Awwwards Site of the Month, May 2019) | https://lusion.co | Pre-baked Houdini cloth; case study read [V], site not opened |
| GPU verlet cloth with matcap, by Jordan | https://gl.jojo.ninja/experiments/verlet-matcap/ | Listed by offscreencanvas.com [V]; not opened |
| Venice Biennale HK 2017 hero cloth | http://2017.venicebiennale.hk/#hk-exhibition | Noise wind, zero-mass anchors; listed there [V]; not opened |
| Oimo cloth | https://oimo.io/works/cloth/ | Listed there [V]; not opened |
| Tearable verlet cloth, Michal Zalobny | https://www.cloudofoz.com/verlet-test/ | Custom WebGL2; described by 80.lv [V]; not opened |

## Part B. Professional, not generic

### B1. What reads as generic

A script that scored 1,590 Show HN pages for common AI-era patterns found 22% with four or more [V,
adriankrebs.ch/blog/design-slop]. The patterns it counts: Inter for everything; a centred hero; **a serif
italic accent word in the headline**; a badge above the H1; purple palettes; permanent dark mode with grey
text; gradients and coloured glows everywhere; identical icon-on-top feature cards; numbered 1-2-3 steps; stat
banner rows; all-caps section labels; emoji icons; glassmorphism. None is wrong alone; several together are
the tell. **Check ours:** the hero has an italic accent word ("*guesswork.*"), and the page has a numbered
story and a feature bento. Keep at most one of these habits.

### B2. What reads as made by someone

- **Type:** two families at most; one scale (ratio ~1.2 on phones, 1.25-1.333 desktop); body 16-18 px at
  1.5-1.6 line height; tight headlines (1.0-1.1); 45-75 characters per line; all spacing from one 4 or 8 px
  step [U]. Devanagari needs more line height than Latin.
- **Restraint:** Linear is described as black, white and greys with one accent, where "every element serves a
  purpose" [U, search summaries]. One accent, one signature moment (ours is the cloth), the rest quiet.
- **Real product:** Linear's hero is a product screen and nearly every section pairs a heading with a real
  interface view [V, linear.app]. Apple product pages pin and scrub one object at a time; Stripe keeps one
  animated gradient over a strict grid; Vercel is near-monochrome with tight type [U, not fetched]. Use real
  screenshots of our app with the sample shop's numbers, in Hindi and English, in a phone frame.
- **Specific copy:** Linear names the thing and the audience: "The product development system for teams and
  agents" [V]. Ours should name a shop moment and a number ("Kal Rs 4,200 udhaar wapas aana hai").
- **Honest proof:** we have no customers. Show what is checkable (free open models, data stays with you, what
  it will not do). Never invent logos, quotes or user counts.
- **Grid and space:** 12 columns, section padding 96-160 px desktop and 56-80 px phone, a few shared edges [U].

### B3. Scroll transformations: when each helps

Parallax, zoom and scroll-linked movement of elements other than the content are named triggers for
vestibular problems; the advice is to remove non-essential motion under `prefers-reduced-motion` [V, web.dev].
CSS scroll-driven animations (`animation-timeline: scroll() / view()`) can run off the main thread when they
animate `transform`, `opacity` or `clip-path`; the Chrome page shows support from Chrome/Edge 115, with Safari
26 and Firefox 159 badges [V, developer.chrome.com; check caniuse before relying on it]. GSAP stays the fallback.

| Type | Use it when | It hurts when | Verdict here |
|---|---|---|---|
| Pinned scrub section | One idea unfolds in 3-4 steps | Pin lasts over ~3 screens; touch scroll feels trapped | One only (how it works) |
| Clip-path / mask reveal | Revealing a screenshot or the shop | Used on every block | Yes, for product shots |
| Text split / scramble | One headline, once | Body copy; Devanagari (splitting breaks conjuncts) | Hero line only, split by word |
| Horizontal scroll | Content is truly a sequence | On phones; with keyboard; with Lenis fighting touch | Replace with vertical steps on phones |
| Parallax depth | Subtle, under 10% offset | Large offsets; motion sickness | Sparingly; off under reduced motion |
| Sticky stacking cards | 3-5 parallel items of equal weight | Tall cards on short screens | Yes, for personas |
| Number count-up | A real number the reader should register | Fake stats; repeats on every scroll | Only inside real screenshots; play once |
| Marquee | A long list where order does not matter | Carries information people must read | Keep one, pausable, stopped under reduced motion |
| Morphing shapes, 3D card tilt | A shape carries meaning (bars becoming a line) | Decoration; touch devices; readability | Skip both |
| View transitions | Landing to app sign-in, same element persists | Cross-document support varies [U] | Optional, progressive |

Rules [R]: animate only transform and opacity; every scene must read correctly as a static page; nothing
blocks scrolling; total page weight and a Lighthouse run on a mid-range Android phone decide what stays.

### B4. Recommended structure for this landing page

| # | Section | What is shown | Transformation | Copy angle |
|---|---|---|---|---|
| 0 | Opening | Closed shop under cloth | The cut (Part A); skipped on repeat visits and reduced motion | None. One caption: "Cut the ribbon" |
| 1 | Hero | Headline left, a phone with the real Today screen right | Headline words rise once; no scroll effect | The shop morning: "Open the shutter knowing three things." Sub-line says who it is for: kirana, garment, medical, general stores. One button: try the sample shop |
| 2 | Proof | A plain strip of checkable facts | None | "Runs on free, open software. Your data stays with you. Hindi, Hinglish, English." No logos, no invented numbers |
| 3 | How it works | Your sales file, then three numbers, then one action you approve | The one pinned scrub on desktop; three stacked steps on phones | "Bring what you already have: a sales file, bill photos, your udhaar book." Stress that nothing is sent without you |
| 4 | Features | 4-5 real screenshots: udhaar chase list, order advice, bill photo to costs, forecast with range, alerts | Clip-path reveal per screenshot as it enters; uneven sizes, not identical cards | One sentence each, written as an outcome with a number from the sample shop |
| 5 | Personas | Owner, manager, accountant, analyst, counter staff | Sticky stacking cards; plain list on phones under 700 px tall | "Everyone sees their part." Counter staff see their own sales, not margins |
| 6 | Voice | A recorded real exchange: spoken Hinglish question, the confirm-the-words step, the answer | Waveform draws with scroll once; a play button for audio, never autoplay | "Bol kar poochho." Show the confirmation step as the feature, not a caveat |
| 7 | Trust and limits | What it does not do | None; calm two-column text | "It advises; you decide." No auto messages, no payments, not a billing or GST filing app, forecasts come with a range and can be wrong |
| 8 | Call to action | One button, the sample shop, one line on setup | None, or the cloth colour returns as a quiet band | "See it with a sample shop. No sign-up." |

Changes from today's page: the horizontal story becomes the one pinned scene (vertical on phones); the
zoom-through goes (a vestibular trigger that duplicates the hero); the principles marquee becomes the static
trust section; personas and voice get their own sections.

## Sources

three.js repo (LICENSE; `examples/js/Cloth.js`, `webgl_animation_cloth.html` at r100; `webgpu_compute_cloth.html`
on dev) · threejs.org/docs/pages/MeshPhysicalMaterial.html · code.tutsplus.com (tearable cloth with verlet) ·
awwwards.com Lusion case study · offscreencanvas.com/issues/cloth-simulation-in-threejs · 80.lv tearable cloth
article · polyhaven.com/license · docs.ambientcg.com/license · adriankrebs.ch/blog/design-slop · linear.app ·
web.dev/articles/prefers-reduced-motion · developer.chrome.com/docs/css-ui/scroll-driven-animations.
**Not fetched (general knowledge only):** Stripe, Vercel, Arc, Apple product pages and individual Awwwards
winners other than Lusion; the Codrops cannon.js cloth tutorial returned 403.
