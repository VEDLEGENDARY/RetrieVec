"""Optional immutable pgvector study. Never selected by the product by default."""

import hashlib
import json
import time
from dataclasses import asdict, dataclass

import numpy as np
from psycopg import sql
from psycopg.types.json import Jsonb

from retrievec.corpus.snapshot import canonical, digest
from retrievec.dense.artifacts import load_embeddings
from retrievec.dense.model import normalize
from retrievec.registry.artifacts import identity

SCHEMA = "retrievec_experiments"


@dataclass(frozen=True)
class VectorConfig:
    m: int = 16
    ef_construction: int = 64
    ef_search: int = 100
    max_vectors: int = 100000

    def __post_init__(self):
        if any(type(value) is not int for value in asdict(self).values()) or not (
            2 <= self.m <= 100
            and 2 * self.m <= self.ef_construction <= 1000
            and 1 <= self.ef_search <= 1000
            and 1 <= self.max_vectors <= 1000000
        ):
            raise ValueError("invalid bounded HNSW configuration")


def initialize(registry):
    """Explicit administrator operation, separate from product migrations."""
    with registry.connect() as db:
        db.execute("SET LOCAL lock_timeout = '3s'")
        db.execute("CREATE EXTENSION IF NOT EXISTS vector")
        db.execute("CREATE SCHEMA IF NOT EXISTS retrievec_experiments")
        db.execute("""CREATE TABLE IF NOT EXISTS retrievec_experiments.vector_indexes (
            index_id text PRIMARY KEY,
            collection_id text NOT NULL REFERENCES collections(collection_id),
            snapshot_id text NOT NULL REFERENCES retrieval_snapshots(snapshot_id),
            manifest jsonb NOT NULL,
            created_at timestamptz NOT NULL DEFAULT clock_timestamp()
        )""")


def build(registry, store, principal, collection, snapshot_id, config=VectorConfig()):
    registered = registry.resolve(principal, collection, snapshot_id)
    manifest = store.manifest(snapshot_id)
    if manifest != registered["manifest"] or not manifest.get("embedding_id"):
        raise ValueError("verified dense snapshot required")
    embedding, vectors = load_embeddings(
        store, manifest["embedding_id"], manifest["corpus_snapshot_id"]
    )
    if embedding["dimension"] > 2000 or embedding["count"] > config.max_vectors:
        raise ValueError("pgvector study resource bound exceeded")
    descriptor = {
        "schema_version": 1,
        "backend": "pgvector",
        "snapshot_id": snapshot_id,
        "collection_id": collection,
        "embedding_id": manifest["embedding_id"],
        "corpus_snapshot_id": manifest["corpus_snapshot_id"],
        "vectors_sha256": embedding["vectors_sha256"],
        "configuration": embedding["configuration"],
        "index_configuration": asdict(config),
        "count": embedding["count"],
        "dimension": embedding["dimension"],
        "enabled_by_default": False,
    }
    started = time.perf_counter()
    with registry.connect() as db:
        db.execute("SET LOCAL lock_timeout = '3s'")
        db.execute("SET LOCAL statement_timeout = '300s'")
        registry.authorize(db, principal, collection)
        version = db.execute(
            "SELECT extversion FROM pg_extension WHERE extname='vector'"
        ).fetchone()
        if not version:
            raise ValueError("administrator must initialize the pgvector study first")
        descriptor["extension_version"] = version["extversion"]
        index_id = "pv_" + digest(canonical(descriptor))
        db.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (index_id,))
        prior = db.execute(
            "SELECT manifest FROM retrievec_experiments.vector_indexes WHERE index_id=%s",
            (index_id,),
        ).fetchone()
        if prior:
            if prior["manifest"] != descriptor:
                raise ValueError("immutable vector index conflict")
            return index_id
        table = sql.Identifier(SCHEMA, "v_" + index_id[3:51])
        db.execute(
            sql.SQL(
                "CREATE TABLE {} (chunk_id text PRIMARY KEY, embedding vector({}) NOT NULL)"
            ).format(table, sql.Literal(embedding["dimension"]))
        )
        statement = sql.SQL("INSERT INTO {} VALUES (%s, %s::vector)").format(table)
        with db.cursor() as cursor:
            for start in range(0, len(vectors), 256):
                cursor.executemany(
                    statement,
                    [
                        (embedding["chunks"][i]["chunk_id"], json.dumps(vectors[i].tolist()))
                        for i in range(start, min(start + 256, len(vectors)))
                    ],
                )
        count = db.execute(sql.SQL("SELECT count(*) AS count FROM {}").format(table)).fetchone()[
            "count"
        ]
        if count != embedding["count"]:
            raise ValueError("backfill count mismatch")
        persisted = hashlib.sha256()
        offset = 0
        with db.cursor(name="verify_vectors") as cursor:
            cursor.execute(
                sql.SQL(
                    "SELECT chunk_id, embedding::text AS value FROM {} ORDER BY chunk_id"
                ).format(table)
            )
            for row in cursor:
                if row["chunk_id"] != embedding["chunks"][offset]["chunk_id"]:
                    raise ValueError("backfill external ID mismatch")
                persisted.update(np.asarray(json.loads(row["value"]), dtype="<f4").tobytes())
                offset += 1
        if persisted.hexdigest() != embedding["vectors_sha256"]:
            raise ValueError("backfill vector checksum mismatch")
        # This table is new and unpublished. Index creation cannot block existing readers.
        db.execute(
            sql.SQL(
                "CREATE INDEX ON {} USING hnsw (embedding vector_cosine_ops) WITH (m={}, ef_construction={})"
            ).format(table, sql.Literal(config.m), sql.Literal(config.ef_construction))
        )
        db.execute(sql.SQL("ANALYZE {}").format(table))
        registry.authorize(db, principal, collection, lock=True)
        db.execute(
            "INSERT INTO retrievec_experiments.vector_indexes VALUES (%s,%s,%s,%s,clock_timestamp())",
            (index_id, collection, snapshot_id, Jsonb(descriptor)),
        )
    from retrievec.telemetry import emit

    emit("pgvector.built", count=len(vectors), elapsed_ms=(time.perf_counter() - started) * 1000)
    return index_id


