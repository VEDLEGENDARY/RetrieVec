"""Offline benchmark adapter over shipped Go BM25, exact cosine and chunk RRF."""

import json
import subprocess
import time

from retrievec.corpus.snapshot import load_snapshot
from retrievec.dense.artifacts import load_embeddings
from retrievec.dense.hybrid import fuse
from retrievec.dense.parallel import run_legs
from retrievec.dense.search import exact_search
from retrievec.registry.artifacts import Store


class Pipeline:
    def __init__(self, engine, work, prepared, model, candidates):
        self.model, self.candidates = model, candidates
        store = Store(work / "store")
        manifest = store.manifest(prepared["snapshot_id"])
        corpus = store.path("corpora", manifest["corpus_snapshot_id"], "ss_")
        _, _, chunks = load_snapshot(corpus)
        self.papers = {row["chunk_id"]: row["paper_id"] for row in chunks}
        embedding, self.vectors = load_embeddings(
            store, prepared["embedding_id"], manifest["corpus_snapshot_id"]
        )
        if embedding["configuration"] != model.config:
            raise ValueError("model configuration changed")
        self.ids = [row["chunk_id"] for row in embedding["chunks"]]
        self.log = (work / "sparse-worker.log").open("w", encoding="utf-8")
        self.process = subprocess.Popen(
            [str(engine.resolve()), "benchmark", "--corpus", str(corpus)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self.log,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        try:
            self.startup = json.loads(self.process.stdout.readline())
            if self.startup["snapshot_id"] != manifest["corpus_snapshot_id"]:
                raise ValueError("sparse/dense snapshot mismatch")
        except (ValueError, KeyError, OSError):
            self.close()
            raise

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
        try:
            self.process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.communicate()
        finally:
            self.log.close()

    def sparse(self, query, config):
        started = time.perf_counter()
        self.process.stdin.write(
            json.dumps(
                {"query": query, "top_k": self.candidates, "k1": config["k1"], "b": config["b"]}
            )
            + "\n"
        )
        self.process.stdin.flush()
        result = json.loads(self.process.stdout.readline())
        return result["hits"], (time.perf_counter() - started) * 1000

    def dense(self, query):
        started = time.perf_counter()
        vector = self.model.encode([self.model.config["query_prefix"] + query])[0]
        hits = exact_search(self.vectors, self.ids, vector, self.candidates)
        return hits, (time.perf_counter() - started) * 1000

    def documents(self, hits, query_id):
        seen, result = {query_id}, []
        for hit in hits:
            paper = self.papers[hit["chunk_id"]]
            if paper not in seen:
                seen.add(paper)
                result.append(paper)
        return result[:100]

    def hybrid(self, sparse, dense, k):
        started = time.perf_counter()
        result = fuse([sparse, dense], k)
        # PinnedClient also slices the fused chunk list before returning it.
        return result[: self.candidates], (time.perf_counter() - started) * 1000

    def retrieve_hybrid(self, query, config, *, concurrent):
        started = time.perf_counter()
        (sparse, sparse_ms), (dense, dense_ms) = run_legs(
            lambda: self.sparse(query, config),
            lambda: self.dense(query),
            concurrent=concurrent,
        )
        hits, fusion_ms = self.hybrid(sparse, dense, config["rrf_k"])
        return (
            hits,
            (time.perf_counter() - started) * 1000,
            {
                "sparse_ms": sparse_ms,
                "dense_ms": dense_ms,
                "fusion_ms": fusion_ms,
            },
        )
