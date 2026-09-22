"""Content-addressed experimental configs with an explicit stable fallback."""

from __future__ import annotations

import os
from pathlib import Path

from retrievec.corpus.snapshot import canonical, digest, parse_json


REFERENCE_CONFIG = {
    "schema_version": 1,
    "kind": "reference",
    "dense": "exact_cosine",
    "sparse": "bm25_reference",
    "reranker": None,
    "approximate": None,
    "default": True,
}


def register_config(directory: Path, config: dict) -> str:
    if config.get("schema_version") != 1 or config.get("default") is not False:
        raise ValueError("experimental config must be versioned and non-default")
    if config.get("kind") not in ("reranker", "approximate", "sparse_optimized", "combined"):
        raise ValueError("unknown experiment config kind")
    if not isinstance(config.get("provenance"), dict) or not config["provenance"]:
        raise ValueError("experimental config requires provenance")
    raw = canonical(config)
    identity = "xc_" + digest(raw)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{identity}.json"
    if target.exists() and target.read_bytes() != raw + b"\n":
        raise ValueError("immutable experiment config conflict")
    if not target.exists():
        stage = directory / f".{identity}.tmp"
        with stage.open("wb") as output:
            output.write(raw + b"\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(stage, target)
    return identity


def load_config(directory: Path, config_id: str | None) -> dict:
    if config_id is None:
        return dict(REFERENCE_CONFIG)
    if not config_id.startswith("xc_") or len(config_id) != 67:
        raise ValueError("invalid experiment config identity")
    raw = (directory / f"{config_id}.json").read_bytes()
    config = parse_json(raw)
    if raw != canonical(config) + b"\n" or config_id != "xc_" + digest(canonical(config)):
        raise ValueError("experiment config identity mismatch")
    if config.get("default") is not False:
        raise ValueError("experimental config cannot replace stable fallback")
    return config


def authorize_config(config: dict, *, requested_collection: str, authorized_collection: str, snapshot_id: str) -> None:
    if requested_collection != authorized_collection:
        raise PermissionError("experiment collection scope denied")
    pinned = config.get("retrieval_snapshot_id")
    if pinned is not None and pinned != snapshot_id:
        raise ValueError("experiment config snapshot differs from pinned request")
