"""Content-addressed artifacts and the prepare/ready boundary."""

import re
import subprocess
from pathlib import Path

from retrievec.corpus.snapshot import canonical, digest, parse_json
from retrievec.registry.database import Registry


def identity(value: str, prefix: str) -> str:
    if (
        not isinstance(value, str)
        or re.fullmatch(re.escape(prefix) + r"[0-9a-f]{64}", value) is None
    ):
        raise ValueError("invalid artifact identity")
    return value


class Store:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def path(self, category: str, value: str, prefix: str) -> Path:
        identity(value, prefix)
        target = self.root / category / value
        if not target.resolve().is_relative_to(self.root):
            raise ValueError("artifact path escapes store")
        return target

    def manifest(self, snapshot_id: str) -> dict:
        path = self.path("snapshots", snapshot_id, "rs_") / "manifest.json"
        if path.is_symlink() or path.stat().st_size > 4 * 1024 * 1024:
            raise ValueError("invalid manifest file")
        raw = path.read_bytes()
        value = parse_json(raw)
        if (
            not isinstance(value, dict)
            or canonical(value) + b"\n" != raw
            or "rs_" + digest(canonical(value)) != snapshot_id
        ):
            raise ValueError("retrieval manifest identity mismatch")
        return value

    def build(self, engine: Path, corpus: Path, embedding_id: str | None = None) -> str:
        command = [
            str(engine.resolve()),
            "build",
            "--store",
            str(self.root),
            "--corpus",
            str(corpus.resolve()),
        ]
        if embedding_id:
            command += ["--embedding", identity(embedding_id, "em_")]
        result = subprocess.run(command, capture_output=True, text=True, timeout=300, check=False)
        if result.returncode:
            raise ValueError("sparse snapshot build failed")
        snapshot_id = identity(result.stdout.strip(), "rs_")
        self.manifest(snapshot_id)
        return snapshot_id


def prepare(registry: Registry, store: Store, principal: str, snapshot_id: str, node) -> dict:
    manifest = store.manifest(snapshot_id)
    registered = registry.register(principal, manifest)
    if registered != snapshot_id:
        raise ValueError("registered identity differs")
    node.prepare(manifest["collection_id"], snapshot_id)
    if manifest["embedding_id"] is not None:
        from retrievec.dense.artifacts import load_embeddings

        load_embeddings(store, manifest["embedding_id"], manifest["corpus_snapshot_id"])
    registry.ready(principal, manifest["collection_id"], snapshot_id)
    return manifest


def publish(
    registry: Registry,
    store: Store,
    principal: str,
    snapshot_id: str,
    expected_parent: str | None,
    node,
) -> None:
    manifest = prepare(registry, store, principal, snapshot_id, node)
    registry.activate(principal, manifest["collection_id"], snapshot_id, expected_parent)
