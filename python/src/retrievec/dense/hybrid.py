"""Snapshot-pinned sparse/dense search and reciprocal rank fusion."""

import math
import time
import uuid

from retrievec.corpus.snapshot import load_snapshot
from retrievec.dense.artifacts import load_embeddings
from retrievec.dense.search import exact_search


def fuse(lists: list[list[dict]], k: int = 60) -> list[dict]:
    if type(k) is not int or k < 1:
        raise ValueError("RRF k must be positive")
    scores = {}
    for ranking in lists:
        seen = set()
        for item in ranking:
            key = item["chunk_id"]
            if key in seen:
                continue
            seen.add(key)
            scores[key] = scores.get(key, 0.0) + 1 / (k + len(seen))
    return [
        {"chunk_id": key, "rrf_score": score, "rank": rank}
        for rank, (key, score) in enumerate(
            sorted(scores.items(), key=lambda item: (-item[1], item[0])), 1
        )
    ]


class PinnedClient:
    def __init__(
        self,
        registry,
        store,
        node,
        principal: str,
        collection: str,
        retrieval: str = "hybrid",
        model=None,
        snapshot_id: str | None = None,
        candidates: int = 100,
    ):
        if (
            retrieval not in ("sparse", "dense", "hybrid")
            or type(candidates) is not int
            or not 1 <= candidates <= 1000
        ):
            raise ValueError("invalid retrieval mode or candidate count")
        self.registry, self.store, self.node = registry, store, node
        self.principal, self.collection = principal, collection
        self.retrieval, self.model, self.candidates = retrieval, model, candidates
        registered = registry.resolve(principal, collection, snapshot_id)
        self.snapshot_id = registered["snapshot_id"]
        self.manifest = store.manifest(self.snapshot_id)
        if self.manifest != registered["manifest"]:
            raise ValueError("registry and artifact manifest differ")
        if retrieval not in self.manifest["capabilities"]:
            raise ValueError("snapshot does not declare requested capability")
        corpus, _, chunks = load_snapshot(
            store.path("corpora", self.manifest["corpus_snapshot_id"], "ss_")
        )
        self.chunks = {chunk["chunk_id"]: chunk for chunk in chunks}
        self.evidence_index = None
        if corpus["configuration"].get("evidence_map_id"):
            from retrievec.extraction.indexing import EvidenceIndex

            self.evidence_index = EvidenceIndex(store.root, corpus)
        _, papers, _ = load_snapshot(
            store.path("corpora", self.manifest["corpus_snapshot_id"], "ss_")
        )
        self.titles = {paper["paper_version_id"]: paper["title"] for paper in papers}
        self.vectors, self.embedding = None, None
        if retrieval != "sparse":
            self.embedding, self.vectors = load_embeddings(
                store, self.manifest["embedding_id"], self.manifest["corpus_snapshot_id"]
            )
            if model is None or model.config != self.embedding["configuration"]:
                raise ValueError("query encoder does not match pinned embedding configuration")
        self.configuration = {
            "retrieval": retrieval,
            "k1": 1.2,
            "b": 0.75,
            "rrf_k": 60,
            "candidates": candidates,
            "embedding_id": self.manifest["embedding_id"],
        }
        self.base_url = "grpc://local/" + collection
        self.info = node.info(collection, self.snapshot_id)
        if self.info.corpus_snapshot_id != self.manifest["corpus_snapshot_id"]:
            raise ValueError("RPC corpus identity mismatch")

    def stats(self) -> dict:
        return {
            "snapshot_id": self.snapshot_id,
            "corpus_snapshot_id": self.manifest["corpus_snapshot_id"],
            "collection_id": self.collection,
            "analyzer_version": self.manifest["analyzer_version"],
            "scoring_version": "bm25-v1+cosine-v1+rrf-v1",
            "configuration": self.configuration,
            "statistics": {
                "chunk_count": self.info.chunk_count,
                "term_count": self.info.term_count,
                "total_tokens": self.info.total_tokens,
                "average_chunk_length": self.info.average_length,
            },
        }

    def search(
        self, query: str, mode: str = "free_text", top_k: int = 10, explain: bool = False
    ) -> dict:
        if (
            not isinstance(query, str)
            or not query.strip()
            or len(query) > 4096
            or mode not in ("free_text", "structured")
            or type(top_k) is not int
            or not 1 <= top_k <= min(100, self.candidates)
        ):
            raise ValueError("invalid query mode, length or top_k")
        if mode == "structured" and self.retrieval != "sparse":
            raise ValueError("structured queries are sparse-only")
        self.registry.resolve(self.principal, self.collection, self.snapshot_id)
        start = time.perf_counter()
        sparse, dense, timings = [], [], {}
        total = 0
        if self.retrieval != "dense":
            response = self.node.search(
                self.collection, self.snapshot_id, query, mode, self.candidates, explain
            )
            if response.corpus_snapshot_id != self.manifest["corpus_snapshot_id"]:
                raise ValueError("cannot combine different corpus snapshots")
            sparse = [
                {
                    "chunk_id": hit.chunk_id,
                    "bm25_score": hit.score,
                    "contributions": [
                        {"term": c.term, "score": c.score, "tf": c.tf, "df": c.df}
                        for c in hit.contributions
                    ],
                }
                for hit in response.hits
            ]
            timings["sparse_ms"] = response.search_ms
            total = response.total_matches
        if self.retrieval != "sparse":
            dense_start = time.perf_counter()
            vector = self.model.encode([self.model.config["query_prefix"] + query])[0]
            dense = exact_search(
                self.vectors,
                [c["chunk_id"] for c in self.embedding["chunks"]],
                vector,
                self.candidates,
            )
            timings["dense_ms"] = (time.perf_counter() - dense_start) * 1000
            total = len(self.chunks)
        if self.retrieval == "hybrid":
            ranked = fuse([sparse, dense])
            total = len(ranked)
        else:
            ranked = sparse if self.retrieval == "sparse" else dense
        sparse_scores = {item["chunk_id"]: item for item in sparse}
        dense_scores = {item["chunk_id"]: item["cosine_score"] for item in dense}
        hits = []
        for rank, item in enumerate(ranked[:top_k], 1):
            chunk = self.chunks[item["chunk_id"]]
            score_key = {"sparse": "bm25_score", "dense": "cosine_score", "hybrid": "rrf_score"}[
                self.retrieval
            ]
            score = item[score_key]
            if not math.isfinite(score):
                raise ValueError("nonfinite retrieval score")
            hit = {
                "rank": rank,
                "chunk_id": chunk["chunk_id"],
                "paper_id": chunk["paper_id"],
                "paper_version_id": chunk["paper_version_id"],
                "title": self.titles[chunk["paper_version_id"]],
                "text": chunk["text"],
                "page_range": chunk["page_range"],
                "score": score,
                "bm25_score": sparse_scores.get(chunk["chunk_id"], {}).get("bm25_score"),
                "cosine_score": dense_scores.get(chunk["chunk_id"]),
                "rrf_score": item.get("rrf_score"),
            }
            if explain:
                hit["contributions"] = sparse_scores.get(chunk["chunk_id"], {}).get(
                    "contributions", []
                )
            if self.evidence_index is not None:
                hit.update(self.evidence_index.attributes(chunk))
            else:
                hit.update(evidence_type="prose", source_locator=None)
            hits.append(hit)
        timings["search_ms"] = (time.perf_counter() - start) * 1000
        return {
            **self.stats(),
            "request_id": uuid.uuid4().hex,
            "total_matches": total,
            "hits": hits,
            "timings": timings,
        }
