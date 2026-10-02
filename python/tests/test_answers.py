import json
import unittest

from retrievec.app.answers import abstention, safe, validate_answer


class AnswerTests(unittest.TestCase):
    def test_scientific_prose_and_untrusted_markup_table(self):
        accepted = [
            "p < 0.05 and n > 30",
            "training data: 100 passages",
            "data: not reported",
            "x <= 5",
            "n >= 30",
            "A > B",
            "95% confidence",
            "O(n log n)",
            "Model A: baseline",
            "No links in this answer.",
        ]
        rejected = [
            "<script>alert(1)</script>",
            "<img src=x onerror=alert(1)>",
            "<svg/onload=alert(1)>",
            "<b>bold</b>",
            "<!-- comment -->",
            "https://example.org",
            "HTTP:example.org",
            "javascript:alert(1)",
            "data:text/html,hello",
            "data:;base64,abc",
            "data:,hello",
            "<?xml?>",
        ]
        for text in accepted:
            with self.subTest(text=text):
                safe({"claims": [text]})
        for text in rejected:
            with self.subTest(text=text), self.assertRaises(ValueError):
                safe({"claims": [text]})

    evidence = [{"evidence_id": "e_1", "text": "Method A reports 42 percent on dataset B."}]

    def answer(self):
        return {
            "status": "answered",
            "claims": [
                {
                    "id": "c1",
                    "text": "A reports 42 percent.",
                    "evidence_ids": ["e_1"],
                    "support_status": "structurally_valid",
                    "quotes": [{"evidence_id": "e_1", "text": "42 percent"}],
                }
            ],
            "comparisons": [],
            "limitations": ["Conditions not reported"],
        }

    def test_valid_structure_and_abstention(self):
        self.assertEqual(validate_answer(json.dumps(self.answer()), self.evidence), self.answer())
        self.assertEqual(validate_answer(json.dumps(abstention()), []), abstention())

    def test_fabricated_citations_quotes_numbers_and_markup_rejected(self):
        for field, value in (
            ("evidence_ids", ["invented"]),
            ("quotes", [{"evidence_id": "e_1", "text": "99 percent"}]),
            ("text", "Reports 99 percent"),
            ("text", "<script>alert(1)</script>"),
            ("text", "javascript:steal()"),
        ):
            result = self.answer()
            result["claims"][0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                validate_answer(json.dumps(result), self.evidence)

    def test_no_evidence_or_unexpected_tool_call(self):
        with self.assertRaises(ValueError):
            validate_answer(json.dumps(self.answer()), [])
        with self.assertRaises(ValueError):
            validate_answer(json.dumps({**self.answer(), "tool_call": "read files"}), self.evidence)

    def test_paper_number_cannot_be_attributed_to_project_measurements(self):
        answer = self.answer()
        answer["claims"][0]["text"] = "RetrieVec measured 42 percent."
        with self.assertRaisesRegex(ValueError, "RetrieVec measurement"):
            validate_answer(json.dumps(answer), self.evidence)
