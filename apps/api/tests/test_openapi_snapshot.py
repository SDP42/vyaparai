"""openapi.json (which the web app's generated types come from) must match the API as it is now."""

import json
from pathlib import Path

from app.main import create_app


def test_openapi_json_is_up_to_date() -> None:
    saved = json.loads((Path(__file__).resolve().parents[1] / "openapi.json").read_text())
    fresh = json.loads(json.dumps(create_app().openapi(), sort_keys=True, ensure_ascii=False))
    assert saved == fresh, (
        "API changed: run `python scripts/export_openapi.py` and `npm run gen:api`"
    )
