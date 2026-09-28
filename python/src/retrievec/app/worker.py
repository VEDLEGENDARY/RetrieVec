"""Single heavy ingestion consumer for all workspace principals."""

import os
from pathlib import Path

from retrievec.app.config import Settings
from retrievec.client.rpc import RPCClient
from retrievec.registry.artifacts import Store
from retrievec.registry.database import Registry
from retrievec.registry.supervisor import serve_worker
from retrievec.registry.worker import Worker
from retrievec.telemetry import configure


def main():
    configure("retrievec.ingestion")
    settings = Settings.from_env()
    registry = Registry(settings.dsn)
    engine = Path(os.environ["RETRIEVEC_ENGINE"]).resolve()

    def tick():
        with registry.connect() as db:
            owners = db.execute(
                "SELECT c.owner_id,min(j.available_at) AS oldest FROM ingestion_jobs j JOIN "
                "collections c USING(collection_id) WHERE NOT c.archived AND "
                "((j.state IN ('queued','retry_wait') AND j.available_at<=clock_timestamp()) "
                "OR (j.state='running' AND j.lease_until<clock_timestamp())) "
                "GROUP BY c.owner_id ORDER BY oldest,c.owner_id LIMIT 64"
            ).fetchall()
        for owner in owners:
            user = owner["owner_id"]
            node = RPCClient(
                settings.rpc_address, os.environ["RETRIEVEC_WORKER_TOKEN"], principal=user
            )
            try:
                result = Worker(registry, Store(settings.store), user, engine, node).run_once()
                if result is not None:
                    return True
            finally:
                node.close()
        return False

    serve_worker(registry, 7823402, tick, idle_seconds=2)


if __name__ == "__main__":
    main()
