"""Cross-process admission for memory-heavy local workers.

The session lock is held outside a transaction during model execution. PostgreSQL
releases it when a worker connection closes; publication still uses job fencing.
"""

from contextlib import contextmanager

HEAVY_WORK_LOCK = 7823404


@contextmanager
def heavy_slot(registry, kind):
    if kind not in ("ingestion", "research"):
        raise ValueError("unknown worker kind")
    with registry.connect() as db:
        acquired = db.execute(
            "SELECT pg_try_advisory_lock(%s) AS acquired", (HEAVY_WORK_LOCK,)
        ).fetchone()["acquired"]
        db.commit()
        try:
            yield acquired
        finally:
            if acquired:
                db.execute("SELECT pg_advisory_unlock(%s)", (HEAVY_WORK_LOCK,))
                db.commit()
