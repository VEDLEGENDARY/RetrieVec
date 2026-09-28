"""Allowlisted operational events. Payloads and exception messages never enter logs."""

import contextvars
import json
import logging
import math
import re
import time
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from types import MappingProxyType

CONTEXT = contextvars.ContextVar("retrievec_trace", default=MappingProxyType({}))
LOGGER = logging.getLogger("retrievec.events")
IDS = {"request_id", "job_id", "run_id", "snapshot_id", "collection_id"}
LABELS = {"stage", "outcome", "error_code", "service", "operation", "worker_kind"}
COUNTS = {"elapsed_ms", "queue_age_ms", "attempt", "active_workers", "status_code", "count"}
IDENTIFIER = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")


def configure(service="retrievec.python"):
    from retrievec.observability import configure as configure_tracing

    configure_tracing(service)
    if not LOGGER.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        LOGGER.addHandler(handler)
    LOGGER.setLevel(logging.INFO)
    LOGGER.propagate = False


def request_identity(value=None):
    if isinstance(value, str) and re.fullmatch(r"[0-9a-f]{32}", value):
        return value
    return uuid.uuid4().hex


def fields(values):
    safe = {}
    for key, value in values.items():
        if key in IDS | LABELS and value is not None and IDENTIFIER.fullmatch(str(value)):
            safe[key] = str(value)
        elif key in COUNTS and type(value) in (int, float) and math.isfinite(value) and value >= 0:
            safe[key] = round(value, 3) if isinstance(value, float) else value
    return safe


def emit(event, **values):
    if not IDENTIFIER.fullmatch(event):
        raise ValueError("invalid event name")
    record = {
        "schema_version": 1,
        "time": datetime.now(UTC).isoformat(),
        "event": event,
        **fields(CONTEXT.get()),
        **fields(values),
    }
    LOGGER.info(json.dumps(record, sort_keys=True, separators=(",", ":")))


@contextmanager
def correlate(**values):
    token = CONTEXT.set({**CONTEXT.get(), **fields(values)})
    try:
        yield
    finally:
        CONTEXT.reset(token)


@contextmanager
def stage(operation, **values):
    started = time.perf_counter()
    outcome = "completed"
    with correlate(**values):
        try:
            yield
        except BaseException:
            outcome = "failed"
            raise
        finally:
            emit(
                "stage.finished",
                operation=operation,
                outcome=outcome,
                elapsed_ms=(time.perf_counter() - started) * 1000,
            )
