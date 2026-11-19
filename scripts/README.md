# scripts

Developer and operations utilities. Run them from the repository root unless a line says otherwise.

| Script | What it does | How to run |
|---|---|---|
| `generate_demo_data.py` | Writes the reproducible synthetic sample shop exports (clean and deliberately messy) to `data/sample/` | `python scripts/generate_demo_data.py` |
| `eval_voice.py` | Smoke test of the voice pipeline on synthetic macOS speech: transcript, intent reached, seconds, invented words on silence. Not a measure of real shopkeepers | `cd apps/api && .venv/bin/python ../../scripts/eval_voice.py` |
| `a11y-audit.js` | Accessibility basics without a library: names, labels, alt text, headings, ids, tabindex, touch targets, contrast. Not a screen-reader test | Paste into the browser console on any page |
| `backup.sh` | Dumps PostgreSQL and archives uploaded files, keeping the 14 newest; copy them off the machine | `./scripts/backup.sh [dir]` |
| `restore-check.sh` | Restores a dump into a throw-away database and counts users, workspaces and orders | `./scripts/restore-check.sh backups/db-<time>.dump` |
| `capture-screens.mjs` | Screenshots of the running prototype with headless Chrome over the DevTools protocol, into `docs/linkedin/images` | Dev servers running, then `node scripts/capture-screens.mjs [landing]` |
