"""Fetch link sources that are due. Schedule it, for example every 15 minutes:

    */15 * * * *  cd /path/to/apps/api && uv run python -m app.import_runner

Each source has its own schedule (hourly or daily), so running this often is safe. A source that
fails five times in a row is paused and shows a message in the app.
"""

import json

from app.db.session import get_engine
from app.services.sources import run_due


def main() -> None:
    print(json.dumps({"checked": run_due(get_engine())}))


if __name__ == "__main__":
    main()
