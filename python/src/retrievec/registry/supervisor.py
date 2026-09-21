"""Reconnect worker sessions after transient database outages without replaying calls."""

import threading

import psycopg

from retrievec.telemetry import emit

TRANSIENT = (
    psycopg.OperationalError,
    psycopg.InterfaceError,
    psycopg.errors.SerializationFailure,
    psycopg.errors.DeadlockDetected,
)


def serve_worker(registry, guard_key, tick, *, idle_seconds=1, stop=None):
    if guard_key not in (7823402, 7823403) or not 0 < idle_seconds <= 30:
        raise ValueError("invalid worker supervision settings")
    stop = stop if stop is not None else threading.Event()
    failures = 0
    while not stop.is_set():
        try:
            with registry.connect() as guard:
                acquired = guard.execute(
                    "SELECT pg_try_advisory_lock(%s) AS acquired", (guard_key,)
                ).fetchone()["acquired"]
                guard.commit()
                if not acquired:
                    raise SystemExit("Another worker of this kind is already running")
                while not stop.is_set():
                    # Never trust a process guard that belonged to a disconnected session.
                    guard.execute("SELECT 1")
                    guard.commit()
                    worked = tick()
                    if failures:
                        emit("worker.recovered", attempt=failures)
                    failures = 0
                    if not worked:
                        stop.wait(idle_seconds)
        except TRANSIENT:
            failures += 1
            emit("worker.reconnecting", attempt=failures, error_code="database_unavailable")
            # The old guard is closed before waiting/reacquiring. Leases, not this loop,
            # decide whether old ingestion can retry or interrupted generation must fail.
            stop.wait(min(30, 2 ** min(failures - 1, 5)))
