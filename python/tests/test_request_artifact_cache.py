import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np
from retrievec.dense.hybrid import PinnedClient
from retrievec.dense.model import FixtureModel


class RequestArtifactCacheTests(unittest.TestCase):
    def test_reuse_does_not_cache_permission(self):
        model = FixtureModel()
        manifest = {
            "capabilities": ["sparse", "dense", "hybrid"],
            "corpus_snapshot_id": "corpus",
            "embedding_id": "embedding",
        }
        registry = Mock()
        registry.resolve.return_value = {"snapshot_id": "snapshot", "manifest": manifest}
        store = Mock(root=Path("fixture-store"))
        store.manifest.return_value = manifest
        node = Mock()
        node.info.return_value = SimpleNamespace(corpus_snapshot_id="corpus")
        cache = {}
        with (
            patch(
                "retrievec.dense.hybrid.load_snapshot", return_value=({"configuration": {}}, [], [])
            ) as corpus,
            patch(
                "retrievec.dense.hybrid.load_embeddings",
                return_value=({"configuration": model.config, "chunks": []}, np.empty((0, 32))),
            ) as embeddings,
        ):
            for mode in ("sparse", "dense", "hybrid"):
                client = PinnedClient(
                    registry,
                    store,
                    node,
                    "owner",
                    "collection",
                    mode,
                    model,
                    "snapshot",
                    artifact_cache=cache,
                )
            self.assertEqual(corpus.call_count, 1)
            self.assertEqual(embeddings.call_count, 1)
            registry.resolve.side_effect = PermissionError("revoked")
            with self.assertRaises(PermissionError):
                client.search("question")
            with self.assertRaises(PermissionError):
                PinnedClient(
                    registry,
                    store,
                    node,
                    "other",
                    "collection",
                    "dense",
                    model,
                    "snapshot",
                    artifact_cache=cache,
                )
            node.search.assert_not_called()
