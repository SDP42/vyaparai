# LinkedIn kit

Everything needed to announce Vyapar AI: the post, images and the full project document.

| Path | What it is |
|---|---|
| [POST.md](POST.md) | The post text (about 2,400 characters) and the suggested image order |
| [Vyapar-AI-Project-Document.pdf](Vyapar-AI-Project-Document.pdf) | The complete project document, 28 A4 pages with 13 figures; also shared on [Google Drive](https://drive.google.com/drive/folders/1FtSuD1PuTelw9huB_Uoz9cdQK3vUowm7?usp=sharing) |
| [showcase/](showcase/) | Four 1080x1350 slides (cover, ask, agents, opening), rendered at 2x |
| [images/](images/) | 25 screenshots of the running prototype (desktop at 2x, phone at 390 px wide), the repository summary card and three GitHub pages (26–28) |
| [repo-summary-card.html](repo-summary-card.html) | Source of `images/00-repo-summary.png`, built from the real Git history |

## How the images are made

- Screenshots: start the API and web dev servers, then `node scripts/capture-screens.mjs` (all) or
  `node scripts/capture-screens.mjs landing` (landing only). It drives headless Chrome over the DevTools
  protocol and signs in with a sample account, so it needs `DEMO_LOGIN_ENABLED=true` in development.
- Showcase slides: open `showcase/slides.html#cover` (or `#ask`, `#agents`, `#opening`) in headless Chrome
  at 1080x1350 with `--force-device-scale-factor=2 --allow-file-access-from-files`.
- Repository card: render `repo-summary-card.html` at 1200x675, scale factor 2.

All data shown is the sample shop (Kulkarni General Stores); no real customer appears.
