"""Single heavy ingestion consumer for all workspace principals."""

import os
import time
from pathlib import Path

from retrievec.app.config import Settings
from retrievec.client.rpc import RPCClient
from retrievec.registry.artifacts import Store
from retrievec.registry.database import Registry
from retrievec.registry.worker import Worker


def main():
    settings = Settings.from_env()
    registry = Registry(settings.dsn)
    engine = Path(os.environ["RETRIEVEC_ENGINE"]).resolve()
    with registry.connect() as guard:
        if not guard.execute("SELECT pg_try_advisory_lock(7823402) AS acquired").fetchone()[
            "acquired"
        ]:
            raise SystemExit("A workspace ingestion worker is already running")
        guard.commit()
        while True:
            with registry.connect() as db:
                owners = db.execute(
                    "SELECT DISTINCT c.owner_id FROM ingestion_jobs j JOIN "
                    "collections c USING(collection_id) WHERE NOT c.archived "
                    "AND j.state IN ('queued','retry_wait','running')"
                ).fetchall()
            for owner in owners:
                user = owner["owner_id"]
                node = RPCClient(
                    settings.rpc_address, os.environ["RETRIEVEC_WORKER_TOKEN"], principal=user
                )
                try:
                    Worker(registry, Store(settings.store), user, engine, node).run_once()
                finally:
                    node.close()
            time.sleep(2)


if __name__ == "__main__":
    main()
