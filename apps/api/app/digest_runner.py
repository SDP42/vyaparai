"""Send due owner digests once. Schedule it, for example every 15 minutes:

    */15 * * * *  cd /path/to/apps/api && uv run python -m app.digest_runner

Each digest is sent at most once per local day, so running it often is safe.
"""

import json

from app.db.session import get_session_factory
from app.services.digest_delivery import run_due


def main() -> None:
    with get_session_factory()() as db:
        results = run_due(db)
    print(json.dumps({"sent": results}))


if __name__ == "__main__":
    main()
