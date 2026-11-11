"""Write the API's OpenAPI description to openapi.json (the web app's types are generated from it).

cd apps/api && .venv/bin/python scripts/export_openapi.py
cd apps/web && npm run gen:api
"""

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import create_app

logging.disable(logging.CRITICAL)
OUT = Path(__file__).resolve().parents[1] / "openapi.json"
OUT.write_text(
    json.dumps(create_app().openapi(), indent=1, sort_keys=True, ensure_ascii=False) + "\n"
)
print(f"wrote {OUT}")
