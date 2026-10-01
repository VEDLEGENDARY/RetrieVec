import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from retrievec.corpus.analyzer import GoAnalyzer
from retrievec.corpus.importer import import_manifest
from retrievec.corpus.snapshot import CorpusError, canonical, digest, load_snapshot
from retrievec.corpus.wordpieces import WordpieceBudget
from tokenizers import Tokenizer, models, pre_tokenizers, processors


class WordpieceTests(unittest.TestCase):
    def budget(self, limit=12):
        tokenizer = Tokenizer(models.WordPiece({"[UNK]": 0, "[CLS]": 1, "[SEP]": 2, ".": 3}))
        tokenizer.pre_tokenizer = pre_tokenizers.BertPreTokenizer()
        tokenizer.post_processor = processors.TemplateProcessing(
            single="[CLS] $A [SEP]", special_tokens=[("[CLS]", 1), ("[SEP]", 2)]
        )
        model = SimpleNamespace(
            tokenizer=tokenizer,
            config={
                "max_tokens": limit,
                "document_prefix": "",
                "revision": "test",
                "tokenizer_sha256": digest(tokenizer.to_str().encode()),
            },
        )
        return WordpieceBudget(model, GoAnalyzer())

    def test_punctuation_and_unicode_are_preserved_with_indexable_chunks(self):
        budget = self.budget()
        text = "café . . . . . alpha . . . . . βeta . . . . . final"
        parts = budget.split(text)
        self.assertGreater(len(parts), 1)
        self.assertEqual("".join(parts).encode(), text.encode())
        self.assertTrue(all(budget.fits(part) for part in parts))
        self.assertTrue(all(budget.analyzer.analyze(parts)))
        self.assertEqual(parts, budget.split(text))
        self.assertEqual(budget.split("short text"), ["short text"])
        self.assertNotEqual(budget.version, self.budget(13).version)

    def test_unsplittable_span_is_rejected_not_truncated(self):
        with self.assertRaises(CorpusError):
            self.budget().split("word " + ". " * 20)

    def test_import_round_trip_records_opt_in_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            text = "alpha . . . . . beta . . . . . gamma . . . . . final"
            raw = text.encode()
            (root / "paper.txt").write_bytes(raw)
            (root / "manifest.json").write_bytes(
                canonical(
                    {
                        "schema_version": 1,
                        "sources": [
                            {
                                "paper_id": "paper",
                                "title": "Synthetic",
                                "authors": [],
                                "path": "paper.txt",
                                "source_url": None,
                                "source_sha256": digest(raw),
                                "license_note": "synthetic",
                            }
                        ],
                    }
                )
            )
            args = (root / "manifest.json", root, root / "output")
            original = import_manifest(*args)
            refined = import_manifest(*args, wordpiece_budget=self.budget())
            self.assertNotEqual(original, refined)
            manifest, _, chunks = load_snapshot(refined)
            self.assertEqual(
                json.loads(manifest["configuration"]["wordpiece_budget"])["max_tokens"], 12
            )
            self.assertEqual(
                "".join(c["text"] for c in sorted(chunks, key=lambda c: c["ordinal"])), text
            )
            self.assertEqual(refined, import_manifest(*args, wordpiece_budget=self.budget()))
