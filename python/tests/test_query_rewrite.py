import unittest

from retrievec.app.query_rewrite import rewrite_query


class RewriteTests(unittest.TestCase):
    def test_bounded_original_history_without_recursive_expansion(self):
        parent = {
            "original_question": "How does BM25 rank?",
            "effective_query": "old private context",
        }
        self.assertEqual(
            rewrite_query("And dense retrieval?", parent),
            "Previous question: How does BM25 rank?\nFollow-up question: And dense retrieval?",
        )
        self.assertEqual(
            rewrite_query(
                "What about their dataset?",
                {"original_question": "Which dataset did the authors use?"},
            ),
            "Previous question: Which dataset did the authors use?\n"
            "Follow-up question: What about their dataset?",
        )
        self.assertEqual(rewrite_query("How does BM25 rank?", parent), "How does BM25 rank?")
        self.assertEqual(rewrite_query("New question", None), "New question")
        with self.assertRaises(ValueError):
            rewrite_query("x" * 4096, parent)
        with self.assertRaises(ValueError):
            rewrite_query("   ", None)
