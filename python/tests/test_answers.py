import json
import unittest

from retrievec.app.answers import abstention, validate_answer


class AnswerTests(unittest.TestCase):
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
