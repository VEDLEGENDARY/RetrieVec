"""End-to-end experiment decision records with conservative default retention."""

from __future__ import annotations

from retrievec.corpus.snapshot import canonical, digest


def compare_final_configs(reference: dict, experimental: dict, criteria: dict) -> dict:
    required = ("quality", "latency", "memory", "failures", "isolation", "snapshot_parity")
    if any(key not in reference or key not in experimental for key in required):
        raise ValueError("final comparison is incomplete")
    if criteria.get("frozen_before_held_out") is not True:
        raise ValueError("decision criteria were not frozen before held-out evaluation")
    if experimental.get("reviewed_judgments") is not True:
        decision, reasons = "inconclusive", ["reviewed held-out judgments unavailable"]
    elif experimental["isolation"] is not True or experimental["snapshot_parity"] is not True:
        decision, reasons = "retain_reference", ["scope or pinned-snapshot parity failed"]
    elif experimental["failures"]:
        decision, reasons = "retain_reference", ["experimental configuration has failures"]
    else:
        minimum = criteria.get("minimum_quality_delta")
        maximum_p95 = criteria.get("maximum_p95_ms")
        maximum_memory = criteria.get("maximum_memory_bytes")
        if not all(isinstance(value, (int, float)) for value in (minimum, maximum_p95, maximum_memory)):
            raise ValueError("numeric retain criteria are incomplete")
        quality_delta = experimental["quality"] - reference["quality"]
        passed = quality_delta >= minimum and experimental["latency"]["p95"] <= maximum_p95 and experimental["memory"] <= maximum_memory
        decision = "retain_experimental" if passed else "retain_reference"
        reasons = [] if passed else ["one or more frozen quality/resource criteria failed"]
    identity = {
        "schema_version": 1,
        "reference_hash": digest(canonical(reference)),
        "experimental_hash": digest(canonical(experimental)),
        "criteria_hash": digest(canonical(criteria)),
        "decision": decision,
        "reasons": reasons,
        "default_changed": False,
        "owner_approval_required": decision == "retain_experimental",
    }
    return dict(identity, decision_id="fd_" + digest(canonical(identity)))


def verify_adapter_scope(run: dict, *, principal_id: str, collection_id: str, snapshot_id: str) -> None:
    if run.get("principal_id") != principal_id or run.get("collection_id") != collection_id:
        raise PermissionError("experiment run scope mismatch")
    if run.get("retrieval_snapshot_id") != snapshot_id:
        raise ValueError("experiment run did not preserve pinned snapshot")
    if run.get("configuration", {}).get("default") is not False:
        raise ValueError("experimental configuration cannot become implicit default")
