"""Rebuild stale forecasts once. Schedule it, for example every hour:

    0 * * * *  cd /path/to/apps/api && uv run python -m app.forecast_runner

A workspace is only rebuilt when new sales arrived after its active forecast, and at most once
every 20 hours, so running this often is safe.
"""

import json

from app.db.session import get_session_factory
from app.services.forecasting.service import run_stale


def main() -> None:
    with get_session_factory()() as db:
        results = run_stale(db)
    print(json.dumps({"rebuilt": results}))


if __name__ == "__main__":
    main()
