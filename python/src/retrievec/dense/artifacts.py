"""Checked float32 vectors with exact chunk mappings and complete cache identity."""

import hashlib
import shutil
import tempfile

import numpy as np

from retrievec.corpus.snapshot import canonical, digest, load_snapshot, parse_json
from retrievec.dense.model import normalize
from retrievec.registry.artifacts import Store
from retrievec.registry.worker import publish_bytes


def build_embeddings(store: Store, corpus_path, model) -> str:
    corpus, _, chunks = load_snapshot(corpus_path)
    chunks.sort(key=lambda chunk: chunk["chunk_id"])
    dimension = model.config["dimension"]
    root = store.root / "embeddings"
    root.mkdir(parents=True, exist_ok=True)
    stage = type(root)(tempfile.mkdtemp(prefix=".embedding-", dir=root))
    try:
        vector_path = stage / "vectors.f32"
        with vector_path.open("wb") as output:
            for start in range(0, len(chunks), 16):
                batch = chunks[start : start + 16]
                vectors = [None] * len(batch)
                missing, texts = [], []
                keys = []
                for i, chunk in enumerate(batch):
                    key = digest(
                        canonical(
                            {
                                "text_sha256": chunk["text_sha256"],
                                "configuration": model.config,
                                "role": "document",
                            }
                        )
                    )
                    path = store.root / "embedding-cache" / (key + ".f32")
                    keys.append(path)
                    if path.exists():
                        raw = path.read_bytes()
                        checksum_path = path.with_suffix(".sha256")
                        if len(raw) != dimension * 4 or checksum_path.read_text() != digest(raw):
                            raise ValueError("embedding cache corruption")
                        cached = np.frombuffer(raw, dtype="<f4")
                        if not np.isfinite(cached).all() or not np.isclose(
                            np.linalg.norm(cached.astype(np.float64)), 1, atol=1e-5, rtol=0
                        ):
                            raise ValueError("invalid cached vector")
                        vectors[i] = cached
                    else:
                        missing.append(i)
                        texts.append(model.config["document_prefix"] + chunk["text"])
                if missing:
                    encoded = normalize(model.encode(texts))
                    if encoded.shape != (len(missing), dimension):
                        raise ValueError("embedding adapter dimension mismatch")
                    for i, vector in zip(missing, encoded, strict=True):
                        vectors[i] = vector
                        raw = vector.astype("<f4").tobytes()
                        publish_bytes(keys[i].with_suffix(".sha256"), digest(raw).encode())
                        publish_bytes(keys[i], raw)
                output.write(np.asarray(vectors, dtype="<f4").tobytes())
            output.flush()
            import os

            os.fsync(output.fileno())
        with vector_path.open("rb") as file:
            vectors_hash = hashlib.file_digest(file, "sha256").hexdigest()
        manifest = {
            "schema_version": 1,
            "corpus_snapshot_id": corpus["snapshot_id"],
            "configuration": model.config,
            "chunks": [
                {"chunk_id": c["chunk_id"], "text_sha256": c["text_sha256"]} for c in chunks
            ],
            "vectors_sha256": vectors_hash,
            "count": len(chunks),
            "dimension": dimension,
            "dtype": "<f4",
            "truncated_inputs": 0,
        }
        raw = canonical(manifest)
        embedding_id = "em_" + digest(raw)
        publish_bytes(stage / "manifest.json", raw + b"\n")
        target = store.path("embeddings", embedding_id, "em_")
        try:
            stage.rename(target)
        except OSError:
            if not target.is_dir():
                raise
        load_embeddings(store, embedding_id, corpus["snapshot_id"])
        return embedding_id
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def load_embeddings(store: Store, embedding_id: str, corpus_id: str):
    target = store.path("embeddings", embedding_id, "em_")
    manifest_path, vectors_path = target / "manifest.json", target / "vectors.f32"
    if (
        manifest_path.is_symlink()
        or vectors_path.is_symlink()
        or manifest_path.stat().st_size > 64 << 20
    ):
        raise ValueError("invalid embedding artifact paths")
    raw = manifest_path.read_bytes()
    manifest = parse_json(raw)
    if (
        canonical(manifest) + b"\n" != raw
        or "em_" + digest(canonical(manifest)) != embedding_id
        or manifest["schema_version"] != 1
        or manifest["corpus_snapshot_id"] != corpus_id
    ):
        raise ValueError("embedding identity mismatch")
    count, dimension = manifest["count"], manifest["dimension"]
    if (
        type(count) is not int
        or not 0 <= count <= 1000000
        or type(dimension) is not int
        or not 1 <= dimension <= 4096
        or manifest["dtype"] != "<f4"
        or manifest["configuration"]["dimension"] != dimension
        or count * dimension * 4 > 1 << 30
    ):
        raise ValueError("invalid embedding shape")
    if vectors_path.stat().st_size != count * dimension * 4:
        raise ValueError("embedding byte count mismatch")
    with vectors_path.open("rb") as file:
        if hashlib.file_digest(file, "sha256").hexdigest() != manifest["vectors_sha256"]:
            raise ValueError("embedding checksum mismatch")
    _, _, chunks = load_snapshot(store.path("corpora", corpus_id, "ss_"))
    expected = [
        {"chunk_id": c["chunk_id"], "text_sha256": c["text_sha256"]}
        for c in sorted(chunks, key=lambda c: c["chunk_id"])
    ]
    if expected != manifest["chunks"] or count != len(expected):
        raise ValueError("embedding chunk mapping mismatch")
    vectors = (
        np.memmap(vectors_path, dtype="<f4", mode="r", shape=(count, dimension))
        if count
        else np.empty((0, dimension), dtype="<f4")
    )
    for start in range(0, count, 4096):
        block = vectors[start : start + 4096]
        if not np.isfinite(block).all() or not np.allclose(
            np.linalg.norm(block.astype(np.float64), axis=1), 1, atol=1e-5, rtol=0
        ):
            raise ValueError("stored vectors must be finite and normalized")
    return manifest, vectors
