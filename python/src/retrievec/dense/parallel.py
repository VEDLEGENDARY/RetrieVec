"""Overlap two bounded, snapshot-pinned legs without changing their ranking logic."""

from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context


def run_legs(sparse, dense, *, concurrent: bool):
    if type(concurrent) is not bool:
        raise ValueError("concurrent must be boolean")
    if not concurrent:
        return sparse(), dense()
    # Dense stays on the caller's thread. One sparse task per request; no fanout
    # over candidates and no background task survives return or an exception.
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="hybrid-sparse") as executor:
        pending = executor.submit(copy_context().run, sparse)
        dense_result = dense()
        return pending.result(), dense_result
