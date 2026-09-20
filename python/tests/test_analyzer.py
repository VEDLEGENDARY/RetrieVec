import json
import unittest
from pathlib import Path

from retrievec.corpus.analyzer import GoAnalyzer
from retrievec.corpus.snapshot import CorpusError

ROOT = Path(__file__).resolve().parents[2]


class AnalyzerTests(unittest.TestCase):
    def test_shared_go_fixtures(self) -> None:
        fixtures = json.loads((ROOT / "datasets/fixtures/analyzer-v1.json").read_text("utf-8"))
        analyzer = GoAnalyzer()
        batches = analyzer.analyze([fixture["text"] for fixture in fixtures])
        self.assertTrue(analyzer.version.startswith("analyzer-v1-unicode-"))
        for fixture, tokens in zip(fixtures, batches, strict=True):
            with self.subTest(text=fixture["text"]):
                self.assertEqual([token["term"] for token in tokens], fixture["terms"])
                self.assertEqual([token["position"] for token in tokens], list(range(len(tokens))))
                for token in tokens:
                    fixture["text"].encode("utf-8")[token["start"] : token["end"]].decode("utf-8")

    def test_limits_and_missing_executable(self) -> None:
        with self.assertRaises(CorpusError):
            GoAnalyzer().analyze([""] * 257)
        with self.assertRaises(CorpusError):
            GoAnalyzer().analyze(["x" * (1024 * 1024 + 1)])
        with self.assertRaises(CorpusError):
            GoAnalyzer("missing-retrieval-engine").analyze(["hello"])
