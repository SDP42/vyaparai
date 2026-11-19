# scripts

Developer and operations utilities. Run them from the repository root unless a line says otherwise.

| Script | What it does | How to run |
|---|---|---|
| `generate_demo_data.py` | Writes the reproducible synthetic sample shop exports (clean and deliberately messy) to `data/sample/` | `python scripts/generate_demo_data.py` |
| `eval_voice.py` | Smoke test of the voice pipeline on synthetic macOS speech: transcript, intent reached, seconds, invented words on silence. Not a measure of real shopkeepers | `cd apps/api && .venv/bin/python ../../scripts/eval_voice.py` |
