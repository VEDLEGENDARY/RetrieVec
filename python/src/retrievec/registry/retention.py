"""Check that retained metadata resolves to complete immutable artifact graphs."""

import re

from retrievec.corpus.snapshot import digest, load_snapshot, parse_json
from retrievec.registry.artifacts import Store, identity


def audit_retained(db, root, files):
    store = Store(root)
    by_path = {row["path"]: row for row in files}
    counts = {"ready_snapshots": 0, "sources": 0, "pending_inputs": 0}

    def retained(path, expected_hash, expected_size=None):
        relative = path.relative_to(store.root).as_posix()
        row = by_path.get(relative)
        if row is None or row["sha256"] != expected_hash:
            raise ValueError("referenced artifact missing or inconsistent")
        if expected_size is not None and row["bytes"] != expected_size:
            raise ValueError("referenced artifact size differs")

    if db.execute(
        "SELECT 1 FROM research_runs r JOIN retrieval_snapshots s USING(snapshot_id) "
        "WHERE s.state<>'ready' UNION ALL "
        "SELECT 1 FROM collections c JOIN retrieval_snapshots s "
        "ON s.snapshot_id=c.active_snapshot WHERE s.state<>'ready' LIMIT 1"
    ).fetchone():
        raise ValueError("active or saved snapshot is not ready")

    for row in db.execute(
        "SELECT snapshot_id,collection_id,corpus_snapshot_id,manifest "
        "FROM retrieval_snapshots WHERE state='ready' ORDER BY snapshot_id"
    ):
        manifest = store.manifest(row["snapshot_id"])
        if (
            manifest != row["manifest"]
            or manifest["collection_id"] != row["collection_id"]
            or manifest["corpus_snapshot_id"] != row["corpus_snapshot_id"]
        ):
            raise ValueError("retained snapshot registration differs")
        corpus_path = store.path("corpora", row["corpus_snapshot_id"], "ss_")
        retained(corpus_path / "manifest.json", manifest["corpus_manifest_sha256"])
        corpus, _, chunks = load_snapshot(corpus_path)
        if corpus["collection_id"] != row["collection_id"]:
            raise ValueError("retained corpus belongs to a different collection")
        if corpus["configuration"].get("evidence_map_id"):
            from retrievec.extraction.indexing import EvidenceIndex

            index = EvidenceIndex(store.root, corpus)
            for chunk in chunks:
                evidence = index.object_for(chunk)
                if evidence is not None:
                    retained(
                        store.root / "evidence-sources" / (evidence.source_sha256 + ".pdf"),
                        evidence.source_sha256,
                    )
                    retained(
                        index.store.image(evidence.page_render_sha256), evidence.page_render_sha256
                    )
                    if evidence.region_crop_sha256:
                        retained(
                            index.store.image(evidence.region_crop_sha256),
                            evidence.region_crop_sha256,
                        )
        segments = manifest["segments"]
        if (
            not isinstance(segments, list)
            or len(segments) > 1024
            or len(set(segments)) != len(segments)
        ):
            raise ValueError("invalid retained segment references")
        for segment in segments:
            retained(store.root / "segments" / (identity(segment, "") + ".seg"), segment)
        if manifest["embedding_id"] is not None:
            from retrievec.dense.artifacts import load_embeddings

            _, vectors = load_embeddings(store, manifest["embedding_id"], row["corpus_snapshot_id"])
            # The backup audit must not keep mapped vector files open during copying on Windows.
            mapping = getattr(vectors, "_mmap", None)
            if mapping is not None:
                mapping.close()
        counts["ready_snapshots"] += 1

    for row in db.execute(
        "SELECT s.storage_key,s.source_hash,s.size_bytes,s.owner_id,c.owner_id AS collection_owner "
        "FROM upload_sources s JOIN collections c USING(collection_id) ORDER BY s.source_id"
    ):
        if row["owner_id"] != row["collection_owner"] or not re.fullmatch(
            r"[0-9a-f]{32}\.(pdf|txt|md)", row["storage_key"]
        ):
            raise ValueError("invalid retained source ownership or storage key")
        retained(store.root / "sources" / row["storage_key"], row["source_hash"], row["size_bytes"])
        counts["sources"] += 1

    for row in db.execute(
        "SELECT payload FROM ingestion_jobs WHERE state IN ('queued','retry_wait')"
    ):
        key = identity(row["payload"]["input"]["manifest_hash"], "")
        path = store.root / "inputs" / (key + ".json")
        retained(path, key)
        # Input manifests have no trailing newline: their raw bytes are the content identity.
        if digest(path.read_bytes()) != key:
            raise ValueError("queued input changed during audit")
        for source in parse_json(path.read_bytes())["sources"]:
            source_path = source["path"]
            if (
                not isinstance(source_path, str)
                or source_path in ("", ".", "..")
                or any(character in source_path for character in ("/", "\\", ":"))
            ):
                raise ValueError("queued source reference escapes retained store")
            retained(store.root / "sources" / source_path, source["source_sha256"])
        counts["pending_inputs"] += 1
    return counts