class PgvectorIndex:
    def __init__(self, registry, principal, collection, snapshot_id, index_id):
        self.registry, self.principal, self.collection = registry, principal, collection
        self.snapshot_id = identity(snapshot_id, "rs_")
        self.index_id = identity(index_id, "pv_")
        self.table = sql.Identifier(SCHEMA, "v_" + index_id[3:51])

    def search(self, query, *, configuration, top_k=10, approximate=False):
        if type(top_k) is not int or not 1 <= top_k <= 1000 or type(approximate) is not bool:
            raise ValueError("invalid vector search bounds")
        registered = self.registry.resolve(self.principal, self.collection, self.snapshot_id)
        query = np.asarray(query, dtype=np.float32)
        if query.ndim != 1:
            raise ValueError("query must be a vector")
        with self.registry.connect() as db:
            db.execute("SET LOCAL statement_timeout = '5s'")
            self.registry.authorize(db, self.principal, self.collection, lock=True, read=True)
            row = db.execute(
                "SELECT manifest FROM retrievec_experiments.vector_indexes WHERE index_id=%s AND collection_id=%s AND snapshot_id=%s",
                (self.index_id, self.collection, self.snapshot_id),
            ).fetchone()
            if not row:
                raise ValueError("vector index unavailable for this scope")
            manifest = row["manifest"]
            if (
                manifest["configuration"] != configuration
                or len(query) != manifest["dimension"]
                or manifest["embedding_id"] != registered["manifest"]["embedding_id"]
                or "pv_" + digest(canonical(manifest)) != self.index_id
            ):
                raise ValueError("vector index or model identity mismatch")
            value = json.dumps(normalize(query.reshape(1, -1))[0].tolist())
            if approximate:
                ef = max(top_k, manifest["index_configuration"]["ef_search"])
                db.execute("SELECT set_config('hnsw.ef_search', %s, true)", (str(ef),))
                db.execute("SET LOCAL enable_seqscan = off")
                order = sql.SQL("distance")
            else:
                db.execute("SET LOCAL enable_indexscan = off")
                db.execute("SET LOCAL enable_bitmapscan = off")
                order = sql.SQL("distance, chunk_id")
            rows = db.execute(
                sql.SQL(
                    "SELECT chunk_id, embedding <=> %s::vector AS distance FROM {} ORDER BY {} LIMIT %s"
                ).format(self.table, order),
                (value, top_k),
            ).fetchall()
            if any(not np.isfinite(row["distance"]) for row in rows):
                raise ValueError("nonfinite vector distance")
            rows.sort(key=lambda row: (row["distance"], row["chunk_id"]))
            return [
                {"chunk_id": row["chunk_id"], "cosine_score": 1 - row["distance"], "rank": rank}
                for rank, row in enumerate(rows, 1)
            ]
