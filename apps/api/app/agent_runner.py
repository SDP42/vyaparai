"""Run the automation agents that are due. Schedule it, for example every 15 minutes:

    */15 * * * *  cd /path/to/apps/api && uv run python -m app.agent_runner

Each enabled agent runs at most once per local day, so running this often is safe.
"""

import json

from app.db.session import get_session_factory
from app.services.agents.schedule import run_due


def main() -> None:
    with get_session_factory()() as db:
        results = run_due(db)
    print(json.dumps({"ran": results}))


if __name__ == "__main__":
    main()
