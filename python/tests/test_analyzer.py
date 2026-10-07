import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from retrievec.corpus.analyzer import GoAnalyzer
from retrievec.corpus.snapshot import CorpusError, canonical

ROOT = Path(__file__).resolve().parents[2]


class AnalyzerTests(unittest.TestCase):
    def test_external_offsets_must_align_to_utf8_boundaries(self):
        for start, end, invalid in ((0, 2, False), (1, 2, True), (0, 1, True)):
            with self.subTest(start=start, end=end):
                response = canonical(
                    {
                        "analyzer_version": "analyzer-v1-unicode-fixture",
                        "tokens": [[{"term": "é", "position": 0, "start": start, "end": end}]],
                    }
                )
                result = subprocess.CompletedProcess(["fixture-engine", "analyze"], 0, response)
                analyzer = GoAnalyzer("fixture-engine")
                with patch("retrievec.corpus.analyzer.subprocess.run", return_value=result):
                    if invalid:
                        with self.assertRaisesRegex(CorpusError, "UTF-8 boundary"):
                            analyzer.analyze(["é x"])
                        self.assertEqual(analyzer.version, "")
                    else:
                        self.assertEqual(analyzer.analyze(["é x"])[0][0]["end"], 2)

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
