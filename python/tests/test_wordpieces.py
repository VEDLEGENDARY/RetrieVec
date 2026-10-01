import unittest
from types import SimpleNamespace

from retrievec.corpus.analyzer import GoAnalyzer
from retrievec.corpus.snapshot import CorpusError, digest
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
