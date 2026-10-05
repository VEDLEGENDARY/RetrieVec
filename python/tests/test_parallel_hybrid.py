import unittest
from contextvars import ContextVar
from pathlib import Path
from threading import Event
from types import SimpleNamespace
from unittest.mock import Mock, patch

from retrievec.dense.hybrid import PinnedClient
from retrievec.dense.model import FixtureModel
from retrievec.dense.parallel import run_legs


class ParallelHybridTests(unittest.TestCase):
    def test_legs_overlap_and_preserve_context_without_timing_assertions(self):
        started, release = Event(), Event()
        context = ContextVar("test_request", default="missing")
        token = context.set("request")

        def sparse():
            started.set()
            if not release.wait(5):
                raise AssertionError("dense leg did not overlap sparse leg")
            return context.get()

        def dense():
            self.assertTrue(started.wait(5))
            release.set()
            return "dense"

        try:
            self.assertEqual(run_legs(sparse, dense, concurrent=True), ("request", "dense"))
        finally:
            release.set()
            context.reset(token)

    def test_failures_propagate_without_publishing_a_partial_ranking(self):
        def fail():
            raise ValueError("leg failed")

        for concurrent in (False, True):
            for sparse, dense in ((fail, lambda: []), (lambda: [], fail)):
                with (
                    self.subTest(concurrent=concurrent),
                    self.assertRaisesRegex(ValueError, "leg failed"),
                ):
                    run_legs(sparse, dense, concurrent=concurrent)

    def test_pinned_results_and_scores_equal_sequential_path(self):
        # Transport fixture; the actual dense scoring, fusion, explanation and
        # pinned-client assembly execute on both paths. Full-corpus offline Go
        # parity is also checked before each measured benchmark comparison.
        model = FixtureModel()
        texts = ["dense lexical retrieval", "lexical evidence", "dense lexical retrieval"]
        chunks = [
            dict(
                chunk_id=f"c{i}",
                paper_id=f"p{i}",
                paper_version_id=f"v{i}",
                text=text,
                page_range=[1, 1],
            )
            for i, text in enumerate(texts)
        ]
        manifest = {
            "capabilities": ["sparse", "dense", "hybrid"],
            "corpus_snapshot_id": "corpus",
            "embedding_id": "embedding",
            "analyzer_version": "fixture",
        }
        registry = Mock()
        registry.resolve.return_value = {"snapshot_id": "snapshot", "manifest": manifest}
        store = Mock(root=Path("fixture-store"))
        store.manifest.return_value = manifest
        node = Mock()
        node.info.return_value = SimpleNamespace(
            corpus_snapshot_id="corpus",
            chunk_count=3,
            term_count=5,
            total_tokens=8,
            average_length=8 / 3,
        )
        node.search.return_value = SimpleNamespace(
            corpus_snapshot_id="corpus",
            search_ms=0,
            total_matches=2,
            hits=[
                SimpleNamespace(
                    chunk_id=key,
                    score=score,
                    contributions=[SimpleNamespace(term="lexical", score=score, tf=1, df=2)],
                )
                for key, score in [("c2", 2.0), ("c0", 2.0)]
            ],
        )
        with (
            patch(
                "retrievec.dense.hybrid.load_snapshot",
                return_value=(
                    {"configuration": {}},
                    [dict(paper_version_id=f"v{i}", title=f"Paper {i}") for i in range(3)],
                    chunks,
                ),
            ),
            patch(
                "retrievec.dense.hybrid.load_embeddings",
                return_value=(
                    {"configuration": model.config, "chunks": chunks},
                    model.encode(texts),
                ),
            ),
        ):
            clients = [
                PinnedClient(
                    registry, store, node, "owner", "collection", model=model, concurrent_legs=value
                )
                for value in (False, True)
            ]
            for query in ("lexical", "dense retrieval", "unseen query"):
                for cutoff in (1, 3):
                    sequential, parallel = [
                        client.search(query, top_k=cutoff, explain=True) for client in clients
                    ]
                    for result in (sequential, parallel):
                        result.pop("request_id")
                        result.pop("timings")
                    self.assertEqual(sequential, parallel)
            node.search.return_value.corpus_snapshot_id = "different"
            with self.assertRaisesRegex(ValueError, "different corpus"):
                clients[1].search("lexical")
            registry.resolve.side_effect = PermissionError("revoked")
            node.search.reset_mock()
            with self.assertRaises(PermissionError):
                clients[1].search("lexical")
            node.search.assert_not_called()
