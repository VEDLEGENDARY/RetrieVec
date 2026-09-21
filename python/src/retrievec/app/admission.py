"""Bound workspace queues across users, while retaining per-user quotas."""

from retrievec.app.errors import APIError

ADMISSION_LOCK = 7823405


def lock_admission(db, user):
    # All enqueue routes lock admission -> principal -> collection in this order.
    acquired = db.execute(
        "SELECT pg_try_advisory_xact_lock(%s) AS acquired", (ADMISSION_LOCK,)
    ).fetchone()["acquired"]
    if not acquired:
        raise APIError(429, "workspace_busy", "Another upload or run is being queued; try again")
    db.execute("SELECT principal_id FROM principals WHERE principal_id=%s FOR UPDATE", (user,))


def require_capacity(db, limit):
    pending = db.execute(
        "SELECT (SELECT count(*) FROM ingestion_jobs "
        "WHERE state IN ('queued','running','retry_wait')) + "
        "(SELECT count(*) FROM research_runs "
        "WHERE state IN ('queued','retrieving','generating','validating')) AS count"
    ).fetchone()["count"]
    if pending >= limit:
        raise APIError(429, "workspace_capacity", "Workspace queue is full; try again later")
