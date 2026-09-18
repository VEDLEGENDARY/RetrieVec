"""Transactional ownership and immutable snapshot registration."""

from importlib.resources import files

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from retrievallab.corpus.snapshot import canonical, digest


class Conflict(ValueError):
    pass


class Registry:
    def __init__(self, dsn: str):
        self.dsn = dsn

    def connect(self):
        return psycopg.connect(self.dsn, row_factory=dict_row, connect_timeout=5)

    def migrate(self) -> None:
        with self.connect() as connection:
            if not 180000 <= connection.info.server_version < 190000:
                raise ValueError("PostgreSQL 18 is required")
            connection.execute("SELECT pg_advisory_xact_lock(7823401)")
            connection.execute(files("retrievallab.registry").joinpath("migrations/001_registry.sql").read_text())

    @staticmethod
    def authorize(connection, principal: str, collection: str, *, lock: bool = False) -> dict:
        row = connection.execute("SELECT * FROM collections WHERE collection_id=%s AND owner_id=%s" + (" FOR UPDATE" if lock else ""), (collection, principal)).fetchone()
        if row is None:
            raise PermissionError("collection is unavailable to this principal")
        return row

    def create_collection(self, principal: str, collection: str) -> None:
        if not principal or not collection:
            raise ValueError("principal and collection required")
        with self.connect() as connection:
            connection.execute("INSERT INTO principals VALUES(%s) ON CONFLICT DO NOTHING", (principal,))
            connection.execute("INSERT INTO collections(collection_id,owner_id) VALUES(%s,%s) ON CONFLICT DO NOTHING", (collection, principal))
            self.authorize(connection, principal, collection)

    def register(self, principal: str, manifest: dict) -> str:
        snapshot_id = "rs_" + digest(canonical(manifest))
        if manifest.get("schema_version") != 1 or manifest.get("capabilities") not in (["sparse"], ["sparse", "dense", "hybrid"]):
            raise ValueError("invalid retrieval manifest")
        with self.connect() as connection:
            self.authorize(connection, principal, manifest["collection_id"])
            connection.execute("INSERT INTO retrieval_snapshots(snapshot_id,collection_id,corpus_snapshot_id,manifest,state,capabilities) VALUES(%s,%s,%s,%s,'prepared',%s) ON CONFLICT DO NOTHING", (snapshot_id, manifest["collection_id"], manifest["corpus_snapshot_id"], Jsonb(manifest), manifest["capabilities"]))
            row = connection.execute("SELECT manifest FROM retrieval_snapshots WHERE snapshot_id=%s", (snapshot_id,)).fetchone()
            if row["manifest"] != manifest:
                raise Conflict("immutable snapshot registration conflict")
        return snapshot_id

    def ready(self, principal: str, collection: str, snapshot_id: str) -> None:
        with self.connect() as connection:
            self.authorize(connection, principal, collection)
            row = connection.execute("UPDATE retrieval_snapshots SET state='ready' WHERE collection_id=%s AND snapshot_id=%s RETURNING snapshot_id", (collection, snapshot_id)).fetchone()
            if row is None:
                raise ValueError("snapshot is not registered")

    def resolve(self, principal: str, collection: str, snapshot_id: str | None = None) -> dict:
        with self.connect() as connection:
            owner = self.authorize(connection, principal, collection)
            pinned = snapshot_id or owner["active_snapshot"]
            row = connection.execute("SELECT * FROM retrieval_snapshots WHERE collection_id=%s AND snapshot_id=%s AND state='ready'", (collection, pinned)).fetchone()
            if row is None:
                raise ValueError("no ready snapshot for requested identity")
            return row

    def activate(self, principal: str, collection: str, snapshot_id: str, expected_parent: str | None) -> None:
        with self.connect() as connection:
            row = self.authorize(connection, principal, collection, lock=True)
            if row["active_snapshot"] == snapshot_id:
                return
            ready = connection.execute("SELECT snapshot_id FROM retrieval_snapshots WHERE snapshot_id=%s AND collection_id=%s AND state='ready'", (snapshot_id, collection)).fetchone()
            if ready is None or row["active_snapshot"] != expected_parent:
                raise Conflict("snapshot not ready or expected parent is stale")
            connection.execute("UPDATE collections SET active_snapshot=%s WHERE collection_id=%s", (snapshot_id, collection))
